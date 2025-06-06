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
    
    # Base tools - always include DuckDuckGo
    base_tools = [DuckDuckGoTools()]
    
    # Check if MCP SSE URLs are provided via parameter or environment
    if mcp_sse_urls is None:
        # Check environment for MCP URLs
        env_urls = os.getenv("MCP_SSE_URLS", "").strip()
        if env_urls:
            mcp_sse_urls = [url.strip() for url in env_urls.split(",") if url.strip()]
    
    # For now, we'll create the agent without MCP tools in the synchronous context
    # MCP tools require async context which is incompatible with the current setup
    # We'll log a warning if MCP URLs are provided
    if mcp_sse_urls:
        print(f"Warning: MCP SSE URLs provided but async MCP tools are not supported in synchronous context")
        print(f"MCP URLs: {mcp_sse_urls}")
        print("To use MCP tools, the agent needs to be created in an async context")
        mcp_info = f"MCP servers configured but not connected (requires async context): {len(mcp_sse_urls)} server(s)"
    else:
        mcp_info = "No MCP servers configured"
    
    # Create agent with base tools only
    return create_agent_instance(
        model_id=model_id,
        user_id=user_id,
        session_id=session_id,
        debug_mode=debug_mode,
        tools=base_tools,
        mcp_info=mcp_info
    )


def create_agent_instance(
    model_id: str,
    user_id: Optional[str],
    session_id: Optional[str],
    debug_mode: bool,
    tools: List,
    mcp_info: str = ""
) -> Agent:
    """
    Create the actual agent instance with the provided tools.
    
    This is separated out to be reused whether or not MCP tools are included.
    """
    
    # Build tool list description for instructions
    tool_descriptions = []
    for tool in tools:
        if hasattr(tool, 'name'):
            tool_descriptions.append(f"- {tool.name}")
        elif hasattr(tool, '__class__'):
            tool_descriptions.append(f"- {tool.__class__.__name__}")
    
    tools_list = "\n".join(tool_descriptions) if tool_descriptions else "- DuckDuckGoTools (web search)"
    
    return Agent(
        name="Web Search Agent",
        agent_id="web_search_agent",
        user_id=user_id,
        session_id=session_id,
        model=OpenAIChat(id=model_id),
        # Tools available to the agent
        tools=tools,
        # Description of the agent
        description=dedent(f"""\
            You are WebX, an advanced Web Search Agent designed to deliver accurate, context-rich information from the web.
            
            {mcp_info}
            
            Your responses should be clear, concise, and supported by citations from the web.
        """),
        # Instructions for the agent
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
        # This makes `current_user_id` available in the instructions
        add_state_in_messages=True,
        # -*- Storage -*-
        # Storage chat history and session state in a Postgres table
        storage=PostgresAgentStorage(table_name="web_search_agent_sessions", db_url=db_url),
        # -*- History -*-
        # Send the last 3 messages from the chat history
        add_history_to_messages=True,
        num_history_runs=3,
        # Add a tool to read the chat history if needed
        read_chat_history=True,
        # -*- Memory -*-
        # Enable agentic memory where the Agent can personalize responses to the user
        memory=Memory(
            model=OpenAIChat(id=model_id),
            db=PostgresMemoryDb(table_name="user_memories", db_url=db_url),
            delete_memories=True,
            clear_memories=True,
        ),
        enable_agentic_memory=True,
        # -*- Other settings -*-
        # Format responses using markdown
        markdown=True,
        # Add the current date and time to the instructions
        add_datetime_to_instructions=True,
        # Show debug logs
        debug_mode=debug_mode,
    )


# Alternative: Create an async version for use with MCP
async def get_web_agent_async(
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
