# E0 Exposure Forensics - 2026-07-01

Freeze remains active. This audit resolves the live
`exposure_without_render_count=5` blocker without weakening the operator
invariant.

## Summary

Result: resolved.

The five blocking rows were all recent Holmesberg dogfood
`task_creation_nudge_lookup` decisions from `analytics.bias_factor.lookup`.
They had `decision_status=delivered`, no render row, no render acknowledgement,
no linked notification lifecycle row, no task binding, and no suppression row.

The rows were repaired through the canonical owner-scoped suppression endpoint:

`POST /v1/exposures/{exposure_id}/ack/suppress`

No render evidence was fabricated.

## Row-Level Classification

Private full row IDs are kept only under ignored `tmp/` artifacts and must not
be committed.

| exposure_ref | surface/template | trigger | status before | evidence | classification | repair action | remaining risk |
|---|---|---|---|---|---|---|---|
| `4e4ea94e8c09` | `task_creation_nudge_lookup` | `analytics.bias_factor.lookup` | `delivered` | Holmesberg user hash; July 1 dogfood window; no render/ack/notification/task; ledger already identified five live dogfood rows | dogfood synthetic delivered-without-render debt | suppression `dogfood_synthetic_cleanup` | none for cohort blocker |
| `98bdfb3a0d4c` | `task_creation_nudge_lookup` | `analytics.bias_factor.lookup` | `delivered` | same as above | dogfood synthetic delivered-without-render debt | suppression `dogfood_synthetic_cleanup` | none for cohort blocker |
| `f29923b4a295` | `task_creation_nudge_lookup` | `analytics.bias_factor.lookup` | `delivered` | same as above | dogfood synthetic delivered-without-render debt | suppression `dogfood_synthetic_cleanup` | none for cohort blocker |
| `1e650e167cb8` | `task_creation_nudge_lookup` | `analytics.bias_factor.lookup` | `delivered` | same as above | dogfood synthetic delivered-without-render debt | suppression `dogfood_synthetic_cleanup` | none for cohort blocker |
| `65ae90b72b87` | `task_creation_nudge_lookup` | `analytics.bias_factor.lookup` | `delivered` | same as above | dogfood synthetic delivered-without-render debt | suppression `dogfood_synthetic_cleanup` | none for cohort blocker |

## Snapshots

Before repair:

- private artifact: `tmp/e0-exposure-forensics/20260701-155800/PRIVATE_full_ids_do_not_commit.json`
- redacted artifact: `tmp/e0-exposure-forensics/20260701-155800/redacted_snapshot.json`
- actionable missing-render count: `5`
- template breakdown: `task_creation_nudge_lookup=5`
- trigger breakdown: `analytics.bias_factor.lookup=5`

After repair:

- redacted repair result:
  `tmp/e0-exposure-forensics/20260701-155800/repair_result_redacted.json`
- redacted after-snapshot:
  `tmp/e0-exposure-forensics/20260701-155800/after_snapshot_redacted.json`
- actionable missing-render count: `0`
- repaired rows: all five now `decision_status=suppressed`
- render rows added: `0`
- suppression reason: `dogfood_synthetic_cleanup`

## Operator Verification

Aggregate operator API after repair:

- `exposure_without_render_count=0`
- `suppressed_without_render_count=101`
- readiness status: `yellow`
- blockers: none
- remaining dynamic issues:
  - `no_closed_sessions_for_trace_ratio`
  - `notification_source_freshness_not_instrumented`
  - `invalid_recovery_actions_not_instrumented`
  - `product_loop_dropoff_detected`

Read-only browser stress passed:

`tmp/operator-readonly-stress-2026-07-01T16-01-59-981Z`

The operator dashboard/export counts, route counts, and dashboard invariant
snapshots did not change during `/operator` desktop/mobile browser reads.

## Decision

This was not a reason to weaken `exposure_without_render_count`. The invariant
worked: it found delivered decisions without terminal render or suppression
evidence. The correct repair was to classify the dogfood-created rows and add
suppression evidence through the canonical owner-scoped API.

## Follow-Up R3 Dogfood Row - 2026-07-01

Result: resolved.

During the R3 invalidation-helper verification loop, the Holmesberg product
loop created one additional `task_creation_nudge_lookup` decision from
`analytics.bias_factor.lookup` that never crossed the browser render boundary.
The row was from the Holmesberg dogfood account, had `decision_status=delivered`,
no task binding, no render row, no render acknowledgement, no notification
lifecycle row, and no suppression row.

Private full row IDs are kept only under ignored `tmp/` artifacts and must not
be committed.

| exposure_ref | surface/template | trigger | status before | evidence | classification | repair action | remaining risk |
|---|---|---|---|---|---|---|---|
| `705e58d539db` | `task_creation_nudge_lookup` | `analytics.bias_factor.lookup` | `delivered` | Holmesberg user hash; R3 product-loop window; no render/ack/notification/task/suppression; created by local-current dogfood verification | dogfood synthetic delivered-without-render debt | suppression `dogfood_synthetic_cleanup` through owner-scoped API | none for cohort blocker |

Before repair:

- private artifact:
  `tmp/e0-exposure-forensics/20260701172151-r3-invalidation-helper/PRIVATE_full_ids_do_not_commit.json`
- redacted before-snapshot:
  `tmp/e0-exposure-forensics/20260701172151-r3-invalidation-helper/redacted_before_snapshot.json`
- actionable missing-render candidates: `1`
- template breakdown: `task_creation_nudge_lookup=1`
- trigger breakdown: `analytics.bias_factor.lookup=1`

After repair:

- redacted repair result:
  `tmp/e0-exposure-forensics/20260701172151-r3-invalidation-helper/repair_result_redacted.json`
- redacted after-snapshot:
  `tmp/e0-exposure-forensics/20260701172151-r3-invalidation-helper/redacted_after_snapshot.json`
- actionable missing-render candidates: `0`
- repaired row now `decision_status=suppressed`
- render rows added: `0`
- suppression reason: `dogfood_synthetic_cleanup`

Follow-up verifier fix:

- The reusable Holmesberg product-loop runner now cleans newly-created
  synthetic `task_creation_nudge_lookup` decisions from the current run if they
  remain delivered with no render, render ack, suppression, task binding, or
  notification lifecycle evidence.
- The runner asserts cleanup with
  `cleanup leaves no unrendered synthetic creation-nudge exposures`.
- This is verifier cleanup, not a weaker operator invariant. The operator
  blocker remains critical for live rows.

Operator verification after repair:

- browser artifact:
  `tmp/operator-readonly-stress-r3-invalidation-helpers-operator-after-exposure-repair/result.json`
- `exposure_without_render_count=0`
- `implementation_green=true`
- no count diffs, route count diffs, or dashboard snapshot diffs during
  `/operator` reads.

## Remaining Work

R2 should now distinguish:

- `implementation_green`: cockpit logic is correct and false blockers are gone.
- `cohort_green`: enough real clean data exists and no readiness blockers remain.

The cockpit is no longer blocked by exposure lifecycle debt. It remains
cohort-yellow because clean closed-session evidence is insufficient and some
instrumentation signals are still not implemented.
