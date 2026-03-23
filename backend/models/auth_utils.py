"""
auth_utils.py — JWT token creation and verification
JWT = JSON Web Token — a signed string that proves who the user is
Structure: header.payload.signature
"""
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import bcrypt
from config import settings

# Tells FastAPI: "look for the token in the Authorization: Bearer <token> header"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(plain: str) -> str:
    """Convert 'password123' → '$2b$12$...' (irreversible hash)"""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Check if a plain password matches a stored hash"""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(data: dict) -> str:
    """
    Create a signed JWT token.
    data = {"sub": user_id, "role": "patient", "name": "Tript"}
    The token expires after JWT_EXPIRE_MINUTES minutes.
    """
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload["exp"] = expire
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token. Raises 401 if invalid or expired."""
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """FastAPI dependency — inject this into any route that requires login"""
    return decode_token(token)


async def require_role(role: str):
    """Factory for role-specific dependencies"""
    async def checker(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") != role:
            raise HTTPException(status_code=403, detail=f"Access restricted to {role}s only")
        return current_user
    return checker
