#!/usr/bin/env python3
"""
Test validation with a small number of pages
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Temporarily override the crawl limit for testing
import agents.slack_treez_agent
# Monkey patch the limit for this test
original_code = agents.slack_treez_agent.SlackTreezBot.update_knowledge_base

async def update_with_small_limit(self, urls=None, force_update=False):
    # Save original limit
    import re
    
    # Read the function source
    import inspect
    source = inspect.getsource(original_code)
    
    # Replace limit
    modified_source = source.replace("limit=800,", "limit=10,")
    
    # Create new function with modified source
    exec_globals = {
        'logger': agents.slack_treez_agent.logger,
        'os': os,
        'datetime': agents.slack_treez_agent.datetime,
        'FirecrawlApp': agents.slack_treez_agent.FirecrawlApp,
        'ScrapeOptions': agents.slack_treez_agent.ScrapeOptions,
        'Document': agents.slack_treez_agent.Document,
        'hashlib': agents.slack_treez_agent.hashlib,
        'json': agents.slack_treez_agent.json
    }
    exec(modified_source, exec_globals)
    
    # Call the modified function
    return await exec_globals['update_knowledge_base'](self, urls, force_update)

# Apply monkey patch
agents.slack_treez_agent.SlackTreezBot.update_knowledge_base = update_with_small_limit

from agents.slack_treez_agent import SlackTreezBot, get_slack_treez_agent
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def main():
    """Test with small limit"""
    print("\n=== Testing with 10 page limit ===\n")
    
    # Set correct database
    os.environ["DATABASE_URL"] = "postgresql+psycopg://rag_user:qGufXd7ddboX07VgmEqess0spXiXcmyu@dpg-d0poargdl3ps73b0c630-a.oregon-postgres.render.com:5432/agno"
    
    agent = get_slack_treez_agent(model_id="gpt-4o-mini", debug_mode=True)
    bot = SlackTreezBot(agent=agent)
    
    results = await bot.update_knowledge_base(urls=["https://support.treez.io/en/"])
    
    print("\n=== Results ===")
    print(f"Added: {results['updated']}")
    print(f"Skipped: {results['skipped']}")
    print(f"Failed: {results['failed']}")

if __name__ == "__main__":
    if not os.getenv("FIRECRAWL_API_KEY"):
        os.environ["FIRECRAWL_API_KEY"] = "fc-05935e879f594170b09e54181f4dd5f0"
    asyncio.run(main())