#!/usr/bin/env python3
"""
Test script to verify memory persistence in Slack Treez Agent

This script:
1. Sends messages to the agent as different users
2. Verifies memories are created and stored
3. Tests if agent remembers information across sessions
"""

import asyncio
import time
import os
import sys
import logging
from datetime import datetime
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.slack_treez_agent import get_slack_treez_agent, SlackTreezBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MemoryTester:
    def __init__(self):
        self.test_user = "memory_test_user_123"
        self.test_channel = "memory_test_channel"
        
    async def send_message(self, bot, text, user=None):
        """Send a message and get response"""
        event = {
            "text": f"<@bot> {text}",
            "user": user or self.test_user,
            "channel": self.test_channel,
            "ts": str(time.time())
        }
        
        logger.info(f"Sending: {text}")
        response = await bot.process_mention(event)
        logger.info(f"Response: {response[:200]}...")
        return response
    
    async def check_database_for_memories(self):
        """Check if memories exist in database"""
        try:
            from sqlalchemy import create_engine, text
            
            db_url = os.getenv("DATABASE_URL", "postgresql+psycopg://user:password@location/agno")
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql://", 1)
            elif db_url.startswith("postgresql+psycopg://"):
                db_url = db_url.replace("postgresql+psycopg://", "postgresql://", 1)
            
            engine = create_engine(db_url)
            
            with engine.connect() as conn:
                # Check if memory table exists
                result = conn.execute(text("""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = 'ai' 
                    AND table_name = 'slack_treez_agent_memory'
                """))
                
                if result.scalar() == 0:
                    logger.warning("Memory table does not exist yet")
                    return []
                
                # Get memory entries
                result = conn.execute(text("""
                    SELECT user_id, memory, created_at, metadata
                    FROM ai.slack_treez_agent_memory
                    WHERE user_id LIKE '%memory_test_user%'
                    ORDER BY created_at DESC
                    LIMIT 10
                """))
                
                memories = []
                for row in result:
                    memories.append({
                        "user_id": row[0],
                        "memory": row[1],
                        "created_at": str(row[2]),
                        "metadata": row[3]
                    })
                
                return memories
                
        except Exception as e:
            logger.error(f"Error checking database: {e}")
            return []
    
    async def run_memory_test(self):
        """Run the full memory test sequence"""
        print("\n" + "="*80)
        print("MEMORY PERSISTENCE TEST")
        print("="*80)
        
        # Check environment
        if not os.getenv("OPENAI_API_KEY"):
            print("ERROR: OPENAI_API_KEY required")
            return
        
        print("\n1. Creating first agent instance...")
        agent1 = get_slack_treez_agent(debug_mode=False)
        bot1 = SlackTreezBot(agent1)
        
        print(f"\nAgent configuration:")
        print(f"  - agent_id: {agent1.agent_id}")
        print(f"  - enable_agentic_memory: {agent1.enable_agentic_memory}")
        print(f"  - User: {self.test_user}")
        
        # Phase 1: Establish some facts
        print("\n2. PHASE 1: Teaching the agent about user preferences...")
        await self.send_message(bot1, 
            "Hi! I'm John and I manage three dispensaries in California. "
            "My favorite Treez feature is the inventory management system."
        )
        
        await asyncio.sleep(2)
        
        await self.send_message(bot1,
            "I'm particularly interested in the compliance reporting features "
            "because we need to stay compliant with California regulations."
        )
        
        # Check memories after phase 1
        print("\n3. Checking database for stored memories...")
        memories = await self.check_database_for_memories()
        print(f"Found {len(memories)} memory entries")
        for i, mem in enumerate(memories):
            print(f"\nMemory {i+1}:")
            print(f"  User: {mem['user_id']}")
            print(f"  Content: {mem['memory'][:100]}...")
            print(f"  Created: {mem['created_at']}")
        
        # Phase 2: Create new agent instance
        print("\n4. PHASE 2: Creating NEW agent instance (simulating restart)...")
        await asyncio.sleep(2)
        
        agent2 = get_slack_treez_agent(debug_mode=False)
        bot2 = SlackTreezBot(agent2)
        print(f"New agent created with same agent_id: {agent2.agent_id}")
        
        # Test if it remembers
        print("\n5. Testing if agent remembers previous conversation...")
        response = await self.send_message(bot2,
            "Do you remember what I told you about my dispensaries and what features I like?"
        )
        
        # Check for memory indicators
        memory_indicators = [
            "three dispensaries",
            "California",
            "inventory management",
            "compliance",
            "John"
        ]
        
        memories_found = []
        for indicator in memory_indicators:
            if indicator.lower() in response.lower():
                memories_found.append(indicator)
        
        print(f"\n6. MEMORY TEST RESULTS:")
        print(f"   Memories found in response: {memories_found}")
        print(f"   Success rate: {len(memories_found)}/{len(memory_indicators)}")
        
        if len(memories_found) >= 3:
            print("   ✅ PASS: Agent successfully remembered user information!")
        else:
            print("   ❌ FAIL: Agent did not remember enough information")
        
        # Phase 3: Test with different user
        print("\n7. PHASE 3: Testing with different user...")
        response = await self.send_message(bot2,
            "What do you know about me?",
            user="different_user_456"
        )
        
        if any(indicator.lower() in response.lower() for indicator in memory_indicators):
            print("   ❌ FAIL: Agent confused users - shared memories incorrectly")
        else:
            print("   ✅ PASS: Agent correctly separated user memories")
        
        # Final memory check
        print("\n8. Final database check...")
        final_memories = await self.check_database_for_memories()
        print(f"Total memories in database: {len(final_memories)}")
        
        print("\n" + "="*80)
        print("TEST COMPLETE")
        print("="*80)

async def main():
    tester = MemoryTester()
    await tester.run_memory_test()

if __name__ == "__main__":
    print("\nMemory Persistence Test for Slack Treez Agent")
    print("This will test if memories are properly stored and retrieved\n")
    
    asyncio.run(main())