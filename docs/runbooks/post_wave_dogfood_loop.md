---
authority: active-runbook
may_authorize_code: true
runtime_owner: scripts/run_post_wave_dogfood_loop.ps1
---

# Post-Wave Dogfood Loop

Use this after every wave cycle and before any merge/release decision. The goal
is not to prove Lyra is perfect; the goal is to prove that the core loop,
authority boundaries, privacy boundaries, and operator cockpit did not regress.

This runbook is reusable by design. Prefer improving this loop over inventing a
new one-off verification ritual.

## Accounts

Default browser identities:

- `LYRA_COOKIE_ALINASSERSABRY`: operator account. Read-only verification only.
- `LYRA_COOKIE_HOLMESBERG`: mutable chaos account. Synthetic tasks, deadlines,
  timers, and brain dumps are allowed, then cleaned up.

Never use the operator account for mutable dogfood. Operator browser checks must
observe runtime state without creating, editing, rendering actions, dismissing
notifications, starting timers, or changing product/user state.

## Command

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_post_wave_dogfood_loop.ps1 -Topology public -Mode standard -WaveName "wave-name"
```

Add `-IncludeMutable` when the wave needs Holmesberg chaos dogfooding:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_post_wave_dogfood_loop.ps1 -Topology public -Mode full -IncludeMutable -WaveName "wave-name"
```

Add `-IncludeProductLoop` when the wave touches user-facing product surfaces or
the delta -> Cortex/analytics -> ClaimCompiler -> exposure chain:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_post_wave_dogfood_loop.ps1 -Topology public -Mode full -IncludeProductLoop -WaveName "wave-name"
```

Local topology is allowed only when the local stack is intentionally up:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_post_wave_dogfood_loop.ps1 -Topology local -Mode standard -WaveName "wave-name"
```

Outputs are written under:

```text
tmp/post-wave-dogfood/<timestamp>-<wave>-<mode>-<topology>/
```

The script records:

- transcript;
- summary JSON;
- nested browser outputs under the existing `tmp/browser-smoke` and
  `tmp/operator-readonly-stress-*` paths;
- product-loop browser outputs under `tmp/browser-product-loop` or the nested
  `holmesberg-product-loop` directory when `-IncludeProductLoop` is used.

## Modes

`quick`

- Cookie checks for operator and Holmesberg.
- `git diff --check`.
- topology verifier.
- multi-account browser smoke.
- operator read-only browser stress.
- No mutable Holmesberg writes.
- Use after tiny docs-only or script-only changes.

`standard`

- Cookie checks for operator and Holmesberg.
- S1C stack with backend full suite skipped.
- Frontend production build.
- multi-account smoke.
- operator read-only stress.
- Holmesberg mutable smoke only with `-IncludeMutable`.
- second operator read-only stress after mutable cleanup only with
  `-IncludeMutable`.
- Full Holmesberg product-loop dogfood plus a second operator read-only stress
  when `-IncludeProductLoop` is passed.
- Use after most frontend/refactor seams and small backend changes.

`full`

- Same as `standard`, but includes the full backend pytest suite.
- Use before merge, release, branch rollover, or any wave that touched backend
  authority, provider, timer, exposure, notification, export/delete, or
  operator readiness logic.

`chaos`

- Same as `full`; with `-IncludeMutable`, repeats Holmesberg mutable smoke and
  operator read-only stress.
- Use after high-risk refactors, cache/timer changes, auth/scoping changes, or
  when dogfooding found a suspicious runtime issue.

## What The Loop Must Prove

Authentication and scoping:

- operator cookie resolves as operator;
- Holmesberg resolves as non-operator;
- non-operator cannot access operator/admin/Jarvis routes;
- account export rows are scoped to the authenticated user.

Topology:

- public/local frontend and API origins are coherent;
- frontend build id/API build id topology check passes.

Mutable product loop on Holmesberg:

- deadline creation works;
- task creation and task-deadline binding work;
- only one active timer can run;
- timer start, pause, resume, completion update, and clean stop work;
- brain dump parse and commit work;
- synthetic artifacts are voided/deleted after the run.

Operator read-only invariant:

- `/operator` loads through the operator account on desktop and mobile;
- cockpit/dashboard reads do not change task, deadline, session, pause,
  feedback, exposure, notification, provider, or runtime counts;
- dashboard invariant snapshots do not drift before/after reads;
- no `[object Object]`, internal alert copy, obvious server error text, or
  non-Cloudflare console failures render.

Product routes are verified through Holmesberg, not through the operator
read-only stress. Product pages such as `/pulse` and `/insights` may correctly
create user-facing exposure/render/ack telemetry when they show output
surfaces. Mixing those routes into the operator read-only invariant hides the
thing the cockpit test is meant to prove.

Static/refactor integrity:

- mutation-capable surfaces have owners;
- refactor contracts do not show blocked violations;
- Alembic fresh DB smoke passes;
- frontend production build passes;
- backend suite passes in `full` and `chaos`.

## Product-Loop UI Add-On

The wrapper proves contracts, API health, route health, account boundaries, and
operator read-only invariants. It does not automatically prove the full user
journey through every modal.

`-IncludeProductLoop` runs
`scripts/browser_holmesberg_product_loop_dogfood.mjs`, which currently covers:

- non-operator route denial for `/operator`, `/admin`, and parked Jarvis;
- read-only route sweep for Pulse, Today, Calendar, Deadlines, Table, Insights,
  and Settings;
- deadline creation through the browser;
- task creation through the browser, including deadline binding;
- creation-nudge Use/Keep outcomes plus exposure render acknowledgement;
- overlapping planned-task soft conflict and explicit Create anyway branch;
- brain-dump parse as write-free and commit as explicit mutation;
- pressure-map preview and dismiss-no-mutation;
- timer start, pause, resume, completion/scope, stop, and delta projection;
- insights/ClaimCompiler-safe response shape and forbidden-claim scan;
- notification enqueue, web pending, toast/render path where available, and
  lifecycle acknowledgement;
- export registry-section and secret-marker scan;
- cleanup of synthetic Holmesberg tasks/deadlines;
- operator privacy scan after mutable dogfood.

For waves that touch Pulse, task creation, deadlines, timers, calendar,
pressure map, recovery, insights, notifications, provider display, table, or
settings, add at least one targeted browser journey to the wrapper proof.

Minimum product-loop journey:

1. On Holmesberg, create or import a deadline.
2. From `/pulse`, open quick capture and paste a messy multi-line dump.
3. Confirm at least one task/deadline binding or explicit no-bind choice.
4. Verify committed tasks/deadlines appear in Today/Deadlines.
5. Open pressure map and switch day/week/14-day views.
6. Preview a recovery/planning block, dismiss once, and verify no mutation.
7. Commit one block if the wave touched planning/recovery creation.
8. Start a task from Today, pause with a reason, refresh or navigate away,
   resume, update completion/scope, and stop cleanly.
9. Open Insights and verify either evidence appears or the held/locked state
   gives a concrete non-contradictory reason.
10. Re-run operator read-only stress and compare dashboard/export snapshots.

If a step is not automated yet, record it as manual browser verification in the
ledger with the account, route, and observed result.

## Documented Surface Coverage Matrix

Use this matrix as the post-wave expansion checklist. A row marked browser
covered must have a Holmesberg automated path. A row marked fixture-covered
must have backend/API tests or a seeded targeted script. A row marked gated must
stay out of unattended dogfood until the named account/credential/authority
exists.

| Surface / Flow | Required Proof | Current Status |
|---|---|---|
| Auth and scoping | Holmesberg is non-operator; operator is operator; non-operator cannot access `/operator`, `/admin`, or active Jarvis. | browser covered |
| Operator cockpit | `/operator` and `/v1/operator/dashboard` are read-only, content-minimized, invariant-derived. | browser covered |
| Pulse hub | Quick capture, re-entry visibility, focus card, pressure map, notifications render without raw internals. | partially browser covered |
| First-run onboarding | Consent/intro, parse, edit dump, lock-in, skip, empty validation. | targeted/gated |
| Brain dump | Parse is write-free; commit creates intended task/deadline/binding. | browser covered |
| Brain dump chaos | Edit parsed items, partial failure, retry, duplicate commit/idempotency, existing-deadline binding. | targeted |
| New task modal | Create task, bind deadline, duration nudge exposure, Use/Keep nudge outcomes, create-anyway soft conflict when present. | browser covered |
| New task branches | Edit mode, terminal deadline rejection, custom category, no-bind/pick-another, Dismiss nudge outcome. | targeted |
| Deadlines | Create, edit, complete/skip/reopen staging, void confirm/cancel, duplicate warning. | partially browser covered |
| Today execution | Task row start/stop, date nav, retroactive edit, overdue done, void/reschedule/drop. | partially browser covered |
| Timer/focus | Start, pause, resume, stop, completion/scope, pause event, delta. | browser covered |
| Timer chaos | Refresh/navigation while paused, long-lived stale session, one-active rejection, interruption/switch/open-thread recovery. | targeted |
| Pressure map | Exposure metadata, horizon API, preview, dismiss-no-mutation. | browser covered |
| Pressure-map planning | Horizon UI switches, edit preview, commit recovery block, created blocks appear in Today/Calendar. | targeted |
| Calendar | Day/week/month render; old/new tasks and deadlines visible. | partially browser covered |
| Calendar mutation | Drag/resize planned tasks, reject immutable/executed/deadline/provider rows, dense overlap. | targeted |
| Table | Route render; executed dogfood row/delta visible. | partially browser covered |
| Table audit/correction | Filters, sort, CSV download, voided visibility, executed-row correction. | targeted |
| Insights / ClaimCompiler | Locked/held/unlocked/suppressed states avoid causal/identity/diagnostic claims and show concrete reasons. | partially browser/API covered |
| Exposure lifecycle | Decision, render or suppression, browser ack, linked interaction outcome where applicable. | partially browser/API covered |
| Notifications | Queue, pending, render, dismiss, terminal lifecycle row. | browser/API covered |
| Notification branches | Action, expiry, duplicate/cooldown, linked exposure, OpenClaw mirror redaction. | targeted/gated |
| Settings/export | Export registry sections and no secret markers. | API covered |
| Settings/delete | Browser export download, staged delete, final hard-delete and Redis purge. | disposable-account gated |
| Providers/integrations | Credential redaction, provider provenance, connect/disconnect/failure/import idempotency. | credential gated |
| OpenClaw/operator relay | No accidental product-user exposure, no destructive drain before send, one delivery authority. | authority gated |

## What The Loop Does Not Yet Prove

The current loop is broad, but not a replacement for every human dogfood path.
It does not yet fully exercise:

- every `NewTaskModal` branch: edit mode, terminal deadline rejection,
  custom category, nudge dismiss, and all no-bind/pick-another branches;
- calendar drag/resize/reschedule UI;
- pressure-map recovery block commit from the UI;
- table audit/correction flows;
- notification action/expiry paths and linked-exposure notification cases;
- forced insights held/unlocked/latency states;
- long-lived sessions over hours/days;
- rapid-click race conditions.

When a wave touches one of those surfaces, add a targeted Playwright dogfood
script before treating the loop as sufficient.

Highest-priority targeted scripts to add next:

1. `NewTaskModal` edit mode, terminal deadline rejection, custom category,
   no-bind/pick-another, and nudge-dismiss outcome.
2. Brain dump modal partial failure, edit/retry, and duplicate commit.
3. Pressure-map recovery-block commit through UI.
4. Timer UI refresh/navigation during pause and long-lived session handling.
5. Notification action/expiry lifecycle and linked exposure outcomes.
6. Forced insights held/unlocked/latency states.
7. Calendar drag/resize/reschedule and table correction flows.

## Pass / Fail Rule

The loop fails on:

- command/test failure;
- topology mismatch;
- cookie resolution failure;
- operator route accessible to non-operator;
- operator read mutating product/user/runtime state;
- synthetic cleanup failure;
- critical browser route issues;
- authority/static scan failures;
- backend/frontend build/test failures for the selected mode.

The loop does not automatically fail just because `/operator` readiness is
yellow or red. During freeze closure, readiness may be yellow/red because known
invariants are still open. It fails if readiness regresses in a way the cockpit
cannot explain, if blockers become stale labels instead of concrete invariants,
or if critical counters violate active contracts.

## Ledger Requirement

Every wave or risky PR must record:

- command and mode run;
- output directory;
- changed authority;
- removed paths;
- parked paths;
- moved authority;
- tests added or named;
- rollback note;
- any gaps the loop did not cover.

Use `docs/registries/refactor_stabilization_ledger.md` for refactor waves.

## Standard Post-Wave Checklist

1. Commit or shelve unrelated work.
2. Run the dogfood loop in the right mode.
3. Inspect the summary JSON and the latest operator screenshots if the wave
   touched UI.
4. If mutable smoke ran, confirm cleanup succeeded.
5. Record proof in the ledger.
6. Push only after the loop passes or after the user explicitly accepts a known
   failing invariant.

## Next Coverage Targets

Add targeted scripts for:

- `NewTaskModal` edit/conflict/terminal-deadline UX;
- calendar drag/resize/reschedule;
- pressure-map commit;
- notification lifecycle action/expiry;
- table correction;
- insights held/unlocked latency.
