from enum import Enum
from typing import List, Optional

from agents.agno_assist import get_agno_assist
from agents.client import run_agent
from agents.finance_agent import get_finance_agent
from agents.product_image_agent import get_product_image_agent
from agents.treezlambda_agent import get_treezlambda_agent
from agents.web_agent import get_web_agent


class AgentType(Enum):
    WEB_AGENT = "web_agent"
    AGNO_ASSIST = "agno_assist"
    FINANCE_AGENT = "finance_agent"
    CLIENT_AGENT = "client_agent"
    TREEZLAMBDA_AGENT = "treezlambda_agent"
    PRODUCT_IMAGE_AGENT = "product_image_agent"

def get_available_agents() -> List[str]:
    """Returns a list of all available agent IDs."""
    return [agent.value for agent in AgentType]


def get_agent(
    model_id: str = "gpt-4.1",
    agent_id: Optional[AgentType] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
):
    if agent_id == AgentType.WEB_AGENT:
        return get_web_agent(model_id=model_id, user_id=user_id, session_id=session_id, debug_mode=debug_mode)
    elif agent_id == AgentType.AGNO_ASSIST:
        return get_agno_assist(model_id=model_id, user_id=user_id, session_id=session_id, debug_mode=debug_mode)
    elif agent_id == AgentType.FINANCE_AGENT:
        return get_finance_agent(model_id=model_id, user_id=user_id, session_id=session_id, debug_mode=debug_mode)
    elif agent_id == AgentType.CLIENT_AGENT:
        return run_agent(model_id=model_id, user_id=user_id, session_id=session_id, debug_mode=debug_mode)
    elif agent_id == AgentType.TREEZLAMBDA_AGENT:
        return get_treezlambda_agent(model_id=model_id, user_id=user_id, session_id=session_id, debug_mode=debug_mode)
    elif agent_id == AgentType.PRODUCT_IMAGE_AGENT:
        return get_product_image_agent(model_id=model_id, user_id=user_id, session_id=session_id, debug_mode=debug_mode)

    raise ValueError(f"Agent: {agent_id} not found")
