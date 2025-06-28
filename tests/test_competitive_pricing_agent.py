"""
Comprehensive test suite for Competitive Pricing Agent
Tests database operations, web scraping, caching, and analytics
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from datetime import datetime, timedelta
from decimal import Decimal
import json
import aiohttp

from agents.competitive_pricing_agent import CompetitorPricingTools, PriceData, get_competitive_pricing_agent


class TestPriceData:
    """Test the PriceData dataclass"""
    
    def test_price_data_defaults(self):
        """Test default values are set correctly"""
        price_data = PriceData(
            product_name="Test Product",
            price=10.99
        )
        
        assert price_data.product_name == "Test Product"
        assert price_data.price == 10.99
        assert price_data.member_price is None
        assert price_data.availability_status == "in_stock"
        assert price_data.url == ""
        assert price_data.price_tiers == []
        assert isinstance(price_data.scraped_at, datetime)
    
    def test_price_data_custom_values(self):
        """Test custom values override defaults"""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        price_data = PriceData(
            product_name="Test Product",
            price=10.99,
            member_price=9.99,
            availability_status="out_of_stock",
            scraped_at=custom_time,
            price_tiers=[{"tier": "VIP", "price": 8.99}]
        )
        
        assert price_data.member_price == 9.99
        assert price_data.availability_status == "out_of_stock"
        assert price_data.scraped_at == custom_time
        assert len(price_data.price_tiers) == 1


class TestCompetitorPricingTools:
    """Test the CompetitorPricingTools class"""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session"""
        session = MagicMock()
        session.__enter__ = MagicMock(return_value=session)
        session.__exit__ = MagicMock(return_value=None)
        return session
    
    @pytest.fixture
    def pricing_tools(self, mock_session):
        """Create CompetitorPricingTools instance with mocked dependencies"""
        with patch('agents.competitive_pricing_agent.create_engine') as mock_engine:
            with patch('agents.competitive_pricing_agent.sessionmaker') as mock_sessionmaker:
                mock_sessionmaker.return_value = lambda: mock_session
                tools = CompetitorPricingTools('postgresql://test')
                tools.Session = mock_sessionmaker.return_value
                return tools
    
    # Database Operations Tests
    
    @pytest.mark.asyncio
    async def test_track_product_success(self, pricing_tools, mock_session):
        """Test successfully adding a new product"""
        # Mock database responses
        mock_session.execute.side_effect = [
            MagicMock(fetchone=lambda: None),  # Product doesn't exist
            MagicMock(fetchone=lambda: [123])   # Insert returns ID
        ]
        
        result = await pricing_tools.track_product(
            name="Strawberry Gummies",
            brand="Wyld",
            category="edibles",
            search_terms=["wyld strawberry", "strawberry gummies"],
            metadata={"thc_content": "100mg", "package_size": "10-pack"}
        )
        
        assert "✅ Added product to tracking" in result
        assert "Wyld Strawberry Gummies" in result
        assert "(ID: 123)" in result
        assert mock_session.commit.called
    
    @pytest.mark.asyncio
    async def test_track_product_duplicate(self, pricing_tools, mock_session):
        """Test handling duplicate product"""
        # Mock product already exists
        mock_session.execute.return_value.fetchone.return_value = [456]
        
        result = await pricing_tools.track_product(
            name="Strawberry Gummies",
            brand="Wyld"
        )
        
        assert "Product already tracked" in result
        assert "(ID: 456)" in result
        assert not mock_session.commit.called
    
    @pytest.mark.asyncio
    async def test_track_product_db_error(self, pricing_tools, mock_session):
        """Test database error handling"""
        mock_session.execute.side_effect = Exception("Database connection failed")
        
        result = await pricing_tools.track_product(
            name="Test Product",
            brand="Test Brand"
        )
        
        assert "❌ Error adding product" in result
        assert "Database connection failed" in result
    
    @pytest.mark.asyncio
    async def test_add_competitor_new(self, pricing_tools, mock_session):
        """Test adding a new competitor"""
        mock_session.execute.return_value.fetchone.return_value = [789]
        
        result = await pricing_tools.add_competitor(
            name="Harborside",
            urls=["https://shopharborside.com/"],
            metadata={"age_verification": True}
        )
        
        assert "✅ Added competitor" in result
        assert "Harborside" in result
        assert "1 URL(s)" in result
        assert "(ID: 789)" in result
        assert mock_session.commit.called
    
    @pytest.mark.asyncio
    async def test_add_competitor_update(self, pricing_tools, mock_session):
        """Test updating existing competitor with ON CONFLICT"""
        mock_session.execute.return_value.fetchone.return_value = [100]
        
        result = await pricing_tools.add_competitor(
            name="Existing Shop",
            urls=["https://shop1.com/", "https://shop2.com/"]
        )
        
        # Verify ON CONFLICT clause in query
        call_args = mock_session.execute.call_args[0][0]
        assert "ON CONFLICT" in str(call_args)
        assert "DO UPDATE" in str(call_args)
    
    # Price Checking Tests
    
    @pytest.mark.asyncio
    async def test_check_prices_cache_hit(self, pricing_tools, mock_session):
        """Test returning cached price data"""
        # Mock product exists
        product_data = [1, "Strawberry Gummies", "Wyld", '{"thc_content": "100mg"}']
        mock_session.execute.side_effect = [
            MagicMock(fetchall=lambda: [product_data]),  # Product query
            MagicMock(fetchall=lambda: [[1, "Harborside", ["https://shop.com"]]]),  # Competitor query
            MagicMock(fetchone=lambda: [  # Cache query
                Decimal("14.00"),  # price
                None,  # member_price
                "in_stock",  # availability_status
                datetime.utcnow() - timedelta(hours=1),  # scraped_at (1 hour ago)
                "https://shop.com/product"  # url
            ])
        ]
        
        result = await pricing_tools.check_prices("Strawberry Gummies", "Wyld")
        
        assert "Wyld Strawberry Gummies" in result
        assert "$14.00" in result
        assert "in_stock" in result.lower()
        assert "Cached" in result or "💾" in result
    
    @pytest.mark.asyncio
    async def test_check_prices_force_refresh(self, pricing_tools, mock_session):
        """Test force refresh bypasses cache"""
        # Mock product and competitor exist
        product_data = [1, "Strawberry Gummies", "Wyld", '{}']
        competitor_data = [1, "Harborside", ["https://shop.com"]]
        
        mock_session.execute.side_effect = [
            MagicMock(fetchall=lambda: [product_data]),
            MagicMock(fetchall=lambda: [competitor_data])
        ]
        
        # Mock scraping
        with patch.object(pricing_tools, '_scrape_competitor_price') as mock_scrape:
            mock_scrape.return_value = PriceData(
                product_name="Wyld Strawberry Gummies",
                price=15.00,
                availability_status="in_stock",
                url="https://shop.com/wyld-strawberry"
            )
            
            result = await pricing_tools.check_prices(
                "Strawberry Gummies", 
                "Wyld",
                force_refresh=True
            )
            
            # Should call scraping method
            assert mock_scrape.called
            assert "Fresh" in result or "🔄" in result
    
    @pytest.mark.asyncio
    async def test_check_prices_product_not_found(self, pricing_tools, mock_session):
        """Test handling product not found"""
        mock_session.execute.return_value.fetchall.return_value = []
        
        result = await pricing_tools.check_prices("Nonexistent Product")
        
        assert "❌ Product not found" in result
        assert "Nonexistent Product" in result
    
    # Web Scraping Tests
    
    @pytest.mark.asyncio
    async def test_search_product_urls_success(self, pricing_tools):
        """Test successful URL search"""
        mock_response = {
            "organic": [
                {"link": "https://shop.com/products/wyld-strawberry-gummies"},
                {"link": "https://shop.com/category/edibles"},  # Should be filtered
                {"link": "https://shop.com/products/wyld-huckleberry"}
            ]
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_resp
            
            urls = await pricing_tools.search_product_urls(
                "Strawberry Gummies",
                "Wyld",
                "https://shop.com"
            )
            
            assert len(urls) == 1
            assert "wyld-strawberry-gummies" in urls[0]
    
    @pytest.mark.asyncio
    async def test_scrape_competitor_price_success(self, pricing_tools):
        """Test successful price scraping with Firecrawl"""
        # Mock search URLs
        with patch.object(pricing_tools, 'search_product_urls') as mock_search:
            mock_search.return_value = ["https://shop.com/wyld-strawberry"]
            
            # Mock Firecrawl response
            firecrawl_response = {
                "success": True,
                "data": {
                    "extract": {
                        "product_name": "Wyld Strawberry Gummies 100mg",
                        "regular_price": 14.00,
                        "member_price": 12.60,
                        "in_stock": True,
                        "thc_content": "100mg",
                        "package_size": "10-pack"
                    }
                }
            }
            
            with patch('aiohttp.ClientSession') as mock_session:
                mock_resp = AsyncMock()
                mock_resp.status = 200
                mock_resp.json = AsyncMock(return_value=firecrawl_response)
                
                mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_resp
                
                result = await pricing_tools._scrape_competitor_price(
                    "Harborside",
                    "https://shop.com",
                    "Wyld Strawberry Gummies",
                    {"thc_content": "100mg"}
                )
                
                assert result is not None
                assert result.price == 14.00
                assert result.member_price == 12.60
                assert result.availability_status == "in_stock"
                assert result.thc_content == "100mg"
    
    @pytest.mark.asyncio
    async def test_scrape_competitor_price_not_carried(self, pricing_tools):
        """Test handling product not found at competitor"""
        with patch.object(pricing_tools, 'search_product_urls') as mock_search:
            mock_search.return_value = []  # No URLs found
            
            result = await pricing_tools._scrape_competitor_price(
                "Theraleaf",
                "https://theraleaf.com",
                "Wyld Strawberry Gummies",
                {}
            )
            
            assert result is None
    
    # URL Validation Tests
    
    def test_is_relevant_product_url_valid(self, pricing_tools):
        """Test valid product URL detection"""
        assert pricing_tools._is_relevant_product_url(
            "https://shop.com/products/wyld-strawberry-gummies",
            "Wyld",
            "Strawberry Gummies"
        ) is True
    
    def test_is_relevant_product_url_category_page(self, pricing_tools):
        """Test rejection of category pages"""
        assert pricing_tools._is_relevant_product_url(
            "https://shop.com/category/edibles",
            "Wyld",
            "Strawberry Gummies"
        ) is False
    
    def test_is_relevant_product_url_missing_brand(self, pricing_tools):
        """Test rejection of URLs without brand"""
        assert pricing_tools._is_relevant_product_url(
            "https://shop.com/products/strawberry-gummies",
            "Wyld",
            "Strawberry Gummies"
        ) is False
    
    # Bulk Operations Tests
    
    @pytest.mark.asyncio
    async def test_bulk_price_check_multiple_products(self, pricing_tools):
        """Test checking prices for multiple products"""
        products = [
            {"name": "Strawberry Gummies", "brand": "Wyld"},
            {"name": "Huckleberry Gummies", "brand": "Wyld"},
            {"name": "Watermelon Gummies", "brand": "Camino"}
        ]
        
        with patch.object(pricing_tools, 'check_prices') as mock_check:
            mock_check.return_value = "Price data"
            
            result = await pricing_tools.bulk_price_check(products)
            
            assert mock_check.call_count == 3
            assert "Price data" in result
    
    # Analytics Tests
    
    @pytest.mark.asyncio
    async def test_get_price_history_with_data(self, pricing_tools, mock_session):
        """Test retrieving price history"""
        # Mock product exists
        mock_session.execute.side_effect = [
            MagicMock(fetchone=lambda: [1, "Strawberry Gummies", "Wyld"]),
            MagicMock(fetchall=lambda: [
                ["Harborside", datetime(2024, 1, 1), 14.00, 13.00, 15.00, 5, 4],
                ["Harborside", datetime(2024, 1, 2), 14.50, 14.00, 15.00, 3, 3]
            ])
        ]
        
        result = await pricing_tools.get_price_history("Strawberry Gummies", "Wyld", days=7)
        
        assert "Price History" in result
        assert "Wyld Strawberry Gummies" in result
        assert "Harborside" in result
        assert "$14.00" in result
    
    @pytest.mark.asyncio
    async def test_analyze_pricing_trends_significant_changes(self, pricing_tools, mock_session):
        """Test detection of significant price changes"""
        # Mock trend data with >5% change
        trend_data = [
            "Wyld", "Strawberry Gummies", "edibles", "Harborside",
            15.00, 14.00, "in_stock", "in_stock",
            datetime.utcnow(), datetime.utcnow() - timedelta(days=1),
            7.14  # 7.14% increase
        ]
        
        mock_session.execute.return_value.fetchall.return_value = [trend_data]
        
        result = await pricing_tools.analyze_pricing_trends(days=7)
        
        assert "Significant Price Changes" in result
        assert "📈" in result or "📉" in result
        assert "7.1%" in result
    
    # Format Tests
    
    def test_format_price_results_insights(self, pricing_tools):
        """Test price result formatting with insights"""
        results = [
            {
                "product": "Wyld Strawberry Gummies",
                "competitor": "Elemental",
                "price": 12.60,
                "status": "in_stock",
                "scraped_at": datetime.utcnow(),
                "from_cache": False
            },
            {
                "product": "Wyld Strawberry Gummies",
                "competitor": "Harborside",
                "price": 14.00,
                "status": "in_stock",
                "scraped_at": datetime.utcnow(),
                "from_cache": True
            },
            {
                "product": "Wyld Strawberry Gummies",
                "competitor": "Theraleaf",
                "price": None,
                "status": "not_carried",
                "scraped_at": datetime.utcnow(),
                "from_cache": False
            }
        ]
        
        formatted = pricing_tools._format_price_results(results)
        
        assert "Competitive Pricing Report" in formatted
        assert "Best price: $12.60" in formatted
        assert "Average price:" in formatted
        assert "Not carried by: Theraleaf" in formatted


class TestCompetitivePricingAgent:
    """Test the full agent integration"""
    
    @pytest.mark.asyncio
    async def test_agent_creation(self):
        """Test agent can be created successfully"""
        agent = get_competitive_pricing_agent(
            model_id="gpt-4o",
            user_id="test_user",
            session_id="test_session",
            debug_mode=False
        )
        
        assert agent is not None
        assert agent.agent_id == "competitive_pricing"
        assert agent.name == "Competitive Pricing Intelligence Agent"
        assert len(agent.tools) >= 3  # pricing_tools, reasoning_tools, firecrawl_tools
    
    def test_agent_has_required_tools(self):
        """Test agent has all required tool types"""
        agent = get_competitive_pricing_agent()
        
        tool_names = [tool.name for tool in agent.tools]
        assert "competitor_pricing_tools" in tool_names
        assert any("reasoning" in name for name in tool_names)
        assert any("firecrawl" in name for name in tool_names)


# Integration Tests

class TestIntegration:
    """Full workflow integration tests"""
    
    @pytest.mark.asyncio
    async def test_complete_pricing_workflow(self):
        """Test complete workflow from competitor to analysis"""
        with patch('agents.competitive_pricing_agent.create_engine'):
            with patch('agents.competitive_pricing_agent.sessionmaker'):
                tools = CompetitorPricingTools('postgresql://test')
                
                # Mock all database and API calls
                with patch.object(tools, 'Session') as mock_session_factory:
                    mock_session = MagicMock()
                    mock_session.__enter__ = MagicMock(return_value=mock_session)
                    mock_session.__exit__ = MagicMock(return_value=None)
                    mock_session_factory.return_value = mock_session
                    
                    # Step 1: Add competitor
                    mock_session.execute.return_value.fetchone.return_value = [1]
                    result = await tools.add_competitor("Test Shop", ["https://test.com"])
                    assert "✅" in result
                    
                    # Step 2: Track product
                    mock_session.execute.side_effect = [
                        MagicMock(fetchone=lambda: None),
                        MagicMock(fetchone=lambda: [1])
                    ]
                    result = await tools.track_product("Test Product", "Test Brand")
                    assert "✅" in result
                    
                    # Step 3: Check prices (with mocked scraping)
                    with patch.object(tools, '_scrape_competitor_price') as mock_scrape:
                        mock_scrape.return_value = PriceData(
                            product_name="Test Brand Test Product",
                            price=10.00,
                            availability_status="in_stock"
                        )
                        
                        mock_session.execute.side_effect = [
                            MagicMock(fetchall=lambda: [[1, "Test Product", "Test Brand", "{}"]]),
                            MagicMock(fetchall=lambda: [[1, "Test Shop", ["https://test.com"]]]),
                            MagicMock(fetchone=lambda: None)  # No cache
                        ]
                        
                        result = await tools.check_prices("Test Product", force_refresh=True)
                        assert "$10.00" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])