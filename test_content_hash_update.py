#!/usr/bin/env python3
"""
Test script to verify content hash checking in update_knowledge_base function

This script tests the following scenarios:
1. Initial crawl - all documents should be added
2. Second crawl without changes - documents should be skipped
3. Third crawl with force_update=True - all documents should be updated
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


async def test_content_hash_update():
    """Test the content hash checking functionality"""
    print("\n=== Testing Content Hash Update Functionality ===\n")
    
    # Use the actual database URL with the correct database name
    db_url = "postgresql+psycopg://rag_user:qGufXd7ddboX07VgmEqess0spXiXcmyu@dpg-d0poargdl3ps73b0c630-a.oregon-postgres.render.com:5432/agno"
    
    # Override the DATABASE_URL environment variable for this test
    os.environ["DATABASE_URL"] = db_url
    
    # Create the actual agent using the helper function
    agent = get_slack_treez_agent(
        model_id="gpt-4o-mini",
        debug_mode=False
    )
    
    # Create SlackTreezBot instance
    slack_bot = SlackTreezBot(agent=agent)
    
    # Test URLs (using a small subset for testing)
    test_urls = ["https://support.treez.io/en/"]
    
    print("Test 1: Initial crawl - expecting all documents to be added")
    print("-" * 60)
    results1 = await slack_bot.update_knowledge_base(urls=test_urls)
    print(f"Results from first crawl:")
    print(f"  - Updated: {results1['updated']}")
    print(f"  - Skipped: {results1['skipped']}")
    print(f"  - Content Updated: {results1['content_updated']}")
    print(f"  - Failed: {results1['failed']}")
    print(f"  - Total URLs crawled: {len(results1['crawled_urls'])}")
    
    print("\nTest 2: Second crawl without changes - expecting documents to be skipped")
    print("-" * 60)
    results2 = await slack_bot.update_knowledge_base(urls=test_urls)
    print(f"Results from second crawl:")
    print(f"  - Updated: {results2['updated']}")
    print(f"  - Skipped: {results2['skipped']}")
    print(f"  - Content Updated: {results2['content_updated']}")
    print(f"  - Failed: {results2['failed']}")
    print(f"  - Total URLs crawled: {len(results2['crawled_urls'])}")
    
    print("\nTest 3: Third crawl with force_update=True - expecting all documents to be updated")
    print("-" * 60)
    results3 = await slack_bot.update_knowledge_base(urls=test_urls, force_update=True)
    print(f"Results from third crawl with force_update:")
    print(f"  - Updated: {results3['updated']}")
    print(f"  - Skipped: {results3['skipped']}")
    print(f"  - Content Updated: {results3['content_updated']}")
    print(f"  - Failed: {results3['failed']}")
    print(f"  - Total URLs crawled: {len(results3['crawled_urls'])}")
    
    print("\n=== Test Summary ===")
    print(f"✓ First crawl added {results1['updated']} documents")
    print(f"✓ Second crawl skipped {results2['skipped']} unchanged documents")
    print(f"✓ Third crawl with force_update updated {results3['updated']} documents")
    
    # Verify expectations
    if results1['updated'] > 0 and results2['skipped'] > 0 and results3['updated'] > 0:
        print("\n✅ All tests passed! Content hash checking is working correctly.")
    else:
        print("\n❌ Tests failed. Please check the implementation.")


if __name__ == "__main__":
    # Check for required environment variables
    if not os.getenv("FIRECRAWL_API_KEY"):
        print("Error: FIRECRAWL_API_KEY environment variable is required")
        print("Please set it in your .env file or environment")
        sys.exit(1)
    
    # Run the test
    asyncio.run(test_content_hash_update())