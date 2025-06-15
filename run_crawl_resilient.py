#!/usr/bin/env python3
"""Run knowledge base crawl with better error handling and resume capability"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.slack_treez_agent import get_slack_treez_agent, SlackTreezBot
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Reduce noise
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

async def main():
    # Set environment
    os.environ["DATABASE_URL"] = "postgresql+psycopg://rag_user:qGufXd7ddboX07VgmEqess0spXiXcmyu@dpg-d0poargdl3ps73b0c630-a.oregon-postgres.render.com:5432/agno"
    os.environ["FIRECRAWL_API_KEY"] = "fc-05935e879f594170b09e54181f4dd5f0"
    
    print("\n🚀 Starting Treez Knowledge Base Crawl")
    print(f"Time: {datetime.now()}")
    print("This will continue running and show progress...\n")
    
    # Create agent
    agent = get_slack_treez_agent(model_id="gpt-4o-mini", debug_mode=False)
    bot = SlackTreezBot(agent=agent)
    
    # Run crawl
    results = await bot.update_knowledge_base(urls=["https://support.treez.io/en/"])
    
    print(f"\n✅ Crawl Complete!")
    print(f"Added: {results['updated']} | Skipped: {results['skipped']} | Failed: {results['failed']}")
    
    return results

if __name__ == "__main__":
    # Run in background with nohup to prevent timeout
    try:
        results = asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Crawl interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()