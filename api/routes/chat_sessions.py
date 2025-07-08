"""Chat session management endpoints"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from db.session import db_url

# Create router
sessions_router = APIRouter(prefix="/chat/sessions", tags=["Chat Sessions"])

# Database setup for custom queries
engine = create_engine(db_url.replace('+asyncpg', '').replace('+aiopg', ''))
Session = sessionmaker(bind=engine)


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
    print(f"list_user_sessions called with user_id={user_id}, limit={limit}, offset={offset}")
    
    try:
        # Since get_all_sessions might not exist, query the database directly
        with Session() as db_session:
            # Get unique sessions for the user from the memory table
            query = text("""
                SELECT DISTINCT 
                    session_id,
                    user_id,
                    MIN(created_at) as created_at,
                    MAX(created_at) as last_message_at,
                    COUNT(*) as message_count
                FROM competitive_pricing_chat_memory
                WHERE user_id = :user_id
                GROUP BY session_id, user_id
                ORDER BY MAX(created_at) DESC
                LIMIT :limit
                OFFSET :offset
            """)
            
            result = db_session.execute(query, {
                "user_id": user_id,
                "limit": limit,
                "offset": offset
            })
            
            sessions = result.fetchall()
            print(f"Query returned {len(sessions)} sessions from database")
        
        # Convert to our SessionInfo format
        session_infos = []
        
        for session_row in sessions:
            session_id, user_id, created_at, last_message_at, message_count = session_row
            
            # Get first and last messages for this session
            with Session() as db_session:
                message_query = text("""
                    WITH ordered_messages AS (
                        SELECT 
                            user_message,
                            ai_message,
                            created_at,
                            ROW_NUMBER() OVER (ORDER BY created_at ASC) as rn_asc,
                            ROW_NUMBER() OVER (ORDER BY created_at DESC) as rn_desc
                        FROM competitive_pricing_chat_memory
                        WHERE user_id = :user_id AND session_id = :session_id
                    )
                    SELECT 
                        (SELECT user_message FROM ordered_messages WHERE rn_asc = 1 LIMIT 1) as first_message,
                        (SELECT ai_message FROM ordered_messages WHERE rn_desc = 1 LIMIT 1) as last_message
                """)
                
                msg_result = db_session.execute(message_query, {
                    "user_id": user_id,
                    "session_id": session_id
                })
                
                msg_row = msg_result.first()
                first_msg = None
                last_msg = None
                
                if msg_row:
                    # Parse JSON messages if needed
                    if msg_row[0]:
                        try:
                            first_data = json.loads(msg_row[0]) if isinstance(msg_row[0], str) else msg_row[0]
                            first_msg = first_data.get('content', str(first_data)) if isinstance(first_data, dict) else str(first_data)
                        except:
                            first_msg = str(msg_row[0])
                    
                    if msg_row[1]:
                        try:
                            last_data = json.loads(msg_row[1]) if isinstance(msg_row[1], str) else msg_row[1]
                            last_msg = last_data.get('content', str(last_data)) if isinstance(last_data, dict) else str(last_data)
                        except:
                            last_msg = str(msg_row[1])
                
                session_infos.append(SessionInfo(
                    session_id=session_id,
                    user_id=user_id,
                    created_at=created_at,
                    last_message_at=last_message_at,
                    message_count=message_count,
                    first_message=first_msg,
                    last_message=last_msg
                ))
        
        print(f"Returning {len(session_infos)} sessions for user {user_id}")
        for session in session_infos:
            print(f"  - Session {session.session_id}: {session.message_count} messages")
        
        return session_infos
            
    except Exception as e:
        import traceback
        print(f"Error in list_user_sessions: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
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