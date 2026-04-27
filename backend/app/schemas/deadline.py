"""Pydantic schemas for the deadline mechanism (alembic 033, 2026-04-26).

Used by the deferred Phase F endpoints (POST/GET/PUT/DELETE /v1/deadlines).
Defining now keeps the schema layer coherent and gives Pydantic-validated
types to TaskManager's `_validate_bindable_deadline` helper.

State enum values mirror the deadline ORM model:
    planned | active | completed | missed | skipped | voided
"""
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, field_serializer, validator


# Allowed deadline state values. `voided` is a soft-delete; users do not
# transition INTO voided directly — the API will void via a separate endpoint
# that stamps `voided_at`.
DEADLINE_STATES = ("planned", "active", "completed", "missed", "skipped", "voided")
DEADLINE_USER_TRANSITIONABLE_STATES = ("planned", "active", "completed", "skipped")


class DeadlineCreateRequest(BaseModel):
    """Request to create a new deadline."""

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    due_at_utc: datetime
    category_hint: Optional[str] = Field(None, max_length=100)

    @validator("due_at_utc")
    def due_must_be_future(cls, v):
        # Allow past deadlines for retroactive logging (e.g., importing a
        # missed deadline). API endpoint may add stricter validation.
        return v


class DeadlineUpdateRequest(BaseModel):
    """Request to update an existing deadline. All fields optional."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    due_at_utc: Optional[datetime] = None
    category_hint: Optional[str] = Field(None, max_length=100)
    # State transitions enforced server-side. Users cannot transition INTO
    # `voided` via this field (use a dedicated /void endpoint).
    state: Optional[str] = None

    @validator("state")
    def state_is_user_transitionable(cls, v):
        if v is None:
            return v
        if v not in DEADLINE_USER_TRANSITIONABLE_STATES:
            raise ValueError(
                f"state must be one of {DEADLINE_USER_TRANSITIONABLE_STATES}; "
                f"use the dedicated void/missed endpoints for those transitions"
            )
        return v


class DeadlineResponse(BaseModel):
    """Detailed deadline information."""

    deadline_id: str
    user_id: int
    title: str
    description: Optional[str]
    due_at_utc: datetime
    category_hint: Optional[str]
    state: str
    completed_at: Optional[datetime]
    voided_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

    # The deadline columns are stored as naive datetimes representing UTC
    # (alembic 033 uses `sa.DateTime` without timezone=True, matching the
    # rest of the codebase). Pydantic would otherwise emit them without an
    # offset suffix, and `new Date("2026-05-04T15:00:00")` in the browser
    # interprets the string as LOCAL time — so a deadline saved at 18:00
    # Cairo (15:00 UTC) renders as 3:00 PM Cairo. Stamp every datetime
    # field with explicit UTC on the way out so the frontend can
    # disambiguate.
    @field_serializer("due_at_utc", "completed_at", "voided_at", "created_at")
    def _serialize_utc(self, v: Optional[datetime]) -> Optional[str]:
        if v is None:
            return None
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()


class DeadlineListResponse(BaseModel):
    """Response for listing deadlines."""

    deadlines: list[DeadlineResponse]
    total: int
