"""DB session, engine, Redis client."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from contextlib import asynccontextmanager
import redis.asyncio as redis
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, pool_pre_ping=True)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

redis_pool = redis.from_url(settings.REDIS_URL, decode_responses=True)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session


async def get_redis():
    return redis_pool


@asynccontextmanager
async def acquire_redis():
    conn = redis_pool
    try:
        yield conn
    finally:
        pass  # pool manages connection
