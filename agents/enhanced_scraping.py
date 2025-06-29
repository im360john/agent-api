"""Enhanced scraping with detailed logging and confidence scoring"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass, asdict
import aiohttp
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Set up logger
logger = logging.getLogger(__name__)

@dataclass
class ScrapingResult:
    """Enhanced scraping result with confidence scores"""
    success: bool
    tool_used: str
    url_scraped: str
    duration_ms: int
    price_data: Optional['PriceData'] = None
    confidence_score: float = 0.0
    price_confidence: str = 'low'  # high, medium, low
    stock_confidence: str = 'low'  # high, medium, low
    error_message: Optional[str] = None
    raw_response: Optional[Dict] = None


class EnhancedScraper:
    """Enhanced scraper with detailed logging and confidence scoring"""
    
    def __init__(self, db_url: str, firecrawl_key: str, browserbase_key: str = None, exa_key: str = None):
        self.db_url = db_url
        self.firecrawl_key = firecrawl_key
        self.browserbase_key = browserbase_key
        self.exa_key = exa_key
        
        # Create database session
        self.engine = create_engine(db_url.replace('+asyncpg', '').replace('+aiopg', ''))
        self.Session = sessionmaker(bind=self.engine)
    
    async def scrape_with_confidence(
        self, 
        competitor_name: str,
        competitor_id: int,
        competitor_url: str,
        search_query: str,
        product_metadata: Optional[Dict] = None
    ) -> ScrapingResult:
        """
        Scrape with detailed logging and confidence scoring.
        
        Returns ScrapingResult with confidence scores and detailed information.
        """
        start_time = datetime.now()
        
        # First, check knowledge base for patterns
        learned_patterns = self._get_learned_patterns(competitor_id)
        
        # Try Firecrawl first
        result = await self._try_firecrawl(
            competitor_name, competitor_id, competitor_url, 
            search_query, product_metadata, learned_patterns
        )
        
        # If Firecrawl fails and we have other tools, try them
        if not result.success and self.browserbase_key:
            logger.info(f"Firecrawl failed for {competitor_name}, trying Browserbase...")
            result = await self._try_browserbase(
                competitor_name, competitor_id, competitor_url,
                search_query, product_metadata, learned_patterns
            )
        
        # Log the scraping attempt
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        result.duration_ms = duration_ms
        
        # Store metrics in database
        self._store_scraping_metrics(
            competitor_id, competitor_name, search_query,
            result
        )
        
        # Update learned patterns based on result
        if result.success:
            self._update_learned_patterns(competitor_id, result)
        
        return result
    
    async def _try_firecrawl(
        self,
        competitor_name: str,
        competitor_id: int, 
        competitor_url: str,
        search_query: str,
        product_metadata: Optional[Dict],
        learned_patterns: Dict
    ) -> ScrapingResult:
        """Try scraping with Firecrawl"""
        
        # Get URLs to try
        urls = await self._get_product_urls(
            competitor_url, search_query, product_metadata, learned_patterns
        )
        
        if not urls:
            logger.warning(f"No URLs found for {search_query} at {competitor_name}")
            return ScrapingResult(
                success=False,
                tool_used='firecrawl',
                url_scraped='',
                duration_ms=0,
                error_message='No product URLs found'
            )
        
        # Try each URL
        for url in urls[:3]:  # Try top 3 URLs
            logger.info(f"Attempting Firecrawl scrape of {url}")
            
            try:
                result = await self._firecrawl_scrape(url, search_query)
                if result.success:
                    logger.info(f"Successfully scraped {url} with Firecrawl")
                    result.url_scraped = url
                    return result
            except Exception as e:
                logger.error(f"Error scraping {url} with Firecrawl: {e}")
                continue
        
        return ScrapingResult(
            success=False,
            tool_used='firecrawl',
            url_scraped=urls[0] if urls else '',
            duration_ms=0,
            error_message='All URLs failed'
        )
    
    async def _firecrawl_scrape(self, url: str, search_query: str) -> ScrapingResult:
        """Execute Firecrawl scraping"""
        
        extraction_schema = {
            "type": "object",
            "properties": {
                "product_name": {"type": "string"},
                "prices": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tier": {"type": "string"},
                            "price": {"type": "number"}
                        }
                    }
                },
                "regular_price": {"type": "number"},
                "member_price": {"type": "number"},
                "thc_content": {"type": "string"},
                "cbd_content": {"type": "string"},
                "package_size": {"type": "string"},
                "in_stock": {"type": "boolean"},
                "stock_status": {"type": "string"},
                "category": {"type": "string"}
            }
        }
        
        headers = {
            "Authorization": f"Bearer {self.firecrawl_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "url": url,
            "formats": ["extract", "markdown"],  # Get both for analysis
            "extract": {
                "prompt": """Extract cannabis product information including:
                - Product name (full name including brand)
                - All price tiers (regular, member, etc.)
                - THC/CBD content
                - Package size
                - Stock status (be very explicit about in stock vs out of stock)
                - Category
                Return structured data.""",
                "schema": extraction_schema
            },
            "timeout": 30000,
            "waitFor": 3000
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.firecrawl.dev/v1/scrape",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=35)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Firecrawl error: {error_text}")
                    return ScrapingResult(
                        success=False,
                        tool_used='firecrawl',
                        url_scraped=url,
                        duration_ms=0,
                        error_message=f"HTTP {response.status}: {error_text}"
                    )
                
                data = await response.json()
                
                if not data.get("success") or not data.get("data", {}).get("extract"):
                    return ScrapingResult(
                        success=False,
                        tool_used='firecrawl',
                        url_scraped=url,
                        duration_ms=0,
                        error_message="No data extracted",
                        raw_response=data
                    )
                
                extracted = data["data"]["extract"]
                markdown = data["data"].get("markdown", "")
                
                # Calculate confidence scores
                price_confidence, stock_confidence, overall_confidence = self._calculate_confidence(
                    extracted, markdown, search_query
                )
                
                # Parse price data
                from agents.competitive_pricing_agent import PriceData
                
                regular_price = extracted.get("regular_price", 0)
                member_price = extracted.get("member_price")
                price_tiers = extracted.get("prices", [])
                
                # Determine primary price
                if regular_price > 0:
                    price = regular_price
                elif price_tiers:
                    price = price_tiers[0].get("price", 0)
                else:
                    price = 0
                
                # Determine availability with confidence
                in_stock = extracted.get("in_stock", True)
                stock_status = extracted.get("stock_status", "")
                
                if not in_stock or "out" in stock_status.lower():
                    availability = "out_of_stock"
                elif price == 0:
                    availability = "not_carried"
                else:
                    availability = "in_stock"
                
                price_data = PriceData(
                    product_name=extracted.get("product_name", search_query),
                    price=price,
                    member_price=member_price,
                    availability_status=availability,
                    url=url,
                    price_tiers=price_tiers,
                    thc_content=extracted.get("thc_content"),
                    cbd_content=extracted.get("cbd_content"),
                    package_size=extracted.get("package_size"),
                    raw_data=extracted
                )
                
                return ScrapingResult(
                    success=True,
                    tool_used='firecrawl',
                    url_scraped=url,
                    duration_ms=0,
                    price_data=price_data,
                    confidence_score=overall_confidence,
                    price_confidence=price_confidence,
                    stock_confidence=stock_confidence,
                    raw_response=data
                )
    
    def _calculate_confidence(
        self, 
        extracted_data: Dict, 
        markdown_content: str,
        search_query: str
    ) -> Tuple[str, str, float]:
        """
        Calculate confidence scores for price and stock status.
        
        Returns: (price_confidence, stock_confidence, overall_confidence)
        """
        price_confidence_score = 0.0
        stock_confidence_score = 0.0
        
        # Price confidence factors
        if extracted_data.get("regular_price", 0) > 0:
            price_confidence_score += 0.4
        if extracted_data.get("prices"):
            price_confidence_score += 0.3
        if "$" in markdown_content:
            price_confidence_score += 0.2
        if extracted_data.get("member_price") is not None:
            price_confidence_score += 0.1
        
        # Stock confidence factors
        if "in_stock" in extracted_data:
            stock_confidence_score += 0.4
        if extracted_data.get("stock_status"):
            stock_confidence_score += 0.3
        stock_keywords = ["in stock", "out of stock", "available", "sold out", "add to cart"]
        if any(keyword in markdown_content.lower() for keyword in stock_keywords):
            stock_confidence_score += 0.3
        
        # Product match confidence
        product_match_score = 0.0
        search_lower = search_query.lower()
        found_name = extracted_data.get("product_name", "").lower()
        
        if search_lower in found_name or found_name in search_lower:
            product_match_score = 1.0
        else:
            # Partial match scoring
            search_words = set(search_lower.split())
            found_words = set(found_name.split())
            common_words = search_words & found_words
            if search_words:
                product_match_score = len(common_words) / len(search_words)
        
        # Convert to categories
        price_confidence = self._score_to_category(price_confidence_score)
        stock_confidence = self._score_to_category(stock_confidence_score)
        
        # Overall confidence is weighted average
        overall_confidence = (
            price_confidence_score * 0.4 +
            stock_confidence_score * 0.3 +
            product_match_score * 0.3
        )
        
        return price_confidence, stock_confidence, overall_confidence
    
    def _score_to_category(self, score: float) -> str:
        """Convert numeric score to category"""
        if score >= 0.7:
            return 'high'
        elif score >= 0.4:
            return 'medium'
        else:
            return 'low'
    
    async def _get_product_urls(
        self,
        competitor_url: str,
        search_query: str,
        product_metadata: Optional[Dict],
        learned_patterns: Dict
    ) -> List[str]:
        """Get product URLs using various methods"""
        urls = []
        
        # Try learned URL patterns first
        if 'url_patterns' in learned_patterns:
            for pattern in learned_patterns['url_patterns']:
                # Apply pattern (this is simplified, real implementation would be more complex)
                url = pattern.replace('{query}', search_query.replace(' ', '+'))
                urls.append(url)
        
        # Use Exa search if available
        if self.exa_key:
            exa_urls = await self._search_with_exa(competitor_url, search_query)
            urls.extend(exa_urls)
        
        # Fallback to basic search construction
        if not urls:
            base_url = competitor_url.rstrip('/')
            search_paths = [
                f"/search?q={search_query.replace(' ', '+')}",
                f"/products/search?query={search_query.replace(' ', '+')}",
                f"/menu?search={search_query.replace(' ', '+')}"
            ]
            for path in search_paths:
                urls.append(base_url + path)
        
        return urls
    
    async def _search_with_exa(self, competitor_url: str, search_query: str) -> List[str]:
        """Search for product URLs using Exa"""
        # Implementation would go here
        return []
    
    def _get_learned_patterns(self, competitor_id: int) -> Dict:
        """Get learned patterns from knowledge base"""
        patterns = {
            'url_patterns': [],
            'selectors': {},
            'indicators': {}
        }
        
        try:
            with self.Session() as session:
                result = session.execute(text("""
                    SELECT pattern_type, pattern_value, success_rate, metadata
                    FROM pricing.learned_patterns
                    WHERE competitor_id = :competitor_id
                    AND success_rate > 0.5
                    ORDER BY success_rate DESC
                """), {"competitor_id": competitor_id})
                
                for row in result:
                    pattern_type, pattern_value, success_rate, metadata = row
                    if pattern_type == 'url_structure':
                        patterns['url_patterns'].append(pattern_value)
                    elif pattern_type == 'price_selector':
                        patterns['selectors']['price'] = pattern_value
                    elif pattern_type == 'stock_indicator':
                        patterns['indicators']['stock'] = pattern_value
        except Exception as e:
            logger.error(f"Error getting learned patterns: {e}")
        
        return patterns
    
    def _store_scraping_metrics(
        self,
        competitor_id: int,
        competitor_name: str,
        search_query: str,
        result: ScrapingResult
    ):
        """Store scraping metrics in database"""
        try:
            with self.Session() as session:
                session.execute(text("""
                    INSERT INTO pricing.scraping_metrics (
                        competitor_id, competitor_name, product_search,
                        tool_used, url_attempted, success,
                        confidence_score, price_confidence, stock_confidence,
                        response_time_ms, error_message, scraped_data
                    ) VALUES (
                        :competitor_id, :competitor_name, :product_search,
                        :tool_used, :url_attempted, :success,
                        :confidence_score, :price_confidence, :stock_confidence,
                        :response_time_ms, :error_message, :scraped_data
                    )
                """), {
                    "competitor_id": competitor_id,
                    "competitor_name": competitor_name,
                    "product_search": search_query,
                    "tool_used": result.tool_used,
                    "url_attempted": result.url_scraped,
                    "success": result.success,
                    "confidence_score": result.confidence_score,
                    "price_confidence": result.price_confidence,
                    "stock_confidence": result.stock_confidence,
                    "response_time_ms": result.duration_ms,
                    "error_message": result.error_message,
                    "scraped_data": json.dumps(result.raw_response) if result.raw_response else None
                })
                session.commit()
        except Exception as e:
            logger.error(f"Error storing scraping metrics: {e}")
    
    def _update_learned_patterns(self, competitor_id: int, result: ScrapingResult):
        """Update learned patterns based on successful scrape"""
        # This would analyze the successful scrape and update patterns
        # Implementation depends on specific pattern learning logic
        pass
    
    async def _try_browserbase(
        self,
        competitor_name: str,
        competitor_id: int,
        competitor_url: str,
        search_query: str,
        product_metadata: Optional[Dict],
        learned_patterns: Dict
    ) -> ScrapingResult:
        """Try scraping with Browserbase (placeholder)"""
        # Implementation would go here
        return ScrapingResult(
            success=False,
            tool_used='browserbase',
            url_scraped='',
            duration_ms=0,
            error_message='Browserbase not implemented yet'
        )