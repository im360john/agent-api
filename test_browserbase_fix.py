#!/usr/bin/env python3
"""Test the fixed BrowserbaseTools implementation"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.browserbase_tools import BrowserbaseTools
from agents.competitive_pricing_agent import CompetitorPricingTools
from db.session import db_url


def test_browserbase_tools():
    """Test that BrowserbaseTools can be initialized"""
    print("Testing BrowserbaseTools initialization...")
    
    # Get credentials from CompetitorPricingTools
    pricing_tools = CompetitorPricingTools(db_url=db_url)
    
    try:
        # Initialize BrowserbaseTools
        browserbase = BrowserbaseTools(
            api_key=pricing_tools.browserbase_key,
            project_id=pricing_tools.browserbase_project
        )
        print("✓ BrowserbaseTools initialized successfully")
        print(f"  - API Key: {'*' * 10}{pricing_tools.browserbase_key[-4:]}")
        print(f"  - Project ID: {pricing_tools.browserbase_project}")
        print(f"  - Functions available: {len(browserbase.functions)}")
        for func in browserbase.functions:
            print(f"    - {func.name}")
        
        # Test navigate_to without connect_url
        print("\nTesting navigate_to function...")
        result = browserbase.navigate_to("https://example.com")
        print(f"Navigate result: {result}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error initializing BrowserbaseTools: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_creation():
    """Test that the agent can be created with BrowserbaseTools"""
    print("\n\nTesting agent creation with BrowserbaseTools...")
    
    try:
        from agents.competitive_pricing_agent import get_competitive_pricing_agent
        
        agent = get_competitive_pricing_agent(
            model_id="gpt-4o",
            user_id="test_user",
            session_id="test_session"
        )
        
        print("✓ Agent created successfully")
        print(f"  - Tools: {len(agent.tools)}")
        for tool in agent.tools:
            print(f"    - {tool.__class__.__name__}")
            
        # Check if BrowserbaseTools is included
        has_browserbase = any(
            'browserbase' in tool.__class__.__name__.lower() 
            for tool in agent.tools
        )
        
        if has_browserbase:
            print("✓ BrowserbaseTools is included in agent tools")
        else:
            print("✗ BrowserbaseTools not found in agent tools")
            
        return True
        
    except Exception as e:
        print(f"✗ Error creating agent: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("BrowserbaseTools Fix Test")
    print("=" * 60)
    
    # Test 1: BrowserbaseTools initialization
    test1_passed = test_browserbase_tools()
    
    # Test 2: Agent creation
    test2_passed = test_agent_creation()
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print(f"  - BrowserbaseTools init: {'PASSED' if test1_passed else 'FAILED'}")
    print(f"  - Agent creation: {'PASSED' if test2_passed else 'FAILED'}")
    print("=" * 60)