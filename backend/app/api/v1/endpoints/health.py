"""Health check endpoint."""
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health_check():
    """Service health check."""
    return {"status": "ok", "service": "lyra-secretary"}
