#!/usr/bin/env python3
"""Test searching for the specific CBD version"""

import asyncio
import aiohttp
from datetime import datetime, timezone

API_URL = "https://agent-api-xk5r.onrender.com"

async def test_cbd_search():
    """Test searching for CBD version specifically"""
    
    async with aiohttp.ClientSession() as session:
        print("🔍 Testing CBD version search\n")
        
        # Search for the CBD version
        payload = {
            "message": "check prices for Wyld Strawberry 20:1 CBD Hybrid Gummies across all competitors",
            "user_id": "test_user",
            "session_id": f"test_cbd_{int(datetime.now(timezone.utc).timestamp())}",
            "stream": False
        }
        
        print("Searching for: Wyld Strawberry 20:1 CBD Hybrid Gummies\n")
        
        try:
            async with session.post(
                f"{API_URL}/v1/agents/competitive_pricing/runs",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status == 200:
                    response = await resp.json()
                    print("Response:")
                    print("="*80)
                    print(response)
                    print("="*80)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_cbd_search())