# Enhanced Competitive Pricing Agent - Knowledge Base Guide

## Overview
The competitive pricing agent has been enhanced with detailed logging, confidence scoring, and a knowledge base system that learns from user corrections.

## New Features

### 1. Detailed Scraping Metrics
Every scraping operation now captures:
- **Tool Used**: Which scraping tool was used (Firecrawl, Browserbase, Exa)
- **URL Scraped**: The exact URL that was attempted
- **Confidence Scores**: 
  - Overall confidence (0-100%)
  - Price confidence (high/medium/low)
  - Stock confidence (high/medium/low)
- **Response Time**: How long the scrape took
- **Success/Failure**: With detailed error messages

### 2. Knowledge Base System
The agent now maintains a knowledge base that:
- Stores successful URL patterns for each competitor
- Learns from user corrections
- Improves confidence scoring over time
- Tracks scraping performance metrics

### 3. User Correction Learning
When users correct the agent, it:
- Records the correction in the database
- Adjusts confidence scores for future scrapes
- Learns URL patterns that work better
- Improves accuracy over time

## Database Schema

### New Tables Created

#### `pricing.scraping_metrics`
Tracks every scraping attempt with detailed metrics:
```sql
- competitor_id/name
- product_search
- tool_used
- url_attempted
- success
- confidence_score
- price_confidence
- stock_confidence
- response_time_ms
- error_message
- scraped_data (JSONB)
```

#### `pricing.knowledge_base`
Stores learned patterns and intelligence:
```sql
- kb_type (url_pattern, selector, correction, variant_mapping)
- competitor_id
- context (JSONB)
- pattern
- confidence
- usage_count
- success_count
```

#### `pricing.user_corrections`
Records all user corrections:
```sql
- product_id
- competitor_id
- correction_type (price, stock_status, url, product_name)
- original_value
- corrected_value
- user_id
- session_id
- confidence_impact
```

#### `pricing.learned_patterns`
Tracks successful patterns:
```sql
- competitor_id
- pattern_type (url_structure, price_selector, stock_indicator)
- pattern_value
- success_rate
- last_successful_use
```

## New Agent Tools

### 1. `record_user_correction`
Records when users correct the agent's findings:
```python
await agent.record_user_correction(
    product_name="Wyld Gummies",
    competitor_name="Harborside", 
    correction_type="price",
    original_value="20.00",
    corrected_value="18.00"
)
```

### 2. `view_scraping_confidence`
Shows confidence metrics for recent scrapes:
```python
await agent.view_scraping_confidence(
    product_name="Wyld",
    competitor_name="Harborside",
    days=7
)
```

### 3. `analyze_scraping_performance`
Analyzes scraping performance and suggests improvements:
```python
await agent.analyze_scraping_performance(
    competitor_name="Elemental Wellness",
    min_confidence=0.5
)
```

## Using the Enhanced Agent

### Example 1: Price Check with Confidence
```
User: Check prices for Wyld Raspberry Gummies

Agent: [Shows prices with confidence indicators]
- Harborside: $20.00 🟢 High confidence (0.85)
- Elemental: $22.00 🟡 Medium confidence (0.60)
```

### Example 2: Recording Corrections
```
User: Actually, the price at Elemental should be $21.00, not $22.00

Agent: ✅ Correction recorded! This will improve future accuracy.
```

### Example 3: Viewing Performance
```
User: Show me the scraping performance analysis

Agent: [Shows detailed metrics by competitor and tool]
```

## Implementation Files

1. **Enhanced Agent**: `/agents/competitive_pricing_agent_enhanced.py`
2. **Enhanced Scraping**: `/agents/enhanced_scraping.py`
3. **Database Migration**: `/migrations/add_scraping_knowledge_base.sql`
4. **Test Scripts**:
   - `/test_enhanced_agent_local.py`
   - `/test_enhanced_scraping.py`

## Next Steps

### To Deploy:
1. Run the database migration: `python3 run_knowledge_base_migration.py`
2. Update agent imports to use `create_enhanced_agent()`
3. Test with real scraping scenarios
4. Monitor confidence scores and adjust thresholds

### Future Enhancements:
1. **Vector Search**: When pgvector is installed, enable semantic search for similar products
2. **ML-based Pattern Learning**: Use successful scrapes to train pattern recognition
3. **Automated URL Discovery**: Learn new URL patterns from successful manual searches
4. **Confidence Decay**: Reduce confidence over time for stale patterns
5. **A/B Testing**: Test multiple scraping strategies and learn which work best

## Monitoring

Check scraping health:
```sql
-- Recent scraping success rate
SELECT 
    competitor_name,
    COUNT(*) as attempts,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes,
    AVG(confidence_score) as avg_confidence
FROM pricing.scraping_metrics
WHERE scraped_at > NOW() - INTERVAL '24 hours'
GROUP BY competitor_name;

-- Common errors
SELECT 
    competitor_name,
    error_message,
    COUNT(*) as occurrences
FROM pricing.scraping_metrics
WHERE success = false
GROUP BY competitor_name, error_message
ORDER BY occurrences DESC;
```