#!/usr/bin/env python3
"""Check products in database"""

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

with engine.begin() as conn:
    # First check schemas
    print("=== Schemas ===")
    result = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('pg_catalog', 'information_schema')"))
    for row in result:
        print(f"Schema: {row[0]}")
    
    # Check for product-related tables
    print("\n=== Product Tables ===")
    result = conn.execute(text("""
        SELECT table_schema, table_name 
        FROM information_schema.tables 
        WHERE table_name LIKE '%product%' OR table_name LIKE '%pricing%'
        ORDER BY table_schema, table_name
    """))
    for row in result:
        print(f"Schema: {row[0]}, Table: {row[1]}")
    
    # Try to find products in different schemas
    for schema in ['public', 'pricing']:
        try:
            print(f"\n=== Checking {schema} schema for Wyld products ===")
            result = conn.execute(text(f"""
                SELECT id, name, brand
                FROM {schema}.products 
                WHERE LOWER(brand) = 'wyld'
                LIMIT 5
            """))
            for row in result:
                print(f"ID: {row[0]}, Brand: {row[2]}, Name: {row[1]}")
        except Exception as e:
            print(f"Error checking {schema}.products: {e}")
    
    # Check if agno tables exist
    print("\n=== Agno Tables ===")
    result = conn.execute(text("""
        SELECT table_schema, table_name 
        FROM information_schema.tables 
        WHERE table_name LIKE '%competitive_pricing%'
        ORDER BY table_schema, table_name
    """))
    for row in result:
        print(f"Schema: {row[0]}, Table: {row[1]}")