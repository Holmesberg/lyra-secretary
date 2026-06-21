# LyraOS Code Bug Hunt - 2026-06-04

Status: audit report only.  
May authorize code: false.  
Runtime owner: none.  
Scope: Lyra Secretary v0.1 repo, not the Obsidian vault.

## Executive Summary

This audit found a promising product loop with several cohort-blocking reliability
and measurement risks.

The concrete checkpoint:

| Known issue | Current read | Cohort risk |
|---|---|---|
| K01 calendar warning | Operator/debug alerts were able to reach the web path through the shared notification queue. Current dirty worktree mitigates web rendering, but channel design remains fragile. | High |
| K02 timer overflow duplicate + raw float | Raw float is mitigated in current dirty worktree; duplicate operator/web semantics and missing exposure accounting remain. | High |
| K03 invalid mark-done on EXECUTED task | Symptom is consistent with stale `/tasks/query` / evidence cache plus frontend/backend eligibility drift. Current dirty worktree hides the stale card after rejection, but root cache invalidation remains. | High |
| K04 parked 25h interruption chain | Old parked work can stay immediate, Redis-active stale pauses can evade recovery, and stale recovery can auto-mark tasks executed without execution timestamps. | High |
| K05 Pulse quick-capture anchor | Live Pulse anchor is correct and top-positioned; stale tutorial/docs still point some brain-dump framing toward `/today`. | Low |

Verdict:

```text
Not ready to expand the cohort until the notification, stale-session,
range-cache, and clean-measurement gates below are fixed and browser verified.
```

The core loop is not fundamentally broken. The dangerous bugs are not mostly UI
polish. They are boundary bugs: notification channel boundaries, stale state
boundaries, provider-truth boundaries, and clean-data boundaries.

Paper-direction note:

```text
Measurement Integrity Before Agency Claims
```

This bug hunt is one concrete case study for that direction. K01-K05 and later
waves show why LyraOS cannot interpret productivity, focus, motivation,
avoidance, discipline, recovery, or agency until it first knows whether the row
was current, rendered, clean, provider-derived, repaired, exposed,
operator-only, or stale.

Canonical research note:
`docs/measurement_integrity_before_agency_claims.md`.

Senior-grade UI/UX verification rule:

```text
For every feature, bug, or product path changed by this closure cycle, browser
verification must exercise the actual changed workflow, not just page load.
Prefer read-only passes; if testing creates tasks, deadlines, sessions,
notifications, or provider rows, void/delete them in the same turn and report
cleanup evidence.
```

Current read-only operator stress proof:

- account: `alinassersabry` operator cookie;
- command:
  `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_operator_readonly_browser_stress.ps1 -Topology public`;
- result:
  `tmp/operator-readonly-stress-2026-06-21T10-07-16-324Z/result.json`;
- coverage: Pulse, Today, Calendar, Deadlines, Table, Insights, Settings, and
  Operator on desktop and mobile;
- cleanup proof: before/after export counts matched for tasks, deadlines,
  stopwatch sessions, pause events, feedback, exposure logs, and notifications.

## Implementation Checkpoint - 2026-06-04 Evening

Status: partial implementation pass completed for K01-K04.

What changed:

- K01/K02 notification boundary:
  - added explicit web and OpenClaw notification endpoints;
  - web notification fetch now peeks instead of destructively draining;
  - web acknowledgements remove rendered notification IDs;
  - app shell now hosts user-safe notification toasts for Pulse and Today;
  - operator/OpenClaw copy remains separate from web copy.
- K03 state freshness:
  - stopwatch start, pause, resume, switch, stop, stale resolution, readiness
    correction, and completion correction now invalidate task range cache.
- K04 stale paused sessions:
  - stale paused sessions at or beyond 72h now require user-confirmed
    reflection instead of auto-resolution;
  - backend endpoint added:
    `POST /v1/stopwatch/stale-pauses/{session_id}/resolve`;
  - resolution captures focus rating, completion percent, and scope outcome;
  - completion >=80 marks the task `EXECUTED`; completion <80 marks it
    `SKIPPED`;
  - user-resolved stale pause sessions are flagged
    `data_quality_flag=user_resolved_stale_pause` and excluded from clean
    calibration.

Concrete K04 incident repair:

- User: `alinassersabry@gmail.com` / `user_id=1`.
- Task: `Lyra waves`.
- Task id: `a28e8d45-69a3-45c2-928f-5af793b27db6`.
- Session id: `4f3a0273-f5aa-426e-a452-0d65d8717959`.
- Repaired state:
  - `state=EXECUTED`;
  - `executed_duration_minutes=396`;
  - `task_completion_percentage=90`;
  - `post_task_reflection=2`;
  - `scope_outcome=expanded`;
  - `Task.initiation_status=stale_resolved`;
  - `StopwatchSession.data_quality_flag=user_resolved_stale_pause`.

Important nuance:

```text
This repair preserves product truth for the user but excludes the row from
clean calibration baselines.
```

Still open:

- Bias lookup, insights, and deadline-shape endpoints were closed in the newer
  Wave B pass; older agent rows below are retained as historical findings.
- Provider/data-sovereignty issues in Gate 3 remain open.
- Redis-active stale pause recovery and range-cache freshness were closed in
  the newer Wave 2 pass; Pressure Map safe-mode authority and brain-dump
  recovery UX were closed in Wave 3. Dynamic operator issues,
  provider/data-sovereignty, and final cohort-readiness proof remain open.

## Wave A Browser Verification - 2026-06-05

Status: passed on the deployed public web app.

Verification method:

- deployed frontend build: `f251653`;
- disposable production user:
  `wave-a-verify-1780658138440@example.test`;
- seeded only synthetic Wave A rows:
  - one queued `operator_alert` containing `[calendar.sync]` diagnostic copy;
  - one queued `timer_overflow` payload containing a raw float and `Reply with`
    text in the raw payload;
  - one `EXECUTED` task that would be invalid as a missed-plan action;
  - one paused stopwatch session parked for `73h`;
- opened `/pulse#quick-capture` directly, without visiting Today;
- screenshots:
  - `tmp/lyra-wave-a-1780658138440/pulse-wave-a.png`;
  - `tmp/lyra-wave-a-1780658138440/stale-resolution-modal.png`;
- synthetic user, rows, notification queue, stopwatch Redis state, task-range
  cache, `/me` cache, and exposure-ledger rows were cleaned up afterward.

Checks:

| Check | Result | Evidence |
|---|---|---|
| K01 calendar warning leak | Pass | Web Pulse did not render `[calendar.sync]`, Google token-refresh diagnostic copy, affected-user scope, or data-integrity technical text. |
| K02 timer overflow duplicate/raw float | Pass | Pulse rendered exactly one user-safe toast: `Task is past its planned window (36m active; planned 30m). Open it to stop or correct.` No raw float or `Reply with` copy rendered. |
| K03 invalid mark-done on `EXECUTED` task | Pass | The seeded `EXECUTED` task appeared only in the Today-plan list as done, not in the re-entry queue or missed-plan action surface. |
| K04 stale parked pause resolution | Pass | The `73h` parked session showed `Resolve session`; clicking it opened the reflection modal with active work, planned time, paused duration, completion % required, scope required, and the close-at-pause-time notice. |
| K05 quick-capture anchor | Pass | `/pulse#quick-capture` landed on the top quick-capture bar. |
| Pulse notification host | Pass | The queued web notification rendered on Pulse without visiting Today. |

Important nuance:

```text
Wave A verifies the current web/re-entry behavior. It does not close Wave B
clean-measurement work, Wave C provider/data-sovereignty work, or Wave D
formal exposure-registration work.
```

## Wave 1 Closure - Notification Lifecycle And Exposure Truth - 2026-06-08

Status: implemented and Codex-browser verified locally. User-side browser
verification is still required before Wave 2 begins.

Scope closed:

- added durable notification lifecycle rows:
  `created -> queued -> reserved -> rendered -> acted | dismissed | expired |
  lost_unrendered`;
- web pending fetch reserves visible web notifications instead of draining them;
- web ack now records explicit lifecycle event types;
- app-shell notification host only marks actually mounted toasts as rendered;
- unsupported/operator-only payloads in the web path are marked
  `lost_unrendered`, not rendered;
- repeated React renders no longer spam duplicate render/lost ack calls;
- timer overflow is registered as output surface `worker.timer_overflow`;
- timer overflow creates a user web event separately from the OpenClaw/operator
  alert;
- timer-overflow dedupe is backed by DB lifecycle rows so Redis/process restart
  does not create duplicate web prompts;
- operator dashboard notification lifecycle metrics now distinguish web created,
  queued, reserved, rendered, acted, dismissed, expired, lost-unrendered,
  duplicate prompts, and operator pending.

Automated verification:

- `cd backend && ..\.venv311\Scripts\python.exe -m pytest
  tests/test_notification_queue_openclaw_mirror.py
  tests/test_timer_overflow_notifications.py tests/test_operator_dashboard.py
  tests/test_output_surfaces.py`
  - result: `37 passed`;
- `cd frontend && npm run build`
  - result: production build passed;
- `cd backend && ..\.venv311\Scripts\python.exe -m alembic heads`
  - result: `056 (head)`.

Codex browser verification:

- ran against local rebuilt frontend on disposable port `3211`;
- browser session and API responses were mocked; no production data or real user
  account was mutated;
- screenshots and verifier output:
  - `tmp/wave1-pulse-toast.png`;
  - `tmp/wave1-operator-lifecycle.png`;
  - `tmp/wave1-browser-verify-result.json`.

Checks:

| Check | Result | Evidence |
|---|---|---|
| User timer-overflow toast | Pass | Pulse rendered exactly one user-safe toast: `Task is past its planned window (36m active; planned 30m). Open it to stop or correct.` |
| Operator copy leak | Pass | Browser body did not contain `Reply with`, `[alert]`, `[scheduler.timer-overflow]`, or the raw float. |
| Render ack truth | Pass | Verifier recorded `rendered` only for `wave1-timer`. |
| Lost-unrendered truth | Pass | Unsupported `operator_alert` payload recorded `lost_unrendered`, not rendered. |
| Dismiss ack truth | Pass | Closing the toast recorded `dismissed` for `wave1-timer`. |
| Operator lifecycle display | Pass | `/operator` displayed `web_rendered=1`, `web_lost_unrendered=1`, `web_dismissed=1`, `operator_pending=1`. |

Exit gate remaining:

```text
User must verify Pulse/Today do not leak operator copy and that /operator
separates queued/rendered/dismissed/lost-unrendered lifecycle counts before
Wave 2 begins.
```

## Wave 2 Closure - Re-entry, Stale Pause, Cache, And State Freshness - 2026-06-09

Status: implemented, Codex-browser verified locally, and user-browser verified.
Wave 2B idempotency hardening was added on 2026-06-10.

Scope closed:

- Redis-active paused sessions at or beyond `72h` no longer hide behind the
  worker's "currently active" skip branch;
- stale paused sessions remain open for explicit user reflection resolution and
  are not auto-marked `SKIPPED` or `EXECUTED` by the stale-session worker;
- active unattended timers remain the separate scheduler-recovered stale case;
- stale pause resolution boundary tests now cover:
  - `71h59m` rejected;
  - exact `72h` accepted;
  - `79%` completion resolves incomplete/`SKIPPED`;
  - `80%` completion resolves `EXECUTED`;
  - double-submit after resolution is rejected as already closed;
- task range freshness now busts after shared mutation edges:
  - task start, complete, skip, delete, swap, and reschedule;
  - direct void and mark-abandoned endpoint mutations;
  - LLM deadline confirm/reject binding corrections;
  - deadline create/update/import/void changes that affect rendered task context;
  - stale-session and orphan-task recovery workers;
- Pulse timer surfaces now invalidate `stopwatch-status`, `tasks`,
  `tasks-range`, `tasks-evidence`, `pressure-map`, and `/me` after
  start/pause/resume/stop/switch paths;
- Pulse missed-plan rejection handling now treats backend stale-eligibility
  rejections as a reason to dismiss/refetch the stale card rather than show the
  user a dead-action error.
- Wave 2B double-submit hardening:
  - stopwatch start/pause/resume/stop endpoints accept user-scoped
    `X-Idempotency-Key` replay protection;
  - frontend stopwatch and mark-done wrappers send idempotency headers;
  - starting the same already-active task returns the existing session instead
    of creating a duplicate session or surfacing a false error;
  - repeated pause returns the existing paused state without writing an extra
    `PauseEvent`;
  - repeated resume on an already-running active timer returns a zero-duration
    no-op success without incrementing pause count;
  - stop retries with the same idempotency key replay the first response and do
    not perform a second terminal transition;
  - mark-done retries are idempotent only for the narrow retroactive-done shape;
    genuinely timer-executed `EXECUTED` tasks still reject the stale
    missed-plan action.

Automated verification:

- `cd backend && ..\.venv311\Scripts\python.exe -m pytest
  tests/test_stale_pause_resolution.py`
  - result: `7 passed`;
- `cd backend && ..\.venv311\Scripts\python.exe -m pytest
  tests/test_wave2_state_freshness.py`
  - result: `2 passed`;
- `cd backend && ..\.venv311\Scripts\python.exe -m pytest
  tests/test_wave2_idempotency.py`
  - result: `4 passed`;
- Wave 2 targeted bundle:
  - `tests/test_wave2_idempotency.py`;
  - `tests/test_stale_pause_resolution.py`;
  - `tests/test_wave2_state_freshness.py`;
  - `tests/test_state_consistency.py`;
  - `tests/test_stopwatch_start_errors.py`;
  - `tests/test_swap_and_planned_skip.py`;
  - result: `36 passed`;
- adjacent state/recovery suites:
  - `tests/test_state_consistency.py`;
  - `tests/test_stopwatch_switch.py`;
  - `tests/test_swap_and_planned_skip.py`;
  - `tests/test_jobs_skip_voided_tasks.py`;
  - `tests/test_me_cache.py`;
  - `tests/test_stale_session_recovery_scheduler_contract.py`;
  - `tests/test_orphan_task_recovery.py`;
  - `tests/test_stopwatch_recovery.py`;
  - `tests/test_void_clears_stopwatch.py`;
  - `tests/test_stopwatch_pause_counter_anchor.py`;
  - `tests/test_stopwatch_start_errors.py`;
  - result: all targeted adjacent suites passed;
- full backend regression suite:
  - `cd backend && ..\.venv311\Scripts\python.exe -m pytest -q`;
  - result after Wave 2B: `1016 passed, 1 xfailed`;
- frontend production build:
  - `cd frontend && npm run build`;
  - result: production build passed.

Codex browser verification:

- ran against local rebuilt frontend on disposable port `3212`;
- browser session and API responses were mocked; no production data or real user
  account was mutated;
- screenshots and verifier output:
  - `tmp/wave2-reentry-tiers.png`;
  - `tmp/wave2-stale-resolution-modal.png`;
  - `tmp/wave2-after-resolution.png`;
  - `tmp/wave2-browser-verify-result.json`;
  - `tmp/wave2b-start-idempotency.png`;
  - `tmp/wave2b-markdone-idempotency.png`;
  - `tmp/wave2b-browser-verify-result.json`;
  - debug text:
    `tmp/wave2-stale-reentry-text.txt`,
    `tmp/wave2-modal-text.txt`.

Checks:

| Check | Result | Evidence |
|---|---|---|
| 30m paused tier | Pass | Re-entry copy: `Paused for 30m. Pick it back up?` |
| 8h paused tier | Pass | Re-entry copy: `Parked for 8h. Pick up, reschedule, or leave parked.` |
| 25h paused tier | Pass | Re-entry copy: `Open thread from earlier. Parked for 25h.` |
| 73h stale paused tier | Pass | Re-entry card shows `Parked for 73h. Resolve what happened.` and button `Resolve session`. |
| Stale reflection modal | Pass | Modal showed active work, planned time, paused duration, required completion %, required scope, and `Lyra will close the session at the time you paused it.` |
| Stale resolution payload | Pass | Browser submitted `post_task_reflection=2`, `task_completion_percentage=90`, `scope_outcome=expanded`. |
| Resolved card removal | Pass | The `73h` re-entry card disappeared after successful resolution. |
| Executed task eligibility | Pass | A seeded `EXECUTED` task did not appear in the re-entry queue. |
| Timer-start double click | Pass | Browser observed idempotency headers on repeated start clicks and no visible `already running` or `Failed to start` error. |
| Missed-plan done double click | Pass | Browser observed idempotency headers on repeated done clicks, no `current state` error, and the card disappeared. |

Public recovery note:

- During Wave 2B verification, a local frontend build touched the shared
  `.next` directory while the public Next server was serving it, causing
  stale public HTML/chunk mismatch (`ChunkLoadError` / `_next` 400s).
- Recovery performed:
  - rebuilt public frontend with build id `5ad58b7`;
  - restarted backend/Redis and migrations;
  - restarted Cloudflare tunnel on HTTP/2 after WSL SRV DNS failed for QUIC;
  - patched `scripts/restart_cloudflared_wsl.ps1` to use HTTP/2 for this
    tunnel path, matching the verified recovery command;
  - verified `https://lyraos.org/pulse` returns `200`;
  - verified `https://api.lyraos.org/v1/health` returns `200`;
  - verified public topology:
    `frontend_build_id=5ad58b7`, `backend_build_id=dev`;
  - browser fresh-load check found no real `_next` chunk/CSS failures:
    `tmp/public-recovery-check.json`;
  - screenshot: `tmp/public-recovery-pulse.png`.

Important nuance:

```text
Wave 2 closes the concrete K03/K04 stale state and stale pause implementation
pass. Wave 3 now closes product-loop authority/UX. Wave 4 dynamic operator
issues, Wave 5A data sovereignty, Wave 5B provider security, and the Wave 6
final green cohort proof remain open.
```

## Wave 3 Closure - Product Loop Authority And Recovery UX - 2026-06-11

Status: implemented, targeted-tested, production-built, and Codex-browser
verified locally. User-side browser verification is required before Wave 4
begins.

Scope closed:

- Pressure Map no longer has frontend creation authority when the backend does
  not return an explicit `create_plan` or `split_into_blocks` recovery option;
- the previous fallback `Preview focus blocks` path was removed;
- when `confirm_coverage` is the first recovery option and `create_plan` is a
  later option, the preview button renders beside the planning option instead
  of the coverage-confirmation card;
- Pressure Map soft-conflict rows now show an explicit `Create anyway` action
  only when `/v1/create` returns `can_proceed=true` and non-hard severity;
- forced recovery-plan creation sends `force=true`;
- `/v1/brain-dump/commit` accepts a user-scoped `X-Idempotency-Key` and replays
  the first commit response for duplicate submits;
- Pulse brain-dump commits now send idempotency keys;
- brain-dump confirmation rows are editable before commit:
  title, start/due time, and duration;
- partial brain-dump failures preserve the failed item text and offer
  `Edit failed items` plus `Move to tomorrow` for past-time failures;
- edited failed-item retries get a fresh idempotency key so they do not replay
  the failed commit response;
- stale first-run tutorial copy that sent brain dump to `/today` now points to
  Pulse capture and preview confirmation.

Automated verification:

- `cd backend && ..\.venv311\Scripts\python.exe -m pytest
  tests/test_brain_dump_endpoint.py -q`
  - result: `11 passed`;
- `cd backend && ..\.venv311\Scripts\python.exe -m pytest
  tests/test_conflict_detection_severity.py -q`
  - result: `20 passed`;
- `cd backend && ..\.venv311\Scripts\python.exe -m pytest
  tests/test_academic_pressure_map.py::test_read_only_pressure_safe_mode_suppresses_risky_paths -q`
  - result: `1 passed`;
- `cd frontend && npm run build`
  - result: production build passed.

Known test-environment caveat:

- running the full `tests/test_academic_pressure_map.py` file under the local
  repo `.env` keeps `LYRA_SAFE_MODE=read_only_pressure` and
  `LYRA_RECOVERY_NUDGES_ENABLED=false`, so legacy tests that expect recovery
  options enabled fail in that environment. This was not introduced by Wave 3;
  the explicit read-only pressure safe-mode test still passes.

Codex browser verification:

- topology correction: an earlier disposable `3001` run was discarded because
  `runtime_topology.json` only authorizes `localhost:3000` as the local
  frontend origin;
- stopped the stray `3001` frontend process;
- rebuilt the frontend in verified local topology on
  `http://localhost:3000`;
- ran `node scripts/verify_runtime_topology.mjs --topology local --skip-browser`
  before browser verification;
- reran browser verification against `http://localhost:3000`;
- restored the public WSL bundle on `localhost:3000` after verification and
  confirmed `node scripts/verify_runtime_topology.mjs --topology public
  --skip-browser` passed;
- browser session and API responses were mocked; no production data or real
  user account was mutated;
- screenshots and verifier output:
  - `tmp/wave3-pressure-safe-mode.png`;
  - `tmp/wave3-pressure-create-anyway.png`;
  - `tmp/wave3-brain-dump-edit-retry.png`;
  - `tmp/wave3-browser-verify-result.json`.

Checks:

| Check | Result | Evidence |
|---|---|---|
| Safe-mode pressure authority | Pass | With `recovery_options=[]`, Pressure Map showed diagnostic load only and no `Preview focus blocks`/planning option. |
| Recovery-option copy/action alignment | Pass | `Confirm coverage` rendered without a preview button; the preview button rendered on the later `Planning option` card. |
| Soft-conflict override | Pass | First create returned `can_proceed=true`; dialog showed `Create anyway`; retry sent `force=true` and succeeded. |
| Brain-dump partial failure recovery | Pass | Failed item text stayed in the modal; `Edit failed items` reopened editable fields without retyping. |
| Brain-dump retry idempotency | Pass | First and edited retry commits both sent idempotency keys; edited retry used a fresh key and sent the edited title. |
| Stale `/today` brain-dump tutorial copy | Pass | Runtime grep found no `Plan your week`/`/today feed` brain-dump onboarding copy in frontend code. |
| Forbidden copy snapshot | Pass | Browser body did not include `avoidance`, `motivation`, `discipline`, `fragmentation score`, or `focus score` in the Wave 3 flow. |

Important nuance:

```text
Wave 3 closes product-loop authority and brain-dump recovery UX. It does not
close Wave 4 dynamic operator issues, dashboard denominator/exposure cleanup,
Wave 5A data sovereignty, Wave 5B provider security, temporal reliability, or
the Wave 6 final green cohort proof.
```

## Wave 4 Closure - Operator Dashboard Dynamic Issues And Measurement Truth - 2026-06-12

Status: implemented, targeted-tested, production-built, and Codex-browser
verified locally. User-side browser verification is required before Wave 5A
begins.

Scope closed:

- `/operator` now emits `dynamic_issues` derived from live invariants and
  diagnostic rules rather than hard-coded K01-K05 names;
- K01-K05 appear as tags/statuses on the watchlist, while blockers are concrete
  invariant issues such as duplicate open sessions, stale unresolved sessions,
  internal web-copy leaks, duplicate prompts, or low clean-trace ratio;
- readiness blockers, minimum fix set, and operator recommendations are derived
  from `dynamic_issues`;
- `clean_trace_ratio` is explicitly:
  `clean eligible explicit stopwatch sessions / all eligible explicit stopwatch
  sessions`;
- the denominator excludes and separately reports:
  - operator-user sessions;
  - test/synthetic-user sessions;
  - voided/deleted task sessions;
  - deleted-retained sessions;
  - provider-only rows;
  - non-session tasks;
- `dirty_reason_distribution` mirrors the dirty buckets so a low ratio is
  explainable;
- `exposure_contaminated` is now computed per eligible task/session through the
  exposure horizon policy for `planning_estimate` and `duration_behavior`;
- unrelated exposure renders no longer make every closed session dirty;
- per-user clean trace rows use the same aggregate cleanliness decision;
- dirty-session reason samples use hashed session identifiers, not raw task
  content or raw email/provider data;
- provider-integrity counts are scoped to trusted cohort users, excluding
  operator/test/synthetic fixtures;
- `/operator` renders dynamic issues and object-shaped metrics without
  `[object Object]`.

Wave 4A cockpit weighting correction:

- `exposure_without_render_count > 0` is now a critical dynamic issue:
  `exposure_records_without_render_evidence`;
- the issue message includes the live count, for example:
  `Exposure ledger contains 17 exposure records without render evidence`;
- this blocks cohort expansion because exposure-influenced metrics are not
  valid without render linkage proof;
- `notifications_last_seen_at` missing from data freshness now surfaces as:
  `notification_source_freshness_not_instrumented`;
- notification source freshness is a warning by default because it makes
  lifecycle counts incomplete rather than proving a direct product-state
  violation;
- the corrected cockpit read is:
  - critical blockers: duplicate notification prompts or duplicate/open state
    invariants when present, plus exposure records without render evidence;
  - warnings/readiness suppressors: no eligible closed sessions, invalid
    recovery actions not instrumented, product-loop dropoff, and notification
    source freshness not instrumented.

Read-only verification rule:

```text
/operator observes readiness; it must not participate in the user/product
measurement system.
```

Visual browser checks are necessary but insufficient. Read-only proof requires
a before/after snapshot of notification lifecycle counts, pending/reserved/
rendered IDs, exposure counts, user activity timestamps, and relevant user
metric fields. The backend test
`test_operator_dashboard_read_is_side_effect_free` captures that invariant for
the operator endpoint.

Automated verification:

- `cd backend && ..\.venv311\Scripts\python.exe -m pytest
  tests/test_operator_dashboard.py -q`
  - result: `5 passed`;
- `cd backend && ..\.venv311\Scripts\python.exe -m pytest
  tests/test_exposure_ledger_v0.py tests/test_output_surfaces.py -q`
  - result: `36 passed`;
- `cd frontend && npm run build`
  - result: production build passed;
- `cd backend && ..\.venv311\Scripts\python.exe -m pytest -q`
  - result: timed out after 10 minutes before returning a suite result.

Codex browser verification:

- local-only topology was used:
  `http://localhost:3000` frontend and `http://localhost:8000` API;
- `node scripts/verify_runtime_topology.mjs --topology local --skip-browser`
  passed before browser verification;
- browser session and `/v1/operator/dashboard` payload were mocked to verify UI
  rendering without mutating production data or a real user account;
- screenshots and verifier output:
  - `tmp/wave4-operator-dashboard.png`;
  - `tmp/wave4-browser-verify-result.json`.

Checks:

| Check | Result | Evidence |
|---|---|---|
| Dynamic issue visibility | Pass | `/operator` rendered a `Dynamic Issues` section with a seeded duplicate-open-session blocker. |
| Readiness impact | Pass | The seeded invariant produced red readiness, minimum fix set, and operator recommendation entries. |
| K tag boundary | Pass | K03 appeared as a tag/status, not as the issue identity. |
| Clean-trace denominator copy | Pass | UI rendered the explicit denominator definition and exclusion buckets. |
| Object rendering | Pass | Browser body did not contain `[object Object]`. |
| Forbidden copy snapshot | Pass | Browser body did not include `avoidance`, `motivation`, `discipline`, `fragmentation score`, or `focus score`. |

Important nuance:

```text
Wave 4 makes the operator dashboard more decision-grade and fixes the
measurement-integrity denominator/exposure bug. It does not close Wave 5A data
sovereignty, Wave 5B provider security/integrity, or the Wave 6 final green
cohort proof.
```

## Wave 5A Closure - Data Sovereignty - 2026-06-15

Status: implemented, targeted-tested locally, and user browser-verified.

Scope closed:

- added a central user-owned data registry:
  `backend/app/services/user_data_registry.py`;
- `/v1/users/me/export` now uses the registry instead of a hand-curated
  `user/tasks/stopwatch/archetype` list;
- export now includes registered user-owned sections for:
  - tasks;
  - deadlines;
  - deadline completion and task-deadline outcome rows;
  - stopwatch sessions;
  - task execution corrections;
  - pause events;
  - pause/resume prediction logs;
  - calibration nudge events;
  - reflection view logs;
  - exposure decisions, renders, acknowledgements, suppressions, and policy
    diagnostics;
  - feedback;
  - external event outcomes;
  - notification lifecycle rows;
  - email engagement rows;
  - archetype assignments;
  - JARVIS invocation rows.
- export includes an `integration_state` summary without exporting raw Google
  refresh tokens, Moodle iCal URLs, Moodle WS tokens, or raw provider URLs;
- export redacts token-like values in operational URL fields;
- security audit rows remain outside the behavioral/user-data registry because
  `SecurityAuditEvent` is append-only governance infrastructure and is blocked
  from behavioral paths by `tests/test_security_audit.py`;
- export now names that exception in `governance_audit_policy` instead of
  silently omitting it;
- account delete now uses the registry purge/anonymization helpers instead of
  endpoint-local SQL table lists;
- retain-for-research mode still anonymizes task/session rows and purges
  auxiliary user-owned rows;
- hard-delete mode purges task/session rows as well;
- `RedisClient.purge_user_runtime_state()` now clears known user-scoped Redis
  runtime keys:
  - active/paused stopwatch;
  - pending notifications;
  - undo and idempotency keys;
  - `/me` and task-range caches;
  - Google Calendar access-token/event caches;
  - reminder/timer-overflow/insight seen keys;
  - Notion sync queue;
  - last-operated task.

Automated verification:

- `cd backend && ..\.venv311\Scripts\python.exe -m pytest
  tests/test_delete_account_modern_auxiliary_rows.py
  tests/test_redis_state_contract.py -q`
  - result: `8 passed`;
- `cd backend && ..\.venv311\Scripts\python.exe -m pytest
  tests/test_delete_account_modern_auxiliary_rows.py
  tests/test_redis_state_contract.py
  tests/test_delete_account_with_external_outcomes.py
  tests/test_multiuser_isolation_adversarial.py::test_export_and_delete_account_do_not_cross_user_boundaries
  tests/test_security_audit.py -q`
  - result: `15 passed`;
- `cd backend && ..\.venv311\Scripts\python.exe -m pytest
  tests/test_notification_queue_openclaw_mirror.py tests/test_me_cache.py -q`
  - result: `16 passed`.
- `cd backend && ..\.venv311\Scripts\python.exe -m pytest
  tests/test_delete_account_modern_auxiliary_rows.py
  tests/test_redis_state_contract.py
  tests/test_delete_account_with_external_outcomes.py
  tests/test_multiuser_isolation_adversarial.py tests/test_security_audit.py
  tests/test_raw_sql_user_scope_scan.py -q`
  - result: `39 passed`;
- `cd frontend && npm run build`
  - result: production build passed.

Important nuance:

```text
Wave 5A closes export/delete registry coverage and Redis runtime purge. It does
not close provider SSRF protection, credential encryption, provider provenance,
duplicate provider imports, or terminal-deadline binding correction; those are
Wave 5B.
```

## Wave 5B Closure - Provider Security And Integrity - 2026-06-15

Status: implemented and targeted-tested locally. Browser verification is still
required before Wave 6 final cohort-readiness proof.

Scope closed:

- added provider URL network-safety guard:
  `backend/app/utils/provider_url_safety.py`;
- Moodle iCal and Moodle WS fetches now validate every resolved target and
  redirect hop before request;
- loopback, private, link-local, multicast, reserved, unspecified, metadata IP,
  and redirect-to-private targets are rejected;
- Google refresh tokens are now Fernet-encrypted at rest;
- Moodle iCal URLs are now Fernet-encrypted at rest;
- legacy plaintext Google/Moodle credentials still read and rewrite encrypted;
- Moodle WS plaintext legacy tokens still read and rewrite encrypted;
- Moodle WS submission sync now records provider completion candidates instead
  of silently completing canonical deadlines;
- Moodle WS backfilled submitted assignments create visible external deadlines
  plus completion-candidate evidence, not completed canonical rows;
- Settings/Moodle copy now says submission evidence instead of auto-marking;
- `moodle_ws_backfill` deadlines render with Moodle provenance in Today,
  Deadlines, and Pulse;
- external imports now skip native same-title/same-day duplicate deadlines
  instead of creating duplicate obligations;
- deadline-binding correction now rejects terminal deadlines
  (`completed`, `missed`, `skipped`);
- operator provider integrity now counts provider-truth violations and raises a
  critical dynamic issue if provider evidence has completed canonical
  deadlines without user confirmation.

Automated verification:

- `cd backend && ..\.venv311\Scripts\python.exe -m pytest
  tests/test_provider_url_safety.py tests/test_provider_credentials_security.py
  tests/test_moodle_ics_sync.py tests/test_moodle_submissions_sync.py
  tests/test_deadline_binding_correction.py tests/test_operator_route_security.py
  -q`
  - result: `75 passed`;
- `cd backend && ..\.venv311\Scripts\python.exe -m pytest
  tests/test_provider_url_safety.py tests/test_provider_credentials_security.py
  tests/test_moodle_ics_sync.py tests/test_moodle_submissions_sync.py
  tests/test_deadline_binding_correction.py tests/test_operator_route_security.py
  tests/test_delete_account_modern_auxiliary_rows.py tests/test_security_audit.py
  tests/test_raw_sql_user_scope_scan.py tests/test_multiuser_isolation_adversarial.py
  -q`
  - result: `108 passed`;
- `cd frontend && npm run build`
  - result: production build passed.

Browser verification still needed:

- Settings / Moodle copy says submission evidence, not auto-mark complete;
- a `moodle_ws_backfill` deadline shows a Moodle badge in Today, Deadlines, and
  Pulse;
- a terminal deadline cannot be selected/bound through correction UI;
- unsafe Moodle URL attempts show a connection failure without leaking raw URL
  or token;
- operator dashboard provider integrity shows completion candidates, duplicate
  import candidates, and provider-truth violations without exposing secrets.

Important nuance:

```text
Wave 5B closes the provider security/integrity bug class in code and targeted
tests. It does not prove final cohort readiness; Wave 6 must still verify the
full green gate, browser behavior, and cleanup state.
```

## Wave B Implementation And Verification - 2026-06-05

Status: implemented and verified on the deployed public web app.

What changed:

- visible undo UX:
  - added a global app-shell undo toast with a visible `UNDO` button;
  - timer start and task deletion now announce undo availability;
  - task creation no longer announces undo availability; timer start is the
    primary accidental-action rollback surface;
  - undo invalidates task, range, evidence, stopwatch, deadline, operator, and
    `/me` query state after completion;
  - Pulse/Today no longer depend on an invisible 30-second backend capability;
  - timer-start undo reverts the task to its previous state, clears the active
    stopwatch state, and deletes the just-created stopwatch session when the
    exact started session is still active.
- Pulse stop flow:
  - captures post-task focus rating;
  - captures completion percentage;
  - captures scope outcome (`Plan`, `Expanded`, `Reduced`);
  - keeps the entered completion/scope values through the early-stop
    confirmation gate;
  - fixed the readiness control so the visible default `Steady` value is a real
    selectable value and does not leave `Start session` disabled.
- clean measurement gates:
  - bias lookup now sources personal evidence from the shared planning
    calibration clean primitive instead of hand-rolled task filters;
  - planning-calibration output surfaces now reuse the same clean task
    primitive before exposure filtering;
  - deadline-shape outcomes now require clean stopwatch evidence and exclude
    dirty, repaired, auto-closed, corrected, retroactive, imported, voided, and
    incomplete execution rows.

Verification:

- backend targeted tests:
  - `backend/tests/test_analytics_deadline_shape.py`;
  - `backend/tests/test_output_surfaces.py::test_task_creation_nudge_lookup_emits_exposure_when_it_will_render`;
  - `backend/tests/test_output_surfaces.py::test_task_creation_nudge_lookup_excludes_dirty_personal_rows`;
  - `backend/tests/test_output_surfaces.py::test_product_surfaces_do_not_fall_back_to_operator_without_identity`;
  - `backend/tests/test_last_task_and_undo_scoping.py`;
  - result: `17 passed`.
- frontend build:
  - `npm run build`;
  - result: passed.
- public browser verification through an authenticated app account:
  - undo toast was visible after timer start with a `30s undo window`
    countdown;
  - clicking `UNDO` reverted the started task to `PLANNED`, cleared
    pre-task readiness/initiation metadata, removed the stopwatch session, and
    left no active timer;
  - Pulse stop modal showed focus, `Done %`, and `Scope`;
  - submitting `90%`, focus `4`, and `Expanded` persisted:
    - `Task.post_task_reflection=4`;
    - `Task.scope_outcome=expanded`;
    - `StopwatchSession.task_completion_percentage=90`;
  - exact synthetic verification task/session rows were deleted after proof.

Screenshots:

- `tmp/lyra-timer-undo-1780663900000/timer-start-undo-visible.png`;
- `tmp/lyra-timer-undo-1780663900000/timer-start-undo-clicked.png`;
- `tmp/lyra-wave-b-1780661587319/pulse-readiness-default.png`;
- `tmp/lyra-wave-b-1780661587319/pulse-reflection-controls.png`;
- `tmp/lyra-wave-b-1780661587319/pulse-early-confirm-values-persist.png`.

Important nuance:

```text
Wave B closes the current clean-measurement implementation pass for bias lookup,
insights/task-surface clean selection, deadline-shape filtering, and Pulse stop
field capture. Wave C provider/data-sovereignty work and Wave D formal exposure
registration remain open.
```

## Six-Agent Neutralization Verification - 2026-06-05

Status: verification report only.
May authorize code: false.
Runtime owner: none.

Scope:

- the original K01-K05 and B01-B10 bug hunt classes;
- the two attached hidden-bug-class prompts:
  - Redis/Postgres concurrency fractures;
  - temporal boundary tearing;
  - provider backpressure;
  - local cache/polling failure modes;
  - scheduler idempotency/stale reads;
  - denominator/operator/test contamination;
  - soft-delete leakage;
  - unit/time-source mismatch;
  - optimistic/multi-tab races;
  - partial transactions;
  - cache-key collisions;
  - not-instrumented-as-zero;
  - dashboard self-contamination;
  - over-strict cleanliness.

Screenshot hygiene:

```text
All new verification screenshots for this pass must live under repo tmp/.
Do not save or document new screenshots under C:\Users\...\Temp.
```

The previous Wave A screenshots were moved into:

- `tmp/lyra-wave-a-1780658138440/pulse-wave-a.png`
- `tmp/lyra-wave-a-1780658138440/stale-resolution-modal.png`

### Executive Result

The visible Wave A failures are neutralized for the tested web path, but the
broader bug classes are not fully neutralized.

```text
User-facing notification leaks: mostly neutralized.
Stale-pause reflection UX: neutralized for the seeded Pulse path.
Clean measurement integrity: still occurring.
Provider/data sovereignty: still occurring.
Brain-dump/idempotency loop: still occurring.
Temporal/deploy reliability: still occurring.
```

The highest-risk remaining pattern:

```text
The app often looks correct while Lyra's measurement belief about reality can
still become wrong.
```

### Agent 1 - Notifications, Exposure, Scheduler Outputs

| Bug class | Status | Evidence | Required verification |
|---|---|---|---|
| Web fetch drains before render | Neutralized | Web delivery uses peek/ack: `backend/app/api/v1/endpoints/notifications.py`, `backend/app/services/notification_queue.py`. | Browser/API: repeated `/web/pending` polls do not remove queued prompts until ack. |
| Operator alert web leakage | Neutralized | `operator_alert` is filtered from web-visible notifications and preserved for OpenClaw. | Browser: seed `operator_alert`; verify Pulse/Today show nothing. |
| Pulse/app notification host | Neutralized | App shell mounts `AppNotificationHost`; Pulse receives queued web notifications without Today. | Browser route on `/pulse`, not `/today`. |
| Raw float / OpenClaw copy web leak | Neutralized | Timer overflow web copy ignores raw payload message and formats integer minutes. | Browser: seed raw-float/`Reply with` payload. |
| Ack before actual display | Neutralized | Wave 1 app-shell host acks only mounted web toasts as rendered and marks unsupported web payloads `lost_unrendered`. | Keep lifecycle browser regression. |
| Queued/rendered/acted/dismissed lifecycle separation | Neutralized | Wave 1 added durable lifecycle rows and operator dashboard counts. | Keep lifecycle state-machine tests. |
| Timer overflow output surface | Neutralized | Wave 1 registered `worker.timer_overflow` and separates web event from operator/OpenClaw alert. | Keep timer-overflow output-surface regression. |
| Timer overflow duplicate durability | Neutralized | Wave 1 dedupe checks DB lifecycle rows, not Redis/process memory only. | Keep restart/Redis-clear regression. |
| Pause/resume duplicate prompts | Neutralized | Pause/resume prediction logs use durable DB cooldown/caps. | Keep restart-simulation regression optional. |

Agent test note:

- Targeted notification/exposure scheduler tests passed: `48 passed`.

### Agent 2 - Stopwatch, Re-entry, Cache Invalidation

| Bug class | Status | Evidence | Required verification |
|---|---|---|---|
| Stale recovery incomplete `EXECUTED` truth | Neutralized | Old paused sessions are left for user resolution; stale resolution stamps execution interval and dirty flag. | Add exact assertion for `executed_start_utc` / `executed_end_utc` after resolution. |
| User-resolved stale pause clean-calibration exclusion | Neutralized | `data_quality_flag=user_resolved_stale_pause`; Cortex clean session gate excludes dirty rows. | Keep clean-profile regression. |
| Redis-active stale pauses | Neutralized | Wave 2 moves the Redis-active skip after stale-paused eligibility; `73h` Redis-active paused sessions are left open for user resolution. | Keep seeded Redis-active `73h` worker regression. |
| Task-range/evidence cache invalidation | Neutralized for known state paths | Wave 2 invalidates ranges after task start/complete/skip/delete/swap/reschedule, direct void/abandon, LLM binding correction, deadline mutations, and stale/orphan workers. | Keep mutation-edge invalidation tests and browser stale-card regression. |
| K03 invalid mark-done on `EXECUTED` | Neutralized for current re-entry path | Wave 2 broadens stale backend rejection handling and range invalidation; Wave A/Wave 2 browser fixtures keep `EXECUTED` rows out of the re-entry queue. | Keep warm-cache browser regression. |
| K04 stale pause UX | Neutralized for current re-entry path | Wave 2 verifies 30m/8h/25h/73h age tiers and required stale-resolution modal fields. | Keep Wave 2 browser fixture. |
| 72h and 80% boundaries | Neutralized | Wave 2 tests cover `71h59m`, exact `72h`, `79%`, and `80%`. | Optional: add `72h+1s` and `81%` snapshots if future refactor touches thresholds. |
| Double-tap / multi-tab idempotency | Neutralized for current stopwatch/re-entry paths | Wave 2B added endpoint idempotency keys plus convergent no-op behavior for same-task start, duplicate pause/resume, stop retry, and narrow retroactive mark-done replay. | Keep Wave 2B endpoint and browser idempotency regressions. |

Agent test note:

- Targeted stale-pause/state/idempotency tests passed: `36 passed`.

### Agent 3 - Measurement Cleanliness And Operator Dashboard

| Bug class | Status | Evidence | Required verification |
|---|---|---|---|
| Exposure firewall primitive | Neutralized | Rendered relevant exposure dirties baseline; suppression stays clean; Cortex baseline excludes exposed tasks. | Keep exposure-ledger regression tests. |
| Bias lookup dirty personal evidence | Neutralized | Wave B routes bias lookup through shared planning-calibration clean evidence. | Keep no-stopwatch/auto-closed/dirty/corrected/exposed regression. |
| Insights clean-profile overclaim | Neutralized for current planning surfaces | Wave B routes planning-calibration output surfaces through clean task selection before exposure filtering. | Keep imported/retroactive/auto-closed/dirty-session regression. |
| Deadline-shape clean profile | Neutralized | Wave B default deadline-shape filtering excludes dirty, repaired, auto-closed, corrected, retroactive, imported, voided, and provider-only rows. | Keep dirty `TaskDeadlineOutcome` regression. |
| Dashboard denominator semantics | Still occurring | `clean_trace_ratio` denominator differs from dirty-reason populations such as exposure/provider counts. | Every dashboard rate needs numerator/denominator profile metadata. |
| Operator exclusion in aggregates | Still occurring | Non-operator users are selected, but exposure/provider aggregate queries are global in places. | Seed operator-only exposure/provider rows; cohort metrics must not change. |
| Voided/deleted/test/synthetic rows | Still occurring | `DELETED` rows and synthetic non-operator users are not consistently excluded or surfaced. | Seed deleted/synthetic rows and assert exclusion or explicit bucket. |
| `exposure_contaminated` dashboard count | Still occurring | Dashboard counts render events, not contamination joined to matching sessions/tasks. | Seed unrelated render row; count should remain 0 until linked contamination exists. |
| Shared clean-profile primitive usage | Neutralized for Wave B surfaces | Bias lookup, planning-calibration surfaces, and deadline-shape filtering now use shared clean gates where implemented. | Wave 4 still needs dashboard denominator/dynamic issue proof. |
| Metric confidence honesty | Still occurring | Some local/mismatched metrics still report high confidence; frontend hides some not-instrumented detail. | Incomplete/local metrics cannot claim `high`; UI must show instrumentation gaps. |

Concrete exposure trace:

1. `/analytics/insights` calls `emit_surface_render()`.
2. That writes `ExposureDecisionEvent` and `ExposureRenderEvent` with category
   `behavioral_insight`.
3. A later task inside the policy window is marked `EXPOSED` by the exposure
   ledger.
4. Cortex baseline excludes it correctly.
5. Operator dashboard does not yet trace render rows to task/session
   contamination, so `exposure_contaminated` can overcount or misclassify.

Agent test note:

- Targeted measurement tests passed: `55 passed`.

### Agent 4 - Providers, Integrations, Data Sovereignty

| Bug class | Status | Evidence | Required verification |
|---|---|---|---|
| Provider provenance marking | Neutralized | Deadlines carry `external_source`/`imported_at`; completion events carry provenance; pressure map separates external load. | Browser check that `moodle_ws_backfill` displays as external Moodle source. |
| Moodle iCal/WS SSRF/private URL/redirect guard | Backend neutralized; browser pending | Shared provider URL guard validates resolved targets and redirect hops before Moodle iCal/WS requests. | Browser: unsafe Moodle URL fails safely without leaking raw URL/token. |
| Google refresh token + Moodle iCal encryption | Backend neutralized | Google refresh tokens and Moodle iCal URLs store Fernet-prefixed; legacy plaintext rewrites encrypted on read. | DB assertions passed for encrypted storage and legacy fallback. |
| Provider facts becoming canonical truth | Backend neutralized; browser pending | Moodle WS now records completion candidates instead of setting canonical completed state. | Browser: submitted Moodle evidence does not auto-complete user deadline. |
| Native/imported duplicate deadlines | Backend neutralized; browser pending | External import upsert/backfill skips native same-title/same-day duplicates. | Browser/API: native/imported duplicate is prevented or surfaced. |
| Terminal deadline binding correction | Backend neutralized; browser pending | Correction endpoint now rejects non-bindable terminal deadlines. | Regression passed for completed/missed/skipped deadline binding correction. |
| Export completeness | Neutralized; browser passed | Registry-backed export includes user-owned data sections and integration-state summary without raw secrets. | Export registry/completeness test. |
| Delete completeness + Redis purge | Neutralized; browser passed | Delete uses registry helpers and purges user-scoped Redis runtime state. | Delete test with Redis keys: notifications, stopwatch, gcal, me, task ranges. |
| Provider sync backpressure | Still occurring | Per-request timeouts exist, but per-user sync loops lack wall-clock cap/circuit breaker. | Stress test blackholed URLs plus many users. |

Agent test note:

- Focused provider/delete/deadline tests passed: `96 passed` plus `3`
  deadline-binding correction tests.

### Agent 5 - Temporal, Unit, Deploy Reliability

| Bug class | Status | Evidence | Required verification |
|---|---|---|---|
| Timer overflow web copy/formatting | Neutralized | Web overflow copy formats integer minutes and excludes operator reply text. | Browser trigger remains useful. |
| Stale paused auto-execution | Neutralized | Current stale job leaves old paused sessions open for user resolution. | Keep stale-pause modal browser smoke. |
| UTC/local conversion centralization | Still occurring | Central helper exists, but callers still use naive UTC and caller-side stripping. | Aware Supabase-style datetimes, local-midnight, non-Cairo tests. |
| Query/date-range local boundaries | Still occurring | Omitted `date_to` uses UTC now as if local; responses emit local ISO without offset. | Freeze around Cairo midnight; compare inclusion. |
| Rollover session daily bucketing | Still occurring | Pulse buckets whole executed duration by executed-end day; pressure/capacity do not split cross-midnight blocks. | Seed 23:30-00:30 and assert 30/30 split where required. |
| Frontend/backend overdue alignment | Still occurring | Frontend parses naive local strings in browser timezone; Today has Cairo assumptions. | Playwright in Cairo and non-Cairo browser timezones. |
| Worker naive-aware datetime hazards | Still occurring | Workers still compare/subtract raw ORM datetimes; scheduler has no explicit timezone. | Seed aware DB datetimes and run workers. |
| Redis-active stale pause escape | Still occurring | Same B05 issue: stale recovery skips Redis-active sessions. | Seed active paused >72h; run job. |
| Duration unit centralization | Still occurring | API/schema still mix seconds, int minutes, and float pause minutes; frontends have local formatters. | Unit snapshot tests; fractional pause overflow regression. |
| Static chunk/deploy cache reliability | Still occurring | Topology scripts help deploy correctness, but Next/Cloudflare cache headers and old-tab chunk recovery are not handled. | Keep old tab across deploy; request stale chunk; verify graceful reload/no 400. |

### Agent 6 - Frontend Product Loop, Brain Dump, Cache, Feedback

| Bug class | Status | Evidence | Required verification |
|---|---|---|---|
| Quick-capture anchor | Neutralized | Pulse has stable `#quick-capture`; Today empty-state link points to `/pulse#quick-capture`; Wave A browser pass verified. | Route from Today empty-state to Pulse anchor. |
| Polling/zombie loops | Neutralized | React Query hosts polling; manual intervals clear on unmount. | Route-churn network test for duplicate polls. |
| In-app feedback end-to-end | Neutralized | Shell link, modal, backend submit/admin/resolve endpoints, and tests exist. | Browser submit feedback and verify operator view row. |
| Brain-dump double-create idempotency | Neutralized | Wave 3 adds user-scoped commit idempotency and browser verifies commit headers. | Keep backend replay regression and browser retry fixture. |
| Brain-dump partial failure recovery | Neutralized | Wave 3 preserves failed item text, offers edit/retry, and verifies no retyping path in browser. | Keep mixed valid/failed commit browser test. |
| Obligation binding dropoff telemetry | Still occurring | Accepted bindings commit; rejected/ignored suggestions are not fully instrumented as product-loop degradation. | Track suggested/accepted/rejected/dismissed bindings. |
| Pressure-map safe mode | Neutralized | Wave 3 removes frontend fallback preview and browser-verifies no create controls when `recovery_options=[]`. | Keep safe-mode browser test: no preview/lock-in when `recovery_options=[]`. |
| React Query persisted cache scoping | Still occurring | Persisted cache key is global; query keys often omit user id and rely on signout clearing. | Two-user same-browser cache poisoning test. |

## Neutralized Vs Still Occurring Summary

Neutralized enough for current dogfood/browser path:

- K01 web calendar/operator alert leak;
- K02 web timer overflow raw float and `Reply with` copy;
- app-shell notification host for Pulse/Today;
- K04 stale-pause reflection modal for the seeded path;
- stale-pause user resolution marks dirty calibration rows;
- Redis-active stale pauses surface for explicit user resolution instead of
  hiding behind stale recovery;
- range/evidence freshness for known task/session/deadline mutation paths;
- exact `72h` stale-pause and `80%` completion boundaries;
- notification lifecycle separation and timer-overflow output-surface
  registration;
- durable timer-overflow duplicate prevention;
- bias lookup, insights/planning surfaces, and deadline-shape clean gates;
- exposure firewall primitive inside Cortex;
- provider provenance marking;
- quick-capture anchor;
- in-app feedback submission path;
- app-level polling cleanup in normal route changes;
- brain-dump commit idempotency;
- brain-dump partial-failure edit/retry without retyping;
- Pressure Map safe-mode frontend authority;
- recovery-plan soft-conflict `Create anyway` path when backend permits.

Still occurring and cohort-relevant:

- stopwatch/mark-done paths lack request idempotency for double-tap/multi-tab
  races;
- dashboard denominator/operator/test/synthetic contamination risks remain;
- `exposure_contaminated` dashboard counts render rows rather than joined
  contaminated task/session rows;
- provider URL SSRF guards, credential encryption, export/delete registry,
  Redis purge, provider truth, and duplicate imports are backend-fixed but
  still need browser verification and Wave 6 readiness proof;
- local/UTC/naive-aware time boundaries and rollover sessions remain unsafe;
- persisted frontend cache is not user-scoped by key.

Unknown or insufficiently proven:

- multi-tab stopwatch races under real browser concurrency;
- old-tab/static-chunk behavior across deployment;
- non-Cairo browser timezone behavior;
- dashboard side-effect freedom under all operator paths.

## Revised Priority After Six-Agent Verification

Do not broaden features. Fix in this order:

1. Operator dashboard and dynamic issues:
   - dynamic invariant-derived issues instead of static K-tags;
   - explicit dashboard denominators and operator/test/synthetic exclusion;
   - dashboard read-side-effect proof.
2. Remaining idempotency:
   - stopwatch start/pause/resume/stop;
   - mark done/drop/swap paths.
3. Data sovereignty:
   - export/delete registry and Redis purge;
   - user-owned data completeness.
4. Provider security and integrity:
   - SSRF protection;
   - credential encryption;
   - provider provenance/duplicate import truth boundary;
   - terminal-provider truth confirmation.
5. Temporal reliability:
   - timezone boundary tests;
   - rollover splitting or explicit bucketing doctrine;
   - aware/naive worker tests;
   - deploy stale-chunk mitigation.

## Bug-Fix Waves

Historical wave labels from the first bug-hunt pass. The current execution
sequence is the Wave 1-6 closure plan documented above; do not use this section
as the live next-step order.

### Wave A - Browser Verify Implemented K01-K04

Status: passed on 2026-06-05.

Definition of done:

- calendar refresh warning never appears as web technical alert;
- timer overflow web toast appears once, with integer minutes and no `Reply`;
- executed tasks never show missed-plan mark-done cards;
- `>=72h` paused task opens stale-resolution reflection modal;
- Pulse receives queued notifications without visiting Today.

### Wave B - Measurement Cleanliness

Status: implemented and targeted/browser verified on 2026-06-05.

Fix:

- bias lookup uses the shared planning-calibration clean primitive;
- insights use clean-profile selection;
- deadline-shape outcomes exclude dirty/repaired/auto-closed/corrected rows;
- Pulse stop flow captures focus, completion percent, and scope.

### Wave C - Provider And Data Sovereignty

Status: split and implemented as Wave 5A (data sovereignty) and Wave 5B
(provider security/integrity). Browser verification remains pending for Wave
5B provider UI/error surfaces.

Fix:

- private/loopback/link-local/metadata URL rejection for provider fetches;
- credential encryption for Google refresh tokens and Moodle iCal URLs;
- export/delete central registry;
- Redis runtime purge on delete;
- native/imported duplicate deadline prevention or explicit surfacing.

### Wave D - Exposure Registration

Fix:

- timer overflow registered or classified as operational-only;
- queued notification decision, render, dismiss, and action states are separated;
- no exposure row is treated as rendered before user-visible display.

## Audit Conditions

- Branch: `feature/evidence-packet-claim-compiler`.
- Worktree was already dirty before this documentation pass.
- Existing dirty runtime mitigations were treated as present but not durable
  until committed and deployed:
  - web notification channel filtering;
  - timer overflow user copy integer formatting;
  - Pulse reentry stale-card refresh/dismiss mitigation;
  - targeted tests for notification queue and timer overflow copy.
- This audit did not commit, push, merge, deploy, run migrations, or implement
  new fixes.

## Cohort Readiness Verdict

No for a larger 15-20 user cohort today.

Yes after fixes if the minimal gate is completed:

1. Add dynamic operator issues and dashboard side-effect proof.
2. Close data-sovereignty blockers: export/delete registry and Redis runtime
   purge.
3. Close provider/security blockers: Moodle URL SSRF guard, credential
   encryption, provider provenance, and duplicate-import handling.
4. Browser-verify the final green cohort gate from both Codex and user
   accounts.

## Top Critical / High Bugs

### B01 - Notification delivery drains before render

Severity: Critical  
Category: exposure / recovery prompt delivery

`GET /v1/notifications/pending` drains the Redis queue. Today then renders
pause/resume prediction banners only if current stopwatch state matches local
gates. A notification can be consumed and never shown.

Files:

- `backend/app/api/v1/endpoints/notifications.py`
- `backend/app/services/notification_queue.py`
- `frontend/app/(app)/today/page.tsx`

Root cause:

```text
delivery == fetch, not rendered/acked exposure
```

Minimal fix:

- Add durable notification IDs.
- Change web delivery to peek or reserve.
- Add explicit `rendered` / `dismissed` ack endpoints.
- Do not remove recovery predictions until rendered or intentionally dismissed.

Browser test:

1. Queue a resume prediction for task A.
2. Set stopwatch status to task B.
3. Load Today.
4. Verify the notification is not lost.
5. Restore matching status and verify it can still render.

Blocks cohort: yes.

### B02 - Pulse does not host queued notifications

Severity: High  
Category: re-entry / notification surface

Today is the notification host. Pulse is now the command center, but Pulse does
not poll pending notifications. A user who lives in Pulse may never see queued
timer overflow, reminder, pause, or resume prompts.

Files:

- `frontend/app/(app)/pulse/page.tsx`
- `frontend/app/(app)/today/page.tsx`
- `frontend/lib/tasks.ts`

Minimal fix:

- Move notification hosting to the app shell, or add a shared host used by Pulse
  and Today.
- Use one delivery/ack primitive so rendering is not duplicated.

Browser test:

- Mock one reminder and one timer overflow while on `/pulse`.
- Verify both render once and dismiss correctly.

Blocks cohort: yes.

### B03 - Timer overflow is partly fixed but still exposure-unsafe

Severity: High  
Category: timer / alert / measurement

Observed bug:

```text
345.82404850000967 min
Reply with 'done'
duplicate [alert] scheduler copy
```

Current dirty worktree:

- user web copy now rounds to integer active minutes;
- user copy no longer says "Reply with";
- operator copy still uses reply-oriented OpenClaw text;
- timer overflow still has no output surface/exposure render accounting.

Files:

- `backend/app/workers/jobs/timer_overflow.py`
- `backend/app/services/notification_queue.py`
- `backend/app/services/operator_notifier.py`

Remaining root cause:

```text
timer overflow is both a user recovery surface and an operator incident surface,
but the code treats both as one queue family.
```

Minimal fix:

- Register timer overflow in the output surface registry.
- Create one user-facing event with user copy.
- Create one operator incident event with operator copy.
- Give both stable IDs and Redis/process-independent dedupe.

Browser test:

1. Start a planned 5-minute task.
2. Advance time past threshold.
3. Verify one user toast only.
4. Verify copy has integer minutes and no "Reply with".
5. Verify operator alert appears only in the operator channel.

Blocks cohort: yes.

### B04 - Stale session recovery can create incomplete EXECUTED truth

Severity: High  
Category: stopwatch / execution integrity

Stale recovery can set a task to `EXECUTED` and set
`executed_duration_minutes`, but not set `executed_start_utc` or
`executed_end_utc`.

Files:

- `backend/app/workers/jobs/stale_session_recovery.py`
- `backend/app/workers/jobs/reconcile_deadline_outcomes.py`
- `backend/app/services/task_manager.py`

Impact:

- deadline outcome reconciliation requires `executed_end_utc`;
- correction flows can reject tasks without execution timestamps;
- analytics may count duration while other systems cannot locate the execution
  interval.

Minimal fix:

- If stale recovery marks a task `EXECUTED`, also set execution start/end fields
  from the recovered session.
- Mark the recovered task/session dirty enough that it cannot enter clean
  calibration unless explicitly confirmed.

Test:

- Age a paused open session beyond stale threshold.
- Run stale recovery.
- Assert task state, duration, executed timestamps, `auto_closed`, and clean
  profile exclusion.

Blocks cohort: yes.

### B05 - Redis-active stale pauses can evade stale recovery

Severity: High  
Category: parked work / forgotten timers

Stale session recovery skips the Redis active session before applying the
48-hour stale threshold. A paused session can therefore remain open if Redis
still marks it active.

Files:

- `backend/app/workers/jobs/stale_session_recovery.py`
- `backend/app/utils/redis_client.py`

Observed product shape:

```text
AI Bdaya - Parked for 25h 33m during an interruption chain.
```

This is useful at moderate age, but old parked work needs tiers:

- recent: immediate re-entry;
- same-day old: re-entry with drop/reschedule options;
- overnight/very old: review/resolve, not pressure.

Minimal fix:

- Allow recovery for Redis-active paused sessions beyond threshold.
- Clear Redis atomically when stale recovery acts.
- Add age-tiered re-entry copy and priority.

Blocks cohort: yes.

### B06 - Task range cache keeps stale recovery state alive

Severity: High  
Category: stale UI / invalid actions

`tasks_range_cache.py` explicitly says it does not bust on state transitions.
Pulse now uses task state directly for re-entry, focus totals, charts, and
missed-plan cards. Sixty seconds of stale state is visible and actionable.

Files:

- `backend/app/utils/tasks_range_cache.py`
- `backend/app/api/v1/endpoints/query.py`
- `frontend/app/(app)/pulse/page.tsx`
- `frontend/components/pulse/PulseReentryQueue.tsx`

This is the most plausible root cause behind:

```text
Only PLANNED or SKIPPED overdue tasks can be marked done this way
(current state: EXECUTED).
```

Minimal fix:

- Invalidate user task ranges after:
  - stopwatch start/pause/resume/switch/stop;
  - mark done;
  - skip/void;
  - stale/orphan recovery;
  - deadline binding correction;
  - missed-plan recovery actions.

Browser test:

1. Warm `/tasks/query`.
2. Mark a task done.
3. Return to Pulse re-entry.
4. Verify no stale missed-plan action remains.

Blocks cohort: yes.

### B07 - Pressure Map can bypass read-only safe mode

Severity: Critical if safe mode is used  
Category: authority / silent mutation prevention

Backend read-only pressure mode suppresses recovery options. Frontend can still
show fallback `Preview focus blocks` from pressure items and create blocks.

Files:

- `backend/app/core/kill_switches.py`
- `backend/app/services/academic_pressure.py`
- `frontend/components/pulse/PulseAcademicPressureMap.tsx`

Root cause:

```text
frontend derives mutability from pressure items instead of backend-authorized
recovery options
```

Minimal fix:

- Do not render preview/lock-in unless backend returns an explicit
  `create_plan` or `split_into_blocks` recovery option.

Blocks cohort: yes if safe mode is part of launch control.

### B08 - Bias lookup can use dirty personal evidence

Severity: High  
Category: calibration / estimate validity

`/analytics/bias_factor/lookup` builds task candidates with hand-rolled filters
and does not require a clean stopwatch/session provenance before passing tasks
to `blend()`.

Files:

- `backend/app/api/v1/endpoints/analytics.py`
- `backend/app/services/bias_factor_service.py`
- `backend/app/services/cortex.py`

Risk:

- new-task estimates and recovery plan blocks can be shaped by repaired,
  auto-closed, no-stopwatch, or dirty session rows;
- accepted intervention outcomes are then exposed and excluded, compounding the
  calibration problem.

Minimal fix:

- Use `planning_calibration_query()` plus exposure filtering as the candidate
  source.
- Add tests for no-stopwatch and auto-closed rows.

Blocks cohort: yes for estimate/occupancy trust.

### B09 - Insights clean-profile metadata can overstate cleanliness

Severity: High  
Category: insights / research validity

Insights advertise planning-calibration style cleanliness but select tasks
through local endpoint filters plus exposure filtering, not through the full
Cortex clean-profile primitive.

Files:

- `backend/app/api/v1/endpoints/analytics.py`
- `backend/app/services/cortex.py`
- `backend/app/core/output_surface_registry.json`

Minimal fix:

- Create one shared primitive:

```text
candidate_tasks_for_surface(user_id, surface_id)
```

- Use it for insights, bias lookup, deadline shape, and archetype proximity.

Blocks cohort: yes for research/insight claims, not for raw task tracking.

### B10 - Data sovereignty surfaces are incomplete

Severity: High  
Category: export/delete/privacy

Export returns only a narrow subset: user, tasks, stopwatch sessions, and
archetype assignments. It omits deadlines, pause events, feedback, external
event outcomes, exposure logs, email engagement, and integration state.

Delete purges many DB rows but does not clearly purge Redis runtime state:
pending notifications, active stopwatch keys, `/me` cache, task-range cache.

Files:

- `backend/app/api/v1/endpoints/users.py`
- `backend/app/services/notification_queue.py`
- `backend/app/utils/redis_client.py`
- `backend/app/utils/tasks_range_cache.py`
- `backend/app/utils/me_cache.py`
- `frontend/app/(app)/settings/page.tsx`

Minimal fix:

- Create a central user-owned data registry.
- Drive export and delete from that registry.
- Add runtime-state purge for Redis keys.

Blocks cohort: yes if export/delete is promised to trusted users.

## Known Issue Investigations

### K01 - Calendar Sync Warning Copy And Alert Routing

Observed:

```text
[warn] [calendar.sync] Google Calendar token refresh failed...
Affected user scope: user#...
Data integrity risk: No tasks, deadlines, or calendar events are written...
```

Current behavior:

- Calendar refresh failure only calls `notify_operator()` when
  `user.is_operator`.
- The long text is operationally useful but not user appropriate.
- The web UI previously drained the OpenClaw/operator queue, so operator
  payloads could render in product toasts.
- Current dirty worktree adds `channel=web` and filters `operator_alert`, but
  `/pending` still defaults to `openclaw`.

Root cause:

```text
OpenClaw operator alerts and web notifications share a queue family.
```

Fix direction:

- Split endpoints or require explicit channel with no default.
- Keep calendar diagnostics operator-only.
- If the user must act, render a short Settings-integrations warning:

```text
Calendar could not refresh. Reconnect if this keeps happening.
```

Browser verification:

1. Force Google token refresh failure for operator.
2. Open Pulse and Today.
3. Verify no `[calendar.sync]` technical alert appears.
4. Verify Settings still lets the user reconnect.
5. Verify OpenClaw/operator receives the diagnostic.

### K02 - Timer Overflow Duplicate + Raw Float

Observed:

```text
'Lyra waves' has been running for 345.82404850000967 min...
[alert] [scheduler.timer-overflow] ...
```

Current dirty worktree:

- user copy now uses integer active minutes;
- user copy no longer says reply;
- operator copy is still reply-oriented;
- operator account can still receive both user payload and operator alert;
- no exposure render exists for timer overflow.

Root cause:

```text
timer overflow crosses three surfaces: web user, OpenClaw operator, and
measurement exposure, but only the queue/dedupe layer knows about it.
```

Fix direction:

- Separate user and operator payload classes.
- Add durable event ID.
- Add output surface registration and render ack.
- Redis dedupe key should be stable across processes.

Browser verification:

1. Trigger one timer overflow.
2. Confirm exactly one web toast.
3. Confirm no raw float.
4. Confirm no "Reply with" on web.
5. Confirm operator-only channel gets the operational alert.

### K03 - Invalid Mark-Done On EXECUTED Task

Observed:

```text
Only PLANNED or SKIPPED overdue tasks can be marked done this way
(current state: EXECUTED).
```

Current behavior:

- Backend correctly rejects retroactive done for EXECUTED tasks.
- Pulse re-entry can still display stale candidates from task evidence/range
  data.
- Current dirty worktree invalidates `tasks-evidence` and dismisses the card
  after this rejection.
- Root stale-data source remains: range cache and state-transition invalidation.

Fix direction:

- Align frontend eligibility exactly with backend:
  - only PLANNED overdue;
  - or SKIPPED/abandoned;
  - no execution data;
  - not voided;
  - current state checked at action time.
- Bust range/evidence cache on every state transition.
- On rejection, refetch before showing an error.

Browser verification:

1. Create a missed planned task.
2. Execute it through another path.
3. Return to Pulse without hard refresh.
4. Verify no missed-plan card remains.

### K04 - Parked 25h Interruption Chain

Observed:

```text
AI Bdaya - Parked for 25h 33m during an interruption chain.
```

Current behavior:

- Recent parked work is useful.
- Very old parked work is still presented as immediate re-entry.
- UI copy says paused work auto-closes after 12 hours.
- Actual stale recovery threshold is 48 hours.
- Redis-active paused sessions are skipped by stale recovery.
- Stale recovery can auto-mark EXECUTED without execution timestamps.

Fix direction:

- Align copy with actual policy.
- Add age tiers:
  - under 2h: pick back up;
  - same day: pick up / reschedule / drop;
  - overnight: review open thread;
  - beyond stale threshold: resolve before normal work.
- Treat stale recovery rows as dirty unless user confirms.

Browser verification:

1. Seed paused sessions at 30m, 8h, 25h, 49h.
2. Verify different copy/priority.
3. Verify old paused work never becomes clean execution evidence without user
   confirmation.

### K05 - Pulse Quick-Capture Anchor

Observed request:

```text
Brain dump hyperlink should point to capture at the bottom/top of Pulse,
not the Today tab.
```

Current behavior:

- `PulseQuickCaptureV2` renders near the top of Pulse.
- It uses `id="quick-capture"`.
- `PulseTodaysPlanV2` empty-state link points to `/pulse#quick-capture`.
- Capture shrinks when an active timer exists.
- Stale tutorial/onboarding/docs still mention `/today` as the brain-dump
  landing path.

Fix direction:

- No runtime blocker in Pulse.
- Remove or mark stale tutorial/onboarding copy.
- Browser check anchor scroll after route navigation.

Browser verification:

1. Open `/pulse#quick-capture` from another route.
2. Verify focus/scroll lands at quick capture.
3. Start a timer.
4. Verify quick capture shrinks but remains usable.

## Agent Report Synthesis

### Agent 1 - User-Facing Product Loop

Top findings:

- Pressure Map can create recovery blocks in read-only pressure safe mode.
- Recovery card displays `Confirm coverage` while the action opens create-plan
  preview.
- Partial brain-dump failures are visible but not recoverable without retyping.
- Pulse timer stop flow omits completion percentage/scope outcome while Today
  captures them.
- Recovery-plan soft conflicts lack `create anyway`.

### Agent 2 - Timer / Stopwatch / Pause / Re-entry

Top findings:

- Stale recovery can set EXECUTED without execution timestamps.
- Redis-active stale paused sessions can evade recovery.
- Stop/switch paths need the same negative-pause clamp as resume.
- Task-range cache is stale after state transitions.
- Paused-parent ordering and parent selection are nondeterministic.

### Agent 3 - Measurement Integrity

Top findings:

- Insights bypass full Cortex clean-profile enforcement.
- Bias-factor lookup can use dirty personal evidence.
- Deadline-shape outcomes can include repaired/dirty outcomes.
- `bias_factor_observed` in deadline shape uses signed-delta semantics and can
  invert the canonical bias factor meaning.
- Archetype proximity metadata does not match actual duration-ratio inputs.

### Agent 4 - Provider / Integration / Binding

Top findings:

- Deadline binding correction allows terminal deadlines.
- Moodle WS-backfilled deadlines can look native in some UI surfaces.
- Native and imported duplicate deadlines can coexist.
- Moodle connect can report clean success while sync failed.
- Moodle completion copy overclaims "when you submit"; code also uses grade and
  sync-time fallback.

### Agent 5 - Exposure / Notification / Nudge

Top findings:

- Web notifications drain before actual render.
- Pulse does not host queued notifications.
- Exposure ledger can count queued events as rendered, while timer overflow is
  not counted at all.
- Pause actions default research-relevant pause reasons in some UI paths.
- Operator mirroring can become noisy and surveillance-shaped even if redacted.

### Agent 6 - Data Integrity / Production Readiness

Top findings:

- Moodle URL fetch paths need SSRF protection.
- Export is incomplete relative to user-facing promises.
- Delete does not clearly purge Redis runtime state.
- Email engagement rows are not clearly exported/deleted.
- Google refresh tokens and Moodle iCal URLs are plaintext at rest.
- No cohort allowlist gate exists if public sign-in remains open.

## Measurement Integrity Risks

Top 10:

1. Bias lookup uses hand-rolled filters instead of clean planning calibration.
2. Insights use exposure filtering but not full clean-profile primitives.
3. Timer overflow produces user behavior-shaping output without exposure render.
4. Notification queue drain can make exposure logs disagree with actual render.
5. Stale recovery can create task execution duration without execution interval.
6. Auto-closed/repaired rows can leak into deadline-shape outcomes.
7. Pulse stop omits completion percentage/scope outcome.
8. Pause reasons are defaulted in some UI paths.
9. Native/imported duplicate deadlines can inflate pressure and split bindings.
10. User email engagement is not integrated into export/delete governance.

## User-Facing Bug Risks

Top 10:

1. Technical operator warnings can appear in product alerts if channel routing
   regresses.
2. Timer overflow can be duplicated across user/operator contexts.
3. Missed-plan cards can expose invalid actions for already executed tasks.
4. Pulse users can miss queued notifications entirely.
5. Pressure Map can offer a plan while showing coverage-confirmation copy.
6. Partial brain-dump failures are not actionable.
7. Old parked work can feel like pressure instead of recovery.
8. Recovery-plan conflicts dead-end without force-create.
9. Moodle connect can say success despite sync error.
10. Stale tutorial/onboarding copy points brain-dump context back to Today.

## State Machine Risks

Invariants to protect:

```text
One task may be actively executing per user.
Paused parent sessions may remain open, but must be explicitly recoverable.
Executed tasks must have coherent execution duration and execution interval.
Auto-repaired sessions must not become clean measurement rows.
UI recovery actions must be valid against current backend state.
```

Highest-risk paths:

- `stale_session_recovery.py`
- `stopwatch_manager.py`
- `tasks_range_cache.py`
- `PulseReentryQueue.tsx`
- `today/page.tsx`

## Provider / Integration Risks

Provider facts must stay provider facts until confirmed or explicitly marked as
external.

High-risk violations:

- Moodle fetch URLs are not network-safe enough for public users.
- Moodle/iCal credentials are stored plaintext in some paths.
- Moodle WS backfill provenance is hidden in UI.
- Native/imported duplicate deadlines inflate pressure.
- Binding correction can attach tasks to terminal deadlines.

## Exposure / Notification Risks

Current notification architecture mixes four meanings:

1. user-facing recovery prompt;
2. operator incident;
3. queued but unseen item;
4. rendered behavior-shaping exposure.

Those need separate state.

Minimal target:

```text
decision created -> queued/reserved -> rendered -> acted/dismissed/expired
```

Do not treat `queued` as `rendered`.

## Data Integrity / Multi-User Risks

No broad ORM scoping collapse was found. The bigger risks are:

- raw SQL export/delete completeness;
- Redis runtime residue after deletion;
- credential plaintext at rest;
- URL fetch safety;
- no invite/allowlist gate for a controlled cohort.

## Minimal Fix Plan

### Gate 0 - Stop User/Operator Notification Confusion

- Split web and OpenClaw endpoints, or require explicit channel.
- Move notification host to app shell or Pulse + Today shared host.
- Add render/dismiss ack.
- Register timer overflow as an output surface.
- Browser verify K01 and K02.

### Gate 1 - Stabilize Re-entry And Timer State

- Bust range/evidence cache on all state transitions.
- Fix stale recovery timestamps and Redis-active stale pause handling.
- Align re-entry eligibility frontend/backend.
- Add parked-work age tiers.
- Browser verify K03 and K04.

### Gate 2 - Restore Clean Measurement Boundaries

- Bias lookup uses `planning_calibration_query`.
- Insights use shared clean-profile primitive.
- Deadline-shape excludes auto-closed/dirty/corrected rows.
- Pulse stop captures completion/scope like Today.

### Gate 3 - Provider And Data-Sovereignty Safety

- Add SSRF protection for Moodle/iCal/WS URLs.
- Encrypt Google refresh tokens and Moodle iCal URLs.
- Add central export/delete registry.
- Add Redis runtime purge on delete.
- Fix Moodle provenance and duplicate deadlines.

### Gate 4 - Product Loop Polish After Integrity

- Partial brain-dump retry/edit actions.
- Recovery-plan conflict override.
- Remove stale tutorial `/today` brain-dump copy.
- Copy neutralization snapshots.

## Browser Verification Checklist

Top 10:

1. K01: calendar refresh failure never renders technical operator text in web.
2. K02: timer overflow renders one web toast with integer active minutes.
3. K03: executed task never remains as missed-plan mark-done card.
4. K04: paused work at 30m, 8h, 25h, 49h shows age-appropriate recovery.
5. K05: `/pulse#quick-capture` scrolls to the quick capture bar.
6. Pulse notification host: queued reminder/overflow renders on Pulse.
7. Brain dump partial failure: user can recover failed item without retyping.
8. Pressure Map safe mode: no preview/lock-in controls when backend disables
   recovery options.
9. Pulse stop flow: completion percentage/scope outcome are saved.
10. Moodle provenance: `moodle_ws_backfill` renders as external Moodle source.

## Tests To Add

Top 10:

1. Web notification fetch does not drain unrendered recovery predictions.
2. Missing notification channel is rejected, or split endpoint is enforced.
3. Timer overflow exposure render/ack is recorded exactly once.
4. Stale recovery EXECUTED task has timestamps and is excluded from clean
   calibration.
5. Redis-active stale paused session is recovered and Redis keys are cleared.
6. State transitions invalidate task-range cache.
7. Bias lookup ignores no-stopwatch, auto-closed, dirty, corrected rows.
8. Insights ignore imported, retroactive, auto-closed, dirty rows.
9. Deadline binding correction rejects completed/missed/skipped deadlines.
10. Export/delete registry includes deadlines, pause events, feedback, exposure,
    external outcomes, email engagement, and runtime Redis purge.

## Embarrassing But Not Measurement-Critical

- Stale tutorial copy still references `/today` as brain-dump entry.
- Copy says paused work auto-closes after 12h while policy is 48h.
- Timer overflow operator copy is too bot-specific for non-OpenClaw contexts.
- Moodle connect success copy is too cheerful when sync degraded.
- Recovery-plan conflict copy asks user to edit manually without an obvious
  override.

## Invisible But Research-Critical

- Queued notifications counted as if delivered/rendered.
- Bias lookup personal evidence is not clean enough.
- Insights can publish clean-profile-looking outputs from dirty rows.
- Auto-recovered stale sessions can become EXECUTED task rows.
- Export/delete omissions break data-sovereignty assumptions.
- Native/imported duplicate deadlines inflate pressure without looking like a
  bug.

## What Not To Build While Fixing Bugs

- Browser extension passive tracking.
- More provider adapters.
- More insight types.
- More archetype/profile labels.
- New notification channels.
- New pressure-map plan generation features.
- New AI estimate sources.

Every fix should reduce ambiguity in the current loop:

```text
capture -> confirmation -> execution -> interruption -> recovery -> clean insight
```

## Final Sentence

Lyra's product loop is real, but the code still confuses queued with seen,
stale with current, and repaired with clean often enough that cohort expansion
should wait for the integrity gates.
