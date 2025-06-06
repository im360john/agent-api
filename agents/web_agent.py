# agents/web_agent.py
import os
import sys
from textwrap import dedent
from typing import Optional, List
from datetime import datetime

from agno.agent import Agent
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.models.openai import OpenAIChat
from agno.storage.agent.postgres import PostgresAgentStorage
from agno.tools.duckduckgo import DuckDuckGoTools

from db.session import db_url

# Force debug output
def debug_print(msg):
    """Force print to stdout and stderr"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[WEB_AGENT DEBUG {timestamp}] {msg}"
    print(full_msg, file=sys.stdout, flush=True)
    print(full_msg, file=sys.stderr, flush=True)
    
    # Also try logger
    try:
        from logging import getLogger
        logger = getLogger(__name__)
        logger.debug(f"WEB_AGENT: {msg}")
    except:
        pass

# Log at module import time
debug_print("Module web_agent.py is being imported")

def get_web_agent(
    model_id: str = "gpt-4.1",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
    mcp_sse_urls: Optional[List[str]] = None,
) -> Agent:
    """
    Create a Web Search Agent with optional MCP SSE tool integration.
    """
    
    debug_print("get_web_agent() function called")
    debug_print(f"Stack trace: {' -> '.join([f.f_code.co_name for f in sys._getframe().f_back.__iter__()][:5])}")
    
    # Write to a file to ensure we're executing
    try:
        with open('/tmp/web_agent_debug.log', 'a') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"get_web_agent called at {datetime.now()}\n")
            f.write(f"Parameters: model_id={model_id}, user_id={user_id}, session_id={session_id}, debug_mode={debug_mode}, mcp_sse_urls={mcp_sse_urls}\n")
    except:
        pass
    
    # Print with logger
    from logging import getLogger
    logger = getLogger(__name__)
    logger.debug("**************** Agent ID: web_search_agent ****************")
    
    debug_print(f"Parameters: model_id={model_id}, user_id={user_id}, session_id={session_id}")
    
    # Check environment
    env_mcp = os.getenv("MCP_SSE_URLS", "NOT_SET")
    debug_print(f"Environment MCP_SSE_URLS: {env_mcp}")
    
    # Check if MCP SSE URLs are provided via parameter or environment
    if mcp_sse_urls is None:
        env_urls = os.getenv("MCP_SSE_URLS", "").strip()
        if env_urls:
            mcp_sse_urls = [url.strip() for url in env_urls.split(",") if url.strip()]
            debug_print(f"MCP URLs from environment: {mcp_sse_urls}")
    
    # Create base tools
    debug_print("Creating DuckDuckGoTools...")
    base_tools = [DuckDuckGoTools()]
    
    # MCP availability check
    mcp_available = False
    try:
        from agno.tools.mcp import MCPTools
        debug_print("MCPTools import successful")
        mcp_available = True
    except ImportError as e:
        debug_print(f"MCPTools import failed: {e}")
    
    # MCP info for description
    if mcp_sse_urls:
        debug_print(f"MCP URLs configured: {len(mcp_sse_urls)} servers")
        mcp_info = f"MCP servers configured: {len(mcp_sse_urls)}"
    else:
        debug_print("No MCP URLs configured")
        mcp_info = "No MCP servers configured"
    
    debug_print("Creating Agent instance...")
    
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
            - DuckDuckGo web search
            {f"- MCP tools: {mcp_sse_urls}" if mcp_sse_urls else ""}

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
    
    debug_print("Agent created successfully")
    
    # Final debug
    print("=" * 80, flush=True)
    print("WEB_AGENT INITIALIZATION COMPLETE", flush=True)
    print("=" * 80, flush=True)
    
    return agent
