"""Timer overflow background job."""
import logging
import httpx

from app.db.session import SessionLocal
from app.db.models import StopwatchSession, Task
from app.utils.time_utils import now_utc
from app.utils.redis_client import RedisClient

logger = logging.getLogger(__name__)

def check_timer_overflow():
    """Detect stopwatch sessions running longer than planned + buffer."""
    db = SessionLocal()
    try:
        now = now_utc()
        redis = RedisClient()
        
        # Get all active sessions
        sessions = db.query(StopwatchSession).filter(
            StopwatchSession.end_time_utc == None,
            StopwatchSession.auto_closed == False
        ).all()
        
        for session in sessions:
            task = db.query(Task).filter(Task.task_id == session.task_id).first()
            if not task or not task.planned_duration_minutes:
                continue
                
            elapsed_minutes = int((now - session.start_time_utc).total_seconds() / 60)
            planned = task.planned_duration_minutes
            
            # Check overflow condition (planned + 5 minutes buffer)
            if elapsed_minutes > (planned + 5):
                
                # Check Redis to ensure we only report overflow once per session
                notified_key = f"overflow_sent:{session.session_id}"
                if redis.client.exists(notified_key):
                    continue
                    
                message = (
                    f"⏱️ '{task.title}' has been running for {elapsed_minutes} min "
                    f"(planned: {planned} min). How complete are you? "
                    "Reply with a percentage (e.g. 75%) or 'done'."
                )
                
                try:
                    import httpx, json
                    # Notify OpenClaw via backend queue
                    httpx.post(
                        "http://localhost:8000/v1/notifications/push", 
                        json={"type": "timer_overflow", "message": message},
                        timeout=5.0
                    )
                    logger.info(f"Queued overflow notification for session {session.session_id} via backend queue")
                    
                except Exception as e:
                    logger.error(f"Failed to queue overflow notification: {e}")
                
                # Always mark as notified to avoid spamming every 2 minutes
                redis.client.setex(notified_key, 86400, "1")  # 24hr TTL
    
    except Exception as e:
        logger.error(f"Error in timer_overflow job: {e}", exc_info=True)
    finally:
        db.close()
