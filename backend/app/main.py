"""FastAPI application entry point — serves API + static Next.js frontend."""
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings
from app.db.session import engine, Base
from app.api.v1.endpoints import openai, admin


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routers
    app.include_router(openai.router, prefix="/v1")
    app.include_router(admin.router, prefix="/v1/admin")

    return app


app = create_app()


@app.on_event("startup")
async def startup():
    """Create DB tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/health")
async def health():
    return {"status": "healthy", "version": settings.APP_VERSION}


# ─── Serve Next.js built files ─────────────────────────────────────────────
static_path = Path("/app/static")
public_path = Path("/app/public")
frontend_build = Path("/app")

if static_path.exists():
    app.mount("/_next/static", StaticFiles(directory=str(static_path)), name="static")

if public_path.exists():
    app.mount("/public", StaticFiles(directory=str(public_path)), name="public")


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve index.html for all non-API routes (SPA fallback)."""
    index = frontend_build / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"detail": "Not found"}, 404