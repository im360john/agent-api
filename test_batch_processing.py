#!/usr/bin/env python3
"""Test the batch processing functionality"""

import asyncio
import aiohttp
from datetime import datetime, timezone

API_URL = "https://agent-api-xk5r.onrender.com"

async def test_batch_processing():
    """Test batch job creation and monitoring"""
    
    async with aiohttp.ClientSession() as session:
        
        print("🔍 Testing Competitive Pricing Agent - Batch Processing\n")
        
        # Test 1: Create a small batch job
        print("1️⃣ Creating a batch job for multiple products...")
        
        payload = {
            "message": """Create a batch job to check prices for these products:
            - Wyld Strawberry Gummies
            - Wyld Raspberry Gummies  
            - Kiva Camino Gummies
            across all competitors""",
            "user_id": "test_user",
            "session_id": "test_batch_" + str(int(datetime.now(timezone.utc).timestamp())),
            "agent_id": "competitive_pricing"
        }
        
        async with session.post(f"{API_URL}/v1/chat", json=payload) as resp:
            result = await resp.json()
            print(f"Response: {result.get('content', 'No content')}\n")
            
            # Extract job ID from response if present
            content = result.get('content', '')
            if 'Job ID:' in content:
                # Parse job ID from response
                lines = content.split('\n')
                for line in lines:
                    if 'Job ID:' in line:
                        job_id = line.split('`')[1] if '`' in line else None
                        if job_id:
                            print(f"Extracted Job ID: {job_id}\n")
                            
                            # Test 2: Check job status
                            print("2️⃣ Checking batch job status...")
                            
                            payload["message"] = f"check batch status for job {job_id}"
                            payload["session_id"] = "test_status_" + str(int(datetime.now(timezone.utc).timestamp()))
                            
                            async with session.post(f"{API_URL}/v1/chat", json=payload) as resp2:
                                result2 = await resp2.json()
                                print(f"Status: {result2.get('content', 'No content')}\n")
        
        # Test 3: List recent batch jobs
        print("3️⃣ Listing recent batch jobs...")
        
        payload["message"] = "list recent batch jobs"
        payload["session_id"] = "test_list_" + str(int(datetime.now(timezone.utc).timestamp()))
        
        async with session.post(f"{API_URL}/v1/chat", json=payload) as resp:
            result = await resp.json()
            print(f"Recent jobs: {result.get('content', 'No content')}\n")
        
        # Test 4: Test large job warning
        print("4️⃣ Testing large job warning (100 products × 3 competitors)...")
        
        payload["message"] = """Create a batch job for 100 products across all competitors. 
        Products: Wyld Strawberry, Wyld Raspberry, Wyld Huckleberry, Wyld Blackberry, 
        Kiva Camino, Kiva Petra, Plus Gummies, Smokiez Gummies, Lost Farm Gummies, 
        Wana Gummies (and 90 more similar products)"""
        payload["session_id"] = "test_large_" + str(int(datetime.now(timezone.utc).timestamp()))
        
        async with session.post(f"{API_URL}/v1/chat", json=payload) as resp:
            result = await resp.json()
            print(f"Large job response: {result.get('content', 'No content')}\n")
        
        print("✅ Batch processing tests complete!")

if __name__ == "__main__":
    asyncio.run(test_batch_processing())