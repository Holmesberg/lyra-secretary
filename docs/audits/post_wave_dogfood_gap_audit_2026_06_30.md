---
authority: active-audit
may_authorize_code: false
runtime_owner: none
created: 2026-06-30
---

# Post-Wave Dogfood Gap Audit - 2026-06-30

Freeze remains active. This audit defines the reusable dogfood loop and records
the gaps found by the six-agent review before the next refactor wave.

Canonical reusable loop:

- Runbook: `docs/runbooks/post_wave_dogfood_loop.md`
- Wrapper: `scripts/run_post_wave_dogfood_loop.ps1`
- Product-loop browser dogfood: `scripts/browser_holmesberg_product_loop_dogfood.mjs`
- Product-loop wrapper: `scripts/run_holmesberg_product_loop_dogfood.ps1`

Latest proof:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_post_wave_dogfood_loop.ps1 -Topology public -Mode standard -IncludeProductLoop -WaveName full-documented-surface-chain-conflict-branch
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_post_wave_dogfood_loop.ps1 -Topology public -Mode standard -IncludeProductLoop -WaveName new-task-branch-coverage
node scripts\browser_holmesberg_product_loop_dogfood.mjs --topology public --frontend http://localhost:3010 --api https://api.lyraos.org --proxy-api --force-pressure-recovery --run-id pressure-map-local-20260701-9
```

Result:

- status: passed
- output:
  `tmp/post-wave-dogfood/20260701-043838-full-documented-surface-chain-conflict-branch-standard-public`
- latest output:
  `tmp/post-wave-dogfood/20260701-054334-new-task-branch-coverage-standard-public`
- latest targeted pressure-map output:
  `tmp/browser-product-loop/2026-07-01T03-58-49-682Z/result.json`
- operator cookie: `LYRA_COOKIE_ALINASSERSABRY`
- non-operator cookie: `LYRA_COOKIE_HOLMESBERG`
- mutable writes: Holmesberg synthetic task/deadline/timer/notification rows;
  operator stayed read-only
- operator read-only stress: passed
- Holmesberg product loop: passed
- final operator read-only stress:
  `tmp/operator-readonly-stress-2026-07-01T01-48-03-021Z`
- latest final operator read-only stress:
  `tmp/operator-readonly-stress-2026-07-01T02-54-16-423Z`
- latest pressure-map operator read-only stress:
  `tmp/operator-readonly-stress-2026-07-01T04-04-02-208Z`
- latest timer/exposure operator read-only stress:
  `tmp/operator-readonly-stress-2026-07-01T04-43-21-954Z`
- latest notification action/expiry browser proof:
  `tmp/browser-notification-lifecycle/2026-07-01T04-50-58-661Z/result.json`
- latest notification operator read-only stress:
  `tmp/operator-readonly-stress-2026-07-01T04-52-22-671Z`
- latest broad Holmesberg cleanup:
  `tmp/browser-product-loop/2026-07-01T04-05-36-403Z`
- dashboard status: red, explained by concrete invariant blockers.
- notification lifecycle after the timer/exposure pass:
  `exposure_without_render_count=5`, `duplicate_prompt_count=0`,
  `render_without_exposure_count=0`.
- remaining cohort blockers include `exposure_without_render_count=5` and
  `no_closed_sessions_last_14d`.
- new browser-covered branch: `NewTaskModal` duration nudge `Keep` outcome
  plus overlapping-task soft conflict `Create anyway`.
- new browser-covered branches: `NewTaskModal` edit mode, terminal-deadline
  API rejection, terminal deadline picker exclusion, custom category,
  no-deadline, and pick-another override.
- correction discovered by browser verify: queued worker notification decisions
  are counted separately as `queued_without_render_count` and no longer trip the
  actionable exposure-without-render blocker.
- correction discovered by browser verify: deadline-suggestion Playwright waits
  must use real visibility waits, not immediate `isVisible()` checks; synthetic
  deadline fixtures must avoid shared ambiguous tokens because the production
  heuristic correctly suppresses multi-competitive candidates.
- pressure-map recovery commit is now browser-covered through a local
  fixed-frontend/public-backend pass. The public backend still reports real
  recovery options as gated by read-only pressure safe mode, so the browser
  verifier uses an explicit `--force-pressure-recovery` fixture only to exercise
  the UI commit seam. This is not proof that production recovery options are
  enabled.
- timer refresh/navigation while paused is now browser-covered through
  `tmp/browser-product-loop/2026-07-01T04-29-55-097Z/result.json`.
- correction discovered by browser verify: duration-nudge lookup decisions can
  be delivered by the backend and then discarded by the frontend before render.
  The fix adds owner-scoped suppression for existing delivered decisions and
  explicit render acknowledgement on visible Use/Keep interactions. Public API
  deployment is still required before this can clear the live
  `task_creation_nudge_lookup` missing-render debt.
- notification action and expiry lifecycle branches are now covered by a
  targeted Holmesberg browser pass plus backend fixture tests. The targeted
  pass records `acted` via the toast details link and `expired` via auto-dismiss
  without leaving synthetic pending notifications.

## Council Synthesis

All six agents converged on the same shape:

- The current automated loop is strong for route health, topology, auth
  boundaries, API invariants, operator read-only checks, and screenshot smoke.
- It is not yet a full product dogfood loop because many user journeys are
  still API-driven or screenshot-only.
- The reusable gate must separate:
  - contract/runtime proof;
  - mutable non-operator smoke;
  - product-loop UI journeys for touched surfaces;
  - gated checks that need provider credentials or disposable delete accounts.
- Operator account checks must remain cockpit-only/read-only. Holmesberg is
  the only approved mutable chaos account.
- Product routes such as `/pulse`, `/today`, `/insights`, and `/settings` can
  legitimately emit user-facing exposure/render/ack telemetry when visited.
  They belong in the Holmesberg product loop, not the operator read-only
  invariant.

## Documented Behavior vs Current Verification

| Surface | Documented / Expected Behavior | Current Verification | Gap |
|---|---|---|---|
| Pulse hub | Main hub for quick capture, re-entry, deadlines, timers, pressure map, recovery, integrations. | Screenshots and API smoke. | Full click-through product loop from Pulse is not automated. |
| Brain dump modal | Parse, edit, bind to existing deadlines, handle partial failures, retry, and commit idempotently. | Product-loop browser parse/write-free/commit path, editable rows, mixed success/failure review, edit failed item without retyping, retry, existing-deadline binding, and double-submit guard. | First-run onboarding brain-dump still needs targeted browser coverage. |
| New task modal | Create/edit task, duration nudge, deadline preview/binding, conflict handling, custom category. | Product-loop browser create + deadline binding, duration nudge Use/Keep paths, soft-conflict Create anyway path, edit mode, terminal deadline rejection/filtering, custom category, no-bind, pick-another, and API creation-nudge/exposure ack. | Nudge absent/error states and rapid double-submit remain targeted. |
| Pressure map | Diagnostic pressure map with horizon switching, preview, dismiss, edit, commit. | Product-loop browser seeded deadline visibility, preview, dismiss-no-mutation, editable recovery-block preview, double-lock guard, commit, deadline binding, planning-footprint provenance, and Calendar visibility. | Real backend recovery option emission remains gated by read-only pressure safe mode. |
| Timer UI | Start, pause with reason, resume after refresh/navigation, update completion/scope, stop cleanly. | Product-loop browser start/pause/refresh/navigation/resume/completion/scope/stop with exported pause event. | Long-lived stale sessions over hours/days still missing. |
| Today | Execute tasks, handle deadlines, date navigation, pause confirmations, retroactive edits. | Screenshots and API-created data. | Row interactions and date navigation need browser coverage. |
| Calendar | Show old/new planned tasks, deadlines, external events, drag/resize planned tasks only. | Screenshots. | Drag/resize/reschedule and dense overlap cases need browser coverage. |
| Table | Filters, sorting, CSV export, voided visibility, executed-row correction. | Screenshots. | Correction/filter/export browser paths missing. |
| Insights | Locked, held, unlocked, suppressed, error, and evidence states should explain themselves without contradictions. | Screenshots only. | Need forced-state or fixture browser coverage for held/unlocked/latency. |
| Notifications | Queue/reserve/render/dismiss/action/expire lifecycle separated from exposure and operator alerts. | Product-loop enqueue/web-pending/render-if-visible/dismiss ack, targeted browser action/expiry pass, backend tests, and operator counters. | Linked-exposure notification cases still missing. |
| Settings/export/delete | Export scoped data; delete stages; retention options; no credential leaks. | Product-loop export registry/secret-marker scan, API smoke, and backend tests. | Browser export/download/delete-stage walk-through needs a disposable delete account. |
| Operator cockpit | Operator-only, read-only, content-minimized, invariant-derived blockers. | Strong cockpit-only browser/API coverage. | Refresh-click/partial-degraded sections should be added later. |

## Reusable Loop Levels

`quick`:

- Use for docs/script-only changes and small non-runtime edits.
- Read-only.
- Checks cookies, git whitespace, topology, multi-account smoke, and operator
  read-only stress.

`standard`:

- Use for most post-wave checks.
- Read-only by default.
- Runs S1C stack with backend full suite skipped.
- Add `-IncludeMutable` only when product-loop runtime paths must be exercised.

`full`:

- Use before merge/release and for backend authority changes.
- Includes full backend pytest suite.
- Add `-IncludeMutable` for non-operator product-loop mutation proof.

`chaos`:

- Use after high-risk timer/cache/auth/scoping/provider/exposure work or after
  suspicious dogfood reports.
- With `-IncludeMutable`, repeats Holmesberg mutable smoke and operator
  read-only stress.

## Pass / Fail Policy

The loop fails on:

- command/test/build failure;
- cookie resolution failure;
- topology mismatch;
- non-operator operator-route access;
- operator read mutating product/runtime state;
- synthetic cleanup failure;
- static authority failure;
- unexplained cockpit counter regression.

The loop does not automatically fail on `/operator` yellow/red during freeze
closure. It fails when yellow/red is unexplained, stale-label driven, or
contradicts active invariants.

## Important Privacy And Measurement Notes

- Operator account must never create/edit/delete/void tasks, deadlines, timers,
  brain dumps, providers, notifications, or account state.
- Operator read-only stress must not sweep ordinary product routes as operator.
  Ordinary product routes can create legitimate exposure telemetry for the
  authenticated user; verify those routes through Holmesberg.
- Holmesberg is the mutable chaos account.
- Export calls may create governance/audit rows. Do not treat governance audit
  row counts as product-state read-only invariants.
- Notification web pending/reserve endpoints are not read-only. Use them only
  in explicit notification lifecycle tests.
- Deadline preview may create exposure/output-surface records when it renders a
  user-facing suggestion. Treat duration-nudge and deadline-preview changes as
  exposure-sensitive paths.

## Next Automation Targets

Added product-loop browser dogfood in this pass:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_holmesberg_product_loop_dogfood.ps1 -Topology public
```

It is also available through the reusable wrapper:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_post_wave_dogfood_loop.ps1 -Topology public -Mode full -IncludeProductLoop -WaveName "wave-name"
```

Remaining targeted Playwright scripts in priority order:

1. Timer refresh/navigation while paused and long-lived-session correction.
2. Linked-exposure notification lifecycle cases.
3. Forced insights held/unlocked/error/latency states.
4. Calendar drag/resize/reschedule and table correction/export.
5. First-run onboarding brain-dump lock-in/skip/empty-validation coverage.
6. Real pressure-map recovery options after pressure safe mode is lifted.

## Open Questions For Future Decision

No blocker is present for the reusable loop itself. Future decisions:

- Should `/operator` yellow/red ever fail post-wave automatically after freeze
  closure? Default after freeze should be yes for release gates.
- Should legacy direct mutation paths become hard-fail static violations now or
  remain report-only until R4 extraction?
- Should consent/privacy copy include an explicit cookie/localStorage inventory?

Until those are decided, use the conservative default: report gaps, fail on
regressions, and do not mutate operator state.
