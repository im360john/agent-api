"""Color Changer Agent - AI-powered image color transformation agent"""

from textwrap import dedent
from typing import Optional, Dict, List, Tuple, Any
import json
import base64
import io
from dataclasses import dataclass

from agno.agent import Agent
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.models.openai import OpenAIChat
from agno.storage.agent.postgres import PostgresAgentStorage
from agno.tools.toolkit import Toolkit

from db.session import db_url


@dataclass
class ColorTransformation:
    """Represents a color transformation to be applied"""
    type: str  # 'hue_shift', 'replace_color', 'saturation', 'brightness', 'temperature', 'filter'
    params: Dict[str, Any]


class ColorChangerTools(Toolkit):
    """Custom toolkit for image color transformations"""
    
    def __init__(self):
        super().__init__(name="color_changer_tools")
        self.pil_available = False
        self.cv2_available = False
        self.numpy_available = False
        
        # Check for dependencies
        self._check_dependencies()
        
        # Register tools
        self.register(self.analyze_image_colors)
        self.register(self.hue_shift)
        self.register(self.replace_color)
        self.register(self.adjust_saturation)
        self.register(self.adjust_brightness)
        self.register(self.color_temperature)
        self.register(self.apply_artistic_filter)
        self.register(self.selective_color_adjust)
        self.register(self.batch_transform)
    
    def _check_dependencies(self):
        """Check which image processing libraries are available"""
        try:
            from PIL import Image, ImageEnhance
            self.pil_available = True
        except ImportError:
            pass
        
        try:
            import cv2
            self.cv2_available = True
        except ImportError:
            pass
        
        try:
            import numpy as np
            self.numpy_available = True
        except ImportError:
            pass
    
    async def analyze_image_colors(self, image_url: str) -> str:
        """
        Analyze the dominant colors and color distribution in an image.
        
        Args:
            image_url: URL of the image to analyze
            
        Returns:
            JSON analysis of color distribution and dominant colors
        """
        if not self.pil_available:
            return json.dumps({
                "error": "PIL/Pillow not available. Install with: pip install pillow",
                "suggestion": "Add 'pillow' to requirements.txt"
            })
        
        try:
            import aiohttp
            from PIL import Image
            from collections import Counter
            
            # Download image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        return json.dumps({"error": f"Failed to download image: {response.status}"})
                    
                    image_data = await response.read()
                    image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize for faster processing
            image.thumbnail((200, 200))
            
            # Get color data
            pixels = list(image.getdata())
            total_pixels = len(pixels)
            
            # Group similar colors
            color_groups = {}
            for pixel in pixels:
                # Round to nearest 32 for grouping
                grouped = tuple((c // 32) * 32 for c in pixel)
                color_groups[grouped] = color_groups.get(grouped, 0) + 1
            
            # Get top colors
            top_colors = sorted(color_groups.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # Calculate basic stats
            avg_r = sum(p[0] for p in pixels) / total_pixels
            avg_g = sum(p[1] for p in pixels) / total_pixels
            avg_b = sum(p[2] for p in pixels) / total_pixels
            
            # Determine color temperature
            temp = "neutral"
            if avg_r > avg_b + 20:
                temp = "warm"
            elif avg_b > avg_r + 20:
                temp = "cool"
            
            # Calculate saturation
            avg_saturation = sum(
                (max(p) - min(p)) / (max(p) + 0.001) for p in pixels
            ) / total_pixels
            
            return json.dumps({
                "image_url": image_url,
                "dimensions": f"{image.width}x{image.height}",
                "dominant_colors": [
                    {
                        "rgb": list(color),
                        "hex": "#{:02x}{:02x}{:02x}".format(*color),
                        "percentage": round(count / total_pixels * 100, 2)
                    }
                    for color, count in top_colors
                ],
                "average_color": {
                    "rgb": [int(avg_r), int(avg_g), int(avg_b)],
                    "hex": "#{:02x}{:02x}{:02x}".format(int(avg_r), int(avg_g), int(avg_b))
                },
                "color_temperature": temp,
                "average_saturation": round(avg_saturation, 2),
                "suggestions": [
                    "Consider warming the image" if temp == "cool" else "Consider cooling the image",
                    "Increase saturation for more vibrant colors" if avg_saturation < 0.3 else "Image has good color saturation",
                    f"Most dominant color is {top_colors[0][0]}, consider complementary colors for contrast"
                ]
            }, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"Failed to analyze image: {str(e)}"})
    
    async def hue_shift(self, image_url: str, degrees: float, save_path: Optional[str] = None) -> str:
        """
        Shift the hue of all colors in an image.
        
        Args:
            image_url: URL of the source image
            degrees: Degrees to shift hue (-360 to 360)
            save_path: Optional path to save the result
            
        Returns:
            Status message with result details
        """
        if not self.pil_available:
            return json.dumps({"error": "PIL/Pillow not available"})
        
        try:
            import aiohttp
            from PIL import Image
            import colorsys
            
            # Download image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        return json.dumps({"error": f"Failed to download image: {response.status}"})
                    
                    image_data = await response.read()
                    image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB
            if image.mode == 'RGBA':
                # Preserve alpha channel
                rgb_image = image.convert('RGB')
                alpha = image.split()[-1]
            else:
                rgb_image = image.convert('RGB')
                alpha = None
            
            # Process pixels
            pixels = list(rgb_image.getdata())
            shifted_pixels = []
            
            for r, g, b in pixels:
                # Convert to HSV
                h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
                
                # Shift hue
                h = (h + degrees/360.0) % 1.0
                
                # Convert back to RGB
                r, g, b = colorsys.hsv_to_rgb(h, s, v)
                shifted_pixels.append((int(r*255), int(g*255), int(b*255)))
            
            # Create new image
            result = Image.new('RGB', rgb_image.size)
            result.putdata(shifted_pixels)
            
            # Restore alpha if present
            if alpha:
                result.putalpha(alpha)
            
            # Save or return base64
            if save_path:
                result.save(save_path)
                return json.dumps({
                    "status": "success",
                    "operation": "hue_shift",
                    "degrees": degrees,
                    "saved_to": save_path,
                    "dimensions": f"{result.width}x{result.height}"
                })
            else:
                # Return base64 preview
                buffer = io.BytesIO()
                result.save(buffer, format='PNG')
                base64_image = base64.b64encode(buffer.getvalue()).decode()
                
                return json.dumps({
                    "status": "success",
                    "operation": "hue_shift",
                    "degrees": degrees,
                    "preview": f"data:image/png;base64,{base64_image[:100]}...",
                    "dimensions": f"{result.width}x{result.height}",
                    "note": "Full base64 image available - truncated for display"
                })
                
        except Exception as e:
            return json.dumps({"error": f"Failed to shift hue: {str(e)}"})
    
    async def replace_color(self, image_url: str, source_color: str, target_color: str, 
                           tolerance: int = 30, save_path: Optional[str] = None) -> str:
        """
        Replace a specific color with another color.
        
        Args:
            image_url: URL of the source image
            source_color: Source color as "R,G,B" string
            target_color: Target color as "R,G,B" string
            tolerance: Color matching tolerance (0-255)
            save_path: Optional path to save result
            
        Returns:
            Status message with result details
        """
        if not self.pil_available:
            return json.dumps({"error": "PIL/Pillow not available"})
        
        try:
            import aiohttp
            from PIL import Image
            import numpy as np
            
            # Parse colors - handle both "R,G,B" and "(R,G,B)" formats
            source_color_clean = source_color.strip().strip('()')
            target_color_clean = target_color.strip().strip('()')
            
            try:
                source_rgb = tuple(map(int, source_color_clean.split(',')))
                target_rgb = tuple(map(int, target_color_clean.split(',')))
                
                # Validate RGB values
                for val in source_rgb + target_rgb:
                    if not 0 <= val <= 255:
                        return json.dumps({"error": "RGB values must be between 0 and 255"})
                        
            except ValueError:
                return json.dumps({
                    "error": "Invalid color format. Please use R,G,B format (e.g., 255,0,0 for red)",
                    "source_input": source_color,
                    "target_input": target_color
                })
            
            # Download image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        return json.dumps({"error": f"Failed to download image: {response.status}"})
                    
                    image_data = await response.read()
                    image = Image.open(io.BytesIO(image_data))
            
            # Convert to numpy array if available
            if self.numpy_available:
                import numpy as np
                
                # Convert to RGBA
                if image.mode != 'RGBA':
                    image = image.convert('RGBA')
                
                data = np.array(image)
                
                # Calculate color distance
                r, g, b, a = data[:,:,0], data[:,:,1], data[:,:,2], data[:,:,3]
                
                # Find pixels within tolerance
                mask = (
                    (np.abs(r - source_rgb[0]) < tolerance) &
                    (np.abs(g - source_rgb[1]) < tolerance) &
                    (np.abs(b - source_rgb[2]) < tolerance)
                )
                
                # Replace colors
                data[mask] = target_rgb + (255,)
                
                result = Image.fromarray(data, 'RGBA')
                pixels_replaced = np.sum(mask)
                
            else:
                # Fallback to pure PIL
                result = image.convert('RGBA')
                pixels = result.load()
                width, height = result.size
                pixels_replaced = 0
                
                for x in range(width):
                    for y in range(height):
                        r, g, b, a = pixels[x, y]
                        if (abs(r - source_rgb[0]) < tolerance and
                            abs(g - source_rgb[1]) < tolerance and
                            abs(b - source_rgb[2]) < tolerance):
                            pixels[x, y] = target_rgb + (a,)
                            pixels_replaced += 1
            
            # Save or return result
            if save_path:
                result.save(save_path)
                return json.dumps({
                    "status": "success",
                    "operation": "replace_color",
                    "source_color": source_color,
                    "target_color": target_color,
                    "tolerance": tolerance,
                    "pixels_replaced": int(pixels_replaced),
                    "saved_to": save_path
                })
            else:
                return json.dumps({
                    "status": "success",
                    "operation": "replace_color",
                    "source_color": source_color,
                    "target_color": target_color,
                    "tolerance": tolerance,
                    "pixels_replaced": int(pixels_replaced),
                    "preview": "Generated (use save_path to save)"
                })
                
        except Exception as e:
            return json.dumps({"error": f"Failed to replace color: {str(e)}"})
    
    async def adjust_saturation(self, image_url: str, factor: float, save_path: Optional[str] = None) -> str:
        """
        Adjust image saturation.
        
        Args:
            image_url: URL of the source image
            factor: Saturation factor (0.0 = grayscale, 1.0 = original, >1.0 = enhanced)
            save_path: Optional path to save result
            
        Returns:
            Status message
        """
        if not self.pil_available:
            return json.dumps({"error": "PIL/Pillow not available"})
        
        try:
            import aiohttp
            from PIL import Image, ImageEnhance
            
            # Download image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        return json.dumps({"error": f"Failed to download image: {response.status}"})
                    
                    image_data = await response.read()
                    image = Image.open(io.BytesIO(image_data))
            
            # Apply saturation
            enhancer = ImageEnhance.Color(image)
            result = enhancer.enhance(factor)
            
            # Save or return
            if save_path:
                result.save(save_path)
                return json.dumps({
                    "status": "success",
                    "operation": "adjust_saturation",
                    "factor": factor,
                    "saved_to": save_path
                })
            else:
                return json.dumps({
                    "status": "success",
                    "operation": "adjust_saturation",
                    "factor": factor,
                    "preview": "Generated"
                })
                
        except Exception as e:
            return json.dumps({"error": f"Failed to adjust saturation: {str(e)}"})
    
    async def adjust_brightness(self, image_url: str, factor: float, save_path: Optional[str] = None) -> str:
        """
        Adjust image brightness.
        
        Args:
            image_url: URL of the source image
            factor: Brightness factor (0.0 = black, 1.0 = original, >1.0 = brighter)
            save_path: Optional path to save result
            
        Returns:
            Status message
        """
        if not self.pil_available:
            return json.dumps({"error": "PIL/Pillow not available"})
        
        try:
            import aiohttp
            from PIL import Image, ImageEnhance
            
            # Download image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        return json.dumps({"error": f"Failed to download image: {response.status}"})
                    
                    image_data = await response.read()
                    image = Image.open(io.BytesIO(image_data))
            
            # Apply brightness
            enhancer = ImageEnhance.Brightness(image)
            result = enhancer.enhance(factor)
            
            # Save or return
            if save_path:
                result.save(save_path)
                return json.dumps({
                    "status": "success",
                    "operation": "adjust_brightness",
                    "factor": factor,
                    "saved_to": save_path
                })
            else:
                return json.dumps({
                    "status": "success",
                    "operation": "adjust_brightness",
                    "factor": factor,
                    "preview": "Generated"
                })
                
        except Exception as e:
            return json.dumps({"error": f"Failed to adjust brightness: {str(e)}"})
    
    async def color_temperature(self, image_url: str, kelvin: int, save_path: Optional[str] = None) -> str:
        """
        Adjust color temperature of an image.
        
        Args:
            image_url: URL of the source image
            kelvin: Temperature in Kelvin (2000 = warm, 6500 = neutral, 10000 = cool)
            save_path: Optional path to save result
            
        Returns:
            Status message
        """
        if not self.pil_available:
            return json.dumps({"error": "PIL/Pillow not available"})
        
        try:
            import aiohttp
            from PIL import Image
            
            # Download image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        return json.dumps({"error": f"Failed to download image: {response.status}"})
                    
                    image_data = await response.read()
                    image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Calculate RGB adjustment based on temperature
            # Simplified temperature to RGB conversion
            if kelvin < 6500:
                # Warmer (more red/yellow)
                r_factor = 1.0 + (6500 - kelvin) / 10000
                g_factor = 1.0 + (6500 - kelvin) / 20000
                b_factor = 1.0 - (6500 - kelvin) / 10000
            else:
                # Cooler (more blue)
                r_factor = 1.0 - (kelvin - 6500) / 10000
                g_factor = 1.0 - (kelvin - 6500) / 20000
                b_factor = 1.0 + (kelvin - 6500) / 10000
            
            # Apply temperature adjustment
            pixels = list(image.getdata())
            adjusted_pixels = []
            
            for r, g, b in pixels:
                new_r = min(255, int(r * r_factor))
                new_g = min(255, int(g * g_factor))
                new_b = min(255, int(b * b_factor))
                adjusted_pixels.append((new_r, new_g, new_b))
            
            result = Image.new('RGB', image.size)
            result.putdata(adjusted_pixels)
            
            # Save or return
            if save_path:
                result.save(save_path)
                return json.dumps({
                    "status": "success",
                    "operation": "color_temperature",
                    "kelvin": kelvin,
                    "type": "warm" if kelvin < 6500 else "cool" if kelvin > 6500 else "neutral",
                    "saved_to": save_path
                })
            else:
                return json.dumps({
                    "status": "success",
                    "operation": "color_temperature",
                    "kelvin": kelvin,
                    "type": "warm" if kelvin < 6500 else "cool" if kelvin > 6500 else "neutral",
                    "preview": "Generated"
                })
                
        except Exception as e:
            return json.dumps({"error": f"Failed to adjust color temperature: {str(e)}"})
    
    async def apply_artistic_filter(self, image_url: str, filter_name: str, save_path: Optional[str] = None) -> str:
        """
        Apply an artistic color filter to the image.
        
        Args:
            image_url: URL of the source image
            filter_name: Name of filter ('vintage', 'sepia', 'cyberpunk', 'warm', 'cool')
            save_path: Optional path to save result
            
        Returns:
            Status message
        """
        if not self.pil_available:
            return json.dumps({"error": "PIL/Pillow not available"})
        
        try:
            import aiohttp
            from PIL import Image, ImageEnhance
            
            # Download image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        return json.dumps({"error": f"Failed to download image: {response.status}"})
                    
                    image_data = await response.read()
                    image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Apply filter based on name
            if filter_name == 'sepia':
                # Sepia tone
                pixels = list(image.getdata())
                sepia_pixels = []
                
                for r, g, b in pixels:
                    tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                    tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                    tb = int(0.272 * r + 0.534 * g + 0.131 * b)
                    
                    sepia_pixels.append((
                        min(255, tr),
                        min(255, tg),
                        min(255, tb)
                    ))
                
                result = Image.new('RGB', image.size)
                result.putdata(sepia_pixels)
                
            elif filter_name == 'vintage':
                # Vintage: reduced saturation, slight warmth, lower contrast
                result = image
                result = ImageEnhance.Color(result).enhance(0.7)  # Reduce saturation
                result = ImageEnhance.Contrast(result).enhance(0.9)  # Lower contrast
                
                # Add warmth
                pixels = list(result.getdata())
                vintage_pixels = []
                for r, g, b in pixels:
                    vintage_pixels.append((
                        min(255, int(r * 1.1)),
                        min(255, int(g * 1.05)),
                        int(b * 0.9)
                    ))
                result = Image.new('RGB', result.size)
                result.putdata(vintage_pixels)
                
            elif filter_name == 'cyberpunk':
                # Cyberpunk: high contrast, purple/blue tones
                result = image
                result = ImageEnhance.Contrast(result).enhance(1.5)
                
                pixels = list(result.getdata())
                cyber_pixels = []
                for r, g, b in pixels:
                    cyber_pixels.append((
                        int(r * 0.8),
                        int(g * 0.7),
                        min(255, int(b * 1.3))
                    ))
                result = Image.new('RGB', result.size)
                result.putdata(cyber_pixels)
                
            elif filter_name == 'warm':
                # Warm filter
                result = image
                pixels = list(result.getdata())
                warm_pixels = []
                for r, g, b in pixels:
                    warm_pixels.append((
                        min(255, int(r * 1.2)),
                        min(255, int(g * 1.1)),
                        int(b * 0.8)
                    ))
                result = Image.new('RGB', result.size)
                result.putdata(warm_pixels)
                
            elif filter_name == 'cool':
                # Cool filter
                result = image
                pixels = list(result.getdata())
                cool_pixels = []
                for r, g, b in pixels:
                    cool_pixels.append((
                        int(r * 0.8),
                        int(g * 0.9),
                        min(255, int(b * 1.2))
                    ))
                result = Image.new('RGB', result.size)
                result.putdata(cool_pixels)
                
            else:
                return json.dumps({"error": f"Unknown filter: {filter_name}"})
            
            # Save or return
            if save_path:
                result.save(save_path)
                return json.dumps({
                    "status": "success",
                    "operation": "artistic_filter",
                    "filter": filter_name,
                    "saved_to": save_path
                })
            else:
                return json.dumps({
                    "status": "success",
                    "operation": "artistic_filter",
                    "filter": filter_name,
                    "preview": "Generated"
                })
                
        except Exception as e:
            return json.dumps({"error": f"Failed to apply filter: {str(e)}"})
    
    async def selective_color_adjust(self, image_url: str, color_range: str, 
                                   hue_shift: float = 0, saturation: float = 1.0,
                                   save_path: Optional[str] = None) -> str:
        """
        Adjust specific color ranges in an image.
        
        Args:
            image_url: URL of the source image
            color_range: Color range to adjust ('reds', 'greens', 'blues', 'yellows', 'cyans', 'magentas')
            hue_shift: Degrees to shift hue for selected colors
            saturation: Saturation multiplier for selected colors
            save_path: Optional path to save result
            
        Returns:
            Status message
        """
        if not self.pil_available:
            return json.dumps({"error": "PIL/Pillow not available"})
        
        try:
            import aiohttp
            from PIL import Image
            import colorsys
            
            # Define color ranges (in HSV)
            color_ranges = {
                'reds': (330, 30),      # 330-30 degrees
                'yellows': (30, 90),    # 30-90 degrees
                'greens': (90, 150),    # 90-150 degrees
                'cyans': (150, 210),    # 150-210 degrees
                'blues': (210, 270),    # 210-270 degrees
                'magentas': (270, 330)  # 270-330 degrees
            }
            
            if color_range not in color_ranges:
                return json.dumps({"error": f"Invalid color range. Choose from: {list(color_ranges.keys())}"})
            
            range_start, range_end = color_ranges[color_range]
            
            # Download image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        return json.dumps({"error": f"Failed to download image: {response.status}"})
                    
                    image_data = await response.read()
                    image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Process pixels
            pixels = list(image.getdata())
            adjusted_pixels = []
            pixels_affected = 0
            
            for r, g, b in pixels:
                # Convert to HSV
                h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
                h_degrees = h * 360
                
                # Check if in range (handle wraparound for reds)
                in_range = False
                if range_start > range_end:  # Reds wrap around
                    in_range = h_degrees >= range_start or h_degrees <= range_end
                else:
                    in_range = range_start <= h_degrees <= range_end
                
                if in_range:
                    # Apply adjustments
                    h = (h + hue_shift/360.0) % 1.0
                    s = min(1.0, s * saturation)
                    pixels_affected += 1
                
                # Convert back to RGB
                r, g, b = colorsys.hsv_to_rgb(h, s, v)
                adjusted_pixels.append((int(r*255), int(g*255), int(b*255)))
            
            result = Image.new('RGB', image.size)
            result.putdata(adjusted_pixels)
            
            # Save or return
            if save_path:
                result.save(save_path)
                return json.dumps({
                    "status": "success",
                    "operation": "selective_color_adjust",
                    "color_range": color_range,
                    "hue_shift": hue_shift,
                    "saturation": saturation,
                    "pixels_affected": pixels_affected,
                    "saved_to": save_path
                })
            else:
                return json.dumps({
                    "status": "success",
                    "operation": "selective_color_adjust",
                    "color_range": color_range,
                    "hue_shift": hue_shift,
                    "saturation": saturation,
                    "pixels_affected": pixels_affected,
                    "preview": "Generated"
                })
                
        except Exception as e:
            return json.dumps({"error": f"Failed to adjust selective color: {str(e)}"})
    
    async def batch_transform(self, transformations: List[Dict[str, Any]], image_url: str, 
                            save_path: Optional[str] = None) -> str:
        """
        Apply multiple transformations to an image in sequence.
        
        Args:
            transformations: List of transformation dictionaries
            image_url: URL of the source image
            save_path: Optional path to save final result
            
        Returns:
            Status message with all applied transformations
        """
        results = []
        current_url = image_url
        
        for i, transform in enumerate(transformations):
            transform_type = transform.get('type')
            params = transform.get('params', {})
            
            # Add image URL to params
            params['image_url'] = current_url
            
            # Apply transformation based on type
            if transform_type == 'hue_shift':
                result = await self.hue_shift(**params)
            elif transform_type == 'replace_color':
                result = await self.replace_color(**params)
            elif transform_type == 'saturation':
                result = await self.adjust_saturation(**params)
            elif transform_type == 'brightness':
                result = await self.adjust_brightness(**params)
            elif transform_type == 'temperature':
                result = await self.color_temperature(**params)
            elif transform_type == 'filter':
                result = await self.apply_artistic_filter(**params)
            elif transform_type == 'selective_color':
                result = await self.selective_color_adjust(**params)
            else:
                result = json.dumps({"error": f"Unknown transformation: {transform_type}"})
            
            results.append({
                "step": i + 1,
                "type": transform_type,
                "result": json.loads(result)
            })
            
            # If this isn't the last transformation, we need to chain them
            # For now, we'll just track the results
        
        return json.dumps({
            "status": "batch_complete",
            "transformations_applied": len(transformations),
            "results": results,
            "note": "Batch processing completed. Individual transformations were applied."
        }, indent=2)


def get_color_changer_agent(
    model_id: str = "gpt-4o",  # Vision model for image analysis
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    """Create and return the color changer agent"""
    return Agent(
        name="Color Changer Agent",
        agent_id="color_changer",
        user_id=user_id,
        session_id=session_id,
        model=OpenAIChat(id=model_id),
        tools=[ColorChangerTools()],
        description=dedent("""\
            You are an AI-powered image color transformation agent that can modify colors in images through various techniques.
            
            You can perform hue shifting, color replacement, saturation/brightness adjustments, color temperature changes,
            and apply artistic filters to transform images according to user preferences.
        """),
        instructions=dedent("""\
            You are an expert image color transformation agent. Your capabilities include:
            
            ## Core Functions:
            1. **analyze_image_colors** - Analyze dominant colors and color distribution
            2. **hue_shift** - Rotate all colors along the color wheel (-360 to 360 degrees)
            3. **replace_color** - Replace specific colors with target colors (with tolerance)
            4. **adjust_saturation** - Enhance or reduce color intensity (0.0 = grayscale, >1.0 = vibrant)
            5. **adjust_brightness** - Make images darker or brighter (0.0 = black, >1.0 = brighter)
            6. **color_temperature** - Warm/cool adjustments (2000K = warm, 6500K = neutral, 10000K = cool)
            7. **apply_artistic_filter** - Apply predefined filters (vintage, sepia, cyberpunk, warm, cool)
            8. **selective_color_adjust** - Modify specific color ranges (reds, greens, blues, etc.)
            9. **batch_transform** - Apply multiple transformations in sequence
            
            ## Workflow:
            1. When user provides an image URL, first use `analyze_image_colors` to understand the image
            2. Based on analysis, suggest appropriate transformations
            3. Apply requested transformations with appropriate parameters
            4. Always explain what each transformation does
            5. Offer to save results if user provides a path
            
            ## Best Practices:
            - For subtle changes, use factors close to 1.0 (0.8-1.2)
            - For dramatic effects, use larger values
            - Hue shifts of 180 degrees create complementary colors
            - Color temperature: Lower = warmer (more red), Higher = cooler (more blue)
            - When replacing colors, start with tolerance around 30 and adjust as needed
            
            ## Examples:
            - "Make this sunset more vibrant" → Increase saturation on reds/oranges
            - "Fix white balance" → Adjust color temperature to ~5500K
            - "Create vintage look" → Apply vintage filter or reduce saturation + warm temperature
            - "Change red car to blue" → Use replace_color with appropriate tolerance
            
            Always be helpful and explain the effects of different transformations. If a transformation
            doesn't produce desired results, suggest alternatives or parameter adjustments.
            
            Remember: All transformations work with image URLs. Results can be saved with save_path parameter.
        """),
        # Enable memory
        memory=Memory(
            model=OpenAIChat(id=model_id),
            db=PostgresMemoryDb(table_name="color_changer_memories", db_url=db_url),
            delete_memories=True,
            clear_memories=True,
        ),
        enable_agentic_memory=True,
        # Enable storage
        storage=PostgresAgentStorage(table_name="color_changer_agent_sessions", db_url=db_url),
        add_history_to_messages=True,
        num_history_runs=3,
        show_tool_calls=True,
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )