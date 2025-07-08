#!/usr/bin/env python3
"""Check pricing data in database"""

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

with engine.connect() as conn:
    print("=== All Products ===")
    result = conn.execute(text("SELECT id, brand, name FROM pricing.products ORDER BY brand, name"))
    for row in result:
        print(f"ID: {row[0]}, Brand: {row[1]}, Name: {row[2]}")
    
    print("\n=== All Competitors ===")
    result = conn.execute(text("SELECT id, name, urls FROM pricing.competitors ORDER BY name"))
    for row in result:
        print(f"ID: {row[0]}, Name: {row[1]}, URLs: {row[2]}")
    
    print("\n=== Price History (last 10) ===")
    result = conn.execute(text("""
        SELECT 
            p.brand || ' ' || p.name as product,
            c.name as competitor,
            ph.price,
            ph.availability_status,
            ph.scraped_at,
            ph.url
        FROM pricing.price_history ph
        JOIN pricing.products p ON ph.product_id = p.id
        JOIN pricing.competitors c ON ph.competitor_id = c.id
        ORDER BY ph.scraped_at DESC
        LIMIT 10
    """))
    
    count = 0
    for row in result:
        count += 1
        print(f"{row[0]} at {row[1]}: ${row[2] if row[2] else 'N/A'} ({row[3]}) - {row[4]}")
    
    if count == 0:
        print("No price history found")