#!/usr/bin/env python3
"""
Test with a smaller crawl limit to verify validation works
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.slack_treez_agent import get_slack_treez_agent, SlackTreezBot
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def main():
    # Set environment
    os.environ["DATABASE_URL"] = "postgresql+psycopg://rag_user:qGufXd7ddboX07VgmEqess0spXiXcmyu@dpg-d0poargdl3ps73b0c630-a.oregon-postgres.render.com:5432/agno"
    os.environ["FIRECRAWL_API_KEY"] = "fc-05935e879f594170b09e54181f4dd5f0"
    
    print("Testing knowledge base update with validation...")
    print("Database: agno")
    print("Crawl limit: 800 pages")
    print("\nThe system will:")
    print("1. Start crawling support.treez.io")
    print("2. Verify the first batch uploads successfully")
    print("3. Show progress every 50 pages")
    print("4. Skip unchanged documents to save API credits")
    print("\nStarting...\n")
    
    agent = get_slack_treez_agent(model_id="gpt-4o-mini", debug_mode=True)
    bot = SlackTreezBot(agent=agent)
    
    try:
        results = await bot.update_knowledge_base(urls=["https://support.treez.io/en/"])
        
        print("\n" + "="*60)
        print("CRAWL COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"✅ New documents added: {results['updated']}")
        print(f"⏭️  Documents skipped (unchanged): {results['skipped']}")
        print(f"🔄 Documents updated (content changed): {results['content_updated']}") 
        print(f"❌ Failed documents: {results['failed']}")
        print(f"📊 Total URLs processed: {len(results['crawled_urls'])}")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return

if __name__ == "__main__":
    asyncio.run(main())