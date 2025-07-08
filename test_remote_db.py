#!/usr/bin/env python3
"""Test remote database on Render"""

from sqlalchemy import create_engine, text
import sys

# Remote database URL
db_url = "postgresql://rag_user:qGufXd7ddboX07VgmEqess0spXiXcmyu@dpg-d0poargdl3ps73b0c630-a:5432/agno"

print("Connecting to remote database on Render...")
print(f"DB URL: {db_url.replace('qGufXd7ddboX07VgmEqess0spXiXcmyu', '***')}")

try:
    engine = create_engine(db_url)
    
    # Test connection
    with engine.connect() as conn:
        print("\n✓ Successfully connected to remote database!")
        
        # Check schemas
        print("\n=== Checking Schemas ===")
        result = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('pg_catalog', 'information_schema') ORDER BY schema_name"))
        schemas = [row[0] for row in result]
        print(f"Found schemas: {schemas}")
        
        # Check if pricing schema exists
        if 'pricing' not in schemas:
            print("\n❌ ERROR: 'pricing' schema does not exist!")
            print("The competitive pricing schema needs to be created on the remote database.")
            sys.exit(1)
        
        # Check pricing tables
        print("\n=== Checking Pricing Tables ===")
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'pricing'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]
        print(f"Tables in pricing schema: {tables}")
        
        required_tables = ['competitors', 'products', 'price_history']
        missing_tables = [t for t in required_tables if t not in tables]
        
        if missing_tables:
            print(f"\n❌ ERROR: Missing tables: {missing_tables}")
            print("The competitive pricing schema needs to be applied to the remote database.")
            sys.exit(1)
        
        # Check products
        print("\n=== Checking Products ===")
        result = conn.execute(text("SELECT COUNT(*) FROM pricing.products"))
        product_count = result.scalar()
        print(f"Total products: {product_count}")
        
        if product_count > 0:
            result = conn.execute(text("SELECT id, brand, name FROM pricing.products ORDER BY brand, name LIMIT 10"))
            print("\nSample products:")
            for row in result:
                print(f"  ID: {row[0]}, Brand: {row[1]}, Name: {row[2]}")
        
        # Check competitors
        print("\n=== Checking Competitors ===")
        result = conn.execute(text("SELECT COUNT(*) FROM pricing.competitors"))
        competitor_count = result.scalar()
        print(f"Total competitors: {competitor_count}")
        
        if competitor_count > 0:
            result = conn.execute(text("SELECT id, name, urls FROM pricing.competitors ORDER BY name"))
            print("\nCompetitors:")
            for row in result:
                print(f"  ID: {row[0]}, Name: {row[1]}, URLs: {row[2]}")
        
        # Check price history
        print("\n=== Checking Price History ===")
        result = conn.execute(text("SELECT COUNT(*) FROM pricing.price_history"))
        history_count = result.scalar()
        print(f"Total price history records: {history_count}")
        
        # Check materialized view
        print("\n=== Checking Materialized View ===")
        try:
            result = conn.execute(text("SELECT COUNT(*) FROM pricing.latest_prices"))
            view_count = result.scalar()
            print(f"Records in latest_prices view: {view_count}")
        except Exception as e:
            print(f"❌ Materialized view 'latest_prices' error: {e}")
        
        print("\n=== Summary ===")
        if product_count == 0 or competitor_count == 0:
            print("⚠️  The schema exists but needs initial data:")
            print("   - Products: " + ("✓" if product_count > 0 else "❌ No products"))
            print("   - Competitors: " + ("✓" if competitor_count > 0 else "❌ No competitors"))
            print("\nRun the schema SQL file to populate initial data.")
        else:
            print("✓ Remote database is properly configured for competitive pricing!")
            
except Exception as e:
    print(f"\n❌ Error connecting to remote database: {e}")
    print("\nPlease check:")
    print("1. The database URL is correct")
    print("2. The database is accessible from your location")
    print("3. Network connectivity to Render")