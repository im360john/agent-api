# agents/web_agent.py
import os
import asyncio
from textwrap import dedent
from typing import Optional, List

from agno.agent import Agent
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.models.openai import OpenAIChat
from agno.storage.agent.postgres import PostgresAgentStorage
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.mcp import MCPTools
from mcp import StdioServerParameters

from db.session import db_url


def get_web_agent(
    model_id: str = "gpt-4.1",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
    mcp_sse_urls: Optional[List[str]] = None,
) -> Agent:
    """
    Create a Web Search Agent with optional MCP SSE tool integration.
    
    Args:
        model_id: The model to use for the agent
        user_id: Optional user identifier
        session_id: Optional session identifier
        debug_mode: Whether to show debug logs
        mcp_sse_urls: Optional list of MCP SSE URLs to connect to for additional tools
        
    Returns:
        Agent configured with web search and optional MCP tools
    """
    
    # Check if MCP SSE URLs are provided via parameter or environment
    if mcp_sse_urls is None:
        # Check environment for MCP URLs
        env_urls = os.getenv("MCP_SSE_URLS", "").strip()
        if env_urls:
            mcp_sse_urls = [url.strip() for url in env_urls.split(",") if url.strip()]
    
    # If MCP URLs are provided, create an agent that can connect to them
    if mcp_sse_urls:
        # For synchronous context, we need to handle async MCP connection differently
        # We'll create a wrapper that handles the async connection when needed
        return _create_mcp_enabled_agent(
            model_id=model_id,
            user_id=user_id,
            session_id=session_id,
            debug_mode=debug_mode,
            mcp_sse_urls=mcp_sse_urls
        )
    else:
        # No MCP URLs, create standard agent
        return _create_standard_agent(
            model_id=model_id,
            user_id=user_id,
            session_id=session_id,
            debug_mode=debug_mode
        )


def _create_mcp_enabled_agent(
    model_id: str,
    user_id: Optional[str],
    session_id: Optional[str],
    debug_mode: bool,
    mcp_sse_urls: List[str]
) -> Agent:
    """
    Create an agent that can connect to MCP SSE servers.
    Uses a proxy toolkit that connects on-demand.
    """
    from agno.tools.toolkit import Toolkit
    
    class MCPSSEProxy(Toolkit):
        """Proxy toolkit for MCP SSE connections"""
        
        def __init__(self, sse_urls: List[str]):
            super().__init__(name="mcp_sse_proxy")
            self.sse_urls = sse_urls
            self._connections = {}
        
        async def connect_to_mcp(self, url: str):
            """Connect to an MCP SSE server"""
            if url not in self._connections:
                try:
                    # Create MCP server parameters for remote connection
                    server_params = StdioServerParameters(
                        command="npx",
                        args=["-y", "mcp-remote", url]
                    )
                    
                    # Create and store the connection
                    mcp_tools = MCPTools(server_params=server_params)
                    await mcp_tools.__aenter__()
                    self._connections[url] = mcp_tools
                    
                    if debug_mode:
                        print(f"Connected to MCP server: {url}")
                    
                    return mcp_tools
                except Exception as e:
                    print(f"Failed to connect to MCP server {url}: {e}")
                    return None
            
            return self._connections[url]
        
        async def list_mcp_tools(self) -> dict:
            """List all available tools from connected MCP servers"""
            all_tools = {}
            for url in self.sse_urls:
                mcp = await self.connect_to_mcp(url)
                if mcp:
                    # Get available tools from this MCP server
                    # This would depend on the MCP implementation
                    all_tools[url] = "Connected"
                else:
                    all_tools[url] = "Failed to connect"
            return all_tools
        
        async def call_mcp_tool(self, url: str, tool_name: str, **kwargs):
            """Call a tool on a specific MCP server"""
            mcp = await self.connect_to_mcp(url)
            if mcp:
                # Call the tool through MCP
                # Implementation depends on how MCP tools are exposed
                return {"status": "Tool called", "url": url, "tool": tool_name, "args": kwargs}
            else:
                return {"error": f"Not connected to {url}"}
    
    # Create tools list with MCP proxy
    tools = [
        DuckDuckGoTools(),
        MCPSSEProxy(mcp_sse_urls)
    ]
    
    # Create agent with MCP info
    mcp_info = f"Connected to {len(mcp_sse_urls)} MCP SSE server(s)"
    
    return _create_agent_instance(
        model_id=model_id,
        user_id=user_id,
        session_id=session_id,
        debug_mode=debug_mode,
        tools=tools,
        mcp_info=mcp_info,
        tool_descriptions=[
            "- DuckDuckGo web search",
            f"- MCP SSE tools ({len(mcp_sse_urls)} servers configured)"
        ]
    )


def _create_standard_agent(
    model_id: str,
    user_id: Optional[str],
    session_id: Optional[str],
    debug_mode: bool
) -> Agent:
    """Create a standard web search agent without MCP"""
    
    tools = [DuckDuckGoTools()]
    
    return _create_agent_instance(
        model_id=model_id,
        user_id=user_id,
        session_id=session_id,
        debug_mode=debug_mode,
        tools=tools,
        mcp_info="No MCP servers configured",
        tool_descriptions=["- DuckDuckGo web search"]
    )


def _create_agent_instance(
    model_id: str,
    user_id: Optional[str],
    session_id: Optional[str],
    debug_mode: bool,
    tools: List,
    mcp_info: str,
    tool_descriptions: List[str]
) -> Agent:
    """Create the actual agent instance with the provided configuration"""
    
    tools_list = "\n".join(tool_descriptions)
    
    return Agent(
        name="Web Search Agent",
        agent_id="web_search_agent",
        user_id=user_id,
        session_id=session_id,
        model=OpenAIChat(id=model_id),
        tools=tools,
        description=dedent(f"""\
            You are WebX, an advanced Web Search Agent designed to deliver accurate, context-rich information from the web.
            
            {mcp_info}
            
            Your responses should be clear, concise, and supported by citations from the web.
        """),
        instructions=dedent(f"""\
            As WebX, your goal is to provide users with accurate, context-rich information from the web. Follow these steps meticulously:

            Available Tools:
            {tools_list}
            
            When MCP tools are available, they may provide additional capabilities beyond web search. 
            Use the most appropriate tool for each task.

            1. Understand and Search:
            - Carefully analyze the user's query to identify 1-3 *precise* search terms.
            - Use the `duckduckgo_search` tool to gather relevant information. Prioritize reputable and recent sources.
            - If MCP tools are available, check if they can provide more specific or accurate information for the query.
            - Cross-reference information from multiple sources to ensure accuracy.
            - If initial searches are insufficient or yield conflicting information, refine your search terms or acknowledge the limitations/conflicts in your response.

            2. Leverage Memory & Context:
            - You have access to the last 3 messages. Use the `get_chat_history` tool if more conversational history is needed.
            - Integrate previous interactions and user preferences to maintain continuity.
            - Keep track of user preferences and prior clarifications.

            3. Construct Your Response:
            - **Start** with a direct and succinct answer that immediately addresses the user's core question.
            - **Then, if the query warrants it** (e.g., not for simple factual questions like "What is the weather in Tokyo?" or "What is the capital of France?"), **expand** your answer by:
                - Providing clear explanations, relevant context, and definitions.
                - Including supporting evidence such as statistics, real-world examples, and data points.
                - Addressing common misconceptions or providing alternative viewpoints if appropriate.
            - Structure your response for both quick understanding and deeper exploration.
            - Avoid speculation and hedging language (e.g., "it might be," "based on my limited knowledge").
            - **Citations are mandatory.** Support all factual claims with clear citations from your search results.

            4. Enhance Engagement:
            - After delivering your answer, propose relevant follow-up questions or related topics the user might find interesting to explore further.

            5. Final Quality & Presentation Review:
            - Before sending, critically review your response for clarity, accuracy, completeness, depth, and overall engagement.
            - Ensure your answer is well-organized, easy to read, and aligns with your role as an expert web search agent.

            6. Handle Uncertainties Gracefully:
            - If you cannot find definitive information, if data is inconclusive, or if sources significantly conflict, clearly state these limitations.
            - Encourage the user to ask further questions if they need more clarification or if you can assist in a different way.

            Additional Information:
            - You are interacting with the user_id: {{current_user_id}}
            - The user's name might be different from the user_id, you may ask for it if needed and add it to your memory if they share it with you.\
        """),
        add_state_in_messages=True,
        storage=PostgresAgentStorage(table_name="web_search_agent_sessions", db_url=db_url),
        add_history_to_messages=True,
        num_history_runs=3,
        read_chat_history=True,
        memory=Memory(
            model=OpenAIChat(id=model_id),
            db=PostgresMemoryDb(table_name="user_memories", db_url=db_url),
            delete_memories=True,
            clear_memories=True,
        ),
        enable_agentic_memory=True,
        markdown=True,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )
