# Testing the Update Knowledge Base Script

This guide explains how to run the `test_update_knowledge_base.py` script to test the Slack Treez agent's knowledge base update functionality.

## Prerequisites

1. **PostgreSQL Database**: You need a PostgreSQL database running. The default connection expects:
   - Host: localhost
   - Port: 5432
   - Database: ai
   - User: ai
   - Password: ai

2. **Required Environment Variables**: Create a `.env` file in the project root with:
   ```env
   # Required
   OPENAI_API_KEY=your_openai_api_key_here
   FIRECRAWL_API_KEY=your_firecrawl_api_key_here
   
   # Database URL (if different from default)
   DATABASE_URL=postgresql+psycopg://user:password@host:port/database
   
   # Optional (for full Slack functionality, not needed for this test)
   SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
   ```

3. **Python Dependencies**: Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Setting up PostgreSQL (if needed)

If you don't have PostgreSQL running locally:

### Option 1: Using Docker
```bash
docker run -d \
  --name postgres-ai \
  -e POSTGRES_USER=ai \
  -e POSTGRES_PASSWORD=ai \
  -e POSTGRES_DB=ai \
  -p 5432:5432 \
  postgres:15
```

### Option 2: Using the project's compose.yaml
```bash
docker-compose up -d db
```

## Running the Test

1. Ensure your `.env` file is configured with the required API keys
2. Ensure PostgreSQL is running and accessible
3. Run the test script:
   ```bash
   python test_update_knowledge_base.py
   ```

## What the Test Does

1. Creates a Slack Treez agent instance
2. Crawls the Treez support documentation (limited to 10 pages for testing)
3. Stores the crawled content in the PostgreSQL vector database
4. Tests searching the knowledge base for "Treez POS"
5. Displays results and debug information

## Expected Output

You should see:
- Log messages about crawling progress
- Debug information about the crawl response structure
- Summary of pages processed, content found, and documents added
- Search results from the knowledge base (if any were added)

## Troubleshooting

### Database Connection Error
If you see: `psycopg.OperationalError: [Errno -2] Name or service not known`

This means the database hostname can't be resolved. Check:
- Is PostgreSQL running?
- Is the DATABASE_URL correct?
- Can you connect with: `psql -h localhost -U ai -d ai`

### No Documents Added
If the crawl completes but no documents are added:
- Check the debug logs for the crawl response structure
- Look for "Pages with content" and "Treez URLs found" in the summary
- The logs will show why pages were skipped (no content, no URL, non-Treez URL)

### Missing API Keys
- Get an OpenAI API key from https://platform.openai.com/
- Get a Firecrawl API key from https://firecrawl.dev/