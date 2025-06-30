#!/usr/bin/env python3
"""
Initialize memory tables for the agno framework.

This script ensures that the PostgresMemoryDb tables are created with the correct schema
that the agno framework expects.
"""

import os
import sys
from sqlalchemy import create_engine, text
from agno.memory.v2.db.postgres import PostgresMemoryDb
from db.session import db_url

def initialize_memory_tables():
    """Initialize the memory tables for the competitive pricing agent."""
    
    print("Initializing memory tables...")
    
    # Create a PostgresMemoryDb instance
    memory_db = PostgresMemoryDb(
        table_name="competitive_pricing_chat_memory",
        db_url=db_url
    )
    
    # Check if the PostgresMemoryDb has a create_tables or similar method
    # This is what we need to investigate in the agno framework
    
    # For now, let's create a basic connection to check the existing tables
    engine = create_engine(db_url.replace('+asyncpg', '').replace('+aiopg', ''))
    
    with engine.connect() as conn:
        # Check if the table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'competitive_pricing_chat_memory'
            );
        """))
        table_exists = result.scalar()
        
        if table_exists:
            print("Table 'competitive_pricing_chat_memory' already exists.")
            
            # Check the actual schema
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'competitive_pricing_chat_memory'
                ORDER BY ordinal_position;
            """))
            
            print("\nCurrent table schema:")
            for row in result:
                print(f"  - {row[0]}: {row[1]}")
            
            print("\nWARNING: The existing table might not match the agno framework's expected schema.")
            print("Consider backing up and dropping the table to let the framework recreate it.")
        else:
            print("Table 'competitive_pricing_chat_memory' does not exist.")
            print("The agno framework should create it automatically when the agent runs.")
    
    # Try to access the memory_db to see if it has any initialization methods
    print("\nChecking PostgresMemoryDb attributes...")
    for attr in dir(memory_db):
        if not attr.startswith('_') and any(keyword in attr.lower() for keyword in ['create', 'init', 'table', 'setup']):
            print(f"  - {attr}")
    
    print("\nInitialization check complete.")

if __name__ == "__main__":
    initialize_memory_tables()