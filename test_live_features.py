#!/usr/bin/env python3
"""Test live features on the deployed site"""

import asyncio
import websockets
import json
import uuid
import requests
import time

BASE_URL = "https://agent-api-xk5r.onrender.com"
WS_URL = "wss://agent-api-xk5r.onrender.com/chat/ws"

async def test_features():
    """Test all the updated features"""
    
    # Generate IDs
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    
    print("🧪 Testing Live Features")
    print("="*60)
    print(f"User ID: {user_id}")
    print(f"Session ID: {session_id}")
    print()
    
    # Test 1: Check if health endpoint has new fields
    print("1. Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/chat/health")
        data = response.json()
        print(f"   Status: {data.get('status')}")
        print(f"   Default model: {data.get('default_model', 'Not found')}")
        print(f"   Has new fields: {'default_model' in data}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Test WebSocket with model selection
    print("\n2. Testing WebSocket with model selection...")
    try:
        async with websockets.connect(WS_URL) as websocket:
            print("   ✓ Connected!")
            
            # Test tracking workflow
            print("\n3. Testing product tracking workflow...")
            
            # First message: Ask to track a product
            msg1 = {
                "type": "message",
                "content": "track camino raspberry lemonade",
                "user_id": user_id,
                "session_id": session_id,
                "model_id": "gpt-4o"  # Test with GPT-4o
            }
            
            await websocket.send(json.dumps(msg1))
            print("   Sent: 'track camino raspberry lemonade'")
            
            try:
                response1 = await asyncio.wait_for(websocket.recv(), timeout=30)
                data1 = json.loads(response1)
                if data1.get("type") == "response":
                    content = data1.get("content", "")
                    print(f"   Response preview: {content[:200]}...")
                    
                    # Check if it's asking for confirmation
                    if "confirm" in content.lower() or "proceed" in content.lower():
                        print("   ✓ Agent asked for confirmation!")
                        
                        # Send confirmation
                        msg2 = {
                            "type": "message",
                            "content": "proceed",
                            "user_id": user_id,
                            "session_id": session_id,
                            "model_id": "gpt-4o"
                        }
                        
                        await websocket.send(json.dumps(msg2))
                        print("   Sent: 'proceed'")
                        
                        response2 = await asyncio.wait_for(websocket.recv(), timeout=30)
                        data2 = json.loads(response2)
                        if data2.get("type") == "response":
                            content2 = data2.get("content", "")
                            print(f"   Response: {content2[:200]}...")
                            
                            # Check if tracking was successful
                            if "track" in content2.lower() and "added" in content2.lower():
                                print("   ✅ Product tracking successful!")
                            else:
                                print("   ❓ Unclear if product was tracked")
                                
            except asyncio.TimeoutError:
                print("   ⏱️ Timeout waiting for response")
            
            # Test 4: Test conversation history awareness
            print("\n4. Testing conversation history awareness...")
            
            msg3 = {
                "type": "message",
                "content": "what product did I just ask you to track?",
                "user_id": user_id,
                "session_id": session_id,
                "model_id": "claude-sonnet-4-20250514"  # Test with Claude
            }
            
            await websocket.send(json.dumps(msg3))
            print("   Sent: 'what product did I just ask you to track?'")
            
            try:
                response3 = await asyncio.wait_for(websocket.recv(), timeout=30)
                data3 = json.loads(response3)
                if data3.get("type") == "response":
                    content3 = data3.get("content", "")
                    print(f"   Response: {content3[:200]}...")
                    
                    if "camino" in content3.lower() and "raspberry" in content3.lower():
                        print("   ✅ Agent remembers conversation history!")
                    else:
                        print("   ❌ Agent doesn't seem to remember the product")
                        
            except asyncio.TimeoutError:
                print("   ⏱️ Timeout waiting for response")
                
    except Exception as e:
        print(f"   WebSocket error: {e}")
    
    # Test 5: Check if sessions persist
    print("\n5. Testing session persistence...")
    await asyncio.sleep(2)
    
    try:
        response = requests.get(f"{BASE_URL}/chat/sessions/?user_id={user_id}")
        if response.status_code == 200:
            sessions = response.json()
            print(f"   Found {len(sessions)} sessions")
            
            if sessions:
                # Get messages from our test session
                msg_response = requests.get(
                    f"{BASE_URL}/chat/sessions/{session_id}/messages?user_id={user_id}"
                )
                if msg_response.status_code == 200:
                    messages = msg_response.json()
                    print(f"   Session has {len(messages)} messages")
                    for i, msg in enumerate(messages[:4]):
                        print(f"   Message {i+1} ({msg['role']}): {msg['content'][:50]}...")
                else:
                    print(f"   Error getting messages: {msg_response.status_code}")
        else:
            print(f"   Error getting sessions: {response.status_code}")
            
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "="*60)
    print("Testing complete!")
    print("\nSummary:")
    print("- Model picker: Check manually in browser")
    print("- Sessions panel: Check manually in browser")
    print("- Product tracking: Test above")
    print("- History awareness: Test above")
    print("- Session persistence: Test above")

if __name__ == "__main__":
    asyncio.run(test_features())