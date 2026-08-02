"""
Application configuration — loaded from environment variables via Pydantic Settings.
All settings have safe defaults for local development.
Add new env vars here; never read os.environ directly elsewhere in the app.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ────────────────────────────────────────────────────────────────────
    APP_ENV: str = "local"
    APP_VERSION: str = "0.1.0"
    APP_NAME: str = "Personal CFO AI"
    APP_DESCRIPTION: str = "Enterprise-grade personal finance AI platform."

    # ── Server ─────────────────────────────────────────────────────────────────
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # ── Security ───────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-to-a-long-random-string-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Google OAuth ───────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:3000/auth/google/callback"

    # ── OTP ────────────────────────────────────────────────────────────────────
    OTP_EXPIRE_MINUTES: int = 10

    # ── Database ───────────────────────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/personal_cfo"
    )
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False  # set True to log all SQL queries

    # ── Redis ──────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── CORS ───────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # ── Logging ────────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False  # set True in production for structured JSON logs


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — injected via FastAPI Depends."""
    return Settings()


# Module-level singleton for non-DI usage (config, logging setup, etc.)
settings = get_settings()
