"""
routes/auth.py — Login and registration endpoints
POST /api/auth/register  — create new user account
POST /api/auth/login     — get JWT token
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.database import get_db
from models.orm import User, Doctor
from models.schemas import RegisterRequest, LoginRequest, TokenResponse
from models.auth_utils import hash_password, verify_password, create_access_token

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if email already taken
    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Validate doctor registration has specialization
    if payload.role == "doctor" and not payload.specialization:
        raise HTTPException(status_code=400, detail="Specialization required for doctors")

    # Create user
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        phone=payload.phone,
    )
    db.add(user)
    await db.flush()   # flush to get the generated UUID

    # If doctor, also create doctor profile
    if payload.role == "doctor":
        doctor = Doctor(user_id=user.id, specialization=payload.specialization)
        db.add(doctor)

    await db.commit()

    token = create_access_token({"sub": str(user.id), "role": user.role, "name": user.name})
    return TokenResponse(access_token=token, role=user.role, name=user.name, user_id=str(user.id))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": str(user.id), "role": user.role, "name": user.name})
    return TokenResponse(access_token=token, role=user.role, name=user.name, user_id=str(user.id))
