"""Integrated Chat UI for Competitive Pricing Agent"""

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import json
import asyncio
from typing import Dict, Any
from datetime import datetime

from agno.models.openai import OpenAIChat
from agno.agent import Agent
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.storage.agent.postgres import PostgresAgentStorage

from agents.competitive_pricing_agent_enhanced import EnhancedCompetitorPricingTools
from db.session import db_url

# Create router
chat_router = APIRouter(prefix="/chat", tags=["Chat UI"])

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

# Create agent instance
def create_pricing_agent() -> Agent:
    """Create the enhanced competitive pricing agent"""
    
    tools = EnhancedCompetitorPricingTools(db_url=db_url)
    
    instructions = """You are a competitive pricing assistant for cannabis dispensaries.

    Key features:
    - Check prices across competitors with confidence scores (🟢 High >70%, 🟡 Medium 40-70%, 🔴 Low <40%)
    - Track products and manage competitors
    - Learn from user corrections to improve accuracy
    - Analyze pricing trends and scraping performance
    
    Always mention confidence levels and data freshness when reporting prices.
    Format responses with clear tables and actionable insights."""
    
    return Agent(
        name="competitive_pricing_chat",
        agent_id="competitive_pricing_chat", 
        model=OpenAIChat(id="gpt-4o"),
        tools=tools,
        storage=PostgresAgentStorage(
            table_name="competitive_pricing_chat_agents", 
            db_url=db_url
        ),
        memory=Memory(
            db=PostgresMemoryDb(
                table_name="competitive_pricing_chat_memory",
                db_url=db_url,
            )
        ),
        instructions=instructions,
        markdown=True,
    )

# Cache agent instance
_agent = None

def get_agent():
    global _agent
    if _agent is None:
        _agent = create_pricing_agent()
    return _agent

# HTML template for the chat interface
CHAT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Competitive Pricing Assistant</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f5f5f5;
            height: 100vh;
            display: flex;
        }
        
        .container {
            display: flex;
            width: 100%;
            height: 100%;
        }
        
        .sidebar {
            width: 250px;
            background-color: #2E7D32;
            color: white;
            padding: 20px;
            overflow-y: auto;
        }
        
        .sidebar h2 {
            margin-bottom: 20px;
            font-size: 20px;
        }
        
        .quick-actions {
            margin-bottom: 30px;
        }
        
        .action-button {
            display: block;
            width: 100%;
            padding: 10px 15px;
            margin-bottom: 10px;
            background-color: rgba(255, 255, 255, 0.1);
            border: none;
            border-radius: 5px;
            color: white;
            cursor: pointer;
            text-align: left;
            transition: background-color 0.3s;
        }
        
        .action-button:hover {
            background-color: rgba(255, 255, 255, 0.2);
        }
        
        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        
        .header {
            background-color: white;
            padding: 20px;
            border-bottom: 1px solid #e0e0e0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            color: #2E7D32;
            font-size: 24px;
        }
        
        .header p {
            color: #666;
            margin-top: 5px;
        }
        
        .chat-container {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            background-color: white;
            margin: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .message {
            margin-bottom: 20px;
            animation: fadeIn 0.3s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .message.user {
            text-align: right;
        }
        
        .message-content {
            display: inline-block;
            padding: 12px 16px;
            border-radius: 10px;
            max-width: 70%;
            text-align: left;
        }
        
        .message.user .message-content {
            background-color: #2E7D32;
            color: white;
        }
        
        .message.assistant .message-content {
            background-color: #f0f0f0;
            color: #333;
        }
        
        .message-content table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }
        
        .message-content th {
            background-color: #2E7D32;
            color: white;
            padding: 10px;
            text-align: left;
        }
        
        .message-content td {
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }
        
        .message-content tr:hover {
            background-color: #f5f5f5;
        }
        
        .input-container {
            padding: 20px;
            background-color: white;
            border-top: 1px solid #e0e0e0;
        }
        
        .input-wrapper {
            display: flex;
            gap: 10px;
        }
        
        #messageInput {
            flex: 1;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 25px;
            font-size: 16px;
            outline: none;
        }
        
        #messageInput:focus {
            border-color: #2E7D32;
        }
        
        #sendButton {
            padding: 12px 24px;
            background-color: #2E7D32;
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            transition: background-color 0.3s;
        }
        
        #sendButton:hover:not(:disabled) {
            background-color: #1B5E20;
        }
        
        #sendButton:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .typing-indicator {
            display: none;
            padding: 20px;
            color: #666;
        }
        
        .typing-indicator.active {
            display: block;
        }
        
        .confidence-high { color: #4CAF50; font-weight: bold; }
        .confidence-medium { color: #FF9800; font-weight: bold; }
        .confidence-low { color: #F44336; font-weight: bold; }
        
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #2E7D32;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <h2>💰 Quick Actions</h2>
            <div class="quick-actions">
                <button class="action-button" onclick="sendQuickAction('check prices for all tracked products')">
                    📊 Check All Prices
                </button>
                <button class="action-button" onclick="sendQuickAction('list all competitors with their status')">
                    🏪 View Competitors
                </button>
                <button class="action-button" onclick="sendQuickAction('show me the scraping confidence report')">
                    📈 Confidence Report
                </button>
                <button class="action-button" onclick="sendQuickAction('help me add a new product to track')">
                    ➕ Track New Product
                </button>
                <button class="action-button" onclick="sendQuickAction('analyze pricing trends for the last 7 days')">
                    📉 Price Trends
                </button>
                <button class="action-button" onclick="sendQuickAction('list all tracked products')">
                    📦 Tracked Products
                </button>
                <button class="action-button" onclick="sendQuickAction('analyze scraping performance')">
                    🔍 Performance Analysis
                </button>
            </div>
            
            <h2>📝 Examples</h2>
            <div style="font-size: 14px; opacity: 0.9;">
                <p style="margin-bottom: 10px;">• "Check prices for Wyld Gummies"</p>
                <p style="margin-bottom: 10px;">• "The price at Harborside should be $18"</p>
                <p style="margin-bottom: 10px;">• "Show confidence for Elemental Wellness"</p>
                <p style="margin-bottom: 10px;">• "Create batch job for all edibles"</p>
            </div>
        </div>
        
        <div class="main-content">
            <div class="header">
                <h1>Competitive Pricing Assistant</h1>
                <p>Track cannabis prices across dispensaries with confidence scoring</p>
            </div>
            
            <div class="chat-container" id="chatContainer">
                <div class="message assistant">
                    <div class="message-content">
                        <p>👋 Welcome to the Competitive Pricing Assistant!</p>
                        <p>I can help you:</p>
                        <ul>
                            <li>🔍 <strong>Check prices</strong> across all competitors</li>
                            <li>📊 <strong>Track products</strong> and monitor changes</li>
                            <li>🎯 <strong>Learn from corrections</strong> to improve accuracy</li>
                            <li>📈 <strong>Analyze trends</strong> and scraping performance</li>
                        </ul>
                        <p>All results include confidence scores (🟢 High, 🟡 Medium, 🔴 Low) to help you assess data reliability!</p>
                    </div>
                </div>
            </div>
            
            <div class="typing-indicator" id="typingIndicator">
                <div class="loading"></div> Assistant is typing...
            </div>
            
            <div class="input-container">
                <div class="input-wrapper">
                    <input 
                        type="text" 
                        id="messageInput" 
                        placeholder="Ask about prices, competitors, or products..."
                        onkeypress="handleKeyPress(event)"
                    >
                    <button id="sendButton" onclick="sendMessage()">Send</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        const ws = new WebSocket(`ws://${window.location.host}/chat/ws`);
        const chatContainer = document.getElementById('chatContainer');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const typingIndicator = document.getElementById('typingIndicator');
        
        ws.onopen = () => {
            console.log('Connected to chat server');
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'response') {
                addMessage(data.content, 'assistant');
                typingIndicator.classList.remove('active');
                sendButton.disabled = false;
            }
        };
        
        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            addMessage('Connection error. Please refresh the page.', 'assistant');
        };
        
        function handleKeyPress(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                sendMessage();
            }
        }
        
        function sendMessage() {
            const message = messageInput.value.trim();
            if (message && !sendButton.disabled) {
                addMessage(message, 'user');
                ws.send(JSON.stringify({
                    type: 'message',
                    content: message
                }));
                messageInput.value = '';
                sendButton.disabled = true;
                typingIndicator.classList.add('active');
            }
        }
        
        function sendQuickAction(action) {
            messageInput.value = action;
            sendMessage();
        }
        
        function addMessage(content, sender) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            
            // Parse markdown
            const htmlContent = marked.parse(content);
            contentDiv.innerHTML = htmlContent;
            
            // Apply confidence styling
            contentDiv.querySelectorAll('td, p').forEach(el => {
                if (el.textContent.includes('🟢')) {
                    el.classList.add('confidence-high');
                } else if (el.textContent.includes('🟡')) {
                    el.classList.add('confidence-medium');
                } else if (el.textContent.includes('🔴')) {
                    el.classList.add('confidence-low');
                }
            });
            
            messageDiv.appendChild(contentDiv);
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    </script>
</body>
</html>
"""

@chat_router.get("/", response_class=HTMLResponse)
async def chat_interface():
    """Serve the chat interface"""
    return HTMLResponse(content=CHAT_HTML)

@chat_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat"""
    client_id = f"client_{datetime.now().timestamp()}"
    await manager.connect(websocket, client_id)
    
    try:
        agent = get_agent()
        
        while True:
            # Receive message
            data = await websocket.receive_json()
            
            if data.get("type") == "message":
                message = data.get("content", "")
                
                # Run agent
                try:
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
                    await manager.send_message(
                        json.dumps({
                            "type": "response",
                            "content": f"❌ Error: {str(e)}"
                        }),
                        client_id
                    )
                    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(client_id)