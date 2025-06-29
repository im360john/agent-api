#!/usr/bin/env python3
"""Test chat functionality locally"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.routes.chat_ui_fixed import create_pricing_agent

async def test_agent():
    """Test agent creation and basic functionality"""
    try:
        # Test creating agent with Claude
        print("Testing Claude agent creation...")
        claude_agent = create_pricing_agent("claude-sonnet-4-20250514")
        print("✓ Claude agent created successfully")
        
        # Test creating agent with GPT-4o
        print("\nTesting GPT-4o agent creation...")
        gpt_agent = create_pricing_agent("gpt-4o")
        print("✓ GPT-4o agent created successfully")
        
        # Test a simple query
        print("\nTesting agent response...")
        response = await claude_agent.arun("Hello, can you help me check prices?")
        print(f"✓ Agent responded: {response.content[:100]}...")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent())