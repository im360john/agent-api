#!/usr/bin/env python3
"""
Test script for the update_knowledge_base endpoint
"""
import asyncio
import os
import logging
from agents.slack_treez_agent import get_slack_treez_agent, SlackTreezBot
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_update_knowledge_base():
    """Test the update_knowledge_base function"""
    # Load environment variables
    load_dotenv()
    
    # Verify required environment variables
    required_vars = ["OPENAI_API_KEY", "FIRECRAWL_API_KEY", "DATABASE_URL"]
    for var in required_vars:
        if not os.getenv(var):
            logger.error(f"Missing required environment variable: {var}")
            return
    
    try:
        # Create agent
        logger.info("Creating Slack Treez agent...")
        agent = get_slack_treez_agent(debug_mode=True)
        
        # Create bot wrapper
        bot = SlackTreezBot(agent)
        
        # Test update_knowledge_base
        logger.info("Starting knowledge base update...")
        results = await bot.update_knowledge_base(
            urls=["https://support.treez.io/en/"],
            force_update=True
        )
        
        logger.info("Update completed!")
        logger.info(f"Results: {results}")
        
        # Test a search to verify content was added
        logger.info("\nTesting search in knowledge base...")
        search_results = await agent.knowledge.search("Treez POS", limit=5)
        logger.info(f"Found {len(search_results) if search_results else 0} search results")
        
        if search_results:
            for i, result in enumerate(search_results[:3]):  # Show first 3 results
                logger.info(f"\nResult {i+1}:")
                logger.info(f"Title: {result.meta_data.get('title', 'No title')}")
                logger.info(f"Source: {result.meta_data.get('source', 'No source')}")
                logger.info(f"Content preview: {result.content[:200]}...")
        
    except Exception as e:
        logger.error(f"Error during test: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_update_knowledge_base())