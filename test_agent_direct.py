#!/usr/bin/env python3
"""
Test agents directly without running the API server
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Mock the database modules to avoid connection errors
import types

# Create mock db module
mock_db = types.ModuleType('db')
mock_session = types.ModuleType('session')
mock_session.db_url = "sqlite:///./test.db"  # Use SQLite for testing
mock_db.session = mock_session
sys.modules['db'] = mock_db
sys.modules['db.session'] = mock_session

# Now import agents
from agents.web_agent import get_web_agent
from agents.finance_agent import get_finance_agent
from agents.image_evaluator_agent import get_image_evaluator_agent
from agents.agno_assist import get_agno_assist_agent

def test_web_agent():
    """Test the web search agent"""
    print("\n=== Testing Web Search Agent ===")
    
    # Create agent without database
    agent = get_web_agent(
        model_id="gpt-4o-mini",  # Use a cheaper model for testing
        debug_mode=True
    )
    
    # Test a simple query
    query = "What is the weather in Tokyo today?"
    print(f"Query: {query}")
    
    # Run the agent
    try:
        response = agent.run(query)
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"Error: {e}")
        print("Note: The agent may fail due to missing database connections")

def test_finance_agent():
    """Test the finance agent"""
    print("\n=== Testing Finance Agent ===")
    
    agent = get_finance_agent(
        model_id="gpt-4o-mini",
        debug_mode=True
    )
    
    query = "What is the current stock price of AAPL?"
    print(f"Query: {query}")
    
    try:
        response = agent.run(query)
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"Error: {e}")

def test_image_evaluator():
    """Test the image evaluator agent"""
    print("\n=== Testing Image Evaluator Agent ===")
    
    agent = get_image_evaluator_agent(
        model_id="gpt-4o-mini",
        debug_mode=True
    )
    
    # You would need an actual image path here
    query = "Please analyze this image"
    print(f"Query: {query}")
    print("Note: This agent requires an actual image file to work properly")

def main():
    """Main function to test agents"""
    print("Testing Agents Directly")
    print("=" * 50)
    
    # Check if required environment variables are set
    required_vars = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Error: Missing environment variables: {missing_vars}")
        print("Please set them in your .env file")
        return
    
    # Select which agent to test
    print("\nAvailable agents:")
    print("1. Web Search Agent")
    print("2. Finance Agent")
    print("3. Image Evaluator Agent")
    print("4. Run all tests")
    
    choice = input("\nSelect an agent to test (1-4): ")
    
    if choice == "1":
        test_web_agent()
    elif choice == "2":
        test_finance_agent()
    elif choice == "3":
        test_image_evaluator()
    elif choice == "4":
        test_web_agent()
        test_finance_agent()
        test_image_evaluator()
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()