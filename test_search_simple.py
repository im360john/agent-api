#!/usr/bin/env python3
"""Simple test of search functionality"""

import asyncio
import aiohttp
import httpx

# Test the Google search modification
async def test_google_search():
    print("=== Testing Google Search (without quotes) ===\n")
    
    # Google search without quotes
    search_query = 'site:https://shopharborside.com/san-jose/ Wyld Strawberry CBD Gummies'
    print(f"Search query: {search_query}")
    
    headers = {
        "X-API-KEY": "7eb754e913754229bd81b68109a9e5139342c334",
        "Content-Type": "application/json"
    }
    
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
                print(f"\nFound {len(results)} results:")
                for i, result in enumerate(results[:3]):
                    print(f"\n{i+1}. {result.get('title', 'No title')}")
                    print(f"   URL: {result.get('link', '')[:80]}...")
            else:
                print(f"Error: {response.status}")

# Test match scoring
def test_match_scoring():
    print("\n\n=== Testing Match Scoring Logic ===\n")
    
    def calculate_match_score(search_terms: str, found_text: str) -> float:
        search_words = set(search_terms.lower().split())
        found_words = set(found_text.lower().split())
        
        if not search_words:
            return 0.0
        
        matches = search_words.intersection(found_words)
        base_score = len(matches) / len(search_words)
        
        if search_terms.lower() in found_text.lower():
            base_score = min(1.0, base_score + 0.3)
        
        if len(found_words) > len(search_words) * 3:
            base_score *= 0.8
        
        return base_score
    
    test_cases = [
        ("Wyld Strawberry Gummies", "Wyld Strawberry 1:1 THC:CBD Gummies"),
        ("Wyld Strawberry Gummies", "Wyld Blackberry Gummies"),
        ("Wyld Strawberry Gummies", "Kiva Strawberry Gummies"),
        ("Wyld Strawberry CBD Gummies", "Wyld Strawberry CBD Gummies 20ct"),
    ]
    
    MIN_SCORE = 0.5
    for search, found in test_cases:
        score = calculate_match_score(search, found)
        status = "✓ MATCH" if score >= MIN_SCORE else "✗ NO MATCH"
        print(f"{status} (score: {score:.2f})")
        print(f"  Search: '{search}'")
        print(f"  Found:  '{found}'")
        print()

async def main():
    await test_google_search()
    test_match_scoring()

if __name__ == "__main__":
    asyncio.run(main())