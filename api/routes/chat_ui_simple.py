"""Simple Chat UI for Competitive Pricing Agent - Fallback Version"""

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
import json
import asyncio
from typing import Dict, Any
from datetime import datetime

from agno.models.openai import OpenAIChat
from agno.agent import Agent
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.storage.agent.postgres import PostgresAgentStorage

# Try to import the tools
try:
    from agents.competitive_pricing_agent import CompetitorPricingTools
    from db.session import db_url
    TOOLS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import tools: {e}")
    TOOLS_AVAILABLE = False
    db_url = None

# Create router
chat_router_simple = APIRouter(prefix="/chat-simple", tags=["Simple Chat UI"])

# Store active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)

manager = ConnectionManager()

# Create a simple agent without tools if tools aren't available
def create_simple_agent() -> Agent:
    """Create a simple agent that can still chat"""
    
    instructions = """You are a competitive pricing assistant for cannabis dispensaries.
    
    Note: Tool functionality is currently limited. I can help answer questions about:
    - How competitive pricing works
    - Best practices for price tracking
    - General cannabis industry pricing strategies
    - How to set up price monitoring
    
    I'll do my best to assist you with available capabilities."""
    
    # Create agent with or without tools
    agent_config = {
        "name": "competitive_pricing_simple",
        "agent_id": "competitive_pricing_simple",
        "model": OpenAIChat(id="gpt-4o"),
        "instructions": instructions,
        "markdown": True,
    }
    
    # Only add tools and storage if available
    if TOOLS_AVAILABLE and db_url:
        try:
            agent_config["tools"] = CompetitorPricingTools(db_url=db_url)
            agent_config["storage"] = PostgresAgentStorage(
                table_name="competitive_pricing_simple_agents",
                db_url=db_url
            )
            agent_config["memory"] = Memory(
                db=PostgresMemoryDb(
                    table_name="competitive_pricing_simple_memory",
                    db_url=db_url,
                )
            )
        except Exception as e:
            print(f"Warning: Could not initialize tools/storage: {e}")
    
    return Agent(**agent_config)

# Cache agent instance
_agent = None

def get_agent():
    global _agent
    if _agent is None:
        _agent = create_simple_agent()
    return _agent

# Simplified HTML
SIMPLE_CHAT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Competitive Pricing Assistant</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2E7D32;
        }
        #messages {
            height: 400px;
            overflow-y: auto;
            border: 1px solid #ddd;
            padding: 10px;
            margin: 20px 0;
            background: #fafafa;
        }
        .message {
            margin: 10px 0;
            padding: 10px;
            border-radius: 5px;
        }
        .user {
            background: #2E7D32;
            color: white;
            text-align: right;
        }
        .assistant {
            background: #e0e0e0;
        }
        .input-container {
            display: flex;
            gap: 10px;
        }
        #input {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        button {
            padding: 10px 20px;
            background: #2E7D32;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        button:disabled {
            opacity: 0.5;
        }
        .error {
            color: red;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>💰 Competitive Pricing Assistant</h1>
        <p>Chat interface for price tracking assistance</p>
        
        <div id="messages">
            <div class="message assistant">
                Welcome! I'm here to help with competitive pricing questions. How can I assist you today?
            </div>
        </div>
        
        <div class="input-container">
            <input type="text" id="input" placeholder="Type your message..." onkeypress="if(event.key==='Enter')send()">
            <button onclick="send()" id="sendBtn">Send</button>
        </div>
        
        <div id="error" class="error"></div>
    </div>

    <script>
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${protocol}//${window.location.host}/chat-simple/ws`);
        const messages = document.getElementById('messages');
        const input = document.getElementById('input');
        const sendBtn = document.getElementById('sendBtn');
        const error = document.getElementById('error');
        
        ws.onopen = () => {
            console.log('Connected');
            error.textContent = '';
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            addMessage(data.content, 'assistant');
            sendBtn.disabled = false;
        };
        
        ws.onerror = (e) => {
            console.error('WebSocket error:', e);
            error.textContent = 'Connection error. Please refresh the page.';
            sendBtn.disabled = false;
        };
        
        ws.onclose = () => {
            error.textContent = 'Connection closed. Please refresh the page.';
            sendBtn.disabled = false;
        };
        
        function send() {
            const text = input.value.trim();
            if (text && !sendBtn.disabled) {
                addMessage(text, 'user');
                ws.send(JSON.stringify({type: 'message', content: text}));
                input.value = '';
                sendBtn.disabled = true;
            }
        }
        
        function addMessage(text, sender) {
            const div = document.createElement('div');
            div.className = `message ${sender}`;
            div.textContent = text;
            messages.appendChild(div);
            messages.scrollTop = messages.scrollHeight;
        }
    </script>
</body>
</html>
"""

@chat_router_simple.get("/", response_class=HTMLResponse)
async def chat_interface():
    """Serve the simple chat interface"""
    return HTMLResponse(content=SIMPLE_CHAT_HTML)

@chat_router_simple.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "tools_available": TOOLS_AVAILABLE,
        "db_url_set": db_url is not None
    }

@chat_router_simple.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for chat"""
    client_id = f"client_{datetime.now().timestamp()}"
    await manager.connect(websocket, client_id)
    
    try:
        agent = get_agent()
        
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "message":
                message = data.get("content", "")
                
                try:
                    # Run agent
                    response = await agent.run(
                        message=message,
                        user_id=client_id,
                        session_id=client_id
                    )
                    
                    # Send response
                    await manager.send_message(
                        json.dumps({
                            "type": "response",
                            "content": response.content
                        }),
                        client_id
                    )
                except Exception as e:
                    # Send error message
                    await manager.send_message(
                        json.dumps({
                            "type": "response",
                            "content": f"Error: {str(e)}. The system may be initializing. Please try again."
                        }),
                        client_id
                    )
                    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(client_id)