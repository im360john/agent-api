# Manual Testing Guide for Live Updates

Once the deployment is complete, test these features at https://agent-api-xk5r.onrender.com/chat/

## 1. Model Picker
- Look for "AI Model:" dropdown in the header
- Should have two options:
  - Claude Sonnet 4 (Default)
  - GPT-4o
- Test switching between models
- Model preference should persist after page refresh

## 2. Sessions Panel
- Look for ☰ button on the left edge
- Click to open Chat History panel
- Should show:
  - "Chat History" header
  - "New Chat" button
  - List of previous sessions
- Test creating new sessions
- Test switching between sessions
- Sessions should persist after refresh

## 3. Product Tracking Workflow
Test this conversation flow:
```
You: track camino raspberry lemonade
Bot: [Should show what will be tracked and ask for confirmation]
You: proceed
Bot: [Should actually track the product using track_product()]
```

## 4. Conversation History Awareness
After having a conversation:
```
You: what product did I just ask about?
Bot: [Should remember "Camino Raspberry Lemonade"]
```

## 5. Quick Actions
Test each button:
- Check All Prices
- View Competitors
- Tracked Products
- Track New Product
- Price Trends
- Price History
- Batch Check

Each should work without the bulk_price_check validation error.

## 6. Session Persistence
1. Have a conversation
2. Refresh the browser
3. Your previous messages should reload
4. The session should appear in Chat History

## Troubleshooting

If features aren't showing:
1. Hard refresh: Ctrl+Shift+R (or Cmd+Shift+R on Mac)
2. Try incognito/private window
3. Clear browser cache
4. Check browser console for errors (F12)

## Expected Behavior

With the updates, the agent should:
- Remember conversation context across multiple messages
- Show its reasoning process (show_full_reasoning=True)
- Include timestamps in its awareness
- Use Claude Sonnet 4 for reasoning when Claude is selected
- Properly track products when user confirms
- Handle all quick actions without errors