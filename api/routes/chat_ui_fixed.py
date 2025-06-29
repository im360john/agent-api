"""Fixed Chat UI for Competitive Pricing Agent"""

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
import json
import asyncio
from typing import Dict, Any
from datetime import datetime

from agno.models.openai import OpenAIChat
from agno.models.anthropic import AnthropicChat
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
def create_pricing_agent(model_id: str = "claude-sonnet-4-20250514") -> Agent:
    """Create the competitive pricing agent with specified model"""
    
    tools = CompetitorPricingTools(db_url=db_url)
    
    # Select model based on model_id
    if model_id.startswith("claude"):
        model = AnthropicChat(id=model_id)
    else:
        model = OpenAIChat(id=model_id)
    
    instructions = """You are a competitive pricing assistant for cannabis dispensaries.

    IMPORTANT WORKFLOWS:
    
    1. When users ask to track a product:
       - Extract brand and product name from their request
       - Show them what will be tracked: "Product: [name], Brand: [brand]"
       - When they confirm with "yes", "proceed", "ok", etc., immediately call track_product(name, brand)
       - After tracking, optionally check prices for the newly tracked product
    
    2. When users ask for prices:
       - First use check_prices to search for the product
       - If not found, offer to track it first (follow workflow #1)
       - Always show URLs scraped along with prices
    
    3. When checking all tracked products:
       - First call list_products() to get the list
       - Then use check_prices for each product individually
       - Do NOT use bulk_price_check without a products list
    
    Product Search Tips:
    - The system uses fuzzy matching - partial names work
    - Brand names are automatically detected from searches
    - If uncertain, show available options for user confirmation
    
    Key features:
    - Check prices across competitors with smart product matching
    - Track products and manage competitors
    - Analyze pricing trends and history
    - Create batch jobs for large-scale price checking
    
    Format responses with clear tables and actionable insights."""
    
    return Agent(
        name="competitive_pricing_chat",
        agent_id="competitive_pricing_chat", 
        model=model,
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

def get_agent(model_id: str = "claude-sonnet-4-20250514"):
    # For now, create a new agent for each model to avoid conflicts
    # In production, you might want to cache agents per model
    return create_pricing_agent(model_id)

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
        
        .sessions-panel {
            width: 300px;
            background-color: #f8f8f8;
            border-right: 1px solid #e0e0e0;
            display: flex;
            flex-direction: column;
            transition: margin-left 0.3s ease;
        }
        
        .sessions-panel.collapsed {
            margin-left: -300px;
        }
        
        .sessions-header {
            padding: 20px;
            background-color: white;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .sessions-list {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
        }
        
        .session-item {
            background-color: white;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .session-item:hover {
            background-color: #f5f5f5;
            border-color: #2E7D32;
        }
        
        .session-item.active {
            background-color: #E8F5E9;
            border-color: #2E7D32;
        }
        
        .session-time {
            font-size: 12px;
            color: #666;
            margin-bottom: 4px;
        }
        
        .session-preview {
            font-size: 14px;
            color: #333;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .session-actions {
            display: flex;
            gap: 10px;
            margin-top: 8px;
        }
        
        .new-session-btn {
            background-color: #2E7D32;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }
        
        .new-session-btn:hover {
            background-color: #1B5E20;
        }
        
        .delete-session-btn {
            background-color: transparent;
            color: #d32f2f;
            border: none;
            padding: 4px 8px;
            cursor: pointer;
            font-size: 12px;
        }
        
        .toggle-sessions-btn {
            position: absolute;
            left: 0;
            top: 50%;
            transform: translateY(-50%);
            background-color: #2E7D32;
            color: white;
            border: none;
            padding: 10px 5px;
            cursor: pointer;
            border-radius: 0 5px 5px 0;
            z-index: 10;
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
        <button class="toggle-sessions-btn" onclick="toggleSessions()">☰</button>
        
        <div class="sessions-panel" id="sessionsPanel">
            <div class="sessions-header">
                <h3>Chat History</h3>
                <button class="new-session-btn" onclick="createNewSession()">New Chat</button>
            </div>
            <div class="sessions-list" id="sessionsList">
                <!-- Sessions will be loaded here -->
            </div>
        </div>
        
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
                <div style="margin-top: 15px;">
                    <label for="modelSelect" style="margin-right: 10px; color: #666;">AI Model:</label>
                    <select id="modelSelect" style="padding: 8px 12px; border: 1px solid #ddd; border-radius: 5px; background: white; cursor: pointer;">
                        <option value="claude-sonnet-4-20250514" selected>Claude Sonnet 4 (Default)</option>
                        <option value="gpt-4o">GPT-4o</option>
                    </select>
                </div>
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
        // Session management
        let currentUserId = localStorage.getItem('chatUserId') || generateUserId();
        let currentSessionId = localStorage.getItem('currentSessionId') || generateSessionId();
        localStorage.setItem('chatUserId', currentUserId);
        localStorage.setItem('currentSessionId', currentSessionId);
        
        // Model selection
        const modelSelect = document.getElementById('modelSelect');
        let currentModel = localStorage.getItem('selectedModel') || 'claude-sonnet-4-20250514';
        modelSelect.value = currentModel;
        
        modelSelect.addEventListener('change', (e) => {
            currentModel = e.target.value;
            localStorage.setItem('selectedModel', currentModel);
        });
        
        // Use wss:// for HTTPS, ws:// for HTTP
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        let ws = new WebSocket(`${protocol}//${window.location.host}/chat/ws`);
        const chatContainer = document.getElementById('chatContainer');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const typingIndicator = document.getElementById('typingIndicator');
        
        let isConnected = false;
        
        function generateUserId() {
            return 'user_' + Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
        }
        
        function generateSessionId() {
            return 'session_' + Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
        }
        
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
        
        // Session management functions
        function toggleSessions() {
            const panel = document.getElementById('sessionsPanel');
            panel.classList.toggle('collapsed');
        }
        
        async function loadSessions() {
            try {
                const response = await fetch(`/chat/sessions/?user_id=${currentUserId}`);
                const sessions = await response.json();
                
                const sessionsList = document.getElementById('sessionsList');
                sessionsList.innerHTML = '';
                
                sessions.forEach(session => {
                    const sessionDiv = document.createElement('div');
                    sessionDiv.className = 'session-item';
                    if (session.session_id === currentSessionId) {
                        sessionDiv.classList.add('active');
                    }
                    
                    const date = new Date(session.last_message_at || session.created_at);
                    const timeStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
                    
                    sessionDiv.innerHTML = `
                        <div class="session-time">${timeStr}</div>
                        <div class="session-preview">${session.first_message || 'New conversation'}</div>
                        <div class="session-actions">
                            <button class="delete-session-btn" onclick="deleteSession('${session.session_id}', event)">Delete</button>
                        </div>
                    `;
                    
                    sessionDiv.onclick = (e) => {
                        if (!e.target.classList.contains('delete-session-btn')) {
                            loadSession(session.session_id);
                        }
                    };
                    
                    sessionsList.appendChild(sessionDiv);
                });
            } catch (error) {
                console.error('Error loading sessions:', error);
            }
        }
        
        async function loadSession(sessionId) {
            try {
                // Save current session first
                localStorage.setItem('currentSessionId', sessionId);
                currentSessionId = sessionId;
                
                // Load messages
                const response = await fetch(`/chat/sessions/${sessionId}/messages?user_id=${currentUserId}`);
                const messages = await response.json();
                
                // Clear chat container
                chatContainer.innerHTML = '';
                
                // Add messages
                messages.forEach(msg => {
                    addMessage(msg.content, msg.role === 'user' ? 'user' : 'assistant');
                });
                
                // Update active session in UI
                document.querySelectorAll('.session-item').forEach(item => {
                    item.classList.remove('active');
                });
                
                // Reload sessions to update active state
                loadSessions();
                
            } catch (error) {
                console.error('Error loading session:', error);
            }
        }
        
        async function createNewSession() {
            currentSessionId = generateSessionId();
            localStorage.setItem('currentSessionId', currentSessionId);
            
            // Clear chat
            chatContainer.innerHTML = `
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
            `;
            
            // Reload sessions
            loadSessions();
        }
        
        async function deleteSession(sessionId, event) {
            event.stopPropagation();
            
            if (!confirm('Are you sure you want to delete this conversation?')) {
                return;
            }
            
            try {
                const response = await fetch(`/chat/sessions/${sessionId}?user_id=${currentUserId}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    // If deleting current session, create a new one
                    if (sessionId === currentSessionId) {
                        createNewSession();
                    } else {
                        loadSessions();
                    }
                }
            } catch (error) {
                console.error('Error deleting session:', error);
            }
        }
        
        // Update WebSocket message to include user and session IDs
        function sendMessage() {
            const message = messageInput.value.trim();
            if (message && !sendButton.disabled && isConnected) {
                addMessage(message, 'user');
                ws.send(JSON.stringify({
                    type: 'message',
                    content: message,
                    user_id: currentUserId,
                    session_id: currentSessionId,
                    model_id: currentModel
                }));
                messageInput.value = '';
                sendButton.disabled = true;
                typingIndicator.classList.add('active');
            } else if (!isConnected) {
                addMessage('Not connected. Please refresh the page.', 'assistant');
            }
        }
        
        // Load sessions on page load
        window.addEventListener('load', async () => {
            await loadSessions();
            
            // If we have a current session, load its messages
            if (currentSessionId && currentSessionId !== 'null') {
                try {
                    const response = await fetch(`/chat/sessions/${currentSessionId}/messages?user_id=${currentUserId}`);
                    if (response.ok) {
                        const messages = await response.json();
                        if (messages && messages.length > 0) {
                            // Clear welcome message and load session messages
                            chatContainer.innerHTML = '';
                            messages.forEach(msg => {
                                addMessage(msg.content, msg.role === 'user' ? 'user' : 'assistant');
                            });
                        }
                    }
                } catch (error) {
                    console.error('Error loading current session:', error);
                }
            }
        });
        
        // Reload sessions periodically to show updates
        setInterval(loadSessions, 30000); // Every 30 seconds
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
        # Test with default model
        agent = get_agent()
        return {
            "status": "healthy",
            "agent": "initialized" if agent else "not initialized",
            "websocket_path": "/chat/ws",
            "default_model": "claude-sonnet-4-20250514"
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
        # Agent will be created per message with the selected model
        
        while True:
            # Receive message
            data = await websocket.receive_json()
            
            if data.get("type") == "message":
                message = data.get("content", "")
                # Extract user_id, session_id, and model_id from the message
                user_id = data.get("user_id", client_id)
                session_id = data.get("session_id", client_id)
                model_id = data.get("model_id", "claude-sonnet-4-20250514")
                
                # Run agent with proper error handling
                try:
                    # Get agent with selected model
                    agent = get_agent(model_id)
                    
                    # Use async run method since our tools are async
                    response = await agent.arun(
                        message,
                        user_id=user_id,
                        session_id=session_id
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
                    print(f"Error in agent.arun: {error_details}")
                    
                    try:
                        await manager.send_message(
                            json.dumps({
                                "type": "response",
                                "content": f"Error: {str(e)}\n\nPlease try rephrasing your request."
                            }),
                            client_id
                        )
                    except (WebSocketDisconnect, ConnectionError, RuntimeError):
                        # Client already disconnected, just log it
                        print(f"Client {client_id} disconnected before error could be sent")
                    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(client_id)