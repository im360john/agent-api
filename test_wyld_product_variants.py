#!/usr/bin/env python3
"""Test to understand Wyld product variant handling"""

import asyncio
import aiohttp
from datetime import datetime, timezone

API_URL = "https://agent-api-xk5r.onrender.com"

async def test_wyld_variants():
    """Quick test to see what's tracked"""
    
    async with aiohttp.ClientSession() as session:
        print("🔍 Checking Wyld product variants\n")
        
        # Just list products
        payload = {
            "message": "list all tracked products",
            "user_id": "test_user", 
            "session_id": f"test_{int(datetime.now(timezone.utc).timestamp())}",
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
                    print("Products tracked:")
                    print(response[:1000])  # First 1000 chars
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_wyld_variants())