#!/usr/bin/env python3
"""Test script to understand agno storage patterns"""

from sqlalchemy import create_engine, text
from db.session import db_url
import json

# Create engine
engine = create_engine(db_url.replace('+asyncpg', '').replace('+aiopg', ''))

print("=== Investigating Agno Storage Tables ===\n")

with engine.connect() as conn:
    # 1. List all agno-related tables
    print("1. Tables that might contain agent/session data:")
    result = conn.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND (
            table_name LIKE '%agent%' 
            OR table_name LIKE '%session%'
            OR table_name LIKE '%memory%'
            OR table_name LIKE '%chat%'
        )
        ORDER BY table_name;
    """))
    
    tables = list(result)
    for row in tables:
        print(f"   - {row[0]}")
    
    # 2. Check competitive_pricing_chat_agents structure
    print("\n2. Checking competitive_pricing_chat_agents table structure:")
    result = conn.execute(text("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns 
        WHERE table_name = 'competitive_pricing_chat_agents'
        ORDER BY ordinal_position;
    """))
    
    columns = list(result)
    if columns:
        print("   Columns:")
        for col in columns:
            print(f"   - {col[0]}: {col[1]} (nullable: {col[2]})")
            
        # Sample data
        print("\n   Sample data:")
        result = conn.execute(text("""
            SELECT * FROM competitive_pricing_chat_agents
            LIMIT 3
        """))
        for row in result:
            print(f"   {dict(row)}")
    else:
        print("   Table doesn't exist!")
    
    # 3. Check competitive_pricing_chat_memory structure
    print("\n3. Checking competitive_pricing_chat_memory table structure:")
    result = conn.execute(text("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns 
        WHERE table_name = 'competitive_pricing_chat_memory'
        ORDER BY ordinal_position;
    """))
    
    columns = list(result)
    if columns:
        print("   Columns:")
        for col in columns:
            print(f"   - {col[0]}: {col[1]} (nullable: {col[2]})")
    
    # 4. Check session data patterns
    print("\n4. Session data patterns in memory table:")
    result = conn.execute(text("""
        SELECT 
            COUNT(DISTINCT session_id) as unique_sessions,
            COUNT(DISTINCT user_id) as unique_users,
            COUNT(*) as total_messages,
            MIN(created_at) as oldest_message,
            MAX(created_at) as newest_message
        FROM competitive_pricing_chat_memory
    """))
    
    stats = result.first()
    if stats:
        print(f"   - Unique sessions: {stats[0]}")
        print(f"   - Unique users: {stats[1]}")
        print(f"   - Total messages: {stats[2]}")
        print(f"   - Date range: {stats[3]} to {stats[4]}")
    
    # 5. Sample session data
    print("\n5. Sample session data:")
    result = conn.execute(text("""
        SELECT 
            session_id,
            user_id,
            COUNT(*) as message_count,
            MIN(created_at) as first_message,
            MAX(created_at) as last_message
        FROM competitive_pricing_chat_memory
        GROUP BY session_id, user_id
        ORDER BY MAX(created_at) DESC
        LIMIT 5
    """))
    
    for row in result:
        print(f"   Session: {row[0][:20]}...")
        print(f"   User: {row[1]}")
        print(f"   Messages: {row[2]}")
        print(f"   Duration: {row[3]} to {row[4]}")
        print()

print("\n=== Summary ===")
print("Agno appears to store:")
print("1. Agent configurations in 'competitive_pricing_chat_agents' table")
print("2. Chat history/memory in 'competitive_pricing_chat_memory' table")
print("3. Sessions are identified by session_id in the memory table")
print("4. No separate 'sessions' table - sessions are derived from memory data")