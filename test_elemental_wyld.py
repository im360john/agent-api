#!/usr/bin/env python3
"""Test to investigate Elemental Wellness Wyld product search"""

import asyncio
import aiohttp
from datetime import datetime, timezone
import json

API_URL = "https://agent-api-xk5r.onrender.com"

async def test_elemental_wyld():
    """Test different Wyld product searches"""
    
    async with aiohttp.ClientSession() as session:
        print("🔍 Testing Elemental Wellness Wyld Product Search\n")
        
        # Test 1: General Wyld Strawberry search
        print("1️⃣ Testing general 'wyld strawberry gummies' search...")
        payload = {
            "message": "check prices for wyld strawberry gummies at Elemental Wellness",
            "user_id": "test_user",
            "session_id": f"test_general_{int(datetime.now(timezone.utc).timestamp())}",
            "stream": False
        }
        
        try:
            async with session.post(f"{API_URL}/v1/agents/competitive_pricing/runs", json=payload) as resp:
                if resp.status == 200:
                    response = await resp.json()
                    print("\nResponse:")
                    print(response)
                    print("\n" + "="*80 + "\n")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test 2: Search for CBD version specifically
        print("\n2️⃣ Testing specific CBD version search...")
        payload["message"] = "search for Wyld Strawberry CBD gummies at Elemental Wellness"
        payload["session_id"] = f"test_cbd_{int(datetime.now(timezone.utc).timestamp())}"
        
        try:
            async with session.post(f"{API_URL}/v1/agents/competitive_pricing/runs", json=payload) as resp:
                if resp.status == 200:
                    response = await resp.json()
                    print("\nResponse:")
                    print(response)
                    print("\n" + "="*80 + "\n")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test 3: Check what products are tracked
        print("\n3️⃣ Checking all tracked Wyld products...")
        payload["message"] = "list all tracked products from Wyld brand"
        payload["session_id"] = f"test_list_{int(datetime.now(timezone.utc).timestamp())}"
        
        try:
            async with session.post(f"{API_URL}/v1/agents/competitive_pricing/runs", json=payload) as resp:
                if resp.status == 200:
                    response = await resp.json()
                    print("\nTracked Wyld products:")
                    print(response)
                    print("\n" + "="*80 + "\n")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test 4: Track the CBD version
        print("\n4️⃣ Attempting to track the CBD version...")
        payload["message"] = "track product: Wyld Strawberry 20:1 CBD Hybrid Gummies, brand: Wyld, category: edibles"
        payload["session_id"] = f"test_track_{int(datetime.now(timezone.utc).timestamp())}"
        
        try:
            async with session.post(f"{API_URL}/v1/agents/competitive_pricing/runs", json=payload) as resp:
                if resp.status == 200:
                    response = await resp.json()
                    print("\nTracking response:")
                    print(response)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    print("🚀 Starting Elemental Wellness Wyld investigation...\n")
    asyncio.run(test_elemental_wyld())
    print("\n✅ Investigation complete!")