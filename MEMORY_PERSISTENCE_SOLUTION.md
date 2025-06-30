# PostgresMemoryDb Initialization and Memory Persistence Solution

## Issue Summary

Messages are not being saved to the `competitive_pricing_chat_memory` table because:

1. **Wrong Schema**: The agno framework expects memory tables to be in the `ai` schema, not the default `public` schema
2. **Wrong Table Structure**: The manually created table has a different structure than what agno expects
3. **Configuration Issues**: The agent is configured to delete and clear memories, preventing persistence
4. **Table Name Mismatch**: The agent uses `competitive_pricing_memories` but the UI uses `competitive_pricing_chat_memory`

## Root Causes

### 1. Schema Mismatch
- The SQL script creates tables in the `public` schema
- The agno framework expects tables in the `ai` schema

### 2. Table Structure Mismatch
Your SQL creates:
```sql
CREATE TABLE competitive_pricing_chat_memory (
    user_message JSONB,
    ai_message JSONB,
    ...
)
```

But agno expects:
```sql
CREATE TABLE ai.competitive_pricing_chat_memory (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    memory TEXT,
    metadata JSONB,
    ...
)
```

### 3. Memory Configuration Issues
In `competitive_pricing_agent.py`:
```python
memory=Memory(
    db=PostgresMemoryDb(table_name="competitive_pricing_memories", db_url=db_url),
    delete_memories=True,  # ❌ This deletes memories after use
    clear_memories=True,   # ❌ This clears memories on init
)
```

## Solution

### Step 1: Run the Fix Script

```bash
python fix_competitive_pricing_memory.py
```

This script will:
- Create the `ai` schema
- Create the memory table with the correct structure
- Set up proper indexes and triggers

### Step 2: Update Agent Configuration

Edit `agents/competitive_pricing_agent.py`:

```python
# Change this:
memory=Memory(
    model=OpenAIChat(id=model_id),
    db=PostgresMemoryDb(table_name="competitive_pricing_memories", db_url=db_url),
    delete_memories=True,
    clear_memories=True,
),

# To this:
memory=Memory(
    model=OpenAIChat(id=model_id),
    db=PostgresMemoryDb(table_name="competitive_pricing_chat_memory", db_url=db_url),
    delete_memories=False,  # Keep memories for persistence
    clear_memories=False,   # Don't clear memories on init
),
```

### Step 3: Ensure Consistent Table Names

Make sure all components use the same table name. The UI already uses `competitive_pricing_chat_memory`, so update the agent to match.

### Step 4: Verify Memory Persistence

After making these changes:

1. Start a chat session
2. Send some messages
3. Check the database:

```sql
SELECT * FROM ai.competitive_pricing_chat_memory 
ORDER BY created_at DESC 
LIMIT 10;
```

## How PostgresMemoryDb Works

The agno framework's `PostgresMemoryDb`:

1. **Auto-creates tables**: It creates tables in the `ai` schema when first used
2. **Expects specific schema**: Tables must have `id`, `user_id`, `memory`, `metadata` columns
3. **Manages persistence**: Based on `delete_memories` and `clear_memories` settings
4. **Tracks by user**: Memories are associated with `user_id` for personalization

## Key Configuration Points

1. **Table Name**: Must be consistent across all components
2. **Schema**: Tables are created in the `ai` schema
3. **Memory Settings**:
   - `delete_memories=False` - Keep memories after use
   - `clear_memories=False` - Don't clear on initialization
4. **Agent ID**: Keep consistent for memory continuity

## Testing Memory Persistence

Use the diagnostic script:

```bash
python diagnose_memory_issue.py
```

This will show:
- What tables exist
- Current memory configuration
- Any stored memories

## Additional Notes

- The agno framework handles table creation automatically when properly configured
- No need to manually create tables with SQL scripts
- The framework uses the `ai` schema by default for all its tables
- Memory persistence requires both proper configuration and consistent table names