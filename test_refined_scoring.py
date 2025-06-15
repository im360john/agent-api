#!/usr/bin/env python3
"""
Test refined scoring with new examples
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

async def test_refined_examples():
    """Test new examples with refined scoring"""
    print("Testing Refined Image Scoring")
    print("=" * 60)
    print("Focus: Brand details matter more than background")
    print("=" * 60)
    
    # Create agent
    agent = get_image_evaluator_agent(
        model_id="gpt-4o",
        debug_mode=False
    )
    
    # Test images
    test_cases = [
        {
            "url": "https://gomaryjones.com/wp-content/uploads/2023/12/MJ-OrangeCream-5mg-Can.png",
            "name": "Mary Jones Orange Cream",
            "expected": "50-65",
            "reason": "Real product with brand name and details on white background"
        },
        {
            "url": "https://findbreez.com/wp-content/uploads/2023/11/Breez-Extra-Strength-Tablets-Tin-Nighttime-V2-1-1.jpg",
            "name": "Breez Tablets",
            "expected": "50-65",
            "reason": "Professional product photo with clear branding"
        },
        {
            "url": "https://weedmaps.com/images/products/000/627/369/avatar/1747418418-sauce_dual_color_ecommerce_1-25g_v25_1_ghost_train_haze_1.png?auto=format&fit=fill&fill=solid&fill-color=fff&w=540&h=540&blend-mode=darken&blend-color=%23F9F9F8",
            "name": "Sauce Ghost Train Haze",
            "expected": "55-70",
            "reason": "E-commerce product photo with strain name and details"
        },
        {
            "url": "https://rawgarden.farm/wp-content/uploads/2024/09/Sauce-Cartridge-Website-Image-w-NEW-Icon.png",
            "name": "Raw Garden (Previous Example)",
            "expected": "50-60",
            "reason": "Should score higher now - has brand and product visible"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}: {test['name']}")
        print(f"Expected: {test['expected']}")
        print(f"Reason: {test['reason']}")
        print("-" * 60)
        
        query = f"""
        Use analyze_authenticity_strict to evaluate: {test['url']}
        
        Remember the new scoring system:
        - Base score = 40
        - Brand name visible = +20
        - Product/strain name = +15
        - THC/CBD info = +15
        - Real surface/hand = +10
        
        White background is OK if product details are visible!
        """
        
        try:
            response = await agent.arun(query)
            print("\nAnalysis:")
            print(response.content)
        except Exception as e:
            print(f"\nError: {e}")
    
    # Quick batch test
    print("\n" + "="*60)
    print("QUICK BATCH TEST")
    print("-" * 60)
    
    batch_query = """
    Use quick_evaluate on these three images:
    1. https://gomaryjones.com/wp-content/uploads/2023/12/MJ-OrangeCream-5mg-Can.png
    2. https://findbreez.com/wp-content/uploads/2023/11/Breez-Extra-Strength-Tablets-Tin-Nighttime-V2-1-1.jpg
    3. https://weedmaps.com/images/products/000/627/369/avatar/1747418418-sauce_dual_color_ecommerce_1-25g_v25_1_ghost_train_haze_1.png
    
    All three should score 50-70 as professional product photos with clear branding.
    """
    
    try:
        response = await agent.arun(batch_query)
        print("\nBatch Results:")
        print(response.content)
    except Exception as e:
        print(f"\nError: {e}")
    
    print("\n" + "="*60)
    print("KEY SCORING PRINCIPLES:")
    print("- Brand name visible = MINIMUM 50 score")
    print("- White background OK for e-commerce")
    print("- Focus on product details, not just setting")
    print("- Professional product photos = 50-70")
    print("- Amateur authentic photos = 55-75")
    print("- Dispensary photos = 70-95")

if __name__ == "__main__":
    asyncio.run(test_refined_examples())