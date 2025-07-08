#!/usr/bin/env python3
"""Test different Google search variations"""

import asyncio
import aiohttp

async def test_search_variations():
    headers = {
        "X-API-KEY": "7eb754e913754229bd81b68109a9e5139342c334",
        "Content-Type": "application/json"
    }
    
    # Different search variations to test
    searches = [
        'site:shopharborside.com Wyld Strawberry',  # No /san-jose/ in site
        'site:shopharborside.com Wyld gummies',      # More general  
        'shopharborside.com Wyld Strawberry',        # No site: operator
        'site:shopharborside.com/san-jose Wyld',    # No trailing slash
    ]
    
    for search_query in searches:
        print(f"\nTesting: {search_query}")
        print("-" * 50)
        
        payload = {
            "q": search_query,
            "num": 3
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://google.serper.dev/search",
                json=payload,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get("organic", [])
                    print(f"Found {len(results)} results:")
                    for result in results:
                        print(f"  - {result.get('link', '')[:80]}")
                else:
                    print(f"Error: {response.status}")

if __name__ == "__main__":
    asyncio.run(test_search_variations())