"""Admin/User API — providers, routing, models, users, API keys, analytics.

Authentication model:
  - Public: /auth/login, /auth/register, /auth/verify-code, /auth/verify-email, /health
  - Any logged-in user: /auth/me, /api-keys/me/*, /models (public list),
    /providers/presets, /providers/discover, /providers/test-key,
    /analytics, /logs (own logs only)
  - Admin only: /providers/* (create/update/delete/test/sync),
    /routing/*, /users/*, /admin-only fields like api_key on /auth/me

Registration requires email verification:
  1. POST /auth/register → stores PendingRegistration, sends 6-digit code
  2. POST /auth/verify-code → verifies code, creates User row with email_verified_at
  3. GET /auth/verify-email → legacy link verification via token hash

Login is blocked for unverified users (non-admin) until verify-code completes.

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

import time

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy import select, func
from app.db.session import async_session_maker
from app.db.models import Provider, RoutingRule, User, Model, RequestLog, UsageStats, APIKey, VerificationToken, PendingRegistration, UserGatewayConfig, NvidiaSmartConfig, NvidiaSmartAccount
from app.models.schemas import (
    ProviderCreate, ProviderUpdate, ProviderResponse,
    RoutingRuleCreate, RoutingRuleUpdate, RoutingRuleResponse,
    UserCreate, UserUpdate, UserResponse,
    APIKeyResponse, LoginRequest, LoginResponse,
)
from app.core.auth import (
    hash_password, verify_password, create_access_token, create_api_key,
    decode_token, get_current_user_full, require_user as _require_user_payload,
    ACCESS_TOKEN_EXPIRE_HOURS, pwd_scheme, encrypt_gateway_secret,
)
from app.core.config import settings
import shortuuid
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from app.services.email import EmailDeliveryError, send_verification_email
from app.core.usernames import normalize_username, fallback_username, valid_username

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
    """Any logged-in user (must be email-verified for non-admins)."""
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
    """Admin role required (admins bypass email verification check)."""
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
        raise HTTPException(
            status_code=403,
            detail="Account not verified. Check your email for a verification code, or sign up again.",
            headers={"X-Needs-Verification": "true"},
        )

# ─── Per-email rate limiting for verify-code ─────────────────
_verify_attempts: dict = {}  # email → list of timestamps


def _check_verify_rate_limit(email: str) -> None:
    """Block after VERIFICATION_CODE_MAX_ATTEMPTS wrong codes in 15 min window."""
    now = time.time()
    window = settings.VERIFICATION_CODE_MINUTES * 60
    key = f"verify:{email.lower()}"
    attempts = [t for t in _verify_attempts.get(key, []) if now - t < window]
    if len(attempts) >= settings.VERIFICATION_CODE_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail=f"Too many incorrect codes. Wait 15 minutes or sign up again with a new code.",
        )


def _record_verify_failure(email: str) -> None:
    key = f"verify:{email.lower()}"
    if key not in _verify_attempts:
        _verify_attempts[key] = []
    _verify_attempts[key].append(time.time())


# ─── Global login rate limit (in-memory, per-IP) ─────────────────
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
    started = time.perf_counter()
    _check_login_rate_limit(_client_ip(request))
    identifier = (body.identifier or body.email or "").strip()
    if not identifier or not body.password:
        raise HTTPException(status_code=400, detail="Missing identifier or password")

    lookup_started = time.perf_counter()
    async with async_session_maker() as session:
        lookup_identifier = identifier.lower()
        result = await session.execute(
            select(User).where(
                (func.lower(User.email) == lookup_identifier)
                | (func.lower(User.name) == lookup_identifier)
                | (func.lower(User.username) == lookup_identifier)
            ).limit(1)
        )
        user = result.scalar_one_or_none()
        lookup_ms = round((time.perf_counter() - lookup_started) * 1000, 2)

        hash_started = time.perf_counter()
        valid_password = bool(user and user.hashed_password and verify_password(body.password, user.hashed_password))
        hash_ms = round((time.perf_counter() - hash_started) * 1000, 2)
        if not user or not valid_password:
            # Check if this email has a pending registration awaiting verification
            pending_result = await session.execute(
                select(PendingRegistration).where(PendingRegistration.email == lookup_identifier)
            )
            pending = pending_result.scalar_one_or_none()
            if pending and verify_password(body.password, pending.hashed_password):
                raise HTTPException(
                    status_code=403,
                    detail="Account not verified. Check your email for a verification code, or sign up again.",
                    headers={"X-Needs-Verification": "true"},
                )
            print(f"auth.login timing lookup_ms={lookup_ms} hash_ms={hash_ms} token_ms=0 total_ms={round((time.perf_counter() - started) * 1000, 2)} result=reject")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is disabled")
        await _require_verified_user(user)

        token_started = time.perf_counter()
        token = create_access_token(
            {"sub": user.id, "email": user.email, "role": user.role},
        )
        token_ms = round((time.perf_counter() - token_started) * 1000, 2)
        total_ms = round((time.perf_counter() - started) * 1000, 2)
        print(f"auth.login timing lookup_ms={lookup_ms} hash_ms={hash_ms} token_ms={token_ms} total_ms={total_ms} result=success")
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
    """Send verification first; create the real user only after confirmation."""
    started = time.perf_counter()
    _check_registration_rate_limit(_client_ip(request))

    name = body.name.strip()
    email = body.email.strip().lower()
    name = normalize_username(name)

    if not valid_username(name):
        raise HTTPException(status_code=400, detail="Username must start with a letter and contain only lowercase letters, numbers, and hyphens")
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Username must be at least 2 characters")
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # Block registration if email matches the configured admin email
    if email.lower() == settings.ADMIN_EMAIL.lower():
        raise HTTPException(status_code=409, detail="This email address cannot be registered")

    lookup_started = time.perf_counter()
    async with async_session_maker() as session:
        # Check for existing verified user
        existing = await session.execute(
            select(User).where(
                (func.lower(User.email) == email.lower())
            ).limit(1)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already registered. Sign in instead.")

        # Check username conflicts (verified users only)
        username_conflict = await session.execute(
            select(User).where(
                (func.lower(User.username) == name.lower()) |
                (func.lower(User.name) == name.lower())
            ).limit(1)
        )
        if username_conflict.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Username already taken. Choose a different one.")

        # Reject duplicate signups while a pending registration is still valid
        now = datetime.utcnow()
        existing_pending = await session.execute(
            select(PendingRegistration).where(
                PendingRegistration.email == email
            ).limit(1)
        )
        pending = existing_pending.scalar_one_or_none()
        if pending:
            if pending.expires_at >= now:
                raise HTTPException(
                    status_code=409,
                    detail="A verification email has already been sent. Check your inbox or wait for it to expire.",
                )
            await session.delete(pending)
            await session.flush()

        lookup_ms = round((time.perf_counter() - lookup_started) * 1000, 2)
        hash_started = time.perf_counter()
        hashed_password = hash_password(body.password)
        hash_ms = round((time.perf_counter() - hash_started) * 1000, 2)

        raw_code = f"{secrets.randbelow(1000000):06d}"

        pending = PendingRegistration(
            id=shortuuid.uuid(),
            name=name,
            email=email,
            hashed_password=hashed_password,
            token_hash=hashlib.sha256(raw_code.encode()).hexdigest(),
            expires_at=now + timedelta(minutes=settings.VERIFICATION_CODE_MINUTES),
            code_attempts=0,
            created_at=now,
        )
        session.add(pending)
        db_started = time.perf_counter()
        await session.commit()
        db_write_ms = round((time.perf_counter() - db_started) * 1000, 2)

        email_started = time.perf_counter()
        try:
            await send_verification_email(email, raw_code)
        except EmailDeliveryError as exc:
            await session.delete(pending)
            await session.commit()
            print(f"auth.register timing lookup_ms={lookup_ms} hash_ms={hash_ms} db_write_ms={db_write_ms} email_ms={round((time.perf_counter() - email_started) * 1000, 2)} total_ms={round((time.perf_counter() - started) * 1000, 2)} result=email_failure")
            raise HTTPException(status_code=503, detail=f"Verification email could not be sent: {exc}") from exc

        email_ms = round((time.perf_counter() - email_started) * 1000, 2)
        total_ms = round((time.perf_counter() - started) * 1000, 2)
        print(f"auth.register timing lookup_ms={lookup_ms} hash_ms={hash_ms} db_write_ms={db_write_ms} email_ms={email_ms} total_ms={total_ms} result=success")

        return {
            "status": "verification_required",
            "email": email,
            "message": "Check your email to activate your account. The code expires in 15 minutes."
        }

class VerifyCodeBody(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


@router.post("/auth/verify-code")
async def verify_code(body: VerifyCodeBody):
    """Verify the 6-digit code sent to the user's email and activate their account."""
    email = body.email.strip().lower()
    code_hash = hashlib.sha256(body.code.encode()).hexdigest()
    now = datetime.utcnow()

    # Per-email rate limit — blocks before DB lookup
    _check_verify_rate_limit(email)

    async with async_session_maker() as session:
        result = await session.execute(select(PendingRegistration).where(PendingRegistration.email == email))
        pending = result.scalar_one_or_none()

        if not pending:
            raise HTTPException(status_code=400, detail="No pending registration found. Please sign up again.")

        if pending.expires_at < now:
            await session.delete(pending)
            await session.commit()
            raise HTTPException(status_code=400, detail="Verification code expired. Please sign up again.")

        # Global + per-email rate limits (DB counter as backup after 3 wrong attempts)
        if pending.code_attempts >= settings.VERIFICATION_CODE_MAX_ATTEMPTS:
            await session.delete(pending)
            await session.commit()
            raise HTTPException(
                status_code=429,
                detail=f"Too many incorrect attempts. Please sign up again.",
            )

        if not secrets.compare_digest(code_hash, pending.token_hash):
            pending.code_attempts += 1
            pending.last_attempt_at = now
            await session.commit()
            # Also record in global in-memory rate limit
            _record_verify_failure(email)
            remaining = settings.VERIFICATION_CODE_MAX_ATTEMPTS - pending.code_attempts
            raise HTTPException(
                status_code=400,
                detail=f"Incorrect code. {remaining} attempt{'s' if remaining != 1 else ''} remaining.",
            )

        # Final check: verified user already exists for this email
        existing_email = await session.execute(select(User).where(func.lower(User.email) == email.lower()))
        if existing_email.scalar_one_or_none():
            await session.delete(pending)
            await session.commit()
            raise HTTPException(status_code=409, detail="Email already registered. Sign in instead.")

        user = User(
            id=shortuuid.uuid(),
            name=pending.name,
            username=pending.name,
            email=pending.email,
            hashed_password=pending.hashed_password,
            role="user",
            tier="v1",
            api_key=create_api_key(),
            credits=100,
            is_active=True,
            email_verified_at=now,
            created_at=now,
        )
        session.add(user)
        await session.delete(pending)
        await session.commit()
        token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})

    return {
        "verified": True,
        "message": "Email verified. Your account is now active.",
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
            "is_active": user.is_active
        },
    }


@router.get("/auth/verify-email")
async def verify_email(token: str):
    raise HTTPException(
        status_code=410,
        detail="Email verification now uses the 6-digit code sent to your inbox. Enter that code on the verification page.",
    )

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


# ─── Personal gateway configuration (user-owned) ───────────────────────
class PersonalGatewayConfigBody(BaseModel):
    provider: str = Field(min_length=1, max_length=64)
    provider_type: str = Field(default="openai", min_length=1, max_length=32)
    api_key: str = Field(min_length=1, max_length=4096)
    default_model: str = Field(min_length=1, max_length=255)
    base_url: Optional[str] = Field(default=None, max_length=512)
    enabled: bool = True


def _personal_gateway_base_url(username: str) -> str:
    return f"{settings.PUBLIC_GATEWAY_BASE_URL.rstrip('/')}/{username}/v1"


def _personal_config_response(config: UserGatewayConfig, username: str) -> dict:
    return {
        "id": config.id,
        "provider": config.provider,
        "provider_type": config.provider_type,
        "default_model": config.default_model,
        "base_url": config.base_url,
        "enabled": bool(config.enabled),
        "gateway_url": _personal_gateway_base_url(username),
        "has_api_key": True,
        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
    }


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
            username=normalize_username(data.name),
            email=normalized_email,
            hashed_password=hash_password(data.password),
            role=data.role,
            tier=data.tier or "v1",
            api_key=api_key,
            credits=data.credits,
            is_active=True,
            email_verified_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
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
        # Cascade delete related data so we dont leave orphaned rows
        from app.db.models import APIKey, UserGatewayConfig, VerificationToken, RequestLog, UsageStats
        from sqlalchemy import delete as sqla_delete
        await session.execute(sqla_delete(APIKey).where(APIKey.user_id == user_id))
        await session.execute(sqla_delete(UserGatewayConfig).where(UserGatewayConfig.user_id == user_id))
        await session.execute(sqla_delete(VerificationToken).where(VerificationToken.user_id == user_id))
        await session.execute(sqla_delete(RequestLog).where(RequestLog.user_id == user_id))


        await session.execute(sqla_delete(UsageStats).where(UsageStats.user_id == user_id))
        await session.delete(u)
        await session.commit()
        return {"deleted": True}
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


@router.get("/gateway/me")
async def get_my_gateway(payload: dict = Depends(require_user)):
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.id == payload["sub"]))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        username = user.username
        if not username:
            username = fallback_username(user.id)
            user.username = username
            await session.commit()
        config_result = await session.execute(select(UserGatewayConfig).where(UserGatewayConfig.user_id == user.id).order_by(UserGatewayConfig.updated_at.desc()))
        configs = config_result.scalars().all()
        return {
            "username": username,
            "base_url": f"{settings.PUBLIC_GATEWAY_BASE_URL.rstrip('/')}/{username}/v1",
            "enabled": any(c.enabled for c in configs),
            "configs": [{"id": c.id, "provider": c.provider, "provider_type": c.provider_type, "default_model": c.default_model, "base_url": c.base_url, "enabled": c.enabled} for c in configs],
        }


class GatewayConfigBody(BaseModel):
    provider: str = Field(min_length=2, max_length=64)
    provider_type: str = Field(default="openai", min_length=3, max_length=32)
    api_key: Optional[str] = Field(default=None, max_length=4096)
    default_model: str = Field(min_length=1, max_length=255)
    base_url: str = Field(min_length=8, max_length=500)
    enabled: bool = True


@router.put("/gateway/me")
async def upsert_my_gateway(body: GatewayConfigBody, payload: dict = Depends(require_user)):
    if body.provider_type not in {"openai", "anthropic"}:
        raise HTTPException(status_code=400, detail="Unsupported provider type")
    if not body.base_url.lower().startswith("https://"):
        raise HTTPException(status_code=400, detail="Base URL must use HTTPS")
    parsed_base_url = __import__("urllib.parse", fromlist=["urlparse"]).urlparse(body.base_url)
    if parsed_base_url.username or parsed_base_url.password or not parsed_base_url.netloc:
        raise HTTPException(status_code=400, detail="Base URL is invalid")
    async with async_session_maker() as session:
        user_result = await session.execute(select(User).where(User.id == payload["sub"]))
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not user.username:
            user.username = fallback_username(user.id)
        result = await session.execute(select(UserGatewayConfig).where(UserGatewayConfig.user_id == user.id, UserGatewayConfig.provider == body.provider))
        config = result.scalar_one_or_none()
        if not config:
            count_result = await session.execute(select(func.count(UserGatewayConfig.id)).where(UserGatewayConfig.user_id == user.id))
            if (count_result.scalar() or 0) >= settings.PERSONAL_GATEWAY_MAX_CONFIGS:
                raise HTTPException(status_code=400, detail="Personal provider configuration limit reached")
            if not body.api_key:
                raise HTTPException(status_code=400, detail="API key is required for a new provider")
            config = UserGatewayConfig(id=shortuuid.uuid(), user_id=user.id, provider=body.provider, provider_type=body.provider_type, encrypted_api_key=encrypt_gateway_secret(body.api_key), default_model=body.default_model, base_url=body.base_url.rstrip('/'), enabled=body.enabled, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
            session.add(config)
        else:
            if body.api_key:
                config.encrypted_api_key = encrypt_gateway_secret(body.api_key)
            config.provider_type = body.provider_type
            config.default_model = body.default_model
            config.base_url = body.base_url.rstrip('/')
            config.enabled = body.enabled
            config.updated_at = datetime.utcnow()
        await session.commit()
        return {"saved": True, "username": user.username, "base_url": f"{settings.PUBLIC_GATEWAY_BASE_URL.rstrip('/')}/{user.username}/v1", "config": {"id": config.id, "provider": config.provider, "provider_type": config.provider_type, "default_model": config.default_model, "base_url": config.base_url, "enabled": config.enabled}}


@router.post("/personal-gateway/{config_id}/test")
async def test_my_gateway(config_id: str, payload: dict = Depends(require_user)):
    started = time.perf_counter()
    async with async_session_maker() as session:
        result = await session.execute(
            select(UserGatewayConfig).where(
                UserGatewayConfig.id == config_id,
                UserGatewayConfig.user_id == payload["sub"],
            )
        )
        config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Gateway configuration not found")
    if not config.enabled:
        raise HTTPException(status_code=409, detail="Personal gateway is disabled")
    try:
        from app.providers.adapters import make_adapter
        adapter = make_adapter({
            "id": config.provider,
            "provider_type": config.provider_type,
            "base_url": config.base_url,
            "api_key": __import__("app.core.auth", fromlist=["decrypt_gateway_secret"]).decrypt_gateway_secret(config.encrypted_api_key),
        })
        result = await adapter.health_check()
        result["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
        return result
    except Exception:
        return {
            "ok": False,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "error": "Provider connection failed",
        }


@router.delete("/gateway/me/{config_id}")
async def delete_my_gateway(config_id: str, payload: dict = Depends(require_user)):
    async with async_session_maker() as session:
        result = await session.execute(select(UserGatewayConfig).where(UserGatewayConfig.id == config_id, UserGatewayConfig.user_id == payload["sub"]))
        config = result.scalar_one_or_none()
        if not config:
            raise HTTPException(status_code=404, detail="Gateway configuration not found")
        await session.delete(config)
        await session.commit()
        return {"deleted": True}