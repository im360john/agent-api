#!/usr/bin/env python3
"""Add more test products"""

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

# Add some Wyld variants
products_to_add = [
    ("Wyld Strawberry Gummies", "Wyld", "edibles", ["wyld strawberry", "strawberry gummies 100mg"], {"thc_content": "100mg", "package_size": "10-pack"}),
    ("Strawberry 20:1 CBD Hybrid Gummies", "Wyld", "edibles", ["wyld cbd strawberry", "strawberry cbd 20:1"], {"thc_content": "5mg", "cbd_content": "100mg", "package_size": "10-pack"}),
    ("Sour Apple Sativa Gummies", "Wyld", "edibles", ["wyld sour apple", "sour apple gummies"], {"thc_content": "100mg", "package_size": "10-pack"}),
]

with engine.begin() as conn:
    for name, brand, category, search_terms, metadata in products_to_add:
        # Check if exists
        result = conn.execute(text("""
            SELECT id FROM pricing.products 
            WHERE brand = :brand AND name = :name
        """), {"brand": brand, "name": name})
        
        if not result.fetchone():
            import json
            conn.execute(text("""
                INSERT INTO pricing.products (name, brand, category, search_terms, metadata)
                VALUES (:name, :brand, :category, :search_terms, :metadata)
            """), {
                "name": name,
                "brand": brand,
                "category": category,
                "search_terms": search_terms,
                "metadata": json.dumps(metadata)
            })
            print(f"Added: {brand} {name}")
        else:
            print(f"Already exists: {brand} {name}")
    
    # List all products
    print("\n=== All Products ===")
    result = conn.execute(text("SELECT id, brand, name FROM pricing.products ORDER BY brand, name"))
    for row in result:
        print(f"ID: {row[0]}, Brand: {row[1]}, Name: {row[2]}")
    
    # Add a competitor if missing
    result = conn.execute(text("SELECT id FROM pricing.competitors WHERE name = 'Airfield'"))
    if not result.fetchone():
        conn.execute(text("""
            INSERT INTO pricing.competitors (name, urls, metadata)
            VALUES ('Airfield', ARRAY['https://www.airfieldsupply.com/'], '{"age_verification": true}'::jsonb)
        """))
        print("\nAdded Airfield competitor")