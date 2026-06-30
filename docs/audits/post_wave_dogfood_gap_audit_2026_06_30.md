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

Latest proof:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_post_wave_dogfood_loop.ps1 -Topology public -Mode quick -WaveName reusable-loop-v2-smoke
```

Result:

- status: passed
- output: `tmp/post-wave-dogfood/20260630-213059-reusable-loop-v2-smoke-quick-public`
- operator cookie: `LYRA_COOKIE_ALINASSERSABRY`
- non-operator cookie: `LYRA_COOKIE_HOLMESBERG`
- mutable writes: none
- operator read-only stress: passed
- dashboard status: yellow, explained by known freeze-closure measurement
  blockers, not by exposure/notification/state regressions.

## Council Synthesis

All six agents converged on the same shape:

- The current automated loop is strong for route health, topology, auth
  boundaries, API invariants, operator read-only checks, and screenshot smoke.
- It is not yet a full product dogfood loop because many user journeys are
  still API-driven or screenshot-only.
- The reusable gate must separate:
  - contract/runtime proof;
  - mutable non-operator smoke;
  - targeted UI journeys for touched surfaces.
- Operator account checks must remain read-only. Holmesberg is the only
  approved mutable chaos account.

## Documented Behavior vs Current Verification

| Surface | Documented / Expected Behavior | Current Verification | Gap |
|---|---|---|---|
| Pulse hub | Main hub for quick capture, re-entry, deadlines, timers, pressure map, recovery, integrations. | Screenshots and API smoke. | Full click-through product loop from Pulse is not automated. |
| Brain dump modal | Parse, edit, bind to existing deadlines, handle partial failures, retry, and commit idempotently. | Parse/commit API smoke and backend tests. | Modal edit/binding/partial-failure/double-submit paths need Playwright. |
| New task modal | Create/edit task, duration nudge, deadline preview/binding, conflict handling, custom category. | Mostly backend/API coverage. | No senior-grade modal browser path yet. |
| Pressure map | Diagnostic pressure map with horizon switching, preview, dismiss, edit, commit. | API shape and route screenshots. | Preview/dismiss/commit UI path is missing. |
| Timer UI | Start, pause with reason, resume after refresh/navigation, update completion/scope, stop cleanly. | API smoke plus route screenshots. | UI-driven pause/resume/stop/reflection path is missing. |
| Today | Execute tasks, handle deadlines, date navigation, pause confirmations, retroactive edits. | Screenshots and API-created data. | Row interactions and date navigation need browser coverage. |
| Calendar | Show old/new planned tasks, deadlines, external events, drag/resize planned tasks only. | Screenshots. | Drag/resize/reschedule and dense overlap cases need browser coverage. |
| Table | Filters, sorting, CSV export, voided visibility, executed-row correction. | Screenshots. | Correction/filter/export browser paths missing. |
| Insights | Locked, held, unlocked, suppressed, error, and evidence states should explain themselves without contradictions. | Screenshots only. | Need forced-state or fixture browser coverage for held/unlocked/latency. |
| Notifications | Queue/reserve/render/dismiss/action/expire lifecycle separated from exposure and operator alerts. | Backend tests and operator counters. | Browser render/dismiss/action/expiry path missing. |
| Settings/export/delete | Export scoped data; delete stages; retention options; no credential leaks. | API smoke and backend tests. | Browser export/download/delete-stage walk-through missing. |
| Operator cockpit | Operator-only, read-only, content-minimized, invariant-derived blockers. | Strong browser/API coverage. | Refresh-click/mobile/partial-degraded sections should be added later. |

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
- Holmesberg is the mutable chaos account.
- Export calls may create governance/audit rows. Do not treat governance audit
  row counts as product-state read-only invariants.
- Notification web pending/reserve endpoints are not read-only. Use them only
  in explicit notification lifecycle tests.
- Deadline preview may create exposure/output-surface records when it renders a
  user-facing suggestion. Treat duration-nudge and deadline-preview changes as
  exposure-sensitive paths.

## Next Automation Targets

Add targeted Playwright scripts in this order:

1. Brain dump modal edit/binding/partial-failure/retry/double-submit.
2. New task modal duration nudge, deadline preview, binding, and conflict UI.
3. Pressure-map horizon switch, preview, dismiss-no-mutation, commit.
4. Timer UI start, pause, refresh, resume, update completion, stop.
5. Notification render, dismiss, action, expiry.
6. Insights held/unlocked/error/latency states.
7. Calendar drag/resize/reschedule and table correction/export.

## Open Questions For Future Decision

No blocker is present for the reusable loop itself. Future decisions:

- Should `/operator` yellow/red ever fail post-wave automatically after freeze
  closure? Default after freeze should be yes for release gates.
- Should legacy direct mutation paths become hard-fail static violations now or
  remain report-only until R4 extraction?
- Should consent/privacy copy include an explicit cookie/localStorage inventory?

Until those are decided, use the conservative default: report gaps, fail on
regressions, and do not mutate operator state.
