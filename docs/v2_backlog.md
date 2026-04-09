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
