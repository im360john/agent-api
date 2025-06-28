#!/usr/bin/env python3
"""Final test for Wyld Strawberry Gummies search"""

import asyncio
import aiohttp
from datetime import datetime, timezone
import json

API_URL = "https://agent-api-xk5r.onrender.com"

async def test_wyld_search():
    """Test the exact message requested by the user"""
    
    async with aiohttp.ClientSession() as session:
        print("🔍 Testing Competitive Pricing Agent\n")
        print(f"API URL: {API_URL}\n")
        
        # The exact message requested
        payload = {
            "message": "ok search for wyld strawberry gummies across all competitors",
            "user_id": "test_user",
            "session_id": f"test_wyld_{int(datetime.now(timezone.utc).timestamp())}",
            "stream": False  # Important: disable streaming for JSON response
        }
        
        print("📤 Sending: 'ok search for wyld strawberry gummies across all competitors'\n")
        
        try:
            async with session.post(
                f"{API_URL}/v1/agents/competitive_pricing/runs",
                json=payload
            ) as resp:
                print(f"Status: {resp.status}")
                
                if resp.status == 200:
                    response = await resp.json()
                    
                    print("\n✅ Response received successfully!\n")
                    print("=" * 80)
                    print(response)
                    print("=" * 80)
                    
                    # Analyze the response
                    if "database error" in response.lower():
                        print("\n⚠️ Database error detected - production DB needs schema updates")
                    elif "competitive pricing report" in response.lower():
                        print("\n✅ Pricing report generated successfully!")
                    elif "product not found" in response.lower():
                        print("\n⚠️ Product not found - may need to track first")
                    
                else:
                    error = await resp.text()
                    print(f"\n❌ Error: {error}")
                    
        except Exception as e:
            print(f"\n❌ Request failed: {e}")

if __name__ == "__main__":
    print("🚀 Starting Wyld Strawberry Gummies search test...\n")
    asyncio.run(test_wyld_search())
    print("\n✅ Test complete!")