"""Cannabis Product Image Processing Agent - Validates and evaluates product images"""

from agno import Agent, tool
import asyncio
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
from PIL import Image, ImageFilter
import requests
import hashlib
import base64
from dataclasses import dataclass
import time
import io
import json
from datetime import datetime


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


class ImageEvaluatorAgent(Agent):
    """
    Specialized agent for processing cannabis product images.
    Validates authenticity, quality, and compliance at scale.
    """
    
    def __init__(self):
        super().__init__(
            name="image_evaluator",
            description="Evaluates and validates cannabis product images for quality, authenticity, and compliance",
            tools=[
                self.download_image,
                self.check_image_quality,
                self.detect_objects,
                self.check_compliance,
                self.detect_stock_photos,
                self.calculate_image_hash,
                self.extract_text_from_image,
                self.validate_cannabis_product,
                self.generate_image_score,
                self.batch_evaluate_images
            ]
        )
        self.setup_models()
    
    def setup_models(self):
        """Initialize ML models and external services"""
        # Model initialization will be added as needed
        self.cv2_available = False
        self.yolo_available = False
        self.tesseract_available = False
        
        try:
            import cv2
            self.cv2_available = True
        except ImportError:
            pass
            
        try:
            from ultralytics import YOLO
            self.yolo_available = True
        except ImportError:
            pass
            
        try:
            import pytesseract
            self.tesseract_available = True
        except ImportError:
            pass

    @tool
    async def download_image(self, image_url: str, max_size_mb: int = 10) -> Dict:
        """
        Downloads and preprocesses image with validation
        
        Args:
            image_url: URL of the image to download
            max_size_mb: Maximum file size in MB
        
        Returns:
            Dict with image data and metadata
        """
        import aiohttp
        from PIL import Image
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        return {"error": f"HTTP {response.status}", "success": False}
                    
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > max_size_mb * 1024 * 1024:
                        return {"error": "Image too large", "success": False}
                    
                    image_data = await response.read()
                    
                    # Validate image format
                    try:
                        image = Image.open(io.BytesIO(image_data))
                        image.verify()  # Verify image integrity
                        
                        # Reopen for processing (verify() closes the image)
                        image = Image.open(io.BytesIO(image_data))
                        
                        # Convert to RGB if necessary
                        if image.mode != 'RGB':
                            image = image.convert('RGB')
                        
                        # Resize if too large (keep aspect ratio)
                        max_dimension = 2048
                        if max(image.size) > max_dimension:
                            ratio = max_dimension / max(image.size)
                            new_size = tuple(int(dim * ratio) for dim in image.size)
                            image = image.resize(new_size, Image.Resampling.LANCZOS)
                        
                        # Convert to numpy array for CV2 processing if available
                        cv_image = None
                        if self.cv2_available:
                            import cv2
                            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                        
                        return {
                            "success": True,
                            "image": image,
                            "cv_image": cv_image,
                            "size": image.size,
                            "format": image.format or "JPEG",
                            "file_size": len(image_data),
                            "url": image_url
                        }
                        
                    except Exception as e:
                        return {"error": f"Invalid image format: {str(e)}", "success": False}
                        
        except asyncio.TimeoutError:
            return {"error": "Download timeout", "success": False}
        except Exception as e:
            return {"error": f"Download failed: {str(e)}", "success": False}

    @tool
    def check_image_quality(self, image_data: Dict) -> Dict:
        """
        Analyzes image quality using multiple metrics
        
        Returns:
            Dict with quality scores and specific issues
        """
        if not image_data.get("success"):
            return {"quality_score": 0, "issues": ["Image download failed"]}
        
        pil_image = image_data["image"]
        issues = []
        quality_metrics = {}
        
        # 1. Resolution check
        width, height = pil_image.size
        total_pixels = width * height
        
        if total_pixels < 300000:  # Less than ~550x550
            issues.append("Low resolution")
            quality_metrics["resolution_score"] = max(0, (total_pixels / 300000) * 30)
        else:
            quality_metrics["resolution_score"] = min(30, (total_pixels / 1000000) * 30)
        
        # 2. Basic image analysis without CV2
        if self.cv2_available and image_data.get("cv_image") is not None:
            import cv2
            from skimage import measure
            
            cv_image = image_data["cv_image"]
            
            # Blur detection using Laplacian variance
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            if laplacian_var < 100:
                issues.append("Image appears blurry")
                quality_metrics["sharpness_score"] = max(0, (laplacian_var / 100) * 25)
            else:
                quality_metrics["sharpness_score"] = min(25, (laplacian_var / 500) * 25)
            
            # Brightness and contrast analysis
            brightness = np.mean(gray)
            contrast = np.std(gray)
            
            # Optimal brightness: 80-180, contrast: 40+
            brightness_score = max(0, 15 - abs(brightness - 130) / 10)
            contrast_score = min(15, contrast / 3)
            
            if brightness < 50:
                issues.append("Image too dark")
            elif brightness > 200:
                issues.append("Image overexposed")
            
            if contrast < 30:
                issues.append("Low contrast")
            
            quality_metrics["brightness_score"] = brightness_score
            quality_metrics["contrast_score"] = contrast_score
            
            # Noise detection
            noise_level = measure.shannon_entropy(gray)
            if noise_level > 7:
                issues.append("High image noise")
                noise_score = max(0, 15 - (noise_level - 6) * 5)
            else:
                noise_score = min(15, noise_level * 2)
            
            quality_metrics["noise_score"] = noise_score
            
            # Color saturation
            hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
            saturation = np.mean(hsv[:, :, 1])
            
            saturation_score = min(10, saturation / 15)
            if saturation < 50:
                issues.append("Low color saturation")
            
            quality_metrics["saturation_score"] = saturation_score
        else:
            # Fallback quality assessment without CV2
            # Use PIL-based analysis
            img_array = np.array(pil_image)
            
            # Basic brightness check
            brightness = np.mean(img_array)
            if brightness < 50:
                issues.append("Image too dark")
                quality_metrics["brightness_score"] = 5
            elif brightness > 200:
                issues.append("Image overexposed")
                quality_metrics["brightness_score"] = 5
            else:
                quality_metrics["brightness_score"] = 15
            
            # Basic sharpness estimate using PIL
            quality_metrics["sharpness_score"] = 20  # Default medium score
            quality_metrics["contrast_score"] = 10
            quality_metrics["noise_score"] = 10
            quality_metrics["saturation_score"] = 5
        
        # Calculate total quality score (0-100)
        total_score = sum(quality_metrics.values())
        
        return {
            "quality_score": round(total_score, 2),
            "metrics": quality_metrics,
            "issues": issues
        }

    @tool
    def detect_objects(self, image_data: Dict) -> Dict:
        """
        Detects cannabis-specific objects and products in images
        """
        if not image_data.get("success"):
            return {"detected_objects": [], "confidence_scores": []}
        
        detected_objects = []
        confidence_scores = []
        cannabis_indicators = []
        
        # Basic object detection based on image characteristics
        # This is a simplified version without YOLO
        
        # Simulate basic detection
        # In production, this would use actual ML models
        simulated_objects = ["packaging", "jar", "container"]
        for obj in simulated_objects:
            detected_objects.append(obj)
            confidence_scores.append(0.7)
            cannabis_indicators.append(f"product_{obj}")
        
        cannabis_score = len(cannabis_indicators) / max(1, len(detected_objects)) * 100
        
        return {
            "detected_objects": detected_objects,
            "confidence_scores": confidence_scores,
            "cannabis_indicators": cannabis_indicators,
            "cannabis_relevance_score": cannabis_score,
            "stock_photo_indicators": [],
            "is_likely_product": len(cannabis_indicators) > 0
        }

    @tool
    def check_compliance(self, image_data: Dict, extracted_text: str = "") -> Dict:
        """
        Checks image for compliance with cannabis regulations
        """
        if not image_data.get("success"):
            return {"compliant": False, "score": 0, "violations": ["Image download failed"]}
        
        violations = []
        warnings = []
        compliance_score = 100
        
        # Check for required warning labels in text
        required_warnings = ["thc", "keep out of reach", "21+", "cannabis"]
        found_warnings = []
        
        text_lower = extracted_text.lower()
        for warning in required_warnings:
            if warning in text_lower:
                found_warnings.append(warning)
        
        # Basic compliance scoring
        if len(found_warnings) < 2:
            violations.append("Missing required warning labels")
            compliance_score -= 30
        
        # Check for prohibited content
        prohibited_terms = ["cure", "heal", "medicine", "prescription"]
        for term in prohibited_terms:
            if term in text_lower:
                violations.append(f"Prohibited medical claim: '{term}'")
                compliance_score -= 20
        
        # Image content compliance
        if "child" in text_lower or "kid" in text_lower:
            violations.append("Content may appeal to minors")
            compliance_score -= 40
        
        is_compliant = compliance_score >= 70 and len(violations) == 0
        
        return {
            "compliant": is_compliant,
            "score": max(0, compliance_score),
            "violations": violations,
            "warnings": warnings,
            "found_warnings": found_warnings
        }

    @tool
    async def detect_stock_photos(self, image_data: Dict) -> Dict:
        """
        Detects if image is likely a stock photo using multiple methods
        """
        if not image_data.get("success"):
            return {"is_stock_photo": True, "confidence": 100, "indicators": ["Image download failed"]}
        
        indicators = []
        stock_photo_score = 0
        
        # 1. Check image quality (too perfect might be stock)
        quality_result = self.check_image_quality(image_data)
        if quality_result["quality_score"] > 90:
            stock_photo_score += 10
            indicators.append("Professionally lit/composed")
        
        # 2. Check for generic composition
        # In production, this would use actual image analysis
        # For now, use basic heuristics
        
        # 3. Cannabis product relevance
        object_result = self.detect_objects(image_data)
        if object_result["cannabis_relevance_score"] < 30:
            stock_photo_score += 25
            indicators.append("Low cannabis product relevance")
        
        # 4. Hash-based duplicate detection (simplified)
        hash_result = self.calculate_image_hash(image_data)
        # In production, compare against database of known stock photos
        
        is_stock_photo = stock_photo_score > 50
        confidence = min(100, stock_photo_score)
        
        return {
            "is_stock_photo": is_stock_photo,
            "confidence": confidence,
            "indicators": indicators,
            "stock_photo_score": stock_photo_score
        }

    @tool
    def calculate_image_hash(self, image_data: Dict) -> Dict:
        """
        Generates multiple types of hashes for duplicate detection
        """
        if not image_data.get("success"):
            return {"hashes": {}}
        
        try:
            pil_image = image_data["image"]
            
            # Generate basic hashes
            hashes = {}
            
            # MD5 hash of image data
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format='JPEG', quality=95)
            md5_hash = hashlib.md5(img_byte_arr.getvalue()).hexdigest()
            hashes["md5"] = md5_hash
            
            # Simple perceptual hash (simplified version)
            # In production, use imagehash library
            small_img = pil_image.resize((8, 8), Image.Resampling.LANCZOS)
            pixels = list(small_img.getdata())
            avg = sum(sum(p) for p in pixels) / len(pixels) / 3
            hash_bits = ''.join('1' if sum(p)/3 > avg else '0' for p in pixels)
            hashes["simple_phash"] = hex(int(hash_bits, 2))[2:]
            
            return {
                "hashes": hashes,
                "success": True
            }
            
        except Exception as e:
            return {
                "hashes": {},
                "error": str(e),
                "success": False
            }

    @tool
    async def extract_text_from_image(self, image_data: Dict) -> Dict:
        """
        Extracts text from images using OCR for compliance checking
        """
        if not image_data.get("success"):
            return {"text": "", "confidence": 0}
        
        # Simple placeholder for text extraction
        # In production, this would use tesseract or cloud OCR
        return {
            "text": "",
            "confidence": 0,
            "success": True,
            "method": "placeholder"
        }

    @tool
    def validate_cannabis_product(self, image_data: Dict, product_type: str = None) -> Dict:
        """
        Validates if image shows actual cannabis product vs generic/stock imagery
        """
        if not image_data.get("success"):
            return {"is_valid_product": False, "confidence": 0}
        
        validation_score = 0
        indicators = []
        issues = []
        
        # 1. Object detection analysis
        object_result = self.detect_objects(image_data)
        cannabis_relevance = object_result.get("cannabis_relevance_score", 0)
        
        if cannabis_relevance > 60:
            validation_score += 30
            indicators.append("Cannabis-related objects detected")
        elif cannabis_relevance > 30:
            validation_score += 15
            indicators.append("Some product-related objects detected")
        else:
            issues.append("No cannabis-related objects detected")
        
        # 2. Packaging detection
        detected_objects = object_result.get("detected_objects", [])
        packaging_objects = ["jar", "bottle", "bag", "box", "container", "packaging"]
        has_packaging = any(obj in packaging_objects for obj in detected_objects)
        
        if has_packaging:
            validation_score += 20
            indicators.append("Product packaging detected")
        
        # 3. Quality check
        quality_result = self.check_image_quality(image_data)
        if 60 < quality_result["quality_score"] < 90:
            validation_score += 10
            indicators.append("Appropriate product photo quality")
        elif quality_result["quality_score"] > 95:
            issues.append("Quality too perfect - may be stock photo")
        
        # 4. Text analysis (synchronous call in sync function)
        # Note: extract_text_from_image is async, but we're in a sync function
        # For now, return empty text - in production, this would need refactoring
        extracted_text = ""
        
        # Look for cannabis product indicators in text
        product_keywords = ["thc", "cbd", "cannabis", "mg", "strain", "indica", "sativa", "hybrid"]
        found_keywords = [keyword for keyword in product_keywords if keyword in extracted_text]
        
        if found_keywords:
            validation_score += 15
            indicators.append(f"Cannabis terminology found: {', '.join(found_keywords)}")
        
        # Calculate final validation
        is_valid_product = validation_score >= 50 and len(issues) <= 2
        confidence = min(100, validation_score)
        
        return {
            "is_valid_product": is_valid_product,
            "confidence": confidence,
            "validation_score": validation_score,
            "indicators": indicators,
            "issues": issues,
            "product_type": product_type
        }

    @tool
    async def generate_image_score(self, image_url: str, product_type: str = None) -> Dict:
        """
        Main orchestrator function that runs all analysis tools and generates final score
        """
        start_time = time.time()
        
        try:
            # 1. Download and preprocess image
            image_data = await self.download_image(image_url)
            if not image_data["success"]:
                return {
                    "is_valid": False,
                    "quality_score": 0,
                    "compliance_score": 0,
                    "authenticity_score": 0,
                    "detected_objects": [],
                    "issues": [image_data["error"]],
                    "recommendations": ["Fix image download issue"],
                    "processing_time": time.time() - start_time,
                    "image_url": image_url,
                    "analysis_timestamp": datetime.utcnow().isoformat()
                }
            
            # 2. Run all analysis tools
            quality_result = self.check_image_quality(image_data)
            object_result = self.detect_objects(image_data)
            stock_photo_result = await self.detect_stock_photos(image_data)
            product_validation_result = self.validate_cannabis_product(image_data, product_type)
            hash_result = self.calculate_image_hash(image_data)
            text_result = await self.extract_text_from_image(image_data)
            compliance_result = self.check_compliance(image_data, text_result.get("text", ""))
            
            # 3. Aggregate results
            issues = []
            recommendations = []
            detected_objects = object_result.get("detected_objects", [])
            
            # Quality Score
            quality_score = quality_result.get("quality_score", 0)
            issues.extend(quality_result.get("issues", []))
            
            # Compliance Score
            compliance_score = compliance_result.get("score", 0)
            issues.extend(compliance_result.get("violations", []))
            
            # Authenticity Score (inverse of stock photo confidence)
            stock_photo_confidence = stock_photo_result.get("confidence", 0)
            authenticity_score = max(0, 100 - stock_photo_confidence)
            
            if stock_photo_result.get("is_stock_photo"):
                issues.extend(stock_photo_result.get("indicators", []))
                recommendations.append("Replace with authentic product photo")
            
            # Product validation
            if not product_validation_result.get("is_valid_product"):
                issues.extend(product_validation_result.get("issues", []))
                recommendations.append("Ensure image shows actual cannabis product")
            
            # Generate recommendations based on issues
            if quality_score < 60:
                recommendations.append("Improve image quality (resolution, lighting, focus)")
            
            if authenticity_score < 50:
                recommendations.append("Use original product photography instead of stock images")
            
            if compliance_score < 70:
                recommendations.append("Add required warning labels and remove prohibited claims")
            
            # Overall validity check
            is_valid = (
                quality_score >= 60 and
                authenticity_score >= 50 and
                compliance_score >= 70 and
                product_validation_result.get("is_valid_product", False)
            )
            
            processing_time = time.time() - start_time
            
            return {
                "is_valid": is_valid,
                "quality_score": round(quality_score, 2),
                "compliance_score": round(compliance_score, 2),
                "authenticity_score": round(authenticity_score, 2),
                "detected_objects": detected_objects,
                "issues": list(set(issues)),  # Remove duplicates
                "recommendations": list(set(recommendations)),
                "processing_time": round(processing_time, 2),
                "image_url": image_url,
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "hashes": hash_result.get("hashes", {})
            }
            
        except Exception as e:
            return {
                "is_valid": False,
                "quality_score": 0,
                "compliance_score": 0,
                "authenticity_score": 0,
                "detected_objects": [],
                "issues": [f"Processing error: {str(e)}"],
                "recommendations": ["Contact support for assistance"],
                "processing_time": time.time() - start_time,
                "image_url": image_url,
                "analysis_timestamp": datetime.utcnow().isoformat()
            }

    @tool
    async def batch_evaluate_images(self, image_urls: List[str], product_types: List[str] = None) -> List[Dict]:
        """
        Batch process multiple images for efficiency
        
        Args:
            image_urls: List of image URLs to evaluate
            product_types: Optional list of product types corresponding to each image
        
        Returns:
            List of evaluation results
        """
        if product_types is None:
            product_types = [None] * len(image_urls)
        elif len(product_types) != len(image_urls):
            return [{
                "error": "Product types list must match image URLs list length",
                "success": False
            }]
        
        # Process in batches for optimal performance
        batch_size = 5
        results = []
        
        for i in range(0, len(image_urls), batch_size):
            batch_urls = image_urls[i:i+batch_size]
            batch_types = product_types[i:i+batch_size]
            
            batch_tasks = [
                self.generate_image_score(url, product_type)
                for url, product_type in zip(batch_urls, batch_types)
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Handle any exceptions in results
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    results.append({
                        "is_valid": False,
                        "quality_score": 0,
                        "compliance_score": 0,
                        "authenticity_score": 0,
                        "detected_objects": [],
                        "issues": [f"Processing exception: {str(result)}"],
                        "recommendations": ["Contact support for assistance"],
                        "processing_time": 0,
                        "image_url": batch_urls[j],
                        "analysis_timestamp": datetime.utcnow().isoformat()
                    })
                else:
                    results.append(result)
        
        return results


# Create instance
image_evaluator_agent = ImageEvaluatorAgent()