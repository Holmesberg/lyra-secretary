"""JARVIS tool registry — OpenAI function-call schemas + executors.

Operator-only (2026-04-30). Every tool runs under the auto-scoping
ContextVar (current_user_id), so a forgotten user_id filter at the
SQL layer is still defended against by `apply_user_scope()` — but
defense in depth: each tool ALSO writes user_id explicitly when it
matters (create_task, etc.).

Two categories:
  - READ_TOOLS — execute immediately when the agent calls them.
    Side-effect-free (or only the audit log), so no confirmation needed.
  - WRITE_TOOLS — queued as pending confirmations. The agent receives
    a synthetic "queued for confirmation" tool result so it can compose
    the user-facing summary; the actual side-effect runs only when the
    user clicks Confirm in the chat UI.

Adding a new tool: append to READ_TOOLS or WRITE_TOOLS with a TOOL
spec dict, then add an executor in EXECUTORS. The agent loop picks
them up by name.

Argument validation:
  - JSON schema in the TOOL spec is enforced by NIM (the model adheres
    to it on output). We additionally validate at the Python level via
    the `_validate_args()` helper before executing — a hallucinated
    tool call with wrong shape gets a structured error result instead
    of a Python TypeError that crashes the loop.

Audit log: each tool call writes a JarvisInvocation row keyed by
(user_id, tool_name, tool_args, tool_result_summary, status). Read
tools land status='executed' immediately; write tools land
status='pending_confirmation' and update on confirm/reject.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models import (
    Deadline,
    JarvisInvocation,
    StopwatchSession,
    Task,
    TaskSource,
    TaskState,
    User,
)
from app.utils.time_utils import now_utc

# ---------------------------------------------------------------------------
# Tool schemas — OpenAI function-calling JSON shape. NIM consumes these
# verbatim to produce tool_calls in its responses.
# ---------------------------------------------------------------------------

READ_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_today_tasks",
            "description": (
                "List today's tasks (PLANNED + EXECUTING + PAUSED states), "
                "ordered by planned start time. Use this when the user asks "
                "about today's plan, what's next, or what they're working on."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_deadlines",
            "description": (
                "List upcoming and overdue deadlines, soonest-due first. "
                "Includes both Moodle-imported and native deadlines. Use "
                "for questions about due dates, overdue work, what's next, "
                "or planning context."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "window_days": {
                        "type": "integer",
                        "description": "Look-ahead window in days (default 14). Overdue items always included.",
                        "minimum": 1,
                        "maximum": 90,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_focus_minutes",
            "description": (
                "Total focus minutes the user logged across the last N days, "
                "with a per-day breakdown. Counts EXECUTED tasks only."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Look-back window in days (default 7).",
                        "minimum": 1,
                        "maximum": 90,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_overdue_count",
            "description": (
                "Count of deadlines past due_at_utc that are still in "
                "active state (not completed, not skipped). One integer."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_course",
            "description": (
                "The course code (e.g., CMP4099, MAT221) the user has the "
                "most planned + active workload in, derived from category "
                "tags on tasks + deadlines. Useful when the user asks 'what "
                "should I work on?' or 'where's my heaviest load?'"
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_active_session",
            "description": (
                "The currently running stopwatch session, if any (state "
                "EXECUTING or PAUSED). Returns null when no session is "
                "active. Use to answer 'what am I working on right now?'"
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


WRITE_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": (
                "Create a planned task on the user's calendar. ALWAYS requires "
                "user confirmation before the action is taken — the system "
                "will queue it and surface a confirmation chip."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Short task title (e.g., 'Lab 8 problem set')",
                    },
                    "when_iso": {
                        "type": "string",
                        "description": "Planned start time as ISO8601 (e.g., '2026-04-30T15:00:00')",
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Planned duration in minutes (default 30 if user didn't say)",
                        "minimum": 5,
                        "maximum": 720,
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category tag (e.g., course code or 'study')",
                    },
                },
                "required": ["title", "when_iso", "duration_minutes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "start_focus_session",
            "description": (
                "Start a stopwatch session on a planned task. ALWAYS requires "
                "user confirmation before the action is taken."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "UUID of the task to start (from list_today_tasks).",
                    },
                    "readiness": {
                        "type": "integer",
                        "description": "Pre-task readiness 1-5 (1=tired, 5=energized). Default 3 if unsure.",
                        "minimum": 1,
                        "maximum": 5,
                    },
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mark_deadline_done",
            "description": (
                "Mark a deadline as completed. ALWAYS requires user confirmation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "deadline_id": {
                        "type": "string",
                        "description": "UUID of the deadline to mark complete.",
                    },
                },
                "required": ["deadline_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sync_moodle_now",
            "description": (
                "Trigger an immediate Moodle .ics resync for the user (skips "
                "the 6h scheduler interval). ALWAYS requires confirmation."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


def all_tools() -> list[dict[str, Any]]:
    """The full tool list passed to NIM in the agent loop."""
    return READ_TOOLS + WRITE_TOOLS


def is_write_tool(name: str) -> bool:
    """True iff the tool needs a user-confirmation step before execution."""
    return any(t["function"]["name"] == name for t in WRITE_TOOLS)


# ---------------------------------------------------------------------------
# Read-tool executors. Each takes (db, user_id, args) and returns a JSON-
# serializable dict that becomes the tool result string the model sees.
# ---------------------------------------------------------------------------


def _exec_list_today_tasks(db: Session, user_id: int, args: dict) -> dict:
    today = now_utc().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    rows = (
        db.query(Task)
        .filter(
            Task.user_id == user_id,
            Task.voided_at.is_(None),
            Task.state.in_([TaskState.PLANNED, TaskState.EXECUTING, TaskState.PAUSED]),
            Task.planned_start_utc >= today,
            Task.planned_start_utc < tomorrow,
        )
        .order_by(Task.planned_start_utc.asc())
        .all()
    )
    return {
        "count": len(rows),
        "tasks": [
            {
                "task_id": t.task_id,
                "title": t.title,
                "category": t.category,
                "state": t.state.value if hasattr(t.state, "value") else str(t.state),
                "planned_start_utc": t.planned_start_utc.isoformat(),
                "planned_duration_minutes": t.planned_duration_minutes,
            }
            for t in rows
        ],
    }


def _exec_list_deadlines(db: Session, user_id: int, args: dict) -> dict:
    window_days = int(args.get("window_days", 14))
    now = now_utc()
    horizon = now + timedelta(days=window_days)
    rows = (
        db.query(Deadline)
        .filter(
            Deadline.user_id == user_id,
            Deadline.voided_at.is_(None),
            Deadline.state.in_(("planned", "active")),
            Deadline.due_at_utc <= horizon,
        )
        .order_by(Deadline.due_at_utc.asc())
        .all()
    )
    return {
        "count": len(rows),
        "deadlines": [
            {
                "deadline_id": d.deadline_id,
                "title": d.title,
                "due_at_utc": d.due_at_utc.isoformat(),
                "state": d.state,
                "is_overdue": d.due_at_utc < now,
                "external_source": d.external_source,
            }
            for d in rows
        ],
    }


def _exec_get_focus_minutes(db: Session, user_id: int, args: dict) -> dict:
    days = int(args.get("days", 7))
    today = now_utc().replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - timedelta(days=days - 1)
    rows = (
        db.query(Task)
        .filter(
            Task.user_id == user_id,
            Task.voided_at.is_(None),
            Task.state == TaskState.EXECUTED,
            Task.executed_end_utc >= start,
            Task.executed_duration_minutes.is_not(None),
        )
        .all()
    )
    by_day: dict[str, int] = {}
    for t in rows:
        if t.executed_end_utc is None:
            continue
        day_key = t.executed_end_utc.date().isoformat()
        by_day[day_key] = by_day.get(day_key, 0) + (t.executed_duration_minutes or 0)
    total = sum(by_day.values())
    return {
        "total_minutes": total,
        "days": days,
        "by_day": dict(sorted(by_day.items())),
    }


def _exec_get_overdue_count(db: Session, user_id: int, args: dict) -> dict:
    now = now_utc()
    count = (
        db.query(Deadline)
        .filter(
            Deadline.user_id == user_id,
            Deadline.voided_at.is_(None),
            Deadline.state.in_(("planned", "active")),
            Deadline.due_at_utc < now,
        )
        .count()
    )
    return {"overdue_count": count}


def _exec_get_top_course(db: Session, user_id: int, args: dict) -> dict:
    rows = (
        db.query(Task.category)
        .filter(
            Task.user_id == user_id,
            Task.voided_at.is_(None),
            Task.state.in_([TaskState.PLANNED, TaskState.EXECUTING, TaskState.PAUSED]),
            Task.category.is_not(None),
        )
        .all()
    )
    counts: dict[str, int] = {}
    for (cat,) in rows:
        if cat:
            counts[cat] = counts.get(cat, 0) + 1
    if not counts:
        return {"top_course": None, "task_count": 0}
    top = max(counts.items(), key=lambda kv: kv[1])
    return {"top_course": top[0], "task_count": top[1], "all_courses": counts}


def _exec_get_active_session(db: Session, user_id: int, args: dict) -> dict:
    session = (
        db.query(StopwatchSession)
        .join(Task, Task.task_id == StopwatchSession.task_id)
        .filter(
            Task.user_id == user_id,
            Task.voided_at.is_(None),
            StopwatchSession.stopped_at_utc.is_(None),
        )
        .order_by(StopwatchSession.started_at_utc.desc())
        .first()
    )
    if session is None:
        return {"active_session": None}
    task = db.query(Task).filter(Task.task_id == session.task_id).first()
    return {
        "active_session": {
            "session_id": session.session_id,
            "task_id": session.task_id,
            "task_title": task.title if task else None,
            "task_state": (
                task.state.value if task and hasattr(task.state, "value") else (str(task.state) if task else None)
            ),
            "started_at_utc": session.started_at_utc.isoformat(),
        }
    }


# ---------------------------------------------------------------------------
# Write-tool executors. These run AFTER user confirmation. The pre-confirm
# path returns a "queued" stub so the agent can describe the proposed action.
# ---------------------------------------------------------------------------


def _exec_create_task(db: Session, user_id: int, args: dict) -> dict:
    """Run after confirmation. Uses TaskManager for the SMA invariant."""
    from app.services.task_manager import TaskManager

    title = args["title"]
    when_iso = args["when_iso"]
    duration = int(args["duration_minutes"])
    category = args.get("category")

    # The LLM is told the user's timezone in the system prompt (see
    # _build_system_prompt). It may emit a naive ISO (interpreted by
    # TaskManager.to_utc as user-local Cairo time) OR a tz-aware ISO
    # (passed through, TaskManager.to_utc respects the offset). Either
    # way we DO NOT strip tzinfo here — TaskManager handles both cases
    # and the wrong-strip would silently shift aware UTC times into the
    # past via the Cairo-local assumption (start_in_past P4 rejection).
    start_dt = datetime.fromisoformat(when_iso.replace("Z", "+00:00"))
    end_dt = start_dt + timedelta(minutes=duration)

    tm = TaskManager(db)
    task, conflict_result, _ = tm.create_task(
        title=title,
        start=start_dt,
        end=end_dt,
        category=category,
        source=TaskSource.JARVIS,
        force_conflicts=True,
    )
    if task is None:
        return {
            "ok": False,
            "reason": "conflict_blocked",
            "detail": str(conflict_result.severity if conflict_result else "unknown"),
        }
    return {
        "ok": True,
        "task_id": task.task_id,
        "title": task.title,
        "planned_start_utc": task.planned_start_utc.isoformat(),
        "planned_duration_minutes": task.planned_duration_minutes,
    }


def _exec_start_focus_session(db: Session, user_id: int, args: dict) -> dict:
    from app.services.stopwatch_manager import StopwatchManager

    task_id = args["task_id"]
    readiness = int(args.get("readiness", 3))
    task = (
        db.query(Task)
        .filter(Task.task_id == task_id, Task.user_id == user_id, Task.voided_at.is_(None))
        .first()
    )
    if task is None:
        return {"ok": False, "reason": "task_not_found"}
    sm = StopwatchManager(db)
    try:
        session = sm.start(task_id=task_id, readiness=readiness)
    except Exception as e:
        return {"ok": False, "reason": "start_failed", "detail": str(e)[:200]}
    return {
        "ok": True,
        "session_id": getattr(session, "session_id", None),
        "task_id": task_id,
        "task_title": task.title,
    }


def _exec_mark_deadline_done(db: Session, user_id: int, args: dict) -> dict:
    deadline_id = args["deadline_id"]
    d = (
        db.query(Deadline)
        .filter(
            Deadline.deadline_id == deadline_id,
            Deadline.user_id == user_id,
            Deadline.voided_at.is_(None),
        )
        .first()
    )
    if d is None:
        return {"ok": False, "reason": "deadline_not_found"}
    if d.state in ("completed", "missed", "skipped"):
        return {"ok": False, "reason": "terminal_state", "current_state": d.state}
    d.state = "completed"
    d.completed_at = now_utc()
    db.commit()
    return {"ok": True, "deadline_id": deadline_id, "title": d.title}


def _exec_sync_moodle_now(db: Session, user_id: int, args: dict) -> dict:
    from app.workers.jobs.moodle_ics_sync import sync_one_user

    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None or not user.moodle_ics_url:
        return {"ok": False, "reason": "moodle_not_connected"}
    try:
        result = sync_one_user(db, user)
    except Exception as e:
        return {"ok": False, "reason": "sync_failed", "detail": str(e)[:200]}
    return {"ok": True, "result": result if isinstance(result, dict) else {"summary": str(result)[:200]}}


EXECUTORS = {
    # Read
    "list_today_tasks": _exec_list_today_tasks,
    "list_deadlines": _exec_list_deadlines,
    "get_focus_minutes": _exec_get_focus_minutes,
    "get_overdue_count": _exec_get_overdue_count,
    "get_top_course": _exec_get_top_course,
    "get_active_session": _exec_get_active_session,
    # Write
    "create_task": _exec_create_task,
    "start_focus_session": _exec_start_focus_session,
    "mark_deadline_done": _exec_mark_deadline_done,
    "sync_moodle_now": _exec_sync_moodle_now,
}


# ---------------------------------------------------------------------------
# Audit log helpers
# ---------------------------------------------------------------------------


def _summarize_result(result: Any, max_len: int = 480) -> str:
    """One-line summary for the audit log. Keep under 500 chars."""
    if isinstance(result, dict):
        keys = list(result.keys())[:5]
        s = "{" + ", ".join(f"{k}={str(result.get(k))[:60]}" for k in keys) + "}"
    else:
        s = str(result)
    return s[:max_len]


def write_invocation(
    db: Session,
    user_id: int,
    tool_name: str,
    tool_args: dict,
    tool_result: Any,
    status: str = "executed",
    confirmed: bool = False,
) -> str:
    """Insert a JarvisInvocation audit row. Returns the invocation_id."""
    invocation_id = str(uuid4())
    row = JarvisInvocation(
        invocation_id=invocation_id,
        user_id=user_id,
        tool_name=tool_name,
        tool_args=tool_args,
        tool_result_summary=_summarize_result(tool_result),
        status=status,
        invoked_at=now_utc(),
        confirmed_at=now_utc() if confirmed else None,
    )
    db.add(row)
    db.commit()
    return invocation_id


def execute_read_tool(db: Session, user_id: int, name: str, args: dict) -> dict:
    """Run a read tool + log it. Caller injects the result back into the agent loop."""
    if name not in EXECUTORS:
        return {"ok": False, "reason": "unknown_tool", "tool": name}
    if is_write_tool(name):
        # Programmer error; agent loop should never route writes here.
        return {"ok": False, "reason": "is_write_tool"}
    try:
        result = EXECUTORS[name](db, user_id, args or {})
    except Exception as e:
        result = {"ok": False, "reason": "tool_exception", "detail": str(e)[:200]}
        write_invocation(db, user_id, name, args or {}, result, status="failed")
        return result
    write_invocation(db, user_id, name, args or {}, result, status="executed")
    return result


def execute_write_tool_after_confirm(
    db: Session, user_id: int, name: str, args: dict
) -> dict:
    """Run a write tool that the user just confirmed. Logs status='executed'."""
    if name not in EXECUTORS:
        return {"ok": False, "reason": "unknown_tool", "tool": name}
    if not is_write_tool(name):
        return {"ok": False, "reason": "is_read_tool"}
    try:
        result = EXECUTORS[name](db, user_id, args or {})
    except Exception as e:
        result = {"ok": False, "reason": "tool_exception", "detail": str(e)[:200]}
        write_invocation(db, user_id, name, args or {}, result, status="failed", confirmed=True)
        return result
    write_invocation(db, user_id, name, args or {}, result, status="executed", confirmed=True)
    return result
