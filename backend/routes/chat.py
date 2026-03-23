"""
routes/chat.py — Patient chat endpoint
POST /api/chat/  — patient sends a message, agent responds
GET  /api/chat/history/{session_id} — fetch conversation history
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, asc

from models.database import get_db
from models.orm import PromptHistory
from models.schemas import ChatRequest, ChatResponse
from models.auth_utils import get_current_user
from agent.orchestrator import run_patient_agent

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Main chat endpoint.
    1. Saves the user's message to prompt_history
    2. Runs the MCP agent
    3. Saves the assistant's reply
    4. Returns the reply
    """
    user_id = current_user["sub"]

    # Save user message
    db.add(PromptHistory(session_id=payload.session_id, user_id=user_id, role="user", content=payload.message))
    await db.flush()

    # Run the agent (this is where MCP magic happens)
    reply = await run_patient_agent(
        message=payload.message,
        session_id=payload.session_id,
        user_id=user_id,
        db=db,
    )

    # Save assistant reply
    db.add(PromptHistory(session_id=payload.session_id, user_id=user_id, role="assistant", content=reply))
    await db.commit()

    return ChatResponse(reply=reply, session_id=payload.session_id)


@router.get("/history/{session_id}")
async def get_history(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Returns all messages in a conversation — for the sidebar history panel"""
    rows = await db.scalars(
        select(PromptHistory)
        .where(PromptHistory.session_id == session_id)
        .order_by(asc(PromptHistory.created_at))
    )
    return [{"role": r.role, "content": r.content, "time": r.created_at} for r in rows]


@router.get("/sessions")
async def get_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Returns a list of all past session IDs for the user — for the history sidebar"""
    rows = await db.execute(
        select(PromptHistory.session_id, PromptHistory.content, PromptHistory.created_at)
        .where(
            PromptHistory.user_id == current_user["sub"],
            PromptHistory.role == "user",
        )
        .distinct(PromptHistory.session_id)
        .order_by(PromptHistory.session_id, PromptHistory.created_at)
    )
    # Return first user message of each session as the "title"
    seen = {}
    for session_id, content, ts in rows:
        if session_id not in seen:
            seen[session_id] = {"session_id": session_id, "preview": content[:60], "time": ts}
    return list(seen.values())
