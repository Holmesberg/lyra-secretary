"""One-off operator repair for the Lyra waves stale-pause incident.

This is not a reusable product rule. It requires an explicit email + task_id
before mutating data and records provenance in the task notes.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import sqlalchemy as sa

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.models import PauseEvent, StopwatchSession, Task, TaskState, User
from app.db.session import SessionLocal
from app.services.stopwatch_manager import (
    STALE_PAUSE_RESOLUTION_FLAG,
    STALE_PAUSE_TASK_STATUS,
)
from app.utils.tasks_range_cache import invalidate_user_ranges
from app.utils.time_utils import now_utc, strip_tz
from app.utils.redis_client import RedisClient


def _event_end_time(db, session: StopwatchSession) -> datetime | None:
    candidates = [
        strip_tz(ts)
        for ts in (session.paused_at_utc, session.end_time_utc)
        if ts is not None
    ]
    events = (
        db.query(PauseEvent)
        .filter(PauseEvent.session_id == session.session_id)
        .all()
    )
    for evt in events:
        if evt.paused_at_utc is not None:
            candidates.append(strip_tz(evt.paused_at_utc))
        if evt.resumed_at_utc is not None:
            candidates.append(strip_tz(evt.resumed_at_utc))
    return max(candidates) if candidates else None


def _active_minutes(db, session: StopwatchSession, end_time: datetime) -> tuple[int, float]:
    event_pause_total = float(
        db.query(sa.func.coalesce(sa.func.sum(PauseEvent.duration_minutes), 0))
        .filter(PauseEvent.session_id == session.session_id)
        .scalar()
        or 0
    )
    total_pause = max(float(session.total_paused_minutes or 0), event_pause_total)
    active = max(
        0,
        int(
            round(
                (end_time - strip_tz(session.start_time_utc)).total_seconds() / 60.0
                - total_pause
            )
        ),
    )
    return active, total_pause


def _state_value(task: Task) -> str:
    return task.state.value if hasattr(task.state, "value") else str(task.state)


def list_candidates(email: str) -> int:
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            print(f"user not found: {email}")
            return 1
        tasks = (
            db.query(Task)
            .filter(Task.user_id == user.user_id, sa.func.lower(Task.title) == "lyra waves")
            .order_by(Task.created_at.desc())
            .all()
        )
        print(f"user_id={user.user_id} email={email} candidates={len(tasks)}")
        for task in tasks:
            session = (
                db.query(StopwatchSession)
                .filter(StopwatchSession.task_id == task.task_id)
                .order_by(StopwatchSession.start_time_utc.desc())
                .first()
            )
            if session is None:
                print(f"- task_id={task.task_id} state={_state_value(task)} no_session")
                continue
            end_time = _event_end_time(db, session)
            active = None
            if end_time is not None:
                active, _pause = _active_minutes(db, session, end_time)
            print(
                "- "
                f"task_id={task.task_id} "
                f"state={_state_value(task)} "
                f"session_id={session.session_id} "
                f"planned={task.planned_duration_minutes} "
                f"active={active} "
                f"paused_at={session.paused_at_utc} "
                f"ended_at={session.end_time_utc} "
                f"flag={session.data_quality_flag}"
            )
    return 0


def repair(args: argparse.Namespace) -> int:
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == args.email).first()
        if user is None:
            raise SystemExit(f"user not found: {args.email}")
        task = (
            db.query(Task)
            .filter(Task.user_id == user.user_id, Task.task_id == args.task_id)
            .first()
        )
        if task is None:
            raise SystemExit("task not found for explicit user/task pair")
        if task.title != "Lyra waves":
            raise SystemExit(f"refusing: expected title 'Lyra waves', got {task.title!r}")
        repairable_executed = (
            task.state == TaskState.EXECUTED
            and (task.notes or "").startswith("retrospective_done:")
        )
        if (
            task.state not in (TaskState.SKIPPED, TaskState.PAUSED, TaskState.EXECUTING)
            and not repairable_executed
        ):
            raise SystemExit(f"refusing: unexpected state {_state_value(task)}")

        q = db.query(StopwatchSession).filter(StopwatchSession.task_id == task.task_id)
        if args.session_id:
            q = q.filter(StopwatchSession.session_id == args.session_id)
        session = q.order_by(StopwatchSession.start_time_utc.desc()).first()
        if session is None:
            raise SystemExit("refusing: no stopwatch evidence found")

        end_time = _event_end_time(db, session)
        if end_time is None:
            raise SystemExit("refusing: session has no paused_at or end_time evidence")

        open_events = (
            db.query(PauseEvent)
            .filter(
                PauseEvent.session_id == session.session_id,
                PauseEvent.resumed_at_utc.is_(None),
            )
            .all()
        )
        for evt in open_events:
            evt.resumed_at_utc = max(strip_tz(evt.paused_at_utc), end_time)
            evt.duration_minutes = max(
                0.0,
                (evt.resumed_at_utc - strip_tz(evt.paused_at_utc)).total_seconds()
                / 60.0,
            )
        db.flush()

        active_minutes, total_pause = _active_minutes(db, session, end_time)
        if task.planned_duration_minutes and active_minutes < task.planned_duration_minutes:
            raise SystemExit(
                "refusing: stopwatch evidence does not show planned overrun "
                f"(active={active_minutes}, planned={task.planned_duration_minutes})"
            )

        note = (
            "operator_repair_2026_06_04: Lyra waves stale pause incident; "
            f"session={session.session_id}; "
            f"active_minutes={active_minutes}; "
            f"completion={args.completion}%; "
            f"focus={args.focus}; "
            f"scope={args.scope}; "
            f"data_quality_flag={STALE_PAUSE_RESOLUTION_FLAG}"
        )
        print(
            "repair_plan "
            f"user_id={user.user_id} task_id={task.task_id} session_id={session.session_id} "
            f"active={active_minutes} planned={task.planned_duration_minutes} "
            f"end={end_time.isoformat()} apply={args.apply}"
        )
        if not args.apply:
            print("dry-run only; pass --apply to mutate")
            return 0

        session.end_time_utc = end_time
        session.paused_at_utc = None
        session.total_paused_minutes = total_pause
        session.task_completion_percentage = args.completion
        session.data_quality_flag = STALE_PAUSE_RESOLUTION_FLAG
        session.auto_closed = False

        task.state = TaskState.EXECUTED
        task.executed_start_utc = strip_tz(session.start_time_utc)
        task.executed_end_utc = end_time
        task.executed_duration_minutes = active_minutes
        task.post_task_reflection = args.focus
        task.scope_outcome = args.scope
        task.initiation_status = STALE_PAUSE_TASK_STATUS
        task.last_modified_at = now_utc()
        task.notes = f"{task.notes or ''}\n{note}".strip()

        try:
            redis = RedisClient()
            active = redis.get_active_stopwatch(str(user.user_id))
            pause_state = redis.get_pause_state(str(user.user_id))
            if active and active.get("session_id") == session.session_id:
                redis.clear_stopwatch_state(str(user.user_id))
            elif pause_state and pause_state.get("session_id") == session.session_id:
                redis.clear_pause_state(str(user.user_id))
        except Exception as exc:  # noqa: BLE001 - repair must not fail on cache cleanup
            print(f"cache cleanup warning: {type(exc).__name__}: {exc}")

        db.commit()
        invalidate_user_ranges(user.user_id)
        print("repaired")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--task-id")
    parser.add_argument("--session-id")
    parser.add_argument("--completion", type=int, default=90)
    parser.add_argument("--focus", type=int, default=2)
    parser.add_argument("--scope", default="expanded")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.list:
        return list_candidates(args.email)
    if not args.task_id:
        raise SystemExit("--task-id is required for repair; use --list first")
    if args.completion != 90 or args.focus != 2 or args.scope != "expanded":
        raise SystemExit("this one-off repair is locked to completion=90 focus=2 scope=expanded")
    return repair(args)


if __name__ == "__main__":
    raise SystemExit(main())
