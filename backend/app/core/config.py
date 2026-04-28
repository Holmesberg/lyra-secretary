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
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: str = ""
    
    # Notion
    NOTION_API_KEY: str = ""
    NOTION_DATABASE_ID: str = ""
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    
    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    
    # User Context (CRITICAL)
    USER_TIMEZONE: str = "Africa/Cairo"
    USER_ID: str = "user_primary"

    # Telegram (Optional — direct reminder delivery)
    TELEGRAM_BOT_TOKEN: Optional[str] = Field(None, env="TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: Optional[str] = Field(None, env="TELEGRAM_CHAT_ID")

    # Alpha feedback widget (alembic 040, 2026-04-28). Resend is the
    # primary channel; Telegram (above) is the fallback. Either or both
    # can be unconfigured — submission still commits the feedback row.
    RESEND_API_KEY: Optional[str] = Field(None, env="RESEND_API_KEY")
    OPERATOR_EMAIL: Optional[str] = Field(None, env="OPERATOR_EMAIL")
    FEEDBACK_FROM_EMAIL: str = Field(
        "onboarding@resend.dev", env="FEEDBACK_FROM_EMAIL"
    )

    # Local LLM enrichment (Workstream 1, magic-for-alpha 2026-04-28).
    # Optional. When OLLAMA_URL is unreachable or the model isn't loaded,
    # the llm_enrichment APScheduler job marks tasks as
    # llm_parse_status='unavailable' and the UI degrades to regex output
    # — task creation never blocks on this dependency.
    OLLAMA_URL: str = Field("http://host.docker.internal:11434", env="OLLAMA_URL")
    # Default qwen2.5:3b — fits comfortably in 8GB VRAM (operator's
    # A4000) with room for KV cache + system display. Operators with
    # >12GB VRAM can override to qwen2.5:7b or qwen3:8b for better
    # quality. Q4 quantized: ~1.9GB on disk, ~2.5GB loaded.
    OLLAMA_MODEL: str = Field("qwen2.5:3b", env="OLLAMA_MODEL")
    # Cut from 60s → 10s 2026-04-28 (stress-test P1 #4): qwen2.5:3b runs
    # 5-8s warm; 10s leaves 25-50% headroom while a hung Ollama can no
    # longer pin the APScheduler thread for a full minute (was blocking
    # reminders, pause prediction, stale_session_recovery alongside).
    OLLAMA_TIMEOUT_SECONDS: int = Field(10, env="OLLAMA_TIMEOUT_SECONDS")
    # Tier thresholds for the LLM deadline-binding chip (operator-locked
    # 2026-04-28). Per stress-test conversation: confidence thresholds
    # are the most important calibration stat. Tunable from .env so we
    # can adjust without redeploying once we have alpha-cohort data.
    LLM_TIER1_CONFIDENCE: float = Field(0.85, env="LLM_TIER1_CONFIDENCE")
    LLM_TIER2_CONFIDENCE: float = Field(0.45, env="LLM_TIER2_CONFIDENCE")

    # Auth (Phase 2). JWT_SECRET is shared with the Next.js frontend's
    # NEXTAUTH_SECRET — both must be identical or token validation fails.
    JWT_SECRET: str = "dev-only-replace-me-with-32-byte-urlsafe-secret"
    JWT_ALGORITHM: str = "HS256"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    FRONTEND_URL: str = "http://localhost:3000"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
