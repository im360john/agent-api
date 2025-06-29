"""Test agent endpoint to debug issues"""

from fastapi import APIRouter
from agno.models.openai import OpenAIChat
from agno.agent import Agent
from agents.competitive_pricing_agent import CompetitorPricingTools
from db.session import db_url

test_router = APIRouter(prefix="/test", tags=["Test"])

@test_router.get("/agent")
async def test_agent():
    """Test agent creation and running"""
    try:
        # Create tools
        tools = CompetitorPricingTools(db_url=db_url)
        
        # Create agent
        agent = Agent(
            name="test_agent",
            agent_id="test_agent",
            model=OpenAIChat(id="gpt-4o"),
            tools=tools,
            instructions="You are a test agent.",
            markdown=True,
        )
        
        # Test running
        import asyncio
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: agent.run("list all competitors", user_id="test_user", session_id="test_session")
        )
        
        return {
            "status": "success",
            "agent_created": True,
            "response": response.content,
            "methods": [m for m in dir(agent) if 'run' in m and not m.startswith('_')]
        }
        
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }