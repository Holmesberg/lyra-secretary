# Lyra Dogfood Findings — Living Doc

**Owner:** Operator (Ali)
**Started:** April 9, 2026
**Last updated:** April 12, 2026 (Phase 4.5 triage batch: hook order P0 fix, stale session + ghost banner P0s opened, day navigation P1, research-adjacent P2 backlog, alpha launch date confirmed April 30)
**Status:** Active dogfood, pre-alpha

This document is edited continuously as new findings emerge. Sections of this doc are referenced directly in fix-batch prompts to Claude Code. Items move from OPEN to FIXED with commit hash when shipped. FIXED items get pruned every ~2 weeks.

---

## P0 — must fix before alpha launch

### OPEN

- **New task modal stale defaults (state leak).** Title, duration, and category fields default to the last-created task's values instead of resetting when the modal reopens. Component state is not cleared on modal close. Phase 4.5 fix: reset `useState` fields in the `onClose` handler (or key the modal on `open` so React remounts it). Found during calendar dogfood Apr 11. *Found Apr 11, reproducible.*

- **Cannot start a PLANNED task while another task is PAUSED.** Backend treats any PAUSED session as a blocking active session on the generic `/v1/tasks/{id}/start` path, so the start attempt rejects. The interruption flow we shipped in commit 705b9d0 handles the conflict case explicitly but the plain start path does not distinguish "paused parent" (legal — should trigger interruption flow) from "actively executing" (illegal). Fix: treat PAUSED as non-blocking on start, routing the start through the interruption flow implicitly, OR have the generic start path detect PAUSED conflicts and invoke the interruption resolver. Phase 4.5 — blocks normal usage when a task has been paused and forgotten. *Found Apr 11, reproducible.*

- **Edit click vs multi-select checkbox conflict on PLANNED rows.** Phase 4 added click-row-to-edit and checkbox-for-multi-select-void on the same row. Operator hasn't browser-verified that clicking the checkbox doesn't also trigger the edit modal, or vice versa. Needs verification. *Found Apr 11, untested.*

- **Stale session recovery job not firing as designed.** CO review paused 16h 41m with no auto-abandon action — operator had to manually mark-abandoned via OpenClaw. Investigate: is the 15-min APScheduler job running? Is the threshold 12h as designed or 24h as initially scoped? Are Redis keys clearing on auto-abandon? Does the log show the job executing without finding stale sessions, or not executing at all? *Found Apr 12, reproducible.*

- **Ghost timer banner persists after OpenClaw mark-abandoned.** Operator marked CO review abandoned via OpenClaw → task correctly shows SKIPPED in calendar, but PAUSED timer banner still renders on `/today` showing "CO review 16:41:31 paused." Stale active stopwatch state on the SKIPPED path. Two likely root causes: (a) OpenClaw mark-abandoned endpoint doesn't clear Redis `stopwatch:active` + `stopwatch:paused` keys, (b) `_get_active` doesn't check `task.state == SKIPPED` as an auto-heal condition (only checks `voided_at`). Probably both — the void path already has self-heal (commit 59ca80d), the skip path doesn't. Fix: same self-heal pattern in `_get_active` for SKIPPED tasks, plus mark-abandoned must clear Redis keys like void does. *Found Apr 12, reproducible.*

### FIXED (recent — prune in 2 weeks)

- Stale session recovery job — APScheduler sweeper every 15 min, closes unclosed StopwatchSession rows older than 24h with auto_closed=True, clears matching Redis keys, per-user iteration (LYR-103, this commit)
- Defense-in-depth voided_at filter in _recover_from_db so legacy orphan voided sessions never rehydrate into the banner on Redis-loss events (LYR-095, commit d5da23d)
- Voided task still shows paused timer banner — void_task now closes orphan StopwatchSession and clears Redis active/pause keys; _get_active self-heals historic stale state on next poll (commit 59ca80d)
- OpenClaw void without voided_reason — SKILL.md now mandates "ALWAYS ASK REASON" on any non-DELETED void, endpoint line marks voided_reason as required with enum values listed (commit e57aa7e)
- PLANNED edit affordance via prefilled modal (commit 8eb4ac7)
- PLANNED delete affordance with confirmation (commit afcf868)
- EXECUTING/PAUSED skip affordance (commit 1d85b84)
- Multi-select void replacing row trash icon (commit b54e130)
- LYR-095 get_status falls through to Redis recovery (commit 9b7756f)
- LYR-096 task_completion_percentage passthrough (commit b3f8f2e)
- Friendly 400 on InvalidStateTransitionError (commit 7881ba2)
- Interruption flow handles mixed paused + blocking conflicts (commit 705b9d0)
- LYR-100 CORS middleware ordering (commit 625bf87)
- LYR-091 Notion archived-page detection (commit 951160e)
- AppLayout 401 auto-signOut + always-rendered Sign Out button (commit 7c9f33e)
- Cross-tenant write leak structural fix (Phase 3.2, commits 4cf2168 + 430f120)
- Cross-tenant read leak per-user Redis keys — operator saw a second user's active timer (Phase 3.3 P0-A)
- Pause/resume 500 from int/float type mismatch (Phase 3.3 P0-B)
- completion_pct accepted 500% validation (Phase 3.3 P0-C)
- ActiveTimerBanner hook order violation — click-outside useEffect from f3af1df (pause reason picker) was placed below early return at line 57, causing "Rendered fewer hooks than expected" crash when stopwatch stopped and `status.active` flipped false. Moved effect above early return. (fix applied Apr 12, commit pending)

---

## P1 — fix during Phase 4.5, before alpha

### OPEN

- **New task modal: end-time picker as alternative to duration.** Power-user request from calendar dogfood. Toggle between "duration" mode (current default, keep as default) and "end time" mode — in end-time mode the user picks a wall-clock end instead of a minutes count, and duration is derived on submit. Useful when scheduling around fixed anchors (meeting at 3 PM that ends at 4 PM). *Apr 11.*

- **Task swap feature (planned time exchange).** Multi-select with EXACTLY 2 tasks → new "Swap times" button appears next to "Void" → swaps `planned_start_utc` and `planned_end_utc` between the two task rows (durations preserved only if both sides have the same duration; otherwise each task's duration moves with its new start). New backend endpoint `POST /v1/tasks/swap-times` accepting `{task_id_a, task_id_b}`. Matches OpenClaw parity. Conflict detection must still run on both tasks at their new times. *Apr 11.*

- **Frontend backend-unreachable graceful retry UI.** "Failed to fetch" raw error shown on transient backend issues (host sleep, WSL port forward stabilization). Should be friendly retry banner with auto-retry every 5s. *Apr 11.*

- **Tooltips on `4 → 2 +29min` row arrow.** Only operator knows what readiness/focus/delta arrow means. Add hover tooltip or inline label for new users. *Apr 10.*

- **LYR-097 is_future_task warning ignored.** Backend returns warning when starting timer for task >5min in future, frontend silently discards. *Apr 11 audit.*

- **LYR-098 micro_mirror and calibration_nudge ignored on stop.** Backend computes both, frontend never displays. Research signal lost. *Apr 11 audit.*

- **Density and typography polish on Today view.** Half-page empty, text could be denser. Reference: Linear, Vercel, Cron, Raycast. *Apr 9.*

- **No swap-tasks affordance.** Existed in OpenClaw, missing in web UI. v2 backlog or Phase 4.5. *Apr 9.*

- **Active timer banner display when paused very long.** Currently shows full HH:MM:SS counter which becomes absurd at 16+ hours. Cap display at "12h+ paused — auto-abandoning soon" once stale_session_recovery threshold is approached. *Apr 11.*

- **Today view forward/backward day navigation.** Arrow buttons left of "Sunday April 12" header, navigate prev/next day. Past days are read-only (no start/stop), PLANNED tasks on future days remain editable. Unblocks yesterday-review workflows for reflection — operator and alpha users will both hit this by week 2. *Apr 12.*

- **ReflectionModal completion % ungate.** Currently the completion percentage input only renders on early-stop confirmation flow (`earlyStop && ...` guard in `reflection-modal.tsx:82`). Normal and overrun stops never collect it — research signal lost for the "how complete was this task?" dimension on every non-early stop. Remove the `earlyStop &&` gate so the input appears on every stop. Adds ~2s post-task friction per session — dogfood on operator only for 1 day before promoting to main. *Apr 12.*

### FIXED (recent — prune in 2 weeks)

- **Schedule-X calendar view at `/calendar` (final, browser-verified).** Full day/week/month calendar using `@schedule-x/react@4.1.0` + `@schedule-x/calendar@4.4.0` + drag-and-drop/resize v3.7.3 + `temporal-polyfill@0.3.0`. Five state-colored calendars matching task-row pills. Click PLANNED → edit modal prefilled; click non-PLANNED → readonly details popover (planned/executed times, duration delta, readiness/focus). Drag/resize PLANNED → `POST /v1/reschedule` via `onBeforeEventUpdateAsync`; non-PLANNED drag rejected with auto-dismissing toast. Voided tasks filtered from event list. Backend `/v1/tasks/query` gained optional `days` param (default 1, max 62) so the calendar pulls a 62-day window in one round trip. Stale-closure safety via `useRef<TaskRow[]>` so callbacks see fresh query data after refetch. Cross-view cache sync via predicate-based query invalidation. Initial ship (commit e085671) shipped with four latent runtime issues that required three verification rounds to unblock: (1) Schedule-X `selectedDate` crash from dual-realm `Temporal.PlainDate` — fixed by `temporal-polyfill/global` side-effect import; (2) time grid cropped at ~7 AM — fixed by `h-[calc(100vh-220px)] overflow-y-auto` outer wrapper instead of fixed height + overflow-hidden; (3) overlapping events cascaded with text obscured — fixed by `weekOptions.eventOverlap: false` splitting them into equal sub-columns; (4) drag threw `TypeError: startTimeGridDrag is not a function` due to upstream plugin-vs-core version mismatch (calendar@4.4.0 renamed the method contract but no @schedule-x/drag-and-drop@4.x has been published) — fixed by runtime alias shim binding the 3.x method names under the 4.x expected names. Final commit a1c07a1 closed Phase 4 calendar integration with all browser-verify items green (drag + resize + immutable guard + scroll + overlap split + no console errors).
- **useCurrentTime hook** — shared `useCurrentTime()` hook ticks every 60s so `today/page.tsx` cross-day key rollover and `new-task-modal` default start no longer freeze on page idle. Bundles LYR-099 fix (modal reopen after 30min idle showed stale default) (commit 2c18be9)
- **Pause reason picker on web UI** — `ActiveTimerBanner` Pause button now opens an inline dropdown with the 6 PAUSE_REASONS enum values (mental_fatigue, distraction, task_difficulty, external_interruption, intentional_break, prayer); click-outside dismisses and pauses with `external_interruption` as the least-wrong default (commit f3af1df)
- PLANNED rows sort ascending (next-up first) — partitioned from the execution-axis block so PLANNED-PLANNED comparisons go asc while everything else stays desc; avoids the non-transitive mixed-comparator failure mode for stale PLANNED rows with past planned_start (commit 57839d5)
- Sort direction (newest top) — Phase 3.3 partial fix; superseded by the ascending-PLANNED partition above
- WSL stale-cache cold-restart rule documented in CONTRIBUTING.md — HMR unreliable on WSL + Next.js 15 + Schedule-X, full cold restart (pkill + rm -rf .next + npm run dev) required before every browser-verify (commit ed2f4a8)

---

## P2 — defer to v2 backlog or post-alpha

### OPEN

- **category_type field (estimable vs time_anchored).** Designed in audit, deferred to Phase 4. Required before H1 analysis runs. Prayer/sleep/meals contaminate bias_factor. Bundle this with the `self_reflection → planning` rename below so the category schema migration lands in one shot. **Design note (Apr 11):** prayer is NOT a bug to remove — it stays as a category and will be flagged `time_anchored` via this field, which excludes it from bias_factor analysis while preserving it as behavioral data. Same treatment applies to sleep/meals. *Apr 10.*

- **self_reflection → planning rename.** Cosmetic only, deferred. Bundle with the `category_type` field migration above so the category table gets one coordinated migration instead of two. *Apr 10.*

- **Users 98/99 have Redis `stopwatch:active:*` keys with no corresponding unclosed SQLite session.** Caught during the d5da23d/a67c769/57839d5 verification sweep on Apr 11 — 3 Redis active-stopwatch keys vs 1 unclosed session in SQLite. Not a voided-task leak (tasks exist and aren't voided) so outside LYR-103's scope, but it is a Redis ↔ SQLite drift that stale_session_recovery won't clean up because it sweeps SQLite, not Redis. Most likely cause: test fixture pollution from `test_multiuser_isolation_adversarial.py` or similar that creates Redis state under synthetic user_ids (98, 99) without the matching SQLite rows. Investigate post-Phase 4.5 — possible fixes: (a) add per-test teardown that flushes `stopwatch:active:{user_id}` for the synthetic users, (b) extend `stale_session_recovery` to also reconcile Redis keys whose session_id isn't in SQLite at all. *Apr 11.*

- **Aladhan prayer API integration.** Auto-schedule 5 PRAYER tasks daily, suggest pause on prayer time. v2 backlog. *Apr 10.*

- **VT-5 parent_session_id for split sessions.** Decision deferred to Paper 1 analysis phase. *Audit.*

- **Smart inactivity reminders.** Escalating notifications before stale session recovery fires. v2 backlog. *Apr 10.*

- **Mid-funnel retention loop.** Daily/weekly digest for sessions 5-30. v2 backlog. *Apr 10.*

- **LLM-powered task creation via OpenClaw bridge.** Reframed from "v2 defer indefinitely" to Phase 6 candidate after dogfood data. Operator overruled "scope creep" framing — it's the differentiator, low cost since OpenClaw infrastructure exists. *Apr 10.*

- **PWA support.** iOS/Android home-screen install, offline mode, basic push notifications. ~4 hours of work for 80% of "feels like a real app." Phase 7. *Apr 11.*

- **pre_task_readiness as reactive measure acknowledgment in MANIFESTO.** The 1-5 scale is constructed at prompt time, not retrieved from a stable internal state (Schwarz 1999, simulation heuristic literature). One-paragraph limitation note in MANIFESTO methodology section and Paper 1 methods section. Does not change the measurement — changes how we frame what it means. *Apr 12.*

- **is_anchor boolean column on Task model for prayer/sleep.** Alembic migration, backfill existing prayer rows. Exclude `is_anchor=true` from bias_factor / discrepancy / cascade analytics. Calendar renders anchor events with distinct styling (lighter color, dashed border). Unblocks H1 analysis currently blocked on category_type field (same architectural concern, simpler mechanism). Bundles with `self_reflection → planning` rename in the same migration. *Apr 12.*

- **Metacognitive reliability score per user (Dunning-Kruger stratification).** Latent variable derived from correlation between predicted improvement and actual improvement across calibration attempts. Users with low score won't improve via feedback alone — flag them for different intervention strategy. Requires 30+ sessions per user to compute meaningfully. Phase 6 analysis. *Apr 12.*

- **Prediction-first logging schema.** New `intervention_log` table: `intervention_type`, `context`, `predicted_effect`, `actual_outcome`, `delta_change`. Enables intervention effectiveness ranking. Phase 6 architecture. *Apr 12.*

- **Falsification engine background process.** Continuous computation of H1 correlation, variance reduction, kill-criterion status. Outputs `current_correlation`, `required_threshold`, `confidence_interval`, AT_RISK/PASS/FAIL status. Prevents "feels like it's working" drift. Phase 6 architecture. *Apr 12.*

- **Layered adaptation with different time constants.** Fixed layer (raw signals, hypotheses, kill criteria) must not adapt. Semi-adaptive layer (thresholds, clustering, bias smoothing) adapts only on scheduled re-fit cycles (every 30 sessions or 14 days). Fully adaptive layer (insight wording, intervention timing, prompt selection) adapts fast. Phase 6 architecture. *Apr 12.*

- **Intervention effectiveness tracking.** Log predicted vs actual effect for every intervention (early_stop gate, readiness_prompt, calibration_nudge, etc.). Rank interventions by delta variance reduction. Underutilized ones get deprecated. Phase 6. *Apr 12.*

- **Trigger field for implementation intentions.** Three trigger classes: clock (current default), after_task (task surfaces when `trigger_after_task_id` transitions to EXECUTED), contextual (task sits in Waiting bucket until user taps "start now"). Schema: `trigger_type` enum + `trigger_detail` text. Completion rate uplift 2-3x per Gollwitzer 1999. Significant UX change, test on dogfood operator first. Phase 6+. *Apr 12.*

- **Residue-based cascade model vs probability-based.** Current `cascade_score = P(skip_{N+1} | skip_N)` is stateless. Residue model: `load(t) = sum of decaying context_switch costs within tau window`. New `context_switches` table schema: `from_task_id`, `to_task_id`, `timestamp`, `switch_type`, `category_distance`. Fit both models against alpha data week 10+, ship the one with better predictive validity. Phase 6 analysis. *Apr 12.*

- **Post-novelty retention metric.** Week 3 retention can be novelty-driven false positive per QS literature post-2017. Add week 6-8 retention checkpoint to alpha evaluation. If week 3 green but week 6 red, that's hedonic adaptation, not product-market fit. *Apr 12.*

- **Middle-phase retention mechanism design.** Three candidate paths: (a) insight tiering — new analytical layers unlock at session thresholds keeping "what will I learn today" alive, (b) lightweight social accountability — weekly summary shareable to one partner, (c) predictive intervention replacing descriptive insight — product transitions from mirror to advisor as data accumulates. Phase 7+. *Apr 12.*

- **Archetype re-fit cycle to handle end-of-history illusion.** People change; static archetype assignments progressively misclassify. Either periodic Bayesian update from new data or `archetype(t)` function instead of archetype constant. Implementation decision at Phase 6 after first alpha cohort produces data. *Apr 12.*

- **"Do not add" list.** Documented in `docs/do_not_add.md` (April 14). Covers 11 rejected architectural directions with reasoning. *Apr 12, shipped Apr 14.*

- **Compression cycles every ~10 days.** Force review of signals: which actually changed decisions vs which just felt insightful. Delete or merge 20-30% of signals per cycle. Operator discipline check. First cycle April 28. See Process findings section for schedule details. *Apr 12.*

---

## P3 — post-retention architecture

### OPEN

- **Calendar dense-cluster readability.** With `eventOverlap: false` (current) and 5+ overlapping events in one time slot, each event becomes too narrow to read the title. Schedule-X v4.4.0 has no built-in collapse or truncate option. Investigate Phase 5+: custom event renderer with cluster fallback (e.g. show 3 + "+2 more" badge), or detect dense days and switch to month-style agenda layout for that day. Not blocking — typical Lyra day has 1-3 concurrent events in any slot. *Apr 11.*

- **Schedule-X drag-and-drop plugin shim removal (housekeeping).** `@schedule-x/drag-and-drop@3.7.3` (the latest published version on npm) doesn't match `@schedule-x/calendar@4.4.0`'s renamed plugin method contract — calendar 4.x calls `startTimeGridDrag` / `startDateGridDrag` / `startMonthGridDrag` but the plugin still exposes `createTimeGridDragHandler` / `createDateGridDragHandler` / `createMonthGridDragHandler`. We ship a runtime alias shim in `frontend/app/(app)/calendar/page.tsx:252` that binds the old methods under the new names (signatures are byte-identical, confirmed via source dive). Watch upstream npm for a `@schedule-x/drag-and-drop@4.x` release; when it lands, delete the shim block, bump the dep, and browser-verify drag still works. Resize does NOT need a matching shim — its method name was not renamed in the 4.x refactor. Source-dive evidence lives in the commit message body for the Phase 4 calendar close. *Apr 11, housekeeping.*

- **Multi-timezone API contract refactor.** Currently single-timezone (Cairo). Backend sends and accepts naked Cairo-local ISO strings ("2026-04-05T06:00:00"); frontend parses as `Temporal.PlainDateTime` and attaches `Africa/Cairo` to produce the display `ZonedDateTime`. When the second timezone joins alpha, refactor: backend serializes UTC with Z suffix, frontend converts via new `user.timezone` field, Notion sync path remains naked Cairo local (LYR-019 contract preserved). Estimated 3–5 days work + 2–3 weeks bug hunt. Trigger: first non-Cairo user signup OR explicit request. Single-point-of-truth wire format means `toZdt`/`zdtToIso` in `calendar/page.tsx` change in the same commit as the API serializer — do NOT patch one side in isolation. The `TIMEZONE CONTRACT` comment block at the top of that file exists to stop future contributors from "fixing" it piecemeal. *Apr 11, deferred until post-retention.*

---

## Process / environment findings

- **WSL + Next.js dev server stale cache.** `rm -rf .next` doesn't help if a zombie `next dev` process is still running — the old process recreates the cache from in-memory state. Must `pkill -f "next dev"` first. Operator added `lyra-dev` shell alias that does kill + clean + restart in one command. Goes away on Vercel deploy. *Recurring Apr 9-11.*

- **Zombie port 3000 after dev server crashes.** Same fix as above — the `lyra-dev` alias handles it. *Recurring.*

- **Host sleep breaks WSL port forwarding intermittently.** Symptoms: "Failed to fetch" or net::ERR_FAILED on localhost:8000 from browser, while WSL curl to same endpoint succeeds. Workaround: docker restart backend, or wsl --shutdown + Docker Desktop restart in worst case. *Apr 11.*

- **Middleware ordering rule documented in CONTRIBUTING.md** (LYR-100 lesson): response-modifying middleware must be added LAST to end up outermost. Short-circuiting middleware (auth, rate limit) goes inner. *Apr 11.*

- **Compression cycles — every ~10 days.** Operator reviews the dogfood doc and Phase 6 backlog. Rule: which signals/features actually changed decisions vs which felt insightful but produced no action? Delete or merge 20-30% of items per cycle. Forces discipline against complexity creep. Schedule: end of every two-week sprint. First cycle: April 28 (post-Spring-School return). *Apr 14.*

- **Durable verification gate suite formalized (10 gates).** tsc, container health, APScheduler job count, `_recover_from_db` filter inspect, Redis/SQLite consistency, git state snapshot, dev server compile, dev-log static-paths clean check, browser-verify HARD GATE, multi-tenant isolation gate for new read endpoints. Cross-component cross-route verification gap identified in Phase 4 close emergency — shared components must be state-transition tested on every route that uses them, not just the changed route. *Apr 12.*

- **Phase 6 architecture backlog document recommended.** Create `docs/phase_6_architecture_backlog.md` with schemas and acceptance criteria for all Phase 6 P2 items (prediction-first logging, falsification engine, layered adaptation, intervention tracking, cascade model, metacognitive reliability, archetype re-fit, trigger field). 20 minutes one-time work, prevents rediscovering design decisions next month. *Apr 12.*

---

## Architecture findings (long-term)

- **The clustering layer has 4 stacked unvalidated assumptions.** Documented in `clustering_spec.md` validation gates section. Re-fit after Phase 6+ data. *Audit.*

- **H1 kill criterion was tightened** to require statistically significant + predicted-direction learning improvement. Pre-registration block added. *Audit.*

- **3 behavioral profiles vs 5 operational archetypes** are different abstraction levels, now documented. *Audit.*

- **BCI reframed from replacement-or-parallel to complementary signal** with Bayesian weighting. *Audit.*

- **Single-mutation-authority pattern protects writes but every new read endpoint is a leak surface.** CONTRIBUTING.md isolation test rule added. *Audit.*

---

## How operator uses this doc

1. New finding emerges → operator drops a one-line entry under the appropriate priority section.
2. When ready to ship a fix batch, operator references the relevant section by name in a Claude Code prompt: "read OPEN P0 section of dogfood_findings_living.md and ship items 1-3."
3. Claude Code reports back with commit hashes per item.
4. Operator (or Claude in chat) moves items from OPEN to FIXED with hash + date.
5. FIXED items stay for ~2 weeks then get pruned to keep the doc readable.

P0 = blocks alpha launch
P1 = ships before alpha but doesn't block
P2 = post-alpha, v2, or research-phase work

---

## Alpha launch timeline

- **Confirmed pause April 19-29** for Spring School. Pre-pause hardening target: April 18.
- **Alpha launches April 30** (NOT April 16-17 — retention needs full attention during first-week fragility window).
- **Retention answer projected** May 21 ±3 days.
- **BCI integration decision** June. Path B (October hackathon) preferred for research clarity.
