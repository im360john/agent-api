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
    
    print("=" * 80)
    print("WEB_AGENT INITIALIZATION STARTING")
    print("=" * 80)
    print(f"Parameters received:")
    print(f"  - model_id: {model_id}")
    print(f"  - user_id: {user_id}")
    print(f"  - session_id: {session_id}")
    print(f"  - debug_mode: {debug_mode}")
    print(f"  - mcp_sse_urls: {mcp_sse_urls}")
    
    # Check if MCP SSE URLs are provided via parameter or environment
    if mcp_sse_urls is None:
        print("\nNo MCP URLs provided as parameter, checking environment...")
        # Check environment for MCP URLs
        env_urls = os.getenv("MCP_SSE_URLS", "").strip()
        print(f"Environment MCP_SSE_URLS: '{env_urls}'")
        
        if env_urls:
            mcp_sse_urls = [url.strip() for url in env_urls.split(",") if url.strip()]
            print(f"Parsed MCP URLs from environment: {mcp_sse_urls}")
        else:
            print("No MCP URLs found in environment")
    else:
        print(f"\nMCP URLs provided as parameter: {mcp_sse_urls}")
    
    # Create base tools
    print("\nCreating base tools...")
    duckduckgo_tools = DuckDuckGoTools()
    print(f"DuckDuckGoTools created: {duckduckgo_tools}")
    print(f"DuckDuckGoTools type: {type(duckduckgo_tools)}")
    print(f"DuckDuckGoTools attributes: {dir(duckduckgo_tools)}")
    
    base_tools = [duckduckgo_tools]
    print(f"Base tools list: {base_tools}")
    
    # Check for MCP import availability
    print("\nChecking MCP import availability...")
    try:
        from agno.tools.mcp import MCPTools
        print("✓ MCPTools imported successfully")
        
        try:
            from mcp import StdioServerParameters
            print("✓ StdioServerParameters imported successfully")
            mcp_available = True
        except ImportError as e:
            print(f"✗ Failed to import StdioServerParameters: {e}")
            mcp_available = False
    except ImportError as e:
        print(f"✗ Failed to import MCPTools: {e}")
        mcp_available = False
    
    # Handle MCP URLs if available
    mcp_info = "No MCP servers configured"
    if mcp_sse_urls and mcp_available:
        print(f"\nMCP URLs detected and MCP imports available")
        print(f"Would attempt to connect to: {mcp_sse_urls}")
        print("NOTE: Synchronous MCP connection not currently implemented")
        print("MCP tools require async context which conflicts with uvloop")
        mcp_info = f"MCP configured but not connected (requires async): {len(mcp_sse_urls)} server(s)"
    elif mcp_sse_urls and not mcp_available:
        print(f"\nMCP URLs detected but MCP imports not available")
        print("Cannot use MCP tools without proper imports")
        mcp_info = "MCP URLs provided but MCP libraries not available"
    else:
        print("\nNo MCP configuration detected")
    
    # Create the agent
    print("\nCreating Agent instance...")
    print(f"Tools being passed to Agent: {base_tools}")
    print(f"Number of tools: {len(base_tools)}")
    
    agent = Agent(
        name="Web Search Agent",
        agent_id="web_search_agent",
        user_id=user_id,
        session_id=session_id,
        model=OpenAIChat(id=model_id),
        # Tools available to the agent
        tools=base_tools,
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
            - DuckDuckGo web search (primary tool)
            {f"- MCP tools (not connected in sync mode)" if mcp_sse_urls else ""}

            1. Understand and Search:
            - Carefully analyze the user's query to identify 1-3 *precise* search terms.
            - Use the `duckduckgo_search` tool to gather relevant information. Prioritize reputable and recent sources.
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
    
    print(f"\nAgent created successfully")
    print(f"Agent ID: {agent.agent_id}")
    print(f"Agent name: {agent.name}")
    
    # Check what tools the agent actually has
    if hasattr(agent, 'tools'):
        print(f"\nAgent tools attribute: {agent.tools}")
        print(f"Number of tools in agent: {len(agent.tools) if agent.tools else 0}")
        if agent.tools:
            for i, tool in enumerate(agent.tools):
                print(f"  Tool {i}: {tool}")
                print(f"    Type: {type(tool)}")
                if hasattr(tool, 'name'):
                    print(f"    Name: {tool.name}")
                if hasattr(tool, '__dict__'):
                    print(f"    Attributes: {tool.__dict__}")
    else:
        print("\nAgent has no 'tools' attribute")
    
    # Check for other tool-related attributes
    print("\nChecking for other tool-related attributes on agent:")
    tool_attrs = [attr for attr in dir(agent) if 'tool' in attr.lower()]
    for attr in tool_attrs:
        try:
            value = getattr(agent, attr)
            print(f"  {attr}: {value}")
        except Exception as e:
            print(f"  {attr}: <error accessing: {e}>")
    
    print("\n" + "=" * 80)
    print("WEB_AGENT INITIALIZATION COMPLETE")
    print("=" * 80)
    
    return agent
