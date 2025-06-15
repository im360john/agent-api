#!/usr/bin/env python3
"""
Demo script to show color changer functionality
"""
import asyncio
import json
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock database before imports
from unittest.mock import MagicMock
sys.modules['db.session'] = MagicMock()
sys.modules['db.session'].db_url = "sqlite:///test.db"

from agents.color_changer_agent import ColorChangerTools

async def demo():
    """Demonstrate color changer tools"""
    print("Color Changer Tools Demo")
    print("=" * 60)
    
    # Create tools instance
    tools = ColorChangerTools()
    
    # Check dependencies
    print("\nDependency Status:")
    print(f"✓ PIL/Pillow: {tools.pil_available}")
    print(f"✓ NumPy: {tools.numpy_available}")
    print(f"✓ OpenCV: {tools.cv2_available}")
    
    # Sample image
    sample_image = "https://images.unsplash.com/photo-1501594907352-04cda38ebc29?w=400"
    print(f"\nUsing sample image: {sample_image}")
    print("(A beautiful landscape photo)")
    
    print("\n" + "-" * 60)
    
    # Demo 1: Analyze colors
    print("\n1. ANALYZING IMAGE COLORS:")
    result = await tools.analyze_image_colors(sample_image)
    data = json.loads(result)
    if "error" not in data:
        print(f"   - Dimensions: {data['dimensions']}")
        print(f"   - Color temperature: {data['color_temperature']}")
        print(f"   - Average saturation: {data['average_saturation']}")
        print(f"   - Dominant color: {data['dominant_colors'][0]['hex']} ({data['dominant_colors'][0]['percentage']}%)")
        print(f"   - Average color: {data['average_color']['hex']}")
    else:
        print(f"   Error: {data['error']}")
    
    # Demo 2: Hue shift
    print("\n2. HUE SHIFT (+45 degrees):")
    result = await tools.hue_shift(sample_image, 45)
    data = json.loads(result)
    if "error" not in data:
        print(f"   - Status: {data['status']}")
        print(f"   - Operation: {data['operation']}")
        print(f"   - Degrees shifted: {data['degrees']}")
        print(f"   - Result: Color wheel rotated by 45°")
    else:
        print(f"   Error: {data['error']}")
    
    # Demo 3: Saturation
    print("\n3. SATURATION BOOST (1.5x):")
    result = await tools.adjust_saturation(sample_image, 1.5)
    data = json.loads(result)
    if "error" not in data:
        print(f"   - Status: {data['status']}")
        print(f"   - Factor: {data['factor']} (50% more vibrant)")
        print(f"   - Result: Colors are more intense")
    else:
        print(f"   Error: {data['error']}")
    
    # Demo 4: Artistic filter
    print("\n4. VINTAGE FILTER:")
    result = await tools.apply_artistic_filter(sample_image, "vintage")
    data = json.loads(result)
    if "error" not in data:
        print(f"   - Status: {data['status']}")
        print(f"   - Filter: {data['filter']}")
        print(f"   - Result: Reduced saturation, warm tones, lower contrast")
    else:
        print(f"   Error: {data['error']}")
    
    # Demo 5: Color temperature
    print("\n5. WARM COLOR TEMPERATURE (4000K):")
    result = await tools.color_temperature(sample_image, 4000)
    data = json.loads(result)
    if "error" not in data:
        print(f"   - Status: {data['status']}")
        print(f"   - Temperature: {data['kelvin']}K ({data['type']})")
        print(f"   - Result: Warmer, sunset-like tones")
    else:
        print(f"   Error: {data['error']}")
    
    # Demo 6: Selective color
    print("\n6. SELECTIVE COLOR (Blues +30° hue, 1.2x saturation):")
    result = await tools.selective_color_adjust(sample_image, "blues", 30, 1.2)
    data = json.loads(result)
    if "error" not in data:
        print(f"   - Status: {data['status']}")
        print(f"   - Color range: {data['color_range']}")
        print(f"   - Pixels affected: {data['pixels_affected']}")
        print(f"   - Result: Blues shifted toward purple and more vibrant")
    else:
        print(f"   Error: {data['error']}")
    
    print("\n" + "-" * 60)
    print("\nAll tools demonstrated successfully!")
    print("\nTo use these tools interactively, run:")
    print("  python3 run_color_changer.py")
    print("\nTo save results, add save_path parameter to any tool.")

if __name__ == "__main__":
    asyncio.run(demo())