"""Cannabis Product Image Processing Agent - Validates and evaluates product images with vision AI"""

from textwrap import dedent
from typing import Optional, List, Dict
import asyncio
import time
import json
import io
import base64
from datetime import datetime
from dataclasses import dataclass

from agno.agent import Agent
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.models.openai import OpenAIChat
from agno.storage.agent.postgres import PostgresAgentStorage
from agno.tools.toolkit import Toolkit

from db.session import db_url


class ImageEvaluatorTools(Toolkit):
    """Custom toolkit for cannabis product image evaluation"""
    
    def __init__(self):
        super().__init__(name="image_evaluator_tools")
        self.register(self.analyze_authenticity_strict)
        self.register(self.quick_evaluate)
        self.setup_dependencies()
    
    def setup_dependencies(self):
        """Check which optional dependencies are available"""
        self.pil_available = False
        try:
            from PIL import Image  # noqa: F401
            self.pil_available = True
        except ImportError:
            pass
    
    async def analyze_authenticity_strict(self, image_url: str) -> str:
        """
        Strictly analyzes image authenticity with clear scoring rules.
        
        Args:
            image_url: URL of the image to analyze
            
        Returns:
            Detailed scoring criteria and analysis instructions
        """
        
        criteria = dedent("""
            CRITICAL: You must analyze this cannabis product image and score its authenticity STRICTLY based on these rules:
            
            Image URL: {image_url}
            
            ⚠️ IMPORTANT: IGNORE the URL/source when scoring!
            - Do NOT consider where the image is hosted (dutchie, weedmaps, etc.)
            - Do NOT assume authenticity based on the website
            - ONLY judge what you SEE in the actual image
            - Generic products on legitimate sites are still stock photos!
            
            SPECIAL CASES - CHECK FIRST:
            
            🚫 NOT CANNABIS (Score 0-10):
            - If this is NOT a cannabis product at all = 0-10
            - Random objects, art, non-cannabis items = REJECT
            
            🌿 CANNABIS FLOWER (Score 45-75):
            - Raw flower/buds don't have packaging
            - If authentic-looking flower = 45-60
            - If flower in jar with label = 60-75
            - If generic stock flower photo = 20-30
            
            TRUE STOCK PHOTO INDICATORS (Score 10-30):
            ❌ NO VISIBLE BRAND NAME = automatic 10-30
            ❌ Generic vape/cart/edible shape with no text
            ❌ Could be ANY brand's product
            ❌ No distinguishing features or labels
            ❌ Professional photo but zero specifics
            ❌ Watermarks or placeholder products
            
            CRITICAL: If you can't read a brand name = MAX 30!
            
            PROFESSIONAL PRODUCT PHOTO (Score 50-70):
            ⚪ White/clean background BUT real brand visible
            ⚪ E-commerce style BUT authentic product
            ⚪ Clear packaging with product details
            ⚪ Brand name + product type visible
            
            🏆 IDEAL PRODUCT PHOTO (Score 75-90):
            ✨ Professional composition with multiple elements
            ✨ Shows BOTH packaging AND inner product
            ✨ Clear, bold brand visibility
            ✨ Product name/strain clearly defined
            ✨ Clean, intentional layout
            ✨ High-resolution with sharp details
            ✨ Multiple angles or product states shown
            
            HIGH-VALUE INDICATORS (Add points from base):
            ✅ BRAND NAME visible (+20 from base)
            ✅ PRODUCT/STRAIN NAME (+15)
            ✅ Shows inner product + packaging (+20)
            ✅ THC/CBD percentages (+10)
            ✅ Professional studio quality (+10)
            ✅ Multiple products/angles (+10)
            ✅ Real setting/surface (+5)
            
            SCORING TIERS:
            0-10: Not cannabis
            10-30: Generic/stock with no brand
            30-50: Basic product shot, minimal info
            50-70: Professional with brand/details
            75-90: IDEAL - Multiple elements, packaging + product
            90-95: Dispensary/retail environment
            95-100: Perfect authenticity (rare)
            
            SCORING LOGIC:
            1. Is it cannabis? No = 0-10
            2. Is it flower? Yes = 45-75 based on quality
            3. Is it generic with no details? Yes = 10-30
            4. Does it have brand/product info? Yes = Start at 50
            5. Does it show packaging + inner product? Add +20-25
            6. Is composition professional/intentional? Add +10-15
            
            EXAMPLES:
            - Non-cannabis item = 0-10
            - Generic vape, no brand = 10-30
            - Cannabis flower, good quality = 45-60
            - Basic product with brand = 50-70
            - Product + packaging + details = 75-90
            - Dispensary setting = 85-95
            
            Analyze the image and provide:
            1. List ALL red flags you see
            2. List ALL authentic indicators you see
            3. Count indicators and calculate score
            4. Final score with clear justification
            5. One sentence summary
            
            Remember: Professional product photography for legitimate brands CAN score 75-90 if it shows multiple elements effectively.
        """)
        
        return json.dumps({
            "image_url": image_url,
            "strict_criteria": criteria.format(image_url=image_url),
            "instruction": "Apply these rules STRICTLY. Count the indicators and score accordingly."
        }, indent=2)
    
    async def quick_evaluate(self, image_url: str) -> str:
        """
        Quick evaluation focusing on key authenticity markers.
        
        Args:
            image_url: URL of the image
            
        Returns:
            Quick evaluation prompt
        """
        
        prompt = dedent("""
            Quick authenticity check for: {image_url}
            
            ⚠️ IGNORE the URL/website - only judge the IMAGE content!
            
            FIRST, identify what this is:
            
            1. Is this a cannabis product? (NO = Score 0-10)
            2. Is this cannabis FLOWER/BUDS? (YES = Special scoring 45-75)
            3. Can you see a BRAND NAME? (YES = Base 50 minimum)
            4. Is there a PRODUCT/STRAIN NAME? (YES = +15 points)
            5. Does it show BOTH packaging AND inner product? (YES = +20-25 points)
            6. Is composition professional with multiple elements? (YES = Consider 75-90 range)
            
            SPECIAL SCORING:
            - NOT cannabis = 0-10
            - Cannabis FLOWER (no packaging expected) = 45-60
            - Generic product, no brand = 10-30
            - Real product with brand only = 50-70
            - IDEAL: Package + product + details = 75-90
            - Product in dispensary/retail = 85-95
            
            🏆 IDEAL PRODUCT INDICATORS:
            - Shows packaging AND what's inside
            - Bold, clear brand name
            - Visible strain/product name
            - Professional studio quality
            - Clean, intentional composition
            - Multiple angles or states
            
            Examples:
            - Color splash art = 0-10 (not cannabis)
            - Cannabis flower photo = 45-60 (no brand expected)
            - Generic vape pen = 10-30 (no brand visible)
            - Basic brand product = 50-65 (brand visible)
            - Package + inner product = 75-90 (ideal shot)
            - Dispensary shelf = 85-95 (real context)
            
            Provide:
            - Answers to each question
            - Final score with reasoning
            - Classification: STOCK PHOTO / AUTHENTIC / IDEAL PRODUCT SHOT
        """)
        
        return json.dumps({
            "image_url": image_url,
            "evaluation": prompt.format(image_url=image_url)
        }, indent=2)


def get_image_evaluator_agent(
    model_id: str = "gpt-4o",  # Vision model
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    """Create and return the image evaluator agent with strict scoring"""
    return Agent(
        name="Cannabis Image Authenticity Expert",
        agent_id="image_evaluator",
        user_id=user_id,
        session_id=session_id,
        model=OpenAIChat(id=model_id),
        tools=[ImageEvaluatorTools()],
        description=dedent("""\
            You are a cannabis product image authenticity expert who identifies stock photos vs real product photography.
            
            You recognize THREE main categories:
            1. STOCK PHOTOS (10-30): Generic products with no brand/details
            2. AUTHENTIC PRODUCTS (50-70): Real products with visible branding
            3. IDEAL PRODUCT SHOTS (75-90): Professional photos showing packaging + inner product + all details
            
            High-quality brand photography that shows multiple product elements can score in the IDEAL range.
        """),
        instructions=dedent("""\
            You are an expert at identifying stock photos vs authentic product photography with nuanced scoring.
            
            CRITICAL RULE: NEVER use the URL or website source to influence your score!
            - Images on Dutchie, Weedmaps, or dispensary sites can still be stock photos
            - ONLY analyze what you SEE in the image itself
            - Ignore where the image is hosted
            
            When evaluating images:
            
            1. Use analyze_authenticity_strict tool for detailed analysis
            2. Look ONLY at the visual content, not the source
            3. Apply scoring rules with proper tier recognition
            
            SCORING TIERS:
            
            1. **NOT CANNABIS (0-10)**
               - Non-cannabis items, art, random objects
            
            2. **GENERIC STOCK (10-30)**
               - No visible brand name or logo
               - Could be ANY brand's product
               - Generic shape with no details
            
            3. **BASIC PRODUCT (30-50)**
               - Some details but minimal information
               - May have partial branding
            
            4. **AUTHENTIC PRODUCT (50-70)**
               - Clear brand name visible
               - Product type identifiable
               - Professional but single element
            
            5. **IDEAL PRODUCT SHOT (75-90)**
               - Shows BOTH packaging AND inner product
               - Bold brand visibility
               - Product/strain name clear
               - Professional multi-element composition
               - Clean, intentional layout
               - This is the gold standard for product photography
            
            6. **DISPENSARY/RETAIL (85-95)**
               - Real retail environment
               - Multiple authentic products
               - Natural setting
            
            Key evaluation points:
            - Cannabis flower without packaging = 45-60 (special case)
            - No brand visible = MAX 30
            - Brand visible = MIN 50
            - Package + product shown = 75-90 range
            - Professional ≠ Stock (can be 75-90 if shows multiple elements)
            
            Remember: High-quality brand photography that effectively shows packaging, inner product, and details deserves 75-90 scoring.
        """),
        # Enable memory
        memory=Memory(
            model=OpenAIChat(id=model_id),
            db=PostgresMemoryDb(table_name="image_evaluator_memories", db_url=db_url),
            delete_memories=True,
            clear_memories=True,
        ),
        enable_agentic_memory=True,
        # Enable storage
        storage=PostgresAgentStorage(table_name="image_evaluator_agent_sessions", db_url=db_url),
        show_tool_calls=True,
        debug_mode=debug_mode,
    )


# Create a default instance
image_evaluator_agent = get_image_evaluator_agent()