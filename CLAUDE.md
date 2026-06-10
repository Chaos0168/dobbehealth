# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DOBBE AI is an agentic doctor-appointment assistant built around **MCP (Model Context Protocol)**. A FastAPI backend exposes business logic as MCP tools via a separate MCP server process; a Groq-hosted LLM (Llama 4 Scout) dynamically discovers and calls those tools to handle two scenarios: patient appointment booking (with Google Calendar + email confirmation) and doctor reporting (with Slack notifications).

**Core architectural principle**: there is no hardcoded `if/else` tool routing. The agent loop in `backend/agent/orchestrator.py` calls `tools/list` on the MCP server to get tool descriptions/schemas, hands them to Groq with `tool_choice="auto"`, and executes whatever the LLM decides via `tools/call`. When adding a new capability, add an MCP tool (with a clear docstring/description — the LLM relies on it) rather than adding branching logic to the orchestrator.

## Running the stack

### One-command startup (everything)
```bash
./start.sh
```
This starts Postgres+pgAdmin (Docker), the MCP server (port 8001), FastAPI (port 8000), and the Vite dev server (port 3000).

### Manual / per-service startup
```bash
# 1. Database
docker compose up -d                      # Postgres on :5432, pgAdmin on :5050

# 2. Backend venv (from backend/)
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. One-time Google Calendar OAuth (from backend/, venv active)
python services/auth_calendar.py          # opens browser, writes google_token.json

# 4. MCP server (Terminal 1, from backend/, venv active)
python -m mcp_server.server               # SSE transport on :8001

# 5. FastAPI (Terminal 2, from backend/, venv active)
uvicorn main:app --reload --port 8000     # Swagger at /docs

# 6. Frontend
cd frontend && npm install && npm run dev -- --port 3000
```

The MCP server **must be running** before/while the FastAPI backend handles chat or report requests — the orchestrator connects to it via SSE at `MCP_SERVER_URL` (default `http://localhost:8001/sse`) on every agent invocation.

### Environment

`backend/.env` (copy from `backend/.env.example`) requires: `DATABASE_URL`, `JWT_SECRET_KEY`, `GROQ_API_KEY`, `MCP_SERVER_URL`, Google Calendar credential paths, `RESEND_API_KEY`/`FROM_EMAIL`, `SLACK_BOT_TOKEN`/`SLACK_CHANNEL_ID`. Settings are loaded once via `backend/config.py` (`pydantic_settings.BaseSettings`) — import `settings` from there rather than re-reading env vars.

### Frontend commands
```bash
cd frontend
npm run dev       # Vite dev server
npm run build     # production build
npm run lint      # eslint
```

### Sample logins (seeded via database/seed.sql)
- Patient: `tript@patient.com` / `password123`
- Doctor: `dr.ahuja@hospital.com` / `password123`

## Architecture

```
React Frontend (port 3000)
      │
      ▼
FastAPI Backend (port 8000)
      │
      ├── MCP Client (agent/orchestrator.py)
      │        │  tools/list — discovers tools dynamically at runtime
      │        │  tools/call — executes tools via MCP protocol
      │        ▼
      │   MCP Server (port 8001, SSE transport)
      │        ├── check_availability / list_doctors        → PostgreSQL
      │        ├── book_appointment / cancel_appointment     → PostgreSQL + Google Calendar
      │        ├── send_confirmation_email                   → Resend API
      │        ├── get_appointment_stats / get_appointments_by_symptom → PostgreSQL
      │        ├── send_slack_report                         → Slack Block Kit API
      │        └── find_next_available_slot / reschedule_appointment → PostgreSQL
      │
      └── Groq API — Llama 4 Scout 17B — drives all tool orchestration
```

### Backend layout (`backend/`)
- `main.py` — FastAPI app, CORS (allows `localhost:3000`/`5173`), registers routers under `/api/auth`, `/api/chat`, `/api/doctor`.
- `config.py` — single `Settings` instance, import `settings` from here.
- `agent/orchestrator.py` — the agentic loop (`_run_agent`). Connects to MCP via SSE, builds the tool list, loads multi-turn history from `prompt_history`, loops up to 10 iterations executing tool calls until the LLM returns a final answer. Two public entry points: `run_patient_agent` and `run_doctor_agent`, each with their own system prompt and injected context (patient/doctor IDs, today's date, etc.). **System prompts here encode the business rules** (e.g., never auto-book without explicit confirmation, never hallucinate doctor specializations) — when changing agent behavior, edit these prompts.
- `mcp_server/server.py` — standalone MCP server process (FastMCP, SSE on :8001). Each tool module under `mcp_server/tools/` has a `register(mcp)` function called at startup; this is where new tools get registered.
  - `tools/availability.py` — `list_doctors`, `check_availability`
  - `tools/booking.py` — `book_appointment`, `cancel_appointment` (also touches Google Calendar)
  - `tools/stats.py` — `get_appointment_stats`, `get_appointments_by_symptom`
  - `tools/email_tool.py` — `send_confirmation_email` (Resend)
  - `tools/slack_tool.py` — `send_slack_report` (LLM-invoked) and `send_slack_direct` (called directly from `routes/doctor.py`, bypassing the LLM, for the "guaranteed delivery" dashboard button)
  - `tools/reschedule.py` — `find_next_available_slot`, `reschedule_appointment`
- `routes/` — thin FastAPI routers (`auth.py`, `chat.py`, `doctor.py`) that handle JWT auth, persist `prompt_history` rows, and delegate to `agent/orchestrator.py`. `routes/doctor.py` has a `require_doctor` dependency gating doctor-only endpoints.
- `models/` — `database.py` (async SQLAlchemy engine/session, `get_db` dependency, declarative `Base`), `orm.py` (User, Doctor, AvailabilitySlot, Appointment, PromptHistory — mirrors `database/schema.sql`), `schemas.py` (Pydantic request/response models), `auth_utils.py` (JWT encode/decode, bcrypt, `get_current_user` dependency).
- `services/gcalendar.py` — Google Calendar event create/delete; `services/auth_calendar.py` — one-time OAuth2 script that produces `google_token.json`.

### Database (`database/schema.sql`, `database/seed.sql`)
Five tables: `users` (patients & doctors, role-discriminated), `doctors` (specialization, calendar/Slack IDs, FK to `users`), `availability_slots` (weekly recurring schedule per doctor), `appointments` (core booking record incl. `google_event_id`, `email_sent`, `status` enum), `prompt_history` (multi-turn chat log keyed by `session_id`, used to reconstruct conversation context for the agent loop). All tables use UUID primary keys (`uuid_generate_v4()`).

### Frontend layout (`frontend/src/`)
- `App.jsx` — router + protected routes (role-based: patients → chat, doctors → dashboard).
- `api.js` — Axios client with JWT interceptor.
- `context/AuthContext.jsx` — auth/session state.
- `pages/Login.jsx`, `Register.jsx` — auth flows.
- `pages/PatientChat.jsx` — chat UI + session history sidebar (Scenario 1).
- `pages/DoctorDashboard.jsx` — natural-language report UI + quick-query buttons + Slack send button (Scenario 2).

## Key conventions

- **Multi-turn context** comes entirely from `prompt_history` rows for a given `session_id` (last 20 messages), reloaded on every agent call — there is no in-memory session state.
- **Booking confirmation flow**: the patient agent must restate booking details and get explicit confirmation before calling `book_appointment` (enforced via system prompt, not code).
- **Slack delivery has two paths**: LLM-mediated (`send_slack_report` tool, used when the doctor asks in natural language) vs. direct (`send_slack_direct`, used by the dashboard button in `routes/doctor.py` for guaranteed delivery independent of LLM behavior).
- When adding a new MCP tool, write a precise docstring/description — it is the only thing the LLM sees to decide when/how to call it.
