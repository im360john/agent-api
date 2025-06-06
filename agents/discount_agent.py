# agents/comprehensive_agent.py
import os
import asyncio
from typing import Dict, Any, List
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.mcp import MCPTools, MultiMCPTools
from agno.tools.base import Tool
import requests
import json

# Custom OpenAPI Tool Implementation for Treez API
class TreezDiscountTool(Tool):
    """Custom tool for Treez discount operations"""
    
    def __init__(self, operation: str, description: str):
        self.operation = operation
        self.base_url = "https://uzvlw67ks9.execute-api.us-west-2.amazonaws.com/dev"
        self.api_key = "qYzy78OgBb63vpLqh88kYauPZ0kHhNWz8ABUJcxh"
        super().__init__(name=operation, description=description)
    
    def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request to Treez API"""
        headers = {
            "X-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{self.base_url}{endpoint}",
            headers=headers,
            json=payload
        )
        
        response.raise_for_status()
        return response.json() if response.content else {"status": "success"}
    
    def call(self, **kwargs) -> Dict[str, Any]:
        """Execute the specific operation"""
        try:
            if self.operation == "getDiscounts":
                return self._make_request(
                    "/poc-gpt-get-discounts",
                    {"env": kwargs.get("env", "partnersandbox3")}
                )
            
            elif self.operation == "deleteDiscount":
                if not kwargs.get("discountId"):
                    return {"error": "discountId is required for deletion"}
                return self._make_request(
                    "/poc-gpt-delete-discount",
                    {
                        "env": kwargs.get("env", "partnersandbox3"),
                        "discountId": kwargs["discountId"]
                    }
                )
            
            elif self.operation == "createDiscount":
                # Build the payload with all parameters
                payload = {
                    "env": kwargs.get("env", "partnersandbox3"),
                    "discountTitle": kwargs.get("discountTitle", "title_placeholder"),
                    "discountAmount": kwargs.get("discountAmount", "1"),
                    "discountMethod": kwargs.get("discountMethod", "DOLLAR"),
                    "entityId": kwargs.get("entityId", "entity_id_placeholder"),
                    "organizationId": kwargs.get("organizationId", "org_id_placeholder"),
                    "isAdjustment": kwargs.get("isAdjustment", False),
                    "isStackable": kwargs.get("isStackable", False),
                    "requireCoupon": kwargs.get("requireCoupon", False)
                }
                
                # Add coupon fields if coupon is required
                if kwargs.get("requireCoupon"):
                    payload.update({
                        "couponDescription": kwargs.get("couponDescription", "description placeholder"),
                        "couponCode": kwargs.get("couponCode", "coupon_code_placeholder"),
                        "couponTitle": kwargs.get("couponTitle", "coupon_title_placeholder"),
                        "couponStartDate": kwargs.get("couponStartDate", "2000-01-01"),
                        "couponEndDate": kwargs.get("couponEndDate", "2030-01-01"),
                        "couponStartTime": kwargs.get("couponStartTime", "00:00:00"),
                        "couponEndTime": kwargs.get("couponEndTime", "23:59:00")
                    })
                
                # Add condition fields if specified
                if kwargs.get("conditionCustomerCapEnabled"):
                    payload.update({
                        "conditionCustomerCapEnabled": True,
                        "conditionCustomerCapValue": kwargs.get("conditionCustomerCapValue", 1)
                    })
                
                if kwargs.get("conditionPurchaseMinimumEnabled"):
                    payload.update({
                        "conditionPurchaseMinimumEnabled": True,
                        "conditionPurchaseMinimumType": kwargs.get("conditionPurchaseMinimumType", "SUBTOTAL"),
                        "conditionPurchaseMinimumValue": kwargs.get("conditionPurchaseMinimumValue", 10)
                    })
                
                return self._make_request("/poc-gpt-create-discount", payload)
            
        except Exception as e:
            return {"error": str(e)}


# Create the Treez tools
def get_treez_tools() -> List[Tool]:
    """Get all Treez discount management tools"""
    return [
        TreezDiscountTool(
            "getDiscounts",
            "Fetch all discounts from Treez. Optionally specify env (default: partnersandbox3)"
        ),
        TreezDiscountTool(
            "deleteDiscount",
            "Delete a discount by ID. Required: discountId. Optional: env (default: partnersandbox3)"
        ),
        TreezDiscountTool(
            "createDiscount",
            "Create a new discount. Required: discountTitle, discountAmount, discountMethod (DOLLAR/PERCENT), entityId, organizationId. Optional: coupon settings, conditions, etc."
        )
    ]


async def get_comprehensive_agent(agent_id: str = None, user_id: str = None, session_id: str = None):
    """
    Create a comprehensive agent with:
    - MCP servers: Google Drive, Slack, Fetch (via npx)
    - MCP SSE servers: Snowflake, Browserbase (via URLs)
    - OpenAPI tools: Treez discount management
    """
    
    # Environment variables for MCP servers
    env = {
        **os.environ,
        # Add any required tokens/keys for MCP servers
        "SLACK_TOKEN": os.getenv("SLACK_TOKEN", ""),
        "GOOGLE_DRIVE_TOKEN": os.getenv("GOOGLE_DRIVE_TOKEN", ""),
        "SNOWFLAKE_TOKEN": os.getenv("SNOWFLAKE_TOKEN", ""),
        "BROWSERBASE_API_KEY": os.getenv("BROWSERBASE_API_KEY", ""),
    }
    
    # NPX-based MCP servers
    npx_servers = [
        "npx -y @modelcontextprotocol/server-google-drive",
        "npx -y @modelcontextprotocol/server-slack",
        "npx -y @modelcontextprotocol/server-fetch"
    ]
    
    # SSE-based MCP servers (URLs)
    sse_servers = []
    
    # Add Snowflake SSE server if URL is configured
    snowflake_url = os.getenv("SNOWFLAKE_MCP_URL")
    if snowflake_url:
        sse_servers.append(snowflake_url)
    
    # Add Browserbase SSE server if URL is configured
    browserbase_url = os.getenv("BROWSERBASE_MCP_URL")
    if browserbase_url:
        sse_servers.append(browserbase_url)
    
    # Initialize all tools
    all_tools = []
    
    # Add Treez OpenAPI tools
    all_tools.extend(get_treez_tools())
    
    # Create MCP tools context managers
    mcp_contexts = []
    
    # NPX-based MCP tools
    if npx_servers:
        npx_mcp = MultiMCPTools(npx_servers, env=env)
        mcp_contexts.append(npx_mcp)
    
    # SSE-based MCP tools
    for sse_url in sse_servers:
        sse_mcp = MCPTools(url=sse_url)
        mcp_contexts.append(sse_mcp)
    
    # Use AsyncExitStack to manage multiple contexts
    from contextlib import AsyncExitStack
    
    async with AsyncExitStack() as stack:
        # Enter all MCP contexts
        for mcp_context in mcp_contexts:
            mcp_tools = await stack.enter_async_context(mcp_context)
            all_tools.append(mcp_tools)
        
        # Create and return the agent
        return Agent(
            agent_id=agent_id or "comprehensive_agent",
            name="Comprehensive Multi-Tool Agent",
            user_id=user_id,
            session_id=session_id,
            model=OpenAIChat(id="gpt-4o", temperature=0.7),
            tools=all_tools,
            description="I'm a comprehensive assistant with access to Google Drive, Slack, web fetching, Snowflake, browser automation, and Treez discount management",
            instructions=[
                # Google Drive instructions
                "For file-related queries, use Google Drive to search and retrieve documents",
                "When asked about documents, spreadsheets, or presentations, search Google Drive first",
                
                # Slack instructions
                "For team communication or message history, use Slack tools",
                "Search Slack for conversations, users, or channel information when relevant",
                
                # Fetch instructions
                "Use fetch tools to retrieve content from URLs when needed",
                "For web content that users reference, use fetch to get the actual content",
                
                # Snowflake instructions (if available)
                "For data warehouse queries or analytics, use Snowflake when available",
                "Execute SQL queries on Snowflake for business intelligence requests",
                
                # Browserbase instructions (if available)
                "For web automation or browser-based tasks, use Browserbase",
                "Use browser automation for complex web interactions or scraping",
                
                # Treez discount instructions
                "For discount management in Treez:",
                "- Use getDiscounts to list all current discounts",
                "- Use createDiscount to create new discounts (ensure all required fields are provided)",
                "- Use deleteDiscount to remove discounts (requires discountId)",
                "- Always confirm successful operations and handle errors gracefully",
                "- When creating discounts with coupons, ensure all coupon fields are properly set",
                
                # General instructions
                "Choose the most appropriate tool based on the user's request",
                "Combine information from multiple sources when it adds value",
                "Always provide clear feedback about which tools were used and their results",
                "Handle errors gracefully and suggest alternatives when a tool fails"
            ],
            markdown=True,
            show_tool_calls=True,
            # Enable storage if needed
            # storage=PostgresAgentStorage(
            #     table_name="comprehensive_agent_sessions",
            #     db_engine=db_engine
            # ),
        )


# Synchronous wrapper for FastAPI compatibility
def get_comprehensive_agent_sync(agent_id: str = None, user_id: str = None, session_id: str = None):
    """Synchronous wrapper for the async agent creation"""
    import nest_asyncio
    nest_asyncio.apply()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(
            get_comprehensive_agent(agent_id, user_id, session_id)
        )
    finally:
        loop.close()


# Alternative: Create separate specialized agents
def get_treez_agent(agent_id: str = None, user_id: str = None, session_id: str = None):
    """Create an agent specifically for Treez discount management"""
    return Agent(
        agent_id=agent_id or "treez_agent",
        name="Treez Discount Manager",
        user_id=user_id,
        session_id=session_id,
        model=OpenAIChat(id="gpt-4o"),
        tools=get_treez_tools(),
        description="I manage discounts in the Treez system",
        instructions=[
            "I can help you manage discounts in Treez:",
            "- List all current discounts",
            "- Create new discounts with various options (dollar/percent, coupons, conditions)",
            "- Delete existing discounts",
            "Always verify required fields before creating discounts",
            "Provide clear confirmation of successful operations"
        ],
        markdown=True,
        show_tool_calls=True,
    )
