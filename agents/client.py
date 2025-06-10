import asyncio
from textwrap import dedent
from typing import Any, Optional

from agno.agent import Agent
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.models.openai import OpenAIChat
from agno.storage.agent.postgres import PostgresAgentStorage
from agno.tools.mcp import MCPTools
from agno.tools.toolkit import Toolkit

from db.session import db_url

# This is the URL of the MCP server we want to use.
server_url = "https://snowflake-mcp-backend.onrender.com/mcp/c9cda771-0dbf-4637-90ed-b9cf9c975098/sse"


class AsyncMCPToolsWrapper(Toolkit):
    """Wrapper for MCP tools that handles async initialization"""
    
    def __init__(self, transport: str = "sse", url: str = None):
        super().__init__(name="async_mcp_wrapper")
        self.transport = transport
        self.url = url
        self.mcp_tools = None
        self._initialized = False
        
        # Register a placeholder tool that will be replaced once MCP connects
        self.register(self._list_available_tools)
        
    async def _list_available_tools(self) -> str:
        """List all available MCP tools"""
        await self._ensure_initialized()
        if self.mcp_tools and hasattr(self.mcp_tools, 'functions'):
            tools = [f"- {func.__name__}: {func.__doc__ or 'No description'}" for func in self.mcp_tools.functions]
            return "Available MCP tools:\n" + "\n".join(tools) if tools else "No tools available from MCP server"
        return "MCP tools not initialized"
        
    async def _ensure_initialized(self):
        """Ensure MCP tools are initialized in async context"""
        if not self._initialized:
            try:
                # Initialize MCP tools with async context
                self.mcp_tools = MCPTools(transport=self.transport, url=self.url)
                await self.mcp_tools.__aenter__()
                self._initialized = True
                
                # Register all MCP tools dynamically
                if hasattr(self.mcp_tools, 'functions'):
                    for func in self.mcp_tools.functions:
                        # Create a wrapper for each MCP tool
                        async def tool_wrapper(**kwargs):
                            return await func(**kwargs) if asyncio.iscoroutinefunction(func) else func(**kwargs)
                        
                        # Set the wrapper's name and docstring
                        tool_wrapper.__name__ = func.__name__
                        tool_wrapper.__doc__ = func.__doc__
                        
                        # Register the tool
                        self.register(tool_wrapper)
                        
            except Exception as e:
                raise RuntimeError(f"Failed to initialize MCP tools: {str(e)}")
    
    async def __aenter__(self):
        """Support async context manager"""
        await self._ensure_initialized()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up MCP tools on exit"""
        if self.mcp_tools and self._initialized:
            await self.mcp_tools.__aexit__(exc_type, exc_val, exc_tb)
            self._initialized = False


def get_client_agent(
    model_id: str = "gpt-4.1",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    # Create our async wrapper for MCP tools
    mcp_wrapper = AsyncMCPToolsWrapper(transport="sse", url=server_url)
    
    return Agent(
        name="Client Agent",
        agent_id="client_agent",
        user_id=user_id,
        session_id=session_id,
        model=OpenAIChat(id=model_id),
        # Tools available to the agent
        tools=[mcp_wrapper],
        # Description of the agent
        description=dedent("""\
            You are a Client Agent with access to MCP (Model Context Protocol) tools via Snowflake.
            
            Your goal is to assist users by leveraging the capabilities provided by the MCP server.
        """),
        # Instructions for the agent
        instructions=dedent("""\
            As a Client Agent, you have access to MCP tools that provide specialized capabilities through the Snowflake MCP server.
            
            Start by using the `_list_available_tools` function to see what MCP tools are available from the server.
            The MCP tools will be dynamically loaded when you first interact with them.
            
            Use these tools effectively to help users with their requests. The MCP server may provide various functionalities
            depending on its configuration.
            
            When interacting with the MCP tools:
            - First list available tools to understand what's available
            - Be clear about what capabilities are available
            - Handle any errors gracefully
            - Provide helpful feedback about the operations performed
            - Note that MCP tools may take a moment to initialize on first use
            
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
