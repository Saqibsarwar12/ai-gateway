"""End-to-end auth tests for Saki Gateway: register -> email -> verify -> login,
blocked unverified login, expired tokens, duplicate signup, admin protection,
logout, disabled-user, invalid-token. Brevo is mocked so no real email is sent.

The register flow passes the raw 6-digit code and the verify URL to
send_verification_email(); only their SHA-256 hashes are persisted.
Tests therefore capture the code/link from the mock's call args rather than
reading the DB.
"""

import asyncio
import os
import sqlite3
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

DB_FILE = Path(tempfile.gettempdir()) / "saki-auth-e2e.db"
if DB_FILE.exists():
    DB_FILE.unlink()

os.environ.update(
    {
        "USE_D1": "false",
        "DATABASE_URL": f"sqlite+aiosqlite:///{DB_FILE}",
        "ADMIN_EMAIL": "admin@sakigateway.dev",
        "ADMIN_PASSWORD": "AdminPass!2026",
        "SECRET_KEY": "e2e-test-secret-very-long-and-random",
        "BREVO_API_KEY": "test-brevo-key",
        "EMAIL_FROM": "no-reply@saki-verifier.org",
        "EMAIL_FROM_NAME": "Saki Gateway",
        "FRONTEND_BASE_URL": "https://frontend.test",
        "PUBLIC_GATEWAY_BASE_URL": "https://api.test",
        "APP_BASE_URL": "https://api.test",
        "VERIFICATION_CODE_MINUTES": "15",
        "AUTH_RATE_LIMIT_MAX_ATTEMPTS": "1000",  # loosen for the test run
    }
)
# Make the cached settings singleton reflect THIS module's env (it was created at first import by an earlier test module)
import sys as _sys
_backend_dir = str(__import__("pathlib").Path(__file__).parents[1] / "backend")
if _backend_dir not in _sys.path:
    _sys.path.insert(0, _backend_dir)
from app.core.config import settings as _settings_singleton
_settings_singleton.refresh_from_env()


import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

from app.core.config import settings as _settings_singleton
_settings_singleton.refresh_from_env()


from app.db.models import Base
from app.db.session import async_session_maker, engine, reconfigure_from_env

reconfigure_from_env()

ADMIN_EMAIL = os.environ["ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def app(event_loop):
    # pytest imports every test module BEFORE running any fixture, so a
    # later-collected module (e.g. test_custom_prompts.py) may have
    # overwritten os.environ and the cached settings after this module's
    # body ran. Re-assert THIS module's env before seeding.
    os.environ.update(
        {
            "USE_D1": "false",
            "DATABASE_URL": f"sqlite+aiosqlite:///{DB_FILE}",
            "ADMIN_EMAIL": "admin@sakigateway.dev",
            "ADMIN_PASSWORD": "AdminPass!2026",
            "SECRET_KEY": "e2e-test-secret-very-long-and-random",
            "AUTH_RATE_LIMIT_MAX_ATTEMPTS": "1000",
        }
    )
    from app.core.config import settings as _s
    _s.refresh_from_env()

    from app.core.auth import hash_password
    from app.core.config import settings
    from app.db.models import User
    from app.db import session as db_session

    db_session.reconfigure_from_env()

    async def _seed():
        async with db_session.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with db_session.async_session_maker() as session:
            existing = await session.execute(
                select(User).where(User.email == settings.ADMIN_EMAIL)
            )
            if not existing.scalar_one_or_none():
                session.add(
                    User(
                        id="admin-001",
                        name="Admin",
                        username="admin",
                        email=settings.ADMIN_EMAIL,
                        role="admin",
                        is_active=True,
                        email_verified_at=datetime.utcnow(),
                        hashed_password=hash_password(settings.ADMIN_PASSWORD),
                    )
                )
                await session.commit()

    event_loop.run_until_complete(_seed())

    from app.main import app as fastapi_app  # noqa: E402
    fastapi_app.dependency_overrides = {}
    return fastapi_app


@pytest.fixture()
def client(app):
    from app.db import kv as rate_limit_kv

    rate_limit_kv._memory_store.clear()
    return TestClient(app, base_url="http://testserver")


def _register(client, email, name="New User", password="NewUser!Pass2026"):
    """Register a fresh user, returning (response, code, link_url).

    Patches send_verification_email with an AsyncMock so we can replay the
    raw code/url it was called with (only hashes are stored in the DB).
    """
    from app.api.v1 import admin as admin_module

    mail_mock = AsyncMock()
    with patch.object(admin_module, "send_verification_email", new=mail_mock):
        r = client.post(
            "/admin/auth/register",
            json={"email": email, "password": password, "name": name},
        )
    code, link = None, None
    for call in reversed(mail_mock.call_args_list):
        args, kwargs = call.args, call.kwargs
        recipient = (args[0] if args else kwargs.get("recipient", "")).lower()
        if recipient == email.lower():
            code = args[1] if len(args) > 1 else kwargs.get("verification_code")
            link = kwargs.get("verification_url") or (args[2] if len(args) > 2 else None)
            break
    return r, code, link


@pytest.fixture
def fresh_email():
    return f"newuser-{uuid.uuid4().hex[:8]}@example.org"


def test_admin_login_works(client):
    """Requirement: admin account continues to work normally."""
    r = client.post(
        "/admin/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert r.status_code == 200, r.text
    assert r.json()["user"]["role"] == "admin"
    assert "api_key" in r.json()["user"], "admin login must expose api_key"


def test_signup_creates_pending_not_active(client, fresh_email):
    """Requirement: new users register through the flow and are NOT active until verified."""
    r, code, link = _register(client, fresh_email, name="New User")
    assert r.status_code in (200, 201), r.text
    assert r.json().get("status") == "verification_required", r.text
    assert code and len(code) == 6, f"expected 6-digit code, got {code!r}"
    assert link and link.startswith("https")
    # No active User row should exist yet
    conn = sqlite3.connect(str(DB_FILE))
    try:
        active = conn.execute(
            "SELECT COUNT(*) FROM users WHERE lower(email) = lower(?)", (fresh_email,)
        ).fetchone()[0]
    finally:
        conn.close()
    assert active == 0, "registration must not create an active user prematurely"


def test_login_blocked_before_verification(client, fresh_email):
    """Requirement: login must be blocked until verification completes."""
    _register(client, fresh_email, name="Unverified")
    r = client.post(
        "/admin/auth/login",
        json={"email": fresh_email, "password": "NewUser!Pass2026"},
    )
    assert r.status_code == 401, r.text
    assert r.headers.get("X-Needs-Verification") == "true"
    assert "not verified" in r.json()["detail"].lower()


def test_verify_code_flow(client, fresh_email):
    """Requirement: verify-code -> activated -> login allowed (clean path)."""
    _, code, _ = _register(client, fresh_email, name="Verified")
    assert code, "register did not yield a code"
    r = client.post("/admin/auth/verify-code", json={"email": fresh_email, "code": code})
    assert r.status_code == 200, r.text
    body = r.json()
    # verify-code returns is_active on the merged user record
    assert body.get("is_active") is True or body.get("verified") is True, body
    r = client.post(
        "/admin/auth/login",
        json={"email": fresh_email, "password": "NewUser!Pass2026"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["user"]["email"].lower() == fresh_email.lower()


def test_verify_link_activates(client, fresh_email):
    """Requirement: verification link works end-to-end."""
    _, _, link = _register(client, fresh_email, name="Linkuser")
    assert link and "token=" in link, f"link missing token: {link}"
    token = link.split("token=")[-1]
    r = client.get("/admin/auth/verify-email", params={"token": token}, follow_redirects=False)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("verified") is True or body.get("is_active") is True, body
    # And login should now work
    r = client.post(
        "/admin/auth/login",
        json={"email": fresh_email, "password": "NewUser!Pass2026"},
    )
    assert r.status_code == 200, r.text


def test_expired_token_fails(client, fresh_email):
    """Requirement: expired links must fail safely."""
    _, _, link = _register(client, fresh_email, name="Expired")
    # Force the pending row to be expired
    conn = sqlite3.connect(str(DB_FILE))
    try:
        conn.execute(
            "UPDATE pending_registrations SET expires_at = ? WHERE lower(email) = lower(?)",
            (datetime.utcnow() - timedelta(minutes=30), fresh_email),
        )
        conn.commit()
    finally:
        conn.close()
    token = link.split("token=")[-1]
    r = client.get("/admin/auth/verify-email", params={"token": token}, follow_redirects=False)
    assert r.status_code in (400, 403, 410), (r.status_code, r.text)
    # No active user created
    conn = sqlite3.connect(str(DB_FILE))
    try:
        active = conn.execute(
            "SELECT COUNT(*) FROM users WHERE lower(email) = lower(?)", (fresh_email,)
        ).fetchone()[0]
    finally:
        conn.close()
    assert active == 0


def test_invalid_token_fails(client):
    """Requirement: invalid links must fail safely."""
    r = client.get(
        "/admin/auth/verify-email",
        params={"token": "totally-bogus-token-not-in-db"},
        follow_redirects=False,
    )
    assert r.status_code in (400, 403, 404, 410)


def test_expired_code_fails(client, fresh_email):
    """Requirement: expired verification codes must fail safely."""
    _, code, _ = _register(client, fresh_email, name="ExpiredCode")
    conn = sqlite3.connect(str(DB_FILE))
    try:
        conn.execute(
            "UPDATE pending_registrations SET expires_at = ? WHERE lower(email) = lower(?)",
            (datetime.utcnow() - timedelta(minutes=30), fresh_email),
        )
        conn.commit()
    finally:
        conn.close()
    r = client.post("/admin/auth/verify-code", json={"email": fresh_email, "code": code})
    assert r.status_code in (400, 403, 410), (r.status_code, r.text)


def test_wrong_code_does_not_activate(client, fresh_email):
    """Requirement: invalid code does not grant access and does not activate."""
    _register(client, fresh_email, name="Wrong")
    r = client.post("/admin/auth/verify-code", json={"email": fresh_email, "code": "000000"})
    assert r.status_code in (400, 403, 429), r.text
    conn = sqlite3.connect(str(DB_FILE))
    try:
        active = conn.execute(
            "SELECT COUNT(*) FROM users WHERE lower(email) = lower(?)", (fresh_email,)
        ).fetchone()[0]
    finally:
        conn.close()
    assert active == 0


def test_duplicate_signup_clean(client, fresh_email):
    """Requirement: duplicate signups handled cleanly (no second active account)."""
    first, _, _ = _register(client, fresh_email, name="Dup One")
    assert first.status_code in (200, 201), first.text
    second, _, _ = _register(client, fresh_email, name="Dup Two")
    # Second attempt while a pending registration exists must not silently create a User
    assert second.status_code in (200, 201, 409, 400, 403), second.text
    conn = sqlite3.connect(str(DB_FILE))
    try:
        active = conn.execute(
            "SELECT COUNT(*) FROM users WHERE lower(email) = lower(?)", (fresh_email,)
        ).fetchone()[0]
    finally:
        conn.close()
    assert active == 0, "unverified duplicate signup must not create a verified user"


def test_register_blocked_for_admin_email(client):
    """Requirement: the configured admin email cannot be registered as a new user."""
    r, _, _ = _register(client, ADMIN_EMAIL, name="Imposter")
    assert r.status_code == 409, r.text
    assert "cannot be registered" in r.json()["detail"].lower()


def test_login_disabled_user(client, fresh_email):
    """Requirement: disabled accounts cannot log in."""
    _, code, _ = _register(client, fresh_email, name="Disable")
    r = client.post("/admin/auth/verify-code", json={"email": fresh_email, "code": code})
    assert r.status_code == 200, r.text
    conn = sqlite3.connect(str(DB_FILE))
    try:
        conn.execute(
            "UPDATE users SET is_active = 0 WHERE lower(email) = lower(?)", (fresh_email,)
        )
        conn.commit()
    finally:
        conn.close()
    r = client.post(
        "/admin/auth/login",
        json={"email": fresh_email, "password": "NewUser!Pass2026"},
    )
    assert r.status_code == 403, r.text
    assert "disabled" in r.json()["detail"].lower()


def test_admin_cannot_be_deleted():
    """Requirement: admin account protected from deletion."""
    from app.api.v1.admin import delete_user
    from fastapi import HTTPException

    loop = asyncio.new_event_loop()
    try:
        with pytest.raises(HTTPException) as exc:
            loop.run_until_complete(
                delete_user("admin-001", {"sub": "admin-001", "role": "admin"})
            )
        assert exc.value.status_code == 403
    finally:
        loop.close()


def test_logout_clears_session(client):
    """Requirement: logout invalidates session."""
    login = client.post(
        "/admin/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert login.status_code == 200, login.text
    r = client.post("/admin/auth/logout")
    assert r.status_code == 200
    # Cookie should be cleared (Set-Cookie with empty/max-age=0)
    set_cookie = r.headers.get("set-cookie", "")
    assert "Max-Age=0" in set_cookie or "expires=Thu, 01 Jan 1970" in set_cookie or ('"%s"' % "") in set_cookie, set_cookie


def test_password_never_plaintext():
    """Security: stored password hashes are not plaintext."""
    from app.core.auth import hash_password

    pw = "SomeSecret!2026"
    h = hash_password(pw)
    assert h != pw
    assert "$" in h and len(h) >= 60, "hash should be salted pbkdf2 format"


def test_unknown_route_404s_safely(client):
    """Smoke: unknown admin route returns 404/405, not a 500 stack trace."""
    r = client.get("/admin/does-not-exist")
    assert r.status_code in (404, 405, 422)
