"""
Chat API router — Omni-Intelligence Bot endpoints.

Routes:
  POST   /chat/sessions               — create a new session
  GET    /chat/sessions               — list recent sessions (newest first)
  GET    /chat/sessions/{session_id}  — get session + full message history
  POST   /chat/sessions/{session_id}/messages — send a message (SSE stream)
  DELETE /chat/sessions/{session_id}  — delete session + all messages
"""

from __future__ import annotations

import uuid
import json
import asyncio
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from intelligence_api.core.database import get_db
from intelligence_api.domain.models import ConversationSession, ConversationMessage
from intelligence_api.application.chat_service import ChatService

logger = logging.getLogger(__name__)

chat_router = APIRouter(prefix="/chat", tags=["chat"])


# ── Pydantic schemas ───────────────────────────────────────────────────────────

class SessionCreateIn(BaseModel):
    title: Optional[str] = None
    entity_focus: Optional[str] = None


class MessageIn(BaseModel):
    content: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: Optional[str]
    tool_name: Optional[str]
    tool_args: Optional[dict]
    tool_result: Optional[dict]
    metadata_json: Optional[dict]
    created_at: str


class SessionOut(BaseModel):
    id: str
    title: Optional[str]
    entity_focus: Optional[str]
    created_at: str
    updated_at: str
    message_count: Optional[int] = None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _session_out(session: ConversationSession, message_count: int = 0) -> dict:
    return {
        "id": str(session.id),
        "title": session.title,
        "entity_focus": session.entity_focus,
        "created_at": session.created_at.isoformat() if session.created_at else "",
        "updated_at": session.updated_at.isoformat() if session.updated_at else "",
        "message_count": message_count,
    }


def _message_out(msg: ConversationMessage) -> dict:
    return {
        "id": str(msg.id),
        "role": msg.role,
        "content": msg.content,
        "tool_name": msg.tool_name,
        "tool_call_id": msg.tool_call_id,
        "tool_args": msg.tool_args,
        "tool_result": msg.tool_result,
        "metadata_json": msg.metadata_json,
        "created_at": msg.created_at.isoformat() if msg.created_at else "",
    }


# ── Endpoints ──────────────────────────────────────────────────────────────────

@chat_router.post("/sessions", status_code=201)
def create_session(body: SessionCreateIn, db: Session = Depends(get_db)):
    """Create a new conversation session."""
    session = ConversationSession(
        title=body.title,
        entity_focus=body.entity_focus,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _session_out(session)


@chat_router.get("/sessions")
def list_sessions(limit: int = 20, db: Session = Depends(get_db)):
    """List the most recent conversation sessions."""
    from sqlalchemy import func as sa_func

    rows = (
        db.query(
            ConversationSession,
            sa_func.count(ConversationMessage.id).label("message_count"),
        )
        .outerjoin(
            ConversationMessage,
            ConversationMessage.session_id == ConversationSession.id,
        )
        .group_by(ConversationSession.id)
        .order_by(ConversationSession.updated_at.desc())
        .limit(limit)
        .all()
    )
    return [_session_out(s, count) for s, count in rows]


@chat_router.get("/sessions/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db)):
    """Retrieve a session along with its full message history."""
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session_id")

    session = db.query(ConversationSession).filter(ConversationSession.id == sid).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.session_id == sid)
        .order_by(ConversationMessage.created_at.asc())
        .all()
    )
    return {
        **_session_out(session, len(messages)),
        "messages": [_message_out(m) for m in messages],
    }


@chat_router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    body: MessageIn,
    db: Session = Depends(get_db),
):
    """
    Send a user message and receive a Server-Sent Events (SSE) stream.

    SSE event types:
      tool_start  — {"name": str, "label": str, "args": dict}
      tool_result — {"name": str, "viz": {...}, "sources": [...], "error": str|null}
      text_delta  — {"delta": str}
      done        — {"confidence": float|null, "sources": [...], "message_id": str}
      error       — {"message": str}
    """
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session_id")

    session = db.query(ConversationSession).filter(ConversationSession.id == sid).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not body.content or not body.content.strip():
        raise HTTPException(status_code=422, detail="Message content cannot be empty")

    service = ChatService(db)

    async def event_generator():
        try:
            async for chunk in service.stream_chat(sid, body.content.strip()):
                yield chunk
        except Exception as e:
            logger.exception("Unhandled error in stream_chat")
            error_event = f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
            yield error_event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@chat_router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: str, db: Session = Depends(get_db)):
    """Delete a session and all its messages (CASCADE handled by FK)."""
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session_id")

    session = db.query(ConversationSession).filter(ConversationSession.id == sid).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session)
    db.commit()


@chat_router.patch("/sessions/{session_id}/title")
def update_session_title(session_id: str, body: SessionCreateIn, db: Session = Depends(get_db)):
    """Update the session title (called after first message to auto-set a descriptive title)."""
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session_id")

    session = db.query(ConversationSession).filter(ConversationSession.id == sid).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if body.title:
        session.title = body.title
    if body.entity_focus:
        session.entity_focus = body.entity_focus
    db.commit()
    db.refresh(session)
    return _session_out(session)
