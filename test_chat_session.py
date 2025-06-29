#!/usr/bin/env python3
"""Test creating a chat session and interacting with the agent"""

import asyncio
import websockets
import json
import uuid
import requests
from datetime import datetime

BASE_URL = "https://agent-api-xk5r.onrender.com"
WS_URL = "wss://agent-api-xk5r.onrender.com/chat/ws"

async def test_chat_session():
    """Test creating a session and sending messages"""
    
    # Generate IDs
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    
    print(f"Testing with:")
    print(f"  User ID: {user_id}")
    print(f"  Session ID: {session_id}")
    print()
    
    # Connect to WebSocket
    print("1. Connecting to WebSocket...")
    try:
        async with websockets.connect(WS_URL) as websocket:
            print("   Connected!")
            
            # Test 1: Send a simple message
            print("\n2. Sending test message...")
            message = {
                "type": "message",
                "content": "list all competitors",
                "user_id": user_id,
                "session_id": session_id
            }
            
            await websocket.send(json.dumps(message))
            print("   Message sent!")
            
            # Wait for response
            print("   Waiting for response...")
            response = await asyncio.wait_for(websocket.recv(), timeout=30)
            data = json.loads(response)
            
            if data.get("type") == "response":
                print(f"   Got response: {data.get('content', '')[:200]}...")
            else:
                print(f"   Unexpected response: {data}")
            
            # Test 2: Send another message in same session
            print("\n3. Sending follow-up message...")
            message2 = {
                "type": "message",
                "content": "how many competitors are there?",
                "user_id": user_id,
                "session_id": session_id
            }
            
            await websocket.send(json.dumps(message2))
            response2 = await asyncio.wait_for(websocket.recv(), timeout=30)
            data2 = json.loads(response2)
            
            if data2.get("type") == "response":
                print(f"   Got response: {data2.get('content', '')[:200]}...")
            
    except Exception as e:
        print(f"   WebSocket error: {e}")
    
    # Check if messages were stored
    print("\n4. Checking if messages were stored...")
    await asyncio.sleep(2)  # Give it time to save
    
    try:
        response = requests.get(f"{BASE_URL}/chat/sessions/?user_id={user_id}")
        if response.status_code == 200:
            sessions = response.json()
            print(f"   Found {len(sessions)} sessions for user")
            
            if sessions:
                # Get messages from the session
                print("\n5. Retrieving session messages...")
                msg_response = requests.get(
                    f"{BASE_URL}/chat/sessions/{session_id}/messages?user_id={user_id}"
                )
                
                if msg_response.status_code == 200:
                    messages = msg_response.json()
                    print(f"   Found {len(messages)} messages in session")
                    
                    for i, msg in enumerate(messages[:4]):  # Show first 4
                        print(f"   Message {i+1} ({msg['role']}): {msg['content'][:100]}...")
                else:
                    print(f"   Failed to get messages: {msg_response.status_code}")
        else:
            print(f"   Failed to get sessions: {response.status_code}")
            
    except Exception as e:
        print(f"   Error checking sessions: {e}")
    
    # Test deletion
    print("\n6. Testing session deletion...")
    try:
        del_response = requests.delete(
            f"{BASE_URL}/chat/sessions/{session_id}?user_id={user_id}"
        )
        
        if del_response.status_code == 200:
            print("   Session deleted successfully!")
        else:
            print(f"   Failed to delete: {del_response.status_code}")
            
    except Exception as e:
        print(f"   Error deleting session: {e}")
    
    print("\nTest complete!")

if __name__ == "__main__":
    asyncio.run(test_chat_session())