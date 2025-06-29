"""UI Router for AG UI Chat Interface"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from agno.apps.ag_ui import AGUIApp
from agno.models.openai import OpenAIChat
from agno.agent import Agent
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.storage.agent.postgres import PostgresAgentStorage

from agents.competitive_pricing_agent_enhanced import EnhancedCompetitorPricingTools
from db.session import db_url
import asyncio
import threading

# Create router
ui_router = APIRouter(prefix="/chat", tags=["UI"])

# Global variable to store the AG UI app
agui_app = None
agui_thread = None

def create_agent() -> Agent:
    """Create the enhanced competitive pricing agent"""
    
    # Initialize enhanced tools
    tools = EnhancedCompetitorPricingTools(db_url=db_url)
    
    # Instructions
    instructions = """You are a competitive pricing assistant for cannabis dispensaries.

    Key features:
    - Check prices across competitors with confidence scores (🟢 High >70%, 🟡 Medium 40-70%, 🔴 Low <40%)
    - Track products and manage competitors
    - Learn from user corrections to improve accuracy
    - Analyze pricing trends and scraping performance
    
    Always mention confidence levels and data freshness when reporting prices.
    Format responses with clear tables and actionable insights."""
    
    return Agent(
        name="competitive_pricing",
        agent_id="competitive_pricing", 
        model=OpenAIChat(id="gpt-4o"),
        tools=tools,
        storage=PostgresAgentStorage(
            table_name="competitive_pricing_agents", 
            db_url=db_url
        ),
        memory=Memory(
            db=PostgresMemoryDb(
                table_name="competitive_pricing_memory",
                db_url=db_url,
            )
        ),
        instructions=instructions,
        markdown=True,
    )

def initialize_agui():
    """Initialize AG UI app in a separate thread"""
    global agui_app
    
    # Create agent
    agent = create_agent()
    
    # Create AG UI app with custom port that won't conflict
    agui_app = AGUIApp(
        agent=agent,
        name="💰 Competitive Pricing Assistant",
        description="Track cannabis prices across dispensaries with confidence scoring",
        host="127.0.0.1",
        port=7100,  # Internal port
    )
    
    # Add custom actions
    agui_app.add_action("Check All Prices", "check prices for all tracked products")
    agui_app.add_action("View Competitors", "list all competitors with their status")
    agui_app.add_action("Confidence Report", "show me the scraping confidence report")
    agui_app.add_action("Track New Product", "help me add a new product to track")
    agui_app.add_action("Price Trends", "analyze pricing trends for the last 7 days")
    
    # Set welcome message
    agui_app.set_welcome_message("""
👋 Welcome to the Competitive Pricing Assistant!

I can help you:
- 🔍 **Check prices** across all competitors
- 📊 **Track products** and monitor changes  
- 🎯 **Learn from corrections** to improve accuracy
- 📈 **Analyze trends** and scraping performance

Example queries:
- "Check prices for Wyld Strawberry Gummies"
- "Show me which competitors have the best prices"
- "The price at Harborside should be $18, not $20"
- "How confident are we in the Elemental Wellness data?"

All results include confidence scores to help assess reliability!
""")
    
    # Run AG UI app
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(agui_app.run_async())

# Initialize AG UI on import
if agui_thread is None:
    agui_thread = threading.Thread(target=initialize_agui, daemon=True)
    agui_thread.start()
    # Give it time to start
    import time
    time.sleep(2)

@ui_router.get("/", response_class=HTMLResponse)
async def chat_interface(request: Request):
    """Serve the AG UI chat interface"""
    # Proxy to the AG UI app running on internal port
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Competitive Pricing Assistant</title>
        <style>
            body, html {{
                margin: 0;
                padding: 0;
                height: 100%;
                overflow: hidden;
            }}
            iframe {{
                width: 100%;
                height: 100%;
                border: none;
            }}
        </style>
    </head>
    <body>
        <iframe src="http://localhost:7100" allow="clipboard-write"></iframe>
    </body>
    </html>
    """)

# Alternative approach: Mount AG UI directly
# This requires AG UI to support being mounted as a sub-app
try:
    from agno.apps.ag_ui.core import get_agui_routes
    
    # Get AG UI routes
    agui_routes = get_agui_routes(create_agent())
    
    # Add routes to router
    for route in agui_routes:
        ui_router.add_api_route(
            path=route.path,
            endpoint=route.endpoint,
            methods=route.methods,
            **route.kwargs
        )
except ImportError:
    # AG UI doesn't support direct mounting yet
    pass