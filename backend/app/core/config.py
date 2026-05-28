"""Core config — env vars, secrets, settings."""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AI Gateway"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=os.getenv("DEBUG", "false").lower() == "true")
    SECRET_KEY: str = Field(default=os.getenv("SECRET_KEY", "change-me-in-production"))

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_gateway"
    )
    DATABASE_URL_SYNC: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/ai_gateway"
    )

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # JWT
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    JWT_REFRESH_EXPIRE_DAYS: int = 30

    # Rate Limits
    DEFAULT_RATE_LIMIT: int = 100  # per minute
    DEFAULT_BURST: int = 20

    # Routing
    DEFAULT_ROUTING_STRATEGY: str = "latency"  # latency | cost | weighted | failover
    MAX_RETRIES: int = 3
    REQUEST_TIMEOUT: int = 120  # seconds

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json | text

    # Admin
    ADMIN_EMAIL: str = Field(default=os.getenv("ADMIN_EMAIL", "admin@localhost"))
    ADMIN_PASSWORD: str = Field(default=os.getenv("ADMIN_PASSWORD", "changeme"))

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
