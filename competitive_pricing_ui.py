#!/usr/bin/env python3
"""AG UI Chat Interface for Competitive Pricing Agent"""

from agno.apps.ag_ui import AGUIApp
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
    You are an AI assistant specialized in competitive price tracking for cannabis dispensaries with enhanced capabilities.
    
    ## Your Capabilities:
    
    1. **Price Checking**: Compare prices across multiple dispensaries
    2. **Product Tracking**: Add and manage products to track
    3. **Competitor Management**: Add, update, or remove competitor dispensaries
    4. **Historical Analysis**: View price trends and changes over time
    5. **Batch Operations**: Check multiple products at once
    6. **Learning System**: Record corrections to improve accuracy
    
    ## Enhanced Features:
    
    - **Confidence Scores**: All results include confidence indicators
      - 🟢 High confidence (>70%): Highly reliable data
      - 🟡 Medium confidence (40-70%): Generally reliable
      - 🔴 Low confidence (<40%): May need verification
    
    - **Scraping Details**: You provide transparency about:
      - Which tool was used (Firecrawl, Browserbase, Exa)
      - The URL that was scraped
      - Response time for each scrape
    
    - **User Corrections**: When users correct your data, use the `record_user_correction` tool
    
    ## Response Format:
    
    - Use clear markdown formatting
    - Include tables for price comparisons
    - Show confidence indicators
    - Provide actionable insights
    - Be concise but informative
    
    ## Example Interactions:
    
    - "Check prices for Wyld Gummies"
    - "Add a new competitor: Example Dispensary at https://example.com"
    - "Show me price trends for the last week"
    - "The price at Harborside should be $18, not $20"
    - "Create a batch job to check all edibles"
    
    Always mention data freshness and confidence levels when reporting prices.
    """
    
    agent = Agent(
        name="competitive_pricing_ui",
        agent_id="competitive_pricing_ui", 
        model=OpenAIChat(id="gpt-4o"),
        tools=tools,
        storage=PostgresAgentStorage(
            table_name="competitive_pricing_ui_agents", 
            db_url=db_url
        ),
        memory=Memory(
            db=PostgresMemoryDb(
                table_name="competitive_pricing_ui_memory",
                db_url=db_url,
            )
        ),
        instructions=instructions,
        markdown=True,
    )
    
    return agent

# Configure the AG UI app
app_config = {
    "app": {
        "name": "🏪 Competitive Pricing Assistant",
        "description": "AI-powered price tracking and analysis for cannabis dispensaries",
        "version": "2.0.0"
    },
    "ui": {
        "theme": {
            "primary_color": "#2E7D32",  # Green theme for cannabis industry
            "secondary_color": "#66BB6A",
            "background_color": "#F1F8E9",
            "text_color": "#1B5E20"
        },
        "header": {
            "title": "Competitive Pricing Assistant",
            "subtitle": "Track prices across dispensaries with confidence scoring",
            "logo": "💰"  # Can be replaced with actual logo URL
        },
        "chat": {
            "placeholder": "Ask about prices, add competitors, track products...",
            "initial_messages": [
                {
                    "role": "assistant",
                    "content": """👋 Welcome to the Competitive Pricing Assistant!

I can help you:
- 🔍 **Check prices** across all competitors
- 📊 **Track products** and monitor changes
- 🏪 **Manage competitors** and their URLs
- 📈 **Analyze trends** and price history
- 🎯 **Learn from corrections** to improve accuracy

Try asking:
- "Check prices for Wyld Strawberry Gummies"
- "Show me the pricing confidence report"
- "Add a new competitor"
- "What products are we tracking?"

All results include confidence scores (🟢 High, 🟡 Medium, 🔴 Low) to help you assess data reliability."""
                }
            ]
        },
        "sidebar": {
            "enabled": True,
            "sections": [
                {
                    "title": "Quick Actions",
                    "items": [
                        {"label": "Check All Prices", "action": "check prices for all tracked products"},
                        {"label": "View Competitors", "action": "list all competitors"},
                        {"label": "Tracked Products", "action": "list all tracked products"},
                        {"label": "Confidence Report", "action": "show scraping confidence report"}
                    ]
                },
                {
                    "title": "Analysis Tools",
                    "items": [
                        {"label": "Price Trends", "action": "analyze pricing trends for the last 7 days"},
                        {"label": "Performance", "action": "analyze scraping performance"},
                        {"label": "Batch Jobs", "action": "list batch jobs"}
                    ]
                },
                {
                    "title": "Management",
                    "items": [
                        {"label": "Add Product", "action": "help me add a new product to track"},
                        {"label": "Add Competitor", "action": "help me add a new competitor"},
                        {"label": "Report Correction", "action": "I need to correct some pricing data"}
                    ]
                }
            ]
        },
        "features": {
            "file_upload": False,  # Not needed for this use case
            "voice_input": True,
            "copy_button": True,
            "export_chat": True,
            "dark_mode": True
        }
    },
    "agent": {
        "show_thinking": False,  # Hide internal processing
        "stream_responses": True,
        "response_timeout": 120,  # 2 minutes for complex operations
        "error_handling": {
            "show_errors": True,
            "retry_on_error": True,
            "max_retries": 2
        }
    }
}

# Create the AG UI application
def create_app():
    """Create and configure the AG UI application"""
    agent = create_ui_agent()
    
    # Initialize AG UI app
    app = AGUIApp(
        agent=agent,
        config=app_config,
        host="0.0.0.0",
        port=8080,
        debug=True
    )
    
    # Add custom CSS for better styling
    app.add_custom_css("""
        /* Custom styling for confidence indicators */
        .confidence-high { color: #4CAF50; font-weight: bold; }
        .confidence-medium { color: #FF9800; font-weight: bold; }
        .confidence-low { color: #F44336; font-weight: bold; }
        
        /* Table styling */
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 16px 0;
        }
        
        th {
            background-color: #2E7D32;
            color: white;
            padding: 12px;
            text-align: left;
        }
        
        td {
            padding: 12px;
            border-bottom: 1px solid #ddd;
        }
        
        tr:hover {
            background-color: #F1F8E9;
        }
        
        /* Price formatting */
        .price {
            font-family: monospace;
            font-weight: bold;
        }
        
        /* Status badges */
        .status-in-stock {
            background-color: #4CAF50;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
        }
        
        .status-out-of-stock {
            background-color: #F44336;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
        }
        
        /* Sidebar styling */
        .sidebar-action {
            cursor: pointer;
            padding: 8px 12px;
            margin: 4px 0;
            border-radius: 4px;
            transition: background-color 0.3s;
        }
        
        .sidebar-action:hover {
            background-color: #66BB6A;
            color: white;
        }
    """)
    
    # Add custom JavaScript for enhanced interactivity
    app.add_custom_js("""
        // Add click handlers for quick actions
        document.addEventListener('DOMContentLoaded', function() {
            // Highlight confidence scores
            document.querySelectorAll('td').forEach(td => {
                if (td.textContent.includes('🟢')) {
                    td.classList.add('confidence-high');
                } else if (td.textContent.includes('🟡')) {
                    td.classList.add('confidence-medium');
                } else if (td.textContent.includes('🔴')) {
                    td.classList.add('confidence-low');
                }
            });
            
            // Format prices
            document.querySelectorAll('td').forEach(td => {
                if (td.textContent.match(/\$\d+\.\d{2}/)) {
                    td.classList.add('price');
                }
            });
        });
    """)
    
    return app

# Run the application
if __name__ == "__main__":
    print("🚀 Starting Competitive Pricing UI...")
    print("📍 Access the interface at: http://localhost:8080")
    print("💡 Press Ctrl+C to stop the server\n")
    
    app = create_app()
    app.run()