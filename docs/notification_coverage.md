# Notification Coverage

> **Status:** current operator/system coverage as of 2026-05-16.

LyraOS has two notification paths with different trust boundaries:

- **Per-user queue:** authenticated in-app/user-facing delivery through
  `notifications:pending:{user_id}` and `/v1/notifications/pending`.
- **Operator channel:** shared Telegram bot for system state and
  operator-owned events only. Non-operator behavioral content must not be sent
  to this channel.

## Boundary Rules

1. User-owned behavioral events go to the per-user queue.
2. Operator Telegram can mirror operator-owned events.
3. System-health alerts may go to operator Telegram, but should avoid task
   titles, emails, tokens, iCal URLs, OAuth tokens, or raw payload bodies.
4. Repeated failures must use dedupe/cooldown through
   `app.services.operator_notifier.notify_operator`.
5. Missing Telegram credentials or Telegram delivery failure must never break a
   product mutation or research write.

## Current Coverage Matrix

| Subsystem | User queue | Operator Telegram | Cooldown | Notes |
| --- | --- | --- | --- | --- |
| Pre-task reminders | yes | operator-owned only | per task, 2h | Non-operator reminders stay in the authenticated queue. |
| Timer overflow | yes | operator-owned only | per session, 24h | Non-operator timer state is not mirrored to the shared bot. |
| Pause prediction | yes | operator-owned only | per firing, 10m | Fixes the cross-user leak risk. |
| Resume prediction | yes | operator-owned only | job-level firing caps | Existing `user.is_operator` gate remains required. |
| Scheduler health | no | yes | 30m | Job error, missed run, and max-instance events. |
| Per-user job exceptions | no | yes | 30m | Reports job/user id and exception class only. |
| Moodle iCal | no | operator-owned/system | 15m-6h | Errors, summaries, and unparseable-event drift. |
| Moodle Web Services | no | operator-owned/system | 15m-6h | Auth, decrypt, base-url, user-id, fetch failures. |
| Google Calendar | no | operator-owned only | 1h-24h | Revoked/failed operator calendar sync. |
| Notion retry | no | system/operator | 1h | Missing credentials or queue-stopping retry failure. |
| LLM enrichment | no | system | 30m | Aggregate failed/unavailable/pending counts only. |
| Stale/orphan recovery | no | operator-owned only | 30m | Recovery summaries; no user content. |
| Overdue/missed deadline sweep | no | operator-owned only | caller-specific | Existing operator-only summaries. |

## Explicit Non-Coverage

- Exposure/reconciliation bookkeeping should remain log/diagnostic-first unless
  failure affects user-facing state.
- Feedback has a separate operator feedback fanout because it intentionally
  includes user-submitted text and optional user email.
- Non-operator task titles, pause predictions, reminders, and timer events must
  not enter the shared operator Telegram channel.
