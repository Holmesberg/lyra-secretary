"""Pydantic schemas for feedback submission + triage."""
from datetime import datetime
from typing import Literal, Optional, Any
from pydantic import BaseModel, Field


FeedbackKind = Literal["bug", "suggestion", "confused", "other"]
FeedbackStatus = Literal["unread", "read", "acted_on", "dismissed"]


class FeedbackSubmitRequest(BaseModel):
    """User-submitted feedback. Optional context fields help operator
    reproduce bugs; user opts in via a checkbox at submit time."""
    kind: FeedbackKind
    body: str = Field(..., min_length=1, max_length=5000)
    page_url: Optional[str] = Field(None, max_length=500)
    user_agent: Optional[str] = Field(None, max_length=500)
    error_context: Optional[list[Any]] = None


class FeedbackSubmitResponse(BaseModel):
    feedback_id: str
    submitted_at: datetime


class FeedbackRow(BaseModel):
    """Operator-facing triage row."""
    feedback_id: str
    user_id: Optional[int]
    user_email: Optional[str]
    submitted_at: datetime
    kind: str
    body: str
    page_url: Optional[str]
    user_agent: Optional[str]
    error_context: Optional[list[Any]]
    status: str
    operator_note: Optional[str]
    resolved_at: Optional[datetime]


class FeedbackListResponse(BaseModel):
    items: list[FeedbackRow]
    total: int
    unread_count: int


class FeedbackResolveRequest(BaseModel):
    status: FeedbackStatus
    operator_note: Optional[str] = Field(None, max_length=2000)
