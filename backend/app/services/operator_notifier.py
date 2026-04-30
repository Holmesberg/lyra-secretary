"""Operator-facing notification fan-out (2026-04-30).

Centralized wrapper around `telegram_notifier.send_telegram_message_sync`
that:
  - Tags every message with a `source` label so the operator can read
    the Telegram chat as a structured log instead of unattributed pings.
  - Lets the operator change channels (e.g., add Slack, email, Discord)
    by editing this one function instead of every call site.
  - Severity prefix as a leading emoji so the operator can scan their
    Telegram inbox at a glance.

Why a wrapper instead of calling telegram_notifier directly:
  Operator decision 2026-04-30 — "make all notifications, toasts,
  nudges, ALL go through my telegram openclaw bot." Centralizing
  routing here means future channel changes are one line.

Selective coverage policy (operator-tunable):
  - "info"  — routine state changes worth knowing about (Moodle sync
              completed, brain dump landed, calibration nudge fired)
  - "warn"  — recoverable issues (task auto-skipped overdue, deadline
              just transitioned to missed, stale session recovered)
  - "error" — failures the operator should investigate (NIM down,
              Moodle 4xx, Notion sync exhausted retries)
  - "alert" — load-bearing user-facing events (timer overflow, pause
              prediction fired, scheduled reminder due)

Background jobs that fire EVERY FEW SECONDS (llm_enrichment) or are
pure research-side bookkeeping (reconcile_responses, reconcile_
deadline_outcomes) deliberately do NOT call notify_operator — Telegram
spam-blocking would tank the channel. Coverage list documented in
docs/notification_coverage.md (TODO when audit settles).
"""
from __future__ import annotations

import logging
from typing import Literal

from app.services.telegram_notifier import send_telegram_message_sync

logger = logging.getLogger(__name__)

Severity = Literal["info", "warn", "error", "alert"]

_PREFIX = {
    "info": "ℹ️",
    "warn": "⚠️",
    "error": "🛑",
    "alert": "🔔",
}


def notify_operator(
    message: str,
    *,
    source: str = "system",
    severity: Severity = "info",
) -> bool:
    """Send a structured notification to the operator's Telegram.

    Args:
      message: Body text. Markdown OK (telegram_notifier uses parse_mode=Markdown).
      source: Short tag (e.g., "scheduler.overdue", "frontend.toast",
              "moodle.sync"). Appears between brackets after the
              severity emoji.
      severity: One of info/warn/error/alert. Drives the leading emoji.

    Returns: True if telegram delivery succeeded, False otherwise.
    Failures log + return False — they never raise (callers shouldn't
    have to wrap each notification in try/except).
    """
    prefix = _PREFIX.get(severity, _PREFIX["info"])
    formatted = f"{prefix} `[{source}]` {message}"
    try:
        ok = send_telegram_message_sync(formatted)
        if not ok:
            logger.debug(
                "operator_notifier: telegram send returned False (likely "
                "TELEGRAM_BOT_TOKEN/chat_id absent or 5xx). source=%s",
                source,
            )
        return ok
    except Exception as e:  # noqa: BLE001 — non-fatal observation channel
        logger.warning(
            "operator_notifier: unexpected error sending telegram: %s "
            "(source=%s)",
            e,
            source,
        )
        return False
