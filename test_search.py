#!/usr/bin/env python3
"""Test product search logic"""

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

# Test different search scenarios
test_searches = [
    ("wyld strawberry gummies", None),
    ("strawberry gummies", "wyld"),
    ("strawberry", "wyld"),
    ("wyld", None),
]

for product_name, brand in test_searches:
    print(f"\n=== Searching for product_name='{product_name}', brand='{brand}' ===")
    
    # Extract brand from product name if not provided
    known_brands = ['wyld', 'kiva', 'camino', 'plus', 'wana', 'jetty', 'stiiizy']
    detected_brand = None
    
    if not brand:
        product_words = product_name.lower().split()
        for word in product_words:
            if word in known_brands:
                detected_brand = word
                # Remove brand from product name
                product_name = ' '.join([w for w in product_name.split() if w.lower() != detected_brand])
                break
    
    print(f"  After brand detection: product_name='{product_name}', detected_brand='{detected_brand}'")
    
    with engine.connect() as conn:
        # First query - like the agent does
        query = "SELECT id, name, brand, metadata FROM pricing.products WHERE LOWER(name) LIKE :name"
        params = {"name": f"%{product_name.lower()}%"}
        
        if brand or detected_brand:
            query += " AND LOWER(brand) = :brand"
            params["brand"] = (brand or detected_brand).lower()
        
        print(f"  Query: {query}")
        print(f"  Params: {params}")
        
        result = conn.execute(text(query), params)
        products = result.fetchall()
        
        print(f"  Found {len(products)} products:")
        for p in products:
            print(f"    - ID: {p[0]}, Brand: {p[2]}, Name: {p[1]}")