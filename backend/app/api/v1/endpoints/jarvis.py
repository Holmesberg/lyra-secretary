"""Parked JARVIS compatibility endpoints.

JARVIS is no longer an active runtime assistant. OpenClaw is the operator
reasoning shell; historical ``JarvisInvocation`` rows stay exportable and
deletable, but these endpoints must not invoke models, tools, or writes.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, operator_user_from_scope

router = APIRouter()


class JarvisAskRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    history: list[dict[str, Any]] = Field(default_factory=list)


class JarvisConfirmRequest(BaseModel):
    tool_call_id: str
    name: str
    args: dict[str, Any]
    history: list[dict[str, Any]] = Field(default_factory=list)
    confirmed: bool = True


def _require_operator(db: Session, request: Request) -> None:
    operator_user_from_scope(db, request=request)


def _jarvis_disabled() -> None:
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "error": "jarvis_disabled",
            "status": "parked",
            "message": (
                "JARVIS runtime assistant is disabled. Use OpenClaw as the "
                "operator reasoning shell; no Jarvis model/tool execution is "
                "authorized during the freeze."
            ),
        },
    )


@router.post("/jarvis/ask")
def jarvis_ask(
    _payload: JarvisAskRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    _require_operator(db, request)
    _jarvis_disabled()


@router.post("/jarvis/confirm")
def jarvis_confirm(
    _payload: JarvisConfirmRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    _require_operator(db, request)
    _jarvis_disabled()


@router.get("/jarvis/health")
def jarvis_health(request: Request, db: Session = Depends(get_db)) -> None:
    _require_operator(db, request)
    _jarvis_disabled()
