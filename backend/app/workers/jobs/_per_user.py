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
from typing import Callable

from app.db.models import User
from app.db.scoping import set_current_user_id
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def for_each_user(per_user_fn: Callable) -> None:
    """Run per_user_fn(db, user) for every user, scoped to that user.

    Each iteration gets its own DB session so a failure on one user
    doesn't poison the next. Exceptions are logged and swallowed.
    """
    bootstrap = SessionLocal()
    try:
        users = bootstrap.query(User).all()
    finally:
        bootstrap.close()

    for user in users:
        set_current_user_id(user.user_id)
        db = SessionLocal()
        try:
            per_user_fn(db, user)
        except Exception as e:
            logger.error(
                f"per-user job failed for user_id={user.user_id}: {e}",
                exc_info=True,
            )
        finally:
            db.close()
            set_current_user_id(None)
