#!/usr/bin/env python3
"""
Test edge cases: flower, non-cannabis, generic products
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

async def test_edge_cases():
    """Test special cases in image evaluation"""
    print("Testing Edge Cases in Image Evaluation")
    print("=" * 60)
    
    # Create agent
    agent = get_image_evaluator_agent(
        model_id="gpt-4o",
        debug_mode=False
    )
    
    # Test cases
    test_cases = [
        {
            "url": "https://meadow.imgix.net/2023/10/313df5e6-e34f-4512-a96b-b5ead721f206.jpeg?aspect=1&auto=format%2Ccompress&fit=crop&w=3840&h=3840&q=35",
            "name": "Cannabis Flower",
            "expected": "45-60",
            "reason": "Cannabis flower - no packaging/branding expected"
        },
        {
            "url": "https://images.squarespace-cdn.com/content/v1/64c1553ea125c311a64afe56/71f61a4f-7ed9-4d83-b460-c229ac7a642a/Color+splash.png",
            "name": "Non-Cannabis Image",
            "expected": "0-10",
            "reason": "Not a cannabis product - should be rejected"
        },
        {
            "url": "https://images.dutchie.com/9cf116e9b4ad0014ab3c4c950c630b03?auto=format%2Ccompress&cs=srgb&fit=max&fill=solid&fillColor=%23fff&w=410&ixlib=react-9.8.1",
            "name": "Generic Vape/Product",
            "expected": "10-30",
            "reason": "Generic product with no brand or details"
        }
    ]
    
    print("Special scoring rules:")
    print("- Non-cannabis items: 0-10")
    print("- Cannabis flower: 45-75")
    print("- Generic products: 10-30")
    print("- Branded products: 50+")
    print("=" * 60)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}: {test['name']}")
        print(f"Expected: {test['expected']}")
        print(f"Reason: {test['reason']}")
        print("-" * 60)
        
        query = f"""
        Use analyze_authenticity_strict to evaluate: {test['url']}
        
        Apply the special case rules:
        1. Check if it's even cannabis first
        2. If it's flower, score 45-60 (no branding expected)
        3. If it's generic with no details, score 10-30
        4. If it's not cannabis at all, score 0-10
        """
        
        try:
            response = await agent.arun(query)
            print("\nAnalysis:")
            print(response.content)
        except Exception as e:
            print(f"\nError: {e}")
    
    # Quick evaluation test
    print("\n" + "="*60)
    print("QUICK EVALUATION TEST")
    print("-" * 60)
    
    quick_query = """
    Use quick_evaluate on these three edge cases:
    
    1. Cannabis flower: https://meadow.imgix.net/2023/10/313df5e6-e34f-4512-a96b-b5ead721f206.jpeg
    2. Non-cannabis: https://images.squarespace-cdn.com/content/v1/64c1553ea125c311a64afe56/71f61a4f-7ed9-4d83-b460-c229ac7a642a/Color+splash.png
    3. Generic product: https://images.dutchie.com/9cf116e9b4ad0014ab3c4c950c630b03
    
    Expected scores:
    1. Flower: 45-60 (special case)
    2. Non-cannabis: 0-10 (reject)
    3. Generic: 10-30 (no brand)
    """
    
    try:
        response = await agent.arun(quick_query)
        print("\nQuick Evaluation Results:")
        print(response.content)
    except Exception as e:
        print(f"\nError: {e}")
    
    print("\n" + "="*60)
    print("SCORING SUMMARY:")
    print("0-10:  Not cannabis")
    print("10-30: Generic cannabis, no brand")
    print("45-60: Cannabis flower (no packaging)")
    print("50-70: Branded products")
    print("70-95: Authentic context photos")

if __name__ == "__main__":
    asyncio.run(test_edge_cases())