#!/usr/bin/env python3
"""
Quick test of database connection
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

# Get database URL
from db.url import get_db_url

db_url = get_db_url()
print(f"Database URL: {db_url.replace(os.getenv('DB_PASS', ''), '***')}")

try:
    # Create engine
    engine = create_engine(db_url)
    
    # Test connection
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.scalar()
        print(f"\n✅ Successfully connected to PostgreSQL!")
        print(f"PostgreSQL version: {version}")
        
        # Check existing tables
        result = conn.execute(text("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'ai' 
            ORDER BY table_name
        """))
        
        tables = result.fetchall()
        if tables:
            print(f"\nExisting tables in 'ai' schema:")
            for schema, table in tables:
                print(f"  - {schema}.{table}")
        else:
            print("\nNo tables found in 'ai' schema (will be created on first use)")
            
except Exception as e:
    print(f"\n❌ Database connection failed!")
    print(f"Error: {type(e).__name__}: {e}")