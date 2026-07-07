"""Per-user iteration helper for background jobs.

Every APScheduler job that touches owning tables (task, stopwatch_session)
must iterate users explicitly and set the scoping ContextVar before
running its per-user logic. The before_compile hook then auto-scopes
every query inside.

Usage:
    from app.workers.jobs._per_user import for_each_user

    def my_job():
        for_each_user(_run_for_one_user)

    def _run_for_one_user(db, user):
        # All db.query(Task) calls here are auto-scoped to user.user_id
        ...
"""
import logging
import time
from typing import Callable, Iterable, Optional

from sqlalchemy.exc import OperationalError

from app.db.models import User
from app.db.scoping import set_current_user_id
from app.db.session import SessionLocal, engine
from app.services.operator_notifier import (
    format_alert_context,
    notify_operator,
    redacted_user_ref,
)
from app.workers.jobs._scheduler_contract import (
    JobResult,
    MUTATION_MAY_HAVE_STARTED,
    NO_MUTATION_ATTEMPTED,
    SchedulerJobDegraded,
    degrade_job,
)

logger = logging.getLogger(__name__)

BOOTSTRAP_MAX_ATTEMPTS = 2
BOOTSTRAP_RETRY_DELAY_SECONDS = 1.0
BOOTSTRAP_BACKOFF_SECONDS = 120.0
_bootstrap_backoff_until_monotonic = 0.0


def _dispose_engine_pool() -> None:
    """Drop stale pooled DB connections after a bootstrap OperationalError."""
    try:
        engine.dispose()
    except Exception:  # noqa: BLE001 - diagnostics only; keep worker alive
        logger.warning(
            "per-user bootstrap could not dispose DB engine pool",
            exc_info=True,
        )


def _open_db_backoff() -> None:
    global _bootstrap_backoff_until_monotonic
    _bootstrap_backoff_until_monotonic = (
        time.monotonic() + BOOTSTRAP_BACKOFF_SECONDS
    )


def _remaining_backoff_seconds() -> float:
    return max(0.0, _bootstrap_backoff_until_monotonic - time.monotonic())


def _load_user_ids() -> list[int]:
    """Load user ids for per-user worker iteration with one DB retry.

    The bootstrap read is shared by every per-user scheduler job. A transient
    pool/SSL EOF should not make APScheduler mark the whole job as failed.
    """
    global _bootstrap_backoff_until_monotonic
    now = time.monotonic()
    if now < _bootstrap_backoff_until_monotonic:
        remaining = _bootstrap_backoff_until_monotonic - now
        logger.info(
            "per-user bootstrap in DB backoff for %.1fs; skipping this tick",
            remaining,
        )
        raise SchedulerJobDegraded(
            "per_user",
            "scheduler.per-user / database bootstrap",
        )

    for attempt in range(1, BOOTSTRAP_MAX_ATTEMPTS + 1):
        bootstrap = SessionLocal()
        failed_operationally = False
        try:
            user_ids = [row[0] for row in bootstrap.query(User.user_id).all()]
            _bootstrap_backoff_until_monotonic = 0.0
            return user_ids
        except OperationalError:
            failed_operationally = True
            try:
                bootstrap.rollback()
            except Exception:  # noqa: BLE001 - session may already be broken
                logger.debug(
                    "per-user bootstrap rollback failed after OperationalError",
                    exc_info=True,
                )
            logger.warning(
                "per-user bootstrap user-id query failed with OperationalError "
                "on attempt %s/%s",
                attempt,
                BOOTSTRAP_MAX_ATTEMPTS,
                exc_info=True,
            )
        finally:
            bootstrap.close()

        if failed_operationally:
            _dispose_engine_pool()
            if attempt < BOOTSTRAP_MAX_ATTEMPTS:
                time.sleep(BOOTSTRAP_RETRY_DELAY_SECONDS)

    _open_db_backoff()
    degrade_job(
        job_id="per_user",
        subsystem="scheduler.per-user / database bootstrap",
        message=(
            "Per-user worker bootstrap failed while loading user ids with "
            "`OperationalError`. Job skipped this tick; check backend logs."
        ),
        affected="scheduler.per-user / database bootstrap",
        scope="unknown user count; bootstrap could not load user ids",
        retry=(
            f"Retried {BOOTSTRAP_MAX_ATTEMPTS} total attempt(s), disposed "
            "the DB engine pool after each failure, then opens a short "
            f"{int(BOOTSTRAP_BACKOFF_SECONDS)}s DB backoff before "
            "per-user bootstrap retries."
        ),
        user_action=(
            "No student action. Operator should triage immediately if "
            "this repeats."
        ),
        data_integrity=NO_MUTATION_ATTEMPTED,
        source="scheduler.per-user",
        severity="error",
        dedupe_key="bootstrap-user-ids:OperationalError",
        cooldown_seconds=30 * 60,
        notifier=notify_operator,
    )


def for_each_user(
    per_user_fn: Callable,
    user_ids: Optional[Iterable[int]] = None,
    job_name: str | None = None,
) -> JobResult:
    """Run per_user_fn(db, user) for every user, scoped to that user.

    Each iteration gets its own DB session so a failure on one user
    doesn't poison the next. Exceptions are logged and swallowed.

    The bootstrap session intentionally loads only ids. Passing ORM
    instances from that closed session into per-user jobs makes user-row
    mutations look successful while commits happen on a different session.
    """
    label = job_name or getattr(per_user_fn, "__name__", "per_user_fn")

    if user_ids is not None and _remaining_backoff_seconds() > 0:
        logger.info(
            "per-user job %s skipped because DB backoff is active for %.1fs",
            label,
            _remaining_backoff_seconds(),
        )
        set_current_user_id(None)
        return JobResult.DEGRADED_HANDLED

    try:
        user_ids = list(user_ids) if user_ids is not None else _load_user_ids()
    except SchedulerJobDegraded:
        set_current_user_id(None)
        return JobResult.DEGRADED_HANDLED

    for user_id in user_ids:
        set_current_user_id(user_id)
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.user_id == user_id).one_or_none()
            if user is None:
                continue
            per_user_fn(db, user)
        except OperationalError as e:
            try:
                db.rollback()
            except Exception:  # noqa: BLE001 - session may already be broken
                logger.debug(
                    "per-user job rollback failed after OperationalError",
                    exc_info=True,
                )
            _dispose_engine_pool()
            _open_db_backoff()
            logger.error(
                "per-user job %s hit OperationalError for user_id=%s; "
                "remaining iterations skipped and DB backoff opened: %s",
                label,
                user_id,
                e,
                exc_info=True,
            )
            try:
                degrade_job(
                    job_id=label,
                    subsystem=f"scheduler.per-user / {label}",
                    message=(
                        f"Per-user worker `{label}` hit `OperationalError` while "
                        f"running for `{redacted_user_ref(user_id)}`. Remaining "
                        "iterations were skipped and DB backoff opened; check "
                        "backend logs."
                    ),
                    affected=f"scheduler.per-user / {label}",
                    scope=(
                        f"{redacted_user_ref(user_id)}; remaining users in "
                        "this job were not attempted"
                    ),
                    retry=(
                        "This user iteration and the remaining users for this "
                        "job were skipped; the DB engine pool was disposed, a "
                        f"{int(BOOTSTRAP_BACKOFF_SECONDS)}s DB backoff opened, "
                        "and the scheduler retries on the next tick."
                    ),
                    user_action=(
                        "No student action. Operator should triage the Barzakh DB "
                        "path if this repeats."
                    ),
                    data_integrity=MUTATION_MAY_HAVE_STARTED,
                    source="scheduler.per-user",
                    severity="error",
                    dedupe_key=f"{label}:OperationalError",
                    cooldown_seconds=30 * 60,
                    notifier=notify_operator,
                )
            except SchedulerJobDegraded:
                pass
            return JobResult.DEGRADED_HANDLED
        except Exception as e:
            logger.error(
                f"per-user job {label} failed for user_id={user_id}: {e}",
                exc_info=True,
            )
            notify_operator(
                f"Per-user worker `{label}` failed for "
                f"`{redacted_user_ref(user_id)}` with `{type(e).__name__}`. "
                "Check backend logs.\n\n"
                + format_alert_context(
                    affected=f"scheduler.per-user / {label}",
                    scope=redacted_user_ref(user_id),
                    retry=(
                        "This user iteration was skipped; the scheduler "
                        "continues with remaining users and retries on the "
                        "next tick."
                    ),
                    user_action=(
                        "No student action unless the operator confirms an "
                        "account-specific repair is needed."
                    ),
                    data_integrity=(
                        "Unknown for this user's job until logs are reviewed; "
                        "DB session is closed and scope is cleared."
                    ),
                ),
                source="scheduler.per-user",
                severity="error",
                dedupe_key=f"{label}:{user_id}:{type(e).__name__}",
                cooldown_seconds=30 * 60,
            )
        finally:
            db.close()
            set_current_user_id(None)
    return JobResult.OK
