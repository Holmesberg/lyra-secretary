"""Application configuration using Pydantic Settings."""
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Core
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "your-secret-key-min-32-chars-default"

    # Database
    DATABASE_URL: str = "sqlite:///./data/lyra.db"
    DB_CONNECT_TIMEOUT_SECONDS: int = Field(5, env="DB_CONNECT_TIMEOUT_SECONDS")

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: str = ""

    # User Context (CRITICAL)
    USER_TIMEZONE: str = "Africa/Cairo"
    USER_ID: str = "user_primary"

    # OpenClaw notification bridge. Telegram delivery belongs to OpenClaw's
    # existing bot; LyraOS only queues operator alerts into the same
    # notifications:pending user queue that OpenClaw polls.
    OPENCLAW_OPERATOR_USER_ID: int = Field(1, env="OPENCLAW_OPERATOR_USER_ID")
    OPENCLAW_OPERATOR_NOTIFICATIONS_ENABLED: bool = Field(
        True, env="OPENCLAW_OPERATOR_NOTIFICATIONS_ENABLED"
    )
    OPENCLAW_MIRROR_USER_NOTIFICATIONS: bool = Field(
        True, env="OPENCLAW_MIRROR_USER_NOTIFICATIONS"
    )

    # Alpha feedback widget (alembic 040, 2026-04-28). Resend is the
    # primary channel; OpenClaw operator alerts are the fallback. Either
    # or both can be unconfigured - submission still commits the feedback row.
    RESEND_API_KEY: Optional[str] = Field(None, env="RESEND_API_KEY")
    OPERATOR_EMAIL: Optional[str] = Field(None, env="OPERATOR_EMAIL")
    FEEDBACK_FROM_EMAIL: str = Field(
        "hello@lyraos.org", env="FEEDBACK_FROM_EMAIL"
    )
    USER_EMAIL_ENABLED: bool = Field(False, env="USER_EMAIL_ENABLED")
    USER_EMAIL_FROM: str = Field("hello@lyraos.org", env="USER_EMAIL_FROM")
    EMAIL_TRACKING_BASE_URL: str = Field(
        "https://api.lyraos.org", env="EMAIL_TRACKING_BASE_URL"
    )

    # Auth (Phase 2). JWT_SECRET is shared with the Next.js frontend's
    # NEXTAUTH_SECRET - both must be identical or token validation fails.
    JWT_SECRET: str = "dev-only-replace-me-with-32-byte-urlsafe-secret"
    JWT_ALGORITHM: str = "HS256"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ALLOWED_ORIGINS: str = ""

    # Pre-scale containment switches (LyraOSSim/Baseet 2026-05-22).
    # Defaults preserve current behavior. Operators can disable risky paths
    # without a deploy if a Baseet-scale inference pattern misbehaves.
    LYRA_SAFE_MODE: str = Field("", env="LYRA_SAFE_MODE")
    LYRA_BASEET_PRESSURE_INPUT_ENABLED: bool = Field(
        True, env="LYRA_BASEET_PRESSURE_INPUT_ENABLED"
    )
    LYRA_PROVIDER_PROGRESS_SIGNALS_ENABLED: bool = Field(
        True, env="LYRA_PROVIDER_PROGRESS_SIGNALS_ENABLED"
    )
    LYRA_RECOVERY_NUDGES_ENABLED: bool = Field(
        True, env="LYRA_RECOVERY_NUDGES_ENABLED"
    )

    @property
    def cors_allowed_origins(self) -> list[str]:
        """Frontend origins allowed to call the API from browsers."""
        defaults = [
            self.FRONTEND_URL,
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://lyraos.org",
            "https://lyraos.org",
        ]
        configured = [
            origin.strip()
            for origin in self.CORS_ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

        origins: list[str] = []
        for origin in [*defaults, *configured]:
            normalized = origin.rstrip("/")
            if normalized and normalized not in origins:
                origins.append(normalized)
        return origins

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8-sig"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
