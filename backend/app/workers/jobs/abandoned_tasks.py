"""Abandoned task detection job."""
import logging

from app.db.session import SessionLocal
from app.db.models import Task, TaskState
from app.services.task_manager import TaskManager
from app.utils.time_utils import now_utc

logger = logging.getLogger(__name__)


def check_abandoned_tasks():
    """
    Transition PLANNED tasks to SKIPPED if their window passed without a timer start.

    Runs every 30 minutes. A task is abandoned if:
      - state = PLANNED
      - planned_end_utc < now
      - initiation_status = 'not_started'

    State machine path: PLANNED → SKIPPED (via TaskManager.skip_task)
    initiation_status is then set to 'abandoned' as reason metadata.
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

        manager = TaskManager(db)
        count = 0

        for task in tasks:
            try:
                # Transition to SKIPPED via the state machine — no direct state writes
                task = manager.skip_task(
                    task.task_id,
                    reason="auto-abandoned: task window passed without timer start"
                )
                # Record abandonment as initiation metadata (post-transition write)
                task.initiation_status = "abandoned"
                db.commit()
                count += 1
            except Exception as e:
                logger.error(f"Failed to abandon task {task.task_id}: {e}", exc_info=True)
                db.rollback()

        logger.info(f"Transitioned {count} task(s) to SKIPPED (abandoned)")

    except Exception as e:
        logger.error(f"Error in abandoned_tasks job: {e}", exc_info=True)
    finally:
        db.close()
