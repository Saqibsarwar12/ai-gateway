"""Security: JWT + API Key authentication."""
import os
import time
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
import shortuuid
from jose import jwt, JWTError
from fastapi import HTTPException, Security, Request
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.db.session import async_session
from sqlalchemy import select
from app.db.models import User, ApiKey


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
def create_access_token(user_id: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
    payload = {
        "sub": user_id,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "iss": settings.APP_NAME,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


# ---------------------------------------------------------------------------
# API Key Auth
# ---------------------------------------------------------------------------
API_KEY_HEADER = APIKeyHeader(name="Authorization", auto_error=False)


async def get_current_user_api_key(
    security: HTTPAuthorizationCredentials = Security(API_KEY_HEADER),
) -> Optional[User]:
    """
    Support both Bearer JWT and direct 'sk-...' API key format.
    If Authorization: Bearer <jwt> → validate JWT
    If Authorization: sk-xxx      → validate API key hash
    """
    if not security:
        return None

    token = security.credentials

    # Bearer JWT
    if token.startswith("Bearer "):
        try:
            payload = decode_token(token[7:])
            async with async_session() as session:
                result = await session.execute(select(User).where(User.id == payload["sub"]))
                user = result.scalar_one_or_none()
                if user and user.is_active:
                    return user
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Direct API key (sk-...)
    if token.startswith("sk-"):
        key_hash = hash_token(token)
        async with async_session() as session:
            result = await session.execute(
                select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active == True)
            )
            api_key = result.scalar_one_or_none()
            if not api_key:
                raise HTTPException(status_code=401, detail="Invalid API key")

            # Check expiry
            if api_key.expires_on and api_key.expires_on < datetime.now(timezone.utc):
                raise HTTPException(status_code=401, detail="API key expired")

            # Get user
            result = await session.execute(
                select(User).where(User.id == api_key.user_id, User.is_active == True)
            )
            user = result.scalar_one_or_none()
            if not user:
                raise HTTPException(status_code=401, detail="User not found or suspended")

            # Update last_used_at
            api_key.last_used_at = datetime.now(timezone.utc)
            await session.commit()
            return user

    raise HTTPOptional(None)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_api_key() -> tuple[str, str]:
    """Returns (raw_key, hash). Store hash=raw_key[:8] for prefix."""
    raw = f"sk-{secrets.token_urlsafe(32)}"
    return raw, hash_token(raw)


def require_role(required_role: str):
    """Dependency that enforces role >= required_role."""
    async def checker(user: Optional[User] = Security(get_current_user_api_key)):
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        roleHierarchy = {"user": 1, "staff": 2, "enterprise": 3, "admin": 4}
        if roleHierarchy.get(user.role, 0) < roleHierarchy.get(required_role, 0):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker
