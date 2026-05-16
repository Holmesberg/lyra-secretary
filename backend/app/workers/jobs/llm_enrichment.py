"""LLM enrichment background job (Workstream 1, magic-for-alpha 2026-04-28).

Pulls tasks where `llm_parse_status='pending'` and calls
`enrich_task_via_llm` to populate the LLM-derived fields. Lives behind
the operator-locked guardrail #1: this is enrichment, not critical-path.
POST /v1/create has already returned by the time this runs.

Cadence: every 5 seconds. Per cycle, claims up to 3 tasks at a time.
Cross-tenant isolation via `set_current_user_id(None)` (this is a
system-level operation; queries explicitly scope by task.user_id).

Cold cadence: when consecutive enrichments mark `unavailable` (Ollama
down), the next cycle still runs but logs less noisily. APScheduler's
fixed cadence is fine — the worker self-throttles at the per-task call
(30-60s timeout) so a down Ollama doesn't burn CPU.

Idempotency: `enrich_task_via_llm` is idempotent. If the same task is
claimed twice (rare race), the second call sees the terminal status
and no-ops.
"""
import logging
from typing import Optional

from sqlalchemy import asc

from app.db.models import Task
from app.db.scoping import set_current_user_id
from app.db.session import SessionLocal
from app.services.llm_parser import enrich_task_via_llm
from app.services.operator_notifier import notify_operator
from app.utils.time_utils import now_utc

logger = logging.getLogger(__name__)


# Per-cycle cap. Each task takes 5-60s on the LLM (depending on GPU
# availability), so 3-per-cycle at 5s cadence keeps the queue draining
# without blocking long when Ollama is fast.
_MAX_TASKS_PER_CYCLE = 3


def run_llm_enrichment() -> None:
    """Single APScheduler tick. Pulls pending tasks and enriches each.

    Bypasses the SQLAlchemy ContextVar scoping hook for the SELECT
    (system-wide pull); each per-task `enrich_task_via_llm` call is
    user-scoped because it filters Deadline rows by task.user_id.
    """
    set_current_user_id(None)
    db = SessionLocal()
    try:
        # Debounce: skip tasks created in the last 1 second so the create
        # transaction has fully committed before we read the row.
        from datetime import timedelta
        cutoff = now_utc() - timedelta(seconds=1)
        pending = (
            db.query(Task.task_id)
            .filter(
                Task.llm_parse_status == "pending",
                Task.voided_at.is_(None),
                Task.created_at < cutoff,
            )
            .order_by(asc(Task.created_at))
            .limit(_MAX_TASKS_PER_CYCLE)
            .all()
        )
        if not pending:
            return
        status_counts: dict[str, int] = {}
        unexpected_failures = 0
        for (task_id,) in pending:
            try:
                status = enrich_task_via_llm(db, task_id)
                status_counts[status] = status_counts.get(status, 0) + 1
                logger.debug(
                    "llm_enrichment: task=%s status=%s", task_id, status
                )
            except Exception as e:  # noqa: BLE001 — last-resort catch
                unexpected_failures += 1
                logger.exception(
                    "llm_enrichment: unexpected failure for task=%s: %s",
                    task_id,
                    e,
                )
                # Mark failed defensively so the row doesn't loop forever.
                try:
                    task = db.query(Task).filter(Task.task_id == task_id).first()
                    if task and task.llm_parse_status == "pending":
                        task.llm_parse_status = "failed"
                        db.commit()
                except Exception as e:
                    logger.warning("llm_enrichment: status flip to 'failed' rolled back (non-blocking): %s", e)
                    db.rollback()
        problem_count = (
            status_counts.get("failed", 0)
            + status_counts.get("unavailable", 0)
            + unexpected_failures
        )
        if problem_count:
            remaining_pending = (
                db.query(Task.task_id)
                .filter(
                    Task.llm_parse_status == "pending",
                    Task.voided_at.is_(None),
                )
                .count()
            )
            notify_operator(
                "LLM enrichment degraded: "
                f"failed={status_counts.get('failed', 0) + unexpected_failures}, "
                f"unavailable={status_counts.get('unavailable', 0)}, "
                f"pending_backlog={remaining_pending}.",
                source="scheduler.llm-enrichment",
                severity="warn",
                dedupe_key="llm-enrichment-degraded",
                cooldown_seconds=30 * 60,
            )
    finally:
        db.close()
        set_current_user_id(None)
