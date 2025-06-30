#!/usr/bin/env python3
"""Check and diagnose memory table schema issues"""

from sqlalchemy import create_engine, text
from db.session import db_url

engine = create_engine(db_url.replace('+asyncpg', '').replace('+aiopg', ''))

print("=== Checking Memory Table Schema ===\n")

with engine.connect() as conn:
    # Check if ai schema exists
    print("1. Checking for 'ai' schema:")
    result = conn.execute(text("""
        SELECT schema_name 
        FROM information_schema.schemata 
        WHERE schema_name = 'ai'
    """))
    
    if result.rowcount > 0:
        print("   ✓ 'ai' schema exists")
    else:
        print("   ✗ 'ai' schema does NOT exist")
        print("   Creating 'ai' schema...")
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS ai"))
        conn.commit()
    
    # Check for memory table in ai schema
    print("\n2. Checking for memory table in 'ai' schema:")
    result = conn.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'ai' 
        AND table_name = 'competitive_pricing_chat_memory'
    """))
    
    if result.rowcount > 0:
        print("   ✓ Table 'ai.competitive_pricing_chat_memory' exists")
        
        # Check columns
        print("\n   Table structure:")
        result = conn.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_schema = 'ai'
            AND table_name = 'competitive_pricing_chat_memory'
            ORDER BY ordinal_position
        """))
        
        for row in result:
            print(f"   - {row[0]}: {row[1]} (nullable: {row[2]})")
    else:
        print("   ✗ Table 'ai.competitive_pricing_chat_memory' does NOT exist")
        print("   The agno framework will create it automatically on first use")
    
    # Check for memory table in public schema
    print("\n3. Checking for memory table in 'public' schema:")
    result = conn.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'competitive_pricing_chat_memory'
    """))
    
    if result.rowcount > 0:
        print("   ⚠️  Table exists in 'public' schema (wrong location)")
        print("   The agno framework expects tables in 'ai' schema")
    else:
        print("   ✓ No conflicting table in 'public' schema")
    
    # Check existing data
    print("\n4. Checking for existing memory data:")
    try:
        result = conn.execute(text("""
            SELECT COUNT(*) as count 
            FROM ai.competitive_pricing_chat_memory
        """))
        count = result.scalar()
        print(f"   Found {count} records in ai.competitive_pricing_chat_memory")
    except Exception as e:
        print(f"   Could not query table: {e}")

print("\n=== Summary ===")
print("The agno framework stores memory in the 'ai' schema.")
print("If the table doesn't exist, it will be created automatically.")
print("Make sure your queries reference 'ai.competitive_pricing_chat_memory'.")