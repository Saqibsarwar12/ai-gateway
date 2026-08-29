"""DB session — uses D1 when USE_D1=true, else local SQLite."""

import os

USE_D1 = os.getenv("USE_D1", "").lower() == "true"

# Always define these so importers don't crash
async_session_maker = None
engine = None
init_db = None

if USE_D1:
    from app.db.d1_session import D1Session, d1_session_maker as _d1_maker

    async_session_maker = _d1_maker

    async def _init_db_d1():
        pass

    init_db = _init_db_d1
else:
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./ai_gateway.db")
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def _init_db_sqlite():
        from app.db.models import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    init_db = _init_db_sqlite


async def get_db():
    """FastAPI dependency — yields a session (use with Depends)."""
    session = async_session_maker()
    try:
        yield session
    finally:
        await session.close()


def reconfigure_from_env() -> None:
    """Rebuild the SQLite engine and session maker from the current DATABASE_URL.

    Used by tests that override DATABASE_URL per file/module: the module-level
    `engine` is bound once at import time, so a later env override is ignored.
    Calling this after setting the env var makes the new URL take effect.
    Safe to call multiple times.
    """
    global engine, async_session_maker, init_db
    if USE_D1:
        # No-op for D1 mode (D1 sessions are not bound to a local engine).
        return
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./ai_gateway.db")
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def _init_db_sqlite():
        from app.db.models import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    init_db = _init_db_sqlite