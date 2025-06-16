#!/usr/bin/env python3
"""
Fixed memory configuration for Slack Treez Agent
Shows the changes needed to properly persist memory
"""

# Current problematic configuration:
"""
memory = Memory(
    model=OpenAIChat(id=model_id),
    db=memory_db,
    delete_memories=True,  # ❌ This deletes memories after use
    clear_memories=True    # ❌ This clears memories on init
)

# And:
agent_id=f"slack_treez_agent_{run_id}",  # ❌ Changes every time
"""

# Recommended configuration for persistent memory:
"""
memory = Memory(
    model=OpenAIChat(id=model_id),
    db=memory_db,
    delete_memories=False,  # ✅ Keep memories
    clear_memories=False    # ✅ Don't clear on init
)

# And use consistent agent_id:
agent_id="slack_treez_agent",  # ✅ Same ID across sessions
"""

# To create the memory table manually if needed:
CREATE_MEMORY_TABLE_SQL = """
CREATE SCHEMA IF NOT EXISTS ai;

CREATE TABLE IF NOT EXISTS ai.slack_treez_agent_memory (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR,
    memory TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_memory_user_id 
ON ai.slack_treez_agent_memory(user_id);

CREATE INDEX IF NOT EXISTS idx_memory_updated 
ON ai.slack_treez_agent_memory(updated_at DESC);
"""

print("Memory configuration issues identified:")
print("1. delete_memories=True and clear_memories=True are clearing memories")
print("2. agent_id changes on every run, preventing memory persistence")
print("3. Memory table may not exist in the database")
print("\nTo fix:")
print("1. Set delete_memories=False and clear_memories=False")
print("2. Use a consistent agent_id")
print("3. Run the CREATE TABLE SQL above if table doesn't exist")