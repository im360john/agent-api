#!/usr/bin/env python3
"""Test the new freshness-aware pricing features"""

import asyncio
import aiohttp
from datetime import datetime, timezone

API_URL = "https://agent-api-xk5r.onrender.com"

async def test_freshness_features():
    """Test the new freshness analysis and smart caching"""
    
    async with aiohttp.ClientSession() as session:
        
        print("🔍 Testing Competitive Pricing Agent - Freshness Features\n")
        
        # Test 1: Analyze freshness of existing data
        print("1️⃣ Analyzing price data freshness...")
        
        payload = {
            "message": "analyze the freshness of price data for Wyld products",
            "user_id": "test_user",
            "session_id": "test_freshness_" + str(int(datetime.now(timezone.utc).timestamp())),
            "agent_id": "competitive_pricing"
        }
        
        async with session.post(f"{API_URL}/v1/chat", json=payload) as resp:
            result = await resp.json()
            print(f"Response: {result.get('content', 'No content')}\n")
        
        # Test 2: Check prices with smart caching
        print("2️⃣ Checking prices with smart caching (no force_refresh)...")
        
        payload["message"] = "check prices for Wyld Strawberry Gummies"
        payload["session_id"] = "test_smart_cache_" + str(int(datetime.now(timezone.utc).timestamp()))
        
        async with session.post(f"{API_URL}/v1/chat", json=payload) as resp:
            result = await resp.json()
            print(f"Response: {result.get('content', 'No content')}\n")
        
        # Test 3: Force refresh to bypass cache
        print("3️⃣ Force refreshing all prices...")
        
        payload["message"] = "check prices for Wyld Strawberry Gummies with force_refresh=True"
        payload["session_id"] = "test_force_refresh_" + str(int(datetime.now(timezone.utc).timestamp()))
        
        async with session.post(f"{API_URL}/v1/chat", json=payload) as resp:
            result = await resp.json()
            print(f"Response: {result.get('content', 'No content')}\n")
        
        print("✅ Freshness feature tests complete!")

if __name__ == "__main__":
    asyncio.run(test_freshness_features())