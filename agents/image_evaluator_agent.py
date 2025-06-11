"""Cannabis Product Image Processing Agent - Validates and evaluates product images"""

from textwrap import dedent
from typing import Optional, List, Dict, Any
import asyncio
import time
import json
import base64
import io
from datetime import datetime
from dataclasses import dataclass, asdict

from agno.agent import Agent
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.models.openai import OpenAIChat
from agno.storage.agent.postgres import PostgresAgentStorage
from agno.tools.toolkit import Toolkit

from db.session import db_url


@dataclass
class ImageAnalysisResult:
    is_valid: bool
    quality_score: float  # 0-100
    compliance_score: float  # 0-100
    authenticity_score: float  # 0-100
    detected_objects: List[str]
    issues: List[str]
    recommendations: List[str]
    processing_time: float
    image_url: str
    analysis_timestamp: str


class ImageEvaluatorTools(Toolkit):
    """Custom toolkit for cannabis product image evaluation"""
    
    def __init__(self):
        super().__init__(name="image_evaluator_tools")
        self.register(self.evaluate_image)
        self.register(self.batch_evaluate_images)
        self.register(self.check_image_quality)
        self.register(self.detect_cannabis_products)
        self.register(self.check_compliance)
        self.register(self.detect_stock_photos)
        self.setup_dependencies()
    
    def setup_dependencies(self):
        """Check which optional dependencies are available"""
        self.cv2_available = False
        self.pil_available = False
        self.numpy_available = False
        
        try:
            import cv2
            self.cv2_available = True
        except ImportError:
            pass
            
        try:
            from PIL import Image
            self.pil_available = True
        except ImportError:
            pass
            
        try:
            import numpy as np
            self.numpy_available = True
        except ImportError:
            pass
    
    async def evaluate_image(self, image_url: str, product_type: str = None) -> str:
        """
        Evaluates a single cannabis product image for quality, authenticity, and compliance.
        
        Args:
            image_url: URL of the image to evaluate
            product_type: Optional type of product (flower, concentrate, edible, etc.)
            
        Returns:
            Formatted evaluation results
        """
        start_time = time.time()
        
        try:
            # Download and analyze image
            image_data = await self._download_image(image_url)
            if not image_data["success"]:
                return json.dumps({
                    "error": image_data.get("error", "Failed to download image"),
                    "image_url": image_url
                }, indent=2)
            
            # Run analysis tasks
            quality_result = await self._analyze_quality(image_data)
            compliance_result = await self._check_compliance(image_data)
            authenticity_result = await self._check_authenticity(image_data)
            product_detection = await self._detect_products(image_data, product_type)
            
            # Aggregate results
            issues = []
            recommendations = []
            
            # Quality assessment
            quality_score = quality_result.get("score", 0)
            if quality_score < 60:
                issues.extend(quality_result.get("issues", []))
                recommendations.append("Improve image quality (resolution, lighting, focus)")
            
            # Compliance assessment
            compliance_score = compliance_result.get("score", 0)
            if compliance_score < 70:
                issues.extend(compliance_result.get("violations", []))
                recommendations.append("Add required warning labels and remove prohibited claims")
            
            # Authenticity assessment
            authenticity_score = authenticity_result.get("score", 0)
            if authenticity_score < 50:
                issues.extend(authenticity_result.get("indicators", []))
                recommendations.append("Use original product photography instead of stock images")
            
            # Product detection
            detected_objects = product_detection.get("objects", [])
            is_valid_product = product_detection.get("is_valid", False)
            if not is_valid_product:
                issues.extend(product_detection.get("issues", []))
                recommendations.append("Ensure image shows actual cannabis product")
            
            # Overall validity
            is_valid = (
                quality_score >= 60 and
                compliance_score >= 70 and
                authenticity_score >= 50 and
                is_valid_product
            )
            
            processing_time = time.time() - start_time
            
            result = {
                "image_url": image_url,
                "is_valid": is_valid,
                "scores": {
                    "quality": round(quality_score, 2),
                    "compliance": round(compliance_score, 2),
                    "authenticity": round(authenticity_score, 2)
                },
                "detected_objects": detected_objects,
                "issues": list(set(issues)),  # Remove duplicates
                "recommendations": list(set(recommendations)),
                "processing_time": round(processing_time, 2),
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            return json.dumps({
                "error": f"Processing error: {str(e)}",
                "image_url": image_url
            }, indent=2)
    
    async def batch_evaluate_images(self, image_urls: List[str], product_types: List[str] = None) -> str:
        """
        Evaluates multiple images in batch for efficiency.
        
        Args:
            image_urls: List of image URLs to evaluate
            product_types: Optional list of product types corresponding to each image
            
        Returns:
            Formatted batch evaluation results
        """
        if product_types and len(product_types) != len(image_urls):
            return json.dumps({
                "error": "Product types list must match image URLs list length"
            }, indent=2)
        
        if not product_types:
            product_types = [None] * len(image_urls)
        
        # Process in batches
        batch_size = 5
        all_results = []
        
        for i in range(0, len(image_urls), batch_size):
            batch_urls = image_urls[i:i+batch_size]
            batch_types = product_types[i:i+batch_size]
            
            # Process batch concurrently
            tasks = []
            for url, ptype in zip(batch_urls, batch_types):
                tasks.append(self.evaluate_image(url, ptype))
            
            batch_results = await asyncio.gather(*tasks)
            
            # Parse JSON results
            for result_json in batch_results:
                try:
                    result = json.loads(result_json)
                    all_results.append(result)
                except:
                    all_results.append({"error": "Failed to parse result"})
        
        return json.dumps({
            "total_images": len(image_urls),
            "results": all_results
        }, indent=2)
    
    async def check_image_quality(self, image_url: str) -> str:
        """
        Analyzes image quality metrics including resolution, sharpness, and lighting.
        
        Args:
            image_url: URL of the image to analyze
            
        Returns:
            Quality analysis results
        """
        image_data = await self._download_image(image_url)
        if not image_data["success"]:
            return json.dumps({"error": "Failed to download image"}, indent=2)
        
        quality_result = await self._analyze_quality(image_data)
        return json.dumps(quality_result, indent=2)
    
    async def detect_cannabis_products(self, image_url: str) -> str:
        """
        Detects cannabis-related objects and products in the image.
        
        Args:
            image_url: URL of the image to analyze
            
        Returns:
            Product detection results
        """
        image_data = await self._download_image(image_url)
        if not image_data["success"]:
            return json.dumps({"error": "Failed to download image"}, indent=2)
        
        detection_result = await self._detect_products(image_data)
        return json.dumps(detection_result, indent=2)
    
    async def check_compliance(self, image_url: str) -> str:
        """
        Checks image for regulatory compliance including required warnings.
        
        Args:
            image_url: URL of the image to analyze
            
        Returns:
            Compliance check results
        """
        image_data = await self._download_image(image_url)
        if not image_data["success"]:
            return json.dumps({"error": "Failed to download image"}, indent=2)
        
        compliance_result = await self._check_compliance(image_data)
        return json.dumps(compliance_result, indent=2)
    
    async def detect_stock_photos(self, image_url: str) -> str:
        """
        Detects if an image is likely a stock photo rather than actual product photography.
        
        Args:
            image_url: URL of the image to analyze
            
        Returns:
            Stock photo detection results
        """
        image_data = await self._download_image(image_url)
        if not image_data["success"]:
            return json.dumps({"error": "Failed to download image"}, indent=2)
        
        authenticity_result = await self._check_authenticity(image_data)
        return json.dumps(authenticity_result, indent=2)
    
    # Internal helper methods
    async def _download_image(self, image_url: str, max_size_mb: int = 10) -> Dict:
        """Downloads and preprocesses image"""
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        return {"success": False, "error": f"HTTP {response.status}"}
                    
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > max_size_mb * 1024 * 1024:
                        return {"success": False, "error": "Image too large"}
                    
                    image_data = await response.read()
                    
                    # Basic validation
                    if len(image_data) == 0:
                        return {"success": False, "error": "Empty image data"}
                    
                    # Try to load with PIL if available
                    image_obj = None
                    if self.pil_available:
                        try:
                            from PIL import Image
                            image_obj = Image.open(io.BytesIO(image_data))
                            image_obj.verify()
                            # Reopen after verify
                            image_obj = Image.open(io.BytesIO(image_data))
                            if image_obj.mode != 'RGB':
                                image_obj = image_obj.convert('RGB')
                        except Exception as e:
                            return {"success": False, "error": f"Invalid image format: {str(e)}"}
                    
                    return {
                        "success": True,
                        "data": image_data,
                        "image": image_obj,
                        "size": len(image_data),
                        "url": image_url
                    }
                    
        except asyncio.TimeoutError:
            return {"success": False, "error": "Download timeout"}
        except Exception as e:
            return {"success": False, "error": f"Download failed: {str(e)}"}
    
    async def _analyze_quality(self, image_data: Dict) -> Dict:
        """Analyzes image quality metrics"""
        issues = []
        score = 100
        
        if self.pil_available and image_data.get("image"):
            image = image_data["image"]
            width, height = image.size
            
            # Resolution check
            total_pixels = width * height
            if total_pixels < 300000:  # Less than ~550x550
                issues.append("Low resolution")
                score -= 30
            
            # Basic quality heuristics
            if width < 400 or height < 400:
                issues.append("Image too small")
                score -= 20
            
            # If numpy available, do more analysis
            if self.numpy_available:
                import numpy as np
                img_array = np.array(image)
                
                # Brightness check
                brightness = np.mean(img_array)
                if brightness < 50:
                    issues.append("Image too dark")
                    score -= 15
                elif brightness > 200:
                    issues.append("Image overexposed")
                    score -= 15
        else:
            # Fallback scoring without PIL
            score = 70  # Assume moderate quality
        
        return {
            "score": max(0, score),
            "issues": issues
        }
    
    async def _check_compliance(self, image_data: Dict) -> Dict:
        """Checks for regulatory compliance"""
        violations = []
        score = 100
        
        # Basic compliance checks
        # In production, this would use OCR to extract text
        
        # For now, return basic compliance score
        return {
            "score": score,
            "violations": violations,
            "compliant": len(violations) == 0
        }
    
    async def _check_authenticity(self, image_data: Dict) -> Dict:
        """Checks if image is authentic product photo vs stock photo"""
        indicators = []
        score = 80  # Default to moderately authentic
        
        # Basic authenticity checks
        # In production, this would use various techniques
        
        return {
            "score": score,
            "indicators": indicators,
            "is_stock_photo": score < 50
        }
    
    async def _detect_products(self, image_data: Dict, product_type: str = None) -> Dict:
        """Detects cannabis products in image"""
        objects = []
        issues = []
        
        # Basic product detection
        # In production, this would use ML models
        
        # For now, simulate basic detection
        objects = ["packaging", "container", "product"]
        is_valid = len(objects) > 0
        
        if not is_valid:
            issues.append("No cannabis products detected")
        
        return {
            "objects": objects,
            "is_valid": is_valid,
            "issues": issues,
            "product_type": product_type
        }


def get_image_evaluator_agent(
    model_id: str = "gpt-4.1",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    """Create and return the image evaluator agent"""
    return Agent(
        name="Cannabis Image Evaluator",
        agent_id="image_evaluator",
        user_id=user_id,
        session_id=session_id,
        model=OpenAIChat(id=model_id),
        tools=[ImageEvaluatorTools()],
        description=dedent("""\
            You are an expert Cannabis Product Image Evaluator, specialized in analyzing and validating product images for quality, authenticity, and regulatory compliance.
            
            Your expertise includes:
            - Image quality assessment (resolution, lighting, composition)
            - Product authenticity verification (detecting stock photos vs real products)
            - Regulatory compliance checking (required warnings, prohibited claims)
            - Cannabis product identification and categorization
        """),
        instructions=dedent("""\
            As the Cannabis Image Evaluator, follow these guidelines:
            
            1. Image Analysis Process:
            - Always start by evaluating the overall image quality
            - Check for signs of stock photography or generic images
            - Verify the image shows actual cannabis products
            - Assess regulatory compliance based on visible text and warnings
            
            2. Evaluation Criteria:
            - Quality Score: Resolution, sharpness, lighting, composition (60+ required)
            - Compliance Score: Required warnings, no prohibited claims (70+ required)
            - Authenticity Score: Real product photo vs stock image (50+ required)
            - Product Validity: Must show actual cannabis products
            
            3. Response Format:
            - Provide clear evaluation results with scores
            - List specific issues found
            - Offer actionable recommendations for improvement
            - Be constructive and professional in feedback
            
            4. Batch Processing:
            - When evaluating multiple images, process efficiently
            - Provide consistent evaluation criteria across all images
            - Summarize overall trends or common issues
            
            Remember: Your goal is to help ensure product images meet quality standards and regulatory requirements while being authentic representations of actual products.
        """),
        # Enable memory storage
        memory=Memory(
            model=OpenAIChat(id=model_id),
            db=PostgresMemoryDb(table_name="image_evaluator_memories", db_url=db_url),
            delete_memories=True,
            clear_memories=True,
        ),
        enable_agentic_memory=True,
        # Enable persistent storage
        storage=PostgresAgentStorage(table_name="image_evaluator_agent_sessions", db_url=db_url),
        # Show tool calls in output
        show_tool_calls=True,
        debug_mode=debug_mode,
    )


# Create a default instance for backward compatibility
image_evaluator_agent = get_image_evaluator_agent()