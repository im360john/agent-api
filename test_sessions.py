#!/usr/bin/env python3
"""Test script to check session storage"""

import os
import sys
from sqlalchemy import create_engine, text
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.session import db_url

def check_tables():
    """Check what tables exist and their contents"""
    engine = create_engine(db_url.replace('+asyncpg', '').replace('+aiopg', ''))
    
    with engine.connect() as conn:
        # Check what tables exist
        print("=== Checking existing tables ===")
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%competitive%'
            ORDER BY table_name;
        """))
        
        tables = result.fetchall()
        print("Found tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
        print("\n=== Checking competitive_pricing_chat_agents table ===")
        try:
            result = conn.execute(text("SELECT COUNT(*) FROM competitive_pricing_chat_agents"))
            count = result.scalar()
            print(f"Total rows: {count}")
            
            if count > 0:
                result = conn.execute(text("""
                    SELECT session_id, user_id, agent_id, created_at 
                    FROM competitive_pricing_chat_agents 
                    ORDER BY created_at DESC 
                    LIMIT 5
                """))
                print("\nLatest sessions:")
                for row in result:
                    print(f"  Session: {row[0]}, User: {row[1]}, Agent: {row[2]}, Created: {row[3]}")
        except Exception as e:
            print(f"Error reading agents table: {e}")
        
        print("\n=== Checking competitive_pricing_chat_memory table ===")
        try:
            result = conn.execute(text("SELECT COUNT(*) FROM competitive_pricing_chat_memory"))
            count = result.scalar()
            print(f"Total rows: {count}")
            
            if count > 0:
                result = conn.execute(text("""
                    SELECT DISTINCT session_id, user_id, COUNT(*) as msg_count
                    FROM competitive_pricing_chat_memory 
                    GROUP BY session_id, user_id
                    ORDER BY MAX(created_at) DESC 
                    LIMIT 5
                """))
                print("\nLatest sessions with message counts:")
                for row in result:
                    print(f"  Session: {row[0]}, User: {row[1]}, Messages: {row[2]}")
        except Exception as e:
            print(f"Error reading memory table: {e}")

if __name__ == "__main__":
    check_tables()