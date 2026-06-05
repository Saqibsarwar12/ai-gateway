"""App config from environment variables."""
import os


class Settings:
    VERSION = "1.0.0"
    APP_NAME = "AI Gateway"
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./ai_gateway.db")
    USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

    # Tier rate limits (requests per minute)
    TIER_RATE_LIMITS = {
        "v1": 60,
        "v2": 200,
        "v3": 600,
    }

    # Tier credit multipliers (v2 gets 5x, v3 gets 20x default credits)
    TIER_CREDIT_GRANTS = {
        "v1": 100,
        "v2": 500,
        "v3": 2000,
    }


settings = Settings()
