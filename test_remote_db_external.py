#!/usr/bin/env python3
"""Test remote database on Render with external URL"""

from sqlalchemy import create_engine, text
import sys

# Try with render.com domain (typical pattern for external access)
# The internal hostname pattern dpg-XXX-a suggests external would be dpg-XXX-a.oregon-postgres.render.com
possible_hosts = [
    "dpg-d0poargdl3ps73b0c630-a.oregon-postgres.render.com",
    "dpg-d0poargdl3ps73b0c630-a.ohio-postgres.render.com", 
    "dpg-d0poargdl3ps73b0c630-a.frankfurt-postgres.render.com",
    "dpg-d0poargdl3ps73b0c630-a.singapore-postgres.render.com",
    "dpg-d0poargdl3ps73b0c630-a.postgres.render.com"
]

print("Attempting to connect to remote Render database...")
print("Trying possible external hostnames...\n")

for host in possible_hosts:
    db_url = f"postgresql://rag_user:qGufXd7ddboX07VgmEqess0spXiXcmyu@{host}:5432/agno"
    print(f"Trying: {host}...")
    
    try:
        engine = create_engine(db_url, connect_args={'connect_timeout': 5})
        
        # Test connection
        with engine.connect() as conn:
            print(f"✓ SUCCESS! Connected using: {host}")
            
            # Quick test query
            result = conn.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            print(f"Connected to database: {db_name}")
            
            # Save working URL
            print(f"\nWorking external URL:")
            print(f"postgresql://rag_user:***@{host}:5432/agno")
            
            # Now run full schema check
            print("\n=== Checking Schemas ===")
            result = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('pg_catalog', 'information_schema') ORDER BY schema_name"))
            schemas = [row[0] for row in result]
            print(f"Found schemas: {schemas}")
            
            if 'pricing' not in schemas:
                print("\n❌ 'pricing' schema does not exist on remote database!")
                print("\nTo fix this, run the following on the remote database:")
                print("1. Connect to the database")
                print("2. Run the SQL from sql/competitive_pricing_schema.sql")
            else:
                print("\n✓ 'pricing' schema exists!")
                
                # Check tables
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'pricing'
                    ORDER BY table_name
                """))
                tables = [row[0] for row in result]
                print(f"\nTables in pricing schema: {tables}")
                
                if tables:
                    # Check data
                    result = conn.execute(text("SELECT COUNT(*) FROM pricing.products"))
                    product_count = result.scalar()
                    
                    result = conn.execute(text("SELECT COUNT(*) FROM pricing.competitors"))
                    competitor_count = result.scalar()
                    
                    print(f"\nData summary:")
                    print(f"  - Products: {product_count}")
                    print(f"  - Competitors: {competitor_count}")
            
            break
            
    except Exception as e:
        if "timeout" in str(e).lower() or "could not connect" in str(e).lower():
            continue
        else:
            print(f"  Error: {type(e).__name__}: {str(e)[:100]}...")
            continue
else:
    print("\n❌ Could not connect to remote database with any of the tried hostnames.")
    print("\nThe internal hostname 'dpg-d0poargdl3ps73b0c630-a' suggests this is a Render database.")
    print("You need the external connection string from Render's dashboard.")
    print("\nTo get the external connection string:")
    print("1. Go to your Render dashboard")
    print("2. Navigate to your PostgreSQL database")
    print("3. Look for 'External Database URL' (not Internal)")
    print("4. That URL will have a publicly accessible hostname")