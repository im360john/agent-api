# agents/comprehensive_agent.py
import os
import asyncio
from typing import Dict, Any, List, Optional
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.mcp import MCPTools, MultiMCPTools
from agno.tools.toolkit import Toolkit
import requests
import json


class TreezDiscountTools(Toolkit):
    """
    Toolkit for Treez discount management operations
    """
    
    def __init__(self):
        super().__init__(name="treez_discount_tools")
        self.base_url = "https://uzvlw67ks9.execute-api.us-west-2.amazonaws.com/dev"
        self.api_key = "qYzy78OgBb63vpLqh88kYauPZ0kHhNWz8ABUJcxh"
    
    def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request to Treez API"""
        headers = {
            "X-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}{endpoint}",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json() if response.content else {"status": "success"}
        except requests.exceptions.RequestException as e:
            return {"error": f"API request failed: {str(e)}"}
    
    def get_discounts(self, env: str = "partnersandbox3") -> Dict[str, Any]:
        """
        Fetch all discounts from Treez
        
        Args:
            env: Environment to fetch from (default: partnersandbox3)
            
        Returns:
            Dict containing discount data or error
        """
        return self._make_request("/poc-gpt-get-discounts", {"env": env})
    
    def delete_discount(self, discount_id: str, env: str = "partnersandbox3") -> Dict[str, Any]:
        """
        Delete a discount by ID
        
        Args:
            discount_id: The ID of the discount to delete
            env: Environment (default: partnersandbox3)
            
        Returns:
            Dict containing operation result
        """
        if not discount_id:
            return {"error": "discount_id is required"}
            
        return self._make_request(
            "/poc-gpt-delete-discount",
            {
                "env": env,
                "discountId": discount_id
            }
        )
    
    def create_discount(
        self,
        discount_title: str,
        discount_amount: str,
        discount_method: str,
        entity_id: str,
        organization_id: str,
        env: str = "partnersandbox3",
        is_adjustment: bool = False,
        is_stackable: bool = False,
        require_coupon: bool = False,
        coupon_description: Optional[str] = None,
        coupon_code: Optional[str] = None,
        coupon_title: Optional[str] = None,
        coupon_start_date: Optional[str] = None,
        coupon_end_date: Optional[str] = None,
        coupon_start_time: Optional[str] = None,
        coupon_end_time: Optional[str] = None,
        condition_customer_cap_enabled: bool = False,
        condition_customer_cap_value: Optional[int] = None,
        condition_purchase_minimum_enabled: bool = False,
        condition_purchase_minimum_type: Optional[str] = None,
        condition_purchase_minimum_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Create a new discount in Treez
        
        Args:
            discount_title: Title of the discount
            discount_amount: Amount of discount
            discount_method: Method - either DOLLAR or PERCENT
            entity_id: Entity ID in the environment
            organization_id: Organization ID in the environment
            env: Environment (default: partnersandbox3)
            is_adjustment: Whether discount is an adjustment
            is_stackable: Whether discount is stackable
            require_coupon: Whether discount requires a coupon
            coupon_description: Description of coupon (if require_coupon=True)
            coupon_code: Code to redeem coupon (if require_coupon=True)
            coupon_title: Title of coupon (if require_coupon=True)
            coupon_start_date: Start date YYYY-MM-DD (if require_coupon=True)
            coupon_end_date: End date YYYY-MM-DD (if require_coupon=True)
            coupon_start_time: Start time HH:mm:ss (if require_coupon=True)
            coupon_end_time: End time HH:mm:ss (if require_coupon=True)
            condition_customer_cap_enabled: Enable customer cap condition
            condition_customer_cap_value: Customer cap value (if enabled)
            condition_purchase_minimum_enabled: Enable purchase minimum condition
            condition_purchase_minimum_type: SUBTOTAL or GRANDTOTAL (if enabled)
            condition_purchase_minimum_value: Minimum purchase value (if enabled)
            
        Returns:
            Dict containing created discount data or error
        """
        # Build base payload
        payload = {
            "env": env,
            "discountTitle": discount_title,
            "discountAmount": discount_amount,
            "discountMethod": discount_method,
            "entityId": entity_id,
            "organizationId": organization_id,
            "isAdjustment": is_adjustment,
            "isStackable": is_stackable,
            "requireCoupon": require_coupon
        }
        
        # Add coupon fields if required
        if require_coupon:
            payload.update({
                "couponDescription": coupon_description or "Discount coupon",
                "couponCode": coupon_code or "AUTO_GENERATED",
                "couponTitle": coupon_title or discount_title,
                "couponStartDate": coupon_start_date or "2000-01-01",
                "couponEndDate": coupon_end_date or "2030-01-01",
                "couponStartTime": coupon_start_time or "00:00:00",
                "couponEndTime": coupon_end_time or "23:59:00"
            })
        
        # Add customer cap condition if enabled
        if condition_customer_cap_enabled:
            payload.update({
                "conditionCustomerCapEnabled": True,
                "conditionCustomerCapValue": condition_customer_cap_value or 1
            })
        
        # Add purchase minimum condition if enabled
        if condition_purchase_minimum_enabled:
            payload.update({
                "conditionPurchaseMinimumEnabled": True,
                "conditionPurchaseMinimumType": condition_purchase_minimum_type or "SUBTOTAL",
                "conditionPurchaseMinimumValue": condition_purchase_minimum_value or 10
            })
        
        return self._make_request("/poc-gpt-create-discount", payload)


async def get_comprehensive_agent(agent_id: str = None, user_id: str = None, session_id: str = None):
    """
    Create a comprehensive agent with:
    - MCP servers: Google Drive, Slack, Fetch (via npx)
    - MCP SSE servers: Snowflake, Browserbase (via URLs)
    - Custom tools: Treez discount management
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
    
    # Initialize tools list
    all_tools = []
    
    # Add Treez discount management tools
    all_tools.append(TreezDiscountTools())
    
    # Create MCP tools context managers
    mcp_contexts = []
    
    # NPX-based MCP tools
    if npx_servers:
        npx_mcp = MultiMCPTools(npx_servers, env=env)
        mcp_contexts.append(npx_mcp)
    
    # SSE-based MCP tools - add individually if URLs are configured
    snowflake_url = os.getenv("SNOWFLAKE_MCP_URL")
    if snowflake_url:
        snowflake_mcp = MCPTools(url=snowflake_url)
        mcp_contexts.append(snowflake_mcp)
    
    browserbase_url = os.getenv("BROWSERBASE_MCP_URL")
    if browserbase_url:
        browserbase_mcp = MCPTools(url=browserbase_url)
        mcp_contexts.append(browserbase_mcp)
    
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
                "- Use get_discounts() to list all current discounts",
                "- Use create_discount() to create new discounts - ensure you have discount_title, discount_amount, discount_method (DOLLAR/PERCENT), entity_id, and organization_id",
                "- Use delete_discount() to remove discounts - requires discount_id parameter",
                "- When creating discounts with coupons (require_coupon=True), also provide coupon details",
                "- You can add conditions like customer caps or purchase minimums",
                "- Always confirm successful operations and handle errors gracefully",
                
                # General instructions
                "Choose the most appropriate tool based on the user's request",
                "Combine information from multiple sources when it adds value",
                "Always provide clear feedback about which tools were used and their results",
                "Handle errors gracefully and suggest alternatives when a tool fails"
            ],
            markdown=True,
            show_tool_calls=True,
        )


# Alternative simpler version without MCP (if you want to test just Treez first)
def get_treez_agent(agent_id: str = None, user_id: str = None, session_id: str = None):
    """Create an agent specifically for Treez discount management"""
    return Agent(
        agent_id=agent_id or "treez_agent",
        name="Treez Discount Manager",
        user_id=user_id,
        session_id=session_id,
        model=OpenAIChat(id="gpt-4o"),
        tools=[TreezDiscountTools()],
        description="I manage discounts in the Treez system",
        instructions=[
            "I can help you manage discounts in Treez:",
            "- Use get_discounts() to list all current discounts",
            "- Use create_discount() to create new discounts",
            "  Required: discount_title, discount_amount, discount_method (DOLLAR/PERCENT), entity_id, organization_id",
            "  Optional: coupon settings, purchase conditions, customer caps",
            "- Use delete_discount(discount_id) to remove a discount",
            "Always verify required fields before creating discounts",
            "Handle the env parameter (default is partnersandbox3)",
            "Provide clear confirmation of successful operations"
        ],
        markdown=True,
        show_tool_calls=True,
    )


# If your API needs a synchronous version
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
