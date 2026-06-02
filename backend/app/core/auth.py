"""JWT + API Key authentication — no bcrypt, uses hashlib."""
import os
import time
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from app.core.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

pwd_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-SHA256 — no bcrypt needed."""
    salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"{salt}${hash_obj.hex()}"


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against PBKDF2 hash."""
    try:
        salt, stored_hash = hashed.split("$")
        check = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 100000)
        return secrets.compare_digest(check.hex(), stored_hash)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire.timestamp()})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str, secret: Optional[str] = None) -> Optional[dict]:
    """Decode a JWT and return the payload, or None on failure."""
    try:
        return jwt.decode(token, secret or settings.SECRET_KEY, algorithms=[ALGORITHM])
    except (JWTError, Exception):
        return None


def create_api_key() -> str:
    """Create a random API key."""
    return f"sk-{secrets.token_urlsafe(32)}"


# ─── FastAPI dependencies for protected routes ─────────────────────────
from fastapi import Header  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402


async def _resolve_user(authorization: str = Header(None)) -> Optional[dict]:
    """Return decoded JWT payload or None. Pure header check, no DB."""
    if not authorization:
        return None
    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    else:
        token = authorization.strip()
    if not token:
        return None
    return decode_token(token)


async def require_user(authorization: str = Header(None)) -> dict:
    """Dependency: require any valid JWT. Raises 401 otherwise."""
    payload = await _resolve_user(authorization)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Missing or invalid authorization token")
    return payload


async def require_admin(authorization: str = Header(None)) -> dict:
    """Dependency: require a valid JWT with role=admin. Raises 401/403 otherwise."""
    payload = await require_user(authorization)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return payload


async def get_optional_user(authorization: str = Header(None)) -> Optional[dict]:
    """Dependency: return user payload if a valid JWT is present, else None."""
    return await _resolve_user(authorization)


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(pwd_scheme)) -> str:
    """Validate Bearer token and return user_id."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def admin_required(user_id: str = Depends(get_current_user_id)) -> str:
    """Require admin role (loaded from DB by admin endpoints)."""
    return user_id
