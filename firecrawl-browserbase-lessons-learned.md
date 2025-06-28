# Firecrawl and Browserbase: Lessons Learned in Product Pricing Scraping

## Overview

This document captures key lessons learned from implementing a two-tier web scraping system using Firecrawl and Browserbase for extracting cannabis product pricing information from competitor websites.

## Architecture: Two-Tier Scraping Strategy

The system implements a intelligent fallback approach:

1. **Tier 1 (Firecrawl)**: Fast, LLM-powered extraction for simple pages
2. **Tier 2 (Browserbase)**: JavaScript rendering for complex sites requiring browser automation

### Key Decision Points

```python
# From scraping_orchestrator.py
# Step 2: Try Firecrawl first (Tier 1 - Fast & Simple)
if firecrawl:
    firecrawl_data = await firecrawl.scrape_cannabis_product(found_url)
    
# Step 3: Fall back to Browserbase if Firecrawl failed (Tier 2 - Complex Sites)
if not product_data and browserbase:
    browserbase_data = await browserbase.extract_with_instructions(found_url, extraction_prompt)
```

## Firecrawl Implementation

### Key Features

1. **LLM-Powered Extraction**: Uses structured schemas with LLM to extract specific data
2. **Async Support**: Webhook-based processing for long-running scrapes
3. **Schema-First Approach**: Predefined schemas ensure consistent data extraction

### Cannabis Product Schema

```python
extraction_schema = {
    "prompt": """Extract the following information from this cannabis product page:
    - Product name (full name including brand)
    - All price tiers (regular, member, etc.)
    - THC percentage or mg
    - CBD percentage or mg  
    - Package size (e.g., 3.5g, 100mg, 10-pack)
    - Availability status (in stock, out of stock, sold out)
    - Any stock status messages (e.g., "Out of Stock", "Sold Out", "Currently Unavailable")
    - Product category (flower, edibles, vapes, etc.)
    
    IMPORTANT: If the product is out of stock, still return all available product information.
    Return structured data with these exact fields.""",
    
    "schema": {
        "type": "object",
        "properties": {
            "product_name": {"type": "string"},
            "prices": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "tier": {"type": "string"},
                        "price": {"type": "number"}
                    }
                }
            },
            "regular_price": {"type": "number"},
            "thc_content": {"type": "string"},
            "cbd_content": {"type": "string"},
            "package_size": {"type": "string"},
            "in_stock": {"type": "boolean"},
            "stock_status": {"type": "string"},
            "category": {"type": "string"}
        }
    }
}
```

### API Configuration

- **Base URL**: `https://api.firecrawl.dev/v1`
- **Endpoint**: `/scrape` with `formats: ["extract"]`
- **Timeout**: Increased to 30 seconds to prevent 502 errors
- **Wait Time**: 3000ms default for JavaScript rendering

## Browserbase Implementation

### Key Features

1. **Cloud Browser Sessions**: Remote browser automation for JavaScript-heavy sites
2. **Age Verification Handling**: Automated handling of age gates
3. **Dynamic Content Support**: Waits for selectors and handles dynamic price loading

### Age Verification Strategy

```python
# Flexible age verification handling
age_config = {
    "button_selector": "button:contains('Yes'), button:contains('21+'), button:contains('Enter')",
    "form_selectors": {
        "month": "select[name='month']",
        "day": "select[name='day']", 
        "year": "select[name='year']"
    },
    "submit_selector": "button[type='submit']"
}
```

### CSS Selector Strategy for Price Extraction

```python
extraction_prompt = """
Extract cannabis product information from this page.
Focus on finding the price using these CSS selectors:
- [class*="price"]
- [data-price]
- span:has-text("$")
- .price, .product-price

Also handle:
- Age verification popups (click "Yes", "21+", "Enter", etc.)
- Dynamic price loading (wait for prices to appear)
- Member vs regular pricing
"""
```

## Regular Expression Patterns

### Price Extraction

```python
def extract_price(self, price_text: str) -> float:
    # Remove currency symbols and extra characters
    price_text = re.sub(r'[^\d.,]', '', price_text)
    price_text = price_text.replace(',', '')
    
    try:
        return float(price_text)
    except (ValueError, AttributeError):
        return 0.0
```

**Key patterns:**
- `r'[^\d.,]'` - Remove all non-numeric characters except decimal and comma
- Handle both `$45.00` and `45,00` formats

### THC/CBD Content Extraction

```python
# Percentage patterns
thc_percent_match = re.search(r'THC[:\s]*(\d+\.?\d*)%', text, re.IGNORECASE)
cbd_percent_match = re.search(r'CBD[:\s]*(\d+\.?\d*)%', text, re.IGNORECASE)

# Milligram patterns
thc_mg_match = re.search(r'(\d+\.?\d*)\s*mg\s*THC', text, re.IGNORECASE)
thc_mg_match = re.search(r'THC[:\s]*(\d+\.?\d*)\s*mg', text, re.IGNORECASE)
```

**Handles variations:**
- "THC: 22.5%", "22.5% THC"
- "100mg THC", "THC: 100mg"
- Case-insensitive matching

### Size/Quantity Extraction

```python
patterns = [
    (r'(\d+\.?\d*)\s*(g|gram|grams)', 'g'),
    (r'(\d+\.?\d*)\s*(mg|milligram|milligrams)', 'mg'),
    (r'(\d+\.?\d*)\s*(oz|ounce|ounces)', 'oz'),
    (r'1/8\s*(oz|ounce)?', 'eighth'),
    (r'1/4\s*(oz|ounce)?', 'quarter'),
    (r'1/2\s*(oz|ounce)?', 'half'),
]
```

**Special handling:**
- Converts fractional ounces to grams (1/8 oz = 3.5g)
- Handles "10-pack" format for edibles

## URL Relevance Filtering

### Smart URL Validation Before API Calls

```python
def _is_relevant_product_url(self, url: str, search_term: str) -> bool:
    # Brand matching
    brand_words = ['wyld', 'camino', 'kiva', 'stiiizy', 'raw', 'cookies']
    if search_brands:
        if not any(brand in url_lower for brand in search_brands):
            return False
    
    # Flavor/strain matching
    flavor_words = ['strawberry', 'huckleberry', 'raspberry', ...]
    if search_flavors:
        if not any(flavor in url_lower for flavor in search_flavors):
            return False
    
    # Ratio matching (20:1, 1:1, etc.)
    search_ratio = re.search(r'\d+:\d+', search_term)
    if search_ratio and url_ratio:
        if search_ratio.group() != url_ratio.group():
            return False
```

**Key optimizations:**
- Pre-filter URLs before expensive API calls
- Match brand names exactly
- Ensure flavor specificity
- Handle CBD:THC ratios

## Error Handling & Edge Cases

### Out of Stock Products

```python
# Handle out of stock products - still need a price for the model
price = float(product_data.get('price', 0)) if product_data.get('price') else 0.01

# Special logging for out of stock
if not product_data.get('in_stock'):
    print(f"💡 Storing OUT OF STOCK product: {product_data.get('product_name')}")
```

**Lesson**: Always capture product data even when out of stock, use minimal price (0.01) to satisfy validation.

### Webhook Handling for Async Processing

```python
if webhook_url:
    payload["webhook"] = {"url": webhook_url}
    
if response.status_code == 200:
    data = response.json()
    if webhook_url and data.get("jobId"):
        return {"jobId": data["jobId"], "webhook": True}
```

**Implementation**: Store job IDs and process results asynchronously via webhook endpoint.

## Performance Optimizations

### 1. Process Only Top Search Result

```python
# ENHANCEMENT 1: Only process the top URL instead of multiple
for found_url in serper_urls[:1]:  # Only process top result
```

### 2. Efficient Search Strategy

1. Use Serper API with `site:` operator for targeted search
2. Pre-filter URLs before API calls
3. Fall back to base site browsing if no results

### 3. Concurrent Scraping

```python
# Run scrapers concurrently (limit concurrency to avoid rate limits)
tasks = []
for competitor in self.competitors:
    if competitor.get('enabled', True):
        task = self.scrape_competitor(competitor)
        tasks.append(task)

scraped_data = await asyncio.gather(*tasks)
```

## Mock Implementations

Both Firecrawl and Browserbase include mock clients for development/testing:

```python
class MockFirecrawlClient(FirecrawlClient):
    """Mock Firecrawl client for development"""
    
    async def scrape_cannabis_product(self, url: str) -> Optional[Dict[str, Any]]:
        # Return different data based on URL
        if "strawberry" in url.lower() and "wyld" in url.lower():
            return {
                "product_name": "Wyld Strawberry Gummies 100mg",
                "prices": [
                    {"tier": "Regular", "price": 24.00},
                    {"tier": "Member", "price": 21.60}
                ],
                # ... more mock data
            }
```

## Best Practices

1. **Schema-First Development**: Define extraction schemas before implementation
2. **Graceful Degradation**: Always have fallback strategies (Firecrawl → Browserbase → Manual)
3. **URL Pre-validation**: Filter URLs before making expensive API calls
4. **Comprehensive Extraction**: Capture all data even for out-of-stock products
5. **Mock Development**: Use mock clients to develop without API costs
6. **Timeout Management**: Increase timeouts for complex pages (30s+)
7. **Rate Limiting**: Implement delays between requests to avoid blocking
8. **Error Logging**: Detailed error tracking for debugging production issues

## Common Pitfalls to Avoid

1. **Don't skip out-of-stock products** - They're valuable for inventory tracking
2. **Don't assume price format** - Handle various currency formats
3. **Don't ignore member pricing** - Capture all price tiers
4. **Don't make unnecessary API calls** - Pre-filter URLs aggressively
5. **Don't hardcode selectors** - Make them configurable per site

## Future Improvements

1. **Redis Integration**: Store webhook results in Redis instead of memory
2. **Retry Logic**: Implement exponential backoff for failed requests
3. **Visual Scraping**: Use screenshot analysis for complex layouts
4. **ML-Based Extraction**: Train models on successful extractions
5. **Distributed Scraping**: Scale across multiple Browserbase sessions