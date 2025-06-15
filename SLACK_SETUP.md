# Slack Treez Agent Setup Guide

This guide walks through setting up the Slack integration for the Treez support agent.

## Prerequisites

1. **Slack Workspace**: You need admin access to a Slack workspace
2. **API Keys**: 
   - OpenAI API key (required)
   - Firecrawl API key (optional, for knowledge base updates)
3. **PostgreSQL Database**: For storing agent sessions and knowledge

## Step 1: Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Name your app (e.g., "Treez Support Bot")
4. Select your workspace

## Step 2: Configure Bot Permissions

1. In your app settings, go to "OAuth & Permissions"
2. Under "Bot Token Scopes", add these permissions:
   - `app_mentions:read` - Read messages that mention your bot
   - `chat:write` - Send messages
   - `im:history` - Read direct message history
   - `im:read` - Read direct messages
   - `im:write` - Send direct messages

3. Install the app to your workspace
4. Copy the "Bot User OAuth Token" (starts with `xoxb-`)

## Step 3: Configure Event Subscriptions

1. Go to "Event Subscriptions" in your app settings
2. Enable Events
3. For the Request URL, enter: `https://your-domain.com/v1/slack/events`
   - For local development with ngrok: `https://your-ngrok-url.ngrok.io/v1/slack/events`
4. Subscribe to bot events:
   - `app_mention` - When someone mentions your bot
   - `message.im` - Direct messages to your bot (optional)

## Step 4: Set Up Slash Commands (Optional)

1. Go to "Slash Commands" in your app settings
2. Create a new command: `/treez`
3. Request URL: `https://your-domain.com/v1/slack/slash-commands/treez`
4. Short Description: "Ask Treez support questions"
5. Usage Hint: "[your question about Treez]"

## Step 5: Configure Environment Variables

Add these to your `.env` file:

```bash
# Required
OPENAI_API_KEY="your-openai-api-key"
SLACK_BOT_TOKEN="xoxb-your-bot-token"

# Optional but recommended
SLACK_SIGNING_SECRET="your-signing-secret"  # From Basic Information page
FIRECRAWL_API_KEY="your-firecrawl-key"     # For knowledge base updates

# Database (if not using defaults)
DATABASE_URL="postgresql://user:password@localhost:5432/dbname"
```

## Step 6: Initialize the Knowledge Base

The agent needs Treez documentation in its knowledge base. You have two options:

### Option A: Seed with Basic Knowledge
```bash
curl -X POST http://localhost:8000/v1/slack/knowledge/seed
```

### Option B: Crawl Full Documentation (requires Firecrawl API key)
```bash
curl -X POST http://localhost:8000/v1/slack/knowledge/update
```

## Step 7: Test Your Bot

1. **Test Health Check**:
   ```bash
   curl http://localhost:8000/v1/slack/status
   ```

2. **In Slack**:
   - Mention your bot: `@YourBotName how do I process a return in Treez?`
   - Use slash command: `/treez what are the keyboard shortcuts?`
   - Send a direct message to your bot

## Local Development with ngrok

For local development, use ngrok to expose your local server:

1. Install ngrok: `brew install ngrok` (on macOS)
2. Start your local server: `docker compose up`
3. In another terminal: `ngrok http 8000`
4. Use the ngrok URL for Slack configuration

## API Endpoints

- `POST /v1/slack/events` - Webhook for Slack events
- `POST /v1/slack/slash-commands/treez` - Handler for /treez command
- `POST /v1/slack/knowledge/seed` - Seed initial knowledge base
- `POST /v1/slack/knowledge/update` - Update knowledge from Treez docs
- `GET /v1/slack/status` - Check bot configuration status

## Knowledge Base Management

The agent uses a vector database to store Treez documentation. To keep it updated:

1. **Manual Update**: Call the update endpoint periodically
2. **Scheduled Updates**: Set up a cron job or scheduled task
3. **On-Demand**: Update when new Treez features are released

Example update script:
```bash
#!/bin/bash
# Run weekly to update Treez knowledge
curl -X POST https://your-api.com/v1/slack/knowledge/update
```

## Troubleshooting

### Bot Not Responding
- Check the `/v1/slack/status` endpoint
- Verify SLACK_BOT_TOKEN is set correctly
- Check Docker logs: `docker compose logs -f`

### Knowledge Base Issues
- Ensure PostgreSQL is running
- Check if initial seed was successful
- Verify Firecrawl API key if using web scraping

### Permission Errors
- Reinstall the Slack app to your workspace
- Verify all required bot scopes are added
- Check bot is invited to channels where mentioned

## Security Notes

1. **Request Verification**: In production, implement request signature verification using SLACK_SIGNING_SECRET
2. **Rate Limiting**: Consider implementing rate limiting for slash commands
3. **Error Handling**: The bot handles errors gracefully but logs details for debugging
4. **Data Privacy**: Agent stores conversation history - implement retention policies as needed

## Advanced Configuration

### Custom Knowledge Sources
Modify the `update_knowledge_base` method in `slack_treez_agent.py` to add custom URLs:

```python
urls = [
    "https://support.treez.io/custom-section",
    "https://internal-docs.company.com/treez-guide"
]
```

### Response Formatting
The agent uses Slack markdown. Customize in the agent instructions:
- `*bold*` for emphasis
- `` `code` `` for technical terms
- `>>>` for quoted text
- Emoji reactions for better engagement

### Session Management
Each Slack thread maintains its own session for context continuity. Sessions are stored in PostgreSQL with the pattern: `slack_{channel}_{timestamp}`