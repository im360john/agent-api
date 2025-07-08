#!/usr/bin/env python3
"""Test searching for Wyld Strawberry products specifically"""

import asyncio
import aiohttp

async def search_strawberry():
    headers = {
        "X-API-KEY": "7eb754e913754229bd81b68109a9e5139342c334",
        "Content-Type": "application/json"
    }
    
    # Search variations for strawberry
    searches = [
        ('site:shopharborside.com/san-jose Wyld Strawberry', 'San Jose'),
        ('site:shopharborside.com/oakland Wyld Strawberry', 'Oakland'), 
        ('site:shopharborside.com Wyld Strawberry gummies', 'All Harborside'),
        ('site:elementalwellnesscenter.com Wyld Strawberry', 'Elemental'),
        ('site:airfieldsupply.com Wyld Strawberry', 'Airfield'),
    ]
    
    for search_query, location in searches:
        print(f"\n{location}: {search_query}")
        print("-" * 60)
        
        payload = {
            "q": search_query,
            "num": 5
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
                        url = result.get('link', '')
                        title = result.get('title', '')
                        if 'strawberry' in url.lower() or 'strawberry' in title.lower():
                            print(f"  ✓ {title[:60]}...")
                            print(f"    {url[:80]}...")
                        else:
                            print(f"  - {title[:60]}...")
                else:
                    print(f"Error: {response.status}")

if __name__ == "__main__":
    asyncio.run(search_strawberry())