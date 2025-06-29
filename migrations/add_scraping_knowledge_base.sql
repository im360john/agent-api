-- Create pricing schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS pricing;

-- Create scraping metrics table to track scraping performance
CREATE TABLE IF NOT EXISTS pricing.scraping_metrics (
    id SERIAL PRIMARY KEY,
    competitor_id INTEGER,
    competitor_name VARCHAR(255),
    product_search VARCHAR(500),
    tool_used VARCHAR(100), -- 'firecrawl', 'browserbase', 'exa'
    url_attempted TEXT,
    success BOOLEAN,
    confidence_score DECIMAL(3,2), -- 0.00 to 1.00
    price_confidence VARCHAR(50), -- 'high', 'medium', 'low'
    stock_confidence VARCHAR(50), -- 'high', 'medium', 'low'
    response_time_ms INTEGER,
    error_message TEXT,
    scraped_data JSONB, -- Raw scraped data for analysis
    scraped_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_scraping_metrics_competitor ON pricing.scraping_metrics(competitor_id);
CREATE INDEX IF NOT EXISTS idx_scraping_metrics_tool ON pricing.scraping_metrics(tool_used);
CREATE INDEX IF NOT EXISTS idx_scraping_metrics_success ON pricing.scraping_metrics(success);
CREATE INDEX IF NOT EXISTS idx_scraping_metrics_scraped_at ON pricing.scraping_metrics(scraped_at);

-- Create knowledge base table for storing learned patterns and corrections
CREATE TABLE IF NOT EXISTS pricing.knowledge_base (
    id SERIAL PRIMARY KEY,
    kb_type VARCHAR(50), -- 'url_pattern', 'selector', 'correction', 'variant_mapping'
    competitor_id INTEGER,
    context JSONB, -- Contextual information
    pattern TEXT, -- The pattern or knowledge item
    confidence DECIMAL(3,2) DEFAULT 0.50,
    usage_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255),
    embedding vector(1536) -- For semantic search
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_knowledge_base_type ON pricing.knowledge_base(kb_type);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_competitor ON pricing.knowledge_base(competitor_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_confidence ON pricing.knowledge_base(confidence DESC);

-- Create vector similarity index for semantic search
CREATE INDEX IF NOT EXISTS idx_knowledge_base_embedding ON pricing.knowledge_base 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create user corrections table
CREATE TABLE IF NOT EXISTS pricing.user_corrections (
    id SERIAL PRIMARY KEY,
    product_id INTEGER,
    competitor_id INTEGER,
    correction_type VARCHAR(50), -- 'price', 'stock_status', 'url', 'product_name'
    original_value TEXT,
    corrected_value TEXT,
    user_id VARCHAR(255),
    session_id VARCHAR(255),
    confidence_impact DECIMAL(3,2), -- How much this should affect confidence
    applied BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create learned patterns table
CREATE TABLE IF NOT EXISTS pricing.learned_patterns (
    id SERIAL PRIMARY KEY,
    competitor_id INTEGER,
    pattern_type VARCHAR(50), -- 'url_structure', 'price_selector', 'stock_indicator'
    pattern_value TEXT,
    success_rate DECIMAL(3,2),
    last_successful_use TIMESTAMP,
    failure_count INTEGER DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Check if price_history table exists before adding columns
DO $$ 
BEGIN 
    IF EXISTS (SELECT 1 FROM information_schema.tables 
               WHERE table_schema = 'pricing' AND table_name = 'price_history') THEN
        -- Add confidence columns to price_history
        ALTER TABLE pricing.price_history 
        ADD COLUMN IF NOT EXISTS scraping_confidence DECIMAL(3,2),
        ADD COLUMN IF NOT EXISTS price_confidence VARCHAR(50),
        ADD COLUMN IF NOT EXISTS stock_confidence VARCHAR(50),
        ADD COLUMN IF NOT EXISTS scraping_tool VARCHAR(100),
        ADD COLUMN IF NOT EXISTS scraping_url TEXT,
        ADD COLUMN IF NOT EXISTS scraping_duration_ms INTEGER;
    END IF;
END $$;