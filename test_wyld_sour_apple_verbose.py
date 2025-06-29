#!/usr/bin/env python3
"""Verbose test for Wyld Sour Apple Sativa across all competitors"""

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
        logging.FileHandler('wyld_sour_apple_test.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

API_URL = "https://agent-api-xk5r.onrender.com"

async def test_wyld_sour_apple():
    """Test Wyld Sour Apple Sativa with comprehensive logging"""
    
    logger.info("🚀 Starting Wyld Sour Apple Sativa comprehensive test")
    logger.info(f"API URL: {API_URL}")
    logger.info(f"Test started at: {datetime.now(timezone.utc)}")
    
    async with aiohttp.ClientSession() as session:
        
        # First, check what competitors are configured
        logger.info("\n" + "="*80)
        logger.info("STEP 1: Checking configured competitors")
        logger.info("="*80)
        
        payload = {
            "message": "list all competitors",
            "user_id": "test_user",
            "session_id": f"competitors_{int(datetime.now(timezone.utc).timestamp())}",
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
                    logger.info("✅ Competitors list retrieved:")
                    logger.info(response)
                else:
                    logger.error(f"❌ Failed to get competitors: {resp.status}")
                    logger.error(await resp.text())
        except Exception as e:
            logger.error(f"❌ Error getting competitors: {e}")
        
        # Now run the main test
        logger.info("\n" + "="*80)
        logger.info("STEP 2: Running Wyld Sour Apple Sativa price check")
        logger.info("="*80)
        
        payload = {
            "message": "check prices for Wyld Sour Apple Sativa gummies across all competitors with verbose logging",
            "user_id": "test_user",
            "session_id": f"sour_apple_{int(datetime.now(timezone.utc).timestamp())}",
            "stream": False
        }
        
        logger.info(f"📤 Sending request: {payload['message']}")
        
        try:
            start_time = datetime.now()
            async with session.post(
                f"{API_URL}/v1/agents/competitive_pricing/runs",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)  # 2 minutes for comprehensive scraping
            ) as resp:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                logger.info(f"Response status: {resp.status}")
                logger.info(f"Response time: {duration:.2f} seconds")
                
                if resp.status == 200:
                    response = await resp.json()
                    logger.info("✅ Price check completed successfully!")
                    logger.info("\n" + "="*80)
                    logger.info("FULL RESPONSE:")
                    logger.info("="*80)
                    logger.info(json.dumps(response, indent=2))
                    logger.info("="*80)
                    
                    # Analyze the response for key information
                    logger.info("\n" + "="*80)
                    logger.info("RESPONSE ANALYSIS:")
                    logger.info("="*80)
                    
                    response_text = response.lower() if isinstance(response, str) else str(response).lower()
                    
                    # Check for scraping tool mentions
                    if "firecrawl" in response_text:
                        logger.info("🔧 TOOL USED: Firecrawl detected")
                    if "exa" in response_text:
                        logger.info("🔧 TOOL USED: Exa detected")
                    if "browserbase" in response_text:
                        logger.info("🔧 TOOL USED: Browserbase detected")
                    
                    # Check for URLs
                    if "http" in response_text:
                        logger.info("🌐 URLs found in response")
                        # Extract URLs with simple regex
                        import re
                        urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', str(response))
                        for url in urls:
                            logger.info(f"   - {url}")
                    
                    # Check for price information
                    if "$" in response_text:
                        logger.info("💰 Price information detected")
                    if "out of stock" in response_text:
                        logger.info("📦 Out of stock status detected")
                    if "not carried" in response_text or "not available" in response_text:
                        logger.info("❌ Product not carried status detected")
                    if "in stock" in response_text:
                        logger.info("✅ In stock status detected")
                    
                else:
                    error_text = await resp.text()
                    logger.error(f"❌ Request failed with status {resp.status}")
                    logger.error(f"Error response: {error_text}")
                    
        except Exception as e:
            logger.error(f"❌ Request failed with exception: {e}")
        
        # Additional test: Check if product is already tracked
        logger.info("\n" + "="*80)
        logger.info("STEP 3: Checking if Wyld Sour Apple products are tracked")
        logger.info("="*80)
        
        payload = {
            "message": "list all tracked products containing 'sour apple' or 'wyld'",
            "user_id": "test_user",
            "session_id": f"list_sour_{int(datetime.now(timezone.utc).timestamp())}",
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
                    logger.info("📋 Tracked products response:")
                    logger.info(response)
                else:
                    logger.error(f"❌ Failed to get tracked products: {resp.status}")
        except Exception as e:
            logger.error(f"❌ Error getting tracked products: {e}")
    
    logger.info(f"\n🏁 Test completed at: {datetime.now(timezone.utc)}")
    logger.info("📄 Full log saved to: wyld_sour_apple_test.log")

if __name__ == "__main__":
    print("🚀 Starting comprehensive Wyld Sour Apple Sativa test with verbose logging...")
    print("📄 Logging to: wyld_sour_apple_test.log")
    asyncio.run(test_wyld_sour_apple())
    print("\n✅ Test complete! Check wyld_sour_apple_test.log for detailed analysis")