#!/usr/bin/env python3
"""
Check memory storage for Slack Treez Agent
"""

import os
import sys
import asyncio
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_memory_tables():
    """Check what tables exist and their contents related to memory"""
    
    # Get database URL
    db_url = os.getenv("DATABASE_URL", "postgresql+psycopg://user:password@location/agno")
    
    # Handle legacy postgres:// URLs
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    elif db_url.startswith("postgresql+psycopg://"):
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://", 1)
    
    print(f"Connecting to database...")
    
    try:
        # Create engine
        engine = create_engine(db_url)
        
        # Get inspector
        inspector = inspect(engine)
        
        # Check all schemas
        schemas = inspector.get_schema_names()
        print(f"\nAvailable schemas: {schemas}")
        
        # Check for memory-related tables in each schema
        memory_tables = []
        for schema in schemas:
            tables = inspector.get_table_names(schema=schema)
            for table in tables:
                if 'memory' in table.lower() or 'slack' in table.lower():
                    memory_tables.append(f"{schema}.{table}")
        
        print(f"\nMemory/Slack related tables found: {memory_tables}")
        
        # Check specific tables
        with engine.connect() as conn:
            # Check if ai schema exists
            result = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'ai'"))
            if result.rowcount > 0:
                print("\n'ai' schema exists")
                
                # List all tables in ai schema
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'ai' 
                    ORDER BY table_name
                """))
                print("\nTables in 'ai' schema:")
                for row in result:
                    print(f"  - {row[0]}")
                
                # Check for memory table
                result = conn.execute(text("""
                    SELECT COUNT(*) as count
                    FROM information_schema.tables 
                    WHERE table_schema = 'ai' 
                    AND table_name = 'slack_treez_agent_memory'
                """))
                memory_table_exists = result.scalar() > 0
                
                if memory_table_exists:
                    print("\n✅ Memory table 'ai.slack_treez_agent_memory' EXISTS")
                    
                    # Check structure
                    result = conn.execute(text("""
                        SELECT column_name, data_type 
                        FROM information_schema.columns 
                        WHERE table_schema = 'ai' 
                        AND table_name = 'slack_treez_agent_memory'
                        ORDER BY ordinal_position
                    """))
                    print("\nTable structure:")
                    for row in result:
                        print(f"  - {row[0]}: {row[1]}")
                    
                    # Check row count
                    result = conn.execute(text("SELECT COUNT(*) FROM ai.slack_treez_agent_memory"))
                    count = result.scalar()
                    print(f"\nRow count: {count}")
                    
                    # Show sample data if any
                    if count > 0:
                        result = conn.execute(text("""
                            SELECT id, user_id, created_at, updated_at
                            FROM ai.slack_treez_agent_memory 
                            ORDER BY updated_at DESC 
                            LIMIT 5
                        """))
                        print("\nRecent memory entries:")
                        for row in result:
                            print(f"  - ID: {row[0]}, User: {row[1]}, Created: {row[2]}, Updated: {row[3]}")
                else:
                    print("\n❌ Memory table 'ai.slack_treez_agent_memory' does NOT exist")
                    print("\nThe table may need to be created. The agent should create it automatically on first use.")
                
                # Also check sessions table
                result = conn.execute(text("""
                    SELECT COUNT(*) as count
                    FROM information_schema.tables 
                    WHERE table_schema = 'ai' 
                    AND table_name = 'slack_treez_agent_sessions'
                """))
                sessions_table_exists = result.scalar() > 0
                
                if sessions_table_exists:
                    print("\n✅ Sessions table 'ai.slack_treez_agent_sessions' EXISTS")
                    result = conn.execute(text("SELECT COUNT(*) FROM ai.slack_treez_agent_sessions"))
                    count = result.scalar()
                    print(f"   Row count: {count}")
                else:
                    print("\n❌ Sessions table 'ai.slack_treez_agent_sessions' does NOT exist")
            else:
                print("\n'ai' schema does not exist!")
                
    except Exception as e:
        print(f"\nError checking database: {e}")
        import traceback
        traceback.print_exc()

async def test_memory_creation():
    """Test if memory gets created when agent is used"""
    from agents.slack_treez_agent import get_slack_treez_agent, SlackTreezBot
    
    print("\n" + "="*60)
    print("Testing memory creation...")
    print("="*60)
    
    try:
        # Create agent
        agent = get_slack_treez_agent(debug_mode=False)
        print("✅ Agent created successfully")
        
        # Check if memory is configured
        print(f"\nMemory configuration:")
        print(f"  - enable_agentic_memory: {agent.enable_agentic_memory}")
        print(f"  - memory object exists: {agent.memory is not None}")
        if agent.memory:
            print(f"  - memory db exists: {hasattr(agent.memory, 'db')}")
        
        # Create bot and process a message
        bot = SlackTreezBot(agent)
        
        event = {
            "text": "<@bot> What is Treez POS?",
            "user": "test_memory_user",
            "channel": "test_memory_channel",
            "ts": "1234567890"
        }
        
        print("\nProcessing test message to trigger memory creation...")
        response = await bot.process_mention(event)
        print(f"✅ Message processed. Response length: {len(response)} chars")
        
    except Exception as e:
        print(f"❌ Error testing memory: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Check existing tables
    check_memory_tables()
    
    # Test memory creation
    if os.getenv("OPENAI_API_KEY"):
        asyncio.run(test_memory_creation())
    else:
        print("\n⚠️  Skipping memory creation test - OPENAI_API_KEY not set")