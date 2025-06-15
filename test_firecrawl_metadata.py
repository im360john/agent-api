#!/usr/bin/env python3
"""Test script to debug Firecrawl metadata access"""

import os
from firecrawl import FirecrawlApp

# Get API key
api_key = os.getenv("FIRECRAWL_API_KEY")
if not api_key:
    print("ERROR: FIRECRAWL_API_KEY not set")
    exit(1)

# Initialize Firecrawl
app = FirecrawlApp(api_key=api_key)

# Scrape a single page
print("Scraping single page...")
result = app.scrape_url("https://support.treez.io/en/")

print(f"\nResult type: {type(result)}")
print(f"Result attributes: {dir(result)}")

# Try to access metadata
if hasattr(result, 'metadata'):
    print(f"\nMetadata type: {type(result.metadata)}")
    print(f"Metadata is dict: {isinstance(result.metadata, dict)}")
    
    if isinstance(result.metadata, dict):
        print(f"Metadata keys: {list(result.metadata.keys())}")
        if 'sourceURL' in result.metadata:
            print(f"sourceURL: {result.metadata['sourceURL']}")
        if 'url' in result.metadata:
            print(f"url: {result.metadata['url']}")

# Check the __dict__
print(f"\nResult __dict__ keys: {list(result.__dict__.keys())}")

# Try different ways to get URL
print("\nTrying different ways to get URL:")
print(f"result.url: {getattr(result, 'url', 'NOT FOUND')}")
print(f"result.sourceURL: {getattr(result, 'sourceURL', 'NOT FOUND')}")
if hasattr(result, 'metadata') and isinstance(result.metadata, dict):
    print(f"result.metadata['sourceURL']: {result.metadata.get('sourceURL', 'NOT FOUND')}")
    print(f"result.metadata['url']: {result.metadata.get('url', 'NOT FOUND')}")