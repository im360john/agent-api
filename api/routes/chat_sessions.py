"""Chat session management endpoints"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from db.session import db_url
from agno.storage.agent.postgres import PostgresAgentStorage

# Create router
sessions_router = APIRouter(prefix="/chat/sessions", tags=["Chat Sessions"])

# Database setup for custom queries
engine = create_engine(db_url.replace('+asyncpg', '').replace('+aiopg', ''))
Session = sessionmaker(bind=engine)

# Agent storage for session management
agent_storage = PostgresAgentStorage(
    table_name="competitive_pricing_chat_agents",
    db_url=db_url
)


class SessionInfo(BaseModel):
    session_id: str
    user_id: str
    created_at: datetime
    last_message_at: Optional[datetime]
    message_count: int
    first_message: Optional[str]
    last_message: Optional[str]


class SessionMessage(BaseModel):
    role: str
    content: str
    created_at: datetime


class CreateSessionRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    initial_message: Optional[str] = None


@sessions_router.get("/", response_model=List[SessionInfo])
async def list_user_sessions(
    user_id: str = Query(..., description="User ID to get sessions for"),
    limit: int = Query(20, description="Maximum number of sessions to return"),
    offset: int = Query(0, description="Offset for pagination")
) -> List[SessionInfo]:
    """
    List all sessions for a user using agno's storage.
    """
    try:
        # Get sessions from agno's storage
        agent_sessions = agent_storage.get_all_sessions(
            user_id=user_id,
            limit=limit
        )
        
        # Convert agent sessions to our SessionInfo format
        session_infos = []
        
        for agent_session in agent_sessions:
            # Get message count and content from memory table
            with Session() as db_session:
                query = text("""
                    SELECT 
                        COUNT(*) as message_count,
                        MIN(created_at) as created_at,
                        MAX(created_at) as last_message_at,
                        FIRST_VALUE(ai_message) OVER (ORDER BY created_at) as first_message,
                        LAST_VALUE(ai_message) OVER (ORDER BY created_at 
                            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as last_message
                    FROM competitive_pricing_chat_memory
                    WHERE user_id = :user_id AND session_id = :session_id
                    GROUP BY ai_message, created_at
                    LIMIT 1
                """)
                
                result = db_session.execute(query, {
                    "user_id": user_id,
                    "session_id": agent_session.session_id
                })
                
                row = result.first()
                if row:
                    session_infos.append(SessionInfo(
                        session_id=agent_session.session_id,
                        user_id=user_id,
                        created_at=row.created_at or agent_session.created_at,
                        last_message_at=row.last_message_at or agent_session.updated_at,
                        message_count=row.message_count or 0,
                        first_message=row.first_message,
                        last_message=row.last_message
                    ))
                else:
                    # No messages yet, use agent session data
                    session_infos.append(SessionInfo(
                        session_id=agent_session.session_id,
                        user_id=user_id,
                        created_at=agent_session.created_at,
                        last_message_at=agent_session.updated_at,
                        message_count=0,
                        first_message=None,
                        last_message=None
                    ))
        
        return session_infos
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving sessions: {str(e)}")


@sessions_router.get("/{session_id}/messages", response_model=List[SessionMessage])
async def get_session_messages(
    session_id: str,
    user_id: str = Query(..., description="User ID for authorization")
) -> List[SessionMessage]:
    """
    Get all messages from a specific session.
    """
    try:
        with Session() as session:
            # Get messages for this session
            query = text("""
                SELECT 
                    user_message,
                    ai_message,
                    created_at
                FROM competitive_pricing_chat_memory
                WHERE session_id = :session_id AND user_id = :user_id
                ORDER BY created_at ASC
            """)
            
            result = session.execute(query, {
                "session_id": session_id,
                "user_id": user_id
            })
            
            messages = []
            for row in result:
                # Add user message
                if row[0]:
                    try:
                        user_msg = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                        content = user_msg.get('content', str(user_msg)) if isinstance(user_msg, dict) else str(user_msg)
                        messages.append(SessionMessage(
                            role="user",
                            content=content,
                            created_at=row[2]
                        ))
                    except:
                        messages.append(SessionMessage(
                            role="user",
                            content=str(row[0]),
                            created_at=row[2]
                        ))
                
                # Add AI message
                if row[1]:
                    try:
                        ai_msg = json.loads(row[1]) if isinstance(row[1], str) else row[1]
                        content = ai_msg.get('content', str(ai_msg)) if isinstance(ai_msg, dict) else str(ai_msg)
                        messages.append(SessionMessage(
                            role="assistant",
                            content=content,
                            created_at=row[2]
                        ))
                    except:
                        messages.append(SessionMessage(
                            role="assistant",
                            content=str(row[1]),
                            created_at=row[2]
                        ))
            
            return messages
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving messages: {str(e)}")


@sessions_router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    user_id: str = Query(..., description="User ID for authorization")
) -> Dict[str, str]:
    """
    Delete a specific session and all its messages.
    """
    try:
        with Session() as session:
            # First check if the session belongs to the user
            check_query = text("""
                SELECT COUNT(*) FROM competitive_pricing_chat_memory
                WHERE session_id = :session_id AND user_id = :user_id
            """)
            
            result = session.execute(check_query, {
                "session_id": session_id,
                "user_id": user_id
            })
            
            count = result.scalar()
            if count == 0:
                raise HTTPException(status_code=404, detail="Session not found or unauthorized")
            
            # Delete the session
            delete_query = text("""
                DELETE FROM competitive_pricing_chat_memory
                WHERE session_id = :session_id AND user_id = :user_id
            """)
            
            session.execute(delete_query, {
                "session_id": session_id,
                "user_id": user_id
            })
            
            session.commit()
            
            return {"message": f"Session {session_id} deleted successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting session: {str(e)}")


@sessions_router.post("/", response_model=Dict[str, str])
async def create_session(request: CreateSessionRequest) -> Dict[str, str]:
    """
    Create a new chat session.
    """
    import uuid
    
    session_id = request.session_id or str(uuid.uuid4())
    
    # If there's an initial message, we could store it, but the memory
    # will be created automatically when the first agent interaction happens
    
    return {
        "session_id": session_id,
        "user_id": request.user_id,
        "message": "Session created successfully"
    }


@sessions_router.delete("/user/{user_id}/all")
async def delete_all_user_sessions(user_id: str) -> Dict[str, Any]:
    """
    Delete all sessions for a user.
    """
    try:
        with Session() as session:
            # Get count first
            count_query = text("""
                SELECT COUNT(DISTINCT session_id) 
                FROM competitive_pricing_chat_memory
                WHERE user_id = :user_id
            """)
            
            result = session.execute(count_query, {"user_id": user_id})
            session_count = result.scalar()
            
            # Delete all sessions
            delete_query = text("""
                DELETE FROM competitive_pricing_chat_memory
                WHERE user_id = :user_id
            """)
            
            session.execute(delete_query, {"user_id": user_id})
            session.commit()
            
            return {
                "message": f"All sessions deleted successfully",
                "sessions_deleted": session_count
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting sessions: {str(e)}")