#!/usr/bin/env python3
"""
Simple test of image evaluator without database dependencies
"""
import os
import asyncio
from dotenv import load_dotenv
from textwrap import dedent

# Load environment variables
load_dotenv()

# Import required components
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.toolkit import Toolkit
import json
import time
from datetime import datetime
import aiohttp
import io

class SimpleImageTools(Toolkit):
    """Simplified image evaluation tools"""
    
    def __init__(self):
        super().__init__(name="simple_image_tools")
        self.register(self.evaluate_image)
    
    async def evaluate_image(self, image_url: str) -> str:
        """Simple image evaluation"""
        try:
            # Download image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        return json.dumps({"error": f"HTTP {response.status}"})
                    
                    image_data = await response.read()
                    
                    # Basic evaluation
                    result = {
                        "image_url": image_url,
                        "size_bytes": len(image_data),
                        "evaluation": {
                            "quality": "Good" if len(image_data) > 50000 else "Low",
                            "size_assessment": "Large" if len(image_data) > 100000 else "Small"
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    return json.dumps(result, indent=2)
                    
        except Exception as e:
            return json.dumps({"error": str(e)})

async def test_simple_image_agent():
    """Test a simple image agent"""
    print("Testing Simple Image Agent")
    print("=" * 50)
    
    # Create agent
    agent = Agent(
        name="Simple Image Agent",
        model=OpenAIChat(id="gpt-4o-mini"),
        tools=[SimpleImageTools()],
        description="A simple image evaluation agent",
        instructions=dedent("""
            You are a helpful image evaluation assistant.
            Use the evaluate_image tool to analyze images.
            Provide clear feedback about the image.
        """),
        markdown=True,
        debug_mode=True,
        # No database dependencies
        storage=None,
        memory=None,
        add_history_to_messages=False,
    )
    
    # Test query
    query = "Please evaluate this image: https://picsum.photos/800/600"
    print(f"\nQuery: {query}")
    print("-" * 50)
    
    try:
        response = await agent.arun(query)
        print(f"\nResponse:\n{response.content}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

def main():
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set")
        return
    
    asyncio.run(test_simple_image_agent())

if __name__ == "__main__":
    main()