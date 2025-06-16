# Slack Treez Agent Setup Guide

## Required API Keys

### 1. **OPENAI_API_KEY** (REQUIRED)
- Get from: https://platform.openai.com/api-keys
- Used for: LLM responses and text embeddings
- Export: `export OPENAI_API_KEY="sk-..."`

### 2. **DATABASE_URL** (Optional)
- Default: `postgresql+psycopg://user:password@location/agno`
- Used for: Storing agent sessions, memory, and knowledge base
- Export: `export DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/dbname"`

### 3. **SLACK_BOT_TOKEN** (Optional)
- Get from: Your Slack App settings > OAuth & Permissions
- Used for: Sending messages to Slack
- Export: `export SLACK_BOT_TOKEN="xoxb-..."`

### 4. **FIRECRAWL_API_KEY** (Optional)
- Get from: https://firecrawl.dev
- Used for: Crawling and updating Treez documentation
- Export: `export FIRECRAWL_API_KEY="fc-..."`

## Running the Performance Test

1. Set up environment variables:
```bash
# Required
export OPENAI_API_KEY="your-openai-api-key"

# Optional (for full functionality)
export DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/agno"
export SLACK_BOT_TOKEN="xoxb-your-slack-bot-token"
export FIRECRAWL_API_KEY="your-firecrawl-api-key"
```

2. Run the test script:
```bash
python3 test_slack_performance.py
```

3. Check the performance log:
```bash
tail -f slack_agent_performance.log
```

## Performance Bottlenecks to Monitor

The test script logs detailed timing for:

1. **Agent Creation** - Initializing the agent with all components
2. **Bot Wrapper Creation** - Setting up Slack integration
3. **Total Response Time** - End-to-end message processing
4. **Knowledge Base Search** - Vector similarity search performance

## Current Optimizations

- Model: `gpt-4.1-mini` (faster than gpt-4o)
- Knowledge base limited to top 3 documents
- Streamlined instruction prompt
- History limited to 3 messages
- Disabled monitoring for speed

## Expected Performance

With optimizations:
- Simple queries: 5-15 seconds
- Complex queries with KB search: 15-30 seconds
- Without KB (general queries): 3-10 seconds

## Troubleshooting Slow Responses

1. Check the log file for which phase is slowest
2. Common bottlenecks:
   - Database connection issues
   - Knowledge base search (especially with large datasets)
   - LLM API latency
   - Memory/history retrieval

3. Further optimizations to consider:
   - Use connection pooling for PostgreSQL
   - Implement caching for frequent queries
   - Pre-warm the knowledge base embeddings
   - Use async database operations