#!/usr/bin/env python3
"""Check what agno tables exist in the database"""

from sqlalchemy import create_engine, text
from db.session import db_url

# Create engine
engine = create_engine(db_url.replace('+asyncpg', '').replace('+aiopg', ''))

# Check for agno tables
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND (
            table_name LIKE '%agent%' 
            OR table_name LIKE '%session%'
            OR table_name LIKE '%memory%'
        )
        ORDER BY table_name;
    """))
    
    print("Tables found:")
    for row in result:
        print(f"  - {row[0]}")
    
    # Check specific agno agent table
    print("\nChecking competitive_pricing_chat_agents table...")
    result = conn.execute(text("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'competitive_pricing_chat_agents'
        ORDER BY ordinal_position;
    """))
    
    columns = list(result)
    if columns:
        print("Columns:")
        for col in columns:
            print(f"  - {col[0]}: {col[1]}")
    else:
        print("Table doesn't exist!")
        
    # Check for agent sessions
    print("\nChecking for existing sessions...")
    try:
        result = conn.execute(text("""
            SELECT COUNT(*) as count
            FROM competitive_pricing_chat_agents
        """))
        count = result.scalar()
        print(f"Found {count} records in agent storage table")
    except Exception as e:
        print(f"Error: {e}")