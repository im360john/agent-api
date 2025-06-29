#!/usr/bin/env python3
"""Test enhanced scraping functionality"""

import asyncio
import logging
from agents.enhanced_scraping import EnhancedScraper
from db.session import db_url
import os

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_scraping():
    """Test the enhanced scraping with confidence scores"""
    
    print("🔬 Testing Enhanced Scraping\n")
    
    # Initialize scraper
    scraper = EnhancedScraper(
        db_url=db_url,
        firecrawl_key=os.getenv("FIRECRAWL_API_KEY", "fc-05935e879f594170b09e54181f4dd5f0"),
        browserbase_key=os.getenv("BROWSERBASE_API_KEY"),
        exa_key=os.getenv("EXA_API_KEY")
    )
    
    # Test scraping for a product
    competitors = [
        {"name": "Harborside", "id": 1, "url": "https://shopharborside.com/san-jose/"},
        {"name": "Elemental Wellness", "id": 2, "url": "https://www.elementalwellnesscenter.com/"},
        {"name": "Theraleaf", "id": 3, "url": "https://www.theraleafsjc.com/"},
        {"name": "Airfield", "id": 4, "url": "https://airfieldsupplyco.com/"}
    ]
    
    search_query = "Wyld Raspberry Gummies"
    
    print(f"🔍 Testing scraping for: {search_query}\n")
    
    for comp in competitors:
        print(f"\n{'='*60}")
        print(f"Testing {comp['name']}")
        print('='*60)
        
        try:
            result = await scraper.scrape_with_confidence(
                competitor_name=comp['name'],
                competitor_id=comp['id'],
                competitor_url=comp['url'],
                search_query=search_query,
                product_metadata={"brand": "Wyld", "category": "edibles"}
            )
            
            print(f"\n📊 Results:")
            print(f"Success: {result.success}")
            print(f"Tool Used: {result.tool_used}")
            print(f"URL Scraped: {result.url_scraped}")
            print(f"Duration: {result.duration_ms}ms")
            print(f"Overall Confidence: {result.confidence_score:.2%}")
            print(f"Price Confidence: {result.price_confidence}")
            print(f"Stock Confidence: {result.stock_confidence}")
            
            if result.success and result.price_data:
                print(f"\n💰 Price Data:")
                print(f"Product: {result.price_data.product_name}")
                print(f"Price: ${result.price_data.price:.2f}")
                if result.price_data.member_price:
                    print(f"Member Price: ${result.price_data.member_price:.2f}")
                print(f"Availability: {result.price_data.availability_status}")
            elif result.error_message:
                print(f"\n❌ Error: {result.error_message}")
                
        except Exception as e:
            print(f"\n❌ Exception: {e}")
            import traceback
            traceback.print_exc()
    
    # Check what was stored in the database
    print(f"\n\n{'='*60}")
    print("📊 Checking Database Metrics")
    print('='*60)
    
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    
    engine = create_engine(db_url.replace('+asyncpg', '').replace('+aiopg', ''))
    Session = sessionmaker(bind=engine)
    
    with Session() as session:
        # Get recent scraping metrics
        result = session.execute(text("""
            SELECT 
                competitor_name,
                tool_used,
                success,
                confidence_score,
                price_confidence,
                stock_confidence,
                response_time_ms,
                url_attempted
            FROM pricing.scraping_metrics
            WHERE product_search LIKE :search
            ORDER BY scraped_at DESC
            LIMIT 10
        """), {"search": f"%{search_query}%"})
        
        metrics = result.fetchall()
        
        if metrics:
            print("\nRecent Scraping Metrics:")
            print("| Competitor | Tool | Success | Confidence | Price Conf | Stock Conf | Time | URL |")
            print("|------------|------|---------|------------|------------|------------|------|-----|")
            
            for row in metrics:
                comp, tool, success, conf, p_conf, s_conf, time_ms, url = row
                url_short = url.split('/')[-1][:20] + "..." if url else "N/A"
                print(f"| {comp:<10} | {tool:<4} | {'✓' if success else '✗':<7} | "
                      f"{conf:.2f}       | {p_conf:<10} | {s_conf:<10} | "
                      f"{time_ms:<4} | {url_short} |")
        else:
            print("\nNo metrics found in database yet")

if __name__ == "__main__":
    asyncio.run(test_scraping())