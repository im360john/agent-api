from typing import Optional, List, Union
import os
from datetime import datetime
from textwrap import dedent
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.knowledge.text import TextKnowledgeBase
from agno.knowledge.document import Document
from agno.vectordb.pgvector import PgVector, SearchType
from agno.embedder.openai import OpenAIEmbedder
from agno.tools.firecrawl import FirecrawlTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.storage.agent.postgres import PostgresAgentStorage
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import asyncio
import json
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def get_slack_treez_agent(
    model_id: str = "gpt-4o",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    """
    Create a Slack-integrated Treez support expert agent.
    
    This agent can:
    - Respond to Slack messages when mentioned
    - Search Treez documentation (support.treez.io)
    - Provide expert guidance on Treez products
    - Update its knowledge base with latest documentation
    """
    
    # Check for required API keys
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    if not os.getenv("SLACK_BOT_TOKEN"):
        logger.warning("SLACK_BOT_TOKEN not found - Slack integration will not work")
    
    if not os.getenv("FIRECRAWL_API_KEY"):
        logger.warning("FIRECRAWL_API_KEY not found - Knowledge base updates may be limited")
    
    # Database configuration from environment or defaults
    db_url = os.getenv("DATABASE_URL", "postgresql+psycopg://ai:ai@localhost:5432/ai")
    
    # Handle legacy postgres:// URLs
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    
    # Initialize tools
    tools = []
    
    # Add Firecrawl for documentation scraping if API key is available
    if os.getenv("FIRECRAWL_API_KEY"):
        tools.append(FirecrawlTools(
            api_key=os.getenv("FIRECRAWL_API_KEY"),
            scrape=True,
            crawl=True
        ))
    
    # Add DuckDuckGo as fallback for general searches
    tools.append(DuckDuckGoTools())
    
    # Set up knowledge base with PgVector
    knowledge_base = TextKnowledgeBase(
        vector_db=PgVector(
            table_name="treez_support_articles",
            db_url=db_url,
            search_type=SearchType.hybrid,
            embedder=OpenAIEmbedder(
                id="text-embedding-3-small"
            )
        )
    )
    
    # Storage configuration
    storage = PostgresAgentStorage(
        table_name="slack_treez_agent_sessions", 
        db_url=db_url
    )
    
    # Memory configuration for personalization
    memory_db = PostgresMemoryDb(
        table_name="slack_treez_agent_memory",
        db_url=db_url
    )
    memory = Memory(
        model=OpenAIChat(id=model_id),
        db=memory_db,
        delete_memories=True,
        clear_memories=True
    )
    
    # Initialize the agent
    run_id = datetime.now().strftime("%Y%m%d%H%M%S")
    agent = Agent(
        agent_id=f"slack_treez_agent_{run_id}",
        name="Treez Support Expert",
        model=OpenAIChat(id=model_id),
        knowledge=knowledge_base,
        search_knowledge=True,  # Enable agentic RAG
        tools=tools,
        instructions=dedent("""\
            You are an expert Treez support agent responding via Slack.
            
            You have comprehensive knowledge of all Treez products including:
            - Treez POS (Point of Sale) system
            - Treez eCommerce platform
            - Treez Payments solutions
            - Treez Compliance tools
            - Treez API and integrations
            - Treez reporting and analytics
            
            When responding:
            1. ALWAYS search your knowledge base first for Treez-specific information
            2. Provide accurate answers based on official Treez documentation
            3. Include relevant article titles or links when available
            4. Format responses for Slack readability (use bullet points, numbered lists)
            5. For multi-step processes, provide clear step-by-step instructions
            6. If information isn't in your knowledge base, use web search for latest updates
            7. Be concise but comprehensive - Slack messages should be easy to read
            8. Use Slack markdown formatting when helpful (bold, italics, code blocks)
            
            Response format for Slack:
            - Use *bold* for emphasis
            - Use `code` for technical terms or commands
            - Use ```code blocks``` for multi-line code or configurations
            - Use • for bullet points
            - Keep paragraphs short for mobile readability
            
            If asked about topics not in Treez documentation, politely redirect to Treez support or indicate it's outside your knowledge area.
            
            Additional Information:
            - You are interacting with user_id: {current_user_id}
            - The current session_id is: {current_session_id}
        """),
        storage=storage,
        memory=memory,
        enable_agentic_memory=True,
        user_id=user_id,
        session_id=session_id,
        markdown=True,
        debug_mode=debug_mode,
        monitoring=True,
        description=dedent("""\
            You are a Treez Support Expert, providing accurate and helpful guidance on all Treez products and features.
            
            Your responses are tailored for Slack communication - clear, concise, and well-formatted.
        """),
        add_history_to_messages=True,
        num_history_runs=5,  # Keep last 5 messages for context
        read_chat_history=True,  # Add tool to read chat history
        add_datetime_to_instructions=True,  # Add current date/time automatically
        add_state_in_messages=True,  # Make user_id available in instructions
        show_tool_calls=False,  # Clean output for Slack
    )
    
    return agent


class SlackTreezBot:
    """Wrapper class for Slack integration"""
    
    def __init__(self, agent: Agent, slack_token: Optional[str] = None):
        self.agent = agent
        self.slack_token = slack_token or os.getenv("SLACK_BOT_TOKEN")
        if self.slack_token:
            self.slack_client = WebClient(token=self.slack_token)
        else:
            self.slack_client = None
            logger.warning("No Slack token provided - bot will not be able to send messages")
    
    async def process_mention(self, event: dict) -> Optional[str]:
        """Process a Slack mention and return response"""
        text = event.get("text", "")
        user = event.get("user", "unknown")
        
        # Clean the text (remove bot mention)
        clean_text = text.split(">", 1)[1].strip() if ">" in text else text
        
        # Add user context to session
        session_id = f"slack_{event.get('channel', 'unknown')}_{event.get('ts', '')}"
        
        try:
            # Run the agent with the cleaned message
            response = self.agent.run(
                clean_text,
                session_id=session_id,
                user_id=f"slack_{user}"
            )
            
            return response.content
        except Exception as e:
            logger.error(f"Error processing Slack mention: {str(e)}")
            return f"I apologize, but I encountered an error processing your request: {str(e)}"
    
    async def send_response(self, channel: str, text: str, thread_ts: Optional[str] = None):
        """Send a response to Slack"""
        if not self.slack_client:
            logger.error("No Slack client available - cannot send message")
            return
        
        try:
            self.slack_client.chat_postMessage(
                channel=channel,
                text=text,
                thread_ts=thread_ts
            )
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
    
    async def update_knowledge_base(self, urls: Optional[List[str]] = None) -> dict:
        """Update the Treez knowledge base with latest documentation"""
        if urls is None:
            # Start with the main support site
            urls = ["https://support.treez.io/en/"]
        
        results = {"updated": 0, "failed": 0, "urls": [], "crawled_urls": []}
        
        # Initialize Firecrawl if available
        firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
        if not firecrawl_api_key:
            logger.error("FIRECRAWL_API_KEY not found - cannot crawl documentation")
            results["failed"] = len(urls)
            return results
        
        try:
            from firecrawl import FirecrawlApp
            firecrawl = FirecrawlApp(api_key=firecrawl_api_key)
        except ImportError:
            logger.error("firecrawl-py not installed")
            results["failed"] = len(urls)
            return results
        
        # Get vector database
        if hasattr(self.agent.knowledge, '_kb') and hasattr(self.agent.knowledge._kb, 'vector_db'):
            vector_db = self.agent.knowledge._kb.vector_db
        elif hasattr(self.agent.knowledge, 'vector_db'):
            vector_db = self.agent.knowledge.vector_db
        else:
            logger.error("Cannot access vector database from knowledge base")
            results["failed"] = len(urls)
            return results
        
        for base_url in urls:
            try:
                logger.info(f"Crawling {base_url} and all sub-pages...")
                
                # Use Firecrawl to crawl the entire site
                crawl_params = {
                    'crawlerOptions': {
                        'includes': ['/en/**'],  # Include all English pages
                        'excludes': [],
                        'generateImgAltText': False,
                        'returnOnlyUrls': False,
                        'maxDepth': 10,  # Deep crawl to get all articles
                        'mode': 'crawl',
                        'ignoreSitemap': False,
                        'limit': 500,  # Limit to prevent infinite crawling
                        'allowBackwardCrawling': False,
                        'allowExternalContentLinks': False
                    },
                    'pageOptions': {
                        'includeHtml': False,
                        'includeRawHtml': False,
                        'onlyIncludeTags': ['main', 'article', 'section'],
                        'removeTags': ['nav', 'footer', 'header', 'script', 'style'],
                        'onlyMainContent': True,
                        'waitFor': 1000
                    }
                }
                
                # Start crawl job
                crawl_job = firecrawl.crawl_url(base_url, params=crawl_params)
                
                if crawl_job and 'data' in crawl_job:
                    documents = []
                    
                    for page_data in crawl_job['data']:
                        if 'markdown' in page_data and page_data['markdown']:
                            # Only process pages from support.treez.io
                            page_url = page_data.get('metadata', {}).get('sourceURL', '')
                            if not page_url.startswith('https://support.treez.io'):
                                continue
                            
                            # Extract title
                            title = page_data.get('metadata', {}).get('title', 'Untitled')
                            
                            # Create document
                            doc = Document(
                                content=page_data['markdown'],
                                meta_data={
                                    "title": title,
                                    "source": page_url,
                                    "domain": "support.treez.io",
                                    "description": page_data.get('metadata', {}).get('description', ''),
                                    "updated_at": datetime.now().isoformat()
                                }
                            )
                            documents.append(doc)
                            results["crawled_urls"].append(page_url)
                    
                    # Batch upsert documents
                    if documents:
                        logger.info(f"Upserting {len(documents)} documents from {base_url}")
                        await vector_db.upsert(documents=documents)
                        results["updated"] += len(documents)
                        results["urls"].append(base_url)
                    
                else:
                    logger.error(f"No data returned from crawl of {base_url}")
                    results["failed"] += 1
                    
            except Exception as e:
                logger.error(f"Failed to crawl and update knowledge from {base_url}: {str(e)}")
                results["failed"] += 1
        
        return results


# Helper function to initialize knowledge base with seed data
async def seed_knowledge_base(agent: Agent):
    """Seed the knowledge base with initial Treez documentation"""
    
    seed_content = [
        {
            "title": "Treez Overview",
            "content": """
            Treez is a comprehensive cannabis retail management platform that includes:
            
            **Treez Retail (POS)**
            - Point of Sale system designed specifically for cannabis dispensaries
            - Inventory management with compliance tracking
            - Customer management and loyalty programs
            - Budtender performance tracking
            - Real-time reporting and analytics
            
            **Treez eCommerce**
            - Online menu and ordering platform
            - Integration with POS for real-time inventory
            - Customer accounts and order history
            - Pickup and delivery options
            - SEO-optimized product pages
            
            **Treez Payments**
            - Compliant payment processing for cannabis
            - Cash management solutions
            - Pin debit and ACH options
            - Integrated with POS for seamless checkout
            
            **Compliance Features**
            - State-specific compliance rules
            - Automated compliance reporting
            - Age verification
            - Purchase limit tracking
            - Audit trails
            
            **Integrations**
            - Metrc integration for track-and-trace
            - QuickBooks for accounting
            - Marketing platforms (Springbig, Alpine IQ)
            - Analytics tools
            - Third-party ecommerce platforms
            """,
            "source": "treez_overview",
            "domain": "support.treez.io"
        },
        {
            "title": "Common Treez POS Operations",
            "content": """
            **Creating a Sale**
            1. From the POS screen, search or scan products
            2. Add items to cart
            3. Apply any discounts or promotions
            4. Select customer or create new customer profile
            5. Choose payment method
            6. Complete transaction
            
            **Managing Inventory**
            - Navigate to Inventory > Products
            - Use filters to find specific items
            - Update quantities, prices, and product details
            - Set reorder points and alerts
            - Track inventory movements
            
            **Running Reports**
            - Go to Reports section
            - Select report type (Sales, Inventory, Customer, etc.)
            - Choose date range
            - Apply filters as needed
            - Export to CSV or PDF
            
            **Managing Discounts**
            - Settings > Discounts
            - Create percentage or dollar amount discounts
            - Set conditions (time-based, customer type, product type)
            - Apply automatically or manually
            """,
            "source": "treez_pos_guide",
            "domain": "support.treez.io"
        }
    ]
    
    try:
        # First ensure the table exists by loading the knowledge base
        logger.info("Initializing knowledge base table...")
        await agent.knowledge.aload(recreate=False, upsert=True)
        
        # Convert seed content to Document objects
        documents = []
        for content in seed_content:
            doc = Document(
                content=content["content"],
                meta_data={
                    "title": content["title"],
                    "source": content["source"],
                    "domain": content["domain"]
                }
            )
            documents.append(doc)
        
        # Get the vector database from the knowledge base
        if hasattr(agent.knowledge, '_kb') and hasattr(agent.knowledge._kb, 'vector_db'):
            vector_db = agent.knowledge._kb.vector_db
        elif hasattr(agent.knowledge, 'vector_db'):
            vector_db = agent.knowledge.vector_db
        else:
            raise ValueError("Cannot access vector database from knowledge base")
        
        # Upsert documents into the vector database
        logger.info(f"Inserting {len(documents)} documents into vector database")
        await vector_db.upsert(documents=documents)
        
        logger.info("Knowledge base seeded successfully with initial content")
        return True
    except Exception as e:
        logger.error(f"Failed to seed knowledge base: {str(e)}")
        return False