"""Test the image evaluator with the ideal product image"""

import asyncio
from agents.image_evaluator_agent import get_image_evaluator_agent

async def test_ideal_image():
    """Test the ideal product image that should score high"""
    
    # The ideal image URL provided by the user
    ideal_image_url = "https://content.sunnyside.shop/1c6bfdf6-614f-445e-b61c-cd2b9331783a.jpeg"
    
    # Create the agent
    agent = get_image_evaluator_agent(debug_mode=True)
    
    print("Testing ideal product image...")
    print(f"Image URL: {ideal_image_url}\n")
    
    # Test with current scoring system
    prompt = f"""Please analyze this cannabis product image and provide a detailed authenticity score:

{ideal_image_url}

First, use the analyze_authenticity_strict tool to get the scoring criteria, then evaluate the image.

What I expect to see in this ideal product image:
- Clean layout with professional presentation
- Bold brand visibility
- Clear packaging details
- Inner product inclusion (showing what's inside)
- Clearly defined product name

Please provide:
1. Detailed analysis of what you see
2. Score based on the strict criteria
3. Explanation of scoring
"""
    
    response = await agent.arun(prompt)
    print("\nAgent Response:")
    print(response.content)
    print("\n" + "="*80 + "\n")
    
    # Also do a quick evaluation
    quick_prompt = f"""Now do a quick evaluation of the same image using the quick_evaluate tool:

{ideal_image_url}
"""
    
    quick_response = await agent.arun(quick_prompt)
    print("\nQuick Evaluation:")
    print(quick_response.content)

if __name__ == "__main__":
    asyncio.run(test_ideal_image())