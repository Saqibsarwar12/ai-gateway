"""Core config — env vars, secrets, settings."""
from pydantic_settings import BaseSettings
from pydantic import Field
import os


class Settings(BaseSettings):
    APP_NAME: str = "AI Gateway"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=os.getenv("DEBUG", "false").lower() == "true")
    SECRET_KEY: str = Field(default=os.getenv("SECRET_KEY", "change-me-in-production"))

    # Database — SQLite fallback when no URL provided
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./ai_gateway.db"
    )
    DATABASE_URL_SYNC: str = Field(
        default="sqlite:///./ai_gateway.db"
    )

    # Redis — disabled in DEBUG when no URL provided
    REDIS_URL: str = Field(default="")
    REDIS_ENABLED: bool = Field(
        default=os.getenv("REDIS_ENABLED", "false").lower() == "true"
    )

    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24
    JWT_REFRESH_EXPIRE_DAYS: int = 30

    DEFAULT_RATE_LIMIT: int = 100
    DEFAULT_BURST: int = 20

    DEFAULT_ROUTING_STRATEGY: str = "latency"
    MAX_RETRIES: int = 3
    REQUEST_TIMEOUT: int = 120

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "text"

    ADMIN_EMAIL: str = Field(default=os.getenv("ADMIN_EMAIL", "admin@localhost"))
    ADMIN_PASSWORD: str = Field(default=os.getenv("ADMIN_PASSWORD", "changeme"))

    CORS_ORIGINS: list[str] = ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
