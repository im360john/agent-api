#!/usr/bin/env python3
"""Test WebSocket connection to chat UI"""

import asyncio
import websockets
import json

async def test_websocket():
    uri = "wss://agent-api-xk5r.onrender.com/chat/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket")
            
            # Send a test message
            message = {
                "type": "message",
                "content": "Hello, can you hear me?"
            }
            
            await websocket.send(json.dumps(message))
            print("📤 Sent:", message)
            
            # Wait for response
            response = await websocket.recv()
            data = json.loads(response)
            print("📥 Received:", data)
            
            # Send another message
            message2 = {
                "type": "message", 
                "content": "list all competitors"
            }
            
            await websocket.send(json.dumps(message2))
            print("📤 Sent:", message2)
            
            # Wait for response
            response2 = await websocket.recv()
            data2 = json.loads(response2)
            print("📥 Received:", data2)
            
    except Exception as e:
        print(f"❌ WebSocket error: {e}")

if __name__ == "__main__":
    print("🔍 Testing WebSocket connection to chat UI...")
    asyncio.run(test_websocket())