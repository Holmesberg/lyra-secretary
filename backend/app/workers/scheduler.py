"""APScheduler setup for background jobs."""
from apscheduler.events import (
    EVENT_JOB_ERROR,
    EVENT_JOB_MAX_INSTANCES,
    EVENT_JOB_MISSED,
)
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging

from app.services.operator_notifier import format_alert_context, notify_operator
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
from app.workers.jobs.moodle_submissions_sync import run_moodle_submissions_sync

logger = logging.getLogger(__name__)

# APScheduler default misfire_grace_time is 30s — any job that should
# have fired more than 30s ago is silently dropped. Operator runs the
# backend on a laptop that sleeps overnight, which means hours of
# missed jobs (Moodle sync, Notion retry, etc.) get DROPPED on wake
# instead of replayed. Audit-flagged 2026-04-30. Setting a global
# 24h grace via job_defaults so misfired jobs catch up on wake. Each
# job is internally idempotent (Notion retry queue is queue-based,
# Moodle sync upserts by external_uid, sweep jobs query current state)
# so replaying once on wake is harmless.
scheduler = BackgroundScheduler(
    job_defaults={"misfire_grace_time": 60 * 60 * 24, "coalesce": True}
)
_SCHEDULER_LISTENERS_INSTALLED = False


def _notify_scheduler_event(event) -> None:
    """Mirror scheduler health events into the operator channel."""
    job_id = getattr(event, "job_id", "unknown")
    if event.code == EVENT_JOB_ERROR:
        exc = getattr(event, "exception", None)
        exc_name = type(exc).__name__ if exc is not None else "unknown"
        message = (
            f"APScheduler job `{job_id}` failed with `{exc_name}`. "
            "Check backend logs for the traceback.\n\n"
            + format_alert_context(
                affected=f"scheduler.health / {job_id}",
                scope=(
                    "unknown; inspect the failed job to determine affected "
                    "users"
                ),
                retry=(
                    "APScheduler will run the job again on its next trigger "
                    "unless the process is stopped."
                ),
                user_action=(
                    "No student action. Operator should triage immediately "
                    "if repeated."
                ),
                data_integrity=(
                    "Unknown from scheduler event alone; inspect job logs "
                    "and DB writes."
                ),
            )
        )
        severity = "error"
        dedupe = f"job-error:{job_id}:{exc_name}"
    elif event.code == EVENT_JOB_MISSED:
        message = (
            f"APScheduler job `{job_id}` missed its run window.\n\n"
            + format_alert_context(
                affected=f"scheduler.health / {job_id}",
                scope="unknown; job did not start at the scheduled time",
                retry="Coalesced scheduler config runs one catch-up tick when possible.",
                user_action="No student action.",
                data_integrity=(
                    "Low by default; idempotent jobs reconcile current state "
                    "on the next run."
                ),
            )
        )
        severity = "warn"
        dedupe = f"job-missed:{job_id}"
    elif event.code == EVENT_JOB_MAX_INSTANCES:
        message = (
            f"APScheduler job `{job_id}` hit max_instances; a prior run "
            "is still active.\n\n"
            + format_alert_context(
                affected=f"scheduler.health / {job_id}",
                scope=(
                    "unknown; a previous instance is still running for this "
                    "job"
                ),
                retry=(
                    "This tick is skipped; scheduler tries again on the next "
                    "interval."
                ),
                user_action="No student action.",
                data_integrity=(
                    "Low unless the same job remains stuck across repeated "
                    "intervals."
                ),
            )
        )
        severity = "warn"
        dedupe = f"job-max-instances:{job_id}"
    else:
        return

    notify_operator(
        message,
        source="scheduler.health",
        severity=severity,
        dedupe_key=dedupe,
        cooldown_seconds=30 * 60,
    )


def _install_scheduler_listeners() -> None:
    global _SCHEDULER_LISTENERS_INSTALLED
    if _SCHEDULER_LISTENERS_INSTALLED:
        return
    scheduler.add_listener(
        _notify_scheduler_event,
        EVENT_JOB_ERROR | EVENT_JOB_MISSED | EVENT_JOB_MAX_INSTANCES,
    )
    _SCHEDULER_LISTENERS_INSTALLED = True


def start_scheduler():
    """Start background scheduler."""
    # Reminders (check every 1 minute). Candidate bootstrap loads only users
    # with due planned tasks; DB bootstrap failure skips the tick before any
    # reminder mutation is attempted.
    scheduler.add_job(
        check_upcoming_tasks,
        trigger=IntervalTrigger(minutes=1),
        id="reminders",
        name="Check upcoming task reminders",
        replace_existing=True,
        max_instances=1,
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

    # VT-17 pause prediction (every 1 minute). Lead window is 2-3 min, so
    # check every minute to catch the boundary. The job bootstraps only users
    # with an EXECUTING task so runtime scales with active sessions rather than
    # total registered accounts. In-job FIRING_COOLDOWN_MINUTES prevents
    # re-fires for the same user.
    scheduler.add_job(
        run_pause_prediction,
        trigger=IntervalTrigger(minutes=1),
        id="pause_prediction",
        name="VT-17 pause prediction — fire + log + queue notification",
        replace_existing=True,
        max_instances=1,
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
    # llm_parse_status='pending' and calls the configured LLM for semantic
    # enrichment (priority, deadline candidates, sub-items). This is
    # auxiliary: run every 60s, claim one task per tick, and keep
    # max_instances=1 so provider slowness degrades enrichment rather than
    # weakening scheduler reliability.
    scheduler.add_job(
        run_llm_enrichment,
        trigger=IntervalTrigger(seconds=60),
        id="llm_enrichment",
        name="Magic — LLM async parser; semantic deadline + priority + sub-items",
        replace_existing=True,
        max_instances=1,
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

    # Moodle Web Services submission detection (alembic 043, 2026-05-01).
    # For each user with moodle_ws_token set, queries
    # mod_assign_get_submission_status for matched assignments and
    # records provider completion candidates when Moodle confirms.
    # Preserves the provider-truth boundary: user confirmation owns
    # canonical deadline completion. 6h cadence matches the iCal sync so the
    # operator-Telegram thread carries both updates together.
    scheduler.add_job(
        run_moodle_submissions_sync,
        trigger=IntervalTrigger(hours=6),
        id="moodle_submissions_sync",
        name="Moodle LMS - record submission evidence",
        replace_existing=True,
        max_instances=1,
    )

    _install_scheduler_listeners()
    scheduler.start()
    logger.info("APScheduler started")
    notify_operator(
        "APScheduler started with Lyra background jobs loaded.",
        source="scheduler.health",
        severity="info",
        dedupe_key="scheduler-started",
        cooldown_seconds=30 * 60,
    )


def shutdown_scheduler():
    """Shutdown scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown()
    logger.info("APScheduler shutdown")
    notify_operator(
        "APScheduler shutdown.\n\n"
        + format_alert_context(
            affected="scheduler.health / scheduler process",
            scope="all background jobs on this backend process",
            retry="Jobs resume when the backend process starts the scheduler again.",
            user_action="No student action.",
            data_integrity=(
                "No direct data mutation from shutdown; scheduled work pauses "
                "until restart."
            ),
        ),
        source="scheduler.health",
        severity="warn",
        dedupe_key="scheduler-shutdown",
        cooldown_seconds=30 * 60,
    )
