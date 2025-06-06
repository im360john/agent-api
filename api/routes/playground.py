# playground.py
from agno.playground import Playground
from agents.agno_assist import get_agno_assist
from agents.finance_agent import get_finance_agent
from agents.web_agent import get_web_agent
from agents.comprehensive_agent import get_comprehensive_agent_sync

######################################################
## Routes for the Playground Interface
######################################################

# Get Agents to serve in the playground
print("PLAYGROUND: About to create web_agent", flush=True)
web_agent = get_web_agent(debug_mode=True)
print(f"PLAYGROUND: web_agent created, type: {type(web_agent)}, id: {web_agent.agent_id if hasattr(web_agent, 'agent_id') else 'NO ID'}", flush=True)

agno_assist = get_agno_assist(debug_mode=True)
finance_agent = get_finance_agent(debug_mode=True)
comprehensive_agent = get_comprehensive_agent_sync(debug_mode=True)

# Create a playground instance with all agents including comprehensive
playground = Playground(agents=[web_agent, agno_assist, finance_agent, comprehensive_agent])
# In playground.py, modify the web_agent creation:
# Get the router for the playground
playground_router = playground.get_async_router()
