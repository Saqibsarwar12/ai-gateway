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
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 30 days

    APP_BASE_URL = os.getenv("APP_BASE_URL", "https://saki-gateway.indevs.in").rstrip("/")
    CF_EMAIL_API_TOKEN = os.getenv("CF_EMAIL_API_TOKEN", os.getenv("CLOUDFLARE_EMAIL_API_TOKEN", ""))
    RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
    BREVO_SMTP = os.getenv("BREVO_SMTP", "")
    EMAIL_FROM = os.getenv("EMAIL_FROM", ADMIN_EMAIL)
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp-relay.brevo.com" if BREVO_SMTP else "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "b4bca8001@smtp-brevo.com" if BREVO_SMTP else "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", BREVO_SMTP)
    SMTP_TLS = os.getenv("SMTP_TLS", "true").lower() == "true"
    VERIFICATION_TOKEN_HOURS = int(os.getenv("VERIFICATION_TOKEN_HOURS", "24"))
    AUTH_RATE_LIMIT_WINDOW_SECONDS = 300
    AUTH_RATE_LIMIT_MAX_ATTEMPTS = 5

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
