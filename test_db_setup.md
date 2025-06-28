# Database Setup Instructions for Competitive Pricing Agent

The competitive pricing agent is deployed but encountering database errors. This indicates the PostgreSQL tables haven't been created on the deployment.

## Required Database Setup

1. **Connect to your Render PostgreSQL database**

2. **Run the schema creation SQL** from `sql/competitive_pricing_schema.sql`:
   ```sql
   -- Create schema
   CREATE SCHEMA IF NOT EXISTS pricing;

   -- Create tables
   CREATE TABLE IF NOT EXISTS pricing.competitors (
       id SERIAL PRIMARY KEY,
       name VARCHAR(255) NOT NULL UNIQUE,
       urls TEXT[] NOT NULL,
       enabled BOOLEAN DEFAULT TRUE,
       metadata JSONB DEFAULT '{}',
       created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
       updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
   );

   CREATE TABLE IF NOT EXISTS pricing.products (
       id SERIAL PRIMARY KEY,
       name VARCHAR(255) NOT NULL,
       brand VARCHAR(255),
       category VARCHAR(100),
       search_terms TEXT[],
       metadata JSONB DEFAULT '{}',
       enabled BOOLEAN DEFAULT TRUE,
       created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
       updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
       UNIQUE(name, brand)
   );

   CREATE TABLE IF NOT EXISTS pricing.price_history (
       id SERIAL PRIMARY KEY,
       product_id INTEGER NOT NULL REFERENCES pricing.products(id),
       competitor_id INTEGER NOT NULL REFERENCES pricing.competitors(id),
       price DECIMAL(10,2),
       member_price DECIMAL(10,2),
       availability_status VARCHAR(50) DEFAULT 'unknown',
       url TEXT,
       scraper_used VARCHAR(50),
       raw_data JSONB,
       price_tiers JSONB,
       scraped_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
       created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
   );

   -- Create indexes
   CREATE INDEX idx_price_history_product_competitor ON pricing.price_history(product_id, competitor_id);
   CREATE INDEX idx_price_history_scraped_at ON pricing.price_history(scraped_at DESC);
   CREATE INDEX idx_products_search ON pricing.products USING GIN (search_terms);
   ```

## Environment Variables Needed

Make sure these are set in your Render deployment:

```bash
# Database (should already be set by Render)
DB_USER=<from_render>
DB_PASS=<from_render>
DB_HOST=<from_render>
DB_PORT=<from_render>
DB_DATABASE=<from_render>

# API Keys for scraping
FIRECRAWL_API_KEY=<your_key>
EXA_API_KEY=<your_key>
BROWSERBASE_API_KEY=<your_key>  # Optional
BROWSERBASE_PROJECT_ID=<your_id>  # Optional
```

## Verification

After running the schema, test with:
```sql
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'pricing';
```

Should return:
- competitors
- products
- price_history