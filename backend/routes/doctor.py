"""
routes/doctor.py — Doctor dashboard endpoints
POST /api/doctor/report  — doctor asks a natural language question
POST /api/doctor/report/send — trigger report + send to Slack
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db
from models.schemas import ReportRequest, ReportResponse
from models.auth_utils import get_current_user
from agent.orchestrator import run_doctor_agent

router = APIRouter()


async def require_doctor(current_user: dict = Depends(get_current_user)):
    from fastapi import HTTPException
    if current_user.get("role") != "doctor":
        raise HTTPException(status_code=403, detail="Doctors only")
    return current_user


@router.post("/report", response_model=ReportResponse)
async def doctor_report(
    payload: ReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_doctor),
):
    """
    Doctor asks: "How many patients visited yesterday?"
    Agent queries DB and returns a human-readable summary.
    """
    from models.orm import PromptHistory

    user_id = current_user["sub"]

    # Save to history
    db.add(PromptHistory(session_id=payload.session_id, user_id=user_id, role="user", content=payload.message))
    await db.flush()

    report = await run_doctor_agent(
        message=payload.message,
        session_id=payload.session_id,
        doctor_user_id=user_id,
        db=db,
    )

    db.add(PromptHistory(session_id=payload.session_id, user_id=user_id, role="assistant", content=report))
    await db.commit()

    return ReportResponse(report=report, session_id=payload.session_id)


@router.post("/report/send-slack")
async def send_report_to_slack(
    payload: ReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_doctor),
):
    """Button-triggered: generate report AND push it to Slack directly (not via LLM)"""
    from models.orm import User, PromptHistory
    from sqlalchemy import select
    from mcp_server.tools.slack_tool import send_slack_direct

    user_id = current_user["sub"]

    # Fetch doctor's name for the Slack message header
    user_row = await db.scalar(select(User).where(User.id == user_id))
    doctor_name = user_row.name if user_row else "Doctor"

    # Save user message to history
    db.add(PromptHistory(session_id=payload.session_id, user_id=user_id, role="user", content=payload.message))
    await db.flush()

    # Generate report using the regular agent (no LLM slack instruction needed)
    report = await run_doctor_agent(
        message=payload.message,
        session_id=payload.session_id,
        doctor_user_id=user_id,
        db=db,
        send_to_slack=False,
    )

    # Save assistant response to history
    db.add(PromptHistory(session_id=payload.session_id, user_id=user_id, role="assistant", content=report))
    await db.commit()

    # Directly send to Slack — guaranteed, no LLM involvement
    slack_result = await send_slack_direct(doctor_name=doctor_name, report_text=report)
    print(f"[Slack] {slack_result}")

    return {"status": "sent", "report": report, "slack": slack_result}
