"""FastAPI application entry point — serves API + static Next.js frontend."""
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings
from app.db.session import engine, Base, init_redis
from app.api.v1.endpoints import openai, admin


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(openai.router, prefix="/v1")
    app.include_router(admin.router, prefix="/v1")

    return app


app = create_app()


@app.on_event("startup")
async def startup():
    # Init Redis only when enabled
    init_redis()
    # Create DB tables (SQLite)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
async def root():
    index_path = Path(__file__).parent.parent.parent / "static" / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "AI Gateway API — docs at /docs"}


@app.get("/health")
async def health():
    return {"status": "ok", "debug": settings.DEBUG}
