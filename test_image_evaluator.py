#!/usr/bin/env python3
"""
Test the image evaluator agent directly
"""
import os
import sys
import json
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Mock the database modules
import types
mock_db = types.ModuleType('db')
mock_session = types.ModuleType('session')
mock_session.db_url = "sqlite:///./test.db"
mock_db.session = mock_session
sys.modules['db'] = mock_db
sys.modules['db.session'] = mock_session

# Import the agent
from agents.image_evaluator_agent import get_image_evaluator_agent, ImageEvaluatorTools

def test_image_tools():
    """Test the image evaluator tools directly"""
    print("\n=== Testing Image Evaluator Tools ===")
    print("-" * 50)
    
    # Create tools instance
    tools = ImageEvaluatorTools()
    
    # Test with a sample image URL
    # Using a placeholder URL - replace with actual image
    test_urls = [
        "https://via.placeholder.com/800x600.png?text=Sample+Product+Image",
        "https://picsum.photos/1200/800",  # Random image from Lorem Picsum
        "https://dummyimage.com/600x400/000/fff&text=Cannabis+Product"
    ]
    
    print("\nTesting single image evaluation...")
    
    # Run async function
    async def test_single():
        for url in test_urls[:1]:
            print(f"\nEvaluating: {url}")
            result = await tools.evaluate_image(url, "flower")
            result_dict = json.loads(result)
            print(json.dumps(result_dict, indent=2))
    
    asyncio.run(test_single())
    
    print("\n\nTesting batch evaluation...")
    
    async def test_batch():
        result = await tools.batch_evaluate_images(test_urls, ["flower", "concentrate", "edible"])
        result_dict = json.loads(result)
        print(json.dumps(result_dict, indent=2))
    
    asyncio.run(test_batch())

async def test_image_agent():
    """Test the image evaluator agent"""
    print("\n\n=== Testing Image Evaluator Agent ===")
    print("-" * 50)
    
    # Create agent without database
    agent = get_image_evaluator_agent(
        model_id="gpt-4o-mini",
        debug_mode=True
    )
    
    # Test queries
    queries = [
        "Please evaluate this image URL for quality and compliance: https://picsum.photos/800/600",
        "Check if this is a stock photo or real product image: https://dummyimage.com/600x400/000/fff&text=Cannabis+Product",
        "Analyze the quality of these product images and provide recommendations: ['https://via.placeholder.com/400x300', 'https://picsum.photos/1024/768']"
    ]
    
    for query in queries[:1]:  # Test just the first query
        print(f"\nQuery: {query}")
        print("-" * 30)
        
        try:
            response = await agent.arun(query)
            print(f"Response:\n{response.content}")
        except Exception as e:
            print(f"Error: {type(e).__name__}: {e}")
            print("\nNote: The agent may fail due to missing database. Testing tools directly instead...")

def main():
    """Main test function"""
    print("Image Evaluator Testing")
    print("=" * 50)
    
    # Check environment
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set in environment")
        return
    
    # Test tools first (doesn't require agent/database)
    test_image_tools()
    
    # Then test the agent
    print("\n" + "="*50)
    print("\nTesting full agent...")
    asyncio.run(test_image_agent())

if __name__ == "__main__":
    main()