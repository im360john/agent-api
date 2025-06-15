"""Test the enhanced image evaluator with the ideal product image"""

import asyncio
import os
from unittest.mock import MagicMock
import sys

# Mock the database modules before importing
sys.modules['db.session'] = MagicMock()
sys.modules['db.session'].db_url = "sqlite:///test.db"

from agents.image_evaluator_agent import get_image_evaluator_agent

async def test_enhanced_evaluator():
    """Test the enhanced scoring system"""
    
    # Set up API key
    os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', 'your-openai-key-here')
    
    # The ideal image URL
    ideal_image_url = "https://content.sunnyside.shop/1c6bfdf6-614f-445e-b61c-cd2b9331783a.jpeg"
    
    # Create agent without database dependencies
    agent = get_image_evaluator_agent(
        model_id="gpt-4o",
        debug_mode=True
    )
    
    print("Testing Enhanced Image Evaluator")
    print("=" * 80)
    print(f"Testing ideal product image: {ideal_image_url}")
    print("\nExpected characteristics:")
    print("- Clean layout with professional presentation")
    print("- Bold brand visibility")
    print("- Clear packaging details")
    print("- Inner product inclusion (showing what's inside)")
    print("- Clearly defined product name")
    print("\nExpected score: 75-90 (IDEAL PRODUCT SHOT category)")
    print("=" * 80)
    
    # Test 1: Detailed analysis
    print("\n1. DETAILED ANALYSIS using analyze_authenticity_strict:")
    prompt1 = f"""Please analyze this cannabis product image using the analyze_authenticity_strict tool:

{ideal_image_url}

After getting the criteria, evaluate the image and provide:
1. What you see in the image
2. Score based on the strict criteria
3. Justification for the score
"""
    
    response1 = await agent.arun(prompt1)
    print(response1.content)
    
    print("\n" + "=" * 80)
    
    # Test 2: Quick evaluation
    print("\n2. QUICK EVALUATION using quick_evaluate:")
    prompt2 = f"""Now do a quick evaluation of the same image using the quick_evaluate tool:

{ideal_image_url}

Focus on identifying if this meets the IDEAL PRODUCT SHOT criteria.
"""
    
    response2 = await agent.arun(prompt2)
    print(response2.content)
    
    print("\n" + "=" * 80)
    
    # Test 3: Compare with a generic stock photo
    print("\n3. COMPARISON TEST - Generic stock photo:")
    generic_url = "https://example.com/generic-vape-pen.jpg"  # This won't load but shows scoring
    
    prompt3 = f"""For comparison, evaluate this URL which represents a generic product with no brand visible:

{generic_url}

This should score much lower (10-30) as a generic stock photo.
"""
    
    response3 = await agent.arun(prompt3)
    print(response3.content)

if __name__ == "__main__":
    # Check for API key
    if not os.getenv('OPENAI_API_KEY'):
        print("ERROR: Please set OPENAI_API_KEY environment variable")
        print("export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)
    
    asyncio.run(test_enhanced_evaluator())