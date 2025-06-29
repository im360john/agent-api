# Chat Sessions Testing Guide

## ✅ Deployment Status
The chat sessions feature has been successfully deployed to https://agent-api-xk5r.onrender.com/chat/

## 🧪 How to Test

### 1. Clear Your Browser Cache
Since the UI has been updated, you need to ensure you're seeing the latest version:
- **Hard refresh**: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
- **Or open in incognito/private window**

### 2. Look for the Sessions UI
When you open https://agent-api-xk5r.onrender.com/chat/, you should see:

- **Toggle Button (☰)**: Located on the LEFT edge of the screen
  - It's a green button that slides out the sessions panel
  - If you don't see it, try scrolling or resizing your browser

- **Sessions Panel**: When you click ☰
  - A panel slides out from the left showing "Chat History"
  - Contains a "New Chat" button
  - Lists your previous chat sessions

### 3. Test the Features

#### Create a New Session
1. Send any message in the chat (e.g., "list all competitors")
2. Wait for the response
3. Click the ☰ button to open sessions panel
4. Your current session should appear in the list

#### Start a New Chat
1. Click "New Chat" button in the sessions panel
2. The chat will clear and show the welcome message
3. Send a different message
4. Both sessions should now appear in the history

#### Switch Between Sessions
1. Click on any session in the history
2. The chat will load that session's messages
3. You can continue the conversation from where you left off

#### Delete a Session
1. Hover over a session in the list
2. Click the "Delete" button
3. Confirm deletion
4. The session will be removed

### 4. Test Quick Actions
All the quick action buttons should work with sessions:
- "Check All Prices"
- "View Competitors"
- "Tracked Products"
- etc.

Each action creates a message in your current session.

## 🔍 Troubleshooting

### Can't see the ☰ button?
1. Make sure you're on the full desktop view (not mobile)
2. Try zooming out (Ctrl/Cmd + minus)
3. Check if your browser window is wide enough
4. Clear cache and reload

### Sessions not saving?
1. Check browser console for errors (F12)
2. Make sure localStorage is enabled
3. Try in a different browser

### WebSocket disconnecting?
1. Check your internet connection
2. The server might be under load - try again in a moment
3. Refresh the page and try again

## 📊 API Testing

You can also test the API directly:

```bash
# List sessions for a user
curl "https://agent-api-xk5r.onrender.com/chat/sessions/?user_id=test_user"

# Get messages from a session
curl "https://agent-api-xk5r.onrender.com/chat/sessions/{session_id}/messages?user_id=test_user"

# Delete a session
curl -X DELETE "https://agent-api-xk5r.onrender.com/chat/sessions/{session_id}?user_id=test_user"
```

## ✨ Features Implemented

1. **Persistent User & Session IDs**
   - Stored in localStorage
   - Survives browser refreshes
   - Unique per browser/device

2. **Session Management**
   - View all your chat history
   - Create new sessions
   - Switch between sessions
   - Delete old sessions

3. **Real-time Updates**
   - Sessions list refreshes every 30 seconds
   - New messages appear instantly

4. **Multi-user Support**
   - Each user has their own sessions
   - Sessions are private to each user

## 🎉 Ready to Test!

Open https://agent-api-xk5r.onrender.com/chat/ in a fresh browser window and start chatting!