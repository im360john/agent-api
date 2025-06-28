# Competitive Pricing Agent - Implementation TODO

## Phase 1: Smart History Lookup (Priority 1)

### Tasks:
1. **Enhance check_prices method**
   - [ ] Add freshness check before scraping
   - [ ] Return mixed results (cached + fresh)
   - [ ] Add age indicators to output

2. **Create analyze_price_freshness tool**
   - [ ] Show last scan time per product/competitor
   - [ ] Categorize: Fresh (<12h), Stale (12-24h), Old (>24h)
   - [ ] Suggest which combinations need refresh

3. **Database optimizations**
   - [ ] Add index: idx_price_history_lookup
   - [ ] Create materialized view: latest_prices
   - [ ] Add refresh procedure for mat view

4. **Update agent instructions**
   - [ ] Add freshness awareness to prompts
   - [ ] Explain cache behavior to users

## Phase 2: Batch Processing (Priority 2)

### Tasks:
1. **Database setup**
   - [ ] Create batch_jobs table
   - [ ] Create batch_job_items table
   - [ ] Add job status enum type

2. **Implement batch tools**
   - [ ] create_batch_job (with size confirmation)
   - [ ] check_batch_status
   - [ ] get_batch_results
   - [ ] list_batch_jobs

3. **Background processing**
   - [ ] Add job queue table or Redis
   - [ ] Create worker process
   - [ ] Implement progress tracking

4. **Results handling**
   - [ ] Generate CSV exports
   - [ ] Create summary reports
   - [ ] Store results location

## Quick Wins (Can do immediately):
- Add hours_old to price output format
- Show cached vs fresh indicator
- Add "force_refresh" parameter explanation
- Implement partial competitor list in check_prices

## Testing Requirements:
- Test with 10+ products × 5+ competitors
- Verify freshness logic works correctly
- Ensure batch jobs don't block agent
- Test result retrieval after completion