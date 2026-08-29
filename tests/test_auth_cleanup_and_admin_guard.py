import asyncio
import os
import tempfile
from pathlib import Path
from datetime import datetime

import pytest
from fastapi import HTTPException

DB_FILE = Path(tempfile.gettempdir()) / "saki-auth-cleanup-guard.db"
if DB_FILE.exists():
    DB_FILE.unlink()
os.environ.update({
    "USE_D1": "false",
    "DATABASE_URL": f"sqlite+aiosqlite:///{DB_FILE}",
    "ADMIN_EMAIL": "admin@example.com",
    "SECRET_KEY": "cleanup-test-secret",
})
# Make the cached settings singleton reflect THIS module's env (it was created at first import by an earlier test module)
import sys as _sys
_backend_dir = str(__import__("pathlib").Path(__file__).parents[1] / "backend")
if _backend_dir not in _sys.path:
    _sys.path.insert(0, _backend_dir)
from app.core.config import settings as _settings_singleton
_settings_singleton.refresh_from_env()


import sys
sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

from app.db.session import reconfigure_from_env
reconfigure_from_env()

from sqlalchemy import select
from app.core.auth import create_access_token, hash_password
from app.db.models import Base, User
from app.db import session as db_session
from app.db.migrations import cleanup_legacy_users, migrate_auth_schema
from app.api.v1.admin import delete_user

# Other test modules run their module bodies (env overrides + engine
# reconfigure) before this test executes, so re-assert THIS module's env
# and rebind the engine at test time.
os.environ.update({
    "USE_D1": "false",
    "DATABASE_URL": f"sqlite+aiosqlite:///{DB_FILE}",
    "ADMIN_EMAIL": "admin@example.com",
    "SECRET_KEY": "cleanup-test-secret",
})
_settings_singleton.refresh_from_env()
reconfigure_from_env()


@pytest.mark.asyncio
async def test_cleanup_and_admin_delete_guard():
    async with db_session.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with db_session.async_session_maker() as session:
        session.add_all([
            User(id="admin", name="Admin", username="admin", email="admin@example.com", role="admin", is_active=True, email_verified_at=datetime.utcnow(), hashed_password=hash_password("AdminPass!123")),
            User(id="old", name="Old", username="old", email="old@example.com", role="user", is_active=True, email_verified_at=datetime.utcnow(), hashed_password=hash_password("OldPass!123")),
        ])
        await session.commit()

    await migrate_auth_schema()
    result = await cleanup_legacy_users()
    assert result["admin_id"] == "admin"
    async with db_session.async_session_maker() as session:
        users = (await session.execute(select(User))).scalars().all()
        assert len(users) == 1 and users[0].id == "admin"

    admin_token = create_access_token({"sub": "admin", "role": "admin"})
    with pytest.raises(HTTPException) as exc:
        await delete_user("admin", {"sub": "admin", "role": "admin"})
    assert exc.value.status_code == 403

    assert admin_token
