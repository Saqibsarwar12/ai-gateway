"""FastAPI application entry point — AI Gateway Platform."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import openai, admin
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables
    from app.db.session import engine, Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Seed default admin if none exists
    from app.db.session import async_session_maker
    from app.db.models import User
    from app.core.auth import hash_password, generate_api_key
    from sqlalchemy import select
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
        if not result.scalar_one_or_none():
            api_key_prefix, _ = generate_api_key()
            admin_user = User(
                id="admin-001",
                name="Admin",
                email=settings.ADMIN_EMAIL,
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                role="admin",
                api_key=api_key_prefix,
                credits=999999999,
            )
            session.add(admin_user)
            await session.commit()
    yield
    # Shutdown
    from app.db.session import redis_client
    await redis_client.aclose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Production AI Gateway — OpenAI-compatible API with provider routing",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(openai.router, tags=["AI Gateway"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])


@app.get("/")
async def root():
    return {"message": "AI Gateway API — docs at /docs", "version": settings.VERSION}


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.VERSION}
