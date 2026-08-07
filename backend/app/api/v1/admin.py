"""Admin/User API — providers, routing, models, users, API keys, analytics.

Authentication model:
  - Public: /auth/login, /auth/register, /health
  - Any logged-in user: /auth/me, /api-keys/me/*, /models (public list),
    /providers/presets, /providers/discover, /providers/test-key,
    /analytics, /logs (own logs only)
  - Admin only: /providers/* (create/update/delete/test/sync),
    /routing/*, /users/*, /admin-only fields like api_key on /auth/me

API key ownership:
  - Each user can create multiple APIKey rows via /api-keys/me.
  - Users can ONLY see/manage their own keys.
  - Admins can see all keys and the User.api_key legacy field.
  - Non-admin /auth/me never returns api_key values.
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy import select, func
from app.db.session import async_session_maker
from app.db.models import Provider, RoutingRule, User, Model, RequestLog, UsageStats, APIKey, VerificationToken
from app.models.schemas import (
    ProviderCreate, ProviderUpdate, ProviderResponse,
    RoutingRuleCreate, RoutingRuleUpdate, RoutingRuleResponse,
    UserCreate, UserUpdate, UserResponse,
    APIKeyResponse, LoginRequest, LoginResponse,
)
from app.core.auth import (
    hash_password, verify_password, create_access_token, create_api_key,
    decode_token, get_current_user_full, require_user as _require_user_payload,
    ACCESS_TOKEN_EXPIRE_HOURS, pwd_scheme,
)
from app.core.config import settings
import shortuuid
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from app.services.email import EmailDeliveryError, send_verification_email

router = APIRouter()

def _client_ip(request: Request) -> str:
    """Best-effort client IP from X-Forwarded-For or remote_addr."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return (request.client.host if request.client else "") or "unknown"

# ─── Auth dependency (token decoder) ─────────────────────
async def _decode_bearer(authorization: Optional[str] = Header(None)) -> dict:
    """Decode the JWT bearer token. Raises 401 if missing/invalid."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid authorization header. Provide a Bearer token.",
        )
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_token(token, settings.SECRET_KEY)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload

async def require_user(authorization: Optional[str] = Header(None)) -> dict:
    """Any logged-in user."""
    payload = await _decode_bearer(authorization)
    user_id = payload.get("sub")
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User no longer exists")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is disabled")
        await _require_verified_user(user)
    return payload

async def require_admin(authorization: Optional[str] = Header(None)) -> dict:
    """Admin role required."""
    payload = await _decode_bearer(authorization)
    user_id = payload.get("sub")
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User no longer exists or is disabled")
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin role required")
    return payload

async def _require_verified_user(user: User) -> None:
    if user.role != "admin" and not user.email_verified_at:
        raise HTTPException(status_code=403, detail="Email verification required")

# ─── Rate limit on login (in-memory, per-IP) ───────────────────
_login_attempts: dict = {}  # ip -> [timestamps]
def _check_login_rate_limit(ip: str) -> None:
    now = time.time()
    window = 60 * 5  # 5 minutes
    max_attempts = 10
    attempts = [t for t in _login_attempts.get(ip, []) if now - t < window]
    if len(attempts) >= max_attempts:
        raise HTTPException(
            status_code=429,
            detail=f"Too many login attempts from this IP. Try again in a few minutes.",
        )
    attempts.append(now)
    _login_attempts[ip] = attempts

import time


def _check_registration_rate_limit(ip: str) -> None:
    now = time.time()
    window = settings.AUTH_RATE_LIMIT_WINDOW_SECONDS
    attempts = [t for t in _login_attempts.get(f"register:{ip}", []) if now - t < window]
    if len(attempts) >= settings.AUTH_RATE_LIMIT_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many registration attempts. Try again later.")
    attempts.append(now)
    _login_attempts[f"register:{ip}"] = attempts


async def _delete_created_registration(session, user_id: str, verification_id: str) -> None:
    verification_result = await session.execute(select(VerificationToken).where(VerificationToken.id == verification_id))
    verification_row = verification_result.scalar_one_or_none()
    if verification_row:
        await session.delete(verification_row)
    user_result = await session.execute(select(User).where(User.id == user_id))
    user_row = user_result.scalar_one_or_none()
    if user_row:
        await session.delete(user_row)
    await session.commit()

# ─── Auth (PUBLIC — no token required) ────────────────────────
class LoginBody(BaseModel):
    identifier: Optional[str] = None
    email: Optional[str] = None
    password: str

@router.post("/auth/login")
async def login(body: LoginBody, request: Request):
    """Authenticate with email OR username + password.

    Returns a 30-day JWT and the user record. Never includes api_key
    unless the caller is an admin.
    """
    _check_login_rate_limit(_client_ip(request))
    identifier = (body.identifier or body.email or "").strip()
    if not identifier or not body.password:
        raise HTTPException(status_code=400, detail="Missing identifier or password")

    async with async_session_maker() as session:
        # Try email first, then name (username)
        result = await session.execute(select(User).where(User.email == identifier))
        user = result.scalar_one_or_none()
        if not user:
            result = await session.execute(select(User).where(User.name == identifier))
            user = result.scalar_one_or_none()

        if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is disabled")
        await _require_verified_user(user)

        token = create_access_token(
            {"sub": user.id, "email": user.email, "role": user.role},
        )
        is_admin = user.role == "admin"
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in_hours": ACCESS_TOKEN_EXPIRE_HOURS,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "tier": user.tier,
                "credits": user.credits,
                "is_active": user.is_active,
                # Only admins can see API keys
                **({"api_key": user.api_key} if is_admin else {}),
            },
        }

class RegisterBody(BaseModel):
    name: str = Field(min_length=2, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

@router.post("/auth/register")
async def register(body: RegisterBody, request: Request):
    """Create an inactive account and send a one-time verification link."""
    _check_registration_rate_limit(_client_ip(request))
    name = body.name.strip()
    email = body.email.strip().lower()
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Username must be at least 2 characters")
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    async with async_session_maker() as session:
        existing = await session.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already registered")
        name_exists = await session.execute(select(User).where(User.name == name))
        if name_exists.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Username already taken")

        user_id = shortuuid.uuid()
        user = User(
            id=user_id,
            name=name,
            email=email,
            hashed_password=hash_password(body.password),
            role="user",
            tier="v1",
            api_key=create_api_key(),
            credits=100,
            is_active=False,
        )
        raw_token = secrets.token_urlsafe(48)
        verification = VerificationToken(
            id=shortuuid.uuid(),
            user_id=user_id,
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
            expires_at=datetime.utcnow() + timedelta(hours=settings.VERIFICATION_TOKEN_HOURS),
        )
        session.add(user)
        session.add(verification)
        await session.commit()
        try:
            await send_verification_email(email, f"{settings.APP_BASE_URL}/admin/auth/verify-email?token={raw_token}")
        except EmailDeliveryError as exc:
            await _delete_created_registration(session, user_id, verification.id)
            raise HTTPException(status_code=503, detail="Verification email service is unavailable") from exc
        return {"status": "verification_required", "email": email, "message": "Check your email to activate your account."}

@router.get("/auth/verify-email")
async def verify_email(token: str):
    if not token or len(token) > 256:
        raise HTTPException(status_code=400, detail="Invalid verification link")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    now = datetime.utcnow()
    async with async_session_maker() as session:
        result = await session.execute(select(VerificationToken).where(VerificationToken.token_hash == token_hash))
        verification = result.scalar_one_or_none()
        if not verification or verification.used_at or verification.expires_at < now:
            raise HTTPException(status_code=400, detail="Invalid or expired verification link")
        user_result = await session.execute(select(User).where(User.id == verification.user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=400, detail="Invalid verification link")
        user.email_verified_at = now
        user.is_active = True
        verification.used_at = now
        await session.commit()
    return {"verified": True, "message": "Email verified. You can now sign in."}

@router.get("/auth/me")
async def me(payload: dict = Depends(require_user)):
    """Return the current user.

    NEVER returns api_key for non-admins — users can manage their own
    keys via /api-keys/me/* and get the full key string only at creation
    or rotation time.
    """
    is_admin = payload.get("role") == "admin"
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.id == payload["sub"]))
        u = result.scalar_one_or_none()
        if not u:
            raise HTTPException(status_code=404, detail="User not found")
        out = {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "role": u.role,
            "tier": u.tier,
            "credits": u.credits,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        if is_admin:
            out["api_key"] = u.api_key
        return out

class PasswordChangeBody(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=128)

@router.post("/auth/change-password")
async def change_password(body: PasswordChangeBody, payload: dict = Depends(require_user)):
    """Change the current user's password."""
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.id == payload["sub"]))
        u = result.scalar_one_or_none()
        if not u or not verify_password(body.current_password, u.hashed_password or ""):
            raise HTTPException(status_code=401, detail="Current password is incorrect")
        u.hashed_password = hash_password(body.new_password)
        await session.commit()
    return {"changed": True}


# ─── Providers (admin only — non-admins see nothing) ────────
@router.get("/providers", response_model=list[ProviderResponse])
async def list_providers(payload: dict = Depends(require_user)):
    """List providers. Admin sees everything; non-admins see ONLY the
    providers powering models they have access to (or empty list if none).
    """
    if payload.get("role") != "admin":
        return []  # Hide raw provider config from regular users
    async with async_session_maker() as session:
        result = await session.execute(select(Provider).order_by(Provider.priority))
        providers = result.scalars().all()
        out = []
        for p in providers:
            r = ProviderResponse.model_validate(p)
            if r.api_key:
                r.api_key = r.api_key[:6] + "…" + r.api_key[-4:] if len(r.api_key) > 12 else "•••"
            out.append(r)
        return out


async def _sync_manual_models(session, provider_id: str, models_list: List[str]):
    """Reconcile the Model table with the provider's `models` JSON list.

    - Creates rows for any IDs not yet in the table.
    - Updates existing rows whose name changed.
    - DELETES rows whose model_id is no longer in the list (so admin removals
      propagate to users — without this, /admin/models and /v1/models keep
      showing deleted models).
    """
    desired = [str(m).strip() for m in (models_list or []) if str(m).strip()]

    # Existing rows for this provider
    existing_rows = (
        await session.execute(select(Model).where(Model.provider_id == provider_id))
    ).scalars().all()
    by_mid = {m.model_id: m for m in existing_rows}

    created = updated = 0
    for mid_str in desired:
        m = by_mid.get(mid_str)
        if m:
            if m.name != mid_str:
                m.name = mid_str
                updated += 1
        else:
            session.add(Model(
                id=shortuuid.uuid(),
                name=mid_str,
                provider_id=provider_id,
                model_id=mid_str,
                mode="chat",
                input_cost_per_1m=0.0,
                output_cost_per_1m=0.0,
                context_window=8192,
                supports_functions=False,
                supports_vision=False,
                enabled=True,
                is_active=True,
            ))
            created += 1

    # Delete rows no longer in the list
    desired_set = set(desired)
    for row in existing_rows:
        if row.model_id not in desired_set:
            await session.delete(row)

    await session.commit()
    return {"created": created, "updated": updated, "removed": len(existing_rows) - len(desired_set)}


@router.post("/providers", response_model=ProviderResponse)
async def create_provider(data: ProviderCreate, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        p = Provider(
            id=data.id or shortuuid.uuid(),
            name=data.name,
            provider_type=data.provider_type,
            base_url=data.base_url,
            api_key=data.api_key,
            enabled=data.enabled,
            priority=data.priority,
            max_rpm=data.max_rpm,
            max_tpm=data.max_tpm,
            requires_proxy=data.requires_proxy,
            proxy_url=data.proxy_url,
            models=data.models,
            extra_config=data.extra_config or {},
        )
        session.add(p)
        await session.commit()
        await _sync_manual_models(session, p.id, data.models)
        r = ProviderResponse.model_validate(p)
        if r.api_key:
            r.api_key = r.api_key[:6] + "…" + r.api_key[-4:] if len(r.api_key) > 12 else "•••"
        return r


@router.put("/providers/{provider_id}", response_model=ProviderResponse)
async def update_provider(provider_id: str, data: ProviderUpdate, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        result = await session.execute(select(Provider).where(Provider.id == provider_id))
        p = result.scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="Provider not found")
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(p, key, value)
        p.updated_at = datetime.utcnow()
        await session.commit()
        if data.models is not None:
            await _sync_manual_models(session, p.id, data.models)
        r = ProviderResponse.model_validate(p)
        if r.api_key:
            r.api_key = r.api_key[:6] + "…" + r.api_key[-4:] if len(r.api_key) > 12 else "•••"
        return r


@router.delete("/providers/{provider_id}")
async def delete_provider(provider_id: str, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        result = await session.execute(select(Provider).where(Provider.id == provider_id))
        p = result.scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="Provider not found")
        # Cascade: delete all Model rows belonging to this provider so users
        # can't keep calling models that no longer exist.
        from sqlalchemy import delete as _delete
        await session.execute(_delete(Model).where(Model.provider_id == provider_id))
        await session.delete(p)
        await session.commit()
        return {"deleted": True}


@router.post("/providers/{provider_id}/test")
async def test_provider(provider_id: str, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        result = await session.execute(select(Provider).where(Provider.id == provider_id))
        p = result.scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="Provider not found")

        from app.providers.adapters import OpenAIAdapter
        adapter = OpenAIAdapter(name=p.id, base_url=p.base_url, api_key=p.api_key or "")
        return await adapter.health_check()


@router.post("/providers/{provider_id}/sync-models")
async def sync_provider_models(provider_id: str, _: dict = Depends(require_admin)):
    """Fetch models from the provider's /models endpoint and reconcile.

    Reconciles the Model table to match the upstream: creates missing rows,
    updates renamed ones, and DELETES rows that are no longer advertised.
    """
    async with async_session_maker() as session:
        result = await session.execute(select(Provider).where(Provider.id == provider_id))
        p = result.scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="Provider not found")
        if not p.api_key:
            raise HTTPException(status_code=400, detail="Provider has no API key configured")

        from app.providers.adapters import OpenAIAdapter
        adapter = OpenAIAdapter(name=p.id, base_url=p.base_url, api_key=p.api_key)
        remote_ids = await adapter.list_models()
        if not remote_ids:
            remote_ids = list(p.models or [])

        summary = await _sync_manual_models(session, p.id, remote_ids)
        p.models = remote_ids
        p.updated_at = datetime.utcnow()
        await session.commit()
        return {
            "created": summary["created"],
            "updated": summary["updated"],
            "removed": summary["removed"],
            "total": len(remote_ids),
            "models": remote_ids,
        }


# ─── Routing Rules (admin only) ──────────────────────────────
@router.get("/routing", response_model=list[RoutingRuleResponse])
async def list_routing_rules(_: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        result = await session.execute(select(RoutingRule).order_by(RoutingRule.priority.desc()))
        return [RoutingRuleResponse.model_validate(r) for r in result.scalars().all()]


@router.post("/routing", response_model=RoutingRuleResponse)
async def create_routing_rule(data: RoutingRuleCreate, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        r = RoutingRule(
            id=shortuuid.uuid(),
            name=data.name,
            strategy=data.strategy,
            model_pattern=data.model_pattern,
            provider_order=data.provider_ids,
            weights=data.weights,
            is_active=data.is_active,
            priority=data.priority or 0,
            fallback_enabled=data.fallback_enabled,
            max_retries=data.max_retries,
            timeout_ms=data.timeout_ms,
        )
        session.add(r)
        await session.commit()
        return RoutingRuleResponse.model_validate(r)


@router.put("/routing/{rule_id}", response_model=RoutingRuleResponse)
async def update_routing_rule(rule_id: str, data: RoutingRuleUpdate, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        result = await session.execute(select(RoutingRule).where(RoutingRule.id == rule_id))
        r = result.scalar_one_or_none()
        if not r:
            raise HTTPException(status_code=404, detail="Rule not found")
        update_data = data.model_dump(exclude_unset=True)
        if "provider_ids" in update_data:
            update_data["provider_order"] = update_data.pop("provider_ids")
        for key, value in update_data.items():
            setattr(r, key, value)
        await session.commit()
        return RoutingRuleResponse.model_validate(r)


@router.delete("/routing/{rule_id}")
async def delete_routing_rule(rule_id: str, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        result = await session.execute(select(RoutingRule).where(RoutingRule.id == rule_id))
        r = result.scalar_one_or_none()
        if not r:
            raise HTTPException(status_code=404, detail="Rule not found")
        await session.delete(r)
        await session.commit()
        return {"deleted": True}


# ─── Users (admin only — never accessible to regular users) ──
@router.get("/users", response_model=list[UserResponse])
async def list_users(_: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        result = await session.execute(select(User).order_by(User.created_at.desc()))
        return [UserResponse.model_validate(u) for u in result.scalars().all()]


@router.post("/users", response_model=UserResponse)
async def create_user(data: UserCreate, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        normalized_email = data.email.strip().lower()
        existing = await session.execute(select(User).where(User.email == normalized_email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already registered")
        api_key = create_api_key()
        u = User(
            id=shortuuid.uuid(),
            name=data.name,
            email=normalized_email,
            hashed_password=hash_password(data.password),
            role=data.role,
            tier=data.tier or "v1",
            api_key=api_key,
            credits=data.credits,
            is_active=True,
            email_verified_at=datetime.utcnow(),
        )
        session.add(u)
        await session.commit()
        return UserResponse.model_validate(u)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, data: UserUpdate, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        u = result.scalar_one_or_none()
        if not u:
            raise HTTPException(status_code=404, detail="User not found")
        update_data = data.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["hashed_password"] = hash_password(update_data.pop("password"))
        for key, value in update_data.items():
            setattr(u, key, value)
        await session.commit()
        return UserResponse.model_validate(u)


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        u = result.scalar_one_or_none()
        if not u:
            raise HTTPException(status_code=404, detail="User not found")
        await session.delete(u)
        await session.commit()
        return {"deleted": True}


# ─── Analytics (admin only — internal business data) ─────────
@router.get("/analytics")
async def get_analytics(days: int = 7, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        since = datetime.utcnow() - timedelta(days=days)
        count_result = await session.execute(
            select(func.count(RequestLog.id)).where(RequestLog.created_at >= since)
        )
        total_requests = count_result.scalar() or 0
        if total_requests == 0:
            return {
                "total_requests": 0, "total_input_tokens": 0, "total_output_tokens": 0,
                "total_cost_usd": 0.0, "avg_latency_ms": 0.0,
                "success_rate": 100.0, "error_count": 0,
            }
        token_result = await session.execute(
            select(
                func.sum(RequestLog.input_tokens),
                func.sum(RequestLog.output_tokens),
                func.coalesce(func.sum(RequestLog.cost_usd), 0.0),
            ).where(RequestLog.created_at >= since)
        )
        row = token_result.one()
        total_input = row[0] or 0
        total_output = row[1] or 0
        total_cost = row[2] or 0.0
        lat_result = await session.execute(
            select(func.avg(RequestLog.latency_ms)).where(RequestLog.created_at >= since)
        )
        avg_latency = lat_result.scalar() or 0.0
        err_result = await session.execute(
            select(func.count(RequestLog.id)).where(
                RequestLog.created_at >= since,
                RequestLog.status_code >= 400,
            )
        )
        error_count = err_result.scalar() or 0
        success_rate = ((total_requests - error_count) / max(total_requests, 1)) * 100
        return {
            "total_requests": total_requests,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cost_usd": round(total_cost, 6),
            "avg_latency_ms": round(float(avg_latency), 1),
            "success_rate": round(success_rate, 2),
            "error_count": error_count,
        }


# ─── My own usage analytics (any logged-in user) ─────────────
@router.get("/analytics/me")
async def my_analytics(days: int = 7, payload: dict = Depends(require_user)):
    """User-scoped analytics — only this user's data."""
    async with async_session_maker() as session:
        since = datetime.utcnow() - timedelta(days=days)
        user_id = payload["sub"]
        count_result = await session.execute(
            select(func.count(RequestLog.id)).where(
                RequestLog.created_at >= since, RequestLog.user_id == user_id,
            )
        )
        total = count_result.scalar() or 0
        if total == 0:
            return {
                "total_requests": 0, "total_input_tokens": 0, "total_output_tokens": 0,
                "total_cost_usd": 0.0, "credits_remaining": None, "tier": None,
            }
        token_result = await session.execute(
            select(
                func.sum(RequestLog.input_tokens),
                func.sum(RequestLog.output_tokens),
                func.coalesce(func.sum(RequestLog.cost_usd), 0.0),
            ).where(RequestLog.created_at >= since, RequestLog.user_id == user_id)
        )
        row = token_result.one()
        me_result = await session.execute(select(User).where(User.id == user_id))
        u = me_result.scalar_one()
        return {
            "total_requests": total,
            "total_input_tokens": row[0] or 0,
            "total_output_tokens": row[1] or 0,
            "total_cost_usd": round(row[2] or 0.0, 6),
            "credits_remaining": u.credits,
            "tier": u.tier,
        }


# ─── Logs ───────────────────────────────────────────────────
@router.get("/logs/me")
async def get_my_logs(limit: int = 100, offset: int = 0, payload: dict = Depends(require_user)):
    async with async_session_maker() as session:
        result = await session.execute(
            select(RequestLog)
            .where(RequestLog.user_id == payload["sub"])
            .order_by(RequestLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        logs = result.scalars().all()
        return [
            {
                "id": l.id, "provider": l.provider, "model": l.model,
                "input_tokens": l.input_tokens, "output_tokens": l.output_tokens,
                "latency_ms": l.latency_ms, "status_code": l.status_code,
                "error": l.error, "cost_usd": l.cost_usd,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            } for l in logs
        ]

@router.get("/logs")
async def get_logs(limit: int = 100, offset: int = 0, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        result = await session.execute(
            select(RequestLog)
            .order_by(RequestLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        logs = result.scalars().all()
        return [
            {
                "id": l.id, "provider": l.provider, "model": l.model,
                "input_tokens": l.input_tokens, "output_tokens": l.output_tokens,
                "latency_ms": l.latency_ms, "status_code": l.status_code,
                "error": l.error, "cost_usd": l.cost_usd,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            } for l in logs
        ]


# ─── Models (any logged-in user can READ) ───────────────────
@router.get("/models")
async def list_models(_: dict = Depends(require_user)):
    async with async_session_maker() as session:
        result = await session.execute(select(Model).where(Model.enabled == True))
        models = result.scalars().all()
        return [
            {
                "id": m.id, "name": m.name, "provider_id": m.provider_id,
                "mode": m.mode, "model_id": m.model_id,
                "context_window": m.context_window,
                "supports_functions": m.supports_functions,
                "supports_vision": m.supports_vision,
                "input_cost_per_1m": m.input_cost_per_1m,
                "output_cost_per_1m": m.output_cost_per_1m,
            } for m in models
        ]


# ─── Models write (admin only) ──────────────────────────────
@router.post("/models")
async def create_model(data: dict, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        m = Model(
            id=data.get("id", shortuuid.uuid()),
            name=data.get("name", ""),
            provider_id=data.get("provider_id"),
            model_id=data.get("model_id", ""),
            mode=data.get("mode", "chat"),
            context_window=data.get("context_window", 8192),
            enabled=True,
        )
        session.add(m)
        await session.commit()
        return {"id": m.id, "name": m.name}


@router.put("/models/{model_id}")
async def update_model(model_id: str, data: dict, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        result = await session.execute(select(Model).where(Model.id == model_id))
        m = result.scalar_one_or_none()
        if not m:
            raise HTTPException(status_code=404, detail="Model not found")
        for k, v in data.items():
            if hasattr(m, k) and k != "id":
                setattr(m, k, v)
        await session.commit()
        return {"id": m.id, "name": m.name}


@router.delete("/models/{model_id}")
async def delete_model(model_id: str, _: dict = Depends(require_admin)):
    async with async_session_maker() as session:
        result = await session.execute(select(Model).where(Model.id == model_id))
        m = result.scalar_one_or_none()
        if not m:
            raise HTTPException(status_code=404, detail="Model not found")
        await session.delete(m)
        await session.commit()
        return {"deleted": True}


# ─── Public model catalog (no auth — used by signup/marketing page) ─
@router.get("/public/models")
async def public_models():
    """Public model catalog — anyone (even logged out) can see what models exist."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Model).where(Model.enabled == True, Model.is_active == True)
        )
        models = result.scalars().all()
        return [
            {
                "id": m.id, "name": m.name, "model_id": m.model_id,
                "mode": m.mode, "context_window": m.context_window,
                "supports_functions": m.supports_functions,
                "supports_vision": m.supports_vision,
            } for m in models
        ]


# ─── API Keys — each user manages their own ──────────────────
@router.get("/api-keys")
async def list_my_keys(payload: dict = Depends(require_user)):
    """List the API keys owned by the current user."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(APIKey).where(APIKey.user_id == payload["sub"]).order_by(APIKey.created_at.desc())
        )
        keys = result.scalars().all()
        return [
            {
                "id": k.id, "name": k.name or "Unnamed",
                "key_preview": (k.key[:7] + "..." + k.key[-4:]) if k.key else "",
                "is_active": k.is_active,
                "rate_limit_rpm": k.rate_limit_rpm,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "created_at": k.created_at.isoformat() if k.created_at else None,
            } for k in keys
        ]


@router.post("/api-keys")
async def create_my_key(data: dict, payload: dict = Depends(require_user)):
    """Create a new API key for the current user.

    Returns the full key value ONCE — it is never returned again.
    """
    name = (data or {}).get("name", "").strip() or "My API key"
    raw_key = create_api_key()
    async with async_session_maker() as session:
        # Check if user already has 5 or more keys
        count_result = await session.execute(
            select(func.count(APIKey.id)).where(APIKey.user_id == payload["sub"])
        )
        if (count_result.scalar() or 0) >= 5:
            raise HTTPException(status_code=400, detail="You can only have up to 5 API keys.")

        ak = APIKey(
            id=shortuuid.uuid(),
            key=raw_key,
            user_id=payload["sub"],
            name=name,
            prefix=raw_key[:7],
            rate_limit_rpm=(data or {}).get("rate_limit_rpm", 60),
            rate_limit_tpm=(data or {}).get("rate_limit_tpm", 100000),
            is_active=True,
        )
        session.add(ak)
        await session.commit()
        return {
            "id": ak.id,
            "name": ak.name,
            "key": raw_key,  # shown ONCE
            "key_preview": raw_key[:7] + "..." + raw_key[-4:],
            "is_active": True,
        }


@router.delete("/api-keys/{key_id}")
async def delete_my_key(key_id: str, payload: dict = Depends(require_user)):
    async with async_session_maker() as session:
        result = await session.execute(
            select(APIKey).where(APIKey.id == key_id, APIKey.user_id == payload["sub"])
        )
        ak = result.scalar_one_or_none()
        if not ak:
            raise HTTPException(status_code=404, detail="API key not found")
        await session.delete(ak)
        await session.commit()
        return {"deleted": True}


# ─── Provider Presets (public) ──────────────────────────────
@router.get("/providers/presets")
async def list_provider_presets():
    from app.core.provider_presets import list_presets as get_presets
    return get_presets()


class DiscoverBody(BaseModel):
    base_url: str
    api_key: str = ""
    provider_type: str = "openai"


class TestKeyBody(BaseModel):
    base_url: str
    api_key: str = ""
    model: str = ""
    provider_type: str = "openai"


# ─── Discover models (admin only — protects provider probing) ──
@router.post("/providers/discover")
async def discover_models(body: DiscoverBody, _: dict = Depends(require_admin)):
    import httpx
    from app.core.provider_presets import normalize_base_url, PROVIDER_PRESETS as PRESETS
    base = normalize_base_url(body.base_url)
    headers = {"Content-Type": "application/json"}
    if body.api_key:
        if body.provider_type == "anthropic":
            headers["x-api-key"] = body.api_key
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["Authorization"] = f"Bearer {body.api_key}"
    result = {
        "ok": False, "base_url": base, "models": [],
        "error": None, "warning": None,
        "auth_scheme": ("x-api-key + anthropic-version" if body.provider_type == "anthropic" else "Authorization: Bearer"),
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(f"{base}/models", headers=headers)
            if r.status_code == 200:
                data = r.json()
                ids = []
                if isinstance(data, dict) and isinstance(data.get("data"), list):
                    ids = [str(m.get("id") or m.get("name") or "").strip() for m in data["data"]]
                    ids = [i for i in ids if i]
                elif isinstance(data, dict) and isinstance(data.get("models"), list):
                    ids = [str(x) for x in data["models"] if x]
                elif isinstance(data, list):
                    ids = [str(m.get("id") if isinstance(m, dict) else m) for m in data if m]
                if ids:
                    result["ok"] = True
                    result["models"] = ids
                else:
                    result["warning"] = "Connected, but the response had no model list."
            elif r.status_code == 401:
                result["error"] = "401 Unauthorized — check the API key."
            elif r.status_code == 403:
                result["error"] = "403 Forbidden — the key doesn't have access."
            elif r.status_code == 404:
                result["warning"] = "No /models endpoint (404). The provider may not support listing."
            else:
                result["error"] = f"{r.status_code}: {r.text[:200]}"
    except httpx.ConnectError as e:
        result["error"] = f"Connection failed: {e}"
    except httpx.TimeoutException:
        result["error"] = "Timed out (20s). The base URL may be unreachable from Render."
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
    if not result["models"] and not result["error"]:
        for preset in PRESETS:
            if base.rstrip("/").startswith(preset["base_url"].rstrip("/")):
                result["models"] = list(preset.get("known_models", []))
                result["warning"] = result["warning"] or "Showing preset known models — you can edit before saving."
                break
    return result


# ─── Test key (admin only) ─────────────────────────────────
@router.post("/providers/test-key")
async def test_provider_key(body: TestKeyBody, _: dict = Depends(require_admin)):
    import httpx, time
    from app.core.provider_presets import normalize_base_url
    base = normalize_base_url(body.base_url)
    if not body.model:
        return {"ok": False, "error": "No model specified"}
    start = time.time()
    try:
        if body.provider_type == "anthropic":
            headers = {"x-api-key": body.api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
            payload = {"model": body.model, "max_tokens": 8, "messages": [{"role": "user", "content": "ping"}]}
            url = f"{base}/messages"
        else:
            headers = {"Authorization": f"Bearer {body.api_key}" if body.api_key else "", "Content-Type": "application/json"}
            payload = {"model": body.model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 8, "stream": False}
            url = f"{base}/chat/completions"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, headers=headers, json=payload)
            latency_ms = int((time.time() - start) * 1000)
            if r.status_code == 200:
                data = r.json()
                content = ""
                if body.provider_type == "anthropic":
                    content = (data.get("content") or [{}])[0].get("text", "")
                else:
                    content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
                return {
                    "ok": True, "latency_ms": latency_ms, "status_code": 200,
                    "response_preview": (content[:120] or "(empty content)"),
                    "usage": data.get("usage"),
                }
            else:
                return {"ok": False, "latency_ms": latency_ms, "status_code": r.status_code, "error": r.text[:400]}
    except httpx.ConnectError as e:
        return {"ok": False, "error": f"Connection failed: {e}"}
    except httpx.TimeoutException:
        return {"ok": False, "error": "Timed out (30s)"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
