---
authority: active-contract
may_authorize_code: true
runtime_owner: backend:/v1/operator/dashboard
---

# Operator Dashboard Contract

Status: active implementation contract for the read-only `/operator` surface.

## Purpose

The operator dashboard answers:

```text
Can Lyra invite more trusted users today?
If not, what must be fixed first?
```

It is a product-health and measurement-integrity console, not a user analytics
or productivity evaluation surface.

## Allowed Use

- Cohort readiness: red/yellow/green expansion status.
- Product-loop funnel health.
- Explicit-session activity and retention proxies.
- Measurement integrity and state invariant diagnostics.
- Notification lifecycle diagnostics.
- Provider provenance and sync health.
- Privacy-boundary checks.
- Read-only operator recommendations.

## Forbidden Use

- User productivity scores.
- Focus, motivation, discipline, avoidance, or identity claims.
- Fragmentation/risk scoring.
- Professor, employer, institutional, or admin reporting.
- Silent task/session/provider mutation.
- Automatic user nudges from dashboard output.
- Raw task title, raw email, provider token, or raw provider URL exposure by
  default.

## Metric Semantics

Every section should include:

- `basis`: `direct`, `derived`, `proxy`, `mixed`, `contract`, or
  `not_instrumented`.
- `confidence`: `high`, `medium`, `low`, or `not_instrumented`.
- `readiness_impact`: `blocker`, `warning`, or `informational`.

Unavailable instrumentation must be explicit. Do not report fake zeroes for
login frequency, app opens, quick-capture usage, notification render, or
notification action until those events are persisted.

## Meaningful Activity

Included:

- task created
- brain dump confirmed
- timer started
- timer stopped
- pressure map opened
- recovery action taken
- insight opened
- export requested

Excluded:

- login only
- page refresh
- settings view only
- background sync

## Readiness Interpretation

Red blocks cohort expansion.

Yellow means dogfood only.

Green means cautious trusted-user expansion is allowed.

`safe_to_invite_more_users` may be true only when readiness is green.

## Privacy Boundary

The default dashboard response must keep:

- `raw_task_titles_exposed = false`
- `raw_emails_exposed = false`
- `provider_tokens_exposed = false`
- `raw_provider_urls_exposed = false`
- `user_debug_mode_enabled = false`

Any future debug drilldown requires a separate explicit contract.
