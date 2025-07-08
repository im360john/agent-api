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

# Check schemas
with engine.connect() as conn:
    print("=== Schemas ===")
    result = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('pg_catalog', 'information_schema')"))
    schemas = [row[0] for row in result]
    for schema in schemas:
        print(f"Schema: {schema}")

# Check for product-related tables
with engine.connect() as conn:
    print("\n=== Tables with 'product' or 'pricing' ===")
    result = conn.execute(text("""
        SELECT table_schema, table_name 
        FROM information_schema.tables 
        WHERE (table_name LIKE '%product%' OR table_name LIKE '%pricing%' OR table_name LIKE '%competitive%')
        AND table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY table_schema, table_name
    """))
    tables = [(row[0], row[1]) for row in result]
    for schema, table in tables:
        print(f"{schema}.{table}")

# Check ai schema tables
with engine.connect() as conn:
    print("\n=== Tables in 'ai' schema ===")
    result = conn.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'ai'
        ORDER BY table_name
    """))
    for row in result:
        print(f"ai.{row[0]}")

# Try to find the correct table
potential_tables = [
    ('ai', 'products'),
    ('ai', 'competitive_pricing_products'),
    ('pricing', 'products'),
    ('public', 'products'),
    ('public', 'competitive_pricing_products'),
]

for schema, table in potential_tables:
    with engine.connect() as conn:
        try:
            result = conn.execute(text(f"SELECT 1 FROM {schema}.{table} LIMIT 1"))
            result.fetchone()
            print(f"\n=== Found table: {schema}.{table} ===")
            
            # Check structure
            result = conn.execute(text(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = '{schema}' AND table_name = '{table}'
                ORDER BY ordinal_position
            """))
            print("Columns:")
            for col_name, col_type in result:
                print(f"  - {col_name} ({col_type})")
            
            # Check for Wyld products
            result = conn.execute(text(f"""
                SELECT * FROM {schema}.{table}
                WHERE LOWER(brand) = 'wyld' OR LOWER(name) LIKE '%wyld%'
                LIMIT 5
            """))
            
            print("\nWyld products:")
            for row in result:
                print(f"  {row}")
                
        except Exception as e:
            continue