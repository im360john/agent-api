#!/usr/bin/env python3
"""
Test the improved image evaluator with LLM-based authenticity scoring
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

async def test_authenticity_evaluation():
    """Test the agent with authenticity evaluation"""
    print("Testing Image Evaluator with LLM Authenticity Scoring")
    print("=" * 60)
    
    # Create agent
    agent = get_image_evaluator_agent(
        model_id="gpt-4o-mini",
        user_id="test_user",
        session_id="test_session",
        debug_mode=False  # Set to True for detailed output
    )
    
    # Test images with different authenticity levels
    test_cases = [
        {
            "url": "https://picsum.photos/800/600",
            "description": "Generic stock photo site image"
        },
        {
            "url": "https://dummyimage.com/600x400/000/fff&text=Cannabis+Product",
            "description": "Placeholder image with text"
        },
        {
            "url": "https://images.unsplash.com/photo-1536819114556-1e10f967fb61",
            "description": "Professional cannabis photo from Unsplash"
        }
    ]
    
    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"Testing: {test['description']}")
        print(f"URL: {test['url']}")
        print("-" * 60)
        
        # Create a comprehensive query that will trigger both tools
        query = f"""
        Please evaluate this cannabis product image for e-commerce use: {test['url']}
        
        1. First, perform the initial evaluation for quality and compliance
        2. Then, evaluate the authenticity using the detailed criteria
        3. Provide a comprehensive assessment including:
           - Quality score and issues
           - Compliance status
           - Detailed authenticity score with reasoning
           - Final recommendation on whether to use this image
        
        Image context: {test['description']}
        """
        
        try:
            response = await agent.arun(query)
            print("\nAgent Response:")
            print(response.content)
        except Exception as e:
            print(f"\nError: {type(e).__name__}: {e}")
    
    print("\n" + "="*60)
    print("Testing complete!")

async def test_batch_with_authenticity():
    """Test batch evaluation with follow-up authenticity checks"""
    print("\n\nTesting Batch Evaluation with Authenticity")
    print("=" * 60)
    
    agent = get_image_evaluator_agent(
        model_id="gpt-4o-mini",
        debug_mode=False
    )
    
    query = """
    Please evaluate these product images in batch and then provide authenticity scores:
    - https://picsum.photos/800/600
    - https://dummyimage.com/600x400/000/fff&text=Cannabis+Product
    
    For each image:
    1. Run initial evaluation
    2. Evaluate authenticity
    3. Provide final recommendation
    """
    
    try:
        response = await agent.arun(query)
        print("\nBatch Evaluation Response:")
        print(response.content)
    except Exception as e:
        print(f"\nError: {type(e).__name__}: {e}")

async def main():
    """Run all tests"""
    await test_authenticity_evaluation()
    await test_batch_with_authenticity()

if __name__ == "__main__":
    # Check environment
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set")
        sys.exit(1)
    
    asyncio.run(main())