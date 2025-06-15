#!/usr/bin/env python3
"""Simple test to check crawl response structure"""

import os
from firecrawl import FirecrawlApp, ScrapeOptions

# Get API key
api_key = os.getenv("FIRECRAWL_API_KEY", "fc-05935e879f594170b09e54181f4dd5f0")

# Initialize Firecrawl
app = FirecrawlApp(api_key=api_key)

print("Testing crawl with limit=1...")
try:
    # Crawl with limit of 1 to save credits
    result = app.crawl_url(
        "https://support.treez.io/en/", 
        limit=1,
        scrape_options=ScrapeOptions(
            formats=['markdown']
        )
    )
    
    print(f"\nCrawl result type: {type(result)}")
    print(f"Result success: {result.success if hasattr(result, 'success') else 'N/A'}")
    print(f"Result status: {result.status if hasattr(result, 'status') else 'N/A'}")
    
    if hasattr(result, 'data') and result.data:
        print(f"\nNumber of pages: {len(result.data)}")
        page = result.data[0]
        print(f"\nFirst page type: {type(page)}")
        print(f"Page has metadata: {hasattr(page, 'metadata')}")
        
        if hasattr(page, 'metadata'):
            print(f"Metadata type: {type(page.metadata)}")
            print(f"Metadata is dict: {isinstance(page.metadata, dict)}")
            
            if isinstance(page.metadata, dict):
                print(f"\nMetadata keys: {list(page.metadata.keys())[:10]}")
                print(f"sourceURL: {page.metadata.get('sourceURL', 'NOT FOUND')}")
                print(f"url: {page.metadata.get('url', 'NOT FOUND')}")
        
        # Check page.url
        print(f"\npage.url: {getattr(page, 'url', 'NOT FOUND')}")
        
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")