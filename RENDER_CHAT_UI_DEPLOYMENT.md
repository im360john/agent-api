# Deploying Chat UI on Render

## Overview
Since Render only supports one port, we've integrated the chat UI directly into your FastAPI application. The chat interface will be available at:
```
https://agent-api-xk5r.onrender.com/chat
```

## What Was Changed

### 1. Updated `requirements.txt`
- Changed `agno==1.6.2` to `agno[ag-ui]==1.6.2` to include AG UI dependencies

### 2. Created Chat UI Route (`api/routes/chat_ui.py`)
- Integrated chat interface directly into FastAPI
- WebSocket support for real-time chat
- Custom HTML/CSS/JS interface (no external dependencies)
- All functionality in a single endpoint

### 3. Updated `api/main.py`
- Added chat router to the FastAPI app
- Chat UI accessible at `/chat`

## Deployment Steps

### 1. Push Changes to GitHub
```bash
git add -A
git commit -m "Add integrated chat UI for competitive pricing agent"
git push origin normal
```

### 2. Render Will Auto-Deploy
Since you have auto-deploy enabled, Render will:
1. Detect the changes
2. Install new requirements (including AG UI)
3. Restart the service
4. Make chat available at `/chat`

### 3. Environment Variables
Make sure these are set in Render dashboard:
```
# Database (already set)
DB_HOST
DB_PORT
DB_DATABASE
DB_USER
DB_PASS

# OpenAI (required for chat)
OPENAI_API_KEY

# Scraping APIs (optional but recommended)
FIRECRAWL_API_KEY
BROWSERBASE_API_KEY
EXA_API_KEY
```

## Access Points

Once deployed, you'll have:

1. **API Documentation**: https://agent-api-xk5r.onrender.com/docs
2. **Chat Interface**: https://agent-api-xk5r.onrender.com/chat
3. **API Endpoints**: https://agent-api-xk5r.onrender.com/v1/agents/...

## Features in the Chat UI

The integrated chat interface includes:

### Sidebar Quick Actions
- 📊 Check All Prices
- 🏪 View Competitors  
- 📈 Confidence Report
- ➕ Track New Product
- 📉 Price Trends
- 📦 Tracked Products
- 🔍 Performance Analysis

### Chat Features
- Real-time WebSocket communication
- Markdown rendering for tables
- Confidence indicators (🟢🟡🔴)
- Welcome message with examples
- Mobile-responsive design

### Visual Design
- Cannabis industry green theme
- Clean, professional interface
- Hover effects and animations
- Accessible typography

## Troubleshooting

### If Chat UI Doesn't Load

1. **Check Logs in Render Dashboard**
   - Look for import errors
   - Check for WebSocket connection issues

2. **Verify Requirements Installation**
   ```
   agno[ag-ui] should be installed
   ```

3. **Database Tables**
   - Make sure knowledge base tables are created
   - Run the migration SQL if needed

### WebSocket Issues

If WebSocket connections fail:
1. Render supports WebSockets by default
2. Make sure your browser allows WebSocket connections
3. Check browser console for errors

### Performance

The chat UI is lightweight and should not impact your API performance:
- Single HTML page (no build process)
- WebSocket for efficient real-time communication
- Agent instance is cached

## Testing Locally

Before deploying, test locally:
```bash
# Install requirements
pip install -r requirements.txt

# Run server
python start_server.py

# Access at http://localhost:8000/chat
```

## Security Considerations

1. **No Built-in Authentication**
   - Consider adding authentication if needed
   - Can use Render's access control features

2. **Rate Limiting**
   - Add rate limiting for production use
   - Prevent abuse of the chat interface

3. **CORS Settings**
   - Already configured in your FastAPI app
   - Adjust if needed for specific domains

## Next Steps

After deployment:

1. **Test the Chat Interface**
   - Go to https://agent-api-xk5r.onrender.com/chat
   - Try quick actions
   - Test price checking

2. **Monitor Usage**
   - Check Render metrics
   - Monitor OpenAI API usage
   - Track scraping API calls

3. **Customize Further**
   - Edit `chat_ui.py` to change colors/styling
   - Add more quick actions
   - Enhance the UI as needed

## Alternative Approaches

If you need more advanced features:

1. **Separate UI Service**
   - Deploy AG UI as a separate Render service
   - Use Render's private networking

2. **Static Site with API**
   - Build a React/Vue frontend
   - Deploy on Render Static Sites
   - Call your API endpoints

3. **Embed in Existing Site**
   - Use iframe to embed chat
   - Or build custom integration

The current integrated approach is the simplest for single-port deployment on Render!