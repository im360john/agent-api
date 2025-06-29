#!/usr/bin/env python3
"""Advanced AG UI with Dojo components for Competitive Pricing Agent"""

from agno.apps.ag_ui import AGUIApp, DojoComponents
from agno.models.openai import OpenAIChat
from agno.agent import Agent
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.storage.agent.postgres import PostgresAgentStorage

from agents.competitive_pricing_agent_enhanced import EnhancedCompetitorPricingTools
from db.session import db_url
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Create the enhanced competitive pricing agent
def create_ui_agent() -> Agent:
    """Create the enhanced competitive pricing agent for UI"""
    
    # Initialize enhanced tools
    tools = EnhancedCompetitorPricingTools(db_url=db_url)
    
    # Enhanced instructions with UI-friendly formatting
    instructions = """
    You are an AI assistant specialized in competitive price tracking for cannabis dispensaries.
    
    ## Your Capabilities:
    1. **Price Checking**: Compare prices with confidence scores
    2. **Product Tracking**: Manage products with variant detection
    3. **Learning System**: Improve accuracy through user corrections
    4. **Performance Analysis**: Monitor scraping effectiveness
    
    Always format responses with clear tables and include confidence indicators.
    Use the Dojo UI components when appropriate for better visualization.
    """
    
    agent = Agent(
        name="competitive_pricing_ui_advanced",
        agent_id="competitive_pricing_ui_advanced", 
        model=OpenAIChat(id="gpt-4o"),
        tools=tools,
        storage=PostgresAgentStorage(
            table_name="competitive_pricing_ui_advanced_agents", 
            db_url=db_url
        ),
        memory=Memory(
            db=PostgresMemoryDb(
                table_name="competitive_pricing_ui_advanced_memory",
                db_url=db_url,
            )
        ),
        instructions=instructions,
        markdown=True,
    )
    
    return agent

# Create the AG UI application with Dojo components
def create_app():
    """Create and configure the AG UI application with Dojo"""
    agent = create_ui_agent()
    
    # Initialize Dojo components
    dojo = DojoComponents()
    
    # Configure advanced UI with Dojo
    app_config = {
        "app": {
            "name": "🏪 Competitive Pricing Pro",
            "description": "Advanced price tracking with confidence scoring",
            "version": "2.1.0"
        },
        "dojo": {
            "enabled": True,
            "theme": "cannabis",  # Custom theme
            "components": {
                "DataGrid": {
                    "enabled": True,
                    "features": ["sorting", "filtering", "export"]
                },
                "Charts": {
                    "enabled": True,
                    "types": ["line", "bar", "pie"]
                },
                "Forms": {
                    "enabled": True,
                    "validation": True
                },
                "Notifications": {
                    "enabled": True,
                    "position": "top-right"
                }
            }
        },
        "ui": {
            "layout": "dashboard",  # Dashboard layout for data-heavy app
            "widgets": [
                {
                    "id": "price-overview",
                    "type": "DataGrid",
                    "title": "Current Prices",
                    "position": {"x": 0, "y": 0, "w": 8, "h": 6},
                    "refresh": 300,  # Refresh every 5 minutes
                    "query": "get current prices for all tracked products"
                },
                {
                    "id": "confidence-gauge",
                    "type": "Gauge",
                    "title": "Overall Confidence",
                    "position": {"x": 8, "y": 0, "w": 4, "h": 3},
                    "query": "get average scraping confidence"
                },
                {
                    "id": "competitor-status",
                    "type": "StatusList",
                    "title": "Competitor Status",
                    "position": {"x": 8, "y": 3, "w": 4, "h": 3},
                    "query": "show competitor scraping status"
                },
                {
                    "id": "price-trends",
                    "type": "LineChart",
                    "title": "Price Trends (7 Days)",
                    "position": {"x": 0, "y": 6, "w": 6, "h": 4},
                    "query": "show price trends for top products"
                },
                {
                    "id": "quick-actions",
                    "type": "ActionPanel",
                    "title": "Quick Actions",
                    "position": {"x": 6, "y": 6, "w": 6, "h": 4},
                    "actions": [
                        {
                            "label": "Check All Prices",
                            "icon": "refresh",
                            "action": "check prices for all products",
                            "confirm": true
                        },
                        {
                            "label": "Add Product",
                            "icon": "plus",
                            "action": "show_form:add_product"
                        },
                        {
                            "label": "Report Correction",
                            "icon": "edit",
                            "action": "show_form:correction"
                        },
                        {
                            "label": "Export Report",
                            "icon": "download",
                            "action": "export price report"
                        }
                    ]
                }
            ],
            "forms": {
                "add_product": {
                    "title": "Add Product to Track",
                    "fields": [
                        {
                            "name": "product_name",
                            "label": "Product Name",
                            "type": "text",
                            "required": true,
                            "placeholder": "e.g., Wyld Strawberry Gummies"
                        },
                        {
                            "name": "brand",
                            "label": "Brand",
                            "type": "text",
                            "required": true,
                            "placeholder": "e.g., Wyld"
                        },
                        {
                            "name": "category",
                            "label": "Category",
                            "type": "select",
                            "options": ["edibles", "flower", "vapes", "concentrates", "topicals"],
                            "required": true
                        },
                        {
                            "name": "variants",
                            "label": "Track Variants",
                            "type": "checkbox",
                            "default": true
                        }
                    ],
                    "submit_action": "track product: {product_name}, brand: {brand}, category: {category}"
                },
                "correction": {
                    "title": "Report Price Correction",
                    "fields": [
                        {
                            "name": "product",
                            "label": "Product",
                            "type": "select",
                            "options_query": "list tracked products",
                            "required": true
                        },
                        {
                            "name": "competitor",
                            "label": "Competitor",
                            "type": "select",
                            "options": ["Harborside", "Elemental Wellness", "Theraleaf", "Airfield"],
                            "required": true
                        },
                        {
                            "name": "correction_type",
                            "label": "What to Correct",
                            "type": "select",
                            "options": ["price", "stock_status", "url"],
                            "required": true
                        },
                        {
                            "name": "correct_value",
                            "label": "Correct Value",
                            "type": "text",
                            "required": true,
                            "placeholder": "e.g., 18.00 or out_of_stock"
                        }
                    ],
                    "submit_action": "record correction for {product} at {competitor}: {correction_type} should be {correct_value}"
                }
            },
            "chat": {
                "position": "bottom",
                "height": "300px",
                "collapsible": true,
                "shortcuts": [
                    {"key": "ctrl+p", "action": "check all prices"},
                    {"key": "ctrl+n", "action": "add new product"},
                    {"key": "ctrl+r", "action": "refresh data"}
                ]
            }
        }
    }
    
    # Initialize AG UI app with Dojo
    app = AGUIApp(
        agent=agent,
        config=app_config,
        components=dojo,
        host="0.0.0.0",
        port=8080,
        debug=True
    )
    
    # Add real-time updates
    app.enable_websocket_updates()
    
    # Add custom event handlers
    @app.on_event("price_change")
    def handle_price_change(data):
        """Handle price change events"""
        app.send_notification({
            "type": "info",
            "title": "Price Change Detected",
            "message": f"{data['product']} at {data['competitor']}: ${data['old_price']} → ${data['new_price']}"
        })
    
    @app.on_event("low_confidence")
    def handle_low_confidence(data):
        """Handle low confidence scraping"""
        app.send_notification({
            "type": "warning",
            "title": "Low Confidence Data",
            "message": f"Low confidence scraping for {data['product']} at {data['competitor']}"
        })
    
    # Add custom API endpoints
    @app.route("/api/export")
    async def export_data(format: str = "csv"):
        """Export pricing data"""
        # Implementation for data export
        pass
    
    @app.route("/api/webhooks/price-alert")
    async def price_alert_webhook(product: str, threshold: float):
        """Set up price alerts"""
        # Implementation for price alerts
        pass
    
    return app

# Create a simple CLI version as well
def create_simple_cli():
    """Create a simple command-line interface"""
    print("""
    🏪 Competitive Pricing CLI
    
    Commands:
    - check <product> - Check prices for a product
    - list products - List all tracked products
    - list competitors - List all competitors
    - add product <name> <brand> - Add a product
    - confidence - Show confidence report
    - quit - Exit
    """)
    
    agent = create_ui_agent()
    
    while True:
        try:
            command = input("\n> ").strip()
            
            if command == "quit":
                break
            elif command.startswith("check "):
                product = command[6:]
                response = agent.run_sync(f"check prices for {product}")
                print(response.content)
            elif command == "list products":
                response = agent.run_sync("list all tracked products")
                print(response.content)
            elif command == "list competitors":
                response = agent.run_sync("list all competitors")
                print(response.content)
            elif command.startswith("add product "):
                parts = command[12:].split(" ", 1)
                if len(parts) == 2:
                    name, brand = parts
                    response = agent.run_sync(f"track product: {name}, brand: {brand}")
                    print(response.content)
                else:
                    print("Usage: add product <name> <brand>")
            elif command == "confidence":
                response = agent.run_sync("show scraping confidence report")
                print(response.content)
            else:
                print("Unknown command. Type 'quit' to exit.")
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

# Run the application
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        create_simple_cli()
    else:
        print("🚀 Starting Competitive Pricing UI (Advanced)...")
        print("📍 Access the interface at: http://localhost:8080")
        print("💡 Press Ctrl+C to stop the server")
        print("🖥️  For CLI mode, run: python competitive_pricing_ui_advanced.py --cli\n")
        
        app = create_app()
        app.run()