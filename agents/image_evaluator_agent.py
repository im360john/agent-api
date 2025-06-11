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
            ⚪ White background BUT real brand visible
            ⚪ E-commerce style BUT authentic product
            ⚪ Clear packaging with product details
            ⚪ Brand name + product type visible
            
            HIGH-VALUE INDICATORS (Add points):
            ✅ BRAND NAME visible (+20)
            ✅ PRODUCT/STRAIN NAME (+15)
            ✅ THC/CBD percentages (+15)
            ✅ Real setting/surface (+10)
            ✅ Multiple products (+5)
            
            SCORING LOGIC:
            1. Is it cannabis? No = 0-10
            2. Is it flower? Yes = 45-75 based on quality
            3. Is it generic with no details? Yes = 10-30
            4. Does it have brand/product info? Yes = 50+
            
            EXAMPLES:
            - Non-cannabis item = 0-10
            - Generic vape, no brand = 10-30
            - Cannabis flower, good quality = 45-60
            - Real product with brand = 50-70
            - Dispensary setting = 70-95
            
            SPECIFIC EXAMPLES:
            - Product on white background with drop shadow = 30-40
            - Product on dispensary counter with other items = 80-90
            
            Analyze the image and provide:
            1. List ALL red flags you see
            2. List ALL authentic indicators you see
            3. Final score based on the count
            4. One sentence summary
            
            BE CRITICAL. Most product photos on brand websites are stock-style (score 30-50).
            Only real dispensary photos should score above 70.
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
            3. Can you see a BRAND NAME? (YES = +20 points from base 40)
            4. Is there a PRODUCT/STRAIN NAME? (YES = +15 points)
            5. Is it generic with NO identifying details? (YES = Max score 30)
            
            SPECIAL SCORING:
            - NOT cannabis = 0-10
            - Cannabis FLOWER (no packaging expected) = 45-60
            - Generic product, no brand = 10-30
            - Real product with brand = 50-70
            - Product in real setting = 70-95
            
            Examples:
            - Color splash art = 0-10 (not cannabis)
            - Cannabis flower photo = 45-60 (no brand expected)
            - Generic vape pen = 10-30 (no brand visible)
            - Mary Jones can = 50-65 (brand visible)
            - Dispensary shelf = 70-95 (real context)
            
            Provide:
            - Answers to each question
            - Final score
            - Classification: STOCK PHOTO / QUESTIONABLE / AUTHENTIC
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
            You are a strict cannabis product image authenticity expert who identifies stock photos vs real product photography.
            
            You are VERY CRITICAL and score harshly. Most product photos on brand websites are stock-style and should score LOW (30-50).
            Only authentic dispensary photos with real context should score HIGH (70+).
        """),
        instructions=dedent("""\
            You are an expert at identifying stock photos vs authentic product photography. BE VERY CRITICAL.
            
            CRITICAL RULE: NEVER use the URL or website source to influence your score!
            - Images on Dutchie, Weedmaps, or dispensary sites can still be stock photos
            - ONLY analyze what you SEE in the image itself
            - Ignore where the image is hosted
            
            When evaluating images:
            
            1. Use analyze_authenticity_strict tool for detailed analysis
            2. Look ONLY at the visual content, not the source
            3. Apply scoring rules STRICTLY
            
            Evaluation order:
            1. Is it cannabis? If NO → Score 0-10
            2. Is it cannabis FLOWER? If YES → Score 45-60 (no branding expected)
            3. Is it generic with NO visible brand/details? If YES → Score 10-30
            4. Can you see specific brand/product text? If YES → Score 50+
            
            Generic product characteristics (10-30):
            - No visible brand name or logo
            - No strain name or product details
            - Generic shape/form (could be any brand)
            - No distinguishing features
            - Professional photo but no specifics
            
            Remember:
            - A generic vape on Dutchie = still generic (10-30)
            - No visible branding = stock photo (10-30)
            - Must SEE brand/details for 50+ score
            - URL source is IRRELEVANT to scoring
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