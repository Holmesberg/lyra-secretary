# Per-User Bootstrap OperationalError

**Date:** 2026-05-17.
**Subsystem:** `scheduler.per-user / database bootstrap`.
**Severity:** error when repeated.
**Status:** mitigated in code.

## Alert

```text
Per-user worker bootstrap failed while loading user ids with OperationalError.
Job skipped this tick; check backend logs.
```

## Classification

This is a Lyra platform reliability alert, not a provider-auth degradation.
No per-user mutation runs when bootstrap fails, so data integrity risk is low
for the skipped tick, but repeated failures mean scheduled work is not running.

Required alert context:

- affected provider/subsystem: `scheduler.per-user / database bootstrap`
- affected user scope: unknown user count
- retry behavior: retry, dispose DB pool, then back off before another
  bootstrap attempt
- user action needed: no student action
- data integrity risk: no mutation attempted before bootstrap completes

## Observed Root Cause

Backend logs showed Supabase pooler connectivity failures:

```text
connection refused
SSL SYSCALL error: EOF detected
```

The application already used `pool_pre_ping`; this was not only stale idle
connections. During pooler trouble, every per-user scheduler job could attempt
the shared user-id bootstrap and amplify the outage.

## Mitigation

- Add a short PostgreSQL connect timeout for runtime DB connections.
- Add a short DB-bootstrap circuit breaker in `_per_user`.
- Make `llm_enrichment` treat database bootstrap failure as skipped auxiliary
  work instead of raising an APScheduler job error.
- Keep Telegram delivery on a short timeout so the observation channel does not
  pin scheduler threads during network trouble.
- Keep the first contextual operator alert.
- Skip subsequent per-user scheduler ticks during the backoff window without
  weakening authentication, user scoping, or data writes.
- Narrow `pause_prediction` bootstrap to users with active `EXECUTING` tasks
  so its one-minute cadence scales with active sessions rather than registered
  accounts.
- Narrow `reminders` bootstrap to users with PLANNED, non-voided tasks in the
  reminder window. If the candidate scan fails, no reminder notification,
  output-surface row, or per-user mutation is attempted on that tick.
- Return `503 authentication database temporarily unavailable` when bearer
  auth cannot resolve a user because the Lyra database is unavailable. This
  keeps auth fail-closed without mislabeling a platform outage as an expired
  token.
- If a per-user job gets past bootstrap but hits `OperationalError` while
  loading/running one user's scoped iteration, roll back the session, dispose
  the DB pool, open DB backoff, stop remaining fanout for that job, and alert
  with the caller's job name instead of `_run_for_one_user`.
- Suppress `httpx` INFO request logs so Telegram bot-token URLs cannot leak
  through library-level request logging.

## Invariants

- Database outage must degrade scheduled work, not weaken user scoping.
- Database outage during auth must fail closed without accepting fallback
  identity.
- No per-user mutation may run unless user bootstrap and request scope succeed.
- A DB outage must not fan out one alert per remaining user.
- Backoff is operational load-shedding, not data loss.
