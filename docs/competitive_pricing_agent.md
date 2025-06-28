# Competitive Pricing Agent

## Overview

The Competitive Pricing Agent is an AI-powered tool for tracking and analyzing product prices across competitor e-commerce websites. It uses advanced web scraping techniques and maintains a comprehensive database of pricing history.

## Features

### Core Capabilities
- **Multi-Product Tracking**: Monitor single or multiple products simultaneously
- **Bulk Operations**: Check prices for many products across many competitors in one request
- **Historical Analysis**: Track price changes over time with detailed trends
- **Availability Tracking**: Monitor in-stock, out-of-stock, and not-carried statuses
- **Smart Caching**: 24-hour cache to reduce API calls with force refresh option
- **Member Pricing**: Track both regular and member price tiers
- **Management Functions**: Delete products/competitors, modify URLs, list all tracked items

### Technical Features
- **Two-Tier Scraping**: Firecrawl (fast) with Browserbase fallback (JavaScript sites)
- **GPT-4o Reasoning**: Intelligent analysis and insights
- **PostgreSQL Storage**: Persistent price history with optimized queries
- **Semantic Search**: Find products even with partial names

## Database Schema

### Tables
1. **pricing.competitors**
   - Stores competitor information with multiple URLs support
   - Tracks enabled status and last crawl time

2. **pricing.products**
   - Product catalog with brand, category, and variants
   - Supports metadata like THC/CBD content for cannabis products

3. **pricing.price_history**
   - Complete price tracking with timestamps
   - Stores raw scraped data for debugging
   - Tracks which scraper was used

## Usage Examples

### 1. Basic Setup
```python
# Add competitors
agent.run("""
Add these competitors:
- Harborside - https://shopharborside.com/
- Elemental - https://elementalwellnesscenter.com/
""")

# Track a product
agent.run("""
Track Wyld Strawberry Gummies (edibles category, 100mg THC)
""")
```

### 2. Check Current Prices
```python
# Simple price check
agent.run("Check prices for Wyld Strawberry Gummies")

# Force fresh data (bypass cache)
agent.run("Check prices for Wyld Strawberry Gummies with force_refresh=True")
```

### 3. Bulk Operations
```python
# Check multiple products
agent.run("""
Check prices for:
- Wyld Strawberry Gummies
- Camino Watermelon Gummies
- STIIIZY Blue Dream Pod
""")
```

### 4. Historical Analysis
```python
# Get price history
agent.run("Show me price history for Wyld Strawberry Gummies over the last 30 days")

# Analyze trends
agent.run("Analyze pricing trends for edibles category this week")
```

### 5. Management Functions
```python
# List all tracked items
agent.run("List all competitors")
agent.run("List all products")

# Modify competitor URLs
agent.run("Update Harborside URLs to https://shopharborside.com/san-jose/ and https://shopharborside.com/oakland/")

# Delete items
agent.run("Delete competitor Theraleaf")
agent.run("Delete product Wyld Huckleberry Gummies")
```

## API Keys Required

- **OpenAI**: For GPT-4o reasoning
- **Firecrawl**: Primary web scraping
- **Browserbase**: JavaScript site scraping
- **Exa**: Product discovery across web
- **Serper**: Google search integration

## Output Format

The agent provides formatted reports with:
- **Price Comparison Tables**: Side-by-side competitor pricing
- **Availability Status**: Visual indicators (✅ in stock, ⚠️ out of stock, ❌ not carried)
- **Insights**: Best price, average price, price range
- **Cache Status**: Shows if data is fresh or cached
- **Trend Analysis**: Price changes over time

## Example Output

```
## 💰 Competitive Pricing Report

### Wyld Strawberry Gummies

| Competitor | Price | Member Price | Status | Last Updated | Source |
|------------|-------|--------------|--------|--------------|--------|
| Elemental | $12.60 | — | ✅ In Stock | < 1 hour ago | 🔄 Fresh |
| Harborside | $14.00 | $12.60 | ✅ In Stock | < 1 hour ago | 🔄 Fresh |
| Theraleaf | — | — | ❌ Not Carried | < 1 hour ago | 🔄 Fresh |

**Insights:**
- 🏆 Best price: $12.60 at Elemental
- 📊 Average price: $13.30
- 📈 Price range: $12.60 - $14.00
```

## Advanced Features

### Custom Competitor Configuration
```python
# Add competitor with metadata
agent.run("""
Add competitor "NewShop" with URL https://newshop.com
and metadata: {"age_verification": true, "requires_login": false}
""")
```

### Product Variants
```python
# Track product with variants
agent.run("""
Track product:
- Name: Gummies
- Brand: Wyld
- Variants: ["Strawberry 100mg", "Huckleberry 100mg", "Raspberry 100mg"]
""")
```

### Search Terms
```python
# Add alternative search terms
agent.run("""
Track "Strawberry Gummies" by Wyld
with search terms: ["wyld strawberry", "strawberry gummies 100mg", "wyld edibles strawberry"]
""")
```

## Troubleshooting

### Common Issues

1. **"Product not found"**
   - Ensure exact brand and product name
   - Try adding search terms
   - Check if product is tracked first

2. **"No URLs found"**
   - Product may not be listed online
   - Try broader search terms
   - Check competitor URL is correct

3. **Scraping failures**
   - Site may require special handling
   - Check if Browserbase is configured
   - Some sites may block automated access

### Debug Mode
Enable debug mode to see detailed logs:
```python
agent = get_competitive_pricing_agent(debug_mode=True)
```

## Performance Tips

1. **Use Bulk Operations**: More efficient than individual checks
2. **Respect Cache**: Default 24-hour cache reduces API costs
3. **Schedule Updates**: Run price checks during off-peak hours
4. **Monitor Failures**: Check error_message in price_history table

## Future Enhancements

- Price drop alerts
- Competitor price matching rules
- Export to spreadsheet functionality
- Price prediction models
- API endpoint for external access
- Real-time monitoring with webhooks