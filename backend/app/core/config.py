"""App config from environment variables."""
import os


class Settings:
    VERSION = "1.0.0"
    APP_NAME = "AI Gateway"
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./ai_gateway.db")
    USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 30 days
    SESSION_COOKIE_NAME = "saki_gateway_session"
    APP_BASE_URL = os.getenv("APP_BASE_URL", "https://saki-gateway.indevs.in").rstrip("/")
    FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "https://ai-gateway-frontend.onrender.com").rstrip("/")
    BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
    EMAIL_FROM = os.getenv("EMAIL_FROM", "")
    EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Saki Gateway")
    EMAIL_API_TIMEOUT_SECONDS = float(os.getenv("EMAIL_API_TIMEOUT_SECONDS", "10"))
    VERIFICATION_TOKEN_HOURS = int(os.getenv("VERIFICATION_TOKEN_HOURS", "24"))
    VERIFICATION_CODE_MINUTES = int(os.getenv("VERIFICATION_CODE_MINUTES", "15"))
    VERIFICATION_CODE_MAX_ATTEMPTS = int(os.getenv("VERIFICATION_CODE_MAX_ATTEMPTS", "5"))
    AUTH_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "300"))
    AUTH_RATE_LIMIT_MAX_ATTEMPTS = int(os.getenv("AUTH_RATE_LIMIT_MAX_ATTEMPTS", "5"))
    PERSONAL_GATEWAY_MAX_CONFIGS = int(os.getenv("PERSONAL_GATEWAY_MAX_CONFIGS", "5"))
    PERSONAL_GATEWAY_ENCRYPTION_KEY = os.getenv("PERSONAL_GATEWAY_ENCRYPTION_KEY", "")
    CF_KV_NAMESPACE_ID = os.getenv("CF_KV_NAMESPACE_ID", "")
    PUBLIC_GATEWAY_BASE_URL = os.getenv("PUBLIC_GATEWAY_BASE_URL", "https://saki-gateway.indevs.in")

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

    @classmethod
    def refresh_from_env(cls) -> None:
        """Re-read every env-derived field from os.environ.

        The singleton is created at first import, so modules that override
        env vars AFTER import (e.g. tests that run after other tests) must
        call this to make the cached `settings` reflect the new values.
        """
        cls.DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        cls.ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
        cls.ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
        cls.SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
        cls.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./ai_gateway.db")
        cls.USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"
        cls.APP_BASE_URL = os.getenv("APP_BASE_URL", "https://saki-gateway.indevs.in").rstrip("/")
        cls.FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "https://ai-gateway-frontend.onrender.com").rstrip("/")
        cls.BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
        cls.EMAIL_FROM = os.getenv("EMAIL_FROM", "")
        cls.EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Saki Gateway")
        cls.VERIFICATION_TOKEN_HOURS = int(os.getenv("VERIFICATION_TOKEN_HOURS", "24"))
        cls.VERIFICATION_CODE_MINUTES = int(os.getenv("VERIFICATION_CODE_MINUTES", "15"))
        cls.VERIFICATION_CODE_MAX_ATTEMPTS = int(os.getenv("VERIFICATION_CODE_MAX_ATTEMPTS", "5"))
        cls.AUTH_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "300"))
        cls.AUTH_RATE_LIMIT_MAX_ATTEMPTS = int(os.getenv("AUTH_RATE_LIMIT_MAX_ATTEMPTS", "5"))
        cls.CF_KV_NAMESPACE_ID = os.getenv("CF_KV_NAMESPACE_ID", "")
        cls.PUBLIC_GATEWAY_BASE_URL = os.getenv("PUBLIC_GATEWAY_BASE_URL", "https://saki-gateway.indevs.in")


settings = Settings()
