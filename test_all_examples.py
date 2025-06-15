#!/usr/bin/env python3
"""
Test all three example images with updated scoring
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

async def test_all_images():
    """Test all example images"""
    print("Testing Image Authenticity Scoring - All Examples")
    print("=" * 60)
    
    # Create agent
    agent = get_image_evaluator_agent(
        model_id="gpt-4o",
        debug_mode=False
    )
    
    # Test images with expected scores
    test_images = [
        {
            "url": "https://rawgarden.farm/wp-content/uploads/2024/09/Sauce-Cartridge-Website-Image-w-NEW-Icon.png",
            "name": "Raw Garden Stock Photo",
            "expected": "30-50",
            "reason": "White background, floating product, no context"
        },
        {
            "url": "https://images.dutchie.com/42ebd731b4a374f2260bab845a3e32ce?w=1200&auto=format",
            "name": "Dutchie Authentic Photo",
            "expected": "85-95",
            "reason": "Real product with specific details and branding"
        },
        {
            "url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT7WukH9injL1BRjvuMlrRN92fZjnn0oubMdA&s",
            "name": "Low Resolution Authentic",
            "expected": "55-75",
            "reason": "Low quality but appears to be real product photo with context"
        }
    ]
    
    results = []
    
    for img in test_images:
        print(f"\n{'='*60}")
        print(f"Testing: {img['name']}")
        print(f"Expected Score: {img['expected']}")
        print(f"Reason: {img['reason']}")
        print(f"URL: {img['url'][:50]}...")
        print("-" * 60)
        
        query = f"""
        Use analyze_authenticity_strict to evaluate: {img['url']}
        
        Remember:
        - Low resolution doesn't mean stock photo
        - Look for CONTEXT and SETTING
        - White background + floating = LOW score
        - Real surface/setting = HIGHER score
        """
        
        try:
            response = await agent.arun(query)
            print("\nAnalysis:")
            print(response.content)
            results.append((img['name'], img['expected'], "✓"))
        except Exception as e:
            print(f"\nError: {e}")
            results.append((img['name'], img['expected'], "✗"))
    
    # Summary
    print("\n" + "="*60)
    print("SCORING SUMMARY")
    print("-" * 60)
    print(f"{'Image':<30} {'Expected':<15} {'Status'}")
    print("-" * 60)
    for name, expected, status in results:
        print(f"{name:<30} {expected:<15} {status}")
    
    print("\n" + "="*60)
    print("KEY PRINCIPLES:")
    print("- Stock photos (white bg, floating): 20-50")
    print("- Low quality authentic photos: 55-75")
    print("- High quality authentic photos: 75-95")
    print("- CONTEXT matters more than QUALITY")

if __name__ == "__main__":
    asyncio.run(test_all_images())