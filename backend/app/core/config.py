"""Core configuration — env vars, settings."""
from pydantic_settings import BaseSettings
from pydantic import Field
import os


class Settings(BaseSettings):
    APP_NAME: str = "AI Gateway"
    DEBUG: bool = False
    SECRET_KEY: str = Field(default="change-me-in-production")
    VERSION: str = "1.0.0"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_gateway"
    )

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    # Admin
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "admin123"  # Change in production!

    # Rate limits
    DEFAULT_RATE_LIMIT: int = 100
    DEFAULT_RATE_WINDOW: int = 60  # seconds

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
