"""Scheduler outcome and degradation contracts.

Background jobs should distinguish "skipped safely" from "failed
dangerously". Handled degradation returns a named outcome and must not bubble
into APScheduler's generic error listener.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from enum import Enum
from typing import TypeVar

from app.db.session import engine
from app.services.operator_notifier import format_alert_context, notify_operator

logger = logging.getLogger(__name__)


class JobResult(str, Enum):
    OK = "ok"
    DEGRADED_HANDLED = "degraded_handled"
    FAILED_UNHANDLED = "failed_unhandled"


NO_MUTATION_ATTEMPTED = "No mutation attempted."
MUTATION_MAY_HAVE_STARTED = "Mutation may have started; transaction rolled back."
VALID_DATA_INTEGRITY_PHRASES = {
    NO_MUTATION_ATTEMPTED,
    MUTATION_MAY_HAVE_STARTED,
}

DB_DEGRADATION_BACKOFF_SECONDS = 120.0
_degradation_backoff_until_monotonic: dict[str, float] = {}


class SchedulerJobDegraded(Exception):
    """Raised inside a job after the job has handled its own degradation."""

    def __init__(self, job_id: str, subsystem: str):
        super().__init__(f"{job_id}:{subsystem}:degraded_handled")
        self.job_id = job_id
        self.subsystem = subsystem


_T = TypeVar("_T")


def run_scheduler_job(
    job_id: str,
    subsystem: str,
    fn: Callable[[], _T],
    *,
    raise_unhandled: bool = True,
) -> JobResult:
    """Run a scheduler job with explicit OK/degraded/failed outcomes."""
    try:
        result = fn()
    except SchedulerJobDegraded:
        logger.info("scheduler job %s degraded safely in %s", job_id, subsystem)
        return JobResult.DEGRADED_HANDLED
    except Exception:
        logger.exception("scheduler job %s failed unhandled in %s", job_id, subsystem)
        if raise_unhandled:
            raise
        return JobResult.FAILED_UNHANDLED

    if isinstance(result, JobResult):
        return result
    return JobResult.OK


def reset_degradation_backoff() -> None:
    """Test helper: clear process-local scheduler degradation backoff."""
    _degradation_backoff_until_monotonic.clear()


def is_degradation_backoff_active(subsystem: str) -> bool:
    return time.monotonic() < _degradation_backoff_until_monotonic.get(subsystem, 0.0)


def open_degradation_backoff(
    subsystem: str,
    *,
    seconds: float = DB_DEGRADATION_BACKOFF_SECONDS,
) -> None:
    _degradation_backoff_until_monotonic[subsystem] = time.monotonic() + seconds


def remaining_degradation_backoff_seconds(subsystem: str) -> float:
    return max(0.0, _degradation_backoff_until_monotonic.get(subsystem, 0.0) - time.monotonic())


def dispose_engine_pool(log: logging.Logger | None = None) -> None:
    """Drop stale pooled DB connections after a database OperationalError."""
    try:
        engine.dispose()
    except Exception:  # noqa: BLE001 - diagnostics only; keep worker alive
        (log or logger).warning("could not dispose DB engine pool", exc_info=True)


def notify_degraded_once(
    *,
    job_id: str,
    subsystem: str,
    message: str,
    affected: str,
    scope: str,
    retry: str,
    user_action: str,
    data_integrity: str,
    source: str,
    severity: str,
    dedupe_key: str,
    cooldown_seconds: int = 30 * 60,
    notifier: Callable[..., bool] | None = None,
) -> bool:
    """Notify once per subsystem within the active DB degradation backoff.

    Returns True when an alert was sent. Returns False when the same subsystem
    is already inside its process-local DB backoff window.
    """
    if data_integrity not in VALID_DATA_INTEGRITY_PHRASES:
        raise ValueError(
            "scheduler degradation data_integrity must be one of "
            + ", ".join(sorted(VALID_DATA_INTEGRITY_PHRASES))
        )

    if is_degradation_backoff_active(subsystem):
        logger.info(
            "scheduler degradation alert deduped for %s; %.1fs backoff remains",
            subsystem,
            remaining_degradation_backoff_seconds(subsystem),
        )
        return False

    open_degradation_backoff(subsystem)
    notify = notifier or notify_operator
    notify(
        message
        + "\n\n"
        + format_alert_context(
            affected=affected,
            scope=scope,
            retry=retry,
            user_action=user_action,
            data_integrity=data_integrity,
        ),
        source=source,
        severity=severity,
        dedupe_key=dedupe_key,
        cooldown_seconds=cooldown_seconds,
    )
    return True


def degrade_job(
    *,
    job_id: str,
    subsystem: str,
    message: str,
    affected: str,
    scope: str,
    retry: str,
    user_action: str,
    data_integrity: str,
    source: str,
    severity: str,
    dedupe_key: str,
    cooldown_seconds: int = 30 * 60,
    notifier: Callable[..., bool] | None = None,
) -> None:
    """Record handled degradation and raise the internal handled signal."""
    notify_degraded_once(
        job_id=job_id,
        subsystem=subsystem,
        message=message,
        affected=affected,
        scope=scope,
        retry=retry,
        user_action=user_action,
        data_integrity=data_integrity,
        source=source,
        severity=severity,
        dedupe_key=dedupe_key,
        cooldown_seconds=cooldown_seconds,
        notifier=notifier,
    )
    raise SchedulerJobDegraded(job_id, subsystem)
