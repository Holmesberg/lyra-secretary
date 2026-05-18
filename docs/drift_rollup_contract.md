# Drift Rollup Contract

**Status:** Scalability contract.
**Created:** 2026-05-18.
**Purpose:** Prevent execution-drift metrics from becoming slow, stale, or
research-contaminated as alpha usage grows.
**Governance:** Subordinate to `MANIFESTO.md`, `docs/cortex_contract_v0.md`,
and `docs/cortex_product_research_contract_v0.md`.

This document authorizes no new metric and no new adaptive claim. It defines
when drift computations may stay read-time projections and when they must move
to asynchronous, user-scoped rollups.

---

## 1. Current Rule

Drift is currently safest as a read-time projection over clean source rows.
That keeps the measurement logic inspectable while the cohort is small.

Do not materialize drift rollups until runtime evidence shows read-time
computation is a bottleneck.

Runtime evidence can include:

- sustained endpoint p95 latency above the trusted-alpha target,
- repeated slow-query traces on analytics/Pulse/insights endpoints,
- query plans showing large scans over task/session history,
- or browser smoke showing user-visible delay caused by drift aggregation.

## 2. Materialization Trigger

When the trigger fires, move from read-time calculation to async rollup only if
the rollup preserves:

- `user_id`,
- clean-data profile,
- exposure policy/horizon,
- source table versions or source row high-water marks,
- metric version,
- computation timestamp,
- invalidation source,
- and fallback behavior when the rollup is stale.

The frontend must never read a rollup whose source profile is unknown.

## 3. Rollup Shape

Future rollup rows should be keyed by:

```text
user_id
metric_name
clean_data_profile
window_start_utc
window_end_utc
metric_version
exposure_policy_version
```

Suggested values:

| Metric | Notes |
| --- | --- |
| `execution_multiplier` | Canonical Cortex ratio `executed_active_minutes / planned_active_minutes`. |
| `active_delta_minutes` | Canonical minute-space drift `executed - planned`. |
| `cascade_score` | Sequence-level skip propagation, never causal by default. |
| `unplanned_execution_rate` | Planning-layer usage variable, not productivity truth. |
| `scope_density_delta` | VT-22 candidate; future-gated until enough scope data exists. |

## 4. Redis Cache Rule

Redis may cache rollup reads for product latency, but it is not the source of
research truth.

Redis keys must be user-scoped and profile-scoped:

```text
rollup:{user_id}:{metric_name}:{clean_profile}:{window}:{metric_version}
```

Cached values must not include task titles, notes, raw provider identifiers,
OAuth payloads, Moodle URLs/tokens, or raw behavioral session bodies.

## 5. Scheduler Rule

Async rollup jobs are platform infrastructure. If database bootstrap fails, the
job must degrade using the scheduler degradation contract:

```text
JobResult.DEGRADED_HANDLED
```

No rollup job may:

- weaken user scoping,
- recompute using provider-bound rows when the clean profile excludes them,
- treat passive activity as planned execution,
- or emit a generic scheduler health page for already-handled DB degradation.

## 6. Research Boundary

Materialized rollups are derived values, not observed truth.

Rollup existence does not authorize:

- stronger user-facing claims,
- autonomous scheduling,
- provider-specific inference,
- learning from exposed behavior without exposure evaluation,
- or treating missingness as observed completion.

If rollup logic changes, the metric version must change and any publishable
analysis must report the version used.
