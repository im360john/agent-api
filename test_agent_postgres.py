#!/usr/bin/env python3
"""
Test agents with PostgreSQL database
"""
import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import agents
from agents.web_agent import get_web_agent
from agents.finance_agent import get_finance_agent
from agents.image_evaluator_agent import get_image_evaluator_agent

async def test_web_agent():
    """Test web agent with PostgreSQL"""
    print("\n=== Testing Web Agent with PostgreSQL ===")
    print("-" * 50)
    
    agent = get_web_agent(
        model_id="gpt-4o-mini",
        user_id="test_user",
        session_id="test_session",
        debug_mode=True
    )
    
    query = "What is the latest news about artificial intelligence?"
    print(f"Query: {query}")
    
    try:
        response = await agent.arun(query)
        print(f"\nResponse: {response.content[:500]}...")
        print("\n✅ Web Agent working with PostgreSQL!")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

async def test_finance_agent():
    """Test finance agent with PostgreSQL"""
    print("\n\n=== Testing Finance Agent with PostgreSQL ===")
    print("-" * 50)
    
    agent = get_finance_agent(
        model_id="gpt-4o-mini",
        user_id="test_user",
        session_id="test_session",
        debug_mode=True
    )
    
    query = "What is the current price of TSLA?"
    print(f"Query: {query}")
    
    try:
        response = await agent.arun(query)
        print(f"\nResponse: {response.content[:500]}...")
        print("\n✅ Finance Agent working with PostgreSQL!")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

async def test_image_agent():
    """Test image evaluator agent with PostgreSQL"""
    print("\n\n=== Testing Image Evaluator Agent with PostgreSQL ===")
    print("-" * 50)
    
    agent = get_image_evaluator_agent(
        model_id="gpt-4o-mini",
        user_id="test_user",
        session_id="test_session",
        debug_mode=True
    )
    
    query = "Please evaluate this image: https://picsum.photos/800/600"
    print(f"Query: {query}")
    
    try:
        response = await agent.arun(query)
        print(f"\nResponse: {response.content[:500]}...")
        print("\n✅ Image Evaluator Agent working with PostgreSQL!")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

async def main():
    """Main test function"""
    print("Testing Agents with PostgreSQL Database")
    print("=" * 50)
    
    # Check database configuration
    print("\nDatabase Configuration:")
    print(f"DB_USER: {os.getenv('DB_USER')}")
    print(f"DB_DATABASE: {os.getenv('DB_DATABASE')}")
    print(f"DB_HOST: {os.getenv('DB_HOST')}")
    print(f"DB_PORT: {os.getenv('DB_PORT')}")
    
    # Test connection
    from db.session import db_url
    print(f"\nDatabase URL: {db_url.replace(os.getenv('DB_PASS', ''), '***')}")
    
    # Run tests
    await test_web_agent()
    await test_finance_agent()
    await test_image_agent()
    
    print("\n" + "=" * 50)
    print("Testing complete!")

if __name__ == "__main__":
    # Check environment
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set")
        sys.exit(1)
    
    if not os.getenv("DB_USER"):
        print("Error: Database credentials not set")
        print("Please ensure .env file is loaded")
        sys.exit(1)
    
    asyncio.run(main())