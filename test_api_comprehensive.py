#!/usr/bin/env python3
"""Comprehensive API test"""

import asyncio
import aiohttp
from datetime import datetime, timezone
import json

API_URL = "https://agent-api-xk5r.onrender.com"

async def test_api():
    """Test various API endpoints"""
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Try to get API info
        print("1️⃣ Testing API root...")
        try:
            async with session.get(f"{API_URL}/") as resp:
                print(f"Status: {resp.status}")
                if resp.status == 200:
                    text = await resp.text()
                    print(f"Response: {text[:200]}...")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test 2: Try playground endpoint
        print("\n2️⃣ Testing playground endpoint...")
        payload = {
            "message": "list all tracked products",
            "user_id": "test_user",
            "session_id": f"test_{int(datetime.now(timezone.utc).timestamp())}"
        }
        
        try:
            async with session.post(
                f"{API_URL}/v1/playground/agents/competitive_pricing/runs",
                json=payload
            ) as resp:
                print(f"Status: {resp.status}")
                print(f"Content-Type: {resp.headers.get('Content-Type')}")
                
                if resp.status == 200:
                    # Read full response with timeout
                    full_response = []
                    try:
                        async for chunk in resp.content.iter_any():
                            full_response.append(chunk.decode('utf-8', errors='ignore'))
                            if len(full_response) > 100:  # Safety limit
                                break
                    except asyncio.TimeoutError:
                        pass
                    
                    response_text = ''.join(full_response)
                    print(f"Response length: {len(response_text)}")
                    if response_text:
                        print("Response preview:")
                        print(response_text[:500])
                else:
                    error = await resp.text()
                    print(f"Error: {error}")
                    
        except Exception as e:
            print(f"Error: {e}")
        
        # Test 3: Test with stream parameter
        print("\n3️⃣ Testing with stream=false...")
        payload["stream"] = False
        
        try:
            async with session.post(
                f"{API_URL}/v1/agents/competitive_pricing/runs",
                json=payload
            ) as resp:
                print(f"Status: {resp.status}")
                print(f"Content-Type: {resp.headers.get('Content-Type')}")
                
                if resp.status == 200:
                    if 'json' in resp.headers.get('Content-Type', ''):
                        data = await resp.json()
                        print(f"JSON Response: {json.dumps(data, indent=2)[:500]}...")
                    else:
                        text = await resp.text()
                        print(f"Text Response: {text[:500]}...")
                        
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_api())