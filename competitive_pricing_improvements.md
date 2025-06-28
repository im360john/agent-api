# Competitive Pricing Agent - Scalability & Intelligence Improvements

## Overview
Enhance the competitive pricing agent to handle large-scale operations (20+ competitors, 100+ products) and implement intelligent price history lookups to reduce redundant scraping.

## 1. Batch Processing System

### Problem
- Current synchronous approach times out for large operations (e.g., 20 competitors × 100 products = 2,000 checks)
- No way to track progress or retrieve results later

### Solution: Async Batch Jobs

#### New Tools Required:
1. **`create_batch_job`**
   - Parameters: products[], competitors[], job_name
   - Prompts confirmation for operations >50 checks
   - Returns: job_id, estimated_time

2. **`check_batch_status`**
   - Parameters: job_id
   - Returns: status, progress%, eta

3. **`get_batch_results`**
   - Parameters: job_id, format (summary/detailed/csv)
   - Returns: results or download link

4. **`list_batch_jobs`**
   - Returns: recent jobs with status

#### Database Schema:
```sql
-- Batch jobs tracking
CREATE TABLE pricing.batch_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',
    total_checks INTEGER,
    completed_checks INTEGER DEFAULT 0,
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    results_url TEXT,
    error_message TEXT
);

-- Individual job items
CREATE TABLE pricing.batch_job_items (
    id SERIAL PRIMARY KEY,
    batch_job_id UUID REFERENCES pricing.batch_jobs(id),
    product_id INTEGER REFERENCES pricing.products(id),
    competitor_id INTEGER REFERENCES pricing.competitors(id),
    status VARCHAR(50) DEFAULT 'pending',
    processed_at TIMESTAMP WITH TIME ZONE
);
```

## 2. Intelligent Price History

### Problem
- Redundant scraping when recent data exists
- No awareness of data freshness

### Solution: Smart Cache Utilization

#### Enhanced Logic:
- **Fresh** (<12h): Use cached data
- **Stale** (12-24h): Suggest refresh
- **Old** (>24h): Auto refresh

#### New Features:
1. **`analyze_price_freshness`** tool
   - Shows last scan times per product/competitor
   - Suggests which need updates

2. **Smart check_prices** enhancement
   - Check history first
   - Return mixed results with age indicators
   - Prompt for partial updates

#### Database Optimizations:
```sql
-- Speed up history lookups
CREATE INDEX idx_price_history_lookup 
ON pricing.price_history(product_id, competitor_id, scraped_at DESC);

-- Quick freshness checks
CREATE MATERIALIZED VIEW pricing.latest_prices AS
SELECT DISTINCT ON (product_id, competitor_id)
    product_id, competitor_id, price, scraped_at,
    EXTRACT(EPOCH FROM (NOW() - scraped_at))/3600 as hours_old
FROM pricing.price_history
ORDER BY product_id, competitor_id, scraped_at DESC;
```

## 3. Implementation Plan

### Phase 1: Smart History Lookup
1. Add freshness analysis to check_prices
2. Create analyze_price_freshness tool
3. Add materialized view for performance
4. Update agent prompts for smart suggestions

### Phase 2: Basic Batch Jobs
1. Create batch job tables
2. Implement create_batch_job tool
3. Add background worker for processing
4. Implement status checking and results retrieval

### Phase 3: Enhanced Features
1. Progressive loading (return cached first, update async)
2. Smart batching by competitor
3. Rate limiting per site

### Phase 4: Advanced Analytics
1. Price change subscriptions
2. Trend analysis tools
3. Best price alerts

## User Experience Flow

### Large Operation Example:
```
User: "Check prices for all 100 products at all 20 competitors"
Agent: "This will check 2,000 price points (~45 min). Recent data exists for 600. Check only outdated prices?"
User: "Yes, check outdated only"
Agent: "Created batch job #abc123 for 1,400 checks. Use 'check batch status abc123' to monitor."
```

### Smart Lookup Example:
```
User: "Check Wyld Strawberry Gummies prices"
Agent: "I have recent prices:
- Harborside: $20 (3 hours ago) ✅
- Elemental: $18 (18 hours ago) ⚠️
- Airfield: No data ❌
Update stale/missing data only? (2 checks, ~30 seconds)"
```

## Success Metrics
- Handle 1000+ price checks without timeout
- Reduce redundant scraping by 60%
- Improve response time for cached data to <1 second
- Enable scheduling and automation

## Technical Requirements
- Background job queue (Celery/RQ)
- Redis for job status
- S3/blob storage for large results
- WebSocket for real-time updates (optional)