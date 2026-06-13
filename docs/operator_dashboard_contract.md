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

Research framing:

```text
Measurement Integrity Before Agency Claims
```

The dashboard may show whether Lyra has enough clean, fresh, provenance-aware
evidence to reason responsibly. It must not turn operational diagnostics into
claims about a user's focus, motivation, discipline, avoidance, recovery
quality, agency, or productivity.

## Allowed Use

- Cohort readiness: red/yellow/green expansion status.
- Product-loop funnel health.
- Explicit-session activity and retention proxies.
- Measurement integrity and state invariant diagnostics.
- Notification lifecycle diagnostics.
- Provider provenance and sync health.
- Privacy-boundary checks.
- Read-only operator recommendations.
- Google first names as operator-only identity labels in user rows, when the
  user's Google profile has supplied them. These labels support cohort
  debugging only; they are not behavioral evidence.

## Forbidden Use

- User productivity scores.
- Focus, motivation, discipline, avoidance, or identity claims.
- Fragmentation/risk scoring.
- Professor, employer, institutional, or admin reporting.
- Silent task/session/provider mutation.
- Automatic user nudges from dashboard output.
- Agency or improvement claims inferred directly from clean trace ratio,
  retention, completion, pause, notification, or provider metrics.
- Raw task title, raw email, provider token, or raw provider URL exposure by
  default.

## Identity Metadata

The user table may include `first_name` sourced from the user's Google profile.
This is allowed in `/operator` user rows so the operator can distinguish
trusted users without exposing full emails. The response must include source
metadata such as `name_source = google_profile` when available.

Do not derive first names from emails for analytics. If Google profile metadata
is not available yet, return `null` / `unknown`.

## Metric Semantics

Every section should include:

- `basis`: `direct`, `derived`, `proxy`, `mixed`, `contract`, or
  `not_instrumented`.
- `confidence`: `high`, `medium`, `low`, or `not_instrumented`.
- `readiness_impact`: `blocker`, `warning`, or `informational`.

Unavailable instrumentation must be explicit. Do not report fake zeroes for
login frequency, app opens, quick-capture usage, notification render, or
notification action until those events are persisted.

Every readiness metric should preserve the chain:

```text
event -> metric -> diagnostic meaning -> readiness impact
```

The dashboard stops there. It does not continue to:

```text
diagnostic meaning -> user agency claim
```

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
