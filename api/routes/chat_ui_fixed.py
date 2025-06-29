"""Fixed Chat UI for Competitive Pricing Agent"""

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

# Import the basic tools
from agents.competitive_pricing_agent import CompetitorPricingTools
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
    """Create the competitive pricing agent"""
    
    tools = CompetitorPricingTools(db_url=db_url)
    
    instructions = """You are a competitive pricing assistant for cannabis dispensaries.

    IMPORTANT: When users ask for prices:
    1. First use check_prices to search for the product
    2. If multiple matches are found, the system will show them - ask the user to confirm which one
    3. If no matches found and product needs to be tracked:
       - Show the user what product will be tracked (with exact name and brand)
       - Use track_product only after getting confirmation or being specific
    4. Always show URLs scraped along with prices in your response
    
    Product Search Tips:
    - The system uses fuzzy matching - partial names work (e.g., "sour apple" finds "Sour Apple Sativa Gummies")
    - Brand names are automatically detected from searches
    - If uncertain, show available options for user confirmation
    
    Key features:
    - Check prices across competitors with smart product matching
    - Track products and manage competitors
    - Analyze pricing trends and history
    - Provide batch processing capabilities
    
    Format responses with clear tables and actionable insights."""
    
    return Agent(
        name="competitive_pricing_chat",
        agent_id="competitive_pricing_chat", 
        model=OpenAIChat(id="gpt-4o"),
        tools=[tools],
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
        
        .message-content ul {
            margin: 10px 0;
            padding-left: 20px;
            list-style-position: inside;
        }
        
        .message-content li {
            margin: 5px 0;
            text-indent: -20px;
            padding-left: 20px;
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
        
        .error-message {
            background-color: #ffebee;
            color: #c62828;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <h2>Quick Actions</h2>
            <div class="quick-actions">
                <button class="action-button" onclick="sendQuickAction('check prices for all tracked products')">
                    Check All Prices
                </button>
                <button class="action-button" onclick="sendQuickAction('list all competitors')">
                    View Competitors
                </button>
                <button class="action-button" onclick="sendQuickAction('list all tracked products')">
                    Tracked Products
                </button>
                <button class="action-button" onclick="sendQuickAction('help me add a new product to track')">
                    Track New Product
                </button>
                <button class="action-button" onclick="sendQuickAction('analyze pricing trends for the last 7 days')">
                    Price Trends
                </button>
                <button class="action-button" onclick="sendQuickAction('get price history for Wyld products')">
                    Price History
                </button>
                <button class="action-button" onclick="sendQuickAction('create a batch job to check all prices')">
                    Batch Check
                </button>
            </div>
            
            <h2>Examples</h2>
            <div style="font-size: 14px; opacity: 0.9;">
                <p style="margin-bottom: 10px;">• "Check prices for Wyld Gummies"</p>
                <p style="margin-bottom: 10px;">• "Add competitor: Example Dispensary"</p>
                <p style="margin-bottom: 10px;">• "Track product: Blue Dream"</p>
                <p style="margin-bottom: 10px;">• "Show batch job status"</p>
            </div>
        </div>
        
        <div class="main-content">
            <div class="header">
                <h1>Competitive Pricing Assistant</h1>
                <p>Track cannabis prices across dispensaries</p>
            </div>
            
            <div class="chat-container" id="chatContainer">
                <div class="message assistant">
                    <div class="message-content">
                        <p>Welcome to the Competitive Pricing Assistant!</p>
                        <p>I can help you:</p>
                        <ul>
                            <li><strong>Check prices</strong> across all competitors</li>
                            <li><strong>Track products</strong> and monitor changes</li>
                            <li><strong>Analyze trends</strong> and price history</li>
                            <li><strong>Create batch jobs</strong> for bulk price checking</li>
                        </ul>
                        <p style="margin-top: 10px;"><strong>How to use:</strong></p>
                        <p>Just ask for prices! I'll automatically track new products and fetch current prices. For example:</p>
                        <ul>
                            <li>"Get prices for Wyld Sour Apple Sativa"</li>
                            <li>"Check prices for all Kiva products"</li>
                            <li>"Show me Camino gummies prices at Harborside"</li>
                        </ul>
                        <p style="margin-top: 10px;">Try the quick actions on the left or type your own query!</p>
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
        // Use wss:// for HTTPS, ws:// for HTTP
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${protocol}//${window.location.host}/chat/ws`);
        const chatContainer = document.getElementById('chatContainer');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const typingIndicator = document.getElementById('typingIndicator');
        
        let isConnected = false;
        
        ws.onopen = () => {
            console.log('Connected to chat server');
            isConnected = true;
        };
        
        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'response') {
                    addMessage(data.content, 'assistant');
                    typingIndicator.classList.remove('active');
                    sendButton.disabled = false;
                }
            } catch (e) {
                console.error('Error parsing message:', e);
                addMessage('Error processing response', 'assistant');
            }
        };
        
        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            addMessage('Connection error. Please refresh the page.', 'assistant');
            sendButton.disabled = false;
            typingIndicator.classList.remove('active');
            isConnected = false;
        };
        
        ws.onclose = (event) => {
            console.log('WebSocket closed:', event);
            if (event.code !== 1000) {
                addMessage('Connection lost. Please refresh the page to reconnect.', 'assistant');
            }
            sendButton.disabled = false;
            typingIndicator.classList.remove('active');
            isConnected = false;
        };
        
        function handleKeyPress(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                sendMessage();
            }
        }
        
        function sendMessage() {
            const message = messageInput.value.trim();
            if (message && !sendButton.disabled && isConnected) {
                addMessage(message, 'user');
                ws.send(JSON.stringify({
                    type: 'message',
                    content: message
                }));
                messageInput.value = '';
                sendButton.disabled = true;
                typingIndicator.classList.add('active');
            } else if (!isConnected) {
                addMessage('Not connected. Please refresh the page.', 'assistant');
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
            
            // Parse markdown if assistant message
            if (sender === 'assistant') {
                try {
                    const htmlContent = marked.parse(content);
                    contentDiv.innerHTML = htmlContent;
                } catch (e) {
                    contentDiv.textContent = content;
                }
            } else {
                contentDiv.textContent = content;
            }
            
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

@chat_router.get("/health")
async def health_check():
    """Health check endpoint for debugging"""
    try:
        agent = get_agent()
        return {
            "status": "healthy",
            "agent": "initialized" if agent else "not initialized",
            "websocket_path": "/chat/ws"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "websocket_path": "/chat/ws"
        }

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
                
                # Run agent with proper error handling
                try:
                    # Use async run method since our tools are async
                    response = await agent.arun(
                        message,
                        user_id=client_id,
                        session_id=client_id
                    )
                    
                    # Send response
                    await manager.send_message(
                        json.dumps({
                            "type": "response",
                            "content": response.content if hasattr(response, 'content') else str(response)
                        }),
                        client_id
                    )
                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    print(f"Error in agent.run_sync: {error_details}")
                    
                    await manager.send_message(
                        json.dumps({
                            "type": "response",
                            "content": f"Error: {str(e)}\n\nPlease try rephrasing your request."
                        }),
                        client_id
                    )
                    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(client_id)