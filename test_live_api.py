#!/usr/bin/env python3
"""
Test script for the live competitive pricing agent API
"""

import asyncio
import aiohttp
import json
from datetime import datetime


async def test_competitive_pricing_api():
    """Test the competitive pricing agent through the live API"""
    
    base_url = "https://agent-api-xk5r.onrender.com"
    agent_id = "competitive_pricing"
    
    print(f"🧪 Testing Competitive Pricing Agent at {base_url}")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Add Harborside competitor
        print("\n📍 Test 1: Adding Harborside competitor...")
        
        payload = {
            "message": "Add competitor Harborside with URL https://shopharborside.com/san-jose/",
            "stream": False,
            "model": "gpt-4.1"
        }
        
        try:
            async with session.post(f"{base_url}/v1/agents/{agent_id}/runs", json=payload) as resp:
                if resp.status == 200:
                    result = await resp.text()
                    print(f"✅ Success: {resp.status}")
                    print(f"Response: {result[:200]}...")
                else:
                    error_text = await resp.text()
                    print(f"❌ Error {resp.status}: {error_text}")
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")
        
        # Test 2: Add more competitors
        print("\n📍 Test 2: Adding Elemental and Theraleaf competitors...")
        
        competitors = [
            ("Elemental", "https://www.getweeddelivered.com/"),
            ("Theraleaf", "https://theraleaf.ca/")
        ]
        
        for name, url in competitors:
            payload = {
                "message": f"Add competitor {name} with URL {url}",
                "stream": False,
                "model": "gpt-4.1"
            }
            
            try:
                async with session.post(f"{base_url}/v1/agents/{agent_id}/runs", json=payload) as resp:
                    if resp.status == 200:
                        print(f"✅ Added {name}")
                    else:
                        print(f"❌ Failed to add {name}: {resp.status}")
            except Exception as e:
                print(f"❌ Request failed for {name}: {str(e)}")
        
        # Test 3: Track Wyld Strawberry Gummies
        print("\n📦 Test 3: Tracking Wyld Strawberry Gummies...")
        
        payload = {
            "message": "Track product: Wyld Strawberry Gummies, category: edibles, with THC content 100mg",
            "stream": False,
            "model": "gpt-4.1"
        }
        
        try:
            async with session.post(f"{base_url}/v1/agents/{agent_id}/runs", json=payload) as resp:
                if resp.status == 200:
                    result = await resp.text()
                    print(f"✅ Product tracked successfully")
                else:
                    print(f"❌ Failed to track product: {resp.status}")
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")
        
        # Test 4: Check prices
        print("\n💰 Test 4: Checking prices for Wyld Strawberry Gummies...")
        
        payload = {
            "message": "Check prices for Wyld Strawberry Gummies across all competitors",
            "stream": False,
            "model": "gpt-4.1"
        }
        
        try:
            async with session.post(f"{base_url}/v1/agents/{agent_id}/runs", json=payload) as resp:
                if resp.status == 200:
                    result = await resp.text()
                    print(f"✅ Price check completed")
                    print("\n📊 Results:")
                    print(result)
                else:
                    error_text = await resp.text()
                    print(f"❌ Price check failed: {resp.status}")
                    print(f"Error: {error_text}")
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")
        
        # Test 5: Test the fix for add_competitor
        print("\n🔧 Test 5: Testing add_competitor fix...")
        
        payload = {
            "message": "Use the add_competitor tool to add name: TestShop, urls: ['https://testshop.com']",
            "stream": False,
            "model": "gpt-4.1"
        }
        
        try:
            async with session.post(f"{base_url}/v1/agents/{agent_id}/runs", json=payload) as resp:
                if resp.status == 200:
                    result = await resp.text()
                    print(f"✅ add_competitor tool call succeeded")
                    print(f"Response: {result[:200]}...")
                else:
                    error_text = await resp.text()
                    print(f"❌ Error {resp.status}: {error_text}")
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")
    
    print("\n✨ Testing complete!")


if __name__ == "__main__":
    asyncio.run(test_competitive_pricing_api())