from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
import os
import json
import logging
from typing import Optional
from agents.slack_treez_agent import get_slack_treez_agent, SlackTreezBot, seed_knowledge_base
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize the bot once at module level
_bot_instance: Optional[SlackTreezBot] = None

def get_slack_bot() -> SlackTreezBot:
    """Get or create the Slack bot instance"""
    global _bot_instance
    if _bot_instance is None:
        agent = get_slack_treez_agent()
        _bot_instance = SlackTreezBot(agent)
    return _bot_instance

@router.post("/slack/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    """
    Handle Slack Events API webhook
    
    This endpoint receives events from Slack including:
    - URL verification challenges
    - App mention events
    - Message events (if subscribed)
    """
    try:
        body = await request.json()
        
        # Handle URL verification challenge from Slack
        if "challenge" in body:
            return JSONResponse(content={"challenge": body["challenge"]})
        
        # Verify the request is from Slack (optional but recommended)
        slack_signature = request.headers.get("X-Slack-Signature")
        slack_timestamp = request.headers.get("X-Slack-Request-Timestamp")
        
        # TODO: Implement request verification using SLACK_SIGNING_SECRET
        # This is important for production to ensure requests are from Slack
        
        # Handle events
        if "event" in body:
            event = body["event"]
            event_type = event.get("type")
            
            # Process app mentions in the background
            if event_type == "app_mention":
                background_tasks.add_task(process_app_mention, event)
            
            # Add other event types as needed
            elif event_type == "message":
                # Only process direct messages or thread replies
                if event.get("channel_type") == "im" or event.get("thread_ts"):
                    background_tasks.add_task(process_message, event)
        
        # Always return 200 OK quickly to avoid Slack retries
        return JSONResponse(content={"status": "ok"})
    
    except Exception as e:
        logger.error(f"Error processing Slack event: {str(e)}")
        # Still return 200 to prevent Slack retries on error
        return JSONResponse(content={"status": "ok"})

async def process_app_mention(event: dict):
    """Process app mention events"""
    try:
        bot = get_slack_bot()
        channel = event.get("channel")
        thread_ts = event.get("ts")
        
        # Get response from agent
        response = await bot.process_mention(event)
        
        if response and channel:
            # Send response in thread
            await bot.send_response(channel, response, thread_ts)
    
    except Exception as e:
        logger.error(f"Error processing app mention: {str(e)}")
        # Try to send error message to user
        try:
            bot = get_slack_bot()
            channel = event.get("channel")
            thread_ts = event.get("ts")
            if channel:
                await bot.send_response(
                    channel, 
                    "I apologize, but I encountered an error processing your request. Please try again or contact support.",
                    thread_ts
                )
        except:
            pass

async def process_message(event: dict):
    """Process direct messages"""
    # Similar to app mention but for DMs
    await process_app_mention(event)

@router.post("/slack/slash-commands/treez")
async def treez_slash_command(request: Request):
    """
    Handle /treez slash command
    
    Example usage in Slack:
    /treez how do I process a return?
    /treez what are the keyboard shortcuts?
    """
    try:
        form_data = await request.form()
        
        # Extract slash command data
        team_id = form_data.get("team_id")
        channel_id = form_data.get("channel_id")
        user_id = form_data.get("user_id")
        command = form_data.get("command")
        text = form_data.get("text", "").strip()
        response_url = form_data.get("response_url")
        
        if not text:
            return JSONResponse(content={
                "response_type": "ephemeral",
                "text": "Please provide a question. Usage: `/treez <your question>`"
            })
        
        # Process in background and return immediate response
        asyncio.create_task(process_slash_command(text, response_url, user_id))
        
        return JSONResponse(content={
            "response_type": "ephemeral",
            "text": "🔍 Looking up your Treez question..."
        })
    
    except Exception as e:
        logger.error(f"Error processing slash command: {str(e)}")
        return JSONResponse(content={
            "response_type": "ephemeral",
            "text": "Sorry, I encountered an error processing your request."
        })

async def process_slash_command(text: str, response_url: str, user_id: str):
    """Process slash command in background"""
    try:
        bot = get_slack_bot()
        
        # Create a mock event for the agent
        mock_event = {
            "text": text,
            "user": user_id
        }
        
        response = await bot.process_mention(mock_event)
        
        # Send response using response_url
        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(response_url, json={
                "response_type": "in_channel",
                "text": response
            })
    
    except Exception as e:
        logger.error(f"Error in background slash command processing: {str(e)}")

@router.post("/slack/knowledge/update")
async def update_knowledge_base():
    """
    Update the Treez knowledge base with latest documentation
    
    This endpoint can be called periodically to refresh the agent's knowledge
    """
    try:
        bot = get_slack_bot()
        results = await bot.update_knowledge_base()
        
        return JSONResponse(content={
            "status": "success",
            "message": f"Updated {results['updated']} documents, {results['failed']} failed",
            "details": results
        })
    
    except Exception as e:
        logger.error(f"Error updating knowledge base: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/slack/knowledge/seed")
async def seed_knowledge():
    """
    Seed the knowledge base with initial Treez documentation
    
    This should be called once during initial setup
    """
    try:
        bot = get_slack_bot()
        success = await seed_knowledge_base(bot.agent)
        
        if success:
            return JSONResponse(content={
                "status": "success",
                "message": "Knowledge base seeded with initial content"
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to seed knowledge base")
    
    except Exception as e:
        logger.error(f"Error seeding knowledge base: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/slack/status")
async def slack_status():
    """Check Slack bot status and configuration"""
    return {
        "status": "healthy",
        "slack_token_configured": bool(os.getenv("SLACK_BOT_TOKEN")),
        "firecrawl_configured": bool(os.getenv("FIRECRAWL_API_KEY")),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "bot_initialized": _bot_instance is not None
    }