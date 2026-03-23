"""
agent/orchestrator.py — The MCP Client + LLM Agent Loop

This is where the magic happens. This code:
1. Connects to the MCP server (as an MCP Client)
2. Calls tools/list to DYNAMICALLY discover all available tools
3. Passes tools + user message to Groq (LLM)
4. LLM decides which tools to call
5. We execute the tools via the MCP server
6. Feed results back to LLM
7. LLM forms final human-readable answer

This loop continues until the LLM says "I'm done" (no more tool calls).
That's the agentic loop.
"""
import json
import os
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, asc

from mcp import ClientSession
from mcp.client.sse import sse_client
from groq import AsyncGroq
from dotenv import load_dotenv

from models.orm import PromptHistory

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001/sse")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

groq_client = AsyncGroq(api_key=GROQ_API_KEY)


async def _load_history(session_id: str, db: AsyncSession) -> list[dict]:
    """Load past messages for this session to maintain context (multi-turn)"""
    rows = await db.scalars(
        select(PromptHistory)
        .where(PromptHistory.session_id == session_id)
        .order_by(asc(PromptHistory.created_at))
        .limit(20)   # last 20 messages keeps context without blowing token limit
    )
    return [{"role": r.role, "content": r.content} for r in rows]


async def _run_agent(
    system_prompt: str,
    user_message: str,
    session_id: str,
    db: AsyncSession,
    extra_context: dict = None,
) -> str:
    """
    Core agentic loop using MCP + Groq.
    Works for both patient and doctor scenarios.
    """
    # ── Step 1: Connect to MCP server and discover tools dynamically ──────────
    async with sse_client(MCP_SERVER_URL) as (read, write):
        async with ClientSession(read, write) as mcp_session:
            await mcp_session.initialize()  # handshake with MCP server

            # tools/list — LLM will use these descriptions to decide what to call
            tools_result = await mcp_session.list_tools()

            # Convert MCP tool format → Groq/OpenAI tool format
            groq_tools = []
            for tool in tools_result.tools:
                groq_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                    },
                })

            # ── Step 2: Build message history for multi-turn context ──────────
            history = await _load_history(session_id, db)

            # Inject extra context (e.g., patient's user_id) into system prompt
            full_system = system_prompt
            if extra_context:
                ctx_str = "\n".join(f"{k}: {v}" for k, v in extra_context.items())
                full_system += f"\n\nContext for this session:\n{ctx_str}"

            messages = [{"role": "system", "content": full_system}]
            messages.extend(history)
            messages.append({"role": "user", "content": user_message})

            # ── Step 3: Agentic loop ──────────────────────────────────────────
            # We loop because the LLM might call multiple tools in sequence
            # e.g., check_availability → book_appointment → send_email
            max_iterations = 10  # safety limit
            last_tool_results = []  # track completed tool calls for graceful fallback

            for _ in range(max_iterations):
                try:
                    response = await groq_client.chat.completions.create(
                        model=GROQ_MODEL,
                        messages=messages,
                        tools=groq_tools,
                        tool_choice="auto",  # LLM decides — no hardcoding
                        temperature=0.1,     # low temp = consistent, predictable tool calls
                        max_tokens=4096,
                    )
                except Exception as groq_err:
                    # If tools already ran, return their results gracefully instead of crashing
                    if last_tool_results:
                        summaries = [f"{name}: {res[:300]}" for name, res in last_tool_results]
                        return "Done. " + " | ".join(summaries)
                    raise

                msg = response.choices[0].message

                # If no tool calls → LLM is done, return the final answer
                if not msg.tool_calls:
                    return msg.content or "Done."

                # ── Step 4: Execute each tool call via MCP server ─────────────
                # Add LLM's decision to message history
                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })

                # Execute each tool and collect results
                last_tool_results = []
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    print(f"[Agent] Calling tool: {tool_name} with {tool_args}")

                    # ← This goes through MCP protocol (tools/call), not direct fn call
                    tool_result = await mcp_session.call_tool(tool_name, tool_args)
                    result_text = tool_result.content[0].text if tool_result.content else "No result"
                    last_tool_results.append((tool_name, result_text))

                    # Add tool result back into message history
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_text,
                    })

            return "I was unable to complete the request after multiple attempts."


# ── Public API — called by routes ────────────────────────────────────────────

async def run_patient_agent(
    message: str,
    session_id: str,
    user_id: str,
    db: AsyncSession,
) -> str:
    """Patient scenario: appointment booking and availability checking"""
    system_prompt = """You are a helpful medical appointment assistant for DOBBE Health.

Your job is to help patients book appointments, check doctor availability, and manage their appointments.

CRITICAL RULES — FOLLOW EXACTLY:
1. DOCTOR NAME: Always use the EXACT doctor name the patient specifies. Never substitute or hallucinate. If they say 'Dr. Sharma', only use Dr. Priya Sharma. NEVER make up or guess a doctor's specialization — always get it from list_doctors or check_availability tool results.

2. CONTEXT: Remember the entire conversation. If the patient already mentioned a doctor earlier in the chat, do NOT ask again which doctor — use that doctor.

3. NEVER AUTO-BOOK: Only call book_appointment when the patient EXPLICITLY says 'book', 'schedule', 'confirm', or 'yes'. Never book just because they asked about availability.

4. CONFIRM BEFORE BOOKING: Before calling book_appointment, state the exact details (doctor, date, time) and ask 'Shall I confirm this booking?' — only book after the patient says yes.

5. After a confirmed booking, inform the patient the booking is done — the confirmation email is sent automatically, no need to call send_confirmation_email separately.

6. If a slot is unavailable, use find_next_available_slot to suggest alternatives.

7. To show patient's existing appointments, call get_patient_appointments with the patient_user_id from context.

8. Be warm, professional, and concise. Format dates as YYYY-MM-DD and times as HH:MM for tool calls."""

    from datetime import date
    from sqlalchemy import text as sa_text
    # Fetch patient name and email so agent can use them directly for send_confirmation_email
    row = await db.execute(sa_text("SELECT name, email FROM users WHERE id = :uid"), {"uid": user_id})
    patient_row = row.fetchone()
    patient_name = patient_row[0] if patient_row else "Patient"
    patient_email = patient_row[1] if patient_row else ""

    extra_context = {
        "patient_user_id": user_id,
        "patient_name": patient_name,
        "patient_email": patient_email,
        "today_date": date.today().isoformat(),
        "today_day": date.today().strftime("%A"),
    }

    return await _run_agent(
        system_prompt=system_prompt,
        user_message=message,
        session_id=session_id,
        db=db,
        extra_context=extra_context,
    )


async def run_doctor_agent(
    message: str,
    session_id: str,
    doctor_user_id: str,
    db: AsyncSession,
    send_to_slack: bool = False,
) -> str:
    """Doctor scenario: appointment stats and reporting"""
    system_prompt = f"""You are an intelligent medical reporting assistant for DOBBE Health.

Your job is to provide doctors with clear, accurate summaries of their appointments and patient statistics.

IMPORTANT RULES:
- Use get_appointment_stats for count/schedule queries
- Use get_appointments_by_symptom when asked about specific conditions or symptoms
- Always present data in a clean, readable format
- {"After generating the report, ALWAYS call send_slack_report to notify via Slack." if send_to_slack else "Only send to Slack if the doctor explicitly asks."}
- Today's date is available in context

Be professional, concise, and data-driven."""

    from datetime import date
    extra_context = {
        "doctor_user_id": doctor_user_id,
        "today_date": date.today().isoformat(),
        "today_day": date.today().strftime("%A"),
    }

    return await _run_agent(
        system_prompt=system_prompt,
        user_message=message,
        session_id=session_id,
        db=db,
        extra_context=extra_context,
    )
