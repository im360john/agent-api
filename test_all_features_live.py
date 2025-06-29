#!/usr/bin/env python3
"""Test all live features on the deployed site"""

import asyncio
import websockets
import json
import uuid
import time

BASE_URL = "https://agent-api-xk5r.onrender.com"
WS_URL = "wss://agent-api-xk5r.onrender.com/chat/ws"

# All quick action prompts from the UI
QUICK_ACTIONS = [
    ("Check All Prices", "check prices for all tracked products"),
    ("View Competitors", "list all competitors"),
    ("Tracked Products", "list all tracked products"),
    ("Track New Product", "help me add a new product to track"),
    ("Price Trends", "analyze pricing trends for the last 7 days"),
    ("Price History", "get price history for Wyld products"),
    ("Batch Check", "create a batch job to check all prices")
]

async def test_quick_action(websocket, action_name, prompt, user_id, session_id, model_id="claude-sonnet-4-20250514"):
    """Test a single quick action"""
    print(f"\n{'='*60}")
    print(f"Testing: {action_name}")
    print(f"Prompt: {prompt}")
    print(f"Model: {model_id}")
    
    # Send message
    msg = {
        "type": "message",
        "content": prompt,
        "user_id": user_id,
        "session_id": session_id,
        "model_id": model_id
    }
    
    await websocket.send(json.dumps(msg))
    print("✓ Message sent")
    
    # Collect response
    response_content = ""
    start_time = time.time()
    timeout = 30  # 30 second timeout
    
    try:
        while True:
            if time.time() - start_time > timeout:
                print(f"⏱️ Timeout after {timeout} seconds")
                break
                
            message = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(message)
            
            if data.get("type") == "stream":
                response_content += data.get("content", "")
                print(".", end="", flush=True)
            elif data.get("type") == "response":
                # Final response
                response_content = data.get("content", response_content)
                print(f"\n✓ Response received ({len(response_content)} chars)")
                
                # Show first 300 chars of response
                print(f"Response preview: {response_content[:300]}...")
                
                # Check for common error patterns
                if "error" in response_content.lower():
                    print("⚠️ Response contains 'error'")
                elif "track" in action_name.lower() and "track" in response_content.lower():
                    print("✅ Tracking response looks good")
                elif "price" in action_name.lower() and ("$" in response_content or "price" in response_content.lower()):
                    print("✅ Pricing response looks good")
                elif "competitor" in action_name.lower() and "competitor" in response_content.lower():
                    print("✅ Competitor response looks good")
                else:
                    print("✅ Response received")
                    
                break
                
    except asyncio.TimeoutError:
        print("\n⚠️ No response received within timeout")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    return response_content

async def test_all_features():
    """Test all features"""
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    
    print(f"🧪 Testing All Live Features")
    print(f"User ID: {user_id}")
    print(f"Session ID: {session_id}")
    
    try:
        async with websockets.connect(WS_URL) as websocket:
            print("✓ Connected to WebSocket")
            
            # Test all quick actions with Claude
            print("\n" + "="*60)
            print("TESTING WITH CLAUDE SONNET 4")
            print("="*60)
            
            for action_name, prompt in QUICK_ACTIONS:
                await test_quick_action(websocket, action_name, prompt, user_id, session_id, "claude-sonnet-4-20250514")
                await asyncio.sleep(2)  # Small delay between tests
            
            # Test model switching - try one action with GPT-4o
            print("\n" + "="*60)
            print("TESTING MODEL SWITCHING - GPT-4o")
            print("="*60)
            
            await test_quick_action(
                websocket, 
                "Check Prices (GPT-4o)", 
                "check prices for Camino gummies", 
                user_id, 
                session_id, 
                "gpt-4o"
            )
            
            # Test conversation history
            print("\n" + "="*60)
            print("TESTING CONVERSATION HISTORY")
            print("="*60)
            
            await test_quick_action(
                websocket,
                "History Check",
                "what did I just ask you about?",
                user_id,
                session_id,
                "claude-sonnet-4-20250514"
            )
            
    except Exception as e:
        print(f"\n❌ WebSocket connection error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("🏁 Testing complete!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_all_features())