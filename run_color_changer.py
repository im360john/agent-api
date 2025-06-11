#!/usr/bin/env python3
"""
Standalone script to run the color changer agent or test tools directly
"""
import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the tools for direct testing
from agents.color_changer_agent import ColorChangerTools, get_color_changer_agent

async def test_tools_directly():
    """Test color changer tools without needing API keys"""
    print("\nTesting Color Changer Tools Directly (No API Key Required)")
    print("=" * 60)
    
    tools = ColorChangerTools()
    
    # Check dependencies
    print("\nDependency Check:")
    print(f"- PIL/Pillow available: {tools.pil_available}")
    print(f"- OpenCV available: {tools.cv2_available}")
    print(f"- NumPy available: {tools.numpy_available}")
    
    if not tools.pil_available:
        print("\nError: Pillow is required. Install with: pip install pillow")
        return
    
    print("\nAvailable Tools:")
    print("1. Analyze image colors")
    print("2. Hue shift")
    print("3. Replace color")
    print("4. Adjust saturation")
    print("5. Adjust brightness")
    print("6. Color temperature")
    print("7. Apply artistic filter")
    print("8. Selective color adjust")
    print("9. Exit")
    
    # Sample image for testing
    sample_image = "https://images.unsplash.com/photo-1501594907352-04cda38ebc29?w=400"
    
    while True:
        choice = input("\nSelect tool to test (1-9): ")
        
        if choice == "1":
            url = input(f"Enter image URL (or press Enter for sample): ") or sample_image
            print("\nAnalyzing colors...")
            result = await tools.analyze_image_colors(url)
            print(result)
            
        elif choice == "2":
            url = input(f"Enter image URL (or press Enter for sample): ") or sample_image
            degrees = float(input("Enter hue shift degrees (-360 to 360): "))
            save_path = input("Save to path (or press Enter to skip): ") or None
            print("\nShifting hue...")
            result = await tools.hue_shift(url, degrees, save_path)
            print(result)
            
        elif choice == "3":
            url = input(f"Enter image URL (or press Enter for sample): ") or sample_image
            source = input("Enter source color (R,G,B): ")
            target = input("Enter target color (R,G,B): ")
            tolerance = int(input("Enter tolerance (default 30): ") or "30")
            save_path = input("Save to path (or press Enter to skip): ") or None
            print("\nReplacing color...")
            result = await tools.replace_color(url, source, target, tolerance, save_path)
            print(result)
            
        elif choice == "4":
            url = input(f"Enter image URL (or press Enter for sample): ") or sample_image
            factor = float(input("Enter saturation factor (0.0-2.0, 1.0=normal): "))
            save_path = input("Save to path (or press Enter to skip): ") or None
            print("\nAdjusting saturation...")
            result = await tools.adjust_saturation(url, factor, save_path)
            print(result)
            
        elif choice == "5":
            url = input(f"Enter image URL (or press Enter for sample): ") or sample_image
            factor = float(input("Enter brightness factor (0.0-2.0, 1.0=normal): "))
            save_path = input("Save to path (or press Enter to skip): ") or None
            print("\nAdjusting brightness...")
            result = await tools.adjust_brightness(url, factor, save_path)
            print(result)
            
        elif choice == "6":
            url = input(f"Enter image URL (or press Enter for sample): ") or sample_image
            kelvin = int(input("Enter temperature in Kelvin (2000=warm, 6500=neutral, 10000=cool): "))
            save_path = input("Save to path (or press Enter to skip): ") or None
            print("\nAdjusting color temperature...")
            result = await tools.color_temperature(url, kelvin, save_path)
            print(result)
            
        elif choice == "7":
            url = input(f"Enter image URL (or press Enter for sample): ") or sample_image
            print("Available filters: vintage, sepia, cyberpunk, warm, cool")
            filter_name = input("Enter filter name: ")
            save_path = input("Save to path (or press Enter to skip): ") or None
            print("\nApplying filter...")
            result = await tools.apply_artistic_filter(url, filter_name, save_path)
            print(result)
            
        elif choice == "8":
            url = input(f"Enter image URL (or press Enter for sample): ") or sample_image
            print("Color ranges: reds, greens, blues, yellows, cyans, magentas")
            color_range = input("Enter color range: ")
            hue_shift = float(input("Enter hue shift for this range (default 0): ") or "0")
            saturation = float(input("Enter saturation multiplier (default 1.0): ") or "1.0")
            save_path = input("Save to path (or press Enter to skip): ") or None
            print("\nAdjusting selective colors...")
            result = await tools.selective_color_adjust(url, color_range, hue_shift, saturation, save_path)
            print(result)
            
        elif choice == "9":
            print("Exiting...")
            break
            
        else:
            print("Invalid option")

async def run_with_agent():
    """Run the full agent with AI capabilities (requires API key)"""
    print("\nColor Changer Agent Runner (AI Mode)")
    print("=" * 50)
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\nError: OPENAI_API_KEY not set")
        print("To use AI mode, please set your OpenAI API key:")
        print("export OPENAI_API_KEY='your-key-here'")
        print("\nSwitching to direct tool testing mode...")
        await test_tools_directly()
        return
    
    # Create the agent
    agent = get_color_changer_agent(
        model_id="gpt-4o",  # Vision-capable model
        debug_mode=False
    )
    
    print("\nAgent created successfully!")
    print("\nYou can ask natural language requests like:")
    print("- 'Make this image more vibrant'")
    print("- 'Apply a vintage look to this photo'")
    print("- 'Change all red colors to blue'")
    print("- 'Create a cyberpunk aesthetic'")
    print("\nType 'exit' to quit")
    
    # Sample image for examples
    sample_image = "https://images.unsplash.com/photo-1501594907352-04cda38ebc29?w=400"
    print(f"\nSample image available: {sample_image}")
    
    while True:
        query = input("\nWhat would you like to do? ")
        
        if query.lower() == 'exit':
            print("Exiting...")
            break
            
        # If no URL in query, ask for one
        if "http" not in query:
            url = input("Enter image URL (or press Enter for sample): ") or sample_image
            query = f"{query} for this image: {url}"
        
        print("\nProcessing...")
        try:
            response = await agent.arun(query)
            print("\nResponse:")
            print("-" * 50)
            print(response.content)
        except Exception as e:
            print(f"Error: {type(e).__name__}: {e}")

async def main():
    print("Color Changer Tool")
    print("=" * 50)
    print("\nSelect mode:")
    print("1. Test tools directly (no API key required)")
    print("2. Use AI agent (requires OpenAI API key)")
    print("3. Exit")
    
    choice = input("\nSelect option (1-3): ")
    
    if choice == "1":
        await test_tools_directly()
    elif choice == "2":
        await run_with_agent()
    elif choice == "3":
        print("Exiting...")
    else:
        print("Invalid option")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())