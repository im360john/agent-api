# tools/snowflake_mcp_tool.py

import os
import httpx
import json
from agno.tools import tool

# By using the @tool decorator, we convert this async function
# into a proper Tool that the agent can use, without needing to define a class.
@tool
async def query_snowflake_mcp(query: str) -> str:
    """
    Connects to the Snowflake MCP server to ask questions or send queries.
    The server will stream back a response. Use this for any data-related questions.
    """
    # Get the SSE URL from environment variables for security and flexibility.
    sse_url = os.getenv("SNOWFLAKE_SSE_URL")
    if not sse_url:
        return "Error: SNOWFLAKE_SSE_URL environment variable not set."

    aggregated_response = ""
    
    try:
        # httpx is used for making async HTTP requests.
        # We use a POST request to send our query in the body.
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", sse_url, json={"query": query}, timeout=120) as response:
                # Check for successful connection
                if response.status_code != 200:
                    return f"Error: Failed to connect to Snowflake MCP. Status: {response.status_code}"

                # Process the SSE stream
                async for line in response.aiter_lines():
                    # SSE messages start with "data: "
                    if line.startswith("data:"):
                        try:
                            # Remove "data: " prefix and parse the JSON content
                            content = line[5:].strip()
                            data = json.loads(content)
                            # Extract the actual message from the JSON payload
                            if "data" in data:
                                aggregated_response += data["data"]
                            elif "error" in data:
                                return f"Error from MCP server: {data['error']}"
                        except json.JSONDecodeError:
                            # Handle cases where the data is not valid JSON
                            print(f"Warning: Could not decode JSON from line: {line}")
                            continue
    except httpx.RequestError as e:
        return f"Error: Could not connect to the Snowflake MCP server at {sse_url}. Details: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

    return aggregated_response if aggregated_response else "Received an empty response from the server."
```

Now that the tool is defined correctly, we need to update the agent that uses it. The agent file needs to import this new function and add it to its `tools` list directly. I will provide the updated `snowflake_agent.py` in the next st
