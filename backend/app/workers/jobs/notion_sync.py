"""Background job to retry failed Notion syncs (per-user, gated)."""
import logging

from app.core.config import settings
from app.db.models import Task, User
from app.utils.redis_client import RedisClient
from app.services.notion_client import NotionClient
from app.services.operator_notifier import (
    format_alert_context,
    notify_operator,
    redacted_user_ref,
)
from app.workers.jobs._per_user import for_each_user

logger = logging.getLogger(__name__)


def retry_failed_syncs():
    for_each_user(_run_for_one_user)


def _run_for_one_user(db, user: User):
    """Notion sync is gated on user.notion_enabled (operator-only in Phase 2)."""
    if not user.notion_enabled:
        return

    redis = RedisClient()
    uid = str(user.user_id)
    items = redis.get_notion_sync_queue(user_id=uid, limit=10)
    if not items:
        return

    if not settings.NOTION_API_KEY or not settings.NOTION_DATABASE_ID:
        notify_operator(
            "Notion retry queue has pending items, but Notion credentials "
            "are missing. Queue retained for the next retry.\n\n"
            + format_alert_context(
                affected="Notion / retry queue",
                scope=redacted_user_ref(user.user_id),
                retry=(
                    "Queue is retained and the job retries on the next "
                    "scheduled cycle."
                ),
                user_action="No student action; operator must restore credentials.",
                data_integrity=(
                    "Queued sync items are retained; no task data is dropped."
                ),
            ),
            source="scheduler.notion",
            severity="error",
            dedupe_key=f"notion-missing-creds:{user.user_id}",
            cooldown_seconds=60 * 60,
        )
        return

    notion = NotionClient()
    success_count = 0
    try:
        for item in items:
            task_id = item["task_id"]
            task = db.query(Task).filter(Task.task_id == task_id).first()
            if not task or task.voided_at is not None:
                # Belongs to a different user, deleted, or voided — drop from queue.
                success_count += 1
                continue
            try:
                notion.sync_task(task)
                success_count += 1
                logger.info(f"Retried Notion sync for {task_id} (user {user.user_id})")
            except Exception as e:
                logger.error(f"Notion sync retry failed for {task_id}: {e}")
                notify_operator(
                    f"Notion retry failed for `{redacted_user_ref(user.user_id)}` "
                    f"task_id `{task_id}` with `{type(e).__name__}`. "
                    "Queue retained from this item onward.\n\n"
                    + format_alert_context(
                        affected="Notion / retry queue",
                        scope=redacted_user_ref(user.user_id),
                        retry=(
                            "Queue is retained from this item onward and "
                            "will retry on the next scheduled cycle."
                        ),
                        user_action=(
                            "No student action unless the operator confirms "
                            "Notion needs reconnect."
                        ),
                        data_integrity=(
                            "Unsynced items remain queued; completed earlier "
                            "items are committed before removal."
                        ),
                    ),
                    source="scheduler.notion",
                    severity="error",
                    dedupe_key=f"notion-sync-failed:{user.user_id}:{task_id}:{type(e).__name__}",
                    cooldown_seconds=60 * 60,
                )
                break
    finally:
        if success_count > 0:
            db.commit()
            redis.remove_from_notion_queue(user_id=uid, count=success_count)
