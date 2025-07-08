#!/usr/bin/env python3
"""Create materialized view on remote database"""

from sqlalchemy import create_engine, text

# External Render database URL
db_url = "postgresql://rag_user:qGufXd7ddboX07VgmEqess0spXiXcmyu@dpg-d0poargdl3ps73b0c630-a.oregon-postgres.render.com:5432/agno"

engine = create_engine(db_url)

print("Creating materialized view on remote database...\n")

with engine.begin() as conn:
    try:
        # Create the materialized view
        conn.execute(text("""
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
            WHERE c.enabled = true
            ORDER BY product_id, competitor_id, scraped_at DESC
        """))
        print("✓ Created materialized view 'latest_prices'")
        
        # Create indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_latest_prices_lookup ON pricing.latest_prices(product_id, competitor_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_latest_prices_freshness ON pricing.latest_prices(freshness_status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_latest_prices_hours ON pricing.latest_prices(hours_old)"))
        print("✓ Created indexes on materialized view")
        
        # Check the view
        result = conn.execute(text("SELECT COUNT(*) FROM pricing.latest_prices"))
        count = result.scalar()
        print(f"\n✓ Materialized view contains {count} records")
        
    except Exception as e:
        if "already exists" in str(e):
            print("Materialized view already exists, refreshing it...")
            conn.execute(text("REFRESH MATERIALIZED VIEW pricing.latest_prices"))
            print("✓ Refreshed materialized view")
        else:
            raise

print("\n✓ Remote database is now fully configured!")