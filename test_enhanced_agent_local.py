#!/usr/bin/env python3
"""Test the enhanced competitive pricing agent locally"""

import asyncio
import logging
from datetime import datetime, timezone
from agents.competitive_pricing_agent_enhanced import create_enhanced_agent, EnhancedCompetitorPricingTools
from db.session import db_url

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_enhanced_features():
    """Test the enhanced features of the agent"""
    
    print("🚀 Testing Enhanced Competitive Pricing Agent\n")
    
    # Create the agent
    agent = create_enhanced_agent()
    
    # Create tools instance for direct testing
    tools = EnhancedCompetitorPricingTools(db_url=db_url)
    
    # Test 1: Check prices with enhanced logging
    print("=" * 80)
    print("TEST 1: Price check with detailed logging")
    print("=" * 80)
    
    result = await tools.check_prices(
        product_name="Wyld Elderberry Gummies",
        brand="Wyld"
    )
    print(result)
    
    # Test 2: View scraping confidence
    print("\n" + "=" * 80)
    print("TEST 2: View scraping confidence metrics")
    print("=" * 80)
    
    confidence_report = await tools.view_scraping_confidence(
        product_name="Wyld",
        days=1
    )
    print(confidence_report)
    
    # Test 3: Analyze scraping performance
    print("\n" + "=" * 80)
    print("TEST 3: Analyze scraping performance")
    print("=" * 80)
    
    performance_analysis = await tools.analyze_scraping_performance()
    print(performance_analysis)
    
    # Test 4: Test user correction
    print("\n" + "=" * 80)
    print("TEST 4: Record a user correction")
    print("=" * 80)
    
    # First, let's simulate a scenario where the user corrects a price
    correction_result = await tools.record_user_correction(
        product_name="Wyld Elderberry Gummies",
        competitor_name="Harborside",
        correction_type="price",
        original_value="20.00",
        corrected_value="18.00",
        user_id="test_user",
        session_id="test_session"
    )
    print(correction_result)
    
    # Test 5: Check how corrections affect confidence
    print("\n" + "=" * 80)
    print("TEST 5: View confidence after correction")
    print("=" * 80)
    
    confidence_after = await tools.view_scraping_confidence(
        product_name="Wyld Elderberry",
        competitor_name="Harborside",
        days=1
    )
    print(confidence_after)

async def test_agent_conversation():
    """Test the agent in a conversational context"""
    
    print("\n\n" + "=" * 80)
    print("TEST 6: Agent conversation with enhanced features")
    print("=" * 80)
    
    agent = create_enhanced_agent()
    
    # Simulate conversation
    messages = [
        "Check prices for Wyld Raspberry Gummies and tell me about the scraping confidence",
        "The price at Elemental Wellness should be $22, not what you found. Can you record this correction?",
        "Show me the scraping performance analysis for all competitors"
    ]
    
    for i, message in enumerate(messages, 1):
        print(f"\n🧑 User: {message}")
        
        response = await agent.run(
            message=message,
            user_id="test_user",
            session_id=f"enhanced_test_{i}"
        )
        
        print(f"\n🤖 Agent: {response.content}")

async def main():
    """Run all tests"""
    try:
        # Run enhanced feature tests
        await test_enhanced_features()
        
        # Run conversational tests
        await test_agent_conversation()
        
        print("\n\n✅ All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())