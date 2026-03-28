"""APScheduler setup for background jobs."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging

from app.workers.jobs.reminders import check_upcoming_tasks
from app.workers.jobs.notion_sync import retry_failed_syncs
from app.workers.jobs.timer_overflow import check_timer_overflow

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()

def start_scheduler():
    """Start background scheduler."""
    # Reminders (check every 1 minute)
    scheduler.add_job(
        check_upcoming_tasks,
        trigger=IntervalTrigger(minutes=1),
        id="reminders",
        name="Check upcoming task reminders",
        replace_existing=True
    )
    
    # Notion sync retry (check every 5 minutes)
    scheduler.add_job(
        retry_failed_syncs,
        trigger=IntervalTrigger(minutes=5),
        id="notion_sync",
        name="Retry failed Notion syncs",
        replace_existing=True
    )

    # Timer overflow (check every 2 minutes)
    scheduler.add_job(
        check_timer_overflow,
        trigger=IntervalTrigger(minutes=2),
        id="timer_overflow",
        name="Check for overflowing stopwatch sessions",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("APScheduler started")


def shutdown_scheduler():
    """Shutdown scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown()
    logger.info("APScheduler shutdown")
