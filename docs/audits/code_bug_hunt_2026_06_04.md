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

- Timer overflow still needs formal output-surface registration or explicit
  operational-only classification.
- Bias lookup, insights, and deadline-shape endpoints still need a full
  shared-clean-profile pass.
- Provider/data-sovereignty issues in Gate 3 remain open.

## Bug-Fix Waves

Use this order for the next passes.

### Wave A - Browser Verify Implemented K01-K04

Definition of done:

- calendar refresh warning never appears as web technical alert;
- timer overflow web toast appears once, with integer minutes and no `Reply`;
- executed tasks never show missed-plan mark-done cards;
- `>=72h` paused task opens stale-resolution reflection modal;
- Pulse receives queued notifications without visiting Today.

### Wave B - Measurement Cleanliness

Fix:

- bias lookup uses the shared planning-calibration clean primitive;
- insights use clean-profile selection;
- deadline-shape outcomes exclude dirty/repaired/auto-closed/corrected rows;
- Pulse stop flow captures focus, completion percent, and scope.

### Wave C - Provider And Data Sovereignty

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

1. Split or make explicit notification channels and stop drain-on-fetch loss.
2. Host user notifications in Pulse or the app shell, not only Today.
3. Bust task-range/evidence caches on all task/session state transitions.
4. Fix stale-session recovery so auto-recovered executed tasks have complete
   execution timestamps, or cannot become clean execution evidence.
5. Route bias lookup and insights through shared Cortex clean-profile queries.
6. Add safe-mode frontend guard so Pressure Map cannot create recovery blocks
   when backend recovery options are disabled.
7. Close provider/security blockers: Moodle URL SSRF guard, credential
   encryption, export/delete completeness.

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
