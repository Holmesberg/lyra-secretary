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
  `tmp/operator-readonly-stress-*` paths.

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

- core routes load on desktop and mobile;
- `/operator` loads through the operator account;
- route reads do not change task, deadline, session, pause, feedback,
  exposure, or notification counts;
- dashboard invariant snapshots do not drift before/after reads;
- no `[object Object]`, internal alert copy, obvious server error text, or
  non-Cloudflare console failures render.

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

## What The Loop Does Not Yet Prove

The current loop is broad, but not a replacement for every human dogfood path.
It does not yet fully exercise:

- every `NewTaskModal` branch: edit mode, deadline preview, duration nudge
  keep/use, terminal deadline rejection, conflict UI;
- calendar drag/resize/reschedule UI;
- pressure-map preview and recovery block commit from the UI;
- table audit/correction flows;
- notification render, dismiss, action, expiry, and exposure outcome paths;
- insights held/unlocked/latency states;
- long-lived sessions over hours/days;
- rapid-click race conditions.

When a wave touches one of those surfaces, add a targeted Playwright dogfood
script before treating the loop as sufficient.

Highest-priority targeted scripts to add next:

1. `NewTaskModal` duration nudge, deadline preview, binding, and conflict UI.
2. Brain dump modal partial failure, edit/retry, and duplicate commit.
3. Pressure-map preview/dismiss/commit through UI.
4. Timer UI pause/resume/refresh/stop/reflection path.
5. Notification render/dismiss/action/expiry lifecycle.
6. Insights held/unlocked/latency states.
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

- `NewTaskModal` duration nudge and deadline-preview UX;
- calendar drag/resize/reschedule;
- pressure-map preview/commit;
- notification lifecycle render/dismiss/action;
- table correction;
- insights held/unlocked latency.
