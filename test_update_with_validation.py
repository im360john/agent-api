#!/usr/bin/env python3
"""
Test the knowledge base update with early validation
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.slack_treez_agent import SlackTreezBot, get_slack_treez_agent
import logging

# Set up logging to see all the validation messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def test_update_with_validation():
    """Test the knowledge base update with validation"""
    print("\n=== Testing Knowledge Base Update with Validation ===\n")
    
    # Use the actual database URL
    db_url = "postgresql+psycopg://rag_user:qGufXd7ddboX07VgmEqess0spXiXcmyu@dpg-d0poargdl3ps73b0c630-a.oregon-postgres.render.com:5432/agno"
    os.environ["DATABASE_URL"] = db_url
    
    # Create agent
    agent = get_slack_treez_agent(
        model_id="gpt-4o-mini",
        debug_mode=True  # Enable debug mode to see all logs
    )
    
    # Create SlackTreezBot instance
    slack_bot = SlackTreezBot(agent=agent)
    
    # Test with main Treez support URL
    test_urls = ["https://support.treez.io/en/"]
    
    print("Starting crawl with validation enabled...")
    print("The crawl will verify the first batch upload before continuing.")
    print("If verification fails, it will stop to avoid wasting credits.\n")
    
    results = await slack_bot.update_knowledge_base(urls=test_urls)
    
    print("\n=== Final Results ===")
    print(f"Documents added: {results['updated']}")
    print(f"Documents skipped: {results['skipped']}")
    print(f"Documents with updated content: {results['content_updated']}")
    print(f"Failed: {results['failed']}")
    print(f"Total URLs crawled: {len(results['crawled_urls'])}")
    
    if results['updated'] > 0:
        print(f"\n✅ Successfully added {results['updated']} documents to the knowledge base!")
    
    if results['skipped'] > 0:
        print(f"ℹ️  Skipped {results['skipped']} unchanged documents (saving API credits)")


if __name__ == "__main__":
    # Check for required environment variables
    if not os.getenv("FIRECRAWL_API_KEY"):
        print("Error: FIRECRAWL_API_KEY environment variable is required")
        sys.exit(1)
    
    # Run the test
    asyncio.run(test_update_with_validation())