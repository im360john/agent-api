#!/usr/bin/env python3
"""
Optimized Slack Agent with performance improvements for knowledge base search
"""

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

def get_optimized_slack_agent(
    model_id: str = "gpt-4.1-mini",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    """
    Create an optimized Slack-integrated Treez support expert agent.
    
    Optimizations:
    - Disable knowledge base search for simple queries
    - Use semantic search only (not hybrid)
    - Reduce embeddings model size
    - Connection pooling for database
    - Smaller context window
    """
    
    # Check for required API keys
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    if not os.getenv("SLACK_BOT_TOKEN"):
        logger.warning("SLACK_BOT_TOKEN not found - Slack integration will not work")
    
    # Database configuration with connection pooling
    db_url = os.getenv("DATABASE_URL", "postgresql+psycopg://user:password@location/agno")
    
    # Handle legacy postgres:// URLs
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    
    # Add connection pool settings
    if "?" in db_url:
        db_url += "&pool_size=20&max_overflow=40&pool_pre_ping=true"
    else:
        db_url += "?pool_size=20&max_overflow=40&pool_pre_ping=true"
    
    # Initialize minimal tools
    tools = [DuckDuckGoTools()]
    
    # Set up optimized knowledge base
    knowledge_base = TextKnowledgeBase(
        vector_db=PgVector(
            table_name="treez_support_articles",
            db_url=db_url,
            search_type=SearchType.similarity,  # Use similarity only, not hybrid
            embedder=OpenAIEmbedder(
                id="text-embedding-3-small"
            )
        ),
        num_documents=2  # Reduce to top 2 documents
    )
    
    # Minimal storage configuration
    storage = PostgresAgentStorage(
        table_name="slack_treez_agent_sessions", 
        db_url=db_url
    )
    
    # Minimal memory configuration
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
    
    # Initialize the optimized agent
    run_id = datetime.now().strftime("%Y%m%d%H%M%S")
    agent = Agent(
        agent_id=f"slack_treez_agent_{run_id}",
        name="Treez Support Expert",
        model=OpenAIChat(id=model_id),
        knowledge=knowledge_base,
        search_knowledge=True,  # We'll control this per query
        read_chat_history=False,  # Disable for speed
        tools=tools,
        instructions=dedent("""\
            Treez support expert. For product questions, search knowledge base. For general questions, respond directly.
            
            Products: POS, eCommerce, Payments, Compliance, API
            Format: *bold*, `code`, bullets (•)
            
            Respond concisely for Slack.
        """),
        storage=storage,
        memory=memory,
        enable_agentic_memory=False,  # Disable for speed
        user_id=user_id,
        session_id=session_id,
        markdown=True,
        debug_mode=debug_mode,
        monitoring=False,
        description="Optimized Treez support",
        add_history_to_messages=False,
        num_history_runs=1,  # Minimal history
        add_datetime_to_instructions=False,
        add_state_in_messages=False,
        show_tool_calls=False,
    )
    
    return agent


class OptimizedSlackBot:
    """Optimized wrapper class for Slack integration"""
    
    def __init__(self, agent: Agent, slack_token: Optional[str] = None):
        self.agent = agent
        self.slack_token = slack_token or os.getenv("SLACK_BOT_TOKEN")
        if self.slack_token:
            self.slack_client = WebClient(token=self.slack_token)
        else:
            self.slack_client = None
            logger.warning("No Slack token provided - bot will not be able to send messages")
        
        # Keywords that indicate a Treez-specific query requiring KB search
        self.treez_keywords = {
            'treez', 'pos', 'point of sale', 'ecommerce', 'payment', 'compliance',
            'inventory', 'discount', 'promo', 'carousel', 'prismic', 'product',
            'report', 'analytics', 'integration', 'metrc', 'quickbooks',
            'customer', 'loyalty', 'budtender', 'dispensary', 'menu'
        }
    
    def requires_knowledge_base(self, text: str) -> bool:
        """Determine if query requires knowledge base search"""
        text_lower = text.lower()
        
        # Check for Treez-specific keywords
        for keyword in self.treez_keywords:
            if keyword in text_lower:
                return True
        
        # Check for general queries that don't need KB
        general_patterns = ['weather', 'time', 'date', 'hello', 'hi', 'thanks', 'help me with']
        for pattern in general_patterns:
            if pattern in text_lower and not any(k in text_lower for k in self.treez_keywords):
                return False
        
        # Default to using KB for safety
        return True
    
    async def process_mention(self, event: dict) -> Optional[str]:
        """Process a Slack mention with optimized KB usage"""
        text = event.get("text", "")
        user = event.get("user", "unknown")
        
        # Clean the text (remove bot mention)
        clean_text = text.split(">", 1)[1].strip() if ">" in text else text
        
        # Add user context to session
        session_id = f"slack_{event.get('channel', 'unknown')}_{event.get('ts', '')}"
        
        try:
            # Determine if we need KB search
            use_kb = self.requires_knowledge_base(clean_text)
            
            if not use_kb:
                logger.info(f"Skipping KB search for general query: {clean_text[:50]}...")
                # Temporarily disable KB search
                self.agent.search_knowledge = False
            
            # Run the agent with the cleaned message
            response = self.agent.run(
                clean_text,
                session_id=session_id,
                user_id=f"slack_{user}"
            )
            
            # Re-enable KB search
            self.agent.search_knowledge = True
            
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


# Export the optimized function
def get_slack_treez_agent(
    model_id: str = "gpt-4.1-mini",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    """Wrapper to use optimized agent"""
    return get_optimized_slack_agent(model_id, user_id, session_id, debug_mode)


# Export the optimized bot class
SlackTreezBot = OptimizedSlackBot