#!/usr/bin/env python3
"""Test the updated search functionality with improved Google search and browserbase fallback"""

import asyncio
from agents.competitive_pricing_agent import CompetitorPricingTools

# Use remote database
db_url = "postgresql://rag_user:qGufXd7ddboX07VgmEqess0spXiXcmyu@dpg-d0poargdl3ps73b0c630-a.oregon-postgres.render.com:5432/agno"

async def test_search():
    tools = CompetitorPricingTools(db_url=db_url)
    
    print("=== Testing Updated Search Functionality ===\n")
    
    # Test 1: Search for Wyld Strawberry CBD Gummies at Harborside
    print("Test 1: Searching for Wyld Strawberry CBD Gummies at Harborside")
    print("-" * 60)
    
    urls = await tools.search_product_urls(
        product_name="Strawberry CBD Gummies",
        brand="Wyld",
        competitor_url="https://shopharborside.com/san-jose/"
    )
    
    print(f"\nGoogle Search Results: {len(urls)} URLs found")
    for url in urls:
        print(f"  - {url}")
    
    # Test 2: Force browserbase fallback by using a tricky search
    print("\n\nTest 2: Testing Browserbase fallback")
    print("-" * 60)
    
    # Simulate what happens in _scrape_competitor_price
    print("Simulating no Google results scenario...")
    urls = []  # Simulate empty Google results
    
    if not urls:
        print("Google returned 0 results, trying Browserbase fallback...")
        urls = await tools._browserbase_search_fallback(
            competitor_url="https://shopharborside.com/san-jose/",
            brand="Wyld",
            product_name="Strawberry Gummies"
        )
    
    print(f"\nBrowserbase Results: {len(urls)} URLs found")
    for url in urls:
        print(f"  - {url}")
    
    # Test 3: Test match scoring
    print("\n\nTest 3: Testing Match Scoring")
    print("-" * 60)
    
    test_cases = [
        ("Wyld Strawberry Gummies", "Wyld Strawberry 1:1 THC:CBD Gummies"),
        ("Wyld Strawberry Gummies", "Wyld Blackberry Gummies"),
        ("Wyld Strawberry Gummies", "Kiva Strawberry Gummies"),
        ("Wyld Strawberry Gummies", "Wyld Strawberry CBD Gummies 20ct"),
    ]
    
    for search, found in test_cases:
        score = tools._calculate_match_score(search, found)
        status = "✓ MATCH" if score >= 0.5 else "✗ NO MATCH"
        print(f"{status} (score: {score:.2f})")
        print(f"  Search: '{search}'")
        print(f"  Found:  '{found}'")
        print()

if __name__ == "__main__":
    asyncio.run(test_search())