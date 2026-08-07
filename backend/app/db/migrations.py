"""Idempotent authentication migrations for SQLite and Cloudflare D1."""
from sqlalchemy import text

from app.core.config import settings
from app.db.cloudflare import execute as d1_execute, fetchall as d1_fetchall
from app.db.session import USE_D1, engine


async def _d1_table_exists(name: str) -> bool:
    rows = await d1_fetchall("SELECT name FROM sqlite_master WHERE type='table' AND name = ?", [name])
    return bool(rows)


async def migrate_auth_schema() -> None:
    if USE_D1:
        if not await _d1_table_exists("users"):
            return
        columns = await d1_fetchall("PRAGMA table_info(users)")
        names = {row.get("name") for row in columns}
        if "email_verified_at" not in names:
            await d1_execute("ALTER TABLE users ADD COLUMN email_verified_at TEXT")
        await d1_execute(
            """CREATE TABLE IF NOT EXISTS verification_tokens (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT UNIQUE NOT NULL,
                expires_at TEXT NOT NULL,
                used_at TEXT,
                created_at TEXT NOT NULL
            )"""
        )
        await d1_execute("CREATE INDEX IF NOT EXISTS idx_verification_tokens_hash ON verification_tokens(token_hash)")
        await d1_execute("CREATE INDEX IF NOT EXISTS idx_verification_tokens_user ON verification_tokens(user_id)")
        return

    async with engine.begin() as connection:
        columns = await connection.execute(text("PRAGMA table_info(users)"))
        names = {row[1] for row in columns.fetchall()}
        if "email_verified_at" not in names:
            await connection.execute(text("ALTER TABLE users ADD COLUMN email_verified_at DATETIME"))
        await connection.execute(text(
            """CREATE TABLE IF NOT EXISTS verification_tokens (
                id VARCHAR(255) PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                token_hash VARCHAR(255) UNIQUE NOT NULL,
                expires_at DATETIME NOT NULL,
                used_at DATETIME,
                created_at DATETIME NOT NULL
            )""")
        )
        await connection.execute(text("CREATE INDEX IF NOT EXISTS idx_verification_tokens_hash ON verification_tokens(token_hash)"))
        await connection.execute(text("CREATE INDEX IF NOT EXISTS idx_verification_tokens_user ON verification_tokens(user_id)"))


async def cleanup_legacy_users() -> dict:
    """Preserve only the configured admin row and remove all old users."""
    if USE_D1:
        admin_rows = await d1_fetchall("SELECT id FROM users WHERE lower(email) = lower(?) AND role = 'admin'", [settings.ADMIN_EMAIL])
        if len(admin_rows) != 1:
            raise RuntimeError("Expected exactly one configured admin row before cleanup")
        admin_id = admin_rows[0]["id"]
        await d1_execute("DELETE FROM verification_tokens WHERE user_id != ?", [admin_id])
        await d1_execute("DELETE FROM api_keys WHERE user_id != ?", [admin_id])
        await d1_execute("DELETE FROM users WHERE id != ?", [admin_id])
        await d1_execute("UPDATE users SET email_verified_at = COALESCE(email_verified_at, CURRENT_TIMESTAMP), is_active = 1 WHERE id = ?", [admin_id])
        return {"admin_id": admin_id, "deleted_non_admins": True}

    async with engine.begin() as connection:
        result = await connection.execute(text("SELECT id FROM users WHERE lower(email) = lower(:email) AND role = 'admin'"), {"email": settings.ADMIN_EMAIL})
        rows = result.fetchall()
        if len(rows) != 1:
            raise RuntimeError("Expected exactly one configured admin row before cleanup")
        admin_id = rows[0][0]
        await connection.execute(text("DELETE FROM verification_tokens WHERE user_id != :id"), {"id": admin_id})
        await connection.execute(text("DELETE FROM api_keys WHERE user_id != :id"), {"id": admin_id})
        await connection.execute(text("DELETE FROM users WHERE id != :id"), {"id": admin_id})
        await connection.execute(text("UPDATE users SET email_verified_at = COALESCE(email_verified_at, CURRENT_TIMESTAMP), is_active = 1 WHERE id = :id"), {"id": admin_id})
        return {"admin_id": admin_id, "deleted_non_admins": True}
