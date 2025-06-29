#!/usr/bin/env python3
"""Detailed scraping analysis for knowledge base assessment"""

import asyncio
import aiohttp
from datetime import datetime, timezone
import json
import logging
import sys

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('detailed_scraping_analysis.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

API_URL = "https://agent-api-xk5r.onrender.com"

async def test_detailed_scraping():
    """Test to capture detailed scraping information"""
    
    logger.info("🔍 Starting detailed scraping analysis")
    
    async with aiohttp.ClientSession() as session:
        
        # Test 1: Force a new product that requires scraping
        logger.info("\n" + "="*80)
        logger.info("TEST 1: Force scraping by tracking a new product")
        logger.info("="*80)
        
        payload = {
            "message": "track product: Wyld Elderberry Gummies, brand: Wyld, category: edibles",
            "user_id": "test_user",
            "session_id": f"track_new_{int(datetime.now(timezone.utc).timestamp())}",
            "stream": False
        }
        
        logger.info(f"📤 Tracking new product: {payload['message']}")
        
        try:
            async with session.post(
                f"{API_URL}/v1/agents/competitive_pricing/runs",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                if resp.status == 200:
                    response = await resp.json()
                    logger.info("✅ Product tracking response:")
                    logger.info(json.dumps(response, indent=2))
                else:
                    logger.error(f"❌ Failed: {resp.status}")
                    logger.error(await resp.text())
        except Exception as e:
            logger.error(f"❌ Error: {e}")
        
        # Test 2: Check prices for the newly tracked product
        logger.info("\n" + "="*80)
        logger.info("TEST 2: Check prices for newly tracked product")
        logger.info("="*80)
        
        payload = {
            "message": "check prices for Wyld Elderberry Gummies across all competitors",
            "user_id": "test_user",
            "session_id": f"check_new_{int(datetime.now(timezone.utc).timestamp())}",
            "stream": False
        }
        
        logger.info(f"📤 Checking prices: {payload['message']}")
        
        try:
            async with session.post(
                f"{API_URL}/v1/agents/competitive_pricing/runs",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                if resp.status == 200:
                    response = await resp.json()
                    logger.info("✅ Price check response:")
                    logger.info(json.dumps(response, indent=2))
                    
                    # Analyze for scraping details
                    response_text = str(response).lower()
                    
                    logger.info("\n" + "-"*50)
                    logger.info("SCRAPING ANALYSIS:")
                    logger.info("-"*50)
                    
                    if "firecrawl" in response_text:
                        logger.info("🔧 TOOL: Firecrawl mentioned")
                    if "search" in response_text:
                        logger.info("🔍 SEARCH: Search operation mentioned")
                    if "scraped" in response_text or "scraping" in response_text:
                        logger.info("🕷️ SCRAPING: Scraping operation mentioned")
                    if "http" in response_text:
                        logger.info("🌐 URLs: HTTP URLs found in response")
                    
                else:
                    logger.error(f"❌ Failed: {resp.status}")
                    logger.error(await resp.text())
        except Exception as e:
            logger.error(f"❌ Error: {e}")
        
        # Test 3: Try to get search results for a specific competitor
        logger.info("\n" + "="*80)
        logger.info("TEST 3: Search for URLs at specific competitor")
        logger.info("="*80)
        
        payload = {
            "message": "search for Wyld Elderberry Gummies URLs at Harborside dispensary",
            "user_id": "test_user",
            "session_id": f"search_urls_{int(datetime.now(timezone.utc).timestamp())}",
            "stream": False
        }
        
        logger.info(f"📤 Searching URLs: {payload['message']}")
        
        try:
            async with session.post(
                f"{API_URL}/v1/agents/competitive_pricing/runs",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status == 200:
                    response = await resp.json()
                    logger.info("✅ URL search response:")
                    logger.info(json.dumps(response, indent=2))
                else:
                    logger.error(f"❌ Failed: {resp.status}")
                    logger.error(await resp.text())
        except Exception as e:
            logger.error(f"❌ Error: {e}")
        
        # Test 4: Check what products are currently tracked
        logger.info("\n" + "="*80)
        logger.info("TEST 4: List all tracked products to see database state")
        logger.info("="*80)
        
        payload = {
            "message": "list all tracked products",
            "user_id": "test_user",
            "session_id": f"list_all_{int(datetime.now(timezone.utc).timestamp())}",
            "stream": False
        }
        
        try:
            async with session.post(
                f"{API_URL}/v1/agents/competitive_pricing/runs",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    response = await resp.json()
                    logger.info("✅ All tracked products:")
                    logger.info(response)
                else:
                    logger.error(f"❌ Failed: {resp.status}")
        except Exception as e:
            logger.error(f"❌ Error: {e}")
    
    logger.info(f"\n🏁 Detailed analysis completed at: {datetime.now(timezone.utc)}")

if __name__ == "__main__":
    print("🔍 Starting detailed scraping analysis...")
    print("📄 Detailed log will be saved to: detailed_scraping_analysis.log")
    asyncio.run(test_detailed_scraping())
    print("\n✅ Analysis complete!")