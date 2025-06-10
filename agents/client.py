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
        self._init_attempted = False
        
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
            # Log the query being executed
            if self._initialized:
                print(f"Debug: Executing query through MCP: {query[:100]}...")
            
            await self._ensure_initialized()
            
            # Try to find and use the read_query tool from MCP
            if self.mcp_tools and hasattr(self.mcp_tools, 'functions'):
                for func in self.mcp_tools.functions:
                    # Handle different types of function entries
                    if isinstance(func, str):
                        continue
                    elif hasattr(func, '__name__') and func.__name__ == 'read_query':
                        print(f"Debug: Found read_query function, executing...")
                        result = await func(query=query) if asyncio.iscoroutinefunction(func) else func(query=query)
                        
                        # Handle various response types
                        if result is None:
                            return "Query executed successfully but returned no results."
                        elif isinstance(result, (dict, list)):
                            return json.dumps(result, indent=2)
                        elif isinstance(result, str):
                            # Try to parse as JSON first
                            try:
                                parsed = json.loads(result)
                                return json.dumps(parsed, indent=2)
                            except:
                                return result
                        else:
                            return str(result)
            
            # If we get here, the tool wasn't found in MCP
            # Try to call it directly if it exists as an attribute
            if self.mcp_tools and hasattr(self.mcp_tools, 'read_query'):
                print(f"Debug: Calling read_query directly...")
                result = await self.mcp_tools.read_query(query=query)
                
                if result is None:
                    return "Query executed successfully but returned no results."
                elif isinstance(result, (dict, list)):
                    return json.dumps(result, indent=2)
                else:
                    return str(result)
            
            # If all else fails, try to send the query through any available method
            if self.mcp_tools:
                try:
                    # Try to use the tool invocation method if available
                    if hasattr(self.mcp_tools, 'invoke_tool'):
                        print("Debug: Trying invoke_tool method...")
                        result = await self.mcp_tools.invoke_tool('read_query', query=query)
                        return json.dumps(result, indent=2) if isinstance(result, (dict, list)) else str(result)
                    
                    # Try to call a generic execute method
                    if hasattr(self.mcp_tools, 'execute'):
                        print("Debug: Trying execute method...")
                        result = await self.mcp_tools.execute('read_query', query=query)
                        return json.dumps(result, indent=2) if isinstance(result, (dict, list)) else str(result)
                except Exception as e:
                    print(f"Debug: Alternative method failed: {e}")
            
            # Final fallback
            return """Error: Unable to execute query through MCP server.
            
The MCP connection appears to be having issues. Possible causes:
1. The MCP server is not responding
2. Authentication/authorization issues
3. The server URL may be incorrect or the service is down
4. The read_query tool is not available on this MCP server

Please verify:
- The MCP server URL is correct
- The server is running and accessible
- You have the necessary permissions to use the read_query tool"""
            
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON response from server - {str(e)}. The MCP server may be returning an empty or malformed response."
        except Exception as e:
            error_msg = str(e)
            if "EOF while parsing" in error_msg:
                return "Error: The MCP server returned an empty response. This could indicate a connection issue or server problem."
            elif "validation error" in error_msg:
                return f"Error: Server response validation failed - {error_msg}. The MCP server may not be responding correctly."
            else:
                return f"Error executing query: {error_msg}"
        
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
        if not self._initialized and not self._init_attempted:
            self._init_attempted = True
            try:
                print(f"Debug: Initializing MCP tools with URL: {self.url}")
                
                # Initialize MCP tools with async context
                self.mcp_tools = MCPTools(transport=self.transport, url=self.url)
                await self.mcp_tools.__aenter__()
                self._initialized = True
                
                print(f"Debug: MCP tools initialized successfully")
                
                # Check what tools are available
                if hasattr(self.mcp_tools, 'functions'):
                    print(f"Debug: Found {len(self.mcp_tools.functions)} functions from MCP")
                    for func in self.mcp_tools.functions:
                        # Check if func is actually a callable or just a string/dict
                        if isinstance(func, str):
                            print(f"Debug: - Function entry is a string: {func}")
                            continue
                        elif isinstance(func, dict):
                            print(f"Debug: - Function entry is a dict: {func}")
                            continue
                        elif hasattr(func, '__name__'):
                            print(f"Debug: - {func.__name__}: {getattr(func, '__doc__', 'No doc')}")
                            
                            if func.__name__ != 'read_query':  # Skip read_query as we already have it
                                # Create a wrapper for each MCP tool
                                async def make_wrapper(f):
                                    async def tool_wrapper(**kwargs):
                                        return await f(**kwargs) if asyncio.iscoroutinefunction(f) else f(**kwargs)
                                    return tool_wrapper
                                
                                wrapper = await make_wrapper(func)
                                wrapper.__name__ = func.__name__
                                wrapper.__doc__ = getattr(func, '__doc__', '')
                                
                                # Register the tool
                                self.register(wrapper)
                        else:
                            print(f"Debug: - Unknown function type: {type(func)} - {func}")
                else:
                    print("Debug: No 'functions' attribute found on mcp_tools")
                    
                # Try to inspect mcp_tools structure
                print(f"Debug: mcp_tools type: {type(self.mcp_tools)}")
                print(f"Debug: mcp_tools attributes: {[attr for attr in dir(self.mcp_tools) if not attr.startswith('_')]}")
                    
                # Also check for direct methods
                if hasattr(self.mcp_tools, 'read_query'):
                    print("Debug: Found read_query as direct method on mcp_tools")
                        
            except Exception as e:
                # Log the error but don't fail completely
                error_type = type(e).__name__
                print(f"Warning: Failed to initialize MCP tools ({error_type}): {str(e)}")
                
                # Check if it's the specific JSON error
                if "EOF while parsing" in str(e) or "validation error" in str(e):
                    print("Debug: This appears to be a server connection/response issue")
                    print("Debug: The MCP server may not be responding or may be returning empty responses")
                
                # Continue with limited functionality
                self._initialized = False  # Mark as not initialized to retry later
    
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
