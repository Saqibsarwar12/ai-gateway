"""Idempotent authentication and personal gateway migrations."""
import asyncio

from sqlalchemy import text

from app.core.config import settings
from app.db.cloudflare import execute as d1_execute, fetchall as d1_fetchall
from app.db import session as db_session

USE_D1 = db_session.USE_D1


async def _d1_table_exists(name: str) -> bool:
    rows = await d1_fetchall("SELECT name FROM sqlite_master WHERE type='table' AND name = ?", [name])
    return bool(rows)


async def migrate_auth_schema() -> None:
    if USE_D1:
        if not await _d1_table_exists("users"):
            return
        columns = await d1_fetchall("PRAGMA table_info(users)")
        names = {row.get("name") for row in columns}
        additions = {
            "tier": "TEXT DEFAULT 'v1'",
            "credits": "INTEGER DEFAULT 100",
            "is_active": "INTEGER DEFAULT 1",
            "email_verified_at": "TEXT",
            "extra_metadata": "TEXT",
            "username": "TEXT",
        }
        for column, definition in additions.items():
            if column not in names:
                await d1_execute(f'ALTER TABLE users ADD COLUMN "{column}" {definition}')
        await d1_execute("UPDATE users SET username = lower(name) WHERE username IS NULL OR username = ''")
        await d1_execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        model_columns = await d1_fetchall("PRAGMA table_info(models)")
        model_names = {row.get("name") for row in model_columns}
        model_additions = {
            "model_id": "TEXT",
            "mode": "TEXT DEFAULT 'chat'",
            "input_cost_per_1m": "REAL DEFAULT 0",
            "output_cost_per_1m": "REAL DEFAULT 0",
            "context_window": "INTEGER DEFAULT 8192",
            "supports_functions": "INTEGER DEFAULT 0",
            "supports_vision": "INTEGER DEFAULT 0",
            "is_active": "INTEGER DEFAULT 1",
            "min_tier": "TEXT DEFAULT 'v1'",
            "created_at": "TEXT",
        }
        for column, definition in model_additions.items():
            if column not in model_names:
                await d1_execute(f'ALTER TABLE models ADD COLUMN "{column}" {definition}')
        await d1_execute("UPDATE models SET model_id = COALESCE(model_id, id) WHERE model_id IS NULL OR model_id = ''")
        await d1_execute("UPDATE models SET is_active = COALESCE(is_active, 1) WHERE is_active IS NULL")
        provider_columns = await d1_fetchall("PRAGMA table_info(providers)")
        provider_names = {row.get("name") for row in provider_columns}
        provider_additions = {
            "provider_type": "TEXT DEFAULT 'openai'",
            "api_key": "TEXT",
            "enabled": "INTEGER DEFAULT 1",
            "priority": "INTEGER DEFAULT 100",
            "max_rpm": "INTEGER DEFAULT 1000",
            "max_tpm": "INTEGER DEFAULT 100000",
            "current_rpm": "INTEGER DEFAULT 0",
            "current_tpm": "INTEGER DEFAULT 0",
            "avg_latency_ms": "REAL DEFAULT 0",
            "success_rate": "REAL DEFAULT 100",
            "is_healthy": "INTEGER DEFAULT 1",
            "requires_proxy": "INTEGER DEFAULT 0",
            "proxy_url": "TEXT",
            "models": "TEXT",
            "extra_config": "TEXT",
            "created_at": "TEXT",
            "updated_at": "TEXT",
        }
        for column, definition in provider_additions.items():
            if column not in provider_names:
                await d1_execute(f'ALTER TABLE providers ADD COLUMN "{column}" {definition}')
        await d1_execute("UPDATE providers SET provider_type = COALESCE(provider_type, 'openai') WHERE provider_type IS NULL OR provider_type = ''")
        await d1_execute("""CREATE TABLE IF NOT EXISTS user_gateway_configs (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            provider_type TEXT NOT NULL DEFAULT 'openai',
            encrypted_api_key TEXT NOT NULL,
            default_model TEXT NOT NULL,
            base_url TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")
        await d1_execute("CREATE INDEX IF NOT EXISTS idx_gateway_configs_user ON user_gateway_configs(user_id)")
        await d1_execute("CREATE INDEX IF NOT EXISTS idx_gateway_configs_user_provider ON user_gateway_configs(user_id, provider)")
        await d1_execute("""CREATE TABLE IF NOT EXISTS nvidia_smart_configs (
            id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL DEFAULT 'NVIDIA Smart',
            public_model_id TEXT NOT NULL UNIQUE DEFAULT 'nvidia-smart',
            base_url TEXT NOT NULL DEFAULT 'https://integrate.api.nvidia.com/v1',
            enabled INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")
        await d1_execute("""CREATE TABLE IF NOT EXISTS nvidia_smart_accounts (
            id TEXT PRIMARY KEY,
            config_id TEXT NOT NULL,
            label TEXT NOT NULL,
            encrypted_api_key TEXT NOT NULL,
            model_id TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'healthy',
            cooldown_until TEXT,
            consecutive_failures INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            failure_count INTEGER DEFAULT 0,
            avg_latency_ms REAL DEFAULT 0,
            last_status_code INTEGER,
            last_error_code TEXT,
            last_error_at TEXT,
            last_used_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")
        await d1_execute("CREATE INDEX IF NOT EXISTS idx_nvidia_smart_accounts_config ON nvidia_smart_accounts(config_id)")
        await d1_execute("CREATE INDEX IF NOT EXISTS idx_nvidia_smart_accounts_status ON nvidia_smart_accounts(config_id, status)")
        nvidia_columns = await d1_fetchall("PRAGMA table_info(nvidia_smart_accounts)")
        nvidia_names = {row.get("name") for row in nvidia_columns}
        if "failure_count" not in nvidia_names:
            await d1_execute("ALTER TABLE nvidia_smart_accounts ADD COLUMN failure_count INTEGER DEFAULT 0")
        if "avg_latency_ms" not in nvidia_names:
            await d1_execute("ALTER TABLE nvidia_smart_accounts ADD COLUMN avg_latency_ms REAL DEFAULT 0")
        await d1_execute("""CREATE TABLE IF NOT EXISTS verification_tokens (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token_hash TEXT UNIQUE NOT NULL,
            verification_link_hash TEXT UNIQUE,
            expires_at TEXT NOT NULL,
            used_at TEXT,
            created_at TEXT NOT NULL
        )""")
        token_columns = await d1_fetchall("PRAGMA table_info(verification_tokens)")
        token_names = {row.get("name") for row in token_columns}
        if "verification_link_hash" not in token_names:
            await d1_execute("ALTER TABLE verification_tokens ADD COLUMN verification_link_hash TEXT")
        await d1_execute("""CREATE TABLE IF NOT EXISTS pending_registrations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            token_hash TEXT UNIQUE NOT NULL,
            verification_link_hash TEXT UNIQUE,
            role TEXT NOT NULL DEFAULT 'user',
            tier TEXT NOT NULL DEFAULT 'v1',
            credits INTEGER NOT NULL DEFAULT 100,
            expires_at TEXT NOT NULL,
            code_attempts INTEGER NOT NULL DEFAULT 0,
            last_attempt_at TEXT,
            created_at TEXT NOT NULL
        )""")
        pending_columns = await d1_fetchall("PRAGMA table_info(pending_registrations)")
        pending_names = {row.get("name") for row in pending_columns}
        for column, definition in {
            "verification_link_hash": "TEXT",
            "role": "TEXT NOT NULL DEFAULT 'user'",
            "tier": "TEXT NOT NULL DEFAULT 'v1'",
            "credits": "INTEGER NOT NULL DEFAULT 100",
        }.items():
            if column not in pending_names:
                await d1_execute(f'ALTER TABLE pending_registrations ADD COLUMN "{column}" {definition}')
        pending_columns = await d1_fetchall("PRAGMA table_info(pending_registrations)")
        pending_names = {row.get("name") for row in pending_columns}
        if "code_attempts" not in pending_names:
            await d1_execute("ALTER TABLE pending_registrations ADD COLUMN code_attempts INTEGER NOT NULL DEFAULT 0")
        if "last_attempt_at" not in pending_names:
            await d1_execute("ALTER TABLE pending_registrations ADD COLUMN last_attempt_at TEXT")
        await d1_execute("CREATE INDEX IF NOT EXISTS idx_pending_registrations_email ON pending_registrations(email)")
        await d1_execute("""CREATE TABLE IF NOT EXISTS custom_prompts (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            model_pattern TEXT NOT NULL DEFAULT '*',
            content TEXT NOT NULL,
            preset TEXT NOT NULL DEFAULT 'custom',
            is_active INTEGER DEFAULT 1,
            is_default INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")
        await d1_execute("CREATE INDEX IF NOT EXISTS idx_custom_prompts_user ON custom_prompts(user_id)")
        await d1_execute("CREATE INDEX IF NOT EXISTS idx_custom_prompts_user_model ON custom_prompts(user_id, model_pattern)")
        await d1_execute("CREATE TABLE IF NOT EXISTS auth_migrations (migration_key TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
        return

    async with db_session.engine.begin() as connection:
        columns = await connection.execute(text("PRAGMA table_info(users)"))
        names = {row[1] for row in columns.fetchall()}
        if "email_verified_at" not in names:
            await connection.execute(text("ALTER TABLE users ADD COLUMN email_verified_at DATETIME"))
        if "is_active" not in names:
            await connection.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1"))
        if "username" not in names:
            await connection.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(64)"))
        await connection.execute(text("UPDATE users SET username = lower(name) WHERE username IS NULL OR username = ''"))
        await connection.execute(text("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)"))
        model_columns = await connection.execute(text("PRAGMA table_info(models)"))
        model_names = {row[1] for row in model_columns.fetchall()}
        model_additions = {
            "model_id": "VARCHAR(255)",
            "mode": "VARCHAR(32) DEFAULT 'chat'",
            "input_cost_per_1m": "FLOAT DEFAULT 0",
            "output_cost_per_1m": "FLOAT DEFAULT 0",
            "context_window": "INTEGER DEFAULT 8192",
            "supports_functions": "BOOLEAN DEFAULT 0",
            "supports_vision": "BOOLEAN DEFAULT 0",
            "is_active": "BOOLEAN DEFAULT 1",
            "min_tier": "VARCHAR(16) DEFAULT 'v1'",
            "created_at": "DATETIME",
        }
        for column, definition in model_additions.items():
            if column not in model_names:
                await connection.execute(text(f'ALTER TABLE models ADD COLUMN "{column}" {definition}'))
        await connection.execute(text("UPDATE models SET model_id = COALESCE(model_id, id) WHERE model_id IS NULL OR model_id = ''"))
        await connection.execute(text("UPDATE models SET is_active = COALESCE(is_active, 1) WHERE is_active IS NULL"))
        provider_columns = await connection.execute(text("PRAGMA table_info(providers)"))
        provider_names = {row[1] for row in provider_columns.fetchall()}
        if "provider_type" not in provider_names:
            await connection.execute(text("ALTER TABLE providers ADD COLUMN provider_type VARCHAR(50) NOT NULL DEFAULT 'openai'"))
        await connection.execute(text("UPDATE providers SET provider_type = COALESCE(provider_type, 'openai') WHERE provider_type IS NULL OR provider_type = ''"))
        await connection.execute(text("""CREATE TABLE IF NOT EXISTS verification_tokens (
            id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            token_hash VARCHAR(255) UNIQUE NOT NULL,
            verification_link_hash VARCHAR(255) UNIQUE,
            expires_at DATETIME NOT NULL,
            used_at DATETIME,
            created_at DATETIME NOT NULL
        )"""))
        await connection.execute(text("""CREATE TABLE IF NOT EXISTS pending_registrations (
            id VARCHAR(255) PRIMARY KEY,
            name VARCHAR(64) NOT NULL,
            email VARCHAR(320) UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            token_hash VARCHAR(255) UNIQUE NOT NULL,
            verification_link_hash VARCHAR(255) UNIQUE,
            role VARCHAR(32) NOT NULL DEFAULT 'user',
            tier VARCHAR(16) NOT NULL DEFAULT 'v1',
            credits INTEGER NOT NULL DEFAULT 100,
            expires_at DATETIME NOT NULL,
            code_attempts INTEGER NOT NULL DEFAULT 0,
            last_attempt_at DATETIME,
            created_at DATETIME NOT NULL
        )"""))
        pending_columns = await connection.execute(text("PRAGMA table_info(pending_registrations)"))
        pending_names = {row[1] for row in pending_columns.fetchall()}
        for column, definition in {
            "verification_link_hash": "VARCHAR(255)",
            "role": "VARCHAR(32) NOT NULL DEFAULT 'user'",
            "tier": "VARCHAR(16) NOT NULL DEFAULT 'v1'",
            "credits": "INTEGER NOT NULL DEFAULT 100",
        }.items():
            if column not in pending_names:
                await connection.execute(text(f'ALTER TABLE pending_registrations ADD COLUMN "{column}" {definition}'))
        await connection.execute(text("CREATE INDEX IF NOT EXISTS idx_pending_registrations_email ON pending_registrations(email)"))
        await connection.execute(text("""CREATE TABLE IF NOT EXISTS custom_prompts (
            id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            name VARCHAR(120) NOT NULL,
            model_pattern VARCHAR(255) NOT NULL DEFAULT '*',
            content TEXT NOT NULL,
            preset VARCHAR(32) NOT NULL DEFAULT 'custom',
            is_active BOOLEAN DEFAULT 1,
            is_default BOOLEAN DEFAULT 0,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )"""))
        await connection.execute(text("CREATE INDEX IF NOT EXISTS idx_custom_prompts_user ON custom_prompts(user_id)"))
        await connection.execute(text("CREATE INDEX IF NOT EXISTS idx_custom_prompts_user_model ON custom_prompts(user_id, model_pattern)"))
        await connection.execute(text("""CREATE TABLE IF NOT EXISTS user_gateway_configs (
            id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            provider VARCHAR(100) NOT NULL,
            provider_type VARCHAR(50) NOT NULL DEFAULT 'openai',
            encrypted_api_key TEXT NOT NULL,
            default_model VARCHAR(255) NOT NULL,
            base_url VARCHAR(500) NOT NULL,
            enabled BOOLEAN DEFAULT 1,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )"""))
        await connection.execute(text("CREATE INDEX IF NOT EXISTS idx_gateway_configs_user ON user_gateway_configs(user_id)"))
        await connection.execute(text("CREATE INDEX IF NOT EXISTS idx_gateway_configs_user_provider ON user_gateway_configs(user_id, provider)"))
        await connection.execute(text("""CREATE TABLE IF NOT EXISTS nvidia_smart_configs (
            id VARCHAR(255) PRIMARY KEY,
            display_name VARCHAR(255) NOT NULL DEFAULT 'NVIDIA Smart',
            public_model_id VARCHAR(255) NOT NULL UNIQUE DEFAULT 'nvidia-smart',
            base_url VARCHAR(500) NOT NULL DEFAULT 'https://integrate.api.nvidia.com/v1',
            enabled BOOLEAN DEFAULT 1,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )"""))
        await connection.execute(text("""CREATE TABLE IF NOT EXISTS nvidia_smart_accounts (
            id VARCHAR(255) PRIMARY KEY,
            config_id VARCHAR(255) NOT NULL,
            label VARCHAR(255) NOT NULL,
            encrypted_api_key TEXT NOT NULL,
            model_id VARCHAR(255) NOT NULL,
            enabled BOOLEAN DEFAULT 1,
            status VARCHAR(50) NOT NULL DEFAULT 'healthy',
            cooldown_until DATETIME,
            consecutive_failures INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            failure_count INTEGER DEFAULT 0,
            avg_latency_ms FLOAT DEFAULT 0,
            last_status_code INTEGER,
            last_error_code VARCHAR(128),
            last_error_at DATETIME,
            last_used_at DATETIME,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )"""))
        await connection.execute(text("CREATE INDEX IF NOT EXISTS idx_nvidia_smart_accounts_config ON nvidia_smart_accounts(config_id)"))
        await connection.execute(text("CREATE INDEX IF NOT EXISTS idx_nvidia_smart_accounts_status ON nvidia_smart_accounts(config_id, status)"))
        nvidia_columns = await connection.execute(text("PRAGMA table_info(nvidia_smart_accounts)"))
        nvidia_names = {row[1] for row in nvidia_columns.fetchall()}
        if "failure_count" not in nvidia_names:
            await connection.execute(text("ALTER TABLE nvidia_smart_accounts ADD COLUMN failure_count INTEGER DEFAULT 0"))
        if "avg_latency_ms" not in nvidia_names:
            await connection.execute(text("ALTER TABLE nvidia_smart_accounts ADD COLUMN avg_latency_ms FLOAT DEFAULT 0"))
        await connection.execute(text("CREATE TABLE IF NOT EXISTS auth_migrations (migration_key VARCHAR(255) PRIMARY KEY, applied_at DATETIME NOT NULL)"))


async def cleanup_legacy_users() -> dict:
    """Preserve only the configured admin row and remove all old users once."""
    migration_key = "preserve-admin-remove-legacy-users-v5"
    if USE_D1:
        await d1_execute("CREATE TABLE IF NOT EXISTS auth_migrations (migration_key TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
        marker_rows = await d1_fetchall("SELECT migration_key FROM auth_migrations WHERE migration_key = ?", [migration_key])
        if marker_rows:
            invariant = await d1_fetchall("""SELECT
                (SELECT COUNT(*) FROM users) AS user_count,
                (SELECT COUNT(*) FROM users WHERE lower(email) = lower(?) AND role = 'admin') AS admin_count,
                (SELECT COUNT(*) FROM pending_registrations) AS pending_count
            """, [settings.ADMIN_EMAIL])
            state = invariant[0] if invariant else {}
            if state.get("user_count") == 1 and state.get("admin_count") == 1 and state.get("pending_count") == 0:
                return {"skipped": True}
            await d1_execute("DELETE FROM auth_migrations WHERE migration_key = ?", [migration_key])
        admin_rows = []
        for attempt in range(10):
            admin_rows = await d1_fetchall("SELECT id FROM users WHERE lower(email) = lower(?) AND role = 'admin'", [settings.ADMIN_EMAIL])
            if len(admin_rows) == 1:
                break
            if attempt < 9:
                await asyncio.sleep(1)
        if len(admin_rows) != 1:
            raise RuntimeError("Expected exactly one configured admin row before cleanup after consistency retries")
        admin_id = admin_rows[0]["id"]
        await d1_execute("DELETE FROM verification_tokens WHERE user_id != ?", [admin_id])
        await d1_execute("DELETE FROM api_keys WHERE user_id != ?", [admin_id])
        await d1_execute("DELETE FROM user_gateway_configs WHERE user_id != ?", [admin_id])
        await d1_execute("DELETE FROM request_logs WHERE user_id != ?", [admin_id])
        await d1_execute("DELETE FROM usage_stats WHERE user_id != ?", [admin_id])
        await d1_execute("DELETE FROM pending_registrations")
        await d1_execute("DELETE FROM users WHERE id != ?", [admin_id])
        await d1_execute("UPDATE users SET email_verified_at = COALESCE(email_verified_at, CURRENT_TIMESTAMP), is_active = 1 WHERE id = ?", [admin_id])
        await d1_execute("INSERT INTO auth_migrations (migration_key, applied_at) VALUES (?, CURRENT_TIMESTAMP)", [migration_key])
        return {"admin_id": admin_id, "deleted_non_admins": True}

    async with db_session.engine.begin() as connection:
        await connection.execute(text("CREATE TABLE IF NOT EXISTS auth_migrations (migration_key VARCHAR(255) PRIMARY KEY, applied_at DATETIME NOT NULL)"))
        marker = await connection.execute(text("SELECT migration_key FROM auth_migrations WHERE migration_key = :key"), {"key": migration_key})
        if marker.first():
            invariant = await connection.execute(text("""SELECT
                (SELECT COUNT(*) FROM users) AS user_count,
                (SELECT COUNT(*) FROM users WHERE lower(email) = lower(:email) AND role = 'admin') AS admin_count,
                (SELECT COUNT(*) FROM pending_registrations) AS pending_count
            """), {"email": settings.ADMIN_EMAIL})
            state = invariant.first()
            if state and state.user_count == 1 and state.admin_count == 1 and state.pending_count == 0:
                return {"skipped": True}
            await connection.execute(text("DELETE FROM auth_migrations WHERE migration_key = :key"), {"key": migration_key})
        result = await connection.execute(text("SELECT id FROM users WHERE lower(email) = lower(:email) AND role = 'admin'"), {"email": settings.ADMIN_EMAIL})
        rows = result.fetchall()
        if len(rows) != 1:
            raise RuntimeError("Expected exactly one configured admin row before cleanup")
        admin_id = rows[0][0]
        await connection.execute(text("DELETE FROM verification_tokens WHERE user_id != :id"), {"id": admin_id})
        await connection.execute(text("DELETE FROM api_keys WHERE user_id != :id"), {"id": admin_id})
        await connection.execute(text("DELETE FROM user_gateway_configs WHERE user_id != :id"), {"id": admin_id})
        await connection.execute(text("DELETE FROM request_logs WHERE user_id != :id"), {"id": admin_id})
        await connection.execute(text("DELETE FROM usage_stats WHERE user_id != :id"), {"id": admin_id})
        await connection.execute(text("DELETE FROM pending_registrations"))
        await connection.execute(text("DELETE FROM users WHERE id != :id"), {"id": admin_id})
        await connection.execute(text("UPDATE users SET email_verified_at = COALESCE(email_verified_at, CURRENT_TIMESTAMP), is_active = 1 WHERE id = :id"), {"id": admin_id})
        await connection.execute(text("INSERT INTO auth_migrations (migration_key, applied_at) VALUES (:key, CURRENT_TIMESTAMP)"), {"key": migration_key})
        return {"admin_id": admin_id, "deleted_non_admins": True}


async def cleanup_generic_nvidia_providers() -> dict:
    """Remove legacy generic NVIDIA rows; NVIDIA Smart has its own tables and router."""
    if USE_D1:
        rows = await d1_fetchall("SELECT id FROM providers WHERE lower(provider_type) = 'nvidia'")
        provider_ids = [row.get("id") for row in rows if row.get("id")]
        for provider_id in provider_ids:
            await d1_execute("DELETE FROM models WHERE provider_id = ?", [provider_id])
        if provider_ids:
            placeholders = ",".join("?" for _ in provider_ids)
            await d1_execute(f"DELETE FROM providers WHERE id IN ({placeholders})", provider_ids)
        return {"deleted_providers": len(provider_ids)}

    async with db_session.engine.begin() as connection:
        rows = await connection.execute(text("SELECT id FROM providers WHERE lower(provider_type) = 'nvidia'"))
        provider_ids = [row[0] for row in rows.fetchall()]
        for provider_id in provider_ids:
            await connection.execute(text("DELETE FROM models WHERE provider_id = :provider_id"), {"provider_id": provider_id})
        if provider_ids:
            placeholders = ",".join(f":id_{index}" for index in range(len(provider_ids)))
            params = {f"id_{index}": provider_id for index, provider_id in enumerate(provider_ids)}
            await connection.execute(text(f"DELETE FROM providers WHERE id IN ({placeholders})"), params)
        return {"deleted_providers": len(provider_ids)}
