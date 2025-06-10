from textwrap import dedent
from typing import Optional

from agno.agent import Agent
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.models.openai import OpenAIChat
from agno.storage.agent.postgres import PostgresAgentStorage
from agno.tools.toolkit import Toolkit

from db.session import db_url


class TreezLambdaTools(Toolkit):
    """Custom toolkit for interacting with Treez Lambda functions"""
    
    def __init__(self):
        super().__init__(name="treezlambda_tools")
        self.api_key = "qYzy78OgBb63vpLqh88kYauPZ0kHhNWz8ABUJcxh"
        self.base_url = "https://uzvlw67ks9.execute-api.us-west-2.amazonaws.com/dev"
        self.register(self.invoke_lambda)
        self.register(self.list_endpoints)
    
    def invoke_lambda(self, endpoint: str, payload: dict = None) -> str:
        """
        Invoke a Treez Lambda function endpoint.
        
        Args:
            endpoint: The specific endpoint path to invoke (e.g., "/process", "/analyze")
            payload: Optional JSON payload to send with the request
            
        Returns:
            The response from the Lambda function
        """
        import requests
        import json
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            if payload:
                response = requests.post(url, headers=headers, json=payload)
            else:
                response = requests.get(url, headers=headers)
            
            response.raise_for_status()
            return json.dumps(response.json(), indent=2)
        except requests.exceptions.RequestException as e:
            return f"Error invoking Lambda function: {str(e)}"
    
    def list_endpoints(self) -> str:
        """
        List available Treez Lambda endpoints.
        
        Returns:
            A list of available endpoints and their descriptions
        """
        # This is a placeholder - in a real implementation, this might
        # query an endpoint that returns available APIs
        return dedent("""
            Available Treez Lambda Endpoints:
            - /: Main endpoint
            - Additional endpoints may be available based on your API configuration
            
            Use invoke_lambda with the appropriate endpoint path to interact with specific functions.
        """)


def get_treezlambda_agent(
    model_id: str = "gpt-4.1",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    return Agent(
        name="Treez Lambda Agent",
        agent_id="treezlambda_agent",
        user_id=user_id,
        session_id=session_id,
        model=OpenAIChat(id=model_id),
        # Tools available to the agent
        tools=[TreezLambdaTools()],
        # Description of the agent
        description=dedent("""\
            You are the Treez Lambda Agent, specialized in interacting with Treez AWS Lambda functions.
            
            Your goal is to help users invoke and manage Treez Lambda functions through the API Gateway.
        """),
        # Instructions for the agent
        instructions=dedent("""\
            As the Treez Lambda Agent, you have access to AWS Lambda functions through the Treez API Gateway.
            
            Your capabilities include:
            1. **Listing Available Endpoints**: Use `list_endpoints` to show users what Lambda functions are available.
            2. **Invoking Lambda Functions**: Use `invoke_lambda` to call specific endpoints with appropriate payloads.
            
            When users ask to interact with Lambda functions:
            - First, understand what they want to accomplish
            - If they're unsure about available endpoints, list them
            - When invoking functions, ensure you use the correct endpoint path and payload format
            - Always handle responses gracefully and explain any errors clearly
            
            Security Notes:
            - The API key is already configured in your tools
            - All requests are authenticated automatically
            - Be mindful of the data being sent and received
            
            Response Guidelines:
            - Format Lambda responses clearly using markdown
            - Explain what the function did and what the response means
            - If there are errors, provide helpful suggestions for resolution
            
            Additional Information:
            - You are interacting with the user_id: {current_user_id}
            - The user's name might be different from the user_id, you may ask for it if needed and add it to your memory if they share it with you.\
        """),
        # This makes `current_user_id` available in the instructions
        add_state_in_messages=True,
        # -*- Storage -*-
        # Storage chat history and session state in a Postgres table
        storage=PostgresAgentStorage(table_name="treezlambda_agent_sessions", db_url=db_url),
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