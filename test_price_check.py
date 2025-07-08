#!/usr/bin/env python3
"""Test the price check functionality by simulating the issue"""

from sqlalchemy import create_engine, text
import os

# Construct DB URL from environment
db_driver = os.getenv("DB_DRIVER", "postgresql+psycopg")
db_user = os.getenv("DB_USER", "ai")
db_pass = os.getenv("DB_PASS", "ai")
db_host = os.getenv("DB_HOST", "localhost")
db_port = os.getenv("DB_PORT", "5432")
db_database = os.getenv("DB_DATABASE", "ai")

db_url = "{}://{}{}@{}:{}/{}".format(
    db_driver,
    db_user,
    f":{db_pass}" if db_pass else "",
    db_host,
    db_port,
    db_database,
)

engine = create_engine(db_url.replace('+asyncpg', '').replace('+aiopg', ''))

# Simulate what happens when agent calls check_prices
print("=== Simulating the issue ===")

with engine.connect() as conn:
    # The agent found these products:
    result = conn.execute(text("""
        SELECT id, name, brand FROM pricing.products 
        WHERE LOWER(name) LIKE '%strawberry%'
        ORDER BY name
    """))
    
    products = result.fetchall()
    print(f"Found {len(products)} strawberry products:")
    for p in products:
        print(f"  - ID: {p[0]}, Brand: {p[2]}, Name: {p[1]}")
    
    # Now simulate scraping for each product
    print("\n=== Simulating search queries for scraping ===")
    for product_id, prod_name, prod_brand in products:
        # OLD logic (duplicates brand)
        old_search_query = f"{prod_brand} {prod_name}"
        
        # NEW logic (avoids duplication)
        if prod_brand.lower() in prod_name.lower():
            new_search_query = prod_name
        else:
            new_search_query = f"{prod_brand} {prod_name}"
        
        print(f"\nProduct: {prod_name} (Brand: {prod_brand})")
        print(f"  OLD search query: '{old_search_query}'")
        print(f"  NEW search query: '{new_search_query}'")