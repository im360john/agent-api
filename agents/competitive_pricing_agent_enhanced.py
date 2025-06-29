"""Enhanced Competitive Pricing Agent with knowledge base and detailed logging"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import json
import os
from decimal import Decimal

from agno.agent import Agent
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.models.openai import OpenAIChat
from agno.storage.agent.postgres import PostgresAgentStorage
from agno.tools.toolkit import Toolkit

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from db.session import db_url
from agents.competitive_pricing_agent import CompetitorPricingTools, PriceData
from agents.enhanced_scraping import EnhancedScraper, ScrapingResult

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedCompetitorPricingTools(CompetitorPricingTools):
    """Enhanced toolkit with knowledge base and detailed logging"""
    
    def __init__(self, db_url: str):
        super().__init__(db_url)
        
        # Initialize enhanced scraper
        self.enhanced_scraper = EnhancedScraper(
            db_url=db_url,
            firecrawl_key=self.firecrawl_key,
            browserbase_key=self.browserbase_key,
            exa_key=self.exa_key
        )
        
        # Register additional tools
        self.register(self.record_user_correction)
        self.register(self.view_scraping_confidence)
        self.register(self.analyze_scraping_performance)
    
    async def _scrape_competitor(
        self, 
        competitor_name: str,
        competitor_url: str,
        search_query: str,
        product_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[PriceData]:
        """
        Enhanced scraping with detailed logging and confidence scoring.
        
        This overrides the parent method to use enhanced scraping.
        """
        # Get competitor ID
        competitor_id = self._get_competitor_id(competitor_name)
        
        # Use enhanced scraper
        result: ScrapingResult = await self.enhanced_scraper.scrape_with_confidence(
            competitor_name=competitor_name,
            competitor_id=competitor_id,
            competitor_url=competitor_url,
            search_query=search_query,
            product_metadata=product_metadata
        )
        
        # Log detailed results
        logger.info(f"""
        Scraping Result for {competitor_name}:
        - Tool Used: {result.tool_used}
        - URL Scraped: {result.url_scraped}
        - Success: {result.success}
        - Confidence Score: {result.confidence_score:.2f}
        - Price Confidence: {result.price_confidence}
        - Stock Confidence: {result.stock_confidence}
        - Duration: {result.duration_ms}ms
        """)
        
        if result.success and result.price_data:
            # Add confidence scores to the price data
            result.price_data.raw_data = result.price_data.raw_data or {}
            result.price_data.raw_data['scraping_metadata'] = {
                'tool_used': result.tool_used,
                'url_scraped': result.url_scraped,
                'confidence_score': result.confidence_score,
                'price_confidence': result.price_confidence,
                'stock_confidence': result.stock_confidence,
                'duration_ms': result.duration_ms
            }
            
            return result.price_data
        
        return None
    
    def _get_competitor_id(self, competitor_name: str) -> int:
        """Get competitor ID from name"""
        with self.Session() as session:
            result = session.execute(
                text("SELECT id FROM pricing.competitors WHERE LOWER(name) = :name"),
                {"name": competitor_name.lower()}
            )
            row = result.fetchone()
            return row[0] if row else 0
    
    async def record_user_correction(
        self,
        product_name: str,
        competitor_name: str,
        correction_type: str,
        original_value: str,
        corrected_value: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """
        Record a user correction to improve future scraping accuracy.
        
        Args:
            product_name: Name of the product
            competitor_name: Name of the competitor
            correction_type: Type of correction ('price', 'stock_status', 'url', 'product_name')
            original_value: What the agent found
            corrected_value: What the user says is correct
            user_id: User making the correction
            session_id: Session ID for context
            
        Returns:
            Confirmation message
        """
        try:
            with self.Session() as session:
                # Get IDs
                product_result = session.execute(
                    text("SELECT id FROM pricing.products WHERE LOWER(name) LIKE :name"),
                    {"name": f"%{product_name.lower()}%"}
                )
                product = product_result.fetchone()
                
                competitor_result = session.execute(
                    text("SELECT id FROM pricing.competitors WHERE LOWER(name) = :name"),
                    {"name": competitor_name.lower()}
                )
                competitor = competitor_result.fetchone()
                
                if not product or not competitor:
                    return "❌ Product or competitor not found"
                
                # Calculate confidence impact based on correction type
                confidence_impact = {
                    'price': 0.3,
                    'stock_status': 0.2,
                    'url': 0.4,
                    'product_name': 0.1
                }.get(correction_type, 0.1)
                
                # Record the correction
                session.execute(text("""
                    INSERT INTO pricing.user_corrections (
                        product_id, competitor_id, correction_type,
                        original_value, corrected_value, user_id,
                        session_id, confidence_impact
                    ) VALUES (
                        :product_id, :competitor_id, :correction_type,
                        :original_value, :corrected_value, :user_id,
                        :session_id, :confidence_impact
                    )
                """), {
                    "product_id": product[0],
                    "competitor_id": competitor[0],
                    "correction_type": correction_type,
                    "original_value": original_value,
                    "corrected_value": corrected_value,
                    "user_id": user_id,
                    "session_id": session_id,
                    "confidence_impact": confidence_impact
                })
                
                # If it's a URL correction, add to knowledge base
                if correction_type == 'url':
                    session.execute(text("""
                        INSERT INTO pricing.knowledge_base (
                            kb_type, competitor_id, context, pattern, confidence
                        ) VALUES (
                            'url_pattern', :competitor_id, :context, :pattern, 0.8
                        )
                    """), {
                        "competitor_id": competitor[0],
                        "context": json.dumps({
                            "product": product_name,
                            "original_url": original_value
                        }),
                        "pattern": corrected_value
                    })
                
                session.commit()
                
                return f"""✅ Correction recorded successfully!
                
**Details:**
- Product: {product_name}
- Competitor: {competitor_name}
- Correction Type: {correction_type}
- Original: {original_value}
- Corrected: {corrected_value}

This will help improve future scraping accuracy. Thank you for the feedback!"""
                
        except Exception as e:
            logger.error(f"Error recording correction: {e}")
            return f"❌ Error recording correction: {str(e)}"
    
    async def view_scraping_confidence(
        self,
        product_name: Optional[str] = None,
        competitor_name: Optional[str] = None,
        days: int = 7
    ) -> str:
        """
        View scraping confidence metrics.
        
        Args:
            product_name: Optional product filter
            competitor_name: Optional competitor filter
            days: Number of days to analyze
            
        Returns:
            Confidence report
        """
        try:
            with self.Session() as session:
                query = """
                    SELECT 
                        sm.competitor_name,
                        sm.product_search,
                        sm.tool_used,
                        AVG(sm.confidence_score) as avg_confidence,
                        SUM(CASE WHEN sm.success THEN 1 ELSE 0 END) as success_count,
                        COUNT(*) as total_attempts,
                        AVG(sm.response_time_ms) as avg_response_time,
                        MODE() WITHIN GROUP (ORDER BY sm.price_confidence) as typical_price_confidence,
                        MODE() WITHIN GROUP (ORDER BY sm.stock_confidence) as typical_stock_confidence
                    FROM pricing.scraping_metrics sm
                    WHERE sm.scraped_at >= CURRENT_DATE - INTERVAL :days
                """
                
                params = {"days": f"{days} days"}
                
                if competitor_name:
                    query += " AND LOWER(sm.competitor_name) = :competitor"
                    params["competitor"] = competitor_name.lower()
                
                if product_name:
                    query += " AND LOWER(sm.product_search) LIKE :product"
                    params["product"] = f"%{product_name.lower()}%"
                
                query += """
                    GROUP BY sm.competitor_name, sm.product_search, sm.tool_used
                    ORDER BY avg_confidence DESC
                """
                
                result = session.execute(text(query), params)
                data = result.fetchall()
                
                if not data:
                    return f"No scraping data found for the last {days} days"
                
                output = f"## 📊 Scraping Confidence Report\n"
                output += f"*Last {days} days*\n\n"
                
                # Group by competitor
                by_competitor = {}
                for row in data:
                    comp = row[0]
                    if comp not in by_competitor:
                        by_competitor[comp] = []
                    by_competitor[comp].append(row)
                
                for comp, rows in by_competitor.items():
                    output += f"### {comp}\n\n"
                    output += "| Product | Tool | Avg Confidence | Success Rate | Avg Response | Price Conf | Stock Conf |\n"
                    output += "|---------|------|----------------|--------------|-------------|------------|------------|\n"
                    
                    for row in rows:
                        _, product, tool, avg_conf, success, total, avg_time, price_conf, stock_conf = row
                        success_rate = (success / total * 100) if total > 0 else 0
                        
                        # Confidence emoji
                        conf_emoji = "🟢" if avg_conf >= 0.7 else "🟡" if avg_conf >= 0.4 else "🔴"
                        
                        output += f"| {product[:30]}... | {tool} | {conf_emoji} {avg_conf:.2f} | "
                        output += f"{success_rate:.0f}% ({success}/{total}) | "
                        output += f"{avg_time:.0f}ms | {price_conf} | {stock_conf} |\n"
                    
                    output += "\n"
                
                # Add corrections summary
                corrections_result = session.execute(text("""
                    SELECT 
                        c.name as competitor,
                        uc.correction_type,
                        COUNT(*) as correction_count
                    FROM pricing.user_corrections uc
                    JOIN pricing.competitors c ON c.id = uc.competitor_id
                    WHERE uc.created_at >= CURRENT_DATE - INTERVAL :days
                    GROUP BY c.name, uc.correction_type
                    ORDER BY c.name, correction_count DESC
                """), {"days": f"{days} days"})
                
                corrections = corrections_result.fetchall()
                if corrections:
                    output += "### 📝 User Corrections\n\n"
                    output += "| Competitor | Type | Count |\n"
                    output += "|------------|------|-------|\n"
                    
                    for comp, corr_type, count in corrections:
                        output += f"| {comp} | {corr_type} | {count} |\n"
                
                return output
                
        except Exception as e:
            logger.error(f"Error viewing confidence: {e}")
            return f"❌ Error viewing confidence metrics: {str(e)}"
    
    async def analyze_scraping_performance(
        self,
        competitor_name: Optional[str] = None,
        min_confidence: float = 0.5
    ) -> str:
        """
        Analyze scraping performance and suggest improvements.
        
        Args:
            competitor_name: Optional competitor filter
            min_confidence: Minimum confidence threshold
            
        Returns:
            Performance analysis and recommendations
        """
        try:
            with self.Session() as session:
                # Get low confidence patterns
                query = """
                    SELECT 
                        competitor_name,
                        product_search,
                        url_attempted,
                        tool_used,
                        confidence_score,
                        price_confidence,
                        stock_confidence,
                        error_message
                    FROM pricing.scraping_metrics
                    WHERE confidence_score < :min_confidence
                    AND scraped_at >= CURRENT_DATE - INTERVAL '7 days'
                """
                
                params = {"min_confidence": min_confidence}
                
                if competitor_name:
                    query += " AND LOWER(competitor_name) = :competitor"
                    params["competitor"] = competitor_name.lower()
                
                query += " ORDER BY confidence_score ASC LIMIT 20"
                
                result = session.execute(text(query), params)
                low_confidence = result.fetchall()
                
                output = f"## 🔍 Scraping Performance Analysis\n\n"
                
                if low_confidence:
                    output += f"### ⚠️ Low Confidence Scrapes (< {min_confidence:.0%})\n\n"
                    output += "| Competitor | Product | URL | Tool | Confidence | Issues |\n"
                    output += "|------------|---------|-----|------|------------|--------|\n"
                    
                    for row in low_confidence:
                        comp, prod, url, tool, conf, price_conf, stock_conf, error = row
                        url_short = url.split('/')[-1][:20] + "..." if url else "N/A"
                        issues = []
                        if price_conf == 'low':
                            issues.append("price")
                        if stock_conf == 'low':
                            issues.append("stock")
                        if error:
                            issues.append("error")
                        
                        output += f"| {comp} | {prod[:20]}... | {url_short} | {tool} | "
                        output += f"{conf:.2f} | {', '.join(issues)} |\n"
                
                # Get success rates by tool
                tool_stats = session.execute(text("""
                    SELECT 
                        tool_used,
                        competitor_name,
                        SUM(CASE WHEN success THEN 1 ELSE 0 END)::float / COUNT(*) as success_rate,
                        AVG(confidence_score) as avg_confidence,
                        AVG(response_time_ms) as avg_time,
                        COUNT(*) as attempts
                    FROM pricing.scraping_metrics
                    WHERE scraped_at >= CURRENT_DATE - INTERVAL '7 days'
                    GROUP BY tool_used, competitor_name
                    ORDER BY tool_used, success_rate DESC
                """))
                
                output += "\n### 📊 Tool Performance by Competitor\n\n"
                
                current_tool = None
                for row in tool_stats:
                    tool, comp, success_rate, avg_conf, avg_time, attempts = row
                    
                    if tool != current_tool:
                        current_tool = tool
                        output += f"\n**{tool.upper()}**\n"
                        output += "| Competitor | Success Rate | Avg Confidence | Avg Time | Attempts |\n"
                        output += "|------------|--------------|----------------|----------|----------|\n"
                    
                    output += f"| {comp} | {success_rate:.0%} | {avg_conf:.2f} | "
                    output += f"{avg_time:.0f}ms | {attempts} |\n"
                
                # Recommendations
                output += "\n### 💡 Recommendations\n\n"
                
                # Check for competitors with consistently low performance
                poor_performers = session.execute(text("""
                    SELECT 
                        competitor_name,
                        AVG(confidence_score) as avg_conf,
                        SUM(CASE WHEN success THEN 1 ELSE 0 END)::float / COUNT(*) as success_rate
                    FROM pricing.scraping_metrics
                    WHERE scraped_at >= CURRENT_DATE - INTERVAL '7 days'
                    GROUP BY competitor_name
                    HAVING AVG(confidence_score) < 0.5 OR 
                           SUM(CASE WHEN success THEN 1 ELSE 0 END)::float / COUNT(*) < 0.5
                """)).fetchall()
                
                if poor_performers:
                    output += "**Competitors needing attention:**\n"
                    for comp, avg_conf, success_rate in poor_performers:
                        output += f"- **{comp}**: {avg_conf:.0%} confidence, {success_rate:.0%} success rate\n"
                        output += f"  - Consider updating URL patterns or trying different scraping tools\n"
                
                # Check for common errors
                common_errors = session.execute(text("""
                    SELECT 
                        competitor_name,
                        error_message,
                        COUNT(*) as error_count
                    FROM pricing.scraping_metrics
                    WHERE error_message IS NOT NULL
                    AND scraped_at >= CURRENT_DATE - INTERVAL '7 days'
                    GROUP BY competitor_name, error_message
                    ORDER BY error_count DESC
                    LIMIT 5
                """)).fetchall()
                
                if common_errors:
                    output += "\n**Common errors:**\n"
                    for comp, error, count in common_errors:
                        output += f"- {comp}: '{error}' ({count} times)\n"
                
                return output
                
        except Exception as e:
            logger.error(f"Error analyzing performance: {e}")
            return f"❌ Error analyzing scraping performance: {str(e)}"
    
    def _save_price_history_enhanced(
        self, 
        product_id: int,
        competitor_id: int,
        price_data: PriceData
    ):
        """Enhanced price history saving with confidence scores"""
        try:
            with self.Session() as session:
                # Extract scraping metadata
                scraping_meta = price_data.raw_data.get('scraping_metadata', {}) if price_data.raw_data else {}
                
                session.execute(text("""
                    INSERT INTO pricing.price_history (
                        product_id, competitor_id, price, member_price,
                        availability_status, price_tiers, metadata, scraped_at,
                        scraping_confidence, price_confidence, stock_confidence,
                        scraping_tool, scraping_url, scraping_duration_ms
                    ) VALUES (
                        :product_id, :competitor_id, :price, :member_price,
                        :availability_status, :price_tiers, :metadata, :scraped_at,
                        :scraping_confidence, :price_confidence, :stock_confidence,
                        :scraping_tool, :scraping_url, :scraping_duration_ms
                    )
                """), {
                    "product_id": product_id,
                    "competitor_id": competitor_id,
                    "price": price_data.price,
                    "member_price": price_data.member_price,
                    "availability_status": price_data.availability_status,
                    "price_tiers": json.dumps(price_data.price_tiers) if price_data.price_tiers else None,
                    "metadata": json.dumps(price_data.raw_data) if price_data.raw_data else None,
                    "scraped_at": price_data.scraped_at,
                    "scraping_confidence": scraping_meta.get('confidence_score'),
                    "price_confidence": scraping_meta.get('price_confidence'),
                    "stock_confidence": scraping_meta.get('stock_confidence'),
                    "scraping_tool": scraping_meta.get('tool_used'),
                    "scraping_url": scraping_meta.get('url_scraped'),
                    "scraping_duration_ms": scraping_meta.get('duration_ms')
                })
                session.commit()
        except Exception as e:
            logger.error(f"Error saving enhanced price history: {e}")


# Create the enhanced agent
def create_enhanced_agent() -> Agent:
    """Create the enhanced competitive pricing agent with knowledge base"""
    
    # Initialize enhanced tools
    tools = EnhancedCompetitorPricingTools(db_url=db_url)
    
    # Create agent with enhanced instructions
    enhanced_instructions = """
    You are an AI agent specialized in competitive price tracking for cannabis dispensaries with enhanced capabilities:
    
    1. **Enhanced Scraping**: You now provide detailed information about:
       - Which scraping tool was used (Firecrawl, Browserbase, or Exa)
       - The exact URL that was scraped
       - Confidence scores for price and stock accuracy
       - Response times for each scrape
    
    2. **Knowledge Base**: You learn from:
       - User corrections to improve accuracy
       - Successful scraping patterns
       - URL structures that work for each competitor
    
    3. **Confidence Reporting**: When showing prices, indicate confidence levels:
       - 🟢 High confidence (>70%): Highly reliable data
       - 🟡 Medium confidence (40-70%): Generally reliable but verify if critical
       - 🔴 Low confidence (<40%): Data may be unreliable, manual verification recommended
    
    4. **User Corrections**: When users correct you, use the `record_user_correction` tool to improve future accuracy.
    
    5. **Performance Analysis**: You can analyze scraping performance and suggest improvements.
    
    Always mention the scraping confidence when reporting prices and be transparent about data reliability.
    """
    
    agent = Agent(
        name="enhanced_competitive_pricing",
        agent_id="enhanced_competitive_pricing", 
        model=OpenAIChat(id="gpt-4o"),
        tools=[tools],
        storage=PostgresAgentStorage(table_name="enhanced_competitive_pricing_agents", db_url=db_url),
        memory=Memory(
            db=PostgresMemoryDb(
                table_name="enhanced_competitive_pricing_memory",
                db_url=db_url,
            )
        ),
        instructions=enhanced_instructions,
        markdown=True,
    )
    
    return agent