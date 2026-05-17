"""JARVIS chat endpoints — operator-only.

Three routes:
  POST /v1/jarvis/ask      → submit a user message + chat history; get the
                              assistant's answer + any tool-call records +
                              any pending write-action confirmations
  POST /v1/jarvis/confirm  → confirm or reject a queued write action;
                              returns the post-execution result + a brief
                              follow-up answer
  GET  /v1/jarvis/health   → cheap NIM availability + current model probe

Privacy boundary (operator-locked 2026-04-30, per
project_openclaw_operator_only.md memory class):
  - All three endpoints require is_operator=True (returns 403 otherwise)
  - Mom + sister + students have JARVIS hidden in the UI AND blocked at the API
  - Every JARVIS call sends user task content to NVIDIA NIM (free tier).
    The trust class is "external US-based vendor with standard enterprise
    privacy commitments" — fine for operator's own data, requires a
    consent surface + opt-in flag before opening to other users.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, operator_user_from_scope
from app.core.config import settings
from app.db.models import JarvisInvocation, User
from app.services import jarvis_agent, jarvis_tools, nvidia_nim_client
from app.utils.time_utils import now_utc

router = APIRouter()


def _require_operator(db: Session, request: Request) -> User:
    return operator_user_from_scope(db, request=request)

# ---------------------------------------------------------------------------
# Request / response shapes
# ---------------------------------------------------------------------------


class JarvisAskRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    # Prior turns from the same chat session. The frontend keeps the history
    # in component state — no server-side session store, no DB persistence
    # for chat threads (yet). One JARVIS conversation lives only in the open
    # browser tab.
    history: list[dict[str, Any]] = Field(default_factory=list)


class JarvisConfirmRequest(BaseModel):
    # The pending action's tool_call_id (echoed back from /ask response).
    tool_call_id: str
    name: str
    args: dict[str, Any]
    # The chat history at the point of confirmation, so we can re-enter
    # the agent loop with full context to compose the follow-up answer.
    history: list[dict[str, Any]] = Field(default_factory=list)
    confirmed: bool = True  # False = user clicked Cancel


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/jarvis/ask")
def jarvis_ask(
    payload: JarvisAskRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Submit a user message and get the assistant's response.

    Response shape (consumed by JarvisChatModal):
      {
        "answer": str,
        "tool_calls_executed": [{name, args, result_summary, tool_call_id}],
        "pending_confirmations": [{tool_call_id, name, args, preview}],
        "history": [...messages...],
        "model": "z-ai/glm-4.7" | overridden,
        "error": null | "human-readable reason"
      }
    """
    user = _require_operator(db, request)
    return jarvis_agent.run_agent(
        db=db,
        user_id=user.user_id,
        user_timezone=user.timezone or "UTC",
        user_message=payload.message,
        history=payload.history,
    )


@router.post("/jarvis/confirm")
def jarvis_confirm(
    payload: JarvisConfirmRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Confirm or reject a queued write action.

    On confirm: executes the write tool (with the audit log flipped to
    status='executed', confirmed_at stamped) and re-enters the agent
    loop with the result so NIM can produce the follow-up text ("Done —
    created Lab 8 for 3pm").

    On reject: marks the latest pending invocation for this tool/args
    as status='rejected' and returns a short cancel acknowledgement —
    no NIM round-trip.
    """
    user = _require_operator(db, request)

    if not payload.confirmed:
        # Mark the most recent pending row for this user/tool as rejected.
        # We don't try to match args precisely — the user can only have
        # one pending confirmation in flight at a time per the UI contract.
        pending_row = (
            db.query(JarvisInvocation)
            .filter(
                JarvisInvocation.user_id == user.user_id,
                JarvisInvocation.tool_name == payload.name,
                JarvisInvocation.status == "pending_confirmation",
            )
            .order_by(JarvisInvocation.invoked_at.desc())
            .first()
        )
        if pending_row is not None:
            pending_row.status = "rejected"
            db.commit()
        return {
            "answer": "Cancelled.",
            "tool_calls_executed": [],
            "pending_confirmations": [],
            "history": payload.history,
            "model": settings.NVIDIA_NIM_MODEL,
            "error": None,
        }

    # Confirmed — execute and re-enter the agent loop with the result.
    result = jarvis_tools.execute_write_tool_after_confirm(
        db, user.user_id, payload.name, payload.args
    )
    # Also flip any prior pending row for the same name/args to executed.
    pending_row = (
        db.query(JarvisInvocation)
        .filter(
            JarvisInvocation.user_id == user.user_id,
            JarvisInvocation.tool_name == payload.name,
            JarvisInvocation.status == "pending_confirmation",
        )
        .order_by(JarvisInvocation.invoked_at.desc())
        .first()
    )
    if pending_row is not None:
        pending_row.status = "executed"
        pending_row.confirmed_at = now_utc()
        db.commit()

    # Inject the tool result into the history and ask NIM for the
    # follow-up sentence. We synthesize a synthetic system note so NIM
    # knows the action just happened.
    follow_up_message = (
        f"The user just confirmed '{payload.name}'. Result: {result}. "
        "Briefly tell the user what just happened — one short sentence."
    )
    return jarvis_agent.run_agent(
        db=db,
        user_id=user.user_id,
        user_timezone=user.timezone or "UTC",
        user_message=follow_up_message,
        history=payload.history,
    )


@router.get("/jarvis/health")
def jarvis_health(
    request: Request, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """NIM availability + current model. Used by the floating-button glow.

    Operator-only — same gate as the chat endpoints. Returns:
      {available: bool, model: "...", reason: str|null}
    """
    _require_operator(db, request)
    return nvidia_nim_client.health_check()
