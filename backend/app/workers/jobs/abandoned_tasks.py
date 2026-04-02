"""Abandoned task detection job."""
import logging

from app.db.session import SessionLocal
from app.db.models import Task, TaskState
from app.utils.time_utils import now_utc

logger = logging.getLogger(__name__)


def check_abandoned_tasks():
    """
    Mark PLANNED tasks as abandoned if their window has passed without a timer start.

    Runs every 30 minutes. A task is abandoned if:
      - state = PLANNED
      - planned_end_utc < now
      - initiation_status = 'not_started'
    """
    db = SessionLocal()
    try:
        now = now_utc()
        tasks = db.query(Task).filter(
            Task.state == TaskState.PLANNED,
            Task.planned_end_utc < now,
            Task.initiation_status == "not_started"
        ).all()

        if not tasks:
            return

        for task in tasks:
            task.initiation_status = "abandoned"

        db.commit()
        logger.info(f"Marked {len(tasks)} task(s) as abandoned")

    except Exception as e:
        logger.error(f"Error in abandoned_tasks job: {e}", exc_info=True)
    finally:
        db.close()
