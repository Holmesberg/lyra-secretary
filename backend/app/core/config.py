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
