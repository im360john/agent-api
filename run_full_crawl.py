#!/usr/bin/env python3
"""Run full knowledge base crawl with monitoring"""

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
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'crawl_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

# Reduce noise from other loggers
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

async def main():
    # Set environment
    os.environ["DATABASE_URL"] = "postgresql+psycopg://rag_user:qGufXd7ddboX07VgmEqess0spXiXcmyu@dpg-d0poargdl3ps73b0c630-a.oregon-postgres.render.com:5432/agno"
    os.environ["FIRECRAWL_API_KEY"] = "fc-05935e879f594170b09e54181f4dd5f0"
    
    print("\n" + "="*60)
    print("TREEZ KNOWLEDGE BASE FULL CRAWL")
    print("="*60)
    print(f"Start time: {datetime.now()}")
    print(f"Database: agno")
    print(f"Crawl limit: 800 pages")
    print(f"Cache: 48-hour Firecrawl cache enabled")
    print(f"Deduplication: Content hash checking enabled")
    print("="*60 + "\n")
    
    start_time = datetime.now()
    
    # Create agent
    agent = get_slack_treez_agent(model_id="gpt-4o-mini", debug_mode=False)
    bot = SlackTreezBot(agent=agent)
    
    try:
        # Run crawl
        results = await bot.update_knowledge_base(urls=["https://support.treez.io/en/"])
        
        # Calculate duration
        duration = datetime.now() - start_time
        
        print("\n" + "="*60)
        print("CRAWL COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"Duration: {duration}")
        print(f"✅ New documents added: {results['updated']}")
        print(f"⏭️  Documents skipped (unchanged): {results['skipped']}")
        print(f"🔄 Documents updated (content changed): {results['content_updated']}") 
        print(f"❌ Failed documents: {results['failed']}")
        print(f"📊 Total URLs processed: {len(results['crawled_urls'])}")
        print(f"📈 Effective crawl rate: {len(results['crawled_urls']) / duration.total_seconds():.2f} pages/second")
        print("="*60)
        
        # Save results
        import json
        with open('crawl_results.json', 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': duration.total_seconds(),
                'results': results
            }, f, indent=2)
        
        print("\nResults saved to crawl_results.json")
        
    except Exception as e:
        print(f"\n❌ CRAWL FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)