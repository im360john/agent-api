-- Competitive Pricing Database Schema
-- Tables for tracking product prices across competitor websites

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS pricing;

-- Competitors table
CREATE TABLE IF NOT EXISTS pricing.competitors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    urls TEXT[] NOT NULL, -- Array of URLs for this competitor
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_crawled_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb -- Store additional info like selectors, auth requirements
);

-- Products table
CREATE TABLE IF NOT EXISTS pricing.products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    brand VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    variants JSONB DEFAULT '[]'::jsonb, -- Array of variant info (size, flavor, etc)
    search_terms TEXT[], -- Alternative names/keywords for searching
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb, -- THC/CBD content, package size, etc
    UNIQUE(brand, name) -- Prevent duplicate products
);

-- Price history table
CREATE TABLE IF NOT EXISTS pricing.price_history (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES pricing.products(id) ON DELETE CASCADE,
    competitor_id INTEGER NOT NULL REFERENCES pricing.competitors(id) ON DELETE CASCADE,
    price DECIMAL(10, 2),
    member_price DECIMAL(10, 2),
    availability_status VARCHAR(50) NOT NULL, -- 'in_stock', 'out_of_stock', 'not_carried'
    url TEXT NOT NULL,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    scraper_used VARCHAR(50), -- 'firecrawl', 'browserbase', 'manual'
    raw_data JSONB, -- Store full scraped data for debugging
    price_tiers JSONB DEFAULT '[]'::jsonb, -- Array of {tier: "name", price: 0.00}
    error_message TEXT, -- If scraping failed
    CONSTRAINT chk_availability CHECK (availability_status IN ('in_stock', 'out_of_stock', 'not_carried'))
);

-- Indexes for performance
CREATE INDEX idx_price_history_product_competitor ON pricing.price_history(product_id, competitor_id, scraped_at DESC);
CREATE INDEX idx_price_history_scraped_at ON pricing.price_history(scraped_at DESC);
CREATE INDEX idx_price_history_availability ON pricing.price_history(availability_status);
CREATE INDEX idx_products_brand ON pricing.products(brand);
CREATE INDEX idx_products_category ON pricing.products(category);
CREATE INDEX idx_competitors_enabled ON pricing.competitors(enabled);

-- Full text search indexes
CREATE INDEX idx_products_search ON pricing.products USING gin(to_tsvector('english', name || ' ' || brand));

-- Phase 1 Optimizations: Smart History Lookup

-- Optimized compound index for freshness lookups (if not exists)
CREATE INDEX IF NOT EXISTS idx_price_history_lookup 
ON pricing.price_history(product_id, competitor_id, scraped_at DESC);

-- Materialized view for quick freshness checks
CREATE MATERIALIZED VIEW IF NOT EXISTS pricing.latest_prices AS
SELECT DISTINCT ON (product_id, competitor_id)
    p.id as product_id,
    p.name as product_name,
    p.brand,
    c.id as competitor_id,
    c.name as competitor_name,
    ph.price,
    ph.member_price,
    ph.availability_status,
    ph.scraped_at,
    ph.url,
    EXTRACT(EPOCH FROM (NOW() - ph.scraped_at))/3600 as hours_old,
    CASE 
        WHEN EXTRACT(EPOCH FROM (NOW() - ph.scraped_at))/3600 < 12 THEN 'fresh'
        WHEN EXTRACT(EPOCH FROM (NOW() - ph.scraped_at))/3600 < 24 THEN 'stale'
        ELSE 'old'
    END as freshness_status
FROM pricing.price_history ph
JOIN pricing.products p ON ph.product_id = p.id
JOIN pricing.competitors c ON ph.competitor_id = c.id
WHERE p.enabled = true AND c.enabled = true
ORDER BY product_id, competitor_id, scraped_at DESC;

-- Indexes on materialized view
CREATE INDEX IF NOT EXISTS idx_latest_prices_lookup ON pricing.latest_prices(product_id, competitor_id);
CREATE INDEX IF NOT EXISTS idx_latest_prices_freshness ON pricing.latest_prices(freshness_status);
CREATE INDEX IF NOT EXISTS idx_latest_prices_hours ON pricing.latest_prices(hours_old);

-- Function to refresh materialized view
CREATE OR REPLACE FUNCTION pricing.refresh_latest_prices()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY pricing.latest_prices;
END;
$$ LANGUAGE plpgsql;

-- Auto-refresh trigger (optional - run periodically)
-- Could be called by a cron job or after batch inserts
CREATE INDEX idx_products_search_terms ON pricing.products USING gin(search_terms);

-- Functions for easy querying

-- Get latest price for a product at a competitor
CREATE OR REPLACE FUNCTION pricing.get_latest_price(
    p_product_id INTEGER,
    p_competitor_id INTEGER
) RETURNS TABLE (
    price DECIMAL(10, 2),
    member_price DECIMAL(10, 2),
    availability_status VARCHAR(50),
    scraped_at TIMESTAMP WITH TIME ZONE,
    url TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT ph.price, ph.member_price, ph.availability_status, ph.scraped_at, ph.url
    FROM pricing.price_history ph
    WHERE ph.product_id = p_product_id 
      AND ph.competitor_id = p_competitor_id
    ORDER BY ph.scraped_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Get price trend for a product
CREATE OR REPLACE FUNCTION pricing.get_price_trend(
    p_product_id INTEGER,
    p_competitor_id INTEGER,
    p_days INTEGER DEFAULT 30
) RETURNS TABLE (
    scraped_date DATE,
    avg_price DECIMAL(10, 2),
    min_price DECIMAL(10, 2),
    max_price DECIMAL(10, 2),
    availability_rate DECIMAL(5, 2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        DATE(ph.scraped_at) as scraped_date,
        AVG(ph.price)::DECIMAL(10, 2) as avg_price,
        MIN(ph.price)::DECIMAL(10, 2) as min_price,
        MAX(ph.price)::DECIMAL(10, 2) as max_price,
        (COUNT(CASE WHEN ph.availability_status = 'in_stock' THEN 1 END)::DECIMAL / COUNT(*)::DECIMAL * 100)::DECIMAL(5, 2) as availability_rate
    FROM pricing.price_history ph
    WHERE ph.product_id = p_product_id 
      AND ph.competitor_id = p_competitor_id
      AND ph.scraped_at >= CURRENT_DATE - INTERVAL '1 day' * p_days
    GROUP BY DATE(ph.scraped_at)
    ORDER BY scraped_date DESC;
END;
$$ LANGUAGE plpgsql;

-- Get competitive pricing summary
CREATE OR REPLACE VIEW pricing.competitive_summary AS
WITH latest_prices AS (
    SELECT DISTINCT ON (ph.product_id, ph.competitor_id)
        ph.product_id,
        ph.competitor_id,
        ph.price,
        ph.member_price,
        ph.availability_status,
        ph.scraped_at,
        ph.url
    FROM pricing.price_history ph
    ORDER BY ph.product_id, ph.competitor_id, ph.scraped_at DESC
)
SELECT 
    p.brand,
    p.name as product_name,
    c.name as competitor_name,
    lp.price,
    lp.member_price,
    lp.availability_status,
    lp.scraped_at,
    EXTRACT(HOURS FROM (CURRENT_TIMESTAMP - lp.scraped_at)) as hours_since_update,
    lp.url
FROM latest_prices lp
JOIN pricing.products p ON p.id = lp.product_id
JOIN pricing.competitors c ON c.id = lp.competitor_id
ORDER BY p.brand, p.name, lp.price NULLS LAST;

-- Trigger to update timestamps
CREATE OR REPLACE FUNCTION pricing.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_competitors_updated_at
    BEFORE UPDATE ON pricing.competitors
    FOR EACH ROW
    EXECUTE FUNCTION pricing.update_updated_at();

CREATE TRIGGER update_products_updated_at
    BEFORE UPDATE ON pricing.products
    FOR EACH ROW
    EXECUTE FUNCTION pricing.update_updated_at();

-- Phase 2: Batch Processing Tables

-- Enum for batch job status
DO $$ BEGIN
    CREATE TYPE pricing.batch_job_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Batch jobs tracking
CREATE TABLE IF NOT EXISTS pricing.batch_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255),
    status pricing.batch_job_status DEFAULT 'pending',
    total_checks INTEGER,
    completed_checks INTEGER DEFAULT 0,
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    results_url TEXT,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb -- Store job parameters, settings
);

-- Individual job items
CREATE TABLE IF NOT EXISTS pricing.batch_job_items (
    id SERIAL PRIMARY KEY,
    batch_job_id UUID REFERENCES pricing.batch_jobs(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES pricing.products(id),
    competitor_id INTEGER REFERENCES pricing.competitors(id),
    status pricing.batch_job_status DEFAULT 'pending',
    processed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    result_data JSONB -- Store individual result data
);

-- Indexes for batch processing
CREATE INDEX IF NOT EXISTS idx_batch_jobs_status ON pricing.batch_jobs(status);
CREATE INDEX IF NOT EXISTS idx_batch_jobs_created_by ON pricing.batch_jobs(created_by);
CREATE INDEX IF NOT EXISTS idx_batch_job_items_status ON pricing.batch_job_items(batch_job_id, status);

-- Function to update batch job progress
CREATE OR REPLACE FUNCTION pricing.update_batch_job_progress(p_job_id UUID)
RETURNS void AS $$
DECLARE
    v_completed INTEGER;
    v_total INTEGER;
BEGIN
    -- Count completed items
    SELECT COUNT(*) INTO v_completed
    FROM pricing.batch_job_items
    WHERE batch_job_id = p_job_id
    AND status IN ('completed', 'failed');
    
    -- Get total items
    SELECT COUNT(*) INTO v_total
    FROM pricing.batch_job_items
    WHERE batch_job_id = p_job_id;
    
    -- Update job
    UPDATE pricing.batch_jobs
    SET completed_checks = v_completed,
        status = CASE 
            WHEN v_completed = v_total THEN 'completed'::pricing.batch_job_status
            WHEN status = 'pending' THEN 'running'::pricing.batch_job_status
            ELSE status
        END,
        started_at = CASE 
            WHEN started_at IS NULL THEN CURRENT_TIMESTAMP
            ELSE started_at
        END,
        completed_at = CASE
            WHEN v_completed = v_total THEN CURRENT_TIMESTAMP
            ELSE completed_at
        END
    WHERE id = p_job_id;
END;
$$ LANGUAGE plpgsql;

-- Sample data for testing
INSERT INTO pricing.competitors (name, urls, metadata) VALUES
    ('Harborside', ARRAY['https://shopharborside.com/'], '{"age_verification": true}'::jsonb),
    ('Elemental Wellness', ARRAY['https://elementalwellnesscenter.com/'], '{"age_verification": true}'::jsonb),
    ('Theraleaf', ARRAY['https://www.theraleafsjc.com/'], '{"age_verification": true}'::jsonb)
ON CONFLICT (name) DO NOTHING;

INSERT INTO pricing.products (name, brand, category, search_terms, metadata) VALUES
    ('Strawberry Gummies', 'Wyld', 'edibles', ARRAY['wyld strawberry', 'strawberry gummies 100mg'], '{"thc_content": "100mg", "package_size": "10-pack"}'::jsonb)
ON CONFLICT (brand, name) DO NOTHING;