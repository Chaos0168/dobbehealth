"""
Pydantic Schemas — Request/Response shapes for the API
Pydantic validates incoming JSON and serializes outgoing responses
These are DIFFERENT from ORM models — think of them as the API's "language"
"""
from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import date, time, datetime
from typing import Optional


# ─── Auth ─────────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str           # "patient" | "doctor"
    phone: Optional[str] = None
    specialization: Optional[str] = None   # required if role == "doctor"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str
    user_id: str


# ─── Chat ─────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    session_id: str     # frontend generates this UUID per conversation

class ChatResponse(BaseModel):
    reply: str
    session_id: str


# ─── Appointments ─────────────────────────────────────────────────────────────
class AppointmentOut(BaseModel):
    id: UUID
    doctor_name: str
    patient_name: str
    appointment_date: date
    start_time: time
    end_time: time
    status: str
    reason: Optional[str]

    class Config:
        from_attributes = True   # lets pydantic read from ORM objects


# ─── Doctor Report ────────────────────────────────────────────────────────────
class ReportRequest(BaseModel):
    message: str        # natural language: "how many patients yesterday?"
    session_id: str

class ReportResponse(BaseModel):
    report: str
    session_id: str
