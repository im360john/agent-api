#!/usr/bin/env python3
"""
Test crawling with the new 800 page limit and validation
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

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    """Run the knowledge base update with proper database"""
    
    # Ensure we're using the correct database
    db_url = "postgresql+psycopg://rag_user:qGufXd7ddboX07VgmEqess0spXiXcmyu@dpg-d0poargdl3ps73b0c630-a.oregon-postgres.render.com:5432/agno"
    os.environ["DATABASE_URL"] = db_url
    
    print(f"Using database: agno")
    print(f"Starting crawl with 800 page limit...")
    print("Early validation enabled - will verify first batch before continuing\n")
    
    # Create agent
    agent = get_slack_treez_agent(
        model_id="gpt-4o-mini",
        debug_mode=True
    )
    
    # Create bot
    slack_bot = SlackTreezBot(agent=agent)
    
    # Run update
    results = await slack_bot.update_knowledge_base(
        urls=["https://support.treez.io/en/"]
    )
    
    print("\n=== FINAL RESULTS ===")
    print(f"✅ Documents added: {results['updated']}")
    print(f"ℹ️  Documents skipped (unchanged): {results['skipped']}")
    print(f"🔄 Documents updated (content changed): {results['content_updated']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"📄 Total URLs processed: {len(results['crawled_urls'])}")
    
    return results

if __name__ == "__main__":
    if not os.getenv("FIRECRAWL_API_KEY"):
        print("❌ Error: FIRECRAWL_API_KEY is required")
        print("Please set: export FIRECRAWL_API_KEY='your-api-key'")
        sys.exit(1)
    
    # Run
    asyncio.run(main())