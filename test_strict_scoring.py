#!/usr/bin/env python3
"""
Test strict scoring on specific images
"""
import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the strict scoring agent
from agents.image_evaluator_agent import get_image_evaluator_agent

async def test_images():
    """Test the two specific images with strict scoring"""
    print("Strict Image Authenticity Testing")
    print("=" * 60)
    
    # Create agent
    agent = get_image_evaluator_agent(
        model_id="gpt-4o",
        debug_mode=False
    )
    
    # Test images
    images = [
        {
            "url": "https://rawgarden.farm/wp-content/uploads/2024/09/Sauce-Cartridge-Website-Image-w-NEW-Icon.png",
            "name": "Raw Garden Website Image",
            "expected": "30-50 (stock photo style)"
        },
        {
            "url": "https://images.dutchie.com/42ebd731b4a374f2260bab845a3e32ce?w=1200&auto=format",
            "name": "Dutchie Dispensary Image", 
            "expected": "85-95 (authentic product)"
        }
    ]
    
    for img in images:
        print(f"\n{'='*60}")
        print(f"Testing: {img['name']}")
        print(f"Expected Score: {img['expected']}")
        print(f"URL: {img['url']}")
        print("-" * 60)
        
        query = f"""
        Use the analyze_authenticity_strict tool to evaluate this image: {img['url']}
        
        Be VERY CRITICAL. Look for:
        - Background type (white = bad)
        - Product placement (floating = bad)
        - Context (none = bad)
        
        Follow the scoring rules strictly.
        """
        
        try:
            response = await agent.arun(query)
            print("\nAnalysis:")
            print(response.content)
        except Exception as e:
            print(f"\nError: {e}")
    
    # Quick comparison
    print("\n" + "="*60)
    print("Quick Comparison Test")
    print("-" * 60)
    
    query = """
    Compare these two images using the quick_evaluate tool:
    1. https://rawgarden.farm/wp-content/uploads/2024/09/Sauce-Cartridge-Website-Image-w-NEW-Icon.png
    2. https://images.dutchie.com/42ebd731b4a374f2260bab845a3e32ce?w=1200&auto=format
    
    The first should score LOW (stock photo), the second HIGH (authentic).
    """
    
    try:
        response = await agent.arun(query)
        print("\nComparison:")
        print(response.content)
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    asyncio.run(test_images())