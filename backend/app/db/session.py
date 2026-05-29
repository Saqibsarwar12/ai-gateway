"""Database session — SQLite on Free tier Render, PostgreSQL when available."""
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

Base = declarative_base()

USE_SQLITE = os.getenv("USE_SQLITE", "true").lower() == "true"
DATABASE_URL = os.getenv("DATABASE_URL", "")

if USE_SQLITE or not DATABASE_URL:
    # SQLite for local dev / Free tier — no pip install needed
    DB_PATH = os.getenv("DB_PATH", "/tmp/ai_gateway.db")
    DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"
    engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
else:
    # PostgreSQL for production
    engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True, pool_size=5)

async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
