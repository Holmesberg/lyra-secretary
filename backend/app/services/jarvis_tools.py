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

from app.services.inference_engine import (
    classify_disagreement as _classify_disagreement,
    classify_task_valence as _classify_task_valence,
)

from app.db.models import (
    Deadline,
    JarvisInvocation,
    PauseEvent,
    PausePredictionLog,
    ReflectionViewLog,
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
            "name": "get_pattern_summary",
            "description": (
                "Multi-dimensional cross-cut of the user's recent task data in "
                "ONE call: totals, top categories with bias_factor, by-time-of-"
                "day deltas, readiness-vs-outcome signal, skip rate, overdue "
                "count, and outliers. ALWAYS use this for analytical / pattern "
                "/ trend / 'how am I doing' / 'compare' questions instead of "
                "chaining individual tools — it returns the full picture at "
                "once."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "window_days": {
                        "type": "integer",
                        "description": "Look-back window in days (default 14, max 90).",
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
            "name": "get_active_session",
            "description": (
                "The currently running stopwatch session, if any (state "
                "EXECUTING or PAUSED). Returns null when no session is "
                "active. Use to answer 'what am I working on right now?'"
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    # ----- Phase 2 discovery layer (2026-05-02) -----
    # Operator-only behavioral pattern discovery. These tools expose the
    # ~24 PROMOTE-TO-JARVIS signals from docs/data_utilization_inventory_2026_05_02.md
    # so JARVIS can synthesize hypotheses from the operator's own data.
    # Per docs/calibration_contract.md and project_lyra_is_behavioral_inference_engine.
    {
        "type": "function",
        "function": {
            "name": "analyze_behavioral_signature",
            "description": (
                "Operator's deep behavioral fingerprint over a window. Returns "
                "pause-reason distribution (overall + by time-of-day + by "
                "initiator), recovery latency by pause reason, hesitation "
                "chain (creation→planned-start→executed-start latencies), "
                "schedule volatility (reschedule distribution), context-"
                "switch graph (parent_task_id transitions), POST_PAUSE_"
                "TRANSITIONS (pause_reason → next-task category, answers "
                "'after distraction what do I switch to'), VALENCE_DISTRIBUTION "
                "(per-task friction|flow|scope_creep|under_plan|neutral classes), "
                "DISAGREEMENT_EVENTS (optimism_collapse=pre≥4+post≤2, "
                "capacity_surprise=pre≤2+post≥4, flow_overrun=high_focus+big_"
                "overrun, friction_completion=low_focus+on_time — the explicit-"
                "vs-implicit axis), snooze chains, reflection engagement "
                "(dwell + outcome per reflection_type), and per-signal "
                "confidence tiers. Use this when the operator asks 'what "
                "patterns do you see', 'discover something', 'what's surprising', "
                "'where do my ratings disagree with my behavior', 'what do I "
                "switch to after X' — the discovery counterpart to "
                "get_pattern_summary's productivity headline. NEVER call both "
                "in one turn."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "window_days": {
                        "type": "integer",
                        "description": "Lookback window in days (default 14, max 90).",
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
            "name": "query_dark_columns",
            "description": (
                "Targeted aggregation over a specific 'dark' column (data "
                "Lyra collects but doesn't normally surface). Whitelist-"
                "scoped — only columns from docs/data_utilization_inventory_"
                "2026_05_02.md PROMOTE-TO-JARVIS list are queryable. Returns "
                "distribution / percentiles / counts (never raw rows). Use "
                "for hypothesis-specific drill-downs after analyze_behavioral_"
                "signature surfaces something interesting."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "column_name": {
                        "type": "string",
                        "description": (
                            "One of the whitelisted column refs: "
                            "'task.reschedule_count', 'task.scope_bullet_count_at_execute', "
                            "'stopwatch_session.original_pre_task_readiness', "
                            "'stopwatch_session.task_completion_percentage', "
                            "'pause_event.active_elapsed_at_pause_seconds', "
                            "'pause_prediction_log.mechanism', 'pause_prediction_log.snooze_chain_depth', "
                            "'reflection_view_log.dwell_seconds', 'reflection_view_log.outcome', "
                            "'jarvis_invocation.tool_name_distribution', 'jarvis_invocation.reasoning_time_seconds'."
                        ),
                    },
                    "window_days": {
                        "type": "integer",
                        "description": "Lookback window in days (default 30, max 90).",
                        "minimum": 1,
                        "maximum": 90,
                    },
                },
                "required": ["column_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_pattern_hypothesis",
            "description": (
                "Record a candidate behavioral pattern hypothesis you've "
                "found in the operator's data. Writes a structured proposal "
                "to the audit log so the operator can later validate or "
                "reject it. EVERY proposed hypothesis must have a falsifier "
                "(what would kill it) and a valence_class (per "
                "docs/calibration_contract.md R9). Tag generality_tag "
                "honestly: most operator-data patterns are operator-only "
                "(topology-specific traits like introspection appetite, "
                "instrumentation tolerance) — only behavioral primitives "
                "(transition friction, recovery latency, abandonment "
                "topology) are 'potentially-general'. Use after analyze_"
                "behavioral_signature reveals a pattern; do NOT call this "
                "for every observation, only ones with predictive structure."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "observation": {
                        "type": "string",
                        "description": "Pattern description in one or two sentences. Cite specific numbers from tool output.",
                    },
                    "signals_used": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Names of signals from analyze_behavioral_signature or query_dark_columns this hypothesis rests on.",
                    },
                    "predicted_outcome": {
                        "type": "string",
                        "description": "What the operator (or future user) should expect to see if this hypothesis is true.",
                    },
                    "falsifier": {
                        "type": "string",
                        "description": "Specific observation that would kill the hypothesis. Required.",
                    },
                    "generality_tag": {
                        "type": "string",
                        "enum": ["operator-only", "potentially-general"],
                        "description": (
                            "'operator-only' for topology-specific traits "
                            "(introspection appetite, instrumentation tolerance, "
                            "archetype fascination); 'potentially-general' for "
                            "behavioral primitives (friction, recovery, "
                            "abandonment, divergence)."
                        ),
                    },
                    "valence_class": {
                        "type": "string",
                        "enum": ["friction", "flow", "scope_creep", "under_plan", "neutral"],
                        "description": (
                            "Per R9: 'friction' (overrun + low focus + many "
                            "pauses + scope unchanged), 'flow' (overrun + high "
                            "focus + few pauses), 'scope_creep' (scope grew "
                            "≥50%), 'under_plan' (underrun + high focus), "
                            "'neutral' (within ±15% of plan)."
                        ),
                    },
                    "n_at_proposal": {
                        "type": "integer",
                        "description": "Sample size supporting this hypothesis at proposal time.",
                        "minimum": 1,
                    },
                },
                "required": [
                    "observation",
                    "signals_used",
                    "predicted_outcome",
                    "falsifier",
                    "generality_tag",
                    "valence_class",
                    "n_at_proposal",
                ],
            },
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
            Deadline.state.in_(("planned", "active", "missed")),
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
            Deadline.state.in_(("planned", "active", "missed")),
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


def _exec_get_pattern_summary(db: Session, user_id: int, args: dict) -> dict:
    """Multi-dimensional cross-cut for analytical questions.

    Single SQL window, then in-Python aggregation. Returns a structured dict
    Lyra can read directly to surface both obvious (largest effect size) and
    subtle (non-headline) patterns. Designed to replace the 4-6 tool chain
    Llama 3.3 70B was previously firing for 'pattern' questions.

    voided_at_guard: applied at the SQL filter level. Voided rows never
    enter the aggregations.
    """
    window_days = max(1, min(int(args.get("window_days", 14)), 90))
    now = now_utc()
    window_start = now - timedelta(days=window_days)

    rows = (
        db.query(Task)
        .filter(
            Task.user_id == user_id,
            Task.voided_at.is_(None),
            Task.created_at >= window_start,
        )
        .all()
    )
    executed = [
        t for t in rows
        if t.state == TaskState.EXECUTED
        and t.executed_duration_minutes is not None
        and t.planned_duration_minutes is not None
    ]
    skipped = [t for t in rows if t.state == TaskState.SKIPPED]
    active = [
        t for t in rows
        if t.state in (TaskState.PLANNED, TaskState.EXECUTING, TaskState.PAUSED)
    ]

    # Per-category aggregation with bias_factor (executed_min / planned_min).
    # bf > 1 = systematic overrun in that category, < 1 = systematic underrun.
    cat_stats: dict[str, dict[str, float]] = {}
    for t in executed:
        cat = t.category or "uncategorized"
        s = cat_stats.setdefault(cat, {"sessions": 0, "exec_min": 0, "plan_min": 0})
        s["sessions"] += 1
        s["exec_min"] += t.executed_duration_minutes or 0
        s["plan_min"] += t.planned_duration_minutes or 0
    by_category_top5 = []
    for cat, s in sorted(cat_stats.items(), key=lambda kv: -kv[1]["sessions"])[:5]:
        bf = round(s["exec_min"] / s["plan_min"], 2) if s["plan_min"] > 0 else None
        by_category_top5.append({
            "category": cat,
            "sessions": int(s["sessions"]),
            "executed_minutes": int(s["exec_min"]),
            "bias_factor": bf,
        })

    # Time-of-day buckets (UTC hour — close-enough for pattern reads;
    # exact local-tz bucketing is a Phase 6 polish item).
    def _tod(dt: datetime) -> str:
        h = dt.hour
        if h < 6:
            return "night"
        if h < 12:
            return "morning"
        if h < 18:
            return "afternoon"
        return "evening"

    tod_acc: dict[str, list[dict]] = {
        "morning": [], "afternoon": [], "evening": [], "night": [],
    }
    for t in executed:
        if t.executed_start_utc is None:
            continue
        delta = (t.planned_duration_minutes or 0) - (t.executed_duration_minutes or 0)
        tod_acc[_tod(t.executed_start_utc)].append({
            "delta": delta,
            "readiness": t.pre_task_readiness,
        })
    by_time_of_day: dict[str, dict | None] = {}
    for bucket, items in tod_acc.items():
        if not items:
            by_time_of_day[bucket] = None
            continue
        deltas = [i["delta"] for i in items]
        rdx = [i["readiness"] for i in items if i["readiness"] is not None]
        by_time_of_day[bucket] = {
            "sessions": len(items),
            "avg_delta_min": round(sum(deltas) / len(deltas), 1),
            "avg_readiness": round(sum(rdx) / len(rdx), 2) if rdx else None,
        }

    # Readiness signal — bivariate split. If sharp sessions show LARGER
    # overruns than drained sessions, that's the VT-22 readiness inversion
    # the manifesto pre-registered. Surface that delta directly.
    sharp_rows = [
        t for t in executed
        if t.pre_task_readiness is not None and t.pre_task_readiness >= 4
    ]
    drained_rows = [
        t for t in executed
        if t.pre_task_readiness is not None and t.pre_task_readiness <= 2
    ]

    def _avg_delta(rs: list[Task]) -> float | None:
        if not rs:
            return None
        return round(
            sum((r.planned_duration_minutes or 0) - (r.executed_duration_minutes or 0) for r in rs)
            / len(rs),
            1,
        )

    readiness_signal = {
        "n_with_readiness": len([t for t in executed if t.pre_task_readiness is not None]),
        "n_sharp_4_or_5": len(sharp_rows),
        "avg_delta_min_when_sharp": _avg_delta(sharp_rows),
        "n_drained_1_or_2": len(drained_rows),
        "avg_delta_min_when_drained": _avg_delta(drained_rows),
    }

    # Skip rate over terminal sessions in window.
    terminal_count = len(executed) + len(skipped)
    skip_rate = round(len(skipped) / terminal_count, 2) if terminal_count else None

    overdue_count = (
        db.query(Deadline)
        .filter(
            Deadline.user_id == user_id,
            Deadline.voided_at.is_(None),
            Deadline.state.in_(("planned", "active")),
            Deadline.due_at_utc < now,
        )
        .count()
    )

    # Outliers — biggest signed deltas (most negative = worst overrun).
    deltas_with_meta = [
        ((t.planned_duration_minutes or 0) - (t.executed_duration_minutes or 0), t)
        for t in executed
    ]
    biggest_overrun = min(deltas_with_meta, key=lambda x: x[0]) if deltas_with_meta else None
    biggest_underrun = max(deltas_with_meta, key=lambda x: x[0]) if deltas_with_meta else None
    outliers = {
        "biggest_overrun_min": biggest_overrun[0] if biggest_overrun else None,
        "biggest_overrun_category": biggest_overrun[1].category if biggest_overrun else None,
        "biggest_overrun_title": (biggest_overrun[1].title or "")[:60] if biggest_overrun else None,
        "biggest_underrun_min": biggest_underrun[0] if biggest_underrun else None,
        "biggest_underrun_category": biggest_underrun[1].category if biggest_underrun else None,
        "biggest_underrun_title": (biggest_underrun[1].title or "")[:60] if biggest_underrun else None,
    }

    return {
        "window_days": window_days,
        "totals": {
            "executed_sessions": len(executed),
            "executed_minutes": int(sum(t.executed_duration_minutes or 0 for t in executed)),
            "skipped_sessions": len(skipped),
            "active_sessions": len(active),
        },
        "by_category_top5": by_category_top5,
        "by_time_of_day_utc": by_time_of_day,
        "readiness_signal": readiness_signal,
        "skip_rate": skip_rate,
        "overdue_count": overdue_count,
        "outliers": outliers,
    }


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
# Phase 2 discovery-layer executors (operator-only behavioral pattern
# discovery, 2026-05-02). Whitelisted access to the ~24 PROMOTE-TO-JARVIS
# signals from docs/data_utilization_inventory_2026_05_02.md.
# ---------------------------------------------------------------------------


def _confidence_tier(n: int, low: int = 5, high: int = 30) -> str:
    """Default confidence tier per docs/calibration_contract.md R2.

    Per-signal overrides (R2.1) handled by callers passing custom thresholds.
    """
    if n < low:
        return "cold_start"
    if n < high:
        return "tentative"
    return "confirmed"


def _percentile(values: list[float], p: float) -> float | None:
    """Simple percentile (no scipy dependency). p in [0, 100]."""
    if not values:
        return None
    s = sorted(values)
    if len(s) == 1:
        return round(s[0], 2)
    k = (len(s) - 1) * (p / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    frac = k - lo
    return round(s[lo] * (1 - frac) + s[hi] * frac, 2)


def _tod_bucket(dt: datetime) -> str:
    """Time-of-day bucket. UTC-only for now (matches get_pattern_summary)."""
    h = dt.hour
    if h < 6:
        return "night"
    if h < 12:
        return "morning"
    if h < 18:
        return "afternoon"
    return "evening"


def _exec_analyze_behavioral_signature(db: Session, user_id: int, args: dict) -> dict:
    """Comprehensive behavioral fingerprint for operator-side pattern discovery.

    Joins task + stopwatch_session + pause_event + pause_prediction_log +
    reflection_view_log over a window. Returns aggregated structures JARVIS
    can reason over.

    Single SQL window pulls; in-Python aggregation. <500ms target on
    operator-scale data (~100 sessions, ~200 pause events per 30 days).

    voided_at_guard: applied at every filter level — voided rows never
    enter the aggregations.
    """
    window_days = max(1, min(int(args.get("window_days", 14)), 90))
    now = now_utc()
    window_start = now - timedelta(days=window_days)

    # ----- Tasks in window (executed only for productivity-substrate metrics)
    tasks = (
        db.query(Task)
        .filter(
            Task.user_id == user_id,
            Task.voided_at.is_(None),
            Task.created_at >= window_start,
        )
        .all()
    )
    executed = [
        t for t in tasks
        if t.state == TaskState.EXECUTED
        and t.executed_duration_minutes is not None
    ]
    n_sessions = len(executed)

    # ----- Pause events in window (joined via session ownership)
    pause_events = (
        db.query(PauseEvent)
        .filter(
            PauseEvent.user_id == user_id,
            PauseEvent.paused_at_utc >= window_start,
        )
        .all()
    )
    n_pause_events = len(pause_events)

    # ----- Pause distribution: by reason × time-of-day × initiator
    pause_by_reason: dict[str, int] = {}
    pause_by_initiator: dict[str, int] = {}
    pause_by_tod_reason: dict[str, dict[str, int]] = {
        "morning": {}, "afternoon": {}, "evening": {}, "night": {},
    }
    for pe in pause_events:
        pause_by_reason[pe.pause_reason] = pause_by_reason.get(pe.pause_reason, 0) + 1
        pause_by_initiator[pe.pause_initiator] = pause_by_initiator.get(pe.pause_initiator, 0) + 1
        bucket = _tod_bucket(pe.paused_at_utc)
        pause_by_tod_reason[bucket][pe.pause_reason] = (
            pause_by_tod_reason[bucket].get(pe.pause_reason, 0) + 1
        )

    def _normalize(d: dict[str, int]) -> dict[str, float]:
        total = sum(d.values()) or 1
        return {k: round(v / total, 3) for k, v in d.items()}

    def _sorted_count_dict(d: dict[str, int]) -> dict[str, int]:
        return dict(sorted(d.items(), key=lambda kv: (-kv[1], kv[0])))

    def _task_time(t: Task) -> datetime:
        return t.executed_start_utc or t.planned_start_utc or t.created_at

    pause_distribution = {
        "by_reason_overall": _normalize(pause_by_reason),
        "by_reason_x_tod": {
            tod: _normalize(reasons) for tod, reasons in pause_by_tod_reason.items()
            if reasons
        },
        "by_initiator": _normalize(pause_by_initiator),
        "n_pause_events": n_pause_events,
    }

    # ----- Recovery latency by pause_reason (resumed_at - paused_at)
    recovery_by_reason: dict[str, dict] = {}
    latencies_by_reason: dict[str, list[float]] = {}
    for pe in pause_events:
        if pe.resumed_at_utc is None or pe.duration_minutes is None:
            continue
        latencies_by_reason.setdefault(pe.pause_reason, []).append(float(pe.duration_minutes))
    for reason, vals in latencies_by_reason.items():
        n = len(vals)
        recovery_by_reason[reason] = {
            "n": n,
            "p50_min": _percentile(vals, 50),
            "p75_min": _percentile(vals, 75),
            "confidence": _confidence_tier(n),
        }

    # ----- Hesitation chain: created_at vs planned_start_utc vs executed_start_utc
    creation_to_planned: list[float] = []
    planned_to_executed: list[float] = []
    for t in tasks:
        if t.planned_start_utc and t.created_at:
            delta = (t.planned_start_utc - t.created_at).total_seconds() / 60.0
            if delta >= 0:
                creation_to_planned.append(delta)
        if t.executed_start_utc and t.planned_start_utc:
            delta = (t.executed_start_utc - t.planned_start_utc).total_seconds() / 60.0
            planned_to_executed.append(delta)
    hesitation_chain = {
        "creation_to_planned_start_minutes": {
            "p50": _percentile(creation_to_planned, 50),
            "p75": _percentile(creation_to_planned, 75),
            "n": len(creation_to_planned),
            "confidence": _confidence_tier(len(creation_to_planned)),
        } if creation_to_planned else None,
        "planned_to_executed_start_minutes": {
            "p50": _percentile(planned_to_executed, 50),
            "p75": _percentile(planned_to_executed, 75),
            "n": len(planned_to_executed),
            "confidence": _confidence_tier(len(planned_to_executed)),
        } if planned_to_executed else None,
    }

    # ----- Schedule volatility: reschedule_count distribution
    rc_buckets = {"0": 0, "1": 0, "2": 0, "3+": 0}
    rc_values: list[int] = []
    for t in tasks:
        rc = t.reschedule_count or 0
        rc_values.append(rc)
        if rc == 0:
            rc_buckets["0"] += 1
        elif rc == 1:
            rc_buckets["1"] += 1
        elif rc == 2:
            rc_buckets["2"] += 1
        else:
            rc_buckets["3+"] += 1
    schedule_volatility = {
        "reschedule_count_distribution": rc_buckets,
        "median_reschedule_count": (
            _percentile([float(v) for v in rc_values], 50) if rc_values else None
        ),
        "max_reschedule_count": max(rc_values) if rc_values else 0,
        "n_tasks": len(tasks),
    }

    # ----- Context-switch graph (parent_task_id linkage + task_switch pauses)
    switch_edges: dict[tuple[str, str], int] = {}
    for t in tasks:
        if t.parent_task_id is None:
            continue
        parent = next((p for p in tasks if p.task_id == t.parent_task_id), None)
        if parent is None:
            continue
        from_cat = parent.category or "uncategorized"
        to_cat = t.category or "uncategorized"
        key = (from_cat, to_cat)
        switch_edges[key] = switch_edges.get(key, 0) + 1
    context_switch_graph = sorted(
        [
            {"from_category": k[0], "to_category": k[1], "count": v}
            for k, v in switch_edges.items()
        ],
        key=lambda d: -d["count"],
    )[:10]

    # ----- Snooze chains via parent_firing_id
    pause_predictions = (
        db.query(PausePredictionLog)
        .filter(
            PausePredictionLog.user_id == user_id,
            PausePredictionLog.fired_at >= window_start,
        )
        .all()
    )
    snooze_count = sum(1 for pp in pause_predictions if pp.parent_firing_id is not None)
    # Compute max chain depth by following parent_firing_id links.
    pp_by_id = {pp.firing_id: pp for pp in pause_predictions}
    max_depth = 0
    for pp in pause_predictions:
        depth = 0
        cur = pp
        while cur.parent_firing_id and cur.parent_firing_id in pp_by_id:
            depth += 1
            cur = pp_by_id[cur.parent_firing_id]
            if depth > 20:
                break  # cycle defense
        max_depth = max(max_depth, depth)
    snooze_chains = {
        "n_pause_predictions": len(pause_predictions),
        "n_snoozes": snooze_count,
        "max_chain_depth": max_depth,
        "by_mechanism": {},
    }
    for pp in pause_predictions:
        m = pp.mechanism
        bag = snooze_chains["by_mechanism"].setdefault(m, {"n": 0, "snoozes": 0})
        bag["n"] += 1
        if pp.parent_firing_id is not None:
            bag["snoozes"] += 1

    # ----- Reflection engagement: dwell + outcome per reflection_type
    reflections = (
        db.query(ReflectionViewLog)
        .filter(
            ReflectionViewLog.user_id == user_id,
            ReflectionViewLog.fired_at >= window_start,
            ReflectionViewLog.event_class == "impression",  # exclude telemetry
        )
        .all()
    )
    reflection_engagement: dict[str, dict] = {}
    for r in reflections:
        rt = r.reflection_type
        bag = reflection_engagement.setdefault(rt, {
            "n_fired": 0, "n_viewed": 0, "n_dismissed": 0,
            "dwell_seconds": [], "outcomes": {},
        })
        bag["n_fired"] += 1
        if r.viewed_at:
            bag["n_viewed"] += 1
        if r.dismissed_at:
            bag["n_dismissed"] += 1
        if r.dwell_seconds is not None:
            bag["dwell_seconds"].append(float(r.dwell_seconds))
        if r.outcome:
            bag["outcomes"][r.outcome] = bag["outcomes"].get(r.outcome, 0) + 1
    for rt, bag in reflection_engagement.items():
        dws = bag.pop("dwell_seconds")
        bag["p50_dwell_seconds"] = _percentile(dws, 50)
        bag["p75_dwell_seconds"] = _percentile(dws, 75)
        bag["confidence"] = _confidence_tier(bag["n_fired"])

    # ----- Valence classification per task (per docs/calibration_contract.md R9)
    valence_counts: dict[str, int] = {
        "friction": 0, "flow": 0, "scope_creep": 0, "under_plan": 0, "neutral": 0,
    }
    for t in executed:
        valence_counts[_classify_task_valence(t)] += 1
    valence_distribution = {
        "counts": valence_counts,
        "n_classified": sum(valence_counts.values()),
        "confidence": _confidence_tier(sum(valence_counts.values())),
        "interpretation": (
            "Per R9: 'friction'=overrun+low_focus+≥3pauses; 'flow'=overrun+"
            "high_focus+≤1pause (success state, NOT friction); 'scope_creep'="
            "overrun+medium_focus (route to VT-22 scope analysis); 'under_plan'="
            "underrun+high_focus; 'neutral'=within ±15% plan."
        ),
    }

    # Sessions are reused by several discovery cuts below. Keeping this as
    # aggregate-only output is what lets JARVIS answer harder questions without
    # leaking raw task rows into the model context.
    sessions = (
        db.query(StopwatchSession)
        .join(Task, Task.task_id == StopwatchSession.task_id)
        .filter(
            Task.user_id == user_id,
            Task.voided_at.is_(None),
            StopwatchSession.start_time_utc >= window_start,
        )
        .all()
    )
    sessions_by_id = {s.session_id: s for s in sessions}
    sessions_sorted = sorted(sessions, key=lambda s: s.start_time_utc)
    tasks_by_id = {t.task_id: t for t in tasks}

    pause_reasons_by_task: dict[str, dict[str, int]] = {}
    for pe in pause_events:
        pe_session = sessions_by_id.get(pe.session_id)
        if pe_session is None:
            continue
        bag = pause_reasons_by_task.setdefault(pe_session.task_id, {})
        bag[pe.pause_reason] = bag.get(pe.pause_reason, 0) + 1

    executed_sorted = sorted(executed, key=_task_time)
    valence_by_task_id = {t.task_id: _classify_task_valence(t) for t in executed}
    disagreement_by_task_id = {
        t.task_id: _classify_disagreement(t) for t in executed
    }

    # ----- Valence preconditions: category, time-of-day, prior task valence,
    # and readiness. This prevents the agent from inventing fingerprints from
    # a generic "valence is covered" label.
    valence_preconditions: dict[str, dict[str, Any]] = {}
    previous_valence: Optional[str] = None
    for t in executed_sorted:
        valence = valence_by_task_id[t.task_id]
        bag = valence_preconditions.setdefault(valence, {
            "n": 0,
            "by_category": {},
            "by_time_of_day": {},
            "by_prior_task_valence": {},
            "by_pre_task_readiness": {},
        })
        bag["n"] += 1
        cat = t.category or "uncategorized"
        tod = _tod_bucket(_task_time(t))
        readiness = (
            str(t.pre_task_readiness)
            if t.pre_task_readiness is not None
            else "missing"
        )
        bag["by_category"][cat] = bag["by_category"].get(cat, 0) + 1
        bag["by_time_of_day"][tod] = bag["by_time_of_day"].get(tod, 0) + 1
        if previous_valence is not None:
            prior = bag["by_prior_task_valence"]
            prior[previous_valence] = prior.get(previous_valence, 0) + 1
        bag["by_pre_task_readiness"][readiness] = (
            bag["by_pre_task_readiness"].get(readiness, 0) + 1
        )
        previous_valence = valence
    for bag in valence_preconditions.values():
        for key in (
            "by_category",
            "by_time_of_day",
            "by_prior_task_valence",
            "by_pre_task_readiness",
        ):
            bag[key] = _sorted_count_dict(bag[key])
        bag["confidence"] = _confidence_tier(bag["n"])

    # ----- Explicit-vs-implicit disagreement events
    disagreement_buckets: dict[str, list[dict]] = {
        "optimism_collapse": [],
        "capacity_surprise": [],
        "flow_overrun": [],
        "friction_completion": [],
    }
    for t in executed:
        kind = _classify_disagreement(t)
        if kind is None:
            continue
        pause_reasons = pause_reasons_by_task.get(t.task_id, {})
        disagreement_buckets[kind].append({
            "category": t.category or "uncategorized",
            "pre_readiness": t.pre_task_readiness,
            "post_reflection": t.post_task_reflection,
            "delta_min": (t.executed_duration_minutes or 0) - (t.planned_duration_minutes or 0),
            "pause_reasons": pause_reasons,
        })
    disagreement_events = {}
    for kind, items in disagreement_buckets.items():
        if not items:
            disagreement_events[kind] = {"n": 0}
            continue
        # Cross-tab by category to find which categories drive each disagreement.
        cat_counts: dict[str, int] = {}
        readiness_counts: dict[str, int] = {}
        category_x_pause_reason: dict[str, dict[str, int]] = {}
        for it in items:
            cat_counts[it["category"]] = cat_counts.get(it["category"], 0) + 1
            readiness_key = (
                str(it["pre_readiness"])
                if it["pre_readiness"] is not None
                else "missing"
            )
            readiness_counts[readiness_key] = readiness_counts.get(readiness_key, 0) + 1
            reason_counts = it["pause_reasons"] or {"no_pause_recorded": 1}
            for reason, count in reason_counts.items():
                cat_bag = category_x_pause_reason.setdefault(it["category"], {})
                cat_bag[reason] = cat_bag.get(reason, 0) + count
        top_cat = max(cat_counts.items(), key=lambda kv: kv[1])
        disagreement_events[kind] = {
            "n": len(items),
            "top_category": top_cat[0],
            "top_category_count": top_cat[1],
            "all_categories": _sorted_count_dict(cat_counts),
            "pre_task_readiness_distribution": _sorted_count_dict(readiness_counts),
            "by_category_x_pause_reason": {
                cat: _sorted_count_dict(reasons)
                for cat, reasons in sorted(category_x_pause_reason.items())
            },
        }
    # Description text for the LLM.
    disagreement_events["_descriptions"] = {
        "optimism_collapse": "pre_readiness≥4 + post_reflection≤2 — felt sharp, executed poorly. High-value calibration primitive.",
        "capacity_surprise": "pre_readiness≤2 + post_reflection≥4 — felt drained, executed well. Under-trusted state.",
        "flow_overrun": "post_reflection≥4 + executed≥1.3×planned — high focus AND big overrun (positive valence, not friction).",
        "friction_completion": "post_reflection≤2 + within ±15% of plan — forced through despite friction. Cost not visible in duration metrics alone.",
    }

    # ----- Post-pause transitions: pause_reason → next-task category
    # Answers "after pauses for reason X, what category does the user pick up?"
    # Distinct from context_switch_graph which only tracks parent_task_id
    # (formal /v1/stopwatch/switch). This catches natural cross-task
    # transitions where the user simply stops one task and starts another.
    post_pause_edges: dict[tuple[str, str], int] = {}
    post_pause_reason_totals: dict[str, int] = {}
    category_jump_by_reason: dict[str, dict[str, int]] = {}
    for pe in pause_events:
        if pe.resumed_at_utc is None:
            continue
        pe_session = sessions_by_id.get(pe.session_id)
        if pe_session is None:
            continue
        origin_task = tasks_by_id.get(pe_session.task_id)
        if origin_task is None:
            continue
        origin_cat = origin_task.category or "uncategorized"
        # Find next session by same user that starts AFTER this pause's resume,
        # and is on a DIFFERENT task (cross-task transition only).
        next_s = None
        for s in sessions_sorted:
            if s.start_time_utc <= pe.resumed_at_utc:
                continue
            if s.task_id == pe_session.task_id:
                continue
            next_s = s
            break
        if next_s is None:
            continue
        next_task = tasks_by_id.get(next_s.task_id)
        if next_task is None:
            continue
        next_cat = next_task.category or "uncategorized"
        key = (pe.pause_reason, next_cat)
        post_pause_edges[key] = post_pause_edges.get(key, 0) + 1
        post_pause_reason_totals[pe.pause_reason] = (
            post_pause_reason_totals.get(pe.pause_reason, 0) + 1
        )
        jump_bag = category_jump_by_reason.setdefault(
            pe.pause_reason, {"same_category": 0, "category_jump": 0}
        )
        if origin_cat == next_cat:
            jump_bag["same_category"] += 1
        else:
            jump_bag["category_jump"] += 1
    post_pause_transitions = sorted(
        [
            {"pause_reason": k[0], "next_category": k[1], "count": v}
            for k, v in post_pause_edges.items()
        ],
        key=lambda d: -d["count"],
    )[:20]

    baseline_category_counts: dict[str, int] = {}
    for t in executed:
        cat = t.category or "uncategorized"
        baseline_category_counts[cat] = baseline_category_counts.get(cat, 0) + 1
    baseline_category_frequency = _normalize(baseline_category_counts)
    post_pause_transitions_lift = []
    for (reason, next_cat), count in post_pause_edges.items():
        reason_total = post_pause_reason_totals.get(reason, 0)
        if reason_total == 0:
            continue
        edge_frequency = round(count / reason_total, 3)
        baseline = baseline_category_frequency.get(next_cat, 0.0)
        lift = round(edge_frequency / baseline, 3) if baseline > 0 else None
        post_pause_transitions_lift.append({
            "pause_reason": reason,
            "next_category": next_cat,
            "count": count,
            "edge_frequency_within_pause_reason": edge_frequency,
            "baseline_category_frequency": baseline,
            "lift_vs_baseline": lift,
        })
    post_pause_transitions_lift = sorted(
        post_pause_transitions_lift,
        key=lambda d: (
            d["lift_vs_baseline"] is None,
            -(d["lift_vs_baseline"] or 0),
            -d["count"],
        ),
    )[:20]
    post_pause_category_jump = {}
    for reason, bag in category_jump_by_reason.items():
        total = bag["same_category"] + bag["category_jump"]
        post_pause_category_jump[reason] = {
            **bag,
            "n": total,
            "category_jump_rate": round(bag["category_jump"] / total, 3) if total else None,
        }

    # ----- Big-overrun next-task valence cascade/rebound map.
    big_overrun_next_valence: dict[str, Any] = {
        "threshold": "executed_duration_minutes >= 1.5 * planned_duration_minutes",
        "n_origin_tasks": 0,
        "by_origin_valence": {},
        "by_origin_disagreement": {},
    }
    for idx, t in enumerate(executed_sorted):
        planned = t.planned_duration_minutes or 0
        executed_minutes = t.executed_duration_minutes or 0
        if planned <= 0 or executed_minutes / planned < 1.5:
            continue
        next_task = executed_sorted[idx + 1] if idx + 1 < len(executed_sorted) else None
        if next_task is None:
            continue
        big_overrun_next_valence["n_origin_tasks"] += 1
        next_valence = valence_by_task_id[next_task.task_id]
        origin_valence = valence_by_task_id[t.task_id]
        origin_disagreement = disagreement_by_task_id[t.task_id] or "none"
        for key_name, key_value in (
            ("by_origin_valence", origin_valence),
            ("by_origin_disagreement", origin_disagreement),
        ):
            bag = big_overrun_next_valence[key_name].setdefault(
                key_value, {"n": 0, "next_valence_counts": {}}
            )
            bag["n"] += 1
            counts = bag["next_valence_counts"]
            counts[next_valence] = counts.get(next_valence, 0) + 1
    for key_name in ("by_origin_valence", "by_origin_disagreement"):
        for bag in big_overrun_next_valence[key_name].values():
            bag["next_valence_counts"] = _sorted_count_dict(bag["next_valence_counts"])

    # ----- Repeated-reschedule terminal-state distribution.
    repeated_reschedule_tasks = [t for t in tasks if (t.reschedule_count or 0) >= 2]
    terminal_state_distribution: dict[str, int] = {}
    terminal_by_category: dict[str, dict[str, int]] = {}
    for t in repeated_reschedule_tasks:
        state = t.state.value if hasattr(t.state, "value") else str(t.state)
        terminal_state_distribution[state] = terminal_state_distribution.get(state, 0) + 1
        cat = t.category or "uncategorized"
        cat_bag = terminal_by_category.setdefault(cat, {})
        cat_bag[state] = cat_bag.get(state, 0) + 1
    reschedule_escape_valves = {
        "filter": "task.reschedule_count >= 2",
        "n_tasks": len(repeated_reschedule_tasks),
        "terminal_state_distribution": _sorted_count_dict(terminal_state_distribution),
        "by_category": {
            cat: _sorted_count_dict(states)
            for cat, states in sorted(terminal_by_category.items())
        },
    }

    # Enrich snooze chains with acceptance by depth and mechanism. If depth
    # never exceeds 0, the agent can say "not enough chain data" instead of
    # inferring a collapse point.
    depth_by_firing_id: dict[str, int] = {}
    for pp in pause_predictions:
        depth = 0
        cur = pp
        while cur.parent_firing_id and cur.parent_firing_id in pp_by_id:
            depth += 1
            cur = pp_by_id[cur.parent_firing_id]
            if depth > 20:
                break
        depth_by_firing_id[pp.firing_id] = depth
    acceptance_by_depth: dict[str, dict[str, int]] = {}
    acceptance_by_mechanism_depth: dict[str, dict[str, dict[str, int]]] = {}
    for pp in pause_predictions:
        depth_key = str(depth_by_firing_id.get(pp.firing_id, 0))
        response = pp.user_response or "no_response"
        depth_bag = acceptance_by_depth.setdefault(depth_key, {"n": 0, "accepted": 0})
        depth_bag["n"] += 1
        if response == "pause_now":
            depth_bag["accepted"] += 1
        mech_bag = acceptance_by_mechanism_depth.setdefault(pp.mechanism, {})
        md_bag = mech_bag.setdefault(depth_key, {"n": 0, "accepted": 0})
        md_bag["n"] += 1
        if response == "pause_now":
            md_bag["accepted"] += 1
    for bag in acceptance_by_depth.values():
        bag["acceptance_rate"] = round(bag["accepted"] / bag["n"], 3) if bag["n"] else None
    for mech_bag in acceptance_by_mechanism_depth.values():
        for bag in mech_bag.values():
            bag["acceptance_rate"] = round(bag["accepted"] / bag["n"], 3) if bag["n"] else None
    snooze_chains["acceptance_by_depth"] = acceptance_by_depth
    snooze_chains["acceptance_by_mechanism_depth"] = acceptance_by_mechanism_depth

    # ----- Confidence per top-level signal (rolled up)
    confidence_per_signal = {
        "pause_distribution": _confidence_tier(n_pause_events),
        "recovery_latency": _confidence_tier(
            sum(len(v) for v in latencies_by_reason.values())
        ),
        "hesitation_chain": _confidence_tier(len(creation_to_planned)),
        "schedule_volatility": _confidence_tier(len(tasks)),
        "context_switch_graph": _confidence_tier(sum(switch_edges.values())),
        "snooze_chains": _confidence_tier(len(pause_predictions)),
        "reflection_engagement": _confidence_tier(len(reflections)),
        "valence_distribution": _confidence_tier(sum(valence_counts.values())),
        "valence_preconditions": _confidence_tier(sum(valence_counts.values())),
        "disagreement_events": _confidence_tier(
            sum(v["n"] for k, v in disagreement_events.items() if k != "_descriptions")
        ),
        "post_pause_transitions": _confidence_tier(sum(post_pause_edges.values())),
        "post_pause_transitions_lift": _confidence_tier(sum(post_pause_edges.values())),
        "big_overrun_next_valence": _confidence_tier(
            big_overrun_next_valence["n_origin_tasks"]
        ),
        "reschedule_escape_valves": _confidence_tier(len(repeated_reschedule_tasks)),
    }
    n_by_covered_signal = {
        "pause behavior (reason distribution, initiator, time-of-day)": n_pause_events,
        "recovery latency by pause reason": sum(
            len(v) for v in latencies_by_reason.values()
        ),
        "task hesitation (creation->planned-start, planned->executed-start)": {
            "creation_to_planned_start_minutes": len(creation_to_planned),
            "planned_to_executed_start_minutes": len(planned_to_executed),
        },
        "schedule volatility (reschedule counts)": len(tasks),
        "context-switch graph via parent_task_id (formal /switch endpoint)": sum(
            switch_edges.values()
        ),
        "post-pause cross-task transitions (pause_reason -> next-task category)": sum(
            post_pause_edges.values()
        ),
        "post-pause transition lift vs baseline category frequency": sum(
            post_pause_edges.values()
        ),
        "post-pause same-category vs category-jump rates": sum(post_pause_edges.values()),
        "task valence classification (friction/flow/scope_creep/under_plan/neutral)": sum(
            valence_counts.values()
        ),
        "valence preconditions (category, time-of-day, prior valence, readiness)": sum(
            valence_counts.values()
        ),
        "explicit-vs-implicit disagreements": sum(
            v["n"] for k, v in disagreement_events.items() if k != "_descriptions"
        ),
        "big-overrun next-task valence": big_overrun_next_valence["n_origin_tasks"],
        "reschedule>=2 terminal-state escape valves": len(repeated_reschedule_tasks),
        "pause-prediction snooze chains and mechanism": len(pause_predictions),
        "reflection-surface engagement (dwell + outcome per reflection_type)": len(reflections),
    }

    return {
        "window_days": window_days,
        "n_sessions": n_sessions,
        "n_pause_events": n_pause_events,
        "pause_distribution": pause_distribution,
        "recovery_latency_by_reason": recovery_by_reason,
        "hesitation_chain": hesitation_chain,
        "schedule_volatility": schedule_volatility,
        "context_switch_graph": context_switch_graph,
        "post_pause_transitions": post_pause_transitions,
        "post_pause_transitions_lift_vs_baseline": post_pause_transitions_lift,
        "post_pause_category_jump": post_pause_category_jump,
        "baseline_category_frequency": baseline_category_frequency,
        "valence_distribution": valence_distribution,
        "valence_preconditions": valence_preconditions,
        "disagreement_events": disagreement_events,
        "big_overrun_next_valence": big_overrun_next_valence,
        "reschedule_escape_valves": reschedule_escape_valves,
        "snooze_chains": snooze_chains,
        "reflection_engagement": reflection_engagement,
        "confidence_per_signal": confidence_per_signal,
        # Explicit grounding for the LLM — what this tool DOES and DOES NOT
        # cover. Anti-hallucination defense added 2026-05-02 after operator
        # caught JARVIS inventing onboarding-fingerprint insights it had no
        # data for.
        "coverage": {
            "covered_signal_categories": [
                "pause behavior (reason distribution, initiator, time-of-day)",
                "recovery latency by pause reason",
                "task hesitation (creation→planned-start, planned→executed-start)",
                "schedule volatility (reschedule counts)",
                "context-switch graph via parent_task_id (formal /switch endpoint)",
                "post-pause cross-task transitions (pause_reason → next-task category)",
                "post-pause transition lift vs baseline category frequency",
                "post-pause same-category vs category-jump rates",
                "task valence classification (friction/flow/scope_creep/under_plan/neutral)",
                "valence preconditions (category, time-of-day, prior valence, readiness)",
                "explicit-vs-implicit disagreements (optimism_collapse, capacity_surprise, flow_overrun, friction_completion)",
                "big-overrun next-task valence, crossed by origin valence and disagreement type",
                "reschedule>=2 terminal-state escape valves",
                "pause-prediction snooze chains and mechanism",
                "reflection-surface engagement (dwell + outcome per reflection_type)",
            ],
            "n_by_covered_signal": n_by_covered_signal,
            "NOT_covered_dont_speculate_about_these": [
                "onboarding fingerprint (integration-connect order, skipped steps, archetype-survey response patterns) — NOT INSTRUMENTED",
                "modal dwell / typing latency / hesitation-before-clicking — NOT INSTRUMENTED (Phase 6 telemetry)",
                "calendar/Moodle integration retry patterns or reconnect cadence",
                "per-archetype-item survey timings or response variance",
                "deadline-binding decision history",
                "daily / weekly cascade chains across days (only immediate next-task after big overrun is computed)",
                "user demographics, age, schooling level",
                "external-event attendance vs no-show patterns",
            ],
            "answering_rule": (
                "Answer only from named fields in this payload. If the user asks for "
                "a slice that is not present as a field, say the slice is not computed "
                "by analyze_behavioral_signature yet. Do not infer category/time/"
                "readiness fingerprints from coverage labels alone."
            ),
            "hallucination_rule": (
                "If the operator asks about a signal in NOT_covered, you MUST say "
                "explicitly: 'I don't have that signal in my tool output — I can only "
                "speak to the categories in covered_signal_categories.' Do NOT invent "
                "patterns from data you don't have. Confident-sounding fabrication is "
                "worse than honest 'I can't answer that with current tools.'"
            ),
        },
    }


# Whitelist of dark columns queryable via query_dark_columns. Each entry maps
# to a handler that returns aggregated stats only — never raw rows. Privacy
# (no leaking individual events to LLM context) + token efficiency.
_DARK_COLUMN_QUERIES: set[str] = {
    "task.reschedule_count",
    "task.scope_bullet_count_at_execute",
    "stopwatch_session.original_pre_task_readiness",
    "stopwatch_session.task_completion_percentage",
    "pause_event.active_elapsed_at_pause_seconds",
    "pause_prediction_log.mechanism",
    "pause_prediction_log.snooze_chain_depth",
    "reflection_view_log.dwell_seconds",
    "reflection_view_log.outcome",
    "jarvis_invocation.tool_name_distribution",
    "jarvis_invocation.reasoning_time_seconds",
}


def _exec_query_dark_columns(db: Session, user_id: int, args: dict) -> dict:
    """Targeted dark-column drill-down. Whitelist-only.

    Per docs/data_utilization_inventory_2026_05_02.md: each PROMOTE-TO-JARVIS
    column has a dedicated handler. Returns distribution / percentiles —
    never raw rows. SQL injection prevented by column whitelist (no string
    interpolation into SQL; explicit ORM filters per case).
    """
    column = args.get("column_name", "")
    if column not in _DARK_COLUMN_QUERIES:
        return {
            "ok": False,
            "reason": "column_not_whitelisted",
            "column": column,
            "whitelist": sorted(_DARK_COLUMN_QUERIES),
        }
    window_days = max(1, min(int(args.get("window_days", 30)), 90))
    now = now_utc()
    window_start = now - timedelta(days=window_days)

    # Per-column dispatch. Each branch returns its own structured result.
    if column == "task.reschedule_count":
        rows = (
            db.query(Task)
            .filter(
                Task.user_id == user_id,
                Task.voided_at.is_(None),
                Task.created_at >= window_start,
            )
            .all()
        )
        vals = [t.reschedule_count or 0 for t in rows]
        return {
            "ok": True,
            "column": column,
            "n": len(vals),
            "p50": _percentile([float(v) for v in vals], 50),
            "p75": _percentile([float(v) for v in vals], 75),
            "p95": _percentile([float(v) for v in vals], 95),
            "max": max(vals) if vals else None,
            "n_with_at_least_one_reschedule": sum(1 for v in vals if v > 0),
            "confidence": _confidence_tier(len(vals)),
        }

    if column == "task.scope_bullet_count_at_execute":
        rows = (
            db.query(Task)
            .filter(
                Task.user_id == user_id,
                Task.voided_at.is_(None),
                Task.state == TaskState.EXECUTED,
                Task.created_at >= window_start,
                Task.scope_bullet_count_at_execute.isnot(None),
            )
            .all()
        )
        vals = [float(t.scope_bullet_count_at_execute) for t in rows]
        # Compare against scope_bullet_count_at_plan for drift signal.
        deltas = []
        for t in rows:
            if t.scope_bullet_count_at_plan is not None:
                deltas.append(
                    float(t.scope_bullet_count_at_execute) - float(t.scope_bullet_count_at_plan)
                )
        return {
            "ok": True,
            "column": column,
            "n": len(vals),
            "execute_p50": _percentile(vals, 50),
            "execute_p75": _percentile(vals, 75),
            "delta_vs_plan_n": len(deltas),
            "delta_vs_plan_p50": _percentile(deltas, 50),
            "delta_vs_plan_p75": _percentile(deltas, 75),
            "confidence": _confidence_tier(len(deltas)),
        }

    if column == "stopwatch_session.original_pre_task_readiness":
        # Readiness drift signal: original_pre_task_readiness is snapshotted at
        # pause time. Compare against the task's pre_task_readiness (set at start)
        # to detect within-session readiness drift.
        rows = (
            db.query(StopwatchSession)
            .join(Task, Task.task_id == StopwatchSession.task_id)
            .filter(
                Task.user_id == user_id,
                Task.voided_at.is_(None),
                StopwatchSession.start_time_utc >= window_start,
                StopwatchSession.original_pre_task_readiness.isnot(None),
            )
            .all()
        )
        vals = [float(s.original_pre_task_readiness) for s in rows]
        # Drift = original_pre_task_readiness (at pause) - task.pre_task_readiness (at start)
        drifts = []
        for s in rows:
            t = db.query(Task).filter(Task.task_id == s.task_id).first()
            if t and t.pre_task_readiness is not None:
                drifts.append(float(s.original_pre_task_readiness - t.pre_task_readiness))
        return {
            "ok": True,
            "column": column,
            "n_with_snapshot": len(vals),
            "snapshot_p50": _percentile(vals, 50),
            "snapshot_p75": _percentile(vals, 75),
            "drift_n": len(drifts),
            "drift_p50": _percentile(drifts, 50),
            "drift_p75": _percentile(drifts, 75),
            "interpretation": "Negative drift = readiness dropped between start and pause (engagement decay). Positive = sharpened up.",
            "confidence": _confidence_tier(len(drifts)),
        }

    if column == "stopwatch_session.task_completion_percentage":
        # Early-stop estimate. Useful as cross-check vs Task.task_completion_percentage
        # (set at final stop). Captured during early-stop confirmation.
        rows = (
            db.query(StopwatchSession)
            .join(Task, Task.task_id == StopwatchSession.task_id)
            .filter(
                Task.user_id == user_id,
                Task.voided_at.is_(None),
                StopwatchSession.start_time_utc >= window_start,
                StopwatchSession.task_completion_percentage.isnot(None),
            )
            .all()
        )
        vals = [float(s.task_completion_percentage) for s in rows]
        # Compare against final completion %.
        diffs = []
        for s in rows:
            t = db.query(Task).filter(Task.task_id == s.task_id).first()
            if t and t.task_completion_percentage is not None:
                diffs.append(
                    float(t.task_completion_percentage - s.task_completion_percentage)
                )
        return {
            "ok": True,
            "column": column,
            "n_early_stop_estimates": len(vals),
            "early_p50": _percentile(vals, 50),
            "early_p75": _percentile(vals, 75),
            "diff_vs_final_n": len(diffs),
            "diff_vs_final_p50": _percentile(diffs, 50),
            "diff_vs_final_p75": _percentile(diffs, 75),
            "interpretation": "Positive diff = final completion % higher than early-stop estimate (recovered after pause). Near-zero = early estimate accurate.",
            "confidence": _confidence_tier(len(vals)),
        }

    if column == "pause_event.active_elapsed_at_pause_seconds":
        rows = (
            db.query(PauseEvent)
            .filter(
                PauseEvent.user_id == user_id,
                PauseEvent.paused_at_utc >= window_start,
                PauseEvent.active_elapsed_at_pause_seconds.isnot(None),
            )
            .all()
        )
        # Cross-tab by pause_reason
        by_reason: dict[str, list[float]] = {}
        for pe in rows:
            by_reason.setdefault(pe.pause_reason, []).append(
                float(pe.active_elapsed_at_pause_seconds)
            )
        out = {}
        for reason, vals in by_reason.items():
            out[reason] = {
                "n": len(vals),
                "p50_seconds": _percentile(vals, 50),
                "p75_seconds": _percentile(vals, 75),
                "confidence": _confidence_tier(len(vals)),
            }
        return {
            "ok": True,
            "column": column,
            "n_total": sum(len(v) for v in by_reason.values()),
            "by_pause_reason": out,
        }

    if column == "pause_prediction_log.mechanism":
        rows = (
            db.query(PausePredictionLog)
            .filter(
                PausePredictionLog.user_id == user_id,
                PausePredictionLog.fired_at >= window_start,
            )
            .all()
        )
        # Cross-tab mechanism × user_response
        by_mech: dict[str, dict] = {}
        for pp in rows:
            bag = by_mech.setdefault(pp.mechanism, {"n": 0, "by_response": {}})
            bag["n"] += 1
            resp = pp.user_response or "no_response"
            bag["by_response"][resp] = bag["by_response"].get(resp, 0) + 1
        return {
            "ok": True,
            "column": column,
            "n_total": len(rows),
            "by_mechanism": by_mech,
            "confidence": _confidence_tier(len(rows)),
        }

    if column == "pause_prediction_log.snooze_chain_depth":
        rows = (
            db.query(PausePredictionLog)
            .filter(
                PausePredictionLog.user_id == user_id,
                PausePredictionLog.fired_at >= window_start,
            )
            .all()
        )
        rows_by_id = {r.firing_id: r for r in rows}
        chain_depths: list[int] = []
        seen_root: set[str] = set()
        for r in rows:
            # Walk up to find chain root
            cur = r
            depth = 0
            while cur.parent_firing_id and cur.parent_firing_id in rows_by_id:
                cur = rows_by_id[cur.parent_firing_id]
                depth += 1
                if depth > 20:
                    break
            if cur.firing_id not in seen_root:
                seen_root.add(cur.firing_id)
                # Walk down to count chain depth from root
                # (simpler: use the depth from r upward, but inverted)
                chain_depths.append(depth)
        return {
            "ok": True,
            "column": column,
            "n_chains": len(chain_depths),
            "max_depth": max(chain_depths) if chain_depths else 0,
            "median_depth": _percentile([float(d) for d in chain_depths], 50),
            "n_with_snooze": sum(1 for d in chain_depths if d > 0),
        }

    if column == "reflection_view_log.dwell_seconds":
        rows = (
            db.query(ReflectionViewLog)
            .filter(
                ReflectionViewLog.user_id == user_id,
                ReflectionViewLog.fired_at >= window_start,
                ReflectionViewLog.event_class == "impression",
                ReflectionViewLog.dwell_seconds.isnot(None),
            )
            .all()
        )
        by_type: dict[str, list[float]] = {}
        for r in rows:
            by_type.setdefault(r.reflection_type, []).append(float(r.dwell_seconds))
        out = {}
        for rt, vals in by_type.items():
            out[rt] = {
                "n": len(vals),
                "p50_seconds": _percentile(vals, 50),
                "p75_seconds": _percentile(vals, 75),
                "p95_seconds": _percentile(vals, 95),
                "confidence": _confidence_tier(len(vals)),
            }
        return {
            "ok": True,
            "column": column,
            "n_total": sum(len(v) for v in by_type.values()),
            "by_reflection_type": out,
        }

    if column == "reflection_view_log.outcome":
        rows = (
            db.query(ReflectionViewLog)
            .filter(
                ReflectionViewLog.user_id == user_id,
                ReflectionViewLog.fired_at >= window_start,
                ReflectionViewLog.event_class == "impression",
                ReflectionViewLog.outcome.isnot(None),
            )
            .all()
        )
        by_type: dict[str, dict[str, int]] = {}
        for r in rows:
            bag = by_type.setdefault(r.reflection_type, {})
            bag[r.outcome] = bag.get(r.outcome, 0) + 1
        return {
            "ok": True,
            "column": column,
            "n_total": len(rows),
            "by_reflection_type_x_outcome": by_type,
            "confidence": _confidence_tier(len(rows)),
        }

    if column == "jarvis_invocation.tool_name_distribution":
        rows = (
            db.query(JarvisInvocation)
            .filter(
                JarvisInvocation.user_id == user_id,
                JarvisInvocation.invoked_at >= window_start,
            )
            .all()
        )
        counts: dict[str, int] = {}
        for r in rows:
            counts[r.tool_name] = counts.get(r.tool_name, 0) + 1
        sorted_counts = dict(sorted(counts.items(), key=lambda kv: -kv[1]))
        return {
            "ok": True,
            "column": column,
            "n_total": len(rows),
            "tool_name_counts": sorted_counts,
            "interpretation": "Operator's question patterns. Most-asked tools reveal what the operator cares about.",
            "confidence": _confidence_tier(len(rows)),
        }

    if column == "jarvis_invocation.reasoning_time_seconds":
        rows = (
            db.query(JarvisInvocation)
            .filter(
                JarvisInvocation.user_id == user_id,
                JarvisInvocation.invoked_at >= window_start,
                JarvisInvocation.confirmed_at.isnot(None),
            )
            .all()
        )
        deltas = [
            (r.confirmed_at - r.invoked_at).total_seconds()
            for r in rows
            if r.confirmed_at and r.invoked_at
        ]
        return {
            "ok": True,
            "column": column,
            "n": len(deltas),
            "p50_seconds": _percentile(deltas, 50),
            "p75_seconds": _percentile(deltas, 75),
            "max_seconds": max(deltas) if deltas else None,
            "interpretation": "Operator's reasoning time on confirmable JARVIS write tools (a meta-signal about cognitive load when JARVIS proposes).",
            "confidence": _confidence_tier(len(deltas)),
        }

    # Fallthrough — should never hit because of whitelist check above.
    return {"ok": False, "reason": "no_handler", "column": column}


def _exec_propose_pattern_hypothesis(db: Session, user_id: int, args: dict) -> dict:
    """Record a structured hypothesis proposal in JarvisInvocation audit log.

    Validates required fields + valence_class + generality_tag enum values.
    Returns the invocation_id so the operator can later cite specific
    hypotheses by ID in the docs/jarvis_hypothesis_log.md when promoting
    or rejecting.
    """
    required = [
        "observation", "signals_used", "predicted_outcome", "falsifier",
        "generality_tag", "valence_class", "n_at_proposal",
    ]
    missing = [f for f in required if f not in args or args[f] in (None, "", [])]
    if missing:
        return {"ok": False, "reason": "missing_required_fields", "missing": missing}

    valid_generality = {"operator-only", "potentially-general"}
    if args["generality_tag"] not in valid_generality:
        return {
            "ok": False,
            "reason": "invalid_generality_tag",
            "value": args["generality_tag"],
            "allowed": sorted(valid_generality),
        }

    valid_valence = {"friction", "flow", "scope_creep", "under_plan", "neutral"}
    if args["valence_class"] not in valid_valence:
        return {
            "ok": False,
            "reason": "invalid_valence_class",
            "value": args["valence_class"],
            "allowed": sorted(valid_valence),
        }

    # The hypothesis itself lives in tool_args of the audit row written by
    # write_invocation in execute_read_tool. We just return a structured
    # confirmation so the agent can describe what it just recorded.
    return {
        "ok": True,
        "recorded": True,
        "observation": args["observation"][:200],
        "generality_tag": args["generality_tag"],
        "valence_class": args["valence_class"],
        "n_at_proposal": args["n_at_proposal"],
        "next_step": (
            "Operator reviews via JARVIS in /v1/jarvis/ask later or via "
            "the docs/jarvis_hypothesis_log.md companion doc. Promotion "
            "to Phase 3 inference_engine requires (a) operator validation, "
            "(b) re-derivability via rule-based math, (c) generality_tag "
            "= 'potentially-general' for non-operator user surfaces."
        ),
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
    if d.state in ("completed", "skipped"):
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
    "get_pattern_summary": _exec_get_pattern_summary,
    # Phase 2 discovery layer (2026-05-02)
    "analyze_behavioral_signature": _exec_analyze_behavioral_signature,
    "query_dark_columns": _exec_query_dark_columns,
    "propose_pattern_hypothesis": _exec_propose_pattern_hypothesis,
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
