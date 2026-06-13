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

    # Notion
    NOTION_API_KEY: str = ""
    NOTION_DATABASE_ID: str = ""

    # OpenAI
    OPENAI_API_KEY: str = ""

    # User Context (CRITICAL)
    USER_TIMEZONE: str = "Africa/Cairo"
    USER_ID: str = "user_primary"

    # OpenClaw notification bridge. Telegram delivery belongs to OpenClaw's
    # existing bot; Lyra only queues operator alerts into the same
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

    # Local LLM enrichment (Workstream 1, magic-for-alpha 2026-04-28).
    # Optional. When OLLAMA_URL is unreachable or the model is not loaded,
    # the llm_enrichment APScheduler job marks tasks as
    # llm_parse_status='unavailable' and the UI degrades to regex output
    # - task creation never blocks on this dependency.
    OLLAMA_URL: str = Field("http://host.docker.internal:11434", env="OLLAMA_URL")
    # Default qwen2.5:3b - fits comfortably in 8GB VRAM (operator's
    # A4000) with room for KV cache + system display. Operators with
    # >12GB VRAM can override to qwen2.5:7b or qwen3:8b for better
    # quality. Q4 quantized: ~1.9GB on disk, ~2.5GB loaded.
    OLLAMA_MODEL: str = Field("qwen2.5:3b", env="OLLAMA_MODEL")
    # Cut from 60s to 10s 2026-04-28 (stress-test P1 #4): qwen2.5:3b runs
    # 5-8s warm; 10s leaves 25-50% headroom while a hung Ollama can no
    # longer pin the APScheduler thread for a full minute (was blocking
    # reminders, pause prediction, stale_session_recovery alongside).
    OLLAMA_TIMEOUT_SECONDS: int = Field(10, env="OLLAMA_TIMEOUT_SECONDS")

    # NVIDIA NIM client (JARVIS, 2026-04-30). Hosted free-tier inference
    # at build.nvidia.com. When NVIDIA_NIM_API_KEY is set, the LLM
    # enrichment path tries NIM first and falls back to Ollama on
    # NimUnavailable. JARVIS endpoints (operator-only) require this to be
    # set - they 503 otherwise. Default model switched 2026-05-09 to
    # moonshotai/kimi-k2.6 after operator live-model selection; this is
    # operator-only and does not change any research metric semantics.
    NVIDIA_NIM_API_KEY: str = Field("", env="NVIDIA_NIM_API_KEY")
    NVIDIA_NIM_MODEL: str = Field("moonshotai/kimi-k2.6", env="NVIDIA_NIM_MODEL")
    NVIDIA_NIM_BASE_URL: str = Field(
        "https://integrate.api.nvidia.com/v1", env="NVIDIA_NIM_BASE_URL"
    )
    # JARVIS gets more headroom because it is foreground, operator-only, and
    # can stream longer reasoning/tool turns. Background enrichment must use
    # NVIDIA_NIM_ENRICHMENT_TIMEOUT_SECONDS instead so provider slowness
    # degrades auxiliary parsing rather than pinning the scheduler.
    NVIDIA_NIM_TIMEOUT_SECONDS: int = Field(120, env="NVIDIA_NIM_TIMEOUT_SECONDS")
    NVIDIA_NIM_ENRICHMENT_TIMEOUT_SECONDS: int = Field(
        15, env="NVIDIA_NIM_ENRICHMENT_TIMEOUT_SECONDS"
    )
    # Kimi K2.6 supports NVIDIA's chat_template_kwargs={"thinking": true}
    # switch. Keep it env-controlled because structured JSON parsing must
    # disable it per call.
    NVIDIA_NIM_ENABLE_THINKING: bool = Field(True, env="NVIDIA_NIM_ENABLE_THINKING")
    NVIDIA_NIM_JARVIS_MAX_TOKENS: int = Field(
        16384, env="NVIDIA_NIM_JARVIS_MAX_TOKENS"
    )
    # Tier thresholds for the LLM deadline-binding chip (operator-locked
    # 2026-04-28). Per stress-test conversation: confidence thresholds
    # are the most important calibration stat. Tunable from .env so we
    # can adjust without redeploying once we have alpha-cohort data.
    LLM_TIER1_CONFIDENCE: float = Field(0.85, env="LLM_TIER1_CONFIDENCE")
    LLM_TIER2_CONFIDENCE: float = Field(0.45, env="LLM_TIER2_CONFIDENCE")

    # Auth (Phase 2). JWT_SECRET is shared with the Next.js frontend's
    # NEXTAUTH_SECRET - both must be identical or token validation fails.
    JWT_SECRET: str = "dev-only-replace-me-with-32-byte-urlsafe-secret"
    JWT_ALGORITHM: str = "HS256"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ALLOWED_ORIGINS: str = ""

    # Pre-scale containment switches (LyraSim/Baseet 2026-05-22).
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
