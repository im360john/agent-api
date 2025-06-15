#!/usr/bin/env python3
"""Debug WebSocket crawling"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.slack_treez_agent import get_slack_treez_agent, SlackTreezBot
import logging

# Enable DEBUG logging to see everything
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# But set firecrawl to INFO to reduce noise
logging.getLogger('firecrawl').setLevel(logging.INFO)
logging.getLogger('httpx').setLevel(logging.INFO)
logging.getLogger('urllib3').setLevel(logging.INFO)

async def main():
    os.environ["DATABASE_URL"] = "postgresql+psycopg://rag_user:qGufXd7ddboX07VgmEqess0spXiXcmyu@dpg-d0poargdl3ps73b0c630-a.oregon-postgres.render.com:5432/agno"
    os.environ["FIRECRAWL_API_KEY"] = "fc-05935e879f594170b09e54181f4dd5f0"
    
    print("\n🔍 Testing WebSocket crawl with debug logging...\n")
    
    agent = get_slack_treez_agent(model_id="gpt-4o-mini", debug_mode=True)
    bot = SlackTreezBot(agent=agent)
    
    try:
        results = await bot.update_knowledge_base(urls=["https://support.treez.io/en/"])
        
        print("\n" + "="*60)
        print("Results:")
        print(f"✅ Added: {results['updated']}")
        print(f"⏭️  Skipped: {results['skipped']}")
        print(f"❌ Failed: {results['failed']}")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())