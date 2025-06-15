#!/usr/bin/env python3
"""
Test that URL/source doesn't influence scoring
"""
import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the agent
from agents.image_evaluator_agent import get_image_evaluator_agent

async def test_url_bias():
    """Test that URL doesn't influence scoring"""
    print("Testing URL Bias Prevention")
    print("=" * 60)
    print("The agent should IGNORE where images are hosted")
    print("=" * 60)
    
    # Create agent
    agent = get_image_evaluator_agent(
        model_id="gpt-4o",
        debug_mode=False
    )
    
    # Generic product that should score low regardless of source
    generic_vape_url = "https://images.dutchie.com/9cf116e9b4ad0014ab3c4c950c630b03?auto=format%2Ccompress&cs=srgb&fit=max&fill=solid&fillColor=%23fff&w=410&ixlib=react-9.8.1"
    
    print(f"\nTesting Generic Vape Image")
    print(f"URL: {generic_vape_url[:50]}...")
    print("Expected Score: 10-30 (generic product, no brand visible)")
    print("-" * 60)
    
    query = f"""
    Use analyze_authenticity_strict to evaluate: {generic_vape_url}
    
    CRITICAL REMINDERS:
    - IGNORE that this is from dutchie.com
    - ONLY score based on what you SEE in the image
    - If no brand/details are visible = 10-30 score
    - Generic products are stock photos regardless of source
    
    Look for:
    - Is there a visible brand name? (If NO, score 10-30)
    - Are there product details? (If NO, score 10-30)
    - Is it just a generic vape/product? (If YES, score 10-30)
    """
    
    try:
        response = await agent.arun(query)
        print("\nAnalysis:")
        print(response.content)
        
        # Check if score is in correct range
        content = response.content.lower()
        if "10" in content or "20" in content or "30" in content:
            print("\n✅ CORRECT: Scored in 10-30 range")
        else:
            print("\n❌ ERROR: Score too high! Generic products should be 10-30")
            
    except Exception as e:
        print(f"\nError: {e}")
    
    # Test multiple generic products
    print("\n" + "="*60)
    print("BATCH TEST: Generic Products from Various Sources")
    print("-" * 60)
    
    batch_query = """
    Use quick_evaluate to check if these are generic stock photos:
    
    1. Generic vape from Dutchie: https://images.dutchie.com/9cf116e9b4ad0014ab3c4c950c630b03
    2. Raw Garden from brand site: https://rawgarden.farm/wp-content/uploads/2024/09/Sauce-Cartridge-Website-Image-w-NEW-Icon.png
    
    Remember:
    - IGNORE the source URL
    - Generic product with no visible brand = 10-30
    - Product with visible brand = 50+
    
    The first should score 10-30 (no brand visible)
    The second should score 50-60 (Raw Garden brand visible)
    """
    
    try:
        response = await agent.arun(batch_query)
        print("\nBatch Results:")
        print(response.content)
    except Exception as e:
        print(f"\nError: {e}")
    
    print("\n" + "="*60)
    print("KEY PRINCIPLE:")
    print("A generic product on a legitimate website is STILL a stock photo!")
    print("Only visible brand/product details justify higher scores.")

if __name__ == "__main__":
    asyncio.run(test_url_bias())