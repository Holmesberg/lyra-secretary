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

## API Shape

`GET /v1/operator/dashboard` returns one read-only cockpit payload. The
canonical top-level sections are:

```text
generated_at
data_freshness
metric_confidence
meaningful_activity_definition
cohort_readiness
cohort_segments
cohort
retention
activity_frequency
activation_quality
product_loop_funnel
measurement_integrity
state_invariants
notification_lifecycle
provider_integrity
reliability
privacy_boundary
bug_watchlist
dynamic_issues
users
operator_recommendations
derived_metrics
```

The response is content-minimized by default. It is not a drilldown API.

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

## Dynamic Issues

`dynamic_issues` are the primary readiness mechanism. They must derive from
live invariants and diagnostic rules, not from static bug labels. K01-K05 may
appear only as tags or watchlist statuses.

Critical blockers include:

- privacy-boundary violations;
- operator/internal web-copy leaks;
- duplicate notification prompts;
- exposure records without render evidence;
- duplicate open sessions;
- executing or paused tasks without coherent open sessions;
- executed tasks missing execution interval fields;
- open sessions for executed tasks;
- stale paused sessions without resolution;
- clean trace ratio below the red threshold;
- provider truth violations.

`exposure_without_render_count > 0` must block cohort expansion because
exposure-influenced metrics cannot be trusted without render linkage proof.
This count must include only render-required exposure decisions that lack both
render evidence and suppression evidence. Suppressed exposure decisions are
intentional non-renders and must be reported separately as
`suppressed_without_render_count` with informational impact.

Duplicate prompt issues must name the duplicate type. K02 tags apply only to
timer-overflow duplicates, not to reminder or other prompt duplicates.

Missing notification source freshness is at least a warning. It means
notification lifecycle counts are incomplete, not proven safe.

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

The cockpit must distinguish implementation correctness from cohort readiness:

- `implementation_green` means the cockpit is not blocked by known broken
  invariants, false blockers, privacy leaks, exposure/render debt, provider
  truth violations, or other cohort-blocking dynamic issues.
- `cohort_green` means there is enough real clean evidence to invite more
  trusted users.
- A cockpit may be `implementation_green=true` and `cohort_green=false`. That
  means the instrument appears correct, but the cohort still lacks enough clean
  real-world evidence or has non-blocking instrumentation warnings.
- Controlled evidence collection is allowed only when implementation is green
  and the only cohort gap is insufficient real data. It is not general cohort
  expansion and must not authorize marketing or strong user-facing claims.

## Measurement Integrity

`clean_trace_ratio` is defined as:

```text
clean eligible explicit stopwatch sessions /
all eligible explicit stopwatch sessions
```

The denominator excludes and separately reports:

- operator-user sessions;
- test/synthetic-user sessions;
- voided or deleted task sessions;
- deleted-retained sessions;
- provider-only rows;
- non-session tasks.

Every low ratio must be explainable through `dirty_reason_distribution`.
Unknown exposure, exposure contamination, missing timestamps, impossible
durations, auto-closed rows, stale-recovered rows, retroactive rows, corrected
rows, voided rows, and provider-only rows must not silently enter clean
baselines.

Notification lifecycle diagnostics must distinguish:

- actionable missing renders;
- intentionally suppressed non-renders;
- pending Redis duplicates;
- durable lifecycle duplicates;
- duplicate types and redacted stable identifiers.

## Read-Only Invariant

Reading `/operator` must not mutate:

- last activity;
- notification lifecycle;
- exposure state;
- user metrics;
- task, session, deadline, or provider state;
- Redis user runtime state.

Refreshing the dashboard may update `generated_at` and recompute derived
readiness. It must not participate in the product measurement system it
observes.

## Privacy Boundary

The default dashboard response must keep:

- `raw_task_titles_exposed = false`
- `raw_emails_exposed = false`
- `provider_tokens_exposed = false`
- `raw_provider_urls_exposed = false`
- `user_debug_mode_enabled = false`

Any future debug drilldown requires a separate explicit contract.

## Freeze Stop Line

The operator cockpit is a freeze-closure surface. It must be clear before any
new feature work starts. The dashboard does not authorize AI synthesis,
behavior-transition equations, cascade interventions, new insight types,
archetype/profile labels, passive tracking, new provider adapters, or adaptive
scheduling authority.
