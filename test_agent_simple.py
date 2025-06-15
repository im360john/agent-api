#!/usr/bin/env python3
"""
Simple agent testing without database dependencies
"""
import os
import sys
import types
from dotenv import load_dotenv
from textwrap import dedent

# Load environment variables
load_dotenv()

# Mock db module before importing image evaluator
mock_db = types.ModuleType('db')
mock_session = types.ModuleType('session')
mock_session.db_url = "sqlite:///./test.db"
mock_db.session = mock_session
sys.modules['db'] = mock_db
sys.modules['db.session'] = mock_session

# Import required Agno components
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools

from agents.image_evaluator_agent import ImageEvaluatorTools

def create_simple_web_agent():
    """Create a simple web search agent without database"""
    return Agent(
        name="Simple Web Agent",
        model=OpenAIChat(id="gpt-4o-mini"),
        tools=[DuckDuckGoTools()],
        description="A simple web search agent",
        instructions=dedent("""
            You are a helpful web search assistant.
            Use the search tool to find information and provide clear answers.
            Always cite your sources.
        """),
        markdown=True,
        debug_mode=True,
        # Disable features that require database
        storage=None,
        memory=None,
        add_history_to_messages=False,
    )

def create_simple_finance_agent():
    """Create a simple finance agent without database"""
    return Agent(
        name="Simple Finance Agent",
        model=OpenAIChat(id="gpt-4o-mini"),
        tools=[YFinanceTools(enable_all=True)],
        description="A simple finance agent",
        instructions=dedent("""
            You are a helpful finance assistant.
            Use the yfinance tools to get stock information.
            Provide clear financial insights.
        """),
        markdown=True,
        debug_mode=True,
        storage=None,
        memory=None,
        add_history_to_messages=False,
    )

def create_simple_image_agent():
    """Create a simple image evaluator agent without database"""
    return Agent(
        name="Simple Image Evaluator",
        model=OpenAIChat(id="gpt-4o-mini"),
        tools=[ImageEvaluatorTools()],
        description="A simple image evaluation agent",
        instructions=dedent("""
            You are an image quality evaluator.
            Use the tools to analyze images for quality, authenticity, and compliance.
            Provide clear evaluation results with scores and recommendations.
        """),
        markdown=True,
        debug_mode=True,
        storage=None,
        memory=None,
        add_history_to_messages=False,
    )

def test_agent(agent, query):
    """Test an agent with a query"""
    print(f"\nQuery: {query}")
    print("-" * 50)
    
    try:
        # Run the agent
        response = agent.run(query)
        print(f"\nResponse:\n{response.content}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

def main():
    # Check environment
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set in environment")
        return
    
    print("Simple Agent Testing")
    print("=" * 50)
    
    # Test web agent
    print("\n1. Testing Web Search Agent")
    web_agent = create_simple_web_agent()
    test_agent(web_agent, "What are the latest AI developments in 2024?")
    
    # Test finance agent
    print("\n\n2. Testing Finance Agent")
    finance_agent = create_simple_finance_agent()
    test_agent(finance_agent, "What is the current price and PE ratio of AAPL?")
    
    # Test image evaluator agent
    print("\n\n3. Testing Image Evaluator Agent")
    image_agent = create_simple_image_agent()
    test_agent(image_agent, "Please evaluate this image for quality: https://picsum.photos/800/600")

if __name__ == "__main__":
    main()