#!/usr/bin/env python3
"""
Standalone script to run the image evaluator agent
"""
import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now import the agent (will use real PostgreSQL database)
from agents.image_evaluator_agent import get_image_evaluator_agent, ImageEvaluatorTools

async def main():
    print("Image Evaluator Agent Runner")
    print("=" * 50)
    
    # Create the agent with vision capabilities
    agent = get_image_evaluator_agent(
        model_id="gpt-4o",  # Use vision-capable model
        debug_mode=False  # Set to True for debug output
    )
    
    print("\nAgent created successfully!")
    print("\nAvailable commands:")
    print("1. Evaluate single image")
    print("2. Batch evaluate images")
    print("3. Check image quality")
    print("4. Exit")
    
    while True:
        choice = input("\nSelect option (1-4): ")
        
        if choice == "1":
            url = input("Enter image URL: ")
            query = f"Use analyze_authenticity_strict to evaluate this image: {url}"
            
        elif choice == "2":
            urls = input("Enter image URLs (comma-separated): ")
            url_list = [u.strip() for u in urls.split(",")]
            query = f"Please evaluate these images in batch: {url_list}"
            
        elif choice == "3":
            url = input("Enter image URL: ")
            query = f"Use quick_evaluate to check this image: {url}"
            
        elif choice == "4":
            print("Exiting...")
            break
            
        else:
            print("Invalid option")
            continue
        
        print("\nProcessing...")
        try:
            response = await agent.arun(query)
            print("\nResponse:")
            print("-" * 50)
            print(response.content)
        except Exception as e:
            print(f"Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set in environment")
        print("Please run: source .env")
        sys.exit(1)
    
    # Run the async main function
    asyncio.run(main())
