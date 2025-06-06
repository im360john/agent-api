# agents/web_agent.py
import os
from textwrap import dedent
from typing import Optional, List

from agno.agent import Agent
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.models.openai import OpenAIChat
from agno.storage.agent.postgres import PostgresAgentStorage
from agno.tools.duckduckgo import DuckDuckGoTools

from db.session import db_url



# Alternative: Create an async version for use with MCP
async def get_web_agent(
    model_id: str = "gpt-4.1",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
    mcp_sse_urls: Optional[List[str]] = None,
) -> Agent:
    """
    Async version of get_web_agent that can properly handle MCP SSE connections.
    
    This should be used in async contexts where MCP tools are needed.
    """
    from agno.tools.mcp import MCPTools
    from contextlib import AsyncExitStack
    
    # Base tools
    all_tools = [DuckDuckGoTools()]
    
    # Check for MCP URLs
    if mcp_sse_urls is None:
        env_urls = os.getenv("MCP_SSE_URLS", "").strip()
        if env_urls:
            mcp_sse_urls = [url.strip() for url in env_urls.split(",") if url.strip()]
    
    mcp_info = "No MCP servers configured"
    
    # Connect to MCP servers if URLs provided
    if mcp_sse_urls:
        connected_count = 0
        async with AsyncExitStack() as stack:
            for url in mcp_sse_urls:
                try:
                    mcp_tool = await stack.enter_async_context(MCPTools(url=url))
                    all_tools.append(mcp_tool)
                    connected_count += 1
                    if debug_mode:
                        print(f"Successfully connected to MCP server: {url}")
                except Exception as e:
                    print(f"Warning: Failed to connect to MCP server {url}: {e}")
            
            mcp_info = f"Connected to {connected_count}/{len(mcp_sse_urls)} MCP server(s)"
    
    # Create and return the agent
    return create_agent_instance(
        model_id=model_id,
        user_id=user_id,
        session_id=session_id,
        debug_mode=debug_mode,
        tools=all_tools,
        mcp_info=mcp_info
    )
