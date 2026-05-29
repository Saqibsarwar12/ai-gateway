"""Database session — PostgreSQL on Render, SQLite fallback for local dev."""
import os

USE_SQLITE = os.environ.get("USE_SQLITE", "false").lower() == "true"

if USE_SQLITE:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy.orm import declarative_base
    from sqlalchemy.pool import StaticPool

    engine = create_async_engine(
        "sqlite+aiosqlite:///./ai_gateway.db",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    Base = declarative_base()
    redis_client = None

    async def get_db():
        async with async_session_maker() as session:
            yield session

    async def get_redis():
        return None

else:
    import redis.asyncio as redis
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy.orm import declarative_base

    engine = create_async_engine(
        os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_gateway"),
        echo=False,
        pool_size=20,
        max_overflow=30,
    )
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    Base = declarative_base()
    redis_client = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)

    async def get_db():
        async with async_session_maker() as session:
            yield session

    async def get_redis():
        return redis_client
