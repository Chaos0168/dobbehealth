"""
main.py — FastAPI application entry point
This is where the app boots up, middleware is configured, and routes are registered
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from routes import auth, chat, doctor


# ── Lifespan: runs on startup and shutdown ─────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: anything you want to initialize (DB pool warms up automatically)
    print("✅ DOBBE AI Backend started")
    yield
    # Shutdown
    print("🛑 DOBBE AI Backend shutting down")


# ── Create the app ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="DOBBE AI — Doctor Appointment Assistant",
    description="Agentic AI with MCP for doctor appointment scheduling and reporting",
    version="1.0.0",
    lifespan=lifespan,
)


# ── CORS — allows the React frontend (localhost:3000) to talk to this backend ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],   # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Register Routes ────────────────────────────────────────────────────────────
app.include_router(auth.router,   prefix="/api/auth",   tags=["Authentication"])
app.include_router(chat.router,   prefix="/api/chat",   tags=["Patient Chat"])
app.include_router(doctor.router, prefix="/api/doctor", tags=["Doctor Dashboard"])


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "service": "DOBBE AI Backend"}
