#!/usr/bin/env python3
"""Test database connection"""

import os
import psycopg
from sqlalchemy import create_engine, text

# Get database URL
db_url = os.getenv("DATABASE_URL", "postgresql://rag_user:qGufXd7ddboX07VgmEqess0spXiXcmyu@dpg-d0poargdl3ps73b0c630-a.oregon-postgres.render.com/rag_api")

print(f"Testing connection to: {db_url.split('@')[1]}")  # Hide password

try:
    # Test with SQLAlchemy
    engine = create_engine(db_url)
    with engine.connect() as conn:
        # Test basic connection
        result = conn.execute(text("SELECT current_database(), current_schema()"))
        db_name, schema = result.fetchone()
        print(f"\nConnected to database: {db_name}")
        print(f"Current schema: {schema}")
        
        # Check if schema 'ai' exists
        result = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'ai'"))
        schemas = result.fetchall()
        if schemas:
            print(f"\nSchema 'ai' exists")
        else:
            print(f"\nWARNING: Schema 'ai' does not exist!")
        
        # Check search_path
        result = conn.execute(text("SHOW search_path"))
        search_path = result.fetchone()[0]
        print(f"Current search_path: {search_path}")
        
        # Check if table exists (with schema prefix)
        result = conn.execute(text("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_name = 'treez_support_articles'
        """))
        tables = result.fetchall()
        
        if tables:
            print(f"\nTable 'treez_support_articles' found in schemas:")
            for schema, table in tables:
                print(f"  - {schema}.{table}")
        else:
            print(f"\nWARNING: Table 'treez_support_articles' not found in any schema!")
        
        # Try to query the table directly with schema
        try:
            result = conn.execute(text("SELECT COUNT(*) FROM ai.treez_support_articles"))
            count = result.fetchone()[0]
            print(f"\nSuccessfully queried ai.treez_support_articles: {count} rows")
        except Exception as e:
            print(f"\nERROR querying ai.treez_support_articles: {e}")
            
except Exception as e:
    print(f"\nConnection failed: {type(e).__name__}: {e}")