-- Create the competitive_pricing_chat_memory table for storing chat history
-- This table is used by the Agno Memory v2 system
CREATE TABLE IF NOT EXISTS competitive_pricing_chat_memory (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    user_message JSONB,
    ai_message JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Create indexes for efficient querying
    CONSTRAINT unique_memory_entry UNIQUE (user_id, session_id, created_at)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_chat_memory_user_id ON competitive_pricing_chat_memory(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_memory_session_id ON competitive_pricing_chat_memory(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_memory_user_session ON competitive_pricing_chat_memory(user_id, session_id);
CREATE INDEX IF NOT EXISTS idx_chat_memory_created_at ON competitive_pricing_chat_memory(created_at DESC);

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update the updated_at column
CREATE TRIGGER update_competitive_pricing_chat_memory_updated_at 
    BEFORE UPDATE ON competitive_pricing_chat_memory 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create table for storing agent sessions (used by PostgresAgentStorage)
CREATE TABLE IF NOT EXISTS competitive_pricing_chat_agents (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    user_id TEXT,
    memory JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_agent_session UNIQUE (session_id, agent_id)
);

-- Create indexes for agent sessions
CREATE INDEX IF NOT EXISTS idx_chat_agents_session_id ON competitive_pricing_chat_agents(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_agents_agent_id ON competitive_pricing_chat_agents(agent_id);
CREATE INDEX IF NOT EXISTS idx_chat_agents_user_id ON competitive_pricing_chat_agents(user_id);

-- Create trigger for agent sessions updated_at
CREATE TRIGGER update_competitive_pricing_chat_agents_updated_at 
    BEFORE UPDATE ON competitive_pricing_chat_agents 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Optional: Create a view for easier session querying
CREATE OR REPLACE VIEW chat_session_summary AS
WITH session_stats AS (
    SELECT 
        session_id,
        user_id,
        COUNT(*) as message_count,
        MIN(created_at) as created_at,
        MAX(created_at) as last_message_at,
        FIRST_VALUE(user_message) OVER (PARTITION BY session_id ORDER BY created_at) as first_user_message,
        FIRST_VALUE(ai_message) OVER (PARTITION BY session_id ORDER BY created_at) as first_ai_message,
        LAST_VALUE(user_message) OVER (PARTITION BY session_id ORDER BY created_at 
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as last_user_message,
        LAST_VALUE(ai_message) OVER (PARTITION BY session_id ORDER BY created_at 
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as last_ai_message
    FROM competitive_pricing_chat_memory
    GROUP BY session_id, user_id, user_message, ai_message, created_at
)
SELECT DISTINCT
    session_id,
    user_id,
    created_at,
    last_message_at,
    message_count,
    first_user_message,
    first_ai_message,
    last_user_message,
    last_ai_message
FROM session_stats;

-- Grant necessary permissions (adjust the user as needed)
-- GRANT ALL ON competitive_pricing_chat_memory TO your_app_user;
-- GRANT ALL ON competitive_pricing_chat_agents TO your_app_user;
-- GRANT SELECT ON chat_session_summary TO your_app_user;
-- GRANT USAGE ON SEQUENCE competitive_pricing_chat_memory_id_seq TO your_app_user;
-- GRANT USAGE ON SEQUENCE competitive_pricing_chat_agents_id_seq TO your_app_user;