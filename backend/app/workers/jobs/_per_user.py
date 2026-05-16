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
from typing import Callable

from sqlalchemy.exc import OperationalError

from app.db.models import User
from app.db.scoping import set_current_user_id
from app.db.session import SessionLocal, engine
from app.services.operator_notifier import notify_operator

logger = logging.getLogger(__name__)

BOOTSTRAP_MAX_ATTEMPTS = 2
BOOTSTRAP_RETRY_DELAY_SECONDS = 1.0


def _dispose_engine_pool() -> None:
    """Drop stale pooled DB connections after a bootstrap OperationalError."""
    try:
        engine.dispose()
    except Exception:  # noqa: BLE001 - diagnostics only; keep worker alive
        logger.warning(
            "per-user bootstrap could not dispose DB engine pool",
            exc_info=True,
        )


def _load_user_ids() -> list[int]:
    """Load user ids for per-user worker iteration with one DB retry.

    The bootstrap read is shared by every per-user scheduler job. A transient
    pool/SSL EOF should not make APScheduler mark the whole job as failed.
    """
    for attempt in range(1, BOOTSTRAP_MAX_ATTEMPTS + 1):
        bootstrap = SessionLocal()
        failed_operationally = False
        try:
            return [row[0] for row in bootstrap.query(User.user_id).all()]
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

    notify_operator(
        "Per-user worker bootstrap failed while loading user ids with "
        "`OperationalError`. Job skipped this tick; check backend logs.",
        source="scheduler.per-user",
        severity="error",
        dedupe_key="bootstrap-user-ids:OperationalError",
        cooldown_seconds=30 * 60,
    )
    return []


def for_each_user(per_user_fn: Callable) -> None:
    """Run per_user_fn(db, user) for every user, scoped to that user.

    Each iteration gets its own DB session so a failure on one user
    doesn't poison the next. Exceptions are logged and swallowed.

    The bootstrap session intentionally loads only ids. Passing ORM
    instances from that closed session into per-user jobs makes user-row
    mutations look successful while commits happen on a different session.
    """
    user_ids = _load_user_ids()

    for user_id in user_ids:
        set_current_user_id(user_id)
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.user_id == user_id).one_or_none()
            if user is None:
                continue
            per_user_fn(db, user)
        except Exception as e:
            fn_name = getattr(per_user_fn, "__name__", "per_user_fn")
            logger.error(
                f"per-user job failed for user_id={user_id}: {e}",
                exc_info=True,
            )
            notify_operator(
                f"Per-user worker `{fn_name}` failed for user_id `{user_id}` "
                f"with `{type(e).__name__}`. Check backend logs.",
                source="scheduler.per-user",
                severity="error",
                dedupe_key=f"{fn_name}:{user_id}:{type(e).__name__}",
                cooldown_seconds=30 * 60,
            )
        finally:
            db.close()
            set_current_user_id(None)
