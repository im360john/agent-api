#!/usr/bin/env python3
"""
Test the image evaluator with specific example images
"""
import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the improved agent
from agents.image_evaluator_agent import get_image_evaluator_agent

async def test_specific_images():
    """Test with the two specific example images"""
    print("Testing Image Evaluator with Specific Examples")
    print("=" * 60)
    
    # Create agent with vision model
    agent = get_image_evaluator_agent(
        model_id="gpt-4o",  # Vision-capable model
        user_id="test_user",
        session_id="test_session",
        debug_mode=False
    )
    
    # Test cases with expected scores
    test_cases = [
        {
            "url": "https://rawgarden.farm/wp-content/uploads/2024/09/Sauce-Cartridge-Website-Image-w-NEW-Icon.png",
            "expected_score": "30-50",
            "description": "Raw Garden website image - generic stock photo style",
            "notes": "Perfect white background, floating product, no context"
        },
        {
            "url": "https://images.dutchie.com/42ebd731b4a374f2260bab845a3e32ce?w=1200&auto=format",
            "expected_score": "85-95",
            "description": "Dutchie dispensary image - authentic product photo",
            "notes": "Real product with specific branding and details"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}: {test['description']}")
        print(f"URL: {test['url']}")
        print(f"Expected Score: {test['expected_score']}")
        print(f"Notes: {test['notes']}")
        print("-" * 60)
        
        # Use the vision analysis tool
        query = f"""
        Please analyze this cannabis product image for authenticity using your vision capabilities: {test['url']}
        
        Use the analyze_image_with_vision tool to:
        1. Look at the actual image content
        2. Score its authenticity from 1-100
        3. Identify specific visual elements that indicate stock photo vs real product
        4. Pay special attention to:
           - Background (perfect white vs realistic setting)
           - Product presentation (floating vs natural placement)
           - Branding specificity (generic vs specific brand details)
           - Overall realism
        
        Be critical and accurate in your assessment. This image should score around {test['expected_score']}.
        """
        
        try:
            response = await agent.arun(query)
            print("\nAgent Analysis:")
            print(response.content)
            
            # Extract score if mentioned
            content = response.content.lower()
            if "score:" in content or "authenticity score:" in content:
                print("\n✅ Score provided")
            else:
                print("\n⚠️  No clear score found in response")
                
        except Exception as e:
            print(f"\n❌ Error: {type(e).__name__}: {e}")
    
    print("\n" + "="*60)
    print("Testing complete!")
    print("\nKey differences to look for:")
    print("- Raw Garden image: Perfect white background, floating product, no context = LOW score (30-50)")
    print("- Dutchie image: Real product photo with specific details = HIGH score (85-95)")

async def test_comprehensive_evaluation():
    """Test comprehensive evaluation on both images"""
    print("\n\nTesting Comprehensive Evaluation")
    print("=" * 60)
    
    agent = get_image_evaluator_agent(
        model_id="gpt-4o",
        debug_mode=False
    )
    
    query = """
    Please perform a comprehensive evaluation of these two cannabis product images:
    
    1. https://rawgarden.farm/wp-content/uploads/2024/09/Sauce-Cartridge-Website-Image-w-NEW-Icon.png
    2. https://images.dutchie.com/42ebd731b4a374f2260bab845a3e32ce?w=1200&auto=format
    
    Use evaluate_image_comprehensive for each and compare:
    - Quality scores
    - Compliance scores  
    - Authenticity scores (be very critical here)
    - Overall validity
    
    The first image should score much lower on authenticity (30-50) as it's a generic stock-style photo.
    The second should score much higher (85-95) as it's an authentic product photo.
    """
    
    try:
        response = await agent.arun(query)
        print("\nComprehensive Evaluation:")
        print(response.content)
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")

async def main():
    """Run all tests"""
    await test_specific_images()
    await test_comprehensive_evaluation()

if __name__ == "__main__":
    # Check environment
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set")
        sys.exit(1)
    
    print("Note: This test requires a vision-capable model (gpt-4o)")
    print("Make sure your OpenAI API key has access to vision models\n")
    
    asyncio.run(main())