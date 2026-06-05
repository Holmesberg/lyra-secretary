# Cohort Readiness Gate - 2026-06-04

Status: audit gate only.  
May authorize code: false.  
Runtime owner: none.

## Verdict

```text
Do not expand beyond current dogfood/trusted users until Gate 0 and Gate 1 pass.
```

Lyra can continue operator dogfooding, but it is not ready for a fresh 15-20
user push if the goal is trustworthy product behavior and clean execution data.

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
  - `C:\Users\alina\AppData\Local\Temp\lyra-wave-a-1780658138440\pulse-wave-a.png`;
  - `C:\Users\alina\AppData\Local\Temp\lyra-wave-a-1780658138440\stale-resolution-modal.png`;
- cleanup confirmed zero remaining `wave-a-verify-*` users.

Still open:

- timer overflow output-surface registration remains open;
- Gate 2 and Gate 3 remain open.

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
