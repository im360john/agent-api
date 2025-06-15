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
import hashlib
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
    db_url = os.getenv("DATABASE_URL", "postgresql+psycopg://user:password@location/agno")
    
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
            table_name="treez_support_articles",  # Schema will be added by PgVector
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
    
    async def update_knowledge_base(self, urls: Optional[List[str]] = None, force_update: bool = False) -> dict:
        """
        Update the Treez knowledge base with latest documentation
        
        Args:
            urls: List of URLs to crawl. Defaults to main support site.
            force_update: If True, re-crawl and update all documents regardless of existing content.
        
        Note: Processes articles in small batches to avoid memory issues.
        """
        logger.info("=== UPDATE_KNOWLEDGE_BASE v2 - WITH CACHING AND BATCH PROCESSING ===")
        if urls is None:
            # Start with the main support site
            urls = ["https://support.treez.io/en/"]
        
        results = {"updated": 0, "failed": 0, "skipped": 0, "content_updated": 0, "urls": [], "crawled_urls": []}
        
        # Initialize Firecrawl if available
        firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
        if not firecrawl_api_key:
            logger.error("FIRECRAWL_API_KEY not found - cannot crawl documentation")
            results["failed"] = len(urls)
            return results
        
        try:
            from firecrawl import FirecrawlApp, ScrapeOptions
            firecrawl = FirecrawlApp(api_key=firecrawl_api_key)
        except ImportError as e:
            logger.error(f"Required package not installed: {e}")
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
        
        import hashlib
        
        for base_url in urls:
            try:
                logger.info(f"Crawling {base_url} and all sub-pages (using 48-hour cache for unchanged content)...")
                
                # Use async crawling with polling for real-time processing
                # Initialize processing state
                documents = []
                batch_size = 10
                total_processed = 0
                total_with_content = 0
                total_treez_urls = 0
                total_skipped = 0
                total_updated = 0
                total_failed = 0
                first_batch_uploaded = False
                upload_verified = False
                processed_urls = set()  # Track processed URLs to avoid duplicates
                
                async def process_document(page_data, page_url, content):
                    """Process a single document with deduplication"""
                    nonlocal documents, total_skipped, total_updated, first_batch_uploaded, upload_verified
                    
                    # Calculate content hash
                    content_hash = hashlib.md5(content.encode()).hexdigest()
                    
                    # Check for existing document
                    skip_document = False
                    if not force_update:
                        try:
                            existing_docs = vector_db.search(
                                query=page_url,
                                limit=10
                            )
                            
                            for doc in existing_docs:
                                if doc.meta_data.get("source", "") == page_url:
                                    if doc.meta_data.get("content_hash", "") == content_hash:
                                        logger.debug(f"Skipping unchanged: {page_url}")
                                        total_skipped += 1
                                        skip_document = True
                                        break
                                    else:
                                        logger.info(f"Content changed, updating: {page_url}")
                                        total_updated += 1
                                        break
                        except Exception as e:
                            logger.debug(f"Could not check existing doc: {e}")
                    
                    if skip_document:
                        return
                    
                    # Extract metadata
                    title = None
                    if isinstance(page_data, dict):
                        title = page_data.get('title')
                        if not title and 'metadata' in page_data:
                            title = page_data['metadata'].get('title')
                    elif hasattr(page_data, 'title'):
                        title = page_data.title
                    elif hasattr(page_data, 'metadata') and isinstance(page_data.metadata, dict):
                        title = page_data.metadata.get('title') or page_data.metadata.get('ogTitle')
                    
                    # Check content length and chunk if necessary
                    # Rough estimate: 1 token ≈ 4 characters, max 8192 tokens ≈ 32768 chars
                    # Use 30000 to be safe
                    max_content_length = 30000
                    
                    if len(content) > max_content_length:
                        # Chunk the content
                        chunks = []
                        words = content.split()
                        current_chunk = []
                        current_length = 0
                        
                        for word in words:
                            word_length = len(word) + 1  # +1 for space
                            if current_length + word_length > max_content_length:
                                # Save current chunk
                                chunks.append(' '.join(current_chunk))
                                current_chunk = [word]
                                current_length = word_length
                            else:
                                current_chunk.append(word)
                                current_length += word_length
                        
                        # Add final chunk
                        if current_chunk:
                            chunks.append(' '.join(current_chunk))
                        
                        logger.info(f"Document too large ({len(content)} chars), splitting into {len(chunks)} chunks")
                        
                        # Create documents for each chunk
                        for i, chunk in enumerate(chunks):
                            chunk_doc = Document(
                                content=chunk,
                                meta_data={
                                    "title": f"{title or 'Untitled'} (Part {i+1}/{len(chunks)})",
                                    "source": page_url,
                                    "domain": "support.treez.io",
                                    "description": "",
                                    "updated_at": datetime.now().isoformat(),
                                    "content_hash": content_hash,
                                    "chunk_index": i,
                                    "total_chunks": len(chunks)
                                }
                            )
                            documents.append(chunk_doc)
                    else:
                        # Normal document
                        doc = Document(
                            content=content,
                            meta_data={
                                "title": title or 'Untitled',
                                "source": page_url,
                                "domain": "support.treez.io",
                                "description": "",
                                "updated_at": datetime.now().isoformat(),
                                "content_hash": content_hash
                            }
                        )
                        documents.append(doc)
                    
                    results["crawled_urls"].append(page_url)
                    
                    # Process batch when ready
                    if len(documents) >= batch_size:
                        await upload_batch()
                
                async def upload_batch():
                    """Upload a batch of documents"""
                    nonlocal documents, first_batch_uploaded, upload_verified
                    
                    if not documents:
                        return
                    
                    logger.info(f"Uploading batch of {len(documents)} documents...")
                    try:
                        result = vector_db.upsert(documents=documents)
                        if result is not None and hasattr(result, '__await__'):
                            await result
                        
                        results["updated"] += len(documents)
                        logger.info(f"✅ Successfully uploaded {len(documents)} documents")
                        
                        # Verify first batch
                        if not first_batch_uploaded:
                            first_batch_uploaded = True
                            logger.info("=== FIRST BATCH VERIFICATION ===")
                            if documents and not upload_verified:
                                test_url = documents[0].meta_data.get("source", "")
                                try:
                                    search_results = vector_db.search(query=test_url, limit=1)
                                    if search_results and len(search_results) > 0:
                                        logger.info(f"✅ Upload verification PASSED")
                                        upload_verified = True
                                    else:
                                        logger.error(f"❌ Upload verification FAILED")
                                        raise Exception("Upload verification failed")
                                except Exception as e:
                                    logger.warning(f"Could not verify upload: {e}")
                                    upload_verified = True
                        
                        documents = []  # Clear batch
                        
                    except Exception as e:
                        logger.error(f"❌ Error uploading batch: {e}")
                        results["failed"] += len(documents)
                        if not first_batch_uploaded:
                            raise Exception(f"First batch upload failed: {e}")
                        documents = []
                
                async def process_pages_batch(pages):
                    """Process a batch of pages"""
                    nonlocal total_processed, total_with_content, total_treez_urls, processed_urls
                    
                    for page_data in pages:
                        # Skip if already processed
                        page_url = None
                        if isinstance(page_data, dict):
                            page_url = page_data.get('url') or page_data.get('sourceURL')
                            if not page_url and 'metadata' in page_data:
                                page_url = page_data['metadata'].get('url') or page_data['metadata'].get('sourceURL')
                        elif hasattr(page_data, 'url') and page_data.url:
                            page_url = page_data.url
                        elif hasattr(page_data, 'metadata') and isinstance(page_data.metadata, dict):
                            page_url = page_data.metadata.get('url') or page_data.metadata.get('sourceURL')
                        
                        if not page_url:
                            logger.warning("No URL found for page in batch processing")
                            continue
                            
                        if page_url in processed_urls:
                            logger.debug(f"Skipping already processed URL: {page_url}")
                            continue
                        
                        logger.info(f"Processing URL: {page_url}")
                        processed_urls.add(page_url)
                        total_processed += 1
                        
                        if total_processed % 2 == 0:
                            logger.info(f"📊 Progress: Processed {total_processed} pages")
                        
                        # Only process Treez URLs
                        if not page_url.startswith('https://support.treez.io'):
                            logger.debug(f"Skipping non-Treez URL: {page_url}")
                            continue
                        
                        total_treez_urls += 1
                        
                        # Extract content
                        content = None
                        if isinstance(page_data, dict):
                            content = page_data.get('markdown') or page_data.get('content') or page_data.get('text')
                        elif hasattr(page_data, 'markdown'):
                            content = page_data.markdown
                        elif hasattr(page_data, 'content'):
                            content = page_data.content
                        
                        if not content:
                            logger.debug(f"Page {page_url} has no content")
                            continue
                        
                        total_with_content += 1
                        
                        # Process the document
                        await process_document(page_data, page_url, content)
                
                try:
                    logger.info("Starting async crawl with polling...")
                    
                    # Start async crawl job
                    crawl_job = firecrawl.async_crawl_url(
                        base_url,
                        limit=800,  # Full crawl limit
                        scrape_options=ScrapeOptions(
                            formats=['markdown'],
                            maxAge=172800  # 48-hour cache
                        )
                    )
                    
                    if not crawl_job.success:
                        raise Exception(f"Failed to start crawl: {crawl_job.error}")
                    
                    crawl_id = crawl_job.id
                    logger.info(f"✅ Crawl job started. ID: {crawl_id}")
                    
                    # Poll for results
                    poll_count = 0
                    last_completed = 0
                    
                    while True:
                        # Check crawl status
                        status = firecrawl.check_crawl_status(crawl_id)
                        
                        if not status.success:
                            raise Exception(f"Failed to check status: {status.error}")
                        
                        # Debug status structure on first poll
                        if poll_count == 0:
                            logger.info(f"Status type: {type(status)}")
                            logger.info(f"Status attributes: {[attr for attr in dir(status) if not attr.startswith('_')]}")
                            if hasattr(status, 'data'):
                                logger.info(f"Status.data type: {type(status.data)}, has data: {status.data is not None}")
                        
                        # Log progress
                        if status.completed != last_completed:
                            logger.info(f"📈 Crawl progress: {status.completed}/{status.total} pages (Status: {status.status})")
                            last_completed = status.completed
                        
                        # Process new documents
                        if status.data:
                            logger.info(f"📋 Status has {len(status.data)} documents to process")
                            # Get only new pages (not already processed)
                            new_pages = []
                            for i, page in enumerate(status.data):
                                # Debug first page structure
                                if i == 0:
                                    logger.info(f"First page type: {type(page)}")
                                    if hasattr(page, '__dict__'):
                                        logger.info(f"Page attributes: {[attr for attr in dir(page) if not attr.startswith('_')][:10]}")
                                
                                # Get URL to check if processed
                                url = None
                                if isinstance(page, dict):
                                    url = page.get('url') or page.get('sourceURL') 
                                    if not url and 'metadata' in page:
                                        url = page['metadata'].get('url') or page['metadata'].get('sourceURL')
                                elif hasattr(page, 'url') and page.url:
                                    url = page.url
                                elif hasattr(page, 'sourceURL') and page.sourceURL:
                                    url = page.sourceURL
                                elif hasattr(page, 'metadata'):
                                    if isinstance(page.metadata, dict):
                                        url = page.metadata.get('url') or page.metadata.get('sourceURL')
                                    elif hasattr(page.metadata, 'sourceURL'):
                                        url = page.metadata.sourceURL
                                
                                if not url:
                                    logger.warning(f"Page {i} has no URL!")
                                    continue
                                
                                if url not in processed_urls:
                                    new_pages.append(page)
                                else:
                                    logger.debug(f"URL already processed: {url}")
                            
                            if new_pages:
                                logger.info(f"📄 Processing {len(new_pages)} new pages...")
                                await process_pages_batch(new_pages)
                                
                                # Upload batch if ready
                                if documents and len(documents) >= batch_size:
                                    await upload_batch()
                        
                        # Check if complete
                        if status.status in ['completed', 'failed', 'cancelled']:
                            logger.info(f"🏁 Crawl finished with status: {status.status}")
                            break
                        
                        # Wait before next poll
                        await asyncio.sleep(2)
                        poll_count += 1
                        
                        # Safety limit
                        if poll_count > 300:  # 10 minutes max
                            logger.warning("Crawl timeout - stopping poll")
                            break
                    
                    # Process any remaining documents
                    if documents:
                        await upload_batch()
                    
                except Exception as e:
                    logger.error(f"Error during async crawl: {str(e)}")
                    logger.error(f"Full traceback:", exc_info=True)
                    raise
                
                # Log final summary
                logger.info(f"\n=== CRAWL SUMMARY ===")
                logger.info(f"Total pages crawled: {total_processed}")
                logger.info(f"Pages with content: {total_with_content}")
                logger.info(f"Treez URLs found: {total_treez_urls}")
                logger.info(f"Documents skipped (unchanged): {total_skipped}")
                logger.info(f"Documents updated (content changed): {total_updated}")
                logger.info(f"Documents added to knowledge base: {results['updated']}")
                logger.info(f"Failed: {total_failed}")
                logger.info(f"===================\n")
                
                # Add statistics to results
                results["skipped"] = total_skipped
                results["content_updated"] = total_updated
                results["urls"].append(base_url)

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
        # Get the vector database from the knowledge base
        if hasattr(agent.knowledge, '_kb') and hasattr(agent.knowledge._kb, 'vector_db'):
            vector_db = agent.knowledge._kb.vector_db
        elif hasattr(agent.knowledge, 'vector_db'):
            vector_db = agent.knowledge.vector_db
        else:
            # Try to access the actual TextKnowledgeBase
            if hasattr(agent.knowledge, 'knowledge') and hasattr(agent.knowledge.knowledge, 'vector_db'):
                vector_db = agent.knowledge.knowledge.vector_db
            else:
                raise ValueError("Cannot access vector database from knowledge base")
        
        # Ensure the table exists by running create_table SQL directly
        logger.info("Ensuring vector database table exists...")
        try:
            # Try to use the vector_db's connection to create table
            if hasattr(vector_db, 'Session') or hasattr(vector_db, 'db_url'):
                from sqlalchemy import text, create_engine
                from sqlalchemy.orm import sessionmaker
                
                # Get database URL
                db_url_for_table = getattr(vector_db, 'db_url', db_url)
                engine = create_engine(db_url_for_table.replace('+asyncpg', '').replace('+aiopg', ''))
                
                with engine.begin() as conn:
                    # First ensure schema exists
                    conn.execute(text("CREATE SCHEMA IF NOT EXISTS ai"))
                    
                    # Create the table with proper structure
                    create_table_sql = """
                    CREATE TABLE IF NOT EXISTS ai.treez_support_articles (
                        id VARCHAR PRIMARY KEY,
                        name VARCHAR,
                        meta_data JSONB,
                        filters JSONB,
                        content TEXT,
                        embedding VECTOR(1536),
                        usage JSONB,
                        content_hash VARCHAR
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_treez_support_articles_embedding 
                    ON ai.treez_support_articles USING ivfflat (embedding vector_cosine_ops);
                    """
                    conn.execute(text(create_table_sql))
                    logger.info("Table created successfully")
            else:
                # Fallback - try to trigger table creation
                logger.warning("Cannot access database connection directly, trying fallback")
                if hasattr(vector_db, 'create_table'):
                    await vector_db.create_table()
        except Exception as e:
            logger.warning(f"Table creation attempt failed (may already exist): {e}")
        
        # Convert seed content to Document objects
        documents = []
        import hashlib
        for content in seed_content:
            content_hash = hashlib.md5(content["content"].encode()).hexdigest()
            doc = Document(
                content=content["content"],
                meta_data={
                    "title": content["title"],
                    "source": content["source"],
                    "domain": content["domain"],
                    "updated_at": datetime.now().isoformat(),
                    "content_hash": content_hash
                }
            )
            documents.append(doc)
        
        # Upsert documents into the vector database
        logger.info(f"Inserting {len(documents)} documents into vector database")
        
        # Check if upsert is async or sync
        result = vector_db.upsert(documents=documents)
        if result is not None and hasattr(result, '__await__'):
            await result
        
        logger.info("Knowledge base seeded successfully with initial content")
        return True
    except Exception as e:
        logger.error(f"Failed to seed knowledge base: {str(e)}")
        return False
