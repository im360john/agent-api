#!/usr/bin/env python3
"""
Test script for Slack Treez Agent with detailed performance logging.

Required environment variables:
- OPENAI_API_KEY: Your OpenAI API key
- DATABASE_URL: PostgreSQL connection string (optional, defaults to postgresql+psycopg://user:password@location/agno)
- SLACK_BOT_TOKEN: Slack bot token (optional, but needed for full Slack integration)
- FIRECRAWL_API_KEY: Firecrawl API key (optional, for knowledge base updates)

Usage:
    export OPENAI_API_KEY="your-key-here"
    export DATABASE_URL="postgresql+psycopg://user:password@localhost:5432/agno"  # Optional
    python3 test_slack_performance.py
"""

import asyncio
import time
import os
import sys
import logging
from datetime import datetime
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.slack_treez_agent import get_slack_treez_agent, SlackTreezBot

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('slack_agent_performance.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Create specific loggers for different components
perf_logger = logging.getLogger('performance')
agent_logger = logging.getLogger('agent')
db_logger = logging.getLogger('database')
kb_logger = logging.getLogger('knowledge_base')

class PerformanceTimer:
    """Context manager for timing operations"""
    def __init__(self, operation_name):
        self.operation_name = operation_name
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        perf_logger.info(f"[START] {self.operation_name}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        perf_logger.info(f"[END] {self.operation_name} - Duration: {duration:.2f}s")
        return False

async def test_slack_response():
    """Test the Slack agent response time with detailed logging"""
    
    # Test messages
    test_messages = [
        {
            "id": "promo_carousel",
            "text": "Good morning. Dr A's promo carousel is not displaying the discount names. It looks like everything is configured correctly in prismic. is there something that I'm over looking?",
            "description": "Complex technical support query"
        },
        {
            "id": "simple_query",
            "text": "How do I add a new product to Treez POS?",
            "description": "Simple how-to query"
        },
        {
            "id": "no_kb_query",
            "text": "What's the weather like today?",
            "description": "Query that should not use knowledge base"
        }
    ]
    
    # Check required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("\nERROR: OPENAI_API_KEY environment variable is required!")
        print("Please run: export OPENAI_API_KEY='your-key-here'")
        return
    
    # Log environment setup
    perf_logger.info("=" * 80)
    perf_logger.info("SLACK AGENT PERFORMANCE TEST")
    perf_logger.info("=" * 80)
    perf_logger.info(f"Test started at: {datetime.now()}")
    perf_logger.info(f"OpenAI API Key: {'Set' if os.getenv('OPENAI_API_KEY') else 'Not Set'}")
    perf_logger.info(f"Database URL: {'Set' if os.getenv('DATABASE_URL') else 'Using Default'}")
    perf_logger.info(f"Slack Bot Token: {'Set' if os.getenv('SLACK_BOT_TOKEN') else 'Not Set'}")
    perf_logger.info(f"Firecrawl API Key: {'Set' if os.getenv('FIRECRAWL_API_KEY') else 'Not Set'}")
    perf_logger.info("=" * 80)
    
    try:
        # Create agent with timing
        with PerformanceTimer("Agent Creation"):
            agent = get_slack_treez_agent(debug_mode=False)
            agent_logger.info(f"Agent created with model: gpt-4.1-mini")
            agent_logger.info(f"Knowledge base enabled: {agent.search_knowledge}")
            agent_logger.info(f"History runs: {agent.num_history_runs}")
            agent_logger.info(f"Agentic memory: {agent.enable_agentic_memory}")
        
        # Create bot wrapper
        with PerformanceTimer("Bot Wrapper Creation"):
            bot = SlackTreezBot(agent)
            agent_logger.info("SlackTreezBot wrapper created")
        
        # Test each message
        for test_case in test_messages:
            print(f"\n{'='*80}")
            print(f"Test Case: {test_case['description']}")
            print(f"Message: {test_case['text']}")
            print(f"{'='*80}")
            
            perf_logger.info(f"\n[TEST CASE] {test_case['id']} - {test_case['description']}")
            
            # Simulate Slack event
            event = {
                "text": f"<@bot> {test_case['text']}",
                "user": "test_user",
                "channel": f"test_channel_{test_case['id']}",
                "ts": str(time.time())
            }
            
            # Time the overall response
            with PerformanceTimer(f"Total Response Time - {test_case['id']}"):
                
                # Log the phases we expect
                phases = [
                    "Message preprocessing",
                    "Knowledge base search",
                    "LLM processing",
                    "Response generation"
                ]
                
                try:
                    # Process the mention
                    response = await bot.process_mention(event)
                    
                    # Log response details
                    agent_logger.info(f"Response length: {len(response)} characters")
                    agent_logger.info(f"Response preview: {response[:200]}...")
                    
                    print(f"\nResponse ({len(response)} chars):")
                    print("-" * 40)
                    print(response)
                    print("-" * 40)
                    
                except Exception as e:
                    agent_logger.error(f"Error processing message: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            # Add delay between tests
            await asyncio.sleep(2)
        
        # Summary statistics
        print("\n" + "="*80)
        print("PERFORMANCE SUMMARY")
        print("="*80)
        print("Check 'slack_agent_performance.log' for detailed timing breakdown")
        print("="*80)
        
    except Exception as e:
        perf_logger.error(f"Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_knowledge_base_search():
    """Isolated test for knowledge base search performance"""
    perf_logger.info("\n" + "="*80)
    perf_logger.info("KNOWLEDGE BASE SEARCH TEST")
    perf_logger.info("="*80)
    
    if not os.getenv("OPENAI_API_KEY"):
        return
    
    try:
        with PerformanceTimer("Agent Creation for KB Test"):
            agent = get_slack_treez_agent(debug_mode=False)
        
        # Test direct knowledge base search
        test_queries = [
            "promo carousel discount",
            "treez pos add product",
            "payment processing"
        ]
        
        for query in test_queries:
            with PerformanceTimer(f"Knowledge Base Search - '{query}'"):
                if hasattr(agent.knowledge, 'search'):
                    results = agent.knowledge.search(query, num_documents=3)
                    kb_logger.info(f"Found {len(results) if results else 0} documents for '{query}'")
                else:
                    kb_logger.warning("Knowledge base does not have search method")
                    
    except Exception as e:
        kb_logger.error(f"KB test failed: {str(e)}")

if __name__ == "__main__":
    print("\n" + "="*80)
    print("SLACK TREEZ AGENT PERFORMANCE TEST")
    print("="*80)
    print("\nRequired Environment Variables:")
    print("  export OPENAI_API_KEY='your-openai-api-key'")
    print("\nOptional Environment Variables:")
    print("  export DATABASE_URL='postgresql+psycopg://user:pass@host:port/db'")
    print("  export SLACK_BOT_TOKEN='xoxb-your-slack-bot-token'")
    print("  export FIRECRAWL_API_KEY='your-firecrawl-api-key'")
    print("\nStarting tests...\n")
    
    # Run main test
    asyncio.run(test_slack_response())
    
    # Run knowledge base test
    asyncio.run(test_knowledge_base_search())
    
    print("\nTest complete! Check 'slack_agent_performance.log' for detailed timing.")