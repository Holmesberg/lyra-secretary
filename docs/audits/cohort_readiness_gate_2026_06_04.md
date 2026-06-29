# Cohort Readiness Gate - 2026-06-04

Status: audit gate only.  
May authorize code: false.  
Runtime owner: none.

## Verdict

```text
Do not expand beyond current dogfood/trusted users until the operator cockpit
is green and Wave 6 final cohort proof passes.
```

Lyra can continue operator dogfooding, but it is not ready for a fresh 15-20
user push if the goal is trustworthy product behavior and clean execution data.

Research-method note:

```text
Measurement Integrity Before Agency Claims
```

This gate exists because cohort expansion is not only a product decision. More
users increase intervention effects, provider mess, stale-state paths, dirty
rows, and dashboard interpretation risk. LyraOS should not use retention,
completion, timer, pressure, or provider metrics to claim anything about focus,
motivation, avoidance, discipline, recovery, agency, or improvement until the
measurement substrate can explain what those metrics mean and why they are
clean enough in the relevant slice.

Canonical note:
`docs/measurement_integrity_before_agency_claims.md`.

## 2026-06-22 Freeze-Closure Update

Later bug-closure waves supersede the original Gate 0/Gate 1 wording where the
current implementation has already been tested. The active gate is now:

```text
/operator dynamic issues and final cohort-readiness proof govern expansion.
K01-K05 are watchlist tags, not the primary decision system.
```

Current read:

| Area | Current status |
|---|---|
| Gate 0 notification/re-entry delivery | Implemented through Wave 1; keep lifecycle and operator-copy regressions. |
| Gate 1 timer/re-entry state integrity | Implemented through Wave 2; user browser verified. |
| Gate 2 measurement cleanliness | Implemented for Wave B surfaces; keep clean-profile regressions. |
| Gate 3 data sovereignty | Wave 5A closed. |
| Gate 3 provider security/integrity | Wave 5B closed for current tested paths, including fixture browser proof and operator-cookie read-only stress. |
| Operator cockpit | Implemented as active decision surface; must stay read-only, invariant-derived, content-minimized, and free of fake certainty. |
| Final cohort expansion | Wave 6 proof ran on 2026-06-22 and failed readiness: `/operator` is red, `safe_to_invite_more_users=no`, and dual-account browser proof is blocked by truncated alt cookies. |

Current cohort blockers:

- duplicate queued notification prompts;
- exposure records without render evidence;
- notification/source freshness and other instrumentation gaps;
- no valid non-operator alt cookie for the required two-account browser proof.

Before new features, the operator cockpit must answer:

- can Lyra invite more trusted users today?
- what invariant blocks expansion?
- what is only a warning?
- what is not instrumented?
- what data is excluded from clean baselines?

The dashboard must not mutate last activity, notification lifecycle, exposure
state, user metrics, task/session/deadline/provider state, or Redis runtime
state.

Parked research direction:

- behavior-transition equations are preserved in
  `docs/parked/behavior_transition_equation_stack.md`;
- ClaimCompiler / future AI-synthesis boundaries are preserved in
  `docs/claim_compiler_and_synthesis_boundary.md`;
- neither doc authorizes runtime behavior during the freeze.

## 2026-06-05 Wave A Status

Gate 0 and Gate 1 now have a Wave A browser pass for the current K01-K04/K05
surface checks. This does not mean all Gate 0/Gate 1 engineering is complete;
timer-overflow exposure registration and deeper measurement-cleanliness gates
remain open.

Implemented:

- explicit `/v1/notifications/web/pending`,
  `/v1/notifications/web/ack`, and `/v1/notifications/openclaw/pending`;
- web notification delivery uses peek/ack, not destructive drain;
- app-shell user notification host for Pulse and Today;
- web-safe copy generation for reminder, timer overflow, pause prediction, and
  resume prediction;
- 72h+ stale paused session resolution endpoint and Pulse modal path;
- task-range invalidation on stopwatch state transitions;
- `Lyra waves` incident repaired for user-facing truth while flagged dirty for
  clean calibration.

Browser-passed on deployed build `f251653`:

- K01: seeded `[calendar.sync]` operator diagnostic did not render in the web
  app;
- K02: seeded timer-overflow payload rendered once on Pulse with integer
  minutes and no `Reply with` or raw float;
- K03: seeded `EXECUTED` task did not appear as a missed-plan mark-done card;
- K04: seeded `73h` parked paused session opened the required stale-resolution
  reflection modal;
- K05: `/pulse#quick-capture` landed on the top quick-capture bar;
- Pulse rendered the queued web notification without visiting Today.

Verification artifact:

- synthetic user:
  `wave-a-verify-1780658138440@example.test`;
- screenshots:
  - `tmp/lyra-wave-a-1780658138440/pulse-wave-a.png`;
  - `tmp/lyra-wave-a-1780658138440/stale-resolution-modal.png`;
- cleanup confirmed zero remaining `wave-a-verify-*` users.

Still open:

- timer overflow output-surface registration remains open;
- Gate 2 and Gate 3 remain open.

## 2026-06-05 Wave B Status

Gate 2 now has a targeted implementation pass for the current measurement
cleanliness blockers.

Implemented:

- bias lookup uses the shared planning-calibration clean task primitive for
  personal evidence;
- planning-calibration output surfaces reuse the clean primitive before
  exposure filtering;
- deadline-shape outcomes exclude dirty stopwatch evidence, repaired rows,
  auto-closed sessions, corrected tasks, imported/external deadlines,
  retroactive/system-error tasks, voided rows, and incomplete execution rows;
- Pulse stop flow captures focus rating, completion percentage, and scope
  outcome;
- app-shell undo toast makes timer-start undo visible after accidental session
  starts; task creation no longer announces undo.

Verified:

- targeted backend suite: `17 passed`;
- frontend production build: passed;
- browser verification on deployed `lyraos.org` confirmed:
  - visible timer-start undo toast with `UNDO`;
  - undo reverted the task to `PLANNED`, removed the just-created stopwatch
    session, and left no active timer;
  - Pulse stop modal includes `Done %` and `Scope`;
  - exported proof before cleanup showed focus `4`, completion `90`, and
    `scope_outcome=expanded`;
  - exact synthetic verification rows were deleted afterward.

Still open:

- Gate 3 provider/data-sovereignty work;
- Wave D formal exposure-registration work;
- broader full-suite regression beyond the targeted Wave B suite.

## Gate 0 - Notification And Re-entry Delivery

Must pass:

- Web app never renders `operator_alert` or `[calendar.sync]` diagnostic copy.
- Pulse and Today share a user-facing notification host.
- Pending notifications are not deleted until rendered or explicitly dismissed.
- Timer overflow renders once on web with integer active minutes and no OpenClaw
  reply instructions.
- Timer overflow is registered as an output surface or explicitly classified as
  operational-only until registration.

Browser checks:

1. Calendar refresh failure: OpenClaw only, no web toast.
2. Timer overflow: one web toast, one operator alert, no raw float.
3. Resume prediction: queued while state mismatches, not lost.
4. Pulse page: queued reminder/overflow renders without visiting Today.

Tests:

- notification queue peek/reserve/ack;
- endpoint channel explicitness;
- timer overflow web/operator copy separation;
- exposure render ack.

## Gate 1 - Timer/Re-entry State Integrity

Must pass:

- `/tasks/query` range/evidence cache invalidates on all task/session state
  transitions.
- Re-entry cards only expose actions valid against current backend state.
- Stale paused sessions beyond policy threshold resolve even if Redis still
  marks the session active.
- Auto-recovered EXECUTED tasks have coherent execution timestamps or cannot
  become EXECUTED without user confirmation.
- Old parked work has age-tiered recovery copy.
- Stale paused sessions at `>=72h` must ask for focus rating, completion
  percentage, and scope outcome through the reflection modal. They must not
  auto-mark `SKIPPED` or `EXECUTED`.
- User-resolved stale pauses must remain useful in UI history but excluded from
  clean calibration via `StopwatchSession.data_quality_flag`.

Browser checks:

1. Execute a missed-plan card elsewhere; Pulse removes mark-done action.
2. Pause work 25h; Pulse frames it as open-thread review, not immediate shame.
3. Pause work >=72h; Pulse shows `Resolve session`; modal requires focus,
   completion %, and scope; resolved card disappears.
4. Start another task while paused; interruption type/provenance is explicit.
5. Stop task in Pulse; completion percentage and scope outcome are saved.

Tests:

- stale recovery timestamps and clean exclusion;
- Redis-active stale paused recovery;
- task-range invalidation after stop/pause/resume/switch;
- frontend/backend re-entry eligibility parity.

## Gate 2 - Measurement Cleanliness

Must pass before using insights/estimates as product claims:

- Bias lookup uses `planning_calibration_query` or equivalent shared clean
  primitive.
- Insights use full clean-profile selection, not endpoint-local filters.
- Deadline-shape outcomes exclude auto-closed, corrected, dirty, imported, and
  retroactive rows unless the output clearly labels them.
- Pulse stop captures the same completion/scope fields as Today.

Tests:

- dirty personal evidence cannot produce personal bias nudge;
- no-stopwatch/auto-closed rows do not unlock insights;
- deadline-shape excludes repaired stale outcomes.

## Gate 3 - Provider And Data-Sovereignty Safety

Must pass before encouraging integrations:

- Moodle/iCal/WS URLs reject loopback, private, link-local, metadata addresses,
  and redirects to those addresses.
- Google refresh tokens and Moodle iCal URLs are encrypted at rest.
- Moodle WS backfilled deadlines visibly show external Moodle provenance.
- Native/imported duplicate deadlines are prevented or explicitly surfaced.
- Export and delete use a central user-owned data registry.
- Delete purges Redis runtime state.

Tests:

- SSRF rejection cases;
- encrypted credential storage with legacy fallback;
- export/delete one row per user-owned table;
- Redis purge on deletion.

## Go / No-Go Rule

Go for 15-20 users only when:

```text
Gate 0 passed
Gate 1 passed
K01-K05 browser checks passed
No Critical findings remain open
High findings have owner, test, and rollback path
```

The K01-K05 browser checks have now passed once on Wave A. Cohort expansion
still should wait for the remaining Critical/High items in the code bug hunt,
especially Wave B measurement cleanliness, Wave C provider/data-sovereignty
safety, and Wave D exposure registration. Any user-facing estimate, insight, or
integration push should wait for its relevant gate.

## What Can Continue Now

- Operator dogfooding.
- Small manual browser verification.
- Documentation cleanup.
- Targeted tests.
- Minimal patches against the gates.

## What Should Wait

- New users beyond the current trusted set.
- Browser extension/passive tracking.
- New provider adapters.
- New insight/archetype surfaces.
- New notification campaigns that depend on in-app re-entry being clean.

## Brutally Simple Rule

If the app cannot prove that a prompt was seen, a timer state is current, and a
measurement row is clean, it should not use that row to guide or claim anything.
