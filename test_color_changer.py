"""Test the Color Changer Agent"""

import asyncio
import os
from unittest.mock import MagicMock
import sys

# Mock the database modules before importing
sys.modules['db.session'] = MagicMock()
sys.modules['db.session'].db_url = "sqlite:///test.db"

from agents.color_changer_agent import get_color_changer_agent

async def test_color_changer():
    """Test various color transformation capabilities"""
    
    # Set up API key
    os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', 'your-openai-key-here')
    
    # Test image URL (using a sample image)
    test_image_url = "https://images.unsplash.com/photo-1501594907352-04cda38ebc29?w=400"
    
    # Create agent without database dependencies
    agent = get_color_changer_agent(
        model_id="gpt-4o",
        debug_mode=True
    )
    
    print("Testing Color Changer Agent")
    print("=" * 80)
    print(f"Test image: {test_image_url}")
    print("\n")
    
    # Test 1: Analyze image colors
    print("1. ANALYZING IMAGE COLORS:")
    print("-" * 40)
    prompt1 = f"""Please analyze the colors in this image:

{test_image_url}

Use the analyze_image_colors tool to understand the color distribution and dominant colors.
"""
    
    response1 = await agent.arun(prompt1)
    print(response1.content)
    print("\n" + "=" * 80 + "\n")
    
    # Test 2: Hue shift
    print("2. HUE SHIFT TEST:")
    print("-" * 40)
    prompt2 = f"""Now let's shift the hue of this image by 45 degrees to create a different color mood:

{test_image_url}

Use the hue_shift tool with degrees=45. This should shift all colors along the color wheel.
"""
    
    response2 = await agent.arun(prompt2)
    print(response2.content)
    print("\n" + "=" * 80 + "\n")
    
    # Test 3: Saturation adjustment
    print("3. SATURATION ENHANCEMENT:")
    print("-" * 40)
    prompt3 = f"""Make this image more vibrant by increasing saturation:

{test_image_url}

Use adjust_saturation with factor=1.5 to make colors more intense.
"""
    
    response3 = await agent.arun(prompt3)
    print(response3.content)
    print("\n" + "=" * 80 + "\n")
    
    # Test 4: Artistic filter
    print("4. ARTISTIC FILTER:")
    print("-" * 40)
    prompt4 = f"""Apply a vintage filter to give this image an old-school look:

{test_image_url}

Use apply_artistic_filter with filter_name='vintage'.
"""
    
    response4 = await agent.arun(prompt4)
    print(response4.content)
    print("\n" + "=" * 80 + "\n")
    
    # Test 5: Color temperature
    print("5. COLOR TEMPERATURE ADJUSTMENT:")
    print("-" * 40)
    prompt5 = f"""Make this image warmer by adjusting the color temperature:

{test_image_url}

Use color_temperature with kelvin=4000 to create a warm, sunset-like feeling.
"""
    
    response5 = await agent.arun(prompt5)
    print(response5.content)
    print("\n" + "=" * 80 + "\n")
    
    # Test 6: Complex request
    print("6. COMPLEX COLOR TRANSFORMATION:")
    print("-" * 40)
    prompt6 = f"""I want to create a cyberpunk aesthetic for this image:

{test_image_url}

Can you analyze the image first, then apply appropriate transformations to achieve a cyberpunk look?
Think neon blues and purples with high contrast.
"""
    
    response6 = await agent.arun(prompt6)
    print(response6.content)

if __name__ == "__main__":
    # Check for API key
    if not os.getenv('OPENAI_API_KEY'):
        print("ERROR: Please set OPENAI_API_KEY environment variable")
        print("export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)
    
    asyncio.run(test_color_changer())