#!/usr/bin/env python3
"""Comprehensive test of the competitive pricing agent with SSE support"""

import asyncio
import aiohttp
from datetime import datetime, timezone
import json

API_URL = "https://agent-api-xk5r.onrender.com"

async def read_sse_response(response):
    """Read Server-Sent Events response and extract content"""
    full_content = []
    all_events = []
    
    async for line in response.content:
        line = line.decode('utf-8')
        
        # Debug: collect all lines
        if line.strip():
            all_events.append(line.strip())
        
        if line.startswith('data: '):
            data = line[6:].strip()  # Remove 'data: ' prefix
            
            if data == '[DONE]':
                break
            
            try:
                # Parse the JSON data
                event_data = json.loads(data)
                
                # Extract content from different possible structures
                if isinstance(event_data, dict):
                    if 'content' in event_data:
                        full_content.append(event_data['content'])
                    elif 'chunk' in event_data and 'content' in event_data['chunk']:
                        full_content.append(event_data['chunk']['content'])
                    elif 'response' in event_data:
                        if isinstance(event_data['response'], str):
                            full_content.append(event_data['response'])
                        elif isinstance(event_data['response'], dict) and 'content' in event_data['response']:
                            full_content.append(event_data['response']['content'])
                    elif 'message' in event_data:
                        full_content.append(event_data['message'])
                        
            except json.JSONDecodeError as e:
                # Debug: show what failed to parse
                print(f"Failed to parse: {data[:100]}...")
                pass
    
    # If no content found, show debug info
    if not full_content and all_events:
        print("\nDebug - Raw events received:")
        for event in all_events[:5]:
            print(f"  {event[:100]}...")
        if len(all_events) > 5:
            print(f"  ... and {len(all_events) - 5} more events")
    
    return ''.join(full_content)

async def test_wyld_search():
    """Test searching for Wyld Strawberry Gummies across all competitors"""
    
    async with aiohttp.ClientSession() as session:
        print("🔍 Testing Competitive Pricing Agent - Live Deployment\n")
        print(f"API URL: {API_URL}\n")
        
        # Create a unique session ID
        session_id = f"test_wyld_{int(datetime.now(timezone.utc).timestamp())}"
        
        # Test the exact message requested
        print("📤 Sending: 'ok search for wyld strawberry gummies across all competitors'\n")
        
        payload = {
            "message": "ok search for wyld strawberry gummies across all competitors",
            "user_id": "test_user",
            "session_id": session_id
        }
        
        try:
            async with session.post(
                f"{API_URL}/v1/agents/competitive_pricing/runs", 
                json=payload,
                headers={'Accept': 'text/event-stream'}
            ) as resp:
                if resp.status == 200:
                    content = await read_sse_response(resp)
                    
                    print("✅ Response received successfully!\n")
                    print("=" * 80)
                    print(content)
                    print("=" * 80)
                    
                    # Check if the response contains expected elements
                    if "Competitive Pricing Report" in content:
                        print("\n✅ Pricing report generated successfully!")
                    elif "Product not found" in content:
                        print("\n⚠️ Product not found - may need to track first")
                    elif "Error" in content:
                        print("\n❌ Error in response")
                    
                else:
                    print(f"❌ HTTP Error: {resp.status}")
                    text = await resp.text()
                    print(f"Response: {text}")
                    
        except Exception as e:
            print(f"❌ Request failed: {e}")
        
        # Additional test: List products to see what's tracked
        print("\n\n📋 Checking tracked products...")
        
        payload["message"] = "list all tracked products"
        payload["session_id"] = f"test_list_{int(datetime.now(timezone.utc).timestamp())}"
        
        try:
            async with session.post(
                f"{API_URL}/v1/agents/competitive_pricing/runs",
                json=payload,
                headers={'Accept': 'text/event-stream'}
            ) as resp:
                if resp.status == 200:
                    content = await read_sse_response(resp)
                    print("\nTracked products:")
                    print(content[:500] + "..." if len(content) > 500 else content)
                    
        except Exception as e:
            print(f"❌ List products failed: {e}")
        
        # Test freshness analysis
        print("\n\n📊 Testing freshness analysis...")
        
        payload["message"] = "analyze price freshness for wyld products"
        payload["session_id"] = f"test_fresh_{int(datetime.now(timezone.utc).timestamp())}"
        
        try:
            async with session.post(
                f"{API_URL}/v1/agents/competitive_pricing/runs",
                json=payload,
                headers={'Accept': 'text/event-stream'}
            ) as resp:
                if resp.status == 200:
                    content = await read_sse_response(resp)
                    print("\nFreshness analysis:")
                    print(content[:500] + "..." if len(content) > 500 else content)
                    
        except Exception as e:
            print(f"❌ Freshness analysis failed: {e}")

if __name__ == "__main__":
    print("🚀 Starting comprehensive test with SSE support...\n")
    asyncio.run(test_wyld_search())
    print("\n✅ Test complete!")