from enum import Enum
from typing import List, Optional, Union
from agents.agno_assist import get_agno_assist
from agents.finance_agent import get_finance_agent
from agents.web_agent import get_web_agent

try:
    from agents.comprehensive_agent import get_comprehensive_agent_sync
    print("Import successful - comprehensive_agent loaded")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()

class AgentType(Enum):
    WEB_AGENT = "web_agent"
    AGNO_ASSIST = "agno_assist"
    FINANCE_AGENT = "finance_agent"
    DISCOUNT_AGENT = "comprehensive_agent"

def get_available_agents() -> List[str]:
    """Returns a list of all available agent IDs."""
    agents = [agent.value for agent in AgentType]
    print(f"Available agents: {agents}")
    return agents

def get_agent(
    model_id: str = "gpt-4o",
    agent_id: Optional[Union[AgentType, str]] = None,  # Accept both enum and string
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
):
    print(f"=== GET_AGENT CALLED ===")
    print(f"agent_id type: {type(agent_id)}")
    print(f"agent_id value: {agent_id}")
    print(f"model: {model_id}, user: {user_id}, session: {session_id}")
    
    # Handle string agent_id
    if isinstance(agent_id, str):
        print(f"Converting string '{agent_id}' to AgentType")
        # Try to find matching enum
        for agent_type in AgentType:
            if agent_type.value == agent_id:
                agent_id = agent_type
                print(f"Converted to: {agent_id}")
                break
        else:
            raise ValueError(f"Unknown agent_id string: {agent_id}")
    
    try:
        if agent_id == AgentType.WEB_AGENT:
            print("Creating web agent...")
            return get_web_agent(model_id=model_id, user_id=user_id, session_id=session_id, debug_mode=debug_mode)
        elif agent_id == AgentType.AGNO_ASSIST:
            print("Creating agno assist...")
            return get_agno_assist(model_id=model_id, user_id=user_id, session_id=session_id, debug_mode=debug_mode)
        elif agent_id == AgentType.FINANCE_AGENT:
            print("Creating finance agent...")
            return get_finance_agent(model_id=model_id, user_id=user_id, session_id=session_id, debug_mode=debug_mode)
        elif agent_id == AgentType.DISCOUNT_AGENT:
            print("Creating comprehensive/discount agent...")
            agent = get_comprehensive_agent_sync(
                model_id=model_id, 
                agent_id="comprehensive_agent",  # Use the string value directly
                user_id=user_id, 
                session_id=session_id, 
                debug_mode=debug_mode
            )
            print(f"Agent created successfully: {agent.agent_id}")
            return agent
        else:
            print(f"No matching agent type for: {agent_id}")
    except Exception as e:
        print(f"Error creating agent {agent_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
        
    raise ValueError(f"Agent: {agent_id} not found")
