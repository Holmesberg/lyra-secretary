# v2 backlog

Deferred deliberately. Not blocking alpha or the research-layer goal of
Lyra Secretary v0.1. Revisit after alpha dogfood data comes in.

## Features

- **LLM-powered task creation** — natural-language → structured task via an
  LLM call. Optional, paid, and solves a problem alpha users don't have
  (they can type titles into the modal). Keeps the API surface simple in v1.
- **Email notifications** — reminders, daily summaries. Requires SMTP/SES
  infra + user-facing preferences. Not needed while alpha users are in a
  Telegram/OpenClaw loop.
- **Browser push notifications** — Web Push + VAPID. Device-permission UX
  is heavy; polling at 10s is good enough for Phase 3/4.
- **Per-user category visibility flags** — hide `prayer`,
  `self_reflection`, etc. per user without removing them from the frozen
  taxonomy. Needed once we have a non-Cairo, non-reflective user. Not now.
- **Mobile app** — native or PWA wrapper. Static export already works on
  mobile web; a proper app is a distribution question, not a capability one.
- **Team / multi-user collaboration** — shared tasks, visibility scopes.
  Out of scope for a single-user adaptive scheduler.
- **Prayer time API integration** — auto-block prayer windows using an
  aladhan.com or similar API keyed to user location. Currently the operator
  manually creates prayer-category tasks. An API integration would inject
  them automatically at accurate times, reducing scheduling friction for
  users who observe fixed daily prayers. Requires: location preference per
  user, a lightweight polling job, and conflict-resolution logic for
  auto-created vs manual tasks.
- **Smart reminders (bias-aware)** — instead of flat "task starts in 5 min"
  reminders, adjust lead time based on the user's historical
  `initiation_delay_minutes` for that (category, time_of_day) cell. A
  chronic late-starter on afternoon deep-work gets a 15-min reminder; a
  disciplined morning executor gets 3-min. Requires: sufficient session
  history per cell (n ≥ 10), a reminder preferences table, and integration
  with the notification transport (Telegram/push/email).
- **Mid-funnel retention nudges** — detect users who created an account and
  completed onboarding but have < 3 executed sessions in their first 7
  days. Trigger a lightweight check-in ("How's scheduling going? Here's
  what your first week's data shows...") via the notification channel.
  Goal: reduce Day-7 churn before the system has enough data to
  demonstrate value. Requires: a retention-check worker job and a nudge
  template system.
