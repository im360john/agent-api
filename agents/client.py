from textwrap import dedent
from typing import Optional

from agno.agent import Agent
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.models.openai import OpenAIChat
from agno.storage.agent.postgres import PostgresAgentStorage
from agno.tools.mcp import MCPTools

from db.session import db_url

# This is the URL of the MCP server we want to use.
server_url = "https://snowflake-mcp-backend.onrender.com/mcp/c9cda771-0dbf-4637-90ed-b9cf9c975098/sse"


def get_client_agent(
    model_id: str = "gpt-4.1",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    # Note: MCPTools requires async context when actually used, but we can create the agent synchronously
    # The async context will be handled when the agent's arun method is called
    mcp_tools = MCPTools(transport="sse", url=server_url)
    
    return Agent(
        name="Client Agent",
        agent_id="client_agent",
        user_id=user_id,
        session_id=session_id,
        model=OpenAIChat(id=model_id),
        # Tools available to the agent
        tools=[mcp_tools],
        # Description of the agent
        description=dedent("""\
            You are a Client Agent with access to MCP (Model Context Protocol) tools via Snowflake.
            
            Your goal is to assist users by leveraging the capabilities provided by the MCP server.
        """),
        # Instructions for the agent
        instructions=dedent("""\
            As a Client Agent, you have access to MCP tools that provide specialized capabilities through the Snowflake MCP server.
            
            Use these tools effectively to help users with their requests. The MCP server may provide various functionalities
            depending on its configuration.
            
            When interacting with the MCP tools:
            - Be clear about what capabilities are available
            - Handle any errors gracefully
            - Provide helpful feedback about the operations performed
            
            Additional Information:
            - You are interacting with the user_id: {current_user_id}
            - The user's name might be different from the user_id, you may ask for it if needed and add it to your memory if they share it with you.\
        """),
        # This makes `current_user_id` available in the instructions
        add_state_in_messages=True,
        # -*- Storage -*-
        # Storage chat history and session state in a Postgres table
        storage=PostgresAgentStorage(table_name="client_agent_sessions", db_url=db_url),
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


# For backward compatibility, keep the run_agent function
# This is what's being called in selector.py
def run_agent(
    model_id: str = "gpt-4.1",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    """Alias for get_client_agent to maintain compatibility with existing code"""
    return get_client_agent(
        model_id=model_id,
        user_id=user_id,
        session_id=session_id,
        debug_mode=debug_mode
    )
