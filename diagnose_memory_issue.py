#!/usr/bin/env python3
"""
Diagnose why messages are not being saved to the competitive_pricing_chat_memory table.
"""

import os
import asyncio
from datetime import datetime
from sqlalchemy import create_engine, text
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.models.openai import OpenAIChat
from db.session import db_url

async def test_memory_save():
    """Test if the memory system can save messages."""
    
    print("Testing memory save functionality...")
    print(f"Database URL: {db_url[:30]}...")  # Show only first 30 chars for security
    
    # Create memory components
    memory_db = PostgresMemoryDb(
        table_name="competitive_pricing_chat_memory",
        db_url=db_url
    )
    
    memory = Memory(
        model=OpenAIChat(id="gpt-4"),
        db=memory_db,
        delete_memories=False,
        clear_memories=False,
    )
    
    # Create a test session
    test_user_id = "test_user_123"
    test_session_id = f"test_session_{datetime.now().isoformat()}"
    
    print(f"\nTest user_id: {test_user_id}")
    print(f"Test session_id: {test_session_id}")
    
    # Try to save a test memory
    try:
        # The Memory class might have methods like 'add', 'save', or 'store'
        # Let's explore what methods are available
        print("\nAvailable Memory methods:")
        for attr in dir(memory):
            if not attr.startswith('_') and callable(getattr(memory, attr)):
                print(f"  - {attr}")
        
        print("\nAvailable PostgresMemoryDb methods:")
        for attr in dir(memory_db):
            if not attr.startswith('_') and callable(getattr(memory_db, attr)):
                print(f"  - {attr}")
        
    except Exception as e:
        print(f"\nError during memory operation: {e}")
        import traceback
        traceback.print_exc()
    
    # Check the database directly
    engine = create_engine(db_url.replace('+asyncpg', '').replace('+aiopg', ''))
    
    with engine.connect() as conn:
        # Check if any records exist
        result = conn.execute(text("""
            SELECT COUNT(*) FROM competitive_pricing_chat_memory;
        """))
        count = result.scalar()
        print(f"\nTotal records in competitive_pricing_chat_memory: {count}")
        
        if count > 0:
            # Show recent records
            result = conn.execute(text("""
                SELECT user_id, session_id, created_at 
                FROM competitive_pricing_chat_memory 
                ORDER BY created_at DESC 
                LIMIT 5;
            """))
            print("\nRecent records:")
            for row in result:
                print(f"  - User: {row[0]}, Session: {row[1][:20]}..., Created: {row[2]}")

def check_table_schema():
    """Check the actual schema of the memory table."""
    
    print("\nChecking table schema...")
    engine = create_engine(db_url.replace('+asyncpg', '').replace('+aiopg', ''))
    
    with engine.connect() as conn:
        # Get all tables that might be memory-related
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%memory%'
            ORDER BY table_name;
        """))
        
        print("\nMemory-related tables found:")
        for row in result:
            print(f"  - {row[0]}")
        
        # Check for agno-specific tables
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND (table_name LIKE '%agno%' OR table_name LIKE '%message%' OR table_name LIKE '%chat%')
            ORDER BY table_name;
        """))
        
        print("\nOther potentially related tables:")
        for row in result:
            print(f"  - {row[0]}")

if __name__ == "__main__":
    print("=== Competitive Pricing Memory Diagnostic ===\n")
    
    # Check table schema first
    check_table_schema()
    
    # Test memory save
    asyncio.run(test_memory_save())
    
    print("\n=== Diagnostic complete ===")