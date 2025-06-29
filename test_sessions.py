#!/usr/bin/env python3
"""Test script for chat sessions functionality"""

import asyncio
import aiohttp
import json
from datetime import datetime
import uuid

BASE_URL = "https://agent-api-xk5r.onrender.com"
# BASE_URL = "http://localhost:8000"  # Uncomment for local testing

class SessionTester:
    def __init__(self):
        self.user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        self.session_id = None
        self.sessions = []
        
    async def test_create_session(self, session: aiohttp.ClientSession):
        """Test creating a new session"""
        print("\n1. Testing session creation...")
        
        url = f"{BASE_URL}/chat/sessions/"
        data = {
            "user_id": self.user_id,
            "initial_message": "Test session creation"
        }
        
        async with session.post(url, json=data) as resp:
            if resp.status == 200:
                result = await resp.json()
                self.session_id = result.get("session_id")
                print(f"✓ Session created: {self.session_id}")
                return True
            else:
                print(f"✗ Failed to create session: {resp.status}")
                return False
    
    async def test_websocket_chat(self):
        """Test WebSocket chat with session IDs"""
        print("\n2. Testing WebSocket chat...")
        
        ws_url = BASE_URL.replace("https://", "wss://").replace("http://", "ws://") + "/chat/ws"
        
        try:
            session = aiohttp.ClientSession()
            async with session.ws_connect(ws_url) as ws:
                # Send a test message
                message = {
                    "type": "message",
                    "content": "list all competitors",
                    "user_id": self.user_id,
                    "session_id": self.session_id
                }
                
                await ws.send_json(message)
                print(f"✓ Sent message with session ID: {self.session_id}")
                
                # Wait for response
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        if data.get("type") == "response":
                            print(f"✓ Received response: {data.get('content')[:100]}...")
                            break
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        print(f"✗ WebSocket error: {ws.exception()}")
                        break
                        
            await session.close()
            return True
            
        except Exception as e:
            print(f"✗ WebSocket connection failed: {e}")
            return False
    
    async def test_list_sessions(self, session: aiohttp.ClientSession):
        """Test listing user sessions"""
        print("\n3. Testing session listing...")
        
        url = f"{BASE_URL}/chat/sessions/?user_id={self.user_id}"
        
        async with session.get(url) as resp:
            if resp.status == 200:
                sessions = await resp.json()
                self.sessions = sessions
                print(f"✓ Found {len(sessions)} sessions")
                for s in sessions[:3]:  # Show first 3
                    print(f"  - Session {s['session_id']}: {s.get('first_message', 'No messages')}")
                return True
            else:
                print(f"✗ Failed to list sessions: {resp.status}")
                return False
    
    async def test_get_messages(self, session: aiohttp.ClientSession):
        """Test retrieving session messages"""
        print("\n4. Testing message retrieval...")
        
        if not self.session_id:
            print("✗ No session ID available")
            return False
            
        url = f"{BASE_URL}/chat/sessions/{self.session_id}/messages?user_id={self.user_id}"
        
        async with session.get(url) as resp:
            if resp.status == 200:
                messages = await resp.json()
                print(f"✓ Retrieved {len(messages)} messages")
                for msg in messages[:3]:  # Show first 3
                    print(f"  - {msg['role']}: {msg['content'][:50]}...")
                return True
            else:
                print(f"✗ Failed to get messages: {resp.status}")
                return False
    
    async def test_delete_session(self, session: aiohttp.ClientSession):
        """Test deleting a session"""
        print("\n5. Testing session deletion...")
        
        if not self.session_id:
            print("✗ No session ID available")
            return False
            
        url = f"{BASE_URL}/chat/sessions/{self.session_id}?user_id={self.user_id}"
        
        async with session.delete(url) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"✓ Session deleted: {result['message']}")
                return True
            else:
                print(f"✗ Failed to delete session: {resp.status}")
                return False
    
    async def test_quick_actions(self):
        """Test all quick action prompts"""
        print("\n6. Testing quick action prompts...")
        
        quick_actions = [
            "check prices for all tracked products",
            "list all competitors",
            "list all tracked products",
            "help me add a new product to track",
            "analyze pricing trends for the last 7 days",
            "get price history for Wyld products",
            "create a batch job to check all prices"
        ]
        
        ws_url = BASE_URL.replace("https://", "wss://").replace("http://", "ws://") + "/chat/ws"
        
        session = aiohttp.ClientSession()
        try:
            async with session.ws_connect(ws_url) as ws:
                for action in quick_actions:
                    print(f"\n  Testing: '{action}'")
                    
                    # Create new session for each test
                    test_session_id = f"session_{uuid.uuid4().hex[:8]}"
                    
                    message = {
                        "type": "message",
                        "content": action,
                        "user_id": self.user_id,
                        "session_id": test_session_id
                    }
                    
                    await ws.send_json(message)
                    
                    # Wait for response with timeout
                    try:
                        msg = await asyncio.wait_for(ws.receive(), timeout=30)
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            if data.get("type") == "response":
                                response = data.get("content", "")
                                if "Error" in response:
                                    print(f"  ✗ Error response: {response[:100]}")
                                else:
                                    print(f"  ✓ Success: {response[:100]}...")
                        else:
                            print(f"  ✗ Unexpected message type: {msg.type}")
                    except asyncio.TimeoutError:
                        print(f"  ✗ Timeout waiting for response")
                        
        except Exception as e:
            print(f"✗ Quick actions test failed: {e}")
        finally:
            await session.close()
    
    async def run_all_tests(self):
        """Run all tests"""
        print(f"Starting session tests for user: {self.user_id}")
        print("=" * 60)
        
        async with aiohttp.ClientSession() as session:
            # Run tests in sequence
            await self.test_create_session(session)
            await self.test_websocket_chat()
            await self.test_list_sessions(session)
            await self.test_get_messages(session)
            await self.test_delete_session(session)
            await self.test_quick_actions()
        
        print("\n" + "=" * 60)
        print("Tests completed!")

async def main():
    tester = SessionTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())