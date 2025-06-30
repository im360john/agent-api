#!/usr/bin/env python3
"""
Fix the competitive pricing agent memory persistence issue.

The agno framework expects memory tables to be in the 'ai' schema with a specific structure.
This script creates the proper table structure that the framework expects.
"""

import os
import sys
from sqlalchemy import create_engine, text
from db.session import db_url

def create_memory_tables():
    """Create the proper memory tables for the competitive pricing agent."""
    
    print("Creating memory tables for competitive pricing agent...")
    print(f"Database URL: {db_url[:30]}...")
    
    # Create engine
    engine = create_engine(db_url.replace('+asyncpg', '').replace('+aiopg', ''))
    
    with engine.connect() as conn:
        try:
            # Create the ai schema if it doesn't exist
            print("\n1. Creating 'ai' schema if not exists...")
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS ai;"))
            conn.commit()
            print("   ✓ Schema 'ai' ready")
            
            # Drop the old table if it exists (it has the wrong structure)
            print("\n2. Checking for old table in public schema...")
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'competitive_pricing_chat_memory'
                );
            """))
            
            if result.scalar():
                print("   ! Found old table in public schema")
                # Optional: Back up data first
                # conn.execute(text("CREATE TABLE public.competitive_pricing_chat_memory_backup AS SELECT * FROM public.competitive_pricing_chat_memory;"))
                # print("   ✓ Created backup table")
                
                # For now, just notify - uncomment to actually drop
                # conn.execute(text("DROP TABLE public.competitive_pricing_chat_memory;"))
                # print("   ✓ Dropped old table")
            
            # Create the memory table with the correct structure in ai schema
            print("\n3. Creating memory table in 'ai' schema...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS ai.competitive_pricing_chat_memory (
                    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
                    user_id VARCHAR,
                    memory TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB DEFAULT '{}'::jsonb
                );
            """))
            conn.commit()
            print("   ✓ Created ai.competitive_pricing_chat_memory table")
            
            # Create indexes
            print("\n4. Creating indexes...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_competitive_pricing_memory_user_id 
                ON ai.competitive_pricing_chat_memory(user_id);
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_competitive_pricing_memory_updated 
                ON ai.competitive_pricing_chat_memory(updated_at DESC);
            """))
            conn.commit()
            print("   ✓ Created indexes")
            
            # Create update trigger
            print("\n5. Creating update trigger...")
            conn.execute(text("""
                CREATE OR REPLACE FUNCTION ai.update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            """))
            
            conn.execute(text("""
                CREATE TRIGGER update_competitive_pricing_memory_updated_at 
                BEFORE UPDATE ON ai.competitive_pricing_chat_memory 
                FOR EACH ROW 
                EXECUTE FUNCTION ai.update_updated_at_column();
            """))
            conn.commit()
            print("   ✓ Created update trigger")
            
            # Verify the table structure
            print("\n6. Verifying table structure...")
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_schema = 'ai' 
                AND table_name = 'competitive_pricing_chat_memory'
                ORDER BY ordinal_position;
            """))
            
            print("\n   Table structure:")
            for row in result:
                print(f"   - {row[0]:15} {row[1]:20} {'NULL' if row[2] == 'YES' else 'NOT NULL':8} {row[3] or ''}")
            
            print("\n✅ Memory tables created successfully!")
            print("\nIMPORTANT: Make sure your agent configuration has:")
            print("  - delete_memories=False")
            print("  - clear_memories=False")
            print("  - enable_agentic_memory=True")
            print("  - A consistent agent_id (not changing between runs)")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            conn.rollback()
            raise

def check_agent_configuration():
    """Check the competitive pricing agent configuration."""
    
    print("\n\nChecking agent configuration...")
    
    # Import the agent module
    try:
        from agents.competitive_pricing_agent import get_competitive_pricing_agent
        
        # Create a test agent
        agent = get_competitive_pricing_agent()
        
        print(f"\nAgent configuration:")
        print(f"  - agent_id: {agent.agent_id}")
        print(f"  - enable_agentic_memory: {agent.enable_agentic_memory}")
        
        if hasattr(agent, 'memory') and agent.memory:
            memory = agent.memory
            print(f"  - memory.delete_memories: {memory.delete_memories}")
            print(f"  - memory.clear_memories: {memory.clear_memories}")
            
            if memory.delete_memories or memory.clear_memories:
                print("\n⚠️  WARNING: Memory is configured to delete/clear!")
                print("    Set delete_memories=False and clear_memories=False")
        
    except Exception as e:
        print(f"\n❌ Could not check agent configuration: {e}")

if __name__ == "__main__":
    print("=== Competitive Pricing Memory Fix ===\n")
    
    # Create the proper tables
    create_memory_tables()
    
    # Check agent configuration
    check_agent_configuration()
    
    print("\n=== Fix complete ===")