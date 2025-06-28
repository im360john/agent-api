#!/usr/bin/env python3
"""Test to see raw response from the API"""

import asyncio
import aiohttp
from datetime import datetime, timezone

API_URL = "https://agent-api-xk5r.onrender.com"

async def test_raw():
    """Test and print raw response"""
    
    async with aiohttp.ClientSession() as session:
        print("Testing raw response...\n")
        
        payload = {
            "message": "ok search for wyld strawberry gummies across all competitors",
            "user_id": "test_user", 
            "session_id": f"test_{int(datetime.now(timezone.utc).timestamp())}"
        }
        
        try:
            async with session.post(
                f"{API_URL}/v1/agents/competitive_pricing/runs",
                json=payload
            ) as resp:
                print(f"Status: {resp.status}")
                print(f"Content-Type: {resp.headers.get('Content-Type')}")
                print(f"Headers: {dict(resp.headers)}\n")
                
                # Read first 1000 characters of response
                chunk = await resp.content.read(1000)
                text = chunk.decode('utf-8', errors='ignore')
                
                print("First 1000 chars of response:")
                print("-" * 80)
                print(text)
                print("-" * 80)
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_raw())