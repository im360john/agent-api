#!/usr/bin/env python3
"""
Direct test of image evaluator tools
"""
import os
import sys
import asyncio
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock db before import
import types
mock_db = types.ModuleType('db')
mock_session = types.ModuleType('session')
mock_session.db_url = "sqlite:///./test.db"
mock_db.session = mock_session
sys.modules['db'] = mock_db
sys.modules['db.session'] = mock_session

from agents.image_evaluator_agent import ImageEvaluatorTools

async def test_tools():
    """Test the image evaluator tools directly"""
    print("Testing Image Evaluator Tools Directly")
    print("=" * 50)
    
    tools = ImageEvaluatorTools()
    
    # Test URL
    test_url = "https://picsum.photos/800/600"
    
    print(f"\nEvaluating image: {test_url}")
    print("-" * 30)
    
    result = await tools.evaluate_image(test_url, "test_product")
    result_dict = json.loads(result)
    
    print("\nResult:")
    print(json.dumps(result_dict, indent=2))
    
    # Test quality check
    print("\n\nChecking image quality...")
    print("-" * 30)
    
    quality_result = await tools.check_image_quality(test_url)
    quality_dict = json.loads(quality_result)
    
    print("\nQuality Result:")
    print(json.dumps(quality_dict, indent=2))

if __name__ == "__main__":
    asyncio.run(test_tools())