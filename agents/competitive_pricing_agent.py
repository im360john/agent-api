"""Competitive Pricing Agent - AI-powered price tracking across competitor websites"""

from textwrap import dedent
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta, timezone
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
            self.scraped_at = datetime.now(timezone.utc)
        if self.price_tiers is None:
            self.price_tiers = []


class CompetitorPricingTools(Toolkit):
    """Custom toolkit for competitive price tracking"""
    
    def __init__(self, db_url: str):
        super().__init__(name="competitor_pricing_tools")
        self.db_url = db_url
        # Create engine with pool_pre_ping to handle stale connections
        self.engine = create_engine(
            db_url.replace('+asyncpg', '').replace('+aiopg', ''), 
            poolclass=NullPool,
            pool_pre_ping=True  # Test connections before using them
        )
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
        self.register(self.analyze_price_freshness)
        self.register(self.check_prices)
        self.register(self.bulk_price_check)
        self.register(self.get_price_history)
        self.register(self.analyze_pricing_trends)
        self.register(self.search_product_urls)
        self.register(self.discover_product_variants)
        # Batch processing tools
        self.register(self.create_batch_job)
        self.register(self.check_batch_status)
        self.register(self.get_batch_results)
        self.register(self.list_batch_jobs)
        
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
                
                return f"Added product to tracking: {brand} {name} (ID: {product_id})"
                
        except Exception as e:
            return f"Error adding product: {str(e)}"
    
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
                
                return f"Added competitor: {name} with {len(urls)} URL(s) (ID: {competitor_id})"
                
        except Exception as e:
            return f"Error adding competitor: {str(e)}"
    
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
                    return f"Competitor '{name}' not found"
                
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
                return f"Deleted competitor '{name}' and all associated price history"
                
        except Exception as e:
            return f"Error deleting competitor: {str(e)}"
    
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
                    return f"Competitor '{name}' not found"
                
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
                return f"Updated URLs for '{name}' to: {', '.join(urls)}"
                
        except Exception as e:
            return f"Error updating competitor URLs: {str(e)}"
    
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
                    return f"Product '{brand} {name}' not found"
                
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
                return f"Deleted product '{brand} {name}' and all associated price history"
                
        except Exception as e:
            return f"Error deleting product: {str(e)}"
    
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
                    return "No competitors tracked yet"
                
                output = "**Tracked Competitors:**\n\n"
                for name, urls, enabled, created_at in competitors:
                    status = "Active" if enabled else "Disabled"
                    output += f"• **{name}** - {status}\n"
                    output += f"  URLs: {', '.join(urls)}\n"
                    output += f"  Added: {created_at.strftime('%Y-%m-%d')}\n\n"
                
                return output
                
        except Exception as e:
            return f"Error listing competitors: {str(e)}"
    
    async def list_products(self) -> str:
        """
        List all tracked products.
        
        Returns:
            Formatted list of products
        """
        try:
            with self.Session() as session:
                # Check if enabled column exists
                try:
                    result = session.execute(text("""
                        SELECT name, brand, category, enabled, created_at
                        FROM pricing.products
                        ORDER BY brand, name
                    """))
                    has_enabled = True
                except Exception as e:
                    # Rollback the failed transaction
                    session.rollback()
                    # Fallback for databases without enabled column
                    result = session.execute(text("""
                        SELECT name, brand, category, true as enabled, created_at
                        FROM pricing.products
                        ORDER BY brand, name
                    """))
                    has_enabled = False
                
                products = result.fetchall()
                
                if not products:
                    return " No products tracked yet"
                
                output = " **Tracked Products:**\n\n"
                for name, brand, category, enabled, created_at in products:
                    status = "Active" if enabled else "Disabled"
                    cat_text = f" ({category})" if category else ""
                    output += f"• **{brand} {name}**{cat_text}"
                    if has_enabled:
                        output += f" - {status}"
                    output += f"\n  Added: {created_at.strftime('%Y-%m-%d')}\n\n"
                
                return output
                
        except Exception as e:
            return f"Error listing products: {str(e)}"
    
    async def analyze_price_freshness(self, product_name: Optional[str] = None, 
                                     brand: Optional[str] = None,
                                     competitor_names: Optional[List[str]] = None) -> str:
        """
        Analyze the freshness of price data in the system.
        
        Args:
            product_name: Optional product filter
            brand: Optional brand filter
            competitor_names: Optional list of competitors to check
            
        Returns:
            Freshness analysis report
        """
        try:
            with self.Session() as session:
                # Try to use materialized view first, fall back to direct query if not available
                try:
                    # Build query for latest prices
                    query = text("""
                        SELECT 
                            lp.product_name,
                            lp.brand,
                            lp.competitor_name,
                            lp.price,
                            lp.scraped_at,
                            lp.hours_old,
                            lp.freshness_status,
                            lp.availability_status
                        FROM pricing.latest_prices lp
                        WHERE 1=1
                    """)
                    
                    params = {}
                    
                    # Add filters if provided
                    if product_name and brand:
                        query = text(str(query) + " AND lp.product_name = :product_name AND lp.brand = :brand")
                        params["product_name"] = product_name
                        params["brand"] = brand
                    elif product_name:
                        query = text(str(query) + " AND lp.product_name ILIKE :product_pattern")
                        params["product_pattern"] = f"%{product_name}%"
                    
                    if competitor_names:
                        query = text(str(query) + " AND lp.competitor_name = ANY(:competitors)")
                        params["competitors"] = competitor_names
                    
                    query = text(str(query) + " ORDER BY lp.hours_old DESC")
                    
                    result = session.execute(query, params)
                    data = result.fetchall()
                except Exception as e:
                    # Rollback the failed transaction
                    session.rollback()
                    # Fallback to direct query if materialized view doesn't exist
                    query = text("""
                        SELECT DISTINCT ON (p.id, c.id)
                            p.name as product_name,
                            p.brand,
                            c.name as competitor_name,
                            ph.price,
                            ph.scraped_at,
                            EXTRACT(EPOCH FROM (NOW() - ph.scraped_at))/3600 as hours_old,
                            CASE 
                                WHEN EXTRACT(EPOCH FROM (NOW() - ph.scraped_at))/3600 < 12 THEN 'fresh'
                                WHEN EXTRACT(EPOCH FROM (NOW() - ph.scraped_at))/3600 < 24 THEN 'stale'
                                ELSE 'old'
                            END as freshness_status,
                            ph.availability_status
                        FROM pricing.price_history ph
                        JOIN pricing.products p ON ph.product_id = p.id
                        JOIN pricing.competitors c ON ph.competitor_id = c.id
                        WHERE 1=1
                    """)
                    
                    params = {}
                    
                    # Add filters if provided
                    if product_name and brand:
                        query = text(str(query) + " AND p.name = :product_name AND p.brand = :brand")
                        params["product_name"] = product_name
                        params["brand"] = brand
                    elif product_name:
                        query = text(str(query) + " AND p.name ILIKE :product_pattern")
                        params["product_pattern"] = f"%{product_name}%"
                    
                    if competitor_names:
                        query = text(str(query) + " AND c.name = ANY(:competitors)")
                        params["competitors"] = competitor_names
                    
                    query = text(str(query) + " ORDER BY p.id, c.id, ph.scraped_at DESC")
                    
                    result = session.execute(query, params)
                    data = result.fetchall()
                
                if not data:
                    return "No price data found for the specified criteria"
                
                # Categorize by freshness
                fresh_count = sum(1 for row in data if row[6] == 'fresh')
                stale_count = sum(1 for row in data if row[6] == 'stale')
                old_count = sum(1 for row in data if row[6] == 'old')
                
                output = "**Price Data Freshness Analysis**\n\n"
                
                # Summary
                output += f"**Summary:**\n"
                output += f"- Total price points: {len(data)}\n"
                output += f"- Fresh (<12h): {fresh_count} ({fresh_count/len(data)*100:.1f}%)\n"
                output += f"- Stale (12-24h): {stale_count} ({stale_count/len(data)*100:.1f}%)\n"
                output += f"- Old (>24h): {old_count} ({old_count/len(data)*100:.1f}%)\n\n"
                
                # Recommendations
                if old_count > 0:
                    output += f"**Recommendation:** {old_count} price points need updating (>24h old)\n\n"
                elif stale_count > len(data) * 0.5:
                    output += f"**Suggestion:** Consider refreshing {stale_count} stale price points\n\n"
                else:
                    output += "**Status:** Most price data is fresh\n\n"
                
                # Detailed breakdown
                output += "**Detailed Breakdown:**\n\n"
                
                # Group by product
                from collections import defaultdict
                by_product = defaultdict(list)
                
                for row in data:
                    prod_key = f"{row[1]} {row[0]}"  # brand + name
                    by_product[prod_key].append(row)
                
                for product, rows in sorted(by_product.items()):
                    output += f"**{product}**\n"
                    
                    for row in sorted(rows, key=lambda x: x[5]):  # Sort by hours_old
                        comp_name = row[2]
                        price = f"${row[3]:.2f}" if row[3] else "N/A"
                        hours = row[5]
                        status_icon = {"fresh": "", "stale": "", "old": ""}.get(row[6], "")
                        avail = row[7]
                        
                        if hours < 1:
                            time_str = "< 1 hour ago"
                        else:
                            time_str = f"{int(hours)} hours ago"
                        
                        output += f"  - {comp_name}: {price} - {status_icon} {time_str}"
                        if avail != "in_stock":
                            output += f" ({avail})"
                        output += "\n"
                    
                    output += "\n"
                
                # Quick refresh suggestions
                old_items = [row for row in data if row[6] == 'old']
                if old_items:
                    output += "**Quick Refresh Needed:**\n"
                    for row in old_items[:5]:  # Show first 5
                        output += f"- {row[1]} {row[0]} at {row[2]}\n"
                    if len(old_items) > 5:
                        output += f"- ... and {len(old_items) - 5} more\n"
                
                return output
                
        except Exception as e:
            # Check if materialized view exists
            if "latest_prices" in str(e):
                return "Freshness analysis not available. Database views may need to be created."
            return f"Error analyzing freshness: {str(e)}"
    
    async def check_prices(self, product_name: str, brand: Optional[str] = None, 
                          competitor_names: Optional[List[str]] = None, force_refresh: bool = False) -> str:
        """
        Check current prices for a product across competitors with smart freshness awareness.
        
        Args:
            product_name: Product to search for
            brand: Optional brand filter
            competitor_names: Specific competitors to check
            force_refresh: Bypass cache and scrape fresh data
            
        Returns:
            Formatted price comparison with freshness indicators
        """
        try:
            with self.Session() as session:
                # Find the product - first try exact match
                query = "SELECT id, name, brand, metadata FROM pricing.products WHERE LOWER(name) LIKE :name"
                params = {"name": f"%{product_name.lower()}%"}
                
                if brand:
                    query += " AND LOWER(brand) = :brand"
                    params["brand"] = brand.lower()
                
                result = session.execute(text(query), params)
                products = result.fetchall()
                
                # If no exact match, try to find variants
                if not products and brand:
                    # Extract base product name (remove dosage, ratios, etc)
                    base_words = []
                    for word in product_name.split():
                        # Skip common variant indicators
                        if not any(indicator in word.lower() for indicator in ['mg', 'cbd', 'thc', ':', '100', '50', '20', '10', '5']):
                            base_words.append(word)
                    
                    if base_words:
                        base_product = ' '.join(base_words)
                        
                        # Search for all variants of this base product
                        variant_query = """
                            SELECT id, name, brand, metadata 
                            FROM pricing.products 
                            WHERE LOWER(brand) = :brand 
                            AND LOWER(name) LIKE :base_pattern
                            ORDER BY name
                        """
                        variant_params = {
                            "brand": brand.lower(),
                            "base_pattern": f"%{base_product.lower()}%"
                        }
                        
                        variant_result = session.execute(text(variant_query), variant_params)
                        variants = variant_result.fetchall()
                        
                        if variants:
                            # Show available variants
                            output = f"Exact product '{product_name}' not found.\n\n"
                            output += f"**Available {brand} variants containing '{base_product}':**\n"
                            for _, var_name, var_brand, _ in variants:
                                output += f"• {var_brand} {var_name}\n"
                            
                            output += f"\n**Tip:** Search for a specific variant from the list above for accurate pricing."
                            output += f"\n\n**Showing prices for all {base_product} variants:**\n"
                            
                            # Set products to all variants for price checking
                            products = variants
                
                if not products:
                    return f"Product not found: {product_name}"
                
                # Get competitors
                comp_query = "SELECT id, name, urls FROM pricing.competitors WHERE enabled = true"
                if competitor_names:
                    comp_query += " AND name = ANY(:names)"
                    comp_result = session.execute(text(comp_query), {"names": competitor_names})
                else:
                    comp_result = session.execute(text(comp_query))
                
                competitors = comp_result.fetchall()
                
                results = []
                needs_refresh = []  # Track what needs updating
                
                for product in products:
                    product_id, prod_name, prod_brand, prod_meta = product
                    
                    for competitor in competitors:
                        comp_id, comp_name, comp_urls = competitor
                        
                        # Check if we have ANY data (not just recent)
                        if not force_refresh:
                            cache_result = session.execute(text("""
                                SELECT price, member_price, availability_status, scraped_at, url,
                                       EXTRACT(EPOCH FROM (NOW() - scraped_at))/3600 as hours_old
                                FROM pricing.price_history
                                WHERE product_id = :product_id 
                                  AND competitor_id = :competitor_id
                                ORDER BY scraped_at DESC
                                LIMIT 1
                            """), {
                                "product_id": product_id,
                                "competitor_id": comp_id
                            })
                            
                            cached = cache_result.fetchone()
                            if cached:
                                price, member_price, status, scraped_at, url, hours_old = cached
                                
                                # Determine freshness status
                                if hours_old < 12:
                                    freshness = "fresh"
                                elif hours_old < 24:
                                    freshness = "stale"
                                else:
                                    freshness = "old"
                                
                                # Only use cached data if fresh enough
                                if freshness in ["fresh", "stale"]:
                                    results.append({
                                        "product": f"{prod_brand} {prod_name}",
                                        "competitor": comp_name,
                                        "price": float(price) if price else None,
                                        "member_price": float(member_price) if member_price else None,
                                        "status": status,
                                        "scraped_at": scraped_at,
                                        "url": url,
                                        "from_cache": True,
                                        "freshness": freshness,
                                        "hours_old": hours_old
                                    })
                                    
                                    # Track stale data for potential refresh
                                    if freshness == "stale":
                                        needs_refresh.append((product_id, prod_name, prod_brand, comp_id, comp_name))
                                    
                                    continue
                                else:
                                    # Old data - will refresh automatically
                                    needs_refresh.append((product_id, prod_name, prod_brand, comp_id, comp_name))
                        
                        # Need to scrape fresh data
                        search_query = f"{prod_brand} {prod_name}"
                        # prod_meta is already a dict from the database JSONB column
                        scraped_data = await self._scrape_competitor_price(
                            comp_name, comp_urls[0], search_query, prod_meta if prod_meta else {}
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
                                "from_cache": False,
                                "freshness": "fresh",
                                "hours_old": 0
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
                                "scraped_at": datetime.now(timezone.utc),
                                "url": comp_urls[0],
                                "from_cache": False,
                                "freshness": "fresh",
                                "hours_old": 0
                            })
                
                session.commit()
                
                # Format results with freshness info
                output = self._format_price_results_with_freshness(results)
                
                # Add refresh suggestions if needed
                if needs_refresh and not force_refresh:
                    output += "\n**Freshness Notice:**\n"
                    stale_count = sum(1 for r in results if r.get('freshness') == 'stale')
                    if stale_count > 0:
                        output += f"- {stale_count} price points are 12-24 hours old (marked with )\n"
                        output += "- Use `force_refresh=True` to update all prices\n"
                
                return output
                
        except Exception as e:
            return f"Error checking prices: {str(e)}"
    
    async def bulk_price_check(self, products: List[Dict[str, str]], 
                              competitors: Optional[List[str]] = None) -> str:
        """
        Check prices for multiple products across competitors.
        
        Args:
            products: List of dicts with 'name' and 'brand' keys, e.g. [{"name": "Strawberry Gummies", "brand": "Wyld"}]
            competitors: Optional list of competitor names to check
            
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
                    return f"Product not found: {product_name}"
                
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
            return f"Error getting price history: {str(e)}"
    
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
                        arrow = "" if pct > 0 else ""
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
            return f"Error analyzing trends: {str(e)}"
    
    async def discover_product_variants(self, base_product: str, brand: str) -> str:
        """
        Discover all variants of a product across competitors.
        
        Args:
            base_product: Base product name (e.g., "Strawberry Gummies")
            brand: Brand name (e.g., "Wyld")
            
        Returns:
            Report of all discovered variants
        """
        try:
            with self.Session() as session:
                # Get all tracked variants
                query = text("""
                    SELECT DISTINCT p.name, p.id,
                           COUNT(DISTINCT ph.competitor_id) as competitor_count,
                           MAX(ph.scraped_at) as last_seen
                    FROM pricing.products p
                    LEFT JOIN pricing.price_history ph ON p.id = ph.product_id
                    WHERE LOWER(p.brand) = :brand 
                    AND LOWER(p.name) LIKE :pattern
                    GROUP BY p.name, p.id
                    ORDER BY p.name
                """)
                
                result = session.execute(query, {
                    "brand": brand.lower(),
                    "pattern": f"%{base_product.lower()}%"
                })
                
                variants = result.fetchall()
                
                if not variants:
                    return f"No {brand} {base_product} variants found in the system."
                
                output = f"## {brand} {base_product} Variants Discovery\n\n"
                output += f"Found {len(variants)} variants:\n\n"
                
                for name, _, comp_count, last_seen in variants:
                    output += f"**{name}**\n"
                    output += f"  - Tracked at {comp_count} competitors\n"
                    if last_seen:
                        hours_ago = (datetime.now(timezone.utc) - last_seen).total_seconds() / 3600
                        output += f"  - Last price data: {int(hours_ago)} hours ago\n"
                    output += "\n"
                
                output += f"\n**Tip:** Use 'check prices for [specific variant]' to see current pricing."
                
                return output
                
        except Exception as e:
            return f"Error discovering variants: {str(e)}"
    
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
            # For variant searches, also try base product name
            search_queries = [search_query]
            
            # If the query contains variant indicators, also search for base product
            if any(indicator in search_query.lower() for indicator in ['cbd', 'thc', 'mg', ':', 'hybrid']):
                # Extract base product name
                words = search_query.split()
                base_words = []
                brand_found = False
                
                for word in words:
                    if not brand_found and word.lower() in ['wyld', 'kiva', 'camino', 'plus', 'wana']:
                        base_words.append(word)
                        brand_found = True
                    elif not any(ind in word.lower() for ind in ['mg', 'cbd', 'thc', ':', '100', '50', '20', '10', '5', 'hybrid']):
                        base_words.append(word)
                
                if len(base_words) > 1:  # Need at least brand + product
                    base_query = ' '.join(base_words)
                    search_queries.append(base_query)
            
            # Try searching with each query variant
            all_urls = []
            for query in search_queries:
                # Extract brand and product name from query
                parts = query.split()
                if len(parts) > 1:
                    brand = parts[0]
                    product = ' '.join(parts[1:])
                else:
                    brand = ""
                    product = query
                
                query_urls = await self.search_product_urls(product, brand, competitor_url)
                if query_urls:
                    all_urls.extend(query_urls)
            
            # Remove duplicates while preserving order
            seen = set()
            urls = []
            for url in all_urls:
                if url not in seen:
                    seen.add(url)
                    urls.append(url)
            
            if not urls:
                print(f"No product URLs found for {search_query} (or variants) at {competitor_name}")
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
        
        output = "##  Competitive Pricing Report\n\n"
        
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
                    "in_stock": "",
                    "out_of_stock": "",
                    "not_carried": ""
                }.get(item['status'], "")
                
                status = f"{status_emoji} {item['status'].replace('_', ' ').title()}"
                
                # Time since update
                if item.get('scraped_at'):
                    if isinstance(item['scraped_at'], str):
                        scraped_dt = datetime.fromisoformat(item['scraped_at'].replace('Z', '+00:00'))
                    else:
                        scraped_dt = item['scraped_at']
                    
                    hours_ago = (datetime.now(timezone.utc) - scraped_dt).total_seconds() / 3600
                    if hours_ago < 1:
                        time_str = "< 1 hour ago"
                    elif hours_ago < 24:
                        time_str = f"{int(hours_ago)} hours ago"
                    else:
                        time_str = f"{int(hours_ago/24)} days ago"
                    
                    if item.get('from_cache'):
                        time_str += " "
                else:
                    time_str = "Unknown"
                
                # Source
                source = "Fresh" if not item.get('from_cache') else " Cached"
                
                output += f"| {item['competitor']} | {price} | {member} | {status} | {time_str} | {source} |\n"
            
            # Add insights
            available_prices = [d['price'] for d in data if d.get('price') and d['status'] == 'in_stock']
            if available_prices:
                output += f"\n**Insights:**\n"
                output += f"-  Best price: ${min(available_prices):.2f} at {data[0]['competitor']}\n"
                output += f"- Average price: ${sum(available_prices)/len(available_prices):.2f}\n"
                output += f"-  Price range: ${min(available_prices):.2f} - ${max(available_prices):.2f}\n"
                
                # Out of stock warnings
                out_of_stock = [d['competitor'] for d in data if d['status'] == 'out_of_stock']
                if out_of_stock:
                    output += f"- Out of stock at: {', '.join(out_of_stock)}\n"
                
                not_carried = [d['competitor'] for d in data if d['status'] == 'not_carried']
                if not_carried:
                    output += f"- Not carried by: {', '.join(not_carried)}\n"
            
            output += "\n"
        
        return output
    
    def _is_product_variant(self, search_query: str, found_product: str) -> bool:
        """Check if found product is a variant of the searched product"""
        search_lower = search_query.lower()
        found_lower = found_product.lower()
        
        # Direct match
        if search_lower in found_lower or found_lower in search_lower:
            return True
        
        # Extract base words (excluding dosage, ratios, etc)
        def extract_base_words(text):
            words = []
            for word in text.split():
                if not any(ind in word.lower() for ind in ['mg', 'cbd', 'thc', ':', '100', '50', '20', '10', '5', 'hybrid', 'enhanced']):
                    words.append(word.lower())
            return words
        
        search_base = extract_base_words(search_query)
        found_base = extract_base_words(found_product)
        
        # Check if all search base words are in found product
        if all(word in ' '.join(found_base) for word in search_base):
            return True
        
        # Check specific patterns for cannabis products
        # e.g., "Wyld Strawberry Gummies" matches "Wyld Strawberry 20:1 CBD Hybrid Gummies"
        if len(search_base) >= 2 and len(found_base) >= 2:
            # Brand and key product word match
            if search_base[0] == found_base[0]:  # Same brand
                # Check if key product words match
                common_words = set(search_base) & set(found_base)
                if len(common_words) >= 2:  # At least brand + one product word
                    return True
        
        return False
    
    def _format_price_results_with_freshness(self, results: List[Dict]) -> str:
        """Format price results with freshness indicators"""
        if not results:
            return "No price data available."
        
        # Group by product
        by_product = {}
        for result in results:
            prod = result["product"]
            if prod not in by_product:
                by_product[prod] = []
            by_product[prod].append(result)
        
        output = "##  Competitive Pricing Report\n\n"
        
        for product, data in by_product.items():
            output += f"### {product}\n\n"
            output += "| Competitor | Price | Member Price | Status | Freshness | Last Updated |\n"
            output += "|------------|-------|--------------|--------|-----------|---------------|\n"
            
            # Sort by price
            data.sort(key=lambda x: x.get("price") or float('inf'))
            
            for item in data:
                price = f"${item['price']:.2f}" if item.get('price') else "—"
                member = f"${item['member_price']:.2f}" if item.get('member_price') else "—"
                
                # Status emoji
                status_emoji = {
                    "in_stock": "",
                    "out_of_stock": "",
                    "not_carried": ""
                }.get(item['status'], "")
                
                status = f"{status_emoji} {item['status'].replace('_', ' ').title()}"
                
                # Freshness indicator
                freshness = item.get('freshness', 'unknown')
                freshness_icon = {
                    "fresh": "",
                    "stale": "", 
                    "old": "",
                    "unknown": ""
                }.get(freshness, "")
                
                # Time since update
                hours_old = item.get('hours_old', 0)
                if hours_old < 1:
                    time_str = "< 1 hour ago"
                elif hours_old < 24:
                    time_str = f"{int(hours_old)} hours ago"
                else:
                    time_str = f"{int(hours_old/24)} days ago"
                
                output += f"| {item['competitor']} | {price} | {member} | {status} | {freshness_icon} {freshness.title()} | {time_str} |\n"
            
            # Add insights
            available_prices = [d['price'] for d in data if d.get('price') and d['status'] == 'in_stock']
            if available_prices:
                output += f"\n**Insights:**\n"
                output += f"-  Best price: ${min(available_prices):.2f} at {[d['competitor'] for d in data if d['price'] == min(available_prices)][0]}\n"
                output += f"- Average price: ${sum(available_prices)/len(available_prices):.2f}\n"
                output += f"-  Price range: ${min(available_prices):.2f} - ${max(available_prices):.2f}\n"
                
                # Freshness summary
                fresh_count = sum(1 for d in data if d.get('freshness') == 'fresh')
                stale_count = sum(1 for d in data if d.get('freshness') == 'stale')
                old_count = sum(1 for d in data if d.get('freshness') == 'old')
                
                if fresh_count > 0:
                    output += f"- Fresh data: {fresh_count} competitors\n"
                if stale_count > 0:
                    output += f"- Stale data (12-24h): {stale_count} competitors\n"
                if old_count > 0:
                    output += f"- Old data (>24h): {old_count} competitors\n"
                
                # Out of stock warnings
                out_of_stock = [d['competitor'] for d in data if d['status'] == 'out_of_stock']
                if out_of_stock:
                    output += f"- Out of stock at: {', '.join(out_of_stock)}\n"
                
                not_carried = [d['competitor'] for d in data if d['status'] == 'not_carried']
                if not_carried:
                    output += f"- Not carried by: {', '.join(not_carried)}\n"
            
            output += "\n"
        
        return output
    
    async def create_batch_job(self, products: List[Dict[str, str]], 
                              competitor_names: Optional[List[str]] = None,
                              job_name: Optional[str] = None,
                              user_id: Optional[str] = None) -> str:
        """
        Create a batch job for checking multiple products across competitors.
        
        Args:
            products: List of dicts with 'name' and 'brand' keys
            competitor_names: Optional list of competitors (uses all if not specified)
            job_name: Optional name for the job
            user_id: User creating the job
            
        Returns:
            Job creation confirmation with ID and estimates
        """
        try:
            with self.Session() as session:
                # Validate products
                if not products:
                    return "No products specified for batch job"
                
                # Get all product IDs
                product_ids = []
                for prod in products:
                    if 'name' not in prod or 'brand' not in prod:
                        return "Each product must have 'name' and 'brand' fields"
                    
                    result = session.execute(text("""
                        SELECT id FROM pricing.products 
                        WHERE name = :name AND brand = :brand
                    """), {"name": prod['name'], "brand": prod['brand']})
                    
                    product_row = result.fetchone()
                    if product_row:
                        product_ids.append(product_row[0])
                    else:
                        # Track product if it doesn't exist
                        # Check if enabled column exists
                        try:
                            result = session.execute(text("""
                                INSERT INTO pricing.products (name, brand, enabled)
                                VALUES (:name, :brand, true)
                                RETURNING id
                            """), {"name": prod['name'], "brand": prod['brand']})
                        except Exception as e:
                            # Rollback the failed transaction
                            session.rollback()
                            # Fallback for databases without enabled column
                            result = session.execute(text("""
                                INSERT INTO pricing.products (name, brand)
                                VALUES (:name, :brand)
                                RETURNING id
                            """), {"name": prod['name'], "brand": prod['brand']})
                        product_ids.append(result.fetchone()[0])
                
                # Get competitor IDs
                if competitor_names:
                    comp_result = session.execute(text("""
                        SELECT id FROM pricing.competitors 
                        WHERE enabled = true AND name = ANY(:names)
                    """), {"names": competitor_names})
                else:
                    comp_result = session.execute(text("""
                        SELECT id FROM pricing.competitors WHERE enabled = true
                    """))
                
                competitor_ids = [row[0] for row in comp_result]
                
                if not competitor_ids:
                    return "No active competitors found"
                
                # Calculate total checks
                total_checks = len(product_ids) * len(competitor_ids)
                
                # Prompt for confirmation if large job
                if total_checks > 50:
                    estimated_time = (total_checks * 2) / 60  # ~2 seconds per check
                    confirmation = f"This will create {total_checks} price checks (~{estimated_time:.1f} minutes). "
                    
                    # Check how many already have fresh data
                    fresh_result = session.execute(text("""
                        SELECT COUNT(*) FROM pricing.price_history ph
                        WHERE product_id = ANY(:products)
                        AND competitor_id = ANY(:competitors)
                        AND scraped_at > NOW() - INTERVAL '12 hours'
                    """), {"products": product_ids, "competitors": competitor_ids})
                    
                    fresh_count = fresh_result.fetchone()[0]
                    stale_count = total_checks - fresh_count
                    
                    if fresh_count > 0:
                        confirmation += f"\n\nCache Status:\n"
                        confirmation += f"- Fresh data: {fresh_count} price points\n"
                        confirmation += f"- Needs update: {stale_count} price points\n"
                        confirmation += f"\nConsider checking only stale prices to save time."
                    
                    return confirmation + "\n\nTo proceed, call create_batch_job again with confirm=True"
                
                # Create the batch job
                import uuid
                job_id = str(uuid.uuid4())
                
                session.execute(text("""
                    INSERT INTO pricing.batch_jobs 
                    (id, name, total_checks, created_by, metadata)
                    VALUES (:id, :name, :total, :user, :metadata)
                """), {
                    "id": job_id,
                    "name": job_name or f"Batch price check - {len(products)} products",
                    "total": total_checks,
                    "user": user_id or "system",
                    "metadata": json.dumps({
                        "products": products,
                        "competitors": competitor_names or "all"
                    })
                })
                
                # Create job items
                for prod_id in product_ids:
                    for comp_id in competitor_ids:
                        session.execute(text("""
                            INSERT INTO pricing.batch_job_items
                            (batch_job_id, product_id, competitor_id)
                            VALUES (:job_id, :prod_id, :comp_id)
                        """), {
                            "job_id": job_id,
                            "prod_id": prod_id,
                            "comp_id": comp_id
                        })
                
                session.commit()
                
                # Return confirmation
                output = f"**Batch Job Created**\n\n"
                output += f"- Job ID: `{job_id}`\n"
                output += f"- Total checks: {total_checks}\n"
                output += f"- Products: {len(product_ids)}\n"
                output += f"- Competitors: {len(competitor_ids)}\n"
                output += f"- Estimated time: ~{(total_checks * 2) / 60:.1f} minutes\n\n"
                output += f"Use `check_batch_status('{job_id}')` to monitor progress"
                
                return output
                
        except Exception as e:
            return f"Error creating batch job: {str(e)}"
    
    async def check_batch_status(self, job_id: str) -> str:
        """
        Check the status of a batch job.
        
        Args:
            job_id: UUID of the batch job
            
        Returns:
            Status report with progress
        """
        try:
            with self.Session() as session:
                # Get job details
                result = session.execute(text("""
                    SELECT name, status, total_checks, completed_checks,
                           created_at, started_at, completed_at, error_message
                    FROM pricing.batch_jobs
                    WHERE id = :job_id
                """), {"job_id": job_id})
                
                job = result.fetchone()
                if not job:
                    return f"Batch job not found: {job_id}"
                
                name, status, total, completed, created, started, finished, error = job
                
                # Calculate progress
                progress = (completed / total * 100) if total > 0 else 0
                
                # Status emoji
                status_emoji = {
                    "pending": "",
                    "running": "",
                    "completed": "",
                    "failed": "",
                    "cancelled": ""
                }.get(status, "")
                
                output = f"## {status_emoji} Batch Job Status\n\n"
                output += f"**{name}**\n\n"
                output += f"- Status: {status.upper()}\n"
                output += f"- Progress: {completed}/{total} ({progress:.1f}%)\n"
                
                # Progress bar
                bar_length = 20
                filled = int(bar_length * progress / 100)
                bar = "" * filled + "" * (bar_length - filled)
                output += f"- [{bar}]\n\n"
                
                # Timing info
                if started:
                    elapsed = (finished or datetime.now(timezone.utc)) - started
                    output += f"- Started: {started.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                    output += f"- Elapsed: {elapsed.total_seconds() / 60:.1f} minutes\n"
                    
                    if status == "running" and completed > 0:
                        rate = completed / elapsed.total_seconds()
                        remaining = (total - completed) / rate / 60
                        output += f"- ETA: ~{remaining:.1f} minutes\n"
                
                if finished:
                    output += f"- Completed: {finished.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                
                if error:
                    output += f"\nError: {error}\n"
                
                # Get breakdown by status
                if status in ["running", "completed"]:
                    breakdown = session.execute(text("""
                        SELECT status, COUNT(*) 
                        FROM pricing.batch_job_items
                        WHERE batch_job_id = :job_id
                        GROUP BY status
                    """), {"job_id": job_id})
                    
                    output += "\n**Breakdown:**\n"
                    for item_status, count in breakdown:
                        output += f"- {item_status.title()}: {count}\n"
                
                if status == "completed":
                    output += f"\nJob complete! Use `get_batch_results('{job_id}')` to retrieve results."
                
                return output
                
        except Exception as e:
            return f"Error checking batch status: {str(e)}"
    
    async def get_batch_results(self, job_id: str, format: str = "summary") -> str:
        """
        Get results from a completed batch job.
        
        Args:
            job_id: UUID of the batch job
            format: Output format - 'summary', 'detailed', or 'csv'
            
        Returns:
            Formatted results or download link
        """
        try:
            with self.Session() as session:
                # Check job is completed
                result = session.execute(text("""
                    SELECT status FROM pricing.batch_jobs WHERE id = :job_id
                """), {"job_id": job_id})
                
                job = result.fetchone()
                if not job:
                    return f"Batch job not found: {job_id}"
                
                if job[0] != "completed":
                    return f"Job is not completed yet. Status: {job[0]}"
                
                # Get all results
                results = session.execute(text("""
                    SELECT 
                        p.name as product_name,
                        p.brand,
                        c.name as competitor_name,
                        ph.price,
                        ph.member_price,
                        ph.availability_status,
                        ph.scraped_at,
                        ph.url
                    FROM pricing.batch_job_items bji
                    JOIN pricing.products p ON bji.product_id = p.id
                    JOIN pricing.competitors c ON bji.competitor_id = c.id
                    LEFT JOIN LATERAL (
                        SELECT * FROM pricing.price_history
                        WHERE product_id = bji.product_id
                        AND competitor_id = bji.competitor_id
                        ORDER BY scraped_at DESC
                        LIMIT 1
                    ) ph ON true
                    WHERE bji.batch_job_id = :job_id
                    ORDER BY p.brand, p.name, ph.price
                """), {"job_id": job_id})
                
                data = results.fetchall()
                
                if format == "csv":
                    # Generate CSV
                    import csv
                    import io
                    
                    output = io.StringIO()
                    writer = csv.writer(output)
                    writer.writerow(["Brand", "Product", "Competitor", "Price", "Member Price", 
                                   "Status", "Last Updated", "URL"])
                    
                    for row in data:
                        writer.writerow(row)
                    
                    csv_content = output.getvalue()
                    
                    # In a real implementation, save to S3/blob storage and return URL
                    return f" CSV generated with {len(data)} rows.\n\n[Download would be available in production]"
                
                elif format == "detailed":
                    # Detailed format - reuse existing formatting
                    results_list = []
                    for row in data:
                        results_list.append({
                            "product": f"{row[1]} {row[0]}",
                            "competitor": row[2],
                            "price": float(row[3]) if row[3] else None,
                            "member_price": float(row[4]) if row[4] else None,
                            "status": row[5] or "not_checked",
                            "scraped_at": row[6],
                            "url": row[7],
                            "from_cache": True,
                            "freshness": "fresh",
                            "hours_old": 0
                        })
                    
                    return self._format_price_results_with_freshness(results_list)
                
                else:  # summary format
                    # Group by product
                    by_product = {}
                    for row in data:
                        key = f"{row[1]} {row[0]}"
                        if key not in by_product:
                            by_product[key] = []
                        by_product[key].append(row)
                    
                    output = f"## Batch Job Results Summary\n\n"
                    output += f"Job ID: `{job_id}`\n"
                    output += f"Products analyzed: {len(by_product)}\n\n"
                    
                    for product, competitors in by_product.items():
                        prices = [c[3] for c in competitors if c[3] and c[5] == "in_stock"]
                        
                        if prices:
                            output += f"**{product}**\n"
                            output += f"- Price range: ${min(prices):.2f} - ${max(prices):.2f}\n"
                            output += f"- Best price: ${min(prices):.2f} at {[c[2] for c in competitors if c[3] == min(prices)][0]}\n"
                            output += f"- Availability: {len(prices)}/{len(competitors)} competitors\n\n"
                    
                    output += f"\nFor detailed results, use `get_batch_results('{job_id}', format='detailed')`"
                    output += f"\nFor CSV export, use `get_batch_results('{job_id}', format='csv')`"
                    
                    return output
                
        except Exception as e:
            return f"Error getting batch results: {str(e)}"
    
    async def list_batch_jobs(self, user_id: Optional[str] = None, limit: int = 10) -> str:
        """
        List recent batch jobs.
        
        Args:
            user_id: Filter by user (optional)
            limit: Number of jobs to show
            
        Returns:
            List of recent batch jobs
        """
        try:
            with self.Session() as session:
                query = text("""
                    SELECT id, name, status, total_checks, completed_checks,
                           created_at, created_by
                    FROM pricing.batch_jobs
                    WHERE (:user_id IS NULL OR created_by = :user_id)
                    ORDER BY created_at DESC
                    LIMIT :limit
                """)
                
                result = session.execute(query, {"user_id": user_id, "limit": limit})
                jobs = result.fetchall()
                
                if not jobs:
                    return "No batch jobs found"
                
                output = "## Recent Batch Jobs\n\n"
                
                for job in jobs:
                    job_id, name, status, total, completed, created, creator = job
                    
                    # Status emoji
                    status_emoji = {
                        "pending": "",
                        "running": "",
                        "completed": "",
                        "failed": "",
                        "cancelled": ""
                    }.get(status, "")
                    
                    progress = (completed / total * 100) if total > 0 else 0
                    
                    output += f"{status_emoji} **{name}**\n"
                    output += f"   - ID: `{job_id}`\n"
                    output += f"   - Status: {status} ({progress:.0f}%)\n"
                    output += f"   - Checks: {completed}/{total}\n"
                    output += f"   - Created: {created.strftime('%Y-%m-%d %H:%M UTC')}\n"
                    output += f"   - By: {creator}\n\n"
                
                return output
                
        except Exception as e:
            return f"Error listing batch jobs: {str(e)}"


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
               - Use `check_prices` for current pricing (smart cache-aware)
               - Use `analyze_price_freshness` to check data age before scraping
               - Use `bulk_price_check` for multiple products
               - Force refresh with force_refresh=True parameter
               - Track regular and member pricing tiers
               - Data freshness indicators:
                 * Fresh: < 12 hours old (used automatically)
                 * Stale: 12-24 hours old (used but flagged)
                 * Old: > 24 hours old (auto-refreshed)
            
            4. **Analysis & Insights**
               - Use `get_price_history` for trend data
               - Use `analyze_pricing_trends` for market insights
               - Identify pricing patterns and opportunities
            
            5. **Batch Processing** (for large operations)
               - Use `create_batch_job` for 50+ price checks
               - Monitor with `check_batch_status` 
               - Retrieve results with `get_batch_results`
               - List jobs with `list_batch_jobs`
               - Supports CSV export for analysis
            
            6. **Product Variants** (NEW!)
               - Use `discover_product_variants` to find all variants
               - Automatically shows alternatives when exact match not found
               - Handles CBD/THC ratios, dosages, and formulations
               - Example: "Strawberry Gummies" finds all strawberry variants
            
            ## Workflow for New Requests:
            
            1. **Single Product Check**:
               - First check if product is already tracked
               - If not, use `track_product` to add it
               - Then use `check_prices` to get current data
               - Smart caching: Returns mix of cached and fresh data
               - Use `force_refresh=True` to bypass all caching
               - If product not found, system shows available variants
            
            2. **Bulk Analysis** (< 50 checks):
               - Add all products and competitors first
               - Use `bulk_price_check` with products list: [{"name": "product_name", "brand": "brand_name"}, ...]
               - Optionally specify competitors list
               - Follow up with trend analysis
            
            3. **Large Scale Operations** (50+ checks):
               - Use `create_batch_job` for async processing
               - System will warn if >50 checks and show cache status
               - Monitor progress with `check_batch_status`
               - Retrieve results when complete
               - Export to CSV for external analysis
            
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