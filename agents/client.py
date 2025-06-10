import asyncio
from textwrap import dedent
from typing import Any, Optional, Dict
import json

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


class SnowflakeMCPWrapper(Toolkit):
    """Wrapper for Snowflake MCP tools with focus on SQL query capabilities"""
    
    def __init__(self, transport: str = "sse", url: str = None):
        super().__init__(name="snowflake_mcp_wrapper")
        self.transport = transport
        self.url = url
        self.mcp_tools = None
        self._initialized = False
        
        # Register the primary Snowflake query tool
        self.register(self.read_query)
        self.register(self.list_available_tools)
        
    async def read_query(self, query: str) -> str:
        """
        Execute a SQL query on Snowflake database.
        
        Args:
            query: SQL query to execute (e.g., "SELECT * FROM customers LIMIT 10")
            
        Returns:
            Query results in JSON format
        """
        try:
            await self._ensure_initialized()
            
            # Try to find and use the read_query tool from MCP
            if self.mcp_tools and hasattr(self.mcp_tools, 'functions'):
                for func in self.mcp_tools.functions:
                    if func.__name__ == 'read_query':
                        result = await func(query=query) if asyncio.iscoroutinefunction(func) else func(query=query)
                        return json.dumps(result, indent=2) if isinstance(result, (dict, list)) else str(result)
            
            # Fallback if tool not found
            return "Error: read_query tool not available from MCP server. Please check the connection."
            
        except Exception as e:
            return f"Error executing query: {str(e)}"
        
    async def list_available_tools(self) -> str:
        """List all available MCP tools, focusing on Snowflake capabilities"""
        try:
            await self._ensure_initialized()
            
            if self.mcp_tools and hasattr(self.mcp_tools, 'functions'):
                tools_info = []
                for func in self.mcp_tools.functions:
                    name = func.__name__
                    doc = func.__doc__ or 'No description available'
                    tools_info.append(f"- **{name}**: {doc}")
                
                if tools_info:
                    return "Available Snowflake MCP tools:\n\n" + "\n".join(tools_info)
                else:
                    return "No tools available from MCP server"
            
            return "MCP tools not initialized. The primary tool available is:\n- **read_query**: Execute SQL queries on Snowflake database"
            
        except Exception as e:
            return f"Note: MCP connection issue ({str(e)}). The primary tool available is:\n- **read_query**: Execute SQL queries on Snowflake database"
        
    async def _ensure_initialized(self):
        """Ensure MCP tools are initialized in async context"""
        if not self._initialized:
            try:
                # Initialize MCP tools with async context
                self.mcp_tools = MCPTools(transport=self.transport, url=self.url)
                await self.mcp_tools.__aenter__()
                self._initialized = True
                
                # Register all MCP tools dynamically, but ensure read_query is available
                if hasattr(self.mcp_tools, 'functions'):
                    for func in self.mcp_tools.functions:
                        if func.__name__ != 'read_query':  # Skip read_query as we already have it
                            # Create a wrapper for each MCP tool
                            async def make_wrapper(f):
                                async def tool_wrapper(**kwargs):
                                    return await f(**kwargs) if asyncio.iscoroutinefunction(f) else f(**kwargs)
                                return tool_wrapper
                            
                            wrapper = await make_wrapper(func)
                            wrapper.__name__ = func.__name__
                            wrapper.__doc__ = func.__doc__
                            
                            # Register the tool
                            self.register(wrapper)
                        
            except Exception as e:
                # Log the error but don't fail completely
                print(f"Warning: Failed to fully initialize MCP tools: {str(e)}")
                # Continue with limited functionality
    
    async def __aenter__(self):
        """Support async context manager"""
        await self._ensure_initialized()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up MCP tools on exit"""
        if self.mcp_tools and self._initialized:
            try:
                await self.mcp_tools.__aexit__(exc_type, exc_val, exc_tb)
            except:
                pass  # Ignore cleanup errors
            self._initialized = False


def get_client_agent(
    model_id: str = "gpt-4.1",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    # Create our Snowflake MCP wrapper
    snowflake_wrapper = SnowflakeMCPWrapper(transport="sse", url=server_url)
    
    return Agent(
        name="Snowflake SQL Agent",
        agent_id="client_agent",
        user_id=user_id,
        session_id=session_id,
        model=OpenAIChat(id=model_id),
        # Tools available to the agent
        tools=[snowflake_wrapper],
        # Description of the agent
        description=dedent("""\
            You are a Snowflake SQL Agent with direct access to query Snowflake databases.
            
            Your primary capability is executing SQL queries against Snowflake data warehouses to help users analyze data,
            generate reports, and answer data-related questions.
        """),
        # Instructions for the agent
        instructions=dedent("""\
            As a Snowflake SQL Agent, you have access to execute SQL queries on Snowflake databases through the MCP server.
            
            Your primary tool is `read_query` which allows you to run SQL queries and retrieve results.
            
            When helping users:
            1. **Understanding Requirements**: First understand what data the user needs
            2. **Query Construction**: Write efficient SQL queries to retrieve the requested data
            3. **Data Analysis**: Help interpret the results and provide insights
            
            Best practices for SQL queries:
            - Always use LIMIT clauses for initial data exploration
            - Write clear, well-formatted SQL with proper indentation
            - Use appropriate JOINs when combining data from multiple tables
            - Consider query performance and avoid full table scans when possible
            - Explain what your queries do before executing them
            
            Example queries you can help with:
            - SELECT statements to retrieve data
            - Aggregations with GROUP BY
            - JOIN operations between tables
            - Window functions for advanced analytics
            - CTEs (Common Table Expressions) for complex queries
            
            When errors occur:
            - Check SQL syntax carefully
            - Verify table and column names
            - Consider data types and casting if needed
            - Provide helpful error explanations to users
            
            You can also use `list_available_tools` to see all available MCP tools, though `read_query` is your primary function.
            
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
