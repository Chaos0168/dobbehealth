# 🧠 Full-Stack Developer Intern Assignment – Agentic AI with MCP

## 📌 Overview
Build a smart **doctor appointment and reporting assistant** that uses **MCP (Model Context Protocol)** to expose APIs and tools that can be dynamically discovered and invoked by an AI agent (LLM). The solution should demonstrate **agentic behavior** — where the AI decides what tools to use, when, and how to combine them.

---

## 🎯 Objective
Build a minimal full-stack web application that integrates LLMs with backend logic using:
- **MCP** — tool/resource/prompt exposure
- **FastAPI** — backend
- **React** — frontend
- **PostgreSQL** — database
- **Google Calendar API** — appointment scheduling
- **Gmail/SendGrid/Mailgun** — email notifications
- **Slack/WhatsApp/Firebase** — doctor notifications

---

## 🧩 Scenario 1: Patient Appointment Scheduling

### Use Case
Patient types: _"I want to book an appointment with Dr. Ahuja tomorrow morning."_

### Expected Flow
1. Backend (FastAPI) exposes doctor availability from PostgreSQL **via MCP**
2. AI Agent:
   - Parses the prompt
   - Uses MCP tool to check doctor's availability
   - If available → schedules via **Google Calendar API**
   - Sends **email confirmation** to patient
   - Displays result (success/failure) in **React frontend**

---

## 🔁 Conversation Continuity (Multi-Turn Support)

Support multi-turn interactions with context:

| Turn | Patient Prompt | System Action |
|------|---------------|---------------|
| 1 | "Check Dr. Ahuja's availability for Friday afternoon" | Returns available slots |
| 2 | "Book the 3 PM slot" | Books without re-stating full intent |

Maintain context via **session state or context chaining**.

---

## 🧩 Scenario 2: Doctor Summary Report & Notification

### Use Case
Doctor asks: _"How many patients visited yesterday?"_ or _"How many appointments do I have today?"_

### Expected Flow
1. LLM invokes MCP tools to:
   - Query PostgreSQL for appointment stats
   - Summarize results in human-readable report
2. Send via **non-email** notification (Slack / WhatsApp / in-app)
3. Trigger via:
   - Natural language input, OR
   - Dashboard button (frontend)

---

## 🔧 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React JS |
| Backend | FastAPI + MCP |
| Database | PostgreSQL |
| LLM | OpenAI GPT / Claude / Mistral (tool-calling) |
| Scheduling | Google Calendar API |
| Email | Gmail / SendGrid / Mailgun |
| Notifications | Slack / WhatsApp Business API / Firebase |

---

## 📦 Deliverables
- [ ] GitHub repo with clean, modular code
- [ ] `README.md` with setup steps, sample prompts, API usage summary
- [ ] Screenshots: prompt-based booking + doctor notification
- [ ] Demo video (optional but preferred)

---

## 🧠 Bonus Features
- [ ] Role-based login (patient vs doctor)
- [ ] LLM-powered auto-rescheduling when doctor is unavailable
- [ ] Prompt history tracking

---

## ⚠️ Evaluation Criteria
1. **MCP Architecture** — Client–Server–Tool/Prompt/Resource understanding
2. **LLM Workflow Orchestration** — Agentic decision-making
3. **API Integration** — Async logic, external APIs
4. **Full-Stack Fluency** — React ↔ FastAPI ↔ DB/APIs
5. **Code Quality** — Readability, scalability, agentic design
