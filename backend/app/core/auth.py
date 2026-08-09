"""JWT + API Key authentication — no bcrypt, uses hashlib.

Roles:
  - admin: full control of gateway (providers, models, routing, users)
  - user: can use the API, see public models, manage their own API keys
  - readonly: read-only access to their own data

API key ownership:
  - User.api_key is the legacy single-key field (kept for backwards compat).
  - Each user can create multiple APIKey rows under their own account via
    the /admin/api-keys endpoints.
  - The /admin/auth/me endpoint never returns api_key values for non-admins
    so regular users can't see other users' keys.
"""
import os
import time
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.db.session import async_session_maker
from app.db.models import User, APIKey

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24 * 30  # 30 days — long-lived sessions

pwd_scheme = HTTPBearer()


# ─── Password hashing (PBKDF2-SHA256, no bcrypt) ───────────────────────
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"{salt}${hash_obj.hex()}"


def verify_password(plain: str, hashed: str) -> bool:
    try:
        salt, stored_hash = hashed.split("$")
        check = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 100000)
        return secrets.compare_digest(check.hex(), stored_hash)
    except Exception:
        return False


# ─── JWT helpers ───────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire.timestamp()})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str, secret: Optional[str] = None) -> Optional[dict]:
    try:
        return jwt.decode(token, secret or settings.SECRET_KEY, algorithms=[ALGORITHM])
    except (JWTError, Exception):
        return None


def create_api_key() -> str:
    """Create a random API key with a sk- prefix."""
    return f"sk-{secrets.token_urlsafe(32)}"


def _gateway_fernet():
    from cryptography.fernet import Fernet
    import base64
    configured = settings.PERSONAL_GATEWAY_ENCRYPTION_KEY or settings.SECRET_KEY
    digest = hashlib.sha256(configured.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_gateway_secret(value: str) -> str:
    return _gateway_fernet().encrypt(value.encode()).decode()


def decrypt_gateway_secret(value: str) -> str:
    return _gateway_fernet().decrypt(value.encode()).decode()


# ─── Header / dependency plumbing ──────────────────────────────────────
async def _resolve_user(authorization: str = Header(None)) -> Optional[dict]:
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
    payload = await _resolve_user(authorization)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Missing or invalid authorization token")
    return payload


async def require_admin(authorization: str = Header(None)) -> dict:
    payload = await require_user(authorization)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return payload


async def get_optional_user(authorization: str = Header(None)) -> Optional[dict]:
    return await _resolve_user(authorization)


async def get_current_user_full(authorization: str = Header(None)) -> dict:
    """Decode JWT and load the full User row from the DB.

    Use this when you need the most up-to-date role/credits/active status
    (e.g. for permission checks that depend on data the token may be stale on).
    """
    payload = await require_user(authorization)
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.id == payload["sub"]))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User no longer exists")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is disabled")
        if user.role != "admin" and not user.email_verified_at:
            raise HTTPException(status_code=403, detail="Email verification required")
        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "tier": user.tier,
            "credits": user.credits,
            "is_active": user.is_active,
        }


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(pwd_scheme)) -> str:
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
    return user_id
