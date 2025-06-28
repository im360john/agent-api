"""Competitive Pricing Agent - AI-powered price tracking across competitor websites"""

from textwrap import dedent
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
import asyncio
import json
import re
import os
from decimal import Decimal
from dataclasses import dataclass, asdict
import aiohttp
from urllib.parse import urlparse, quote

from agno.agent import Agent
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.models.openai import OpenAIChat
from agno.storage.agent.postgres import PostgresAgentStorage
from agno.tools.toolkit import Toolkit
from agno.tools.firecrawl import FirecrawlTools
from agno.tools.exa import ExaTools
from agno.tools.reasoning import ReasoningTools

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from db.session import db_url


@dataclass
class PriceData:
    """Structured price data from scraping"""
    product_name: str
    price: float
    member_price: Optional[float] = None
    availability_status: str = "in_stock"  # in_stock, out_of_stock, not_carried
    url: str = ""
    price_tiers: List[Dict[str, Any]] = None
    thc_content: Optional[str] = None
    cbd_content: Optional[str] = None
    package_size: Optional[str] = None
    scraped_at: datetime = None
    raw_data: Optional[Dict] = None
    
    def __post_init__(self):
        if self.scraped_at is None:
            self.scraped_at = datetime.utcnow()
        if self.price_tiers is None:
            self.price_tiers = []


class CompetitorPricingTools(Toolkit):
    """Custom toolkit for competitive price tracking"""
    
    def __init__(self, db_url: str):
        super().__init__(name="competitor_pricing_tools")
        self.db_url = db_url
        self.engine = create_engine(db_url.replace('+asyncpg', '').replace('+aiopg', ''), poolclass=NullPool)
        self.Session = sessionmaker(bind=self.engine)
        
        # API keys from environment
        self.firecrawl_key = os.getenv("FIRECRAWL_API_KEY", "fc-05935e879f594170b09e54181f4dd5f0")
        self.browserbase_key = os.getenv("BROWSERBASE_API_KEY", "bb_live_woocCAM2nkOn71Y5iKYsl34l0L8")
        self.browserbase_project = os.getenv("BROWSERBASE_PROJECT_ID", "e580d1bd-2f55-4b26-bc68-307f51abcbaa")
        self.exa_key = os.getenv("EXA_API_KEY", "9795f6d4-24b1-4f97-a474-3a84caa17a7f")
        
        # Register tools
        self.register(self.track_product)
        self.register(self.add_competitor)
        self.register(self.delete_competitor)
        self.register(self.modify_competitor_urls)
        self.register(self.delete_product)
        self.register(self.list_competitors)
        self.register(self.list_products)
        self.register(self.check_prices)
        self.register(self.bulk_price_check)
        self.register(self.get_price_history)
        self.register(self.analyze_pricing_trends)
        self.register(self.search_product_urls)
        
    async def track_product(self, name: str, brand: str, category: Optional[str] = None, 
                          search_terms: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add a product to price tracking.
        
        Args:
            name: Product name
            brand: Brand name
            category: Product category (edibles, flower, vapes, etc)
            search_terms: Alternative search terms
            metadata: Additional data like THC content, size
            
        Returns:
            Success message with product ID
        """
        try:
            with self.Session() as session:
                # Check if product exists
                result = session.execute(text("""
                    SELECT id FROM pricing.products 
                    WHERE brand = :brand AND name = :name
                """), {"brand": brand, "name": name})
                
                existing = result.fetchone()
                if existing:
                    return f"Product already tracked: {brand} {name} (ID: {existing[0]})"
                
                # Insert new product
                result = session.execute(text("""
                    INSERT INTO pricing.products (name, brand, category, search_terms, metadata)
                    VALUES (:name, :brand, :category, :search_terms, :metadata)
                    RETURNING id
                """), {
                    "name": name,
                    "brand": brand,
                    "category": category,
                    "search_terms": search_terms or [],
                    "metadata": json.dumps(metadata or {})
                })
                
                product_id = result.fetchone()[0]
                session.commit()
                
                return f"✅ Added product to tracking: {brand} {name} (ID: {product_id})"
                
        except Exception as e:
            return f"❌ Error adding product: {str(e)}"
    
    async def add_competitor(self, name: str, urls: List[str], metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add a competitor to track.
        
        Args:
            name: Competitor name
            urls: List of website URLs
            metadata: Additional config like selectors
            
        Returns:
            Success message
        """
        try:
            with self.Session() as session:
                result = session.execute(text("""
                    INSERT INTO pricing.competitors (name, urls, metadata)
                    VALUES (:name, :urls, :metadata)
                    ON CONFLICT (name) 
                    DO UPDATE SET urls = :urls, metadata = :metadata
                    RETURNING id
                """), {
                    "name": name,
                    "urls": urls,
                    "metadata": json.dumps(metadata or {})
                })
                
                competitor_id = result.fetchone()[0]
                session.commit()
                
                return f"✅ Added competitor: {name} with {len(urls)} URL(s) (ID: {competitor_id})"
                
        except Exception as e:
            return f"❌ Error adding competitor: {str(e)}"
    
    async def delete_competitor(self, name: str) -> str:
        """
        Delete a competitor from tracking.
        
        Args:
            name: Competitor name to delete
            
        Returns:
            Success or error message
        """
        try:
            with self.Session() as session:
                # Check if competitor exists
                result = session.execute(text("""
                    SELECT id FROM pricing.competitors WHERE name = :name
                """), {"name": name})
                
                competitor = result.fetchone()
                if not competitor:
                    return f"❌ Competitor '{name}' not found"
                
                competitor_id = competitor[0]
                
                # Delete price history first (due to foreign key constraint)
                session.execute(text("""
                    DELETE FROM pricing.price_history WHERE competitor_id = :competitor_id
                """), {"competitor_id": competitor_id})
                
                # Delete competitor
                session.execute(text("""
                    DELETE FROM pricing.competitors WHERE id = :competitor_id
                """), {"competitor_id": competitor_id})
                
                session.commit()
                return f"✅ Deleted competitor '{name}' and all associated price history"
                
        except Exception as e:
            return f"❌ Error deleting competitor: {str(e)}"
    
    async def modify_competitor_urls(self, name: str, urls: List[str]) -> str:
        """
        Update competitor URLs.
        
        Args:
            name: Competitor name
            urls: New list of URLs
            
        Returns:
            Success or error message
        """
        try:
            with self.Session() as session:
                # Check if competitor exists
                result = session.execute(text("""
                    SELECT id FROM pricing.competitors WHERE name = :name
                """), {"name": name})
                
                competitor = result.fetchone()
                if not competitor:
                    return f"❌ Competitor '{name}' not found"
                
                # Update URLs
                session.execute(text("""
                    UPDATE pricing.competitors 
                    SET urls = :urls, updated_at = CURRENT_TIMESTAMP
                    WHERE name = :name
                """), {
                    "name": name,
                    "urls": urls
                })
                
                session.commit()
                return f"✅ Updated URLs for '{name}' to: {', '.join(urls)}"
                
        except Exception as e:
            return f"❌ Error updating competitor URLs: {str(e)}"
    
    async def delete_product(self, name: str, brand: str) -> str:
        """
        Delete a product from tracking.
        
        Args:
            name: Product name
            brand: Product brand
            
        Returns:
            Success or error message
        """
        try:
            with self.Session() as session:
                # Check if product exists
                result = session.execute(text("""
                    SELECT id FROM pricing.products 
                    WHERE name = :name AND brand = :brand
                """), {"name": name, "brand": brand})
                
                product = result.fetchone()
                if not product:
                    return f"❌ Product '{brand} {name}' not found"
                
                product_id = product[0]
                
                # Delete price history first (due to foreign key constraint)
                session.execute(text("""
                    DELETE FROM pricing.price_history WHERE product_id = :product_id
                """), {"product_id": product_id})
                
                # Delete product
                session.execute(text("""
                    DELETE FROM pricing.products WHERE id = :product_id
                """), {"product_id": product_id})
                
                session.commit()
                return f"✅ Deleted product '{brand} {name}' and all associated price history"
                
        except Exception as e:
            return f"❌ Error deleting product: {str(e)}"
    
    async def list_competitors(self) -> str:
        """
        List all tracked competitors.
        
        Returns:
            Formatted list of competitors
        """
        try:
            with self.Session() as session:
                result = session.execute(text("""
                    SELECT name, urls, enabled, created_at
                    FROM pricing.competitors
                    ORDER BY name
                """))
                
                competitors = result.fetchall()
                
                if not competitors:
                    return "📋 No competitors tracked yet"
                
                output = "📋 **Tracked Competitors:**\n\n"
                for name, urls, enabled, created_at in competitors:
                    status = "✅ Active" if enabled else "❌ Disabled"
                    output += f"• **{name}** - {status}\n"
                    output += f"  URLs: {', '.join(urls)}\n"
                    output += f"  Added: {created_at.strftime('%Y-%m-%d')}\n\n"
                
                return output
                
        except Exception as e:
            return f"❌ Error listing competitors: {str(e)}"
    
    async def list_products(self) -> str:
        """
        List all tracked products.
        
        Returns:
            Formatted list of products
        """
        try:
            with self.Session() as session:
                result = session.execute(text("""
                    SELECT name, brand, category, enabled, created_at
                    FROM pricing.products
                    ORDER BY brand, name
                """))
                
                products = result.fetchall()
                
                if not products:
                    return "📦 No products tracked yet"
                
                output = "📦 **Tracked Products:**\n\n"
                for name, brand, category, enabled, created_at in products:
                    status = "✅ Active" if enabled else "❌ Disabled"
                    cat_text = f" ({category})" if category else ""
                    output += f"• **{brand} {name}**{cat_text} - {status}\n"
                    output += f"  Added: {created_at.strftime('%Y-%m-%d')}\n\n"
                
                return output
                
        except Exception as e:
            return f"❌ Error listing products: {str(e)}"
    
    async def check_prices(self, product_name: str, brand: Optional[str] = None, 
                          competitor_names: List[str] = None, force_refresh: bool = False) -> str:
        """
        Check current prices for a product across competitors.
        
        Args:
            product_name: Product to search for
            brand: Optional brand filter
            competitor_names: Specific competitors to check
            force_refresh: Bypass cache and scrape fresh data
            
        Returns:
            Formatted price comparison
        """
        try:
            with self.Session() as session:
                # Find the product
                query = "SELECT id, name, brand, metadata FROM pricing.products WHERE LOWER(name) LIKE :name"
                params = {"name": f"%{product_name.lower()}%"}
                
                if brand:
                    query += " AND LOWER(brand) = :brand"
                    params["brand"] = brand.lower()
                
                result = session.execute(text(query), params)
                products = result.fetchall()
                
                if not products:
                    return f"❌ Product not found: {product_name}"
                
                # Get competitors
                comp_query = "SELECT id, name, urls FROM pricing.competitors WHERE enabled = true"
                if competitor_names:
                    comp_query += " AND name = ANY(:names)"
                    comp_result = session.execute(text(comp_query), {"names": competitor_names})
                else:
                    comp_result = session.execute(text(comp_query))
                
                competitors = comp_result.fetchall()
                
                # Check cache freshness (default 24 hours)
                cache_hours = 24
                results = []
                
                for product in products:
                    product_id, prod_name, prod_brand, prod_meta = product
                    
                    for competitor in competitors:
                        comp_id, comp_name, comp_urls = competitor
                        
                        # Check if we have recent data
                        if not force_refresh:
                            cache_result = session.execute(text("""
                                SELECT price, member_price, availability_status, scraped_at, url
                                FROM pricing.price_history
                                WHERE product_id = :product_id 
                                  AND competitor_id = :competitor_id
                                  AND scraped_at > :cutoff
                                ORDER BY scraped_at DESC
                                LIMIT 1
                            """), {
                                "product_id": product_id,
                                "competitor_id": comp_id,
                                "cutoff": datetime.utcnow() - timedelta(hours=cache_hours)
                            })
                            
                            cached = cache_result.fetchone()
                            if cached:
                                price, member_price, status, scraped_at, url = cached
                                results.append({
                                    "product": f"{prod_brand} {prod_name}",
                                    "competitor": comp_name,
                                    "price": float(price) if price else None,
                                    "member_price": float(member_price) if member_price else None,
                                    "status": status,
                                    "scraped_at": scraped_at,
                                    "url": url,
                                    "from_cache": True
                                })
                                continue
                        
                        # Need to scrape fresh data
                        search_query = f"{prod_brand} {prod_name}"
                        scraped_data = await self._scrape_competitor_price(
                            comp_name, comp_urls[0], search_query, json.loads(prod_meta) if prod_meta else {}
                        )
                        
                        if scraped_data:
                            # Store in database
                            session.execute(text("""
                                INSERT INTO pricing.price_history 
                                (product_id, competitor_id, price, member_price, availability_status, 
                                 url, scraper_used, raw_data, price_tiers)
                                VALUES (:product_id, :competitor_id, :price, :member_price, 
                                        :availability_status, :url, :scraper_used, :raw_data, :price_tiers)
                            """), {
                                "product_id": product_id,
                                "competitor_id": comp_id,
                                "price": scraped_data.price if scraped_data.price else None,
                                "member_price": scraped_data.member_price,
                                "availability_status": scraped_data.availability_status,
                                "url": scraped_data.url,
                                "scraper_used": "firecrawl",  # TODO: track which scraper was used
                                "raw_data": json.dumps(scraped_data.raw_data),
                                "price_tiers": json.dumps(scraped_data.price_tiers)
                            })
                            
                            results.append({
                                "product": f"{prod_brand} {prod_name}",
                                "competitor": comp_name,
                                "price": scraped_data.price,
                                "member_price": scraped_data.member_price,
                                "status": scraped_data.availability_status,
                                "scraped_at": scraped_data.scraped_at,
                                "url": scraped_data.url,
                                "from_cache": False
                            })
                        else:
                            # Product not found at competitor
                            session.execute(text("""
                                INSERT INTO pricing.price_history 
                                (product_id, competitor_id, availability_status, url, scraper_used)
                                VALUES (:product_id, :competitor_id, 'not_carried', :url, 'firecrawl')
                            """), {
                                "product_id": product_id,
                                "competitor_id": comp_id,
                                "url": comp_urls[0]
                            })
                            
                            results.append({
                                "product": f"{prod_brand} {prod_name}",
                                "competitor": comp_name,
                                "price": None,
                                "status": "not_carried",
                                "scraped_at": datetime.utcnow(),
                                "url": comp_urls[0],
                                "from_cache": False
                            })
                
                session.commit()
                
                # Format results
                return self._format_price_results(results)
                
        except Exception as e:
            return f"❌ Error checking prices: {str(e)}"
    
    async def bulk_price_check(self, products: List[Dict[str, str]], 
                              competitors: List[str] = None) -> str:
        """
        Check prices for multiple products across competitors.
        
        Args:
            products: List of dicts with 'name' and 'brand'
            competitors: Optional list of competitor names
            
        Returns:
            Bulk pricing report
        """
        results = []
        
        for product in products:
            result = await self.check_prices(
                product.get("name"),
                product.get("brand"),
                competitors
            )
            results.append(result)
        
        return "\n\n".join(results)
    
    async def get_price_history(self, product_name: str, brand: str = None, 
                               days: int = 30) -> str:
        """
        Get price history for a product.
        
        Args:
            product_name: Product name
            brand: Optional brand filter
            days: Number of days of history
            
        Returns:
            Price trend analysis
        """
        try:
            with self.Session() as session:
                # Find product
                query = "SELECT id, name, brand FROM pricing.products WHERE LOWER(name) LIKE :name"
                params = {"name": f"%{product_name.lower()}%"}
                
                if brand:
                    query += " AND LOWER(brand) = :brand"
                    params["brand"] = brand.lower()
                
                result = session.execute(text(query), params)
                product = result.fetchone()
                
                if not product:
                    return f"❌ Product not found: {product_name}"
                
                product_id, prod_name, prod_brand = product
                
                # Get price history
                history_result = session.execute(text("""
                    SELECT 
                        c.name as competitor,
                        DATE(ph.scraped_at) as date,
                        AVG(ph.price) as avg_price,
                        MIN(ph.price) as min_price,
                        MAX(ph.price) as max_price,
                        COUNT(*) as samples,
                        SUM(CASE WHEN ph.availability_status = 'in_stock' THEN 1 ELSE 0 END) as in_stock_count
                    FROM pricing.price_history ph
                    JOIN pricing.competitors c ON c.id = ph.competitor_id
                    WHERE ph.product_id = :product_id
                      AND ph.scraped_at >= CURRENT_DATE - INTERVAL :days
                    GROUP BY c.name, DATE(ph.scraped_at)
                    ORDER BY c.name, date DESC
                """), {"product_id": product_id, "days": f"{days} days"})
                
                history_data = history_result.fetchall()
                
                if not history_data:
                    return f"No price history found for {prod_brand} {prod_name} in the last {days} days"
                
                # Format history
                output = f"## Price History: {prod_brand} {prod_name}\n"
                output += f"*Last {days} days*\n\n"
                
                by_competitor = {}
                for row in history_data:
                    comp = row[0]
                    if comp not in by_competitor:
                        by_competitor[comp] = []
                    by_competitor[comp].append(row[1:])
                
                for comp, data in by_competitor.items():
                    output += f"### {comp}\n"
                    output += "| Date | Avg Price | Min | Max | Availability |\n"
                    output += "|------|-----------|-----|-----|-------------|\n"
                    
                    for date, avg_price, min_price, max_price, samples, in_stock in data:
                        availability = f"{(in_stock/samples*100):.0f}%" if samples > 0 else "N/A"
                        output += f"| {date} | ${avg_price:.2f} | ${min_price:.2f} | ${max_price:.2f} | {availability} |\n"
                    
                    output += "\n"
                
                return output
                
        except Exception as e:
            return f"❌ Error getting price history: {str(e)}"
    
    async def analyze_pricing_trends(self, category: str = None, days: int = 7) -> str:
        """
        Analyze pricing trends across products and competitors.
        
        Args:
            category: Optional category filter
            days: Number of days to analyze
            
        Returns:
            Trend analysis report
        """
        try:
            with self.Session() as session:
                # Get recent price changes
                query = """
                    WITH price_changes AS (
                        SELECT 
                            p.brand,
                            p.name,
                            p.category,
                            c.name as competitor,
                            ph1.price as current_price,
                            ph2.price as previous_price,
                            ph1.availability_status as current_status,
                            ph2.availability_status as previous_status,
                            ph1.scraped_at as current_date,
                            ph2.scraped_at as previous_date,
                            CASE 
                                WHEN ph2.price > 0 THEN ((ph1.price - ph2.price) / ph2.price * 100)
                                ELSE 0
                            END as price_change_pct
                        FROM pricing.price_history ph1
                        JOIN pricing.products p ON p.id = ph1.product_id
                        JOIN pricing.competitors c ON c.id = ph1.competitor_id
                        LEFT JOIN LATERAL (
                            SELECT price, availability_status, scraped_at
                            FROM pricing.price_history ph2
                            WHERE ph2.product_id = ph1.product_id
                              AND ph2.competitor_id = ph1.competitor_id
                              AND ph2.scraped_at < ph1.scraped_at
                              AND ph2.scraped_at >= CURRENT_DATE - INTERVAL :days
                            ORDER BY scraped_at DESC
                            LIMIT 1
                        ) ph2 ON true
                        WHERE ph1.scraped_at >= CURRENT_DATE - INTERVAL :days
                    )
                    SELECT * FROM price_changes
                    WHERE previous_price IS NOT NULL
                """
                
                params = {"days": f"{days} days"}
                if category:
                    query += " AND category = :category"
                    params["category"] = category
                
                query += " ORDER BY ABS(price_change_pct) DESC"
                
                result = session.execute(text(query), params)
                trends = result.fetchall()
                
                if not trends:
                    return f"No price trends found for the last {days} days"
                
                # Analyze trends
                output = f"## Pricing Trend Analysis\n"
                output += f"*Last {days} days*\n\n"
                
                # Significant price changes
                output += "### Significant Price Changes\n"
                significant = [t for t in trends if abs(t[10]) > 5]  # More than 5% change
                
                if significant:
                    output += "| Product | Competitor | Previous | Current | Change |\n"
                    output += "|---------|------------|----------|---------|--------|\n"
                    
                    for trend in significant[:10]:  # Top 10
                        brand, name, cat, comp, curr, prev, _, _, _, _, pct = trend
                        arrow = "📈" if pct > 0 else "📉"
                        output += f"| {brand} {name} | {comp} | ${prev:.2f} | ${curr:.2f} | {arrow} {pct:.1f}% |\n"
                else:
                    output += "No significant price changes detected.\n"
                
                output += "\n"
                
                # Availability changes
                availability_changes = [t for t in trends if t[6] != t[7]]
                if availability_changes:
                    output += "### Availability Changes\n"
                    for trend in availability_changes[:10]:
                        brand, name, _, comp, _, _, curr_status, prev_status, _, _, _ = trend
                        output += f"- {brand} {name} at {comp}: {prev_status} → {curr_status}\n"
                
                return output
                
        except Exception as e:
            return f"❌ Error analyzing trends: {str(e)}"
    
    async def search_product_urls(self, product_name: str, brand: str, 
                                 competitor_url: str) -> List[str]:
        """
        Search for product URLs on a competitor site.
        
        Args:
            product_name: Product to search for
            brand: Brand name
            competitor_url: Base URL of competitor site
            
        Returns:
            List of potential product URLs
        """
        try:
            # Use Google search with site: operator for better results
            search_query = f'site:{competitor_url} "{brand}" "{product_name}"'
            
            headers = {
                "X-API-KEY": "7eb754e913754229bd81b68109a9e5139342c334",  # Serper API key
                "Content-Type": "application/json"
            }
            
            payload = {
                "q": search_query,
                "num": 5
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://google.serper.dev/search",
                    json=payload,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        urls = []
                        
                        for result in data.get("organic", []):
                            url = result.get("link", "")
                            if url and self._is_relevant_product_url(url, brand, product_name):
                                urls.append(url)
                        
                        return urls
                    else:
                        return []
                        
        except Exception as e:
            print(f"Error searching URLs: {e}")
            return []
    
    def _is_relevant_product_url(self, url: str, brand: str, product_name: str) -> bool:
        """Check if URL is likely a relevant product page"""
        url_lower = url.lower()
        brand_lower = brand.lower()
        
        # Extract key words from product name
        product_words = [w.lower() for w in product_name.split() if len(w) > 2]
        
        # Check brand
        if brand_lower not in url_lower:
            return False
        
        # Check at least one product word
        if not any(word in url_lower for word in product_words):
            return False
        
        # Avoid category/search pages
        exclude_patterns = ['/search', '/category', '/collections', '/shop/', '?q=', '&q=']
        if any(pattern in url_lower for pattern in exclude_patterns):
            return False
        
        return True
    
    async def _scrape_competitor_price(self, competitor_name: str, competitor_url: str,
                                     search_query: str, product_metadata: Dict) -> Optional[PriceData]:
        """
        Scrape price data from competitor site using Firecrawl/Browserbase.
        
        Args:
            competitor_name: Name of competitor
            competitor_url: Base URL
            search_query: Product search query
            product_metadata: Additional product info
            
        Returns:
            PriceData object or None
        """
        try:
            # First, search for product URLs
            urls = await self.search_product_urls(
                search_query.split()[1] if len(search_query.split()) > 1 else search_query,
                search_query.split()[0] if len(search_query.split()) > 1 else "",
                competitor_url
            )
            
            if not urls:
                print(f"No product URLs found for {search_query} at {competitor_name}")
                return None
            
            # Try Firecrawl first on the top URL
            target_url = urls[0]
            print(f"Scraping {target_url} with Firecrawl...")
            
            # Cannabis product extraction schema
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
                "url": target_url,
                "formats": ["extract"],
                "extract": {
                    "prompt": """Extract cannabis product information including:
                    - Product name (full name including brand)
                    - All price tiers (regular, member, etc.)
                    - THC/CBD content
                    - Package size
                    - Stock status
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
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("success") and data.get("data", {}).get("extract"):
                            extracted = data["data"]["extract"]
                            
                            # Parse prices
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
                            
                            # Determine availability
                            in_stock = extracted.get("in_stock", True)
                            stock_status = extracted.get("stock_status", "")
                            
                            if not in_stock or "out" in stock_status.lower():
                                availability = "out_of_stock"
                            else:
                                availability = "in_stock"
                            
                            return PriceData(
                                product_name=extracted.get("product_name", search_query),
                                price=price,
                                member_price=member_price,
                                availability_status=availability,
                                url=target_url,
                                price_tiers=price_tiers,
                                thc_content=extracted.get("thc_content"),
                                cbd_content=extracted.get("cbd_content"),
                                package_size=extracted.get("package_size"),
                                raw_data=extracted
                            )
            
            # If Firecrawl fails, could fall back to Browserbase here
            print(f"Firecrawl failed for {target_url}, would fall back to Browserbase")
            return None
            
        except Exception as e:
            print(f"Error scraping {competitor_name}: {e}")
            return None
    
    def _format_price_results(self, results: List[Dict]) -> str:
        """Format price results for display"""
        if not results:
            return "No price data available."
        
        # Group by product
        by_product = {}
        for result in results:
            prod = result["product"]
            if prod not in by_product:
                by_product[prod] = []
            by_product[prod].append(result)
        
        output = "## 💰 Competitive Pricing Report\n\n"
        
        for product, data in by_product.items():
            output += f"### {product}\n\n"
            output += "| Competitor | Price | Member Price | Status | Last Updated | Source |\n"
            output += "|------------|-------|--------------|--------|--------------|--------|\n"
            
            # Sort by price
            data.sort(key=lambda x: x.get("price") or float('inf'))
            
            for item in data:
                price = f"${item['price']:.2f}" if item.get('price') else "—"
                member = f"${item['member_price']:.2f}" if item.get('member_price') else "—"
                
                # Status emoji
                status_emoji = {
                    "in_stock": "✅",
                    "out_of_stock": "⚠️",
                    "not_carried": "❌"
                }.get(item['status'], "❓")
                
                status = f"{status_emoji} {item['status'].replace('_', ' ').title()}"
                
                # Time since update
                if item.get('scraped_at'):
                    if isinstance(item['scraped_at'], str):
                        scraped_dt = datetime.fromisoformat(item['scraped_at'].replace('Z', '+00:00'))
                    else:
                        scraped_dt = item['scraped_at']
                    
                    hours_ago = (datetime.utcnow() - scraped_dt).total_seconds() / 3600
                    if hours_ago < 1:
                        time_str = "< 1 hour ago"
                    elif hours_ago < 24:
                        time_str = f"{int(hours_ago)} hours ago"
                    else:
                        time_str = f"{int(hours_ago/24)} days ago"
                    
                    if item.get('from_cache'):
                        time_str += " 📦"
                else:
                    time_str = "Unknown"
                
                # Source
                source = "🔄 Fresh" if not item.get('from_cache') else "💾 Cached"
                
                output += f"| {item['competitor']} | {price} | {member} | {status} | {time_str} | {source} |\n"
            
            # Add insights
            available_prices = [d['price'] for d in data if d.get('price') and d['status'] == 'in_stock']
            if available_prices:
                output += f"\n**Insights:**\n"
                output += f"- 🏆 Best price: ${min(available_prices):.2f} at {data[0]['competitor']}\n"
                output += f"- 📊 Average price: ${sum(available_prices)/len(available_prices):.2f}\n"
                output += f"- 📈 Price range: ${min(available_prices):.2f} - ${max(available_prices):.2f}\n"
                
                # Out of stock warnings
                out_of_stock = [d['competitor'] for d in data if d['status'] == 'out_of_stock']
                if out_of_stock:
                    output += f"- ⚠️ Out of stock at: {', '.join(out_of_stock)}\n"
                
                not_carried = [d['competitor'] for d in data if d['status'] == 'not_carried']
                if not_carried:
                    output += f"- ❌ Not carried by: {', '.join(not_carried)}\n"
            
            output += "\n"
        
        return output


def get_competitive_pricing_agent(
    model_id: str = "gpt-4o",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    """Create and return the competitive pricing agent"""
    
    # Initialize tools
    pricing_tools = CompetitorPricingTools(db_url=db_url)
    
    # Create reasoning tools for analysis
    reasoning_tools = ReasoningTools(
        think=True,
        analyze=True,
        add_instructions=True,
        add_few_shot=True
    )
    
    # Add Firecrawl for direct scraping when needed
    firecrawl_tools = FirecrawlTools(
        scrape=True,
        crawl=False,  # Don't need full site crawling
        api_key=os.getenv("FIRECRAWL_API_KEY", "fc-05935e879f594170b09e54181f4dd5f0")
    )
    
    # Add Exa for finding products across the web
    exa_tools = ExaTools(
        search=True,
        find_similar=True,
        get_contents=True,
        api_key=os.getenv("EXA_API_KEY", "9795f6d4-24b1-4f97-a474-3a84caa17a7f")
    )
    
    return Agent(
        name="Competitive Pricing Intelligence Agent",
        agent_id="competitive_pricing",
        user_id=user_id,
        session_id=session_id,
        model=OpenAIChat(id=model_id),
        tools=[pricing_tools, reasoning_tools, firecrawl_tools, exa_tools],
        description=dedent("""\
            You are an expert competitive pricing intelligence agent that tracks and analyzes product prices across e-commerce websites.
            
            You can monitor single or multiple products across any number of competitors, identify pricing trends, 
            and provide strategic insights about market positioning and availability.
        """),
        instructions=dedent("""\
            You are a competitive pricing intelligence expert. Your mission is to help users track and analyze product prices across competitor websites.
            
            ## Core Capabilities:
            
            1. **Product Tracking**
               - Add products with `track_product` including brand, name, category
               - Remove products with `delete_product` (requires brand and name)
               - List all products with `list_products`
               - Support variants (size, flavor, potency)
               - Handle cannabis products with THC/CBD content
            
            2. **Competitor Management**
               - Add competitors with `add_competitor` 
               - Update competitor URLs with `modify_competitor_urls`
               - Remove competitors with `delete_competitor`
               - List all competitors with `list_competitors`
               - Support multiple URLs per competitor
               - Track both carried and not-carried products
            
            3. **Price Monitoring**
               - Use `check_prices` for current pricing (checks cache first)
               - Use `bulk_price_check` for multiple products
               - Force refresh with force_refresh=True parameter
               - Track regular and member pricing tiers
            
            4. **Analysis & Insights**
               - Use `get_price_history` for trend data
               - Use `analyze_pricing_trends` for market insights
               - Identify pricing patterns and opportunities
            
            ## Workflow for New Requests:
            
            1. **Single Product Check**:
               - First check if product is already tracked
               - If not, use `track_product` to add it
               - Then use `check_prices` to get current data
            
            2. **Bulk Analysis**:
               - Add all products and competitors first
               - Use `bulk_price_check` for efficiency
               - Follow up with trend analysis
            
            3. **Web Scraping Strategy**:
               - System automatically tries Firecrawl first (fast, LLM-powered)
               - Falls back to Browserbase for JavaScript-heavy sites
               - Uses Exa to find product pages across the web
            
            ## Important Notes:
            
            - **Caching**: Prices are cached for 24 hours by default
            - **Availability**: Track "in_stock", "out_of_stock", and "not_carried" - all are valuable
            - **Accuracy**: Always verify brand and product names match exactly
            - **Variants**: Different sizes/flavors are separate products
            
            ## Example Searches:
            - "Track Wyld Strawberry Gummies across all dispensaries"
            - "Compare prices for all Camino gummies at Harborside and Elemental"
            - "Show me price trends for flower products this week"
            - "Which competitors don't carry STIIIZY products?"
            
            When presenting results:
            - Show price comparisons in clear tables
            - Highlight best prices and out-of-stock items
            - Include time since last update
            - Provide actionable insights
            
            For cannabis products specifically:
            - Always note THC/CBD content
            - Track package sizes (grams, mg, units)
            - Consider member vs recreational pricing
            
            User context:
            - User ID: {current_user_id}
            - Session: {current_session_id}
        """),
        # Enable memory
        memory=Memory(
            model=OpenAIChat(id=model_id),
            db=PostgresMemoryDb(table_name="competitive_pricing_memories", db_url=db_url),
            delete_memories=True,
            clear_memories=True,
        ),
        enable_agentic_memory=True,
        # Enable storage
        storage=PostgresAgentStorage(
            table_name="competitive_pricing_agent_sessions", 
            db_url=db_url
        ),
        add_history_to_messages=True,
        num_history_runs=5,  # Keep more history for context
        read_chat_history=True,
        # Formatting
        markdown=True,
        add_datetime_to_instructions=True,
        add_state_in_messages=True,
        show_tool_calls=True,
        debug_mode=debug_mode,
    )