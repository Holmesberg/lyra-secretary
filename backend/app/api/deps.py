"""FastAPI dependency injection."""
from typing import Generator
from app.db.session import SessionLocal

def get_db() -> Generator:
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
