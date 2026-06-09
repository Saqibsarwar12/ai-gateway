"""FastAPI application entry point — AI Gateway Platform.

In production (Render), FastAPI runs on port 8000 and Next.js runs on port 3001.
FastAPI handles all /v1, /v2, /v3, /admin, /health API routes.
All other GET requests are proxied to the Next.js server on port 3001.
"""
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.api.v1 import admin
from app.api.gateway import make_openai_router

NEXT_PORT = int(os.getenv("NEXT_PORT", "3001"))
NEXT_BASE = f"http://localhost:{NEXT_PORT}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create / migrate tables
    from app.db.session import init_db, async_session_maker, USE_D1
    await init_db()

    # Test D1 connectivity
    try:
        async with async_session_maker() as session:
            await session.execute("SELECT 1")
    except Exception as e:
        print(f"WARNING: D1 connectivity test failed — {e}")

    # Seed default admin
    from app.db.models import User
    from app.core.auth import hash_password, create_api_key
    from sqlalchemy import select

    try:
        async with async_session_maker() as session:
            result = await session.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
            admin_user = result.scalar_one_or_none()
            if not admin_user:
                api_key = create_api_key()
                admin_user = User(
                    id="admin-001",
                    name="Admin",
                    email=settings.ADMIN_EMAIL,
                    hashed_password=hash_password(settings.ADMIN_PASSWORD),
                    role="admin",
                    tier="v3",
                    api_key=api_key,
                    credits=999999999,
                    is_active=True,
                )
                session.add(admin_user)
                await session.commit()
                print(f"Admin created: {settings.ADMIN_EMAIL} / API Key: {api_key}")
            else:
                admin_user.hashed_password = hash_password(settings.ADMIN_PASSWORD)
                admin_user.tier = "v3"
                admin_user.is_active = True
                await session.commit()
                print(f"Admin password refreshed: {settings.ADMIN_EMAIL}")
    except Exception as e:
        print(f"WARNING: Admin seed skipped — {e}")

    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Production AI Gateway — OpenAI-compatible API with provider routing and tiered access",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── API Routes ────────────────────────────────────────────────────
app.include_router(make_openai_router("v1"), prefix="/v1", tags=["AI Gateway v1"])
app.include_router(make_openai_router("v2"), prefix="/v2", tags=["AI Gateway v2"])
app.include_router(make_openai_router("v3"), prefix="/v3", tags=["AI Gateway v3"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.VERSION}


# ─── Proxy all other requests to Next.js ───────────────────────────────
@app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
async def proxy_to_nextjs(path: str, request: Request):
    """Proxy frontend requests to the Next.js server running on port 3001."""
    url = f"{NEXT_BASE}/{path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(
                method=request.method,
                url=url,
                headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
                content=await request.body(),
            )
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=dict(resp.headers),
            )
    except httpx.ConnectError:
        return Response(
            content=b"<html><body><h2>Frontend starting up, please refresh in a moment.</h2></body></html>",
            status_code=503,
            media_type="text/html",
        )
