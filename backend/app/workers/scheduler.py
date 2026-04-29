"""APScheduler setup for background jobs."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging

from app.workers.jobs.reminders import check_upcoming_tasks
from app.workers.jobs.notion_sync import retry_failed_syncs
from app.workers.jobs.timer_overflow import check_timer_overflow
from app.workers.jobs.overdue_tasks import detect_and_skip_overdue_tasks
from app.workers.jobs.stale_session_recovery import run_stale_session_recovery
from app.workers.jobs.orphan_task_recovery import run_orphan_task_recovery
from app.workers.jobs.pause_prediction import run_pause_prediction
from app.workers.jobs.reconcile_responses import run_reconcile_responses
from app.workers.jobs.reconcile_deadline_outcomes import run_reconcile_deadline_outcomes
from app.workers.jobs.sweep_missed_deadlines import run_sweep_missed_deadlines
from app.workers.jobs.llm_enrichment import run_llm_enrichment
from app.workers.jobs.resume_prediction import run_resume_prediction
from app.workers.jobs.moodle_ics_sync import run_moodle_ics_sync

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
    
    # Overdue task detection (check every 30 minutes)
    scheduler.add_job(
        detect_and_skip_overdue_tasks,
        trigger=IntervalTrigger(minutes=30),
        id="overdue_tasks",
        name="Detect and skip overdue unstarted tasks",
        replace_existing=True
    )

    # Stale session recovery (check every 15 minutes)
    # Sweeps unclosed StopwatchSession rows older than STALE_THRESHOLD_HOURS
    # (12h) that never got stopped (browser crash mid-pause, container restart,
    # voided task leftovers). LYR-103.
    scheduler.add_job(
        run_stale_session_recovery,
        trigger=IntervalTrigger(minutes=15),
        id="stale_session_recovery",
        name="Auto-close orphan stopwatch sessions older than 12h",
        replace_existing=True
    )

    # Orphan task recovery (every 15 minutes, alongside stale session sweep)
    # Catches tasks stuck in EXECUTING with no open StopwatchSession row —
    # the class of orphan that stale_session_recovery misses (session closed
    # but task state never transitioned). Observed Apr 16-17.
    scheduler.add_job(
        run_orphan_task_recovery,
        trigger=IntervalTrigger(minutes=15),
        id="orphan_task_recovery",
        name="Recover EXECUTING tasks with no active session",
        replace_existing=True
    )

    # VT-17 pause prediction (every 1 minute)
    # Lead window is 2-3 min, so check every minute to catch the boundary.
    # In-job FIRING_COOLDOWN_MINUTES prevents re-fires for the same user.
    scheduler.add_job(
        run_pause_prediction,
        trigger=IntervalTrigger(minutes=1),
        id="pause_prediction",
        name="VT-17 pause prediction — fire + log + queue notification",
        replace_existing=True
    )

    # Reconcile pause_prediction_log outcomes (every 5 minutes)
    # Closes the acceptance window and sets user_response for rows whose
    # predicted_at + ACCEPTANCE_WINDOW_MINUTES has passed without a response.
    scheduler.add_job(
        run_reconcile_responses,
        trigger=IntervalTrigger(minutes=5),
        id="reconcile_responses",
        name="VT-17 outcome reconciliation — close acceptance window",
        replace_existing=True
    )

    # Loop 11 — Phase H reconciliation jobs (2026-04-26).
    # Reconcile deadline_met outcomes for EXECUTED tasks bound to deadlines
    # (every 30 min). Pre-registered MANIFESTO Rule 14.
    scheduler.add_job(
        run_reconcile_deadline_outcomes,
        trigger=IntervalTrigger(minutes=30),
        id="reconcile_deadline_outcomes",
        name="Loop 11 — write task_deadline_outcome rows for EXECUTED deadline-bound tasks",
        replace_existing=True
    )

    # Sweep deadlines that passed due_at_utc without completion (every hour).
    # Transitions active → missed. Planned deadlines stay planned (no task ever bound).
    scheduler.add_job(
        run_sweep_missed_deadlines,
        trigger=IntervalTrigger(hours=1),
        id="sweep_missed_deadlines",
        name="Loop 11 — sweep active deadlines past due_at into missed state",
        replace_existing=True
    )

    # Magic-for-alpha — Workstream 1 (2026-04-28). Pulls tasks where
    # llm_parse_status='pending' and calls Ollama for semantic enrichment
    # (priority, deadline candidates, sub-items). Fires every 5s. Per-cycle
    # cap = 3. Self-throttles when Ollama is down (job runs, marks
    # 'unavailable', returns fast).
    scheduler.add_job(
        run_llm_enrichment,
        trigger=IntervalTrigger(seconds=5),
        id="llm_enrichment",
        name="Magic — LLM async parser; semantic deadline + priority + sub-items",
        replace_existing=True,
        max_instances=1,  # critical: single inflight worker so a slow LLM call doesn't pile up
    )

    # Magic-for-alpha — Workstream 2 (2026-04-28). Sibling of pause_prediction.
    # Runs every 2 minutes for each PAUSED session — when paused-for duration
    # approaches the user's historical p75 for the (category, time_of_day)
    # cell, fires "you usually resume by now" banner. Cold-start fallback at
    # 30min flat cap with synthetic mechanism. Per-session cooldown 5min.
    scheduler.add_job(
        run_resume_prediction,
        trigger=IntervalTrigger(minutes=2),
        id="resume_prediction",
        name="W2 magic — fire resume banner when paused-for >= historical p75",
        replace_existing=True,
        max_instances=1,
    )

    # Moodle LMS .ics sync — every 6h per connected user. Iterates
    # users with non-NULL moodle_ics_url, fetches the .ics, upserts
    # imported events as Deadline rows with external_source='moodle_ics'.
    # See services/moodle_ics_sync.py and workers/jobs/moodle_ics_sync.py
    # for the implementation. Cadence matches Moodle's "several hours"
    # propagation window from the docs. (alembic 041, 2026-04-29.)
    scheduler.add_job(
        run_moodle_ics_sync,
        trigger=IntervalTrigger(hours=6),
        id="moodle_ics_sync",
        name="Moodle LMS — pull .ics deadlines per connected user",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.start()
    logger.info("APScheduler started")


def shutdown_scheduler():
    """Shutdown scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown()
    logger.info("APScheduler shutdown")
