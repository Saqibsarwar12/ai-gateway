import asyncio
import hashlib
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

DB_FILE = Path(tempfile.gettempdir()) / "saki-pytest-auth-regressions.db"
if DB_FILE.exists():
    DB_FILE.unlink()
os.environ.update({
    "USE_D1": "false",
    "DATABASE_URL": f"sqlite+aiosqlite:///{DB_FILE}",
    "ADMIN_EMAIL": "admin@example.com",
    "SECRET_KEY": "pytest-secret",
    "BREVO_API_KEY": "pytest-key",
    "EMAIL_FROM": "no-reply@saki-verifier.ryzedns.org",
    "EMAIL_FROM_NAME": "Saki Gateway",
})
import sys
sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

from app.db.session import engine, async_session_maker
from app.db.models import Base, PendingRegistration, User
from app.core.auth import hash_password
from app.api.v1 import admin
from app.main import app


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
def setup_db():
    async def setup():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    asyncio.run(setup())
    return True


@pytest.mark.asyncio
async def test_auth_flow_and_verification(setup_db, monkeypatch):
    sent = []

    async def fake_email(recipient, code):
        sent.append((recipient, code))

    monkeypatch.setattr(admin, "send_verification_email", fake_email)
    admin._login_attempts.clear()
    request = __import__("starlette.requests", fromlist=["Request"]).Request(
        {"type": "http", "method": "POST", "path": "/", "headers": [(b"x-forwarded-for", b"127.0.0.1")]}
    )
    response = await admin.register(admin.RegisterBody(name="hari", email="hari@example.com", password="Password!123"), request)
    assert response["status"] == "verification_required"
    assert sent and sent[0][0] == "hari@example.com"

    with pytest.raises(HTTPException) as exc:
        await admin.login(admin.LoginBody(identifier="hari@example.com", password="Password!123"), request)
    assert exc.value.status_code == 401

    verified = await admin.verify_code(admin.VerifyCodeBody(email="hari@example.com", code=sent[0][1]))
    assert verified["verified"] is True
    logged_in = await admin.login(admin.LoginBody(identifier="hari@example.com", password="Password!123"), request)
    assert logged_in["user"]["email"] == "hari@example.com"

    with pytest.raises(HTTPException) as exc:
        await admin.verify_code(admin.VerifyCodeBody(email="hari@example.com", code=sent[0][1]))
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_duplicate_registration_and_expired_pending(setup_db, monkeypatch):
    async def fake_email(recipient, code):
        return None

    monkeypatch.setattr(admin, "send_verification_email", fake_email)
    admin._login_attempts.clear()
    request = __import__("starlette.requests", fromlist=["Request"]).Request(
        {"type": "http", "method": "POST", "path": "/", "headers": [(b"x-forwarded-for", b"127.0.0.2")]}
    )
    with pytest.raises(HTTPException) as exc:
        await admin.register(admin.RegisterBody(name="hari", email="hari@example.com", password="Password!123"), request)
    assert exc.value.status_code == 409

    async with async_session_maker() as session:
        pending = PendingRegistration(
            id="expired-pending", name="expired", email="expired@example.com",
            hashed_password=hash_password("Password!123"), token_hash=hashlib.sha256(b"expired").hexdigest(),
            expires_at=datetime.utcnow() - timedelta(minutes=1), created_at=datetime.utcnow(),
        )
        session.add(pending)
        await session.commit()
    with pytest.raises(HTTPException) as exc:
        await admin.verify_code(admin.VerifyCodeBody(email="expired@example.com", code="0000"))
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_health_and_openapi(setup_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/health")).status_code == 200
        assert (await client.get("/openapi.json")).status_code == 200
