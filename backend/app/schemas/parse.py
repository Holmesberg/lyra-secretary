"""Pydantic schemas for parsing."""
from pydantic import BaseModel, Field

# Already defined in task.py
# Included here for clarity

class ParseRequest(BaseModel):
    """Request to parse natural language."""
    text: str = Field(..., min_length=1, max_length=500)


class ParseResponse(BaseModel):
    """Response from parsing."""
    # Same as TaskParseResponse
    pass
