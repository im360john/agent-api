#!/usr/bin/env python3
"""Run the knowledge base migration"""

import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get database connection using environment variables"""
    db_config = {
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_DATABASE'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASS')
    }
    
    print(f"Connecting to database: {db_config['user']}@{db_config['host']}:{db_config['port']}/{db_config['database']}")
    
    # Remove None values
    db_config = {k: v for k, v in db_config.items() if v is not None}
    
    return psycopg2.connect(**db_config)

def run_migration():
    """Run the knowledge base migration"""
    
    # Read migration file
    with open('migrations/add_scraping_knowledge_base.sql', 'r') as f:
        migration_sql = f.read()
    
    # Connect and run migration
    try:
        conn = get_db_connection()
        cur = conn.cursor()
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        print("\nMake sure the following environment variables are set:")
        print("- DB_HOST")
        print("- DB_PORT") 
        print("- DB_DATABASE")
        print("- DB_USER")
        print("- DB_PASS")
        return
    
    try:
        print("Running knowledge base migration...")
        
        # First check if pgvector extension is available
        vector_available = False
        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            conn.commit()
            print("✅ pgvector extension enabled")
            vector_available = True
        except Exception as e:
            print(f"⚠️  Warning: Could not enable pgvector extension: {e}")
            print("   Vector search features will not be available")
            conn.rollback()
            
            # Remove vector-related parts from migration
            migration_sql = migration_sql.replace("embedding vector(1536)", "embedding TEXT")
            
            # Remove the entire CREATE INDEX statement for vector index
            import re
            migration_sql = re.sub(
                r'-- Create vector similarity index.*?\n.*?CREATE INDEX.*?idx_knowledge_base_embedding.*?\n.*?USING ivfflat.*?\n.*?WITH \(lists = 100\);',
                '-- Vector index skipped (pgvector not available)',
                migration_sql,
                flags=re.DOTALL
            )
        
        # Run the migration
        cur.execute(migration_sql)
        conn.commit()
        
        print("✅ Migration completed successfully!")
        
        # Verify tables were created
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'pricing' 
            AND table_name IN ('scraping_metrics', 'knowledge_base', 'user_corrections', 'learned_patterns')
            ORDER BY table_name;
        """)
        
        tables = cur.fetchall()
        print(f"\n📊 Created {len(tables)} tables:")
        for table in tables:
            print(f"   - pricing.{table[0]}")
        
        # Check if columns were added to price_history
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'pricing' 
            AND table_name = 'price_history'
            AND column_name IN ('scraping_confidence', 'price_confidence', 'stock_confidence', 
                               'scraping_tool', 'scraping_url', 'scraping_duration_ms');
        """)
        
        columns = cur.fetchall()
        if columns:
            print(f"\n✅ Added {len(columns)} columns to pricing.price_history")
        else:
            print("\n⚠️  Note: pricing.price_history table doesn't exist yet")
        
        if not vector_available:
            print("\n⚠️  pgvector is not installed. To enable vector search capabilities:")
            print("   1. Install pgvector: sudo apt install postgresql-15-pgvector")
            print("   2. Run: CREATE EXTENSION vector; in your database")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    run_migration()