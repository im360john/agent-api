#!/usr/bin/env python3
"""AG UI Chat Interface for Competitive Pricing Agent"""

from agno.models.openai import OpenAIChat
from agno.agent import Agent
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.storage.agent.postgres import PostgresAgentStorage
from agno.apps.ag_ui import AGUIApp

from agents.competitive_pricing_agent_enhanced import EnhancedCompetitorPricingTools
from db.session import db_url
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Create the agent
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

# Initialize the agent
agent = create_agent()

# Create the AG UI app
app = AGUIApp(
    agent=agent,
    name="💰 Competitive Pricing Assistant",
    description="Track cannabis prices across dispensaries with confidence scoring",
)

# Add custom actions in the sidebar
app.add_action("Check All Prices", "check prices for all tracked products")
app.add_action("View Competitors", "list all competitors with their status")
app.add_action("Confidence Report", "show me the scraping confidence report")
app.add_action("Track New Product", "help me add a new product to track")
app.add_action("Price Trends", "analyze pricing trends for the last 7 days")

# Set welcome message
app.set_welcome_message("""
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

if __name__ == "__main__":
    print("🚀 Starting Competitive Pricing UI...")
    print("📍 Access at: http://localhost:7100")
    app.run()