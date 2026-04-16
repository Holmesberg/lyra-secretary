"""Database session management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

_is_sqlite = "sqlite" in settings.DATABASE_URL

# Supabase pooler drops idle conns after ~60s; pool_pre_ping + pool_recycle
# avoid stale-connection stalls (each stall is a ~400ms EU roundtrip on the
# hot read path). pool_size/max_overflow sized for uvicorn single-worker +
# APScheduler background jobs sharing the pool.
_pool_kwargs = {} if _is_sqlite else {
    "pool_size": 10,
    "max_overflow": 10,
    "pool_pre_ping": True,
    "pool_recycle": 1800,
}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    **_pool_kwargs,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
