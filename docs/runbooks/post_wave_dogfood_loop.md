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

## Proof Preflight

Run the canonical preflight before an expensive browser verifier. Do not
re-derive health paths, ports, account state, or export limits in ad hoc shell
commands.

Hosted read-only example:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\proof_preflight.ps1 `
  -Topology public -Account both -Intent readonly `
  -ExpectedFrontendBuildId <served-build-id>
```

Focused local-current mutable example, after the isolated runtime is already
running:

```powershell
$head = (git rev-parse HEAD).Trim()
powershell -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\start_local_current_proof_runtime.ps1 `
  -ExpectedBuildId $head -OutFile tmp\local-current-runtime\active.json

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\proof_preflight.ps1 `
  -Topology local-current -FrontendOrigin http://localhost:3018 `
  -ApiOrigin http://localhost:8001 -ProxyApi `
  -Account holmesberg -Intent mutable -ExpectedFrontendBuildId $head `
  -RuntimeManifest tmp\local-current-runtime\active.json `
  -FixtureAccountReady -TargetPath /pulse `
  -ReadySelector '[data-testid="pulse-quick-capture-input"]' `
  -SyntheticPrefix 'DOGFOOD W4 seam-name' -MaxPendingNotifications 0
```

The launcher requires `.venv311`, refuses occupied ports instead of killing or
reusing them, builds only `.next-local-current`, verifies exact frontend and
backend build IDs, and records process ownership in the runtime manifest.

For cold-start or account-state proof that must not depend on shared local
rows, start the same runtime with disposable data:

```powershell
$head = (git rev-parse HEAD).Trim()
powershell -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\start_local_current_proof_runtime.ps1 `
  -ExpectedBuildId $head -OutFile tmp\local-current-runtime\disposable.json `
  -DisposableData -DisposableRedisDatabase 15

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\proof_preflight.ps1 `
  -Topology local-current -FrontendOrigin http://localhost:3018 `
  -ApiOrigin http://localhost:8001 -Account holmesberg -Intent readonly `
  -ExpectedFrontendBuildId $head `
  -RuntimeManifest tmp\local-current-runtime\disposable.json
```

Disposable mode migrates a fresh SQLite database, requires an empty dedicated
Redis DB in the bounded `8..15` range, disables email/operator notification
delivery, and permits only the real Holmesberg cookie. The target account is
initially unprovisioned; its first authenticated read may create only its row
and operational audit data inside that disposable database. Account readiness
is therefore predictably cold-start rather than inherited from shared state.
Operator proof remains read-only against a non-disposable runtime.

After proof, tear down only those recorded processes and the bounded artifact:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\stop_local_current_proof_runtime.ps1 `
  -Manifest tmp\local-current-runtime\active.json -RemoveArtifact
```

For disposable mode, require data cleanup explicitly:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\stop_local_current_proof_runtime.ps1 `
  -Manifest tmp\local-current-runtime\disposable.json `
  -RemoveArtifact -RemoveDisposableData
```

Teardown validates the recorded run directory, exact checkout interpreter,
bounded SQLite filename, and dedicated Redis target before deletion/reset. It
does not erase a nonempty Redis DB at startup; unknown state fails closed.

The preflight blocks product API mutations. Outside disposable first-login
provisioning it is read-only. It checks the canonical
`/v1/health/topology` endpoint, artifact isolation, local port/process
ownership, exact build ID, real cookie/session validity, account role,
terms/onboarding state, optional selected date/week, target mount, export
duration/size, active timer, pending notification debt, and active rows for an
explicit `DOGFOOD` prefix. Browser API mutations are blocked.

If the readiness fixture is used, it is local-current and browser-response
only; it does not change the account. It may support focused product proof but
is not hosted-public evidence.

The backend test entrypoint is `scripts/run_backend_pytest.ps1`. It always
runs from `backend/` through `.venv311` and fails closed when that interpreter
is unavailable; do not reconstruct either choice in ad hoc commands.

For abandoned synthetic task/deadline rows, use the existing local-current
`-CleanupOnly` product-loop mode with the exact `DOGFOOD` prefix, then rerun
the preflight with that prefix. This terminalizes test rows through canonical
commands. It is not a user reset, onboarding reset, production repair, or
permission to suppress unrelated lifecycle evidence. Pending lifecycle debt,
an active timer, or a non-`DOGFOOD` prefix remains blocking.

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

Hosted-public mutable/product-loop dogfood is high-care and optional. Prefer
local-current mutable dogfood plus hosted-public read-only proof unless the
public mutable account, cleanup path, and rollback path are already proven
safe. Do not create public synthetic rows merely to make proof feel complete.

After pushing a seam or wave, add read-only CI/CD proof collection:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_post_wave_dogfood_loop.ps1 -Topology public -Mode quick -IncludeCiCdProof -WaveName "wave-name-ci-proof"
```

For a standalone CI/CD proof artifact without browser checks:

```powershell
$branch = (git branch --show-current).Trim()
$head = (git rev-parse HEAD).Trim()
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\collect_github_ci_cd_proof.ps1 -Branch $branch -HeadSha $head -Workflow CI -OutFile tmp\ci-cd-proof\latest.json
```

`-HeadSha` must receive the full commit SHA from `git rev-parse HEAD`, not the
seven-character display SHA. GitHub Actions reports full `headSha` values; a
short SHA will produce `no_matching_run_for_head` even when the selected run is
green. This footgun is tracked in issue #160.

When a wave touches Insights, ClaimCompiler payloads, or insight copy/gates,
add the forced-state browser fixture:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_post_wave_dogfood_loop.ps1 -Topology public -Mode standard -IncludeInsightsStates -WaveName "wave-name"
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
- `ci_cd_proof.json` when `-IncludeCiCdProof` is used.

`summary.json.evidence_manifest` is the top-level proof index. It must surface
the topology class, frontend/backend build IDs, frontend/API origins,
implementation/cohort readiness split, `exposure_without_render_count`, browser
issues/warnings, count diffs, cleanup proof status, gated paths, and CI/CD proof
location/status when collected.

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
- non-operator cannot access `/operator`, remaining operator-only `/admin/*`
  triage endpoints, or removed/parked JARVIS routes;
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

- non-operator route denial for `/operator`, remaining operator-only `/admin/*`
  triage endpoints, and removed/parked JARVIS routes;
- read-only route sweep for Pulse, Today, Calendar, Deadlines, Table, Insights,
  and Settings;
- deadline creation through the browser;
- task creation through the browser, including deadline binding;
- creation-nudge Use/Keep outcomes plus exposure render acknowledgement;
- overlapping planned-task soft conflict and explicit Create anyway branch;
- NewTaskModal edit mode, terminal-deadline API rejection, terminal deadline
  picker exclusion, custom category, no-deadline branch, and pick-another
  override branch;
- brain-dump parse as write-free, commit as explicit mutation, editable parsed
  items, partial-failure review, edit/retry without retyping, and
  double-submit duplicate prevention;
- pressure-map seeded deadline visibility, horizon API metadata, preview,
  dismiss-no-mutation, editable recovery-block preview, double-lock guard,
  deadline-bound planned-block commit, planning-footprint provenance, and
  Calendar visibility;
- timer start, pause, resume, completion/scope, stop, and delta projection;
- insights/ClaimCompiler-safe response shape and forbidden-claim scan;
- notification enqueue, web pending, toast/render path where available, and
  lifecycle acknowledgement;
- export registry-section and secret-marker scan;
- cleanup of synthetic Holmesberg tasks/deadlines;
- operator privacy scan after mutable dogfood.

For pre-deploy frontend fixes, run the same script against a local production
frontend and the public backend with the opt-in Playwright API proxy:

```powershell
node scripts\browser_holmesberg_product_loop_dogfood.mjs `
  --frontend http://localhost:3010 `
  --api https://api.lyraos.org `
  --proxy-api `
  --run-id local-predeploy-check
```

The proxy is test-harness only. It lets local unreleased UI code exercise the
public API without changing production CORS or weakening browser runtime
contracts.

For pre-deploy operator UI/backend seams, use the operator read-only verifier in
the same local-current style:

```powershell
$env:LYRA_COOKIE_ALINASSERSABRY = [Environment]::GetEnvironmentVariable(
  "LYRA_COOKIE_ALINASSERSABRY",
  "User"
)
node scripts\browser_stress_operator_readonly.mjs `
  --frontend http://localhost:3012 `
  --api http://localhost:8000 `
  --proxy-api `
  --expect-readiness-split `
  --run-id local-current-operator-check
```

Label this proof as `local-current`, not `hosted-public`. Hosted-public proof
still requires `scripts\run_operator_readonly_browser_stress.ps1 -Topology public`
and must record frontend/backend build IDs when they are available.

## CI/CD Operations

Local proof, browser dogfood proof, CI proof, and hosted-public proof answer
different questions. Keep them labeled separately.

After each pushed seam or wave:

- inspect the latest GitHub Actions runs for the pushed branch;
- capture the full head SHA with `(git rev-parse HEAD).Trim()` before proof
  collection;
- record the workflow name, status, conclusion, head SHA, and URL, or record
  that no workflow ran for the branch;
- use the same full SHA in `collect_github_ci_cd_proof.ps1 -HeadSha`; short
  SHAs are display-only;
- if a PR exists, inspect PR checks and record failing, pending, and skipped
  checks;
- classify CI/CD failures before fixing them:
  - product regression;
  - verifier/harness bug;
  - workflow/configuration bug;
  - dependency/cache/runner failure;
  - topology/deployment lag;
  - secret/configuration failure;
  - external service outage;
- create or update a GitHub issue for every non-transient CI/CD failure;
- do not treat screenshots as CI proof;
- do not treat CI success as browser dogfood proof.

The reusable wrapper can collect the read-only CI/CD artifact with
`-IncludeCiCdProof`. This records the current branch, full head SHA, latest
matching GitHub Actions run, job results, PR-check state when a PR exists, and
explicit `no_pr`, `no_workflow_ran`, or `no_matching_run_for_head` states
instead of silently treating missing checks as success. Use
`-CiCdFailOnUnsuccessful` only when the seam has already been pushed and CI is
required to be green.

Hosted-public verification must additionally record whether the deployed
frontend/backend build IDs match the expected commit. If they lag, record the
lag explicitly instead of treating local-current proof as hosted-public proof.

Hosted-public mutable verification may run only when all of these are true:

- Holmesberg or another explicit non-operator test account is the mutable
  identity.
- The run has a unique synthetic prefix and bounded cleanup scope.
- Cleanup/void proof is expected to run before the wave closes.
- The operator account remains read-only.
- The ledger records any residual rows, Redis keys, or gated cleanup as a
  blocker or explicitly harmless residue.

If these are not true, run hosted-public read-only proof and local-current
mutable proof instead.

When the public backend is in read-only pressure safe mode,
`--force-pressure-recovery` may be added to fixture only the pressure-map
recovery option returned to the browser. The fixture must preserve the real
backend gate as a reported issue/gated item. It may test the UI commit seam, but
it must not be cited as proof that the backend is emitting real recovery
options.

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
| Auth and scoping | Holmesberg is non-operator; operator is operator; non-operator cannot access `/operator`, remaining operator-only `/admin/*` triage endpoints, or removed/parked JARVIS routes. | browser covered |
| Operator cockpit | `/operator` and `/v1/operator/dashboard` are read-only, content-minimized, invariant-derived. | browser covered |
| Pulse hub | Quick capture, re-entry visibility, focus card, pressure map, notifications render without raw internals. | partially browser covered |
| First-run onboarding | Consent/intro, parse, edit dump, lock-in, skip, empty validation. | targeted/gated |
| Brain dump | Parse is write-free; commit creates intended task/deadline/binding. | browser covered |
| Brain dump chaos | Edit parsed items, partial failure, retry, duplicate commit/idempotency, existing-deadline binding. | browser covered |
| New task modal | Create task, bind deadline, duration nudge exposure, Use/Keep nudge outcomes, create-anyway soft conflict when present. | browser covered |
| New task branches | Edit mode, terminal deadline rejection, terminal deadline picker exclusion, custom category, no-bind, pick-another, and nudge Keep/dismissed outcome. | browser covered |
| Deadlines | Create, edit, complete/skip/reopen staging, void confirm/cancel, duplicate warning. | partially browser covered |
| Today execution | Task row start/stop, date nav, retroactive edit, overdue done, void/reschedule/drop. | partially browser covered |
| Timer/focus | Start, pause, resume, stop, completion/scope, pause event, delta. | browser covered |
| Timer chaos | Refresh/navigation while paused, long-lived stale session, one-active rejection, interruption/switch/open-thread recovery. | refresh/navigation browser covered; long-lived stale targeted |
| Pressure map | Exposure metadata, horizon API, seeded deadline visibility, preview, dismiss-no-mutation. | browser covered |
| Pressure-map planning | Edit preview, double-lock guard, commit recovery block, deadline binding, planning-footprint provenance, created blocks appear in Calendar. | browser covered with gated backend recovery option |
| Calendar | Day/week/month render; old/new tasks and deadlines visible. | partially browser covered |
| Calendar mutation | Drag/resize planned tasks, reject immutable/executed/deadline/provider rows, dense overlap. | targeted |
| Table | Route render; executed dogfood row/delta visible. | partially browser covered |
| Table audit/correction | Filters, sort, CSV download, voided visibility, executed-row correction. | targeted |
| Insights / ClaimCompiler | Locked/held/unlocked/suppressed states avoid causal/identity/diagnostic claims and show concrete reasons. | forced-state browser/API covered |
| Exposure lifecycle | Decision, render or suppression, browser ack, linked interaction outcome where applicable. | partially browser/API covered; existing-decision suppression endpoint covered by backend tests |
| Notifications | Queue, pending, render, dismiss, terminal lifecycle row. | browser/API covered |
| Notification branches | Action, expiry, duplicate/cooldown, linked exposure, operator-mirror redaction. | action/expiry browser/API covered; linked exposure backend covered; duplicate/operator-mirror targeted/gated |
| Settings/export | Export registry sections and no secret markers. | API covered |
| Settings/delete | Browser export download, staged delete, final hard-delete and Redis purge. | disposable-account gated |
| Providers/integrations | Credential redaction, provider provenance, connect/disconnect/failure/import idempotency. | credential gated |
| Operator relay | No accidental product-user exposure, no destructive drain before send, one delivery authority. | relay covered; compatibility pending endpoint operator-gated and peek-only |

## What The Loop Does Not Yet Prove

The current loop is broad, but not a replacement for every human dogfood path.
It does not yet fully exercise:

- calendar drag/resize/reschedule UI;
- real backend pressure-map recovery option emission while read-only pressure
  safe mode is active;
- table audit/correction flows;
- real worker-triggered linked-exposure notification cases in browser;
- real production-data Insights unlocked/held/error states without API interception;
- long-lived sessions over hours/days;
- rapid-click race conditions outside the covered brain-dump commit guard.

When a wave touches one of those surfaces, add a targeted Playwright dogfood
script before treating the loop as sufficient.

Highest-priority targeted scripts to add next:

1. Long-lived timer stale-session handling over hours/days.
2. Real worker-triggered linked-exposure notification outcomes in browser.
3. Real production-data Insights unlocked/held/error states without API interception.
4. Calendar drag/resize/reschedule and table correction flows.
5. First-run onboarding brain-dump lock-in/skip/empty-validation coverage.
6. Real pressure-map recovery options after pressure safe mode is lifted.

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
- backend/frontend build/test failures for the selected mode;
- unexpected CI/CD failure, missing required check, or unclassified deployment
  lag for pushed seams/waves.

The loop also fails the refactor strategy, even if commands pass, when three
consecutive R3/R4 seams are cosmetic-only. A seam is not allowed to count as
danger reduction unless it improves a gate, proof, owner boundary, rollback
boundary, issue state, or runtime observability.

The loop does not automatically fail just because `/operator` readiness is
yellow or red. During freeze closure, readiness may be yellow/red because known
invariants are still open. It fails if readiness regresses in a way the cockpit
cannot explain, if blockers become stale labels instead of concrete invariants,
or if critical counters violate active contracts.

Classify every failure before fixing it:

- product bug;
- verifier/harness bug;
- topology/deployment bug;
- CI/CD operations bug;
- authority bug;
- documentation bug;
- measurement bug.

Verifier bugs are first-class bugs. If the harness lies, file or record the bug
with the same seriousness as a product regression.

Evidence beats screenshots. Screenshots explain failures; they do not prove
behavior. Canonical proof comes from backend state, exported evidence, operator
invariants, and browser behavior together.

Holmesberg mutable verification is incomplete until synthetic rows are cleaned,
voided, or proven harmless. Cleanup proof must be recorded before a wave can be
closed.

## Ledger Requirement

Every wave or risky PR must record:

- command and mode run;
- output directory;
- danger delta: what became more observable, reversible, owned, or provable;
- changed authority;
- removed paths;
- parked paths;
- moved authority;
- tests added or named;
- browser proof artifact;
- CI/CD proof artifact or run URL after push;
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
7. After push, inspect GitHub Actions/PR checks and record CI/CD proof, failure
   classification, or deployment lag.

## Next Coverage Targets

Add targeted scripts for:

- calendar drag/resize/reschedule;
- real pressure-map recovery options after pressure safe mode is lifted;
- notification lifecycle action/expiry;
- table correction;
- production-data insights held/unlocked latency.
