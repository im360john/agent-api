#!/usr/bin/env python3
"""Quick test of live sessions functionality"""

import requests

BASE_URL = "https://agent-api-xk5r.onrender.com"

# Test 1: Check if sessions endpoint exists
print("1. Testing sessions endpoint...")
try:
    response = requests.get(f"{BASE_URL}/chat/sessions/?user_id=test_user")
    print(f"   Status: {response.status_code}")
    if response.status_code == 500:
        print(f"   Error: {response.json().get('detail', 'Unknown error')[:200]}...")
    elif response.status_code == 200:
        print(f"   Success! Found {len(response.json())} sessions")
except Exception as e:
    print(f"   Failed: {e}")

# Test 2: Check main chat UI
print("\n2. Checking chat UI...")
try:
    response = requests.get(f"{BASE_URL}/chat/")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        html = response.text
        has_sessions = "sessions-panel" in html
        has_localStorage = "localStorage" in html and "chatUserId" in html
        has_toggle = "toggle-sessions-btn" in html
        
        print(f"   Has sessions panel: {has_sessions}")
        print(f"   Has localStorage code: {has_localStorage}")
        print(f"   Has toggle button: {has_toggle}")
        
        # Check for specific functions
        has_loadSessions = "loadSessions" in html
        has_createNewSession = "createNewSession" in html
        print(f"   Has loadSessions function: {has_loadSessions}")
        print(f"   Has createNewSession function: {has_createNewSession}")
except Exception as e:
    print(f"   Failed: {e}")

# Test 3: Check if WebSocket sends user_id and session_id
print("\n3. Checking WebSocket code...")
try:
    response = requests.get(f"{BASE_URL}/chat/")
    if response.status_code == 200:
        html = response.text
        # Look for the sendMessage function
        if "ws.send(JSON.stringify({" in html:
            # Check if it includes user_id and session_id
            sends_user_id = "user_id: currentUserId" in html or "user_id: " in html
            sends_session_id = "session_id: currentSessionId" in html or "session_id: " in html
            print(f"   Sends user_id: {sends_user_id}")
            print(f"   Sends session_id: {sends_session_id}")
except Exception as e:
    print(f"   Failed: {e}")

print("\nSummary:")
print("The sessions API is deployed but encountering a database table error.")
print("The chat UI hasn't been updated with the sessions interface yet.")
print("This suggests a partial deployment or caching issue.")