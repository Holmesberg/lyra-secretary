# Lyra Secretary — Feature Backlog  (ARCHIVED)

> **This document is archived and no longer canonical.**
>
> Forward-looking phase planning has moved to [`docs/building_phases.md`](../docs/building_phases.md); retrospective history lives in [`docs/project_history.md`](../docs/project_history.md); tactical dogfood items live in [`docs/dogfood_findings_living.md`](../docs/dogfood_findings_living.md). Items below are kept for historical context only — do not edit; do not use to plan work.

*Frozen April 14, 2026. Last pre-archive update: April 10, 2026 — BCI reframe, LYR-061/unplanned_reason status corrected.*

Priority: 🔴 critical | 🟡 important | 🟢 nice-to-have
Status: 📋 backlog | 🔨 in progress | ✅ done

---

## v1.4 — Measurement Integrity

### ✅ POST /v1/stopwatch/retroactive
Log completed sessions after the fact with full timestamp control.

**Body:**
```json
{
  "title": "string",
  "start_time": "ISO8601",
  "end_time": "ISO8601",
  "pre_task_readiness": 1-5 (optional),
  "post_task_reflection": 1-5 (optional),
  "category": "string (optional)"
}
```
**Behavior:**
- Creates task in EXECUTED state (bypasses state machine and past-time check)
- Sets planned = executed (delta = 0 by definition)
- Tags initiation_status: "retroactive"
- Notion sync as normal
- pre/post optional — retroactive sessions still capture discrepancy even without readiness scores

**Use case:** End-of-day logging of untracked sessions. Discovered on Day 1 of experiment.

---

### ✅ Unplanned execution rate in analytics
Add `unplanned_execution_rate` to `GET /v1/analytics/discrepancy` research layer.

```
unplanned_execution_rate = retroactive_tasks / total_tasks per day
```

Correlate against:
- delta patterns
- discrepancy scores
- time of day
- session sequence position

**Pattern detection to add to insights engine:**
- "X% of your sessions this week were unplanned — your highest yet"
- "Unplanned sessions correlate with higher delta in your data"
- "Structured days (low unplanned rate) show 30% lower delta"

---

### ✅ Bias factor computation endpoint
`GET /v1/analytics/bias_factor?min_sessions=3`

Returns per (category, time_of_day) cells with fallback aggregations. Each cell exposes both metrics:
- `bias_factor` — sum(executed) / sum(planned). **PRIMARY** (weighted, scheduler-consumable).
- `bias_factor_mean` — mean(executed_i / planned_i). Sanity check; divergence reveals long-session dominance.

Response shape: `{ cells, category_only, time_of_day_only, global, insufficient_cells, min_sessions, total_executed, primary_metric }`. Excludes retroactive sessions per MANIFESTO Pre-registered Rule #1. `> 1.0` = underestimates, `< 1.0` = overestimates, `0.9–1.1` = on target. Used by adaptive planning (v1.5).

---

### ✅ Backfill endpoint for pre-fix tasks (LYR-015)
`POST /v1/tasks/{task_id}/sync`

Force Notion sync for any task. Use to backfill tasks created before timezone pipeline fix or after transient Notion API failures.

---

### ✅ Pause reason classification
Add `pause_reason` enum to pause endpoint: `prayer` / `break` / `interruption`.

Distinguishes planned pauses from involuntary interruptions. Interruption frequency is an analytical signal — high rate correlates with environment, not cognitive state. All pause types excluded from delta.

Resolves validity threat VT-6 (see MANIFESTO.md).

**Implemented:** POST /v1/stopwatch/pause accepts optional `pause_reason` (mental_fatigue|distraction|task_difficulty|external_interruption|intentional_break|prayer) and `pause_initiator` (self|external). Migration 004.

---

### ✅ Fix conflict detection on immutable tasks (LYR-070)
Filter candidate tasks in `conflict_detector.py` to `state IN ('PLANNED', 'EXECUTING')` before checking overlap. EXECUTED/SKIPPED/DELETED tasks should not block new task creation.

**Implemented:** One-line fix in conflict_detector.py. Also fixed `Task.is_mutable` to include SKIPPED state.

---

### ✅ Readiness correction endpoint (LYR-074)
POST /v1/stopwatch/correct-readiness — corrects pre_task_readiness any time during active session. No time limit (unlike 30s undo window). Logs original value for audit. Migration 004.

---

### ✅ Parent task ID for interruption tracking
When a new task starts while another is PAUSED, links via `parent_task_id`. Records `interruption_type` (urgent|scheduled_override|distraction|unknown). Paused session stays unclosed for later resumption. Migration 005.

---

### ✅ Task substitution tracking
When a task is DELETED and a new task is created in the same/overlapping slot within 10 minutes, bidirectional linkage: `replaces_task_id` / `replaced_by_task_id`. Best-effort, non-blocking. Migration 006.

---

### ✅ Analytics: pause_pattern, interruption/substitution rates, self-consistency
Research layer additions: per-session pause_pattern (reasons, initiators, first_pause_at_minute), parent_task_id, replaces_task_id. Summary: interruption_rate, substitution_rate, self_consistency_scores (per category+time_of_day variance of discrepancy).

---

### ✅ Enforce min_sessions in insights engine (LYR-061)
Global gate: MIN_SESSIONS=3 enforced. `_insight_discrepancy_signal()` now returns None instead of a noise "no clear link yet" message when no real signal found.

---

### ✅ Unplanned reason capture
`unplanned_reason` enum on retroactive endpoint: `unexpected_task` / `forgot_to_log` / `planning_friction` / `spontaneous_decision`. Implemented in v1.4 (migration 008).

Different reasons need different interventions:
- friction → simplify input
- forgetting → gentle interception
- spontaneous → anchor planning

---

### 🟢 Duration-reflection correlation analysis
Track session duration vs post_task_reflection score. If longer sessions consistently show lower reflection, cognitive degradation within sessions is measurable without BCI.

Computable from existing data — add to `GET /v1/analytics/discrepancy` research layer.

---

## v1.4 — Cascade Analytics (research layer)

*Discovered April 5, 2026. See MANIFESTO.md "The Cascade Failure Discovery".*

### ✅ GET /v1/analytics/cascade

New endpoint returning cascade failure metrics per day and across days.

**Response:**
```json
{
  "daily": [
    {
      "date": "2026-04-05",
      "cascade_score": 0.5,
      "morning_anchor_executed": false,
      "first_skip_time": "06:00",
      "first_skip_category": "fitness",
      "consecutive_skip_sequences": [["Gym", "SWE backlog"], ["CSE281 lecture"]],
      "total_planned": 6,
      "total_executed": 2,
      "total_skipped": 3
    }
  ],
  "summary": {
    "avg_cascade_score": 0.5,
    "morning_anchor_execution_rate": 0.0,
    "skip_propagation_probability": 0.67,
    "most_cascade_prone_category": "fitness",
    "most_cascade_prone_time_of_day": "morning"
  }
}
```

---

### ✅ Add cascade metrics to existing analytics

In `GET /v1/analytics/discrepancy` research_layer summary:
- `cascade_score` for the queried date range
- `morning_anchor_executed` boolean per day
- `skip_propagation_probability` across all sessions

---

### 🟢 Expose session_index_in_day in task responses

Already computed in analytics, not returned in task endpoints. Expose in:
- `GET /v1/tasks/query` responses
- `GET /v1/tasks/{task_id}` response
- `GET /v1/analytics/discrepancy` sessions (already present)

Required for cascade analysis and sequence-aware insights.

---

## v1.5 — Adaptive Planning

### 🔴 Estimate adjustment in task creation
When user creates a task, if bias_factor data exists for that category + time_of_day:

Return adjusted estimate alongside planned:
```json
{
  "task_id": "...",
  "planned_duration_minutes": 60,
  "adjusted_estimate_minutes": 108,
  "adjustment_basis": "Your morning development tasks run 1.8x planned on average (7 sessions)",
  "confidence": "medium"
}
```

Agent presents both and asks user which to use.

---

### 🟡 Gentle interception — unplanned session capture
When user sends any message to Telegram without an active timer, after 9am:

Ask once per 2-hour window: "Are you working on something? (yes/no)"
- Yes → create task flow
- No → ignore, don't ask again for 2 hours

Not a reminder. A soft capture hook. Implemented as OpenClaw SKILL.md rule.

---

### 🟡 Night-before anchor scheduling
Prompted by Lyra at 9-10pm:

"Schedule tomorrow in 60 seconds. What are your 2-3 main blocks?"

Minimal input — title + duration only. No conflict checking. Just anchors.

Anchor-based planning is more resilient than full-day planning. Reduces unplanned execution rate.

---

### 🟡 Contextual metadata capture
Add optional fields to task creation: `sleep_hours`, `prior_task_count_today`, `time_since_last_break_minutes`.

These are covariates that may improve bias_factor prediction beyond the 1-5 readiness scale. If they do, they carry the nuance that the Likert scale can't. If they don't, the scale is sufficient.

Resolves validity threat VT-2 (see MANIFESTO.md).

---

### 🟡 Task complexity rating
Add optional `complexity` field (1-3: routine / moderate / novel) to task creation.

Analyze whether complexity is a stronger predictor of delta than category label. "Development" means CSS debugging AND distributed systems architecture — complexity disambiguates.

---

### 🟢 Onboarding model for first correction moment
When Lyra delivers the first bias_factor insight to a new user:

Frame it as pattern recognition, not accusation:
- ❌ "You consistently overestimate your ability"
- ✅ "Your data shows a pattern: when you feel highly ready, tasks tend to take longer than planned. You're not alone — this is one of the most common patterns we see."

Pre-survey the user's self-model before correction: "Do you think your morning coding estimates are usually accurate?" If they already suspect, correction is welcome. If they don't, progressive framing is needed.

**This is the retention variable most likely to kill or save the product.**

---

### 🟢 Hawthorne effect control period
During Phase 1B onboarding, run 3-5 days of delta-only tracking (no readiness capture). Compare delta distributions between measurement-on and measurement-off periods.

If distributions differ significantly, readiness capture itself is a confound. If they don't, the instrument is passive enough.

Resolves validity threat VT-1 (see MANIFESTO.md).

---

### 🟢 Anchor adherence rate metric
After anchor scheduling is built, measure: what percentage of anchor blocks were actually executed within ±30 min of planned start?

Compare anchor adherence rate vs full-schedule adherence rate. Hypothesis: anchors hold better than full plans.

---

## v1.6 — Planning Friction Elimination

### Cognitive Friction Reducers

### 📋 FEATURE J — "Yesterday's Wins" reverse planning
Instead of blank-slate morning planning, Lyra starts with:
"Yesterday you completed: [list]. What carries over or builds on this?"

- **Trigger:** Morning briefing or first message of the day
- **Requires:** Query EXECUTED tasks from yesterday, show titles + durations
- **Psychology:** Momentum-based planning — continuation not creation
- **Zero new data required** — already in DB

---

### 📋 FEATURE K — One Domino commitment
Minimum viable planning flow:
1. Lyra: "Pick one task that must happen tomorrow to feel like a win."
2. User picks one → Lyra suggests 1-2 micro-tasks from history patterns
3. Everything else stays flexible/untracked

- **Endpoint:** `POST /v1/schedule/anchors` with exactly 1 primary anchor
- **Psychology:** Eliminates decision paralysis, creates first domino
- **Relates to:** v1.5 night-before anchor scheduling (2-3 blocks). This is the minimal version — one anchor only.

---

### 📋 FEATURE L — "What's Already Decided?" scan
Before any planning prompt, query:
- Today's recurring tasks
- Already-scheduled PLANNED tasks
- Prayer times (when Aladhan integration exists)

Output: "Tomorrow already has [N] fixed blocks (prayer 5:30, lecture 11am, gym template). What's left to decide?"

- Frames planning as gap-filling, not blank-slate building
- Reduces perceived planning load by showing what's already handled

---

### 📋 FEATURE M — Last Action Inference
If user sends any Telegram message while:
- A task's planned start time has passed
- No active stopwatch
- Task is still PLANNED

Lyra asks: "Looks like [task] was scheduled to start — working on it? (start timer / skip / not yet)"

- One tap. Turns passive chat into opportunistic tracking.
- **Implementation:** SKILL.md rule — on every message, check for overdue PLANNED tasks with no active stopwatch.
- **Differs from** v1.5 gentle interception: that targets *unplanned* sessions (no scheduled task). This targets *overdue planned* tasks.

---

### 📋 FEATURE N — Voice Delta Dump
After natural break or session end via voice note:
User sends voice: "Just finished debugging, took longer because of X"

OpenClaw transcribes → extracts: task reference, duration estimate, reason → creates retroactive session automatically. Zero typing friction.

- **Implementation:** OpenClaw Talk mode already supports voice notes. Parse transcript for: task title, duration, reflection, unplanned_reason.

---

### 📋 FEATURE O — Auto-pause on inactivity (v1.7 candidate)
If no Telegram activity for 20+ minutes during active timer:
- Auto-pause the stopwatch
- Next message: "Timer was auto-paused after 20 min inactivity. Resume or log reason?"

Reduces manual pause tagging for natural breaks.

- **Implementation:** APScheduler job checking active sessions + last_seen_active timestamp.

---

### 📋 FEATURE P — Friction Score (research layer)
Track per day:
- `planning_messages`: number of messages spent scheduling
- `correction_count`: readiness corrections + retroactive fixes
- `initiation_delays`: avg minutes late to start
- `timer_miss_rate`: tasks executed without timer

Combine into `daily_friction_score` (0-10, lower = less friction).

- Add to `GET /v1/analytics/discrepancy` summary
- Add to weekly insights: "Your planning friction dropped X% this week."
- **This makes the system self-aware** — quantifies the friction reduction features' actual impact

---

## v1.8 — Feedback Loop Closure & Friction Reduction

*Added April 8, 2026 — from research session on EMA compliance, reference class forecasting, and adaptive scheduling.*

**Numbering note:** Features in this section use F6–F15. F1–F5 are not defined in this file; this batch was numbered relative to an external session index. Features J–P (v1.6) use a separate alphabetical scheme for cognitive friction reducers — the two systems are independent.

**Overlap declarations:**
- F6 and F7 share the same underlying data as v1.5 "Estimate adjustment in task creation" (bias_factor per category+time). Trigger points differ: v1.5 fires at single-task creation, F6 fires at session stop, F7 fires at full-week commit. All three are additive.
- F10 (execution probability) is orthogonal to v1.4 bias_factor (duration accuracy). Bias_factor answers "how long will this actually take?" F10 answers "will I do it at all?" Different metrics, different interventions.
- F13 (optimal window) is a higher-order synthesis of F10 + F7 + discrepancy data. Should not be built before F10 and bias_factor are stable.
- F14 (honest schedule) depends on F7 + F10. Cannot generate predicted schedule without both duration (F7) and execution probability (F10).

---

### 📋 F6 — Calibration nudge at moment of reflection

After every session stop, if the user has ≥5 sessions in that category: surface the running calibration alongside the delta. Do not wait for a dashboard — deliver at the exact moment the experience is fresh.

Example output on stop: *"Ran 22 min over plan. Your avg delta for development: +19 min. You've underestimated this category 7/9 times. Consider scheduling 20% more next time."*

- **Data threshold:** 5 sessions per category
- **Schema changes:** None — consumes existing `delta_minutes`, `executed_duration_minutes`, `category`
- **Research layer:** delta, bias_factor (closes the loop from existing computed data)
- **Depends on:** v1.4 bias_factor computation endpoint
- **Note:** Distinct from v1.5 estimate adjustment, which fires at scheduling time. This fires at stop time — different psychology, different intervention window.

---

### 📋 F7 — Shadow schedule — planned vs predicted at scheduling time

When the user is about to commit a weekly or daily plan, show two versions side by side: the aspirational schedule (what they entered) and the predicted schedule (bias_factor-adjusted durations + execution probability per slot). Show the gap and any downstream conflicts created by realistic estimates.

Example: *"Your plan: 14 tasks, 11.5 hrs. Predicted: 9 tasks, ~7 hrs active. The 5 most likely to slip: [list]. Adjust?"*

- **Data threshold:** 5 sessions per category (bias_factor threshold); F10 execution probability needed for full version — partial version (duration-only shadow) usable earlier
- **Schema changes:** None — computed on demand from bias_factor endpoint + F10 data
- **Research layer:** delta, bias_factor
- **Depends on:** v1.4 bias_factor endpoint; full version also depends on F10

---

### 📋 F8 — Cascade interrupt prevention — real-time warning before skip confirms

When user confirms a skip, before writing to DB: query cascade history for that task's category and time-of-day. If skip → cascade has occurred in ≥50% of historical instances, surface a warning before finalizing.

Example: *"Skipping morning fitness has cascaded to your afternoon session 4/6 times. Still skip? [Yes] [Reschedule instead]"*

- **Data threshold:** 3 cascade events per category (low threshold — cascade signal is strong even at small n)
- **Schema changes:** None — reads existing cascade analytics from `GET /v1/analytics/cascade`
- **Research layer:** cascade
- **Depends on:** v1.4 cascade analytics endpoint

---

### 📋 F9 — Resistance signature per category — surface avg initiation delay, ask user why, replay their answer next time

Once avg `initiation_delay_minutes` for a category exceeds a threshold (e.g., consistently >15 min), surface it once and ask: *"You consistently start writing tasks 23 min late. What makes starting harder? [answer]"* Store the answer. Next time that category is scheduled, prepend the user's own answer to the start notification.

The system uses its own delay measurement to prompt a self-authored intervention, then replays it back at the moment of friction.

- **Data threshold:** 5 sessions per category with `initiation_delay_minutes` populated
- **Schema changes:** New field `initiation_resistance_note` (text, nullable) on `CategoryMapping` table — or a new `user_category_notes` table keyed by category. One-time per category.
- **Research layer:** new (`resistance_signature` — derived from initiation_delay, not currently surfaced as a named metric)

---

### 📋 F10 — Execution probability matrix — P(execute | category × time_of_day)

Compute a 2D probability table: given a task of category X scheduled in time-of-day bucket Y, what is the historical execution rate? Expose as `GET /v1/analytics/execution_probability`.

Distinct from bias_factor: bias_factor is *how long* when executed; execution probability is *whether* execution happens at all. Together they answer both planning questions.

Example finding: gym tasks before 8am execute at 12%, gym tasks at 7pm at 71% — directly actionable scheduling guidance.

- **Data threshold:** 3 sessions per (category × time_of_day) bucket — minimum; 10+ per bucket for meaningful signal
- **Schema changes:** None at capture level — all fields (`category`, `planned_start_utc`, `state`) already exist. New analytics endpoint needed.
- **Research layer:** new (`execution_probability` — orthogonal to bias_factor and discrepancy)

---

### 📋 F11 — Planning hangover detection — test whether large planning sessions correlate with lower execution rate same/next day

Hypothesis: creating many tasks in a single planning session produces an illusion-of-progress effect that reduces execution drive on the same or following day. Measure: count tasks created per day (`source=MANUAL`, grouped by `created_at` date) vs execution rate for that day's tasks. Compute correlation.

If correlation is significant and negative, this contradicts standard productivity advice ("plan your week Sunday") and is the kind of finding that constitutes the "surprising result" needed for research validity.

- **Data threshold:** 10+ days with ≥1 multi-task planning session; meaningful signal at 20+ days
- **Schema changes:** None — `created_at` and `state` already exist. Planning intensity is computable as count of tasks created within a short window. If explicit planning session tagging needed: add `planning_session_id` (nullable UUID) to Task.
- **Research layer:** new (`planning_hangover_coefficient` — correlation between tasks_created_per_day and execution_rate_same_or_next_day)

---

### 📋 F12 — "Done but differently" capture — scope_changed field on stop with enum

A critical data gap: tasks completed in a different form than planned are currently forced into EXECUTED (misleading) or SKIPPED (inaccurate). On session stop, optional question: *"Did you do what you planned, or something adjacent?"* If adjacent: classify the deviation.

Enum values: `scope_expanded` | `approach_changed` | `merged_with_other` | `interrupted_by_dependency`

This adds an entire analytical dimension: tasks with `scope_changed` have structurally different delta distributions than clean executions — lumping them together contaminates the discrepancy signal.

- **Data threshold:** 0 — enriches data from day 1; analysis meaningful at 10+ scope_changed events
- **Schema changes:** New `scope_changed` boolean field + `scope_change_type` enum field on Task (nullable, set only on stop if user selects "adjacent"). Migration required.
- **Research layer:** new (`scope_change_rate` per category; also filters delta and discrepancy analyses for execution purity)

---

### 📋 F13 — Optimal window detection — behavioral fingerprint: (time_of_day × category × prior_task_state × day_of_week) combination with lowest delta + highest focus

After sufficient data: identify the multi-dimensional combination of contextual factors that produces the lowest duration delta, highest post_task_reflection, and fewest pauses for each user. Present as a single personalized insight.

Example: *"Your clearest execution window: Tue/Thu 10am–12pm, after a reading session, for development tasks. Your data, not generic advice."*

This is personally calibrated and unreachable via external sources. It also directly validates the core research hypothesis: that measuring these dimensions produces actionable, individual-specific signal.

- **Data threshold:** 20+ sessions distributed across multiple time-of-day and day-of-week combinations; earlier runs will find local optima only
- **Schema changes:** None — synthesizes `planned_start_utc`, `category`, `post_task_reflection`, `executed_duration_minutes`, `delta_minutes`, `pause_count`. No new fields needed.
- **Research layer:** new (`optimal_window_signature` — aggregates delta + discrepancy + execution_probability)
- **Depends on:** F10 for execution probability component; v1.4 bias_factor for duration component

---

### 📋 F14 — The honest schedule — aspirational vs predicted side-by-side before week commits

Before the user finalizes a week's plan: generate two parallel schedules. Aspirational: what they entered. Predicted: bias_factor-adjusted durations + F10 execution probabilities applied to each slot. Show the gap. Flag tasks most likely to slip. Ask: adjust now, or proceed with the aspirational plan?

Does not block commitment — user can override. The goal is to make the implicit explicit at the moment of commitment, not after failure.

- **Data threshold:** 5+ sessions per category (bias_factor minimum); F10 execution probability meaningful at 3+ sessions per bucket
- **Schema changes:** None — computed on demand; no persistence required
- **Research layer:** delta, bias_factor, execution_probability
- **Depends on:** F7 (shadow schedule per task), F10 (execution probability matrix); F14 is the week-scope composition of both

---

### 📋 F15 — Intention stability tracking — track gap between created_at and planned_start_utc + reschedule history as proxy for commitment quality

A task created 5 minutes before its start time differs from one created 3 days in advance. Tasks repeatedly rescheduled represent a third failure mode distinct from execution failure or skip: *intention instability* — you keep intending to do it but keep deciding not to at the last moment.

Compute per task: `planning_horizon = (planned_start_utc - created_at).minutes`. Track `reschedule_count`. Hypothesis: low execution rate correlates with high reschedule_count, not low planning_horizon — the rescheduling behavior is the signal, not the initial lead time.

- **Data threshold:** 0 — `planning_horizon` is computable from existing fields immediately. `reschedule_count` requires schema change — currently rescheduling updates `planned_start_utc` without incrementing a counter.
- **Schema changes:** New `reschedule_count` integer field (default 0) on Task, incremented in `reschedule_task()`. Alternatively: task history/audit table if full reschedule timestamps are needed. Minimum viable: counter only.
- **Research layer:** new (`intention_stability_score` — combined planning_horizon + reschedule_count; feeds into execution prediction model as input feature)

---

## v1.7 — Multi-user

### 🟡 User table + timezone per user
Replace single USER_TIMEZONE env var with per-user timezone stored in DB.

Required before any multi-user deployment. Single env var is load-bearing now but won't scale.

---

### 🟡 Auth layer
Currently single-user, no auth. Before any public deployment:
- API key per user
- Telegram user_id → user mapping
- Rate limiting per user

---

### 🟢 Comparative analytics
"Users with your profile (high pre, variable post) average X% estimation error vs Y% for other types."

Only meaningful with 10+ users. Backlog until Phase 1B.

---

## v2.0 — ML Layer

### 🟡 Delta prediction model
Input features:
- pre_task_readiness
- task_category
- time_of_day
- session_sequence_position (task 1 vs task 4 in day)
- previous_session_delta
- unplanned_execution_rate (recent)
- day_of_week

Target: delta_minutes

Start with linear regression. Add complexity only if needed.

**Trigger condition:** 30+ sessions per user with clean data.

---

### 🟢 User clustering
K-means or similar on behavioral profiles:
- Consistent overestimator
- Consistent underestimator
- Accurate but bypasses planning
- Reactive executor (high unplanned rate)

Each cluster gets different intervention strategy.

---

## v3.0 — BCI Integration

### 🟡 Cognitive session logging
`POST /v1/cognitive/log`

Accepts EEG state snapshot during task execution.

**Validity gate before implementation:**
- Run simultaneous EEG + self-report sessions (minimum 20 per subject)
- Estimate per-source SNR: test-retest reliability of EEG markers vs self-report scores
- Combine via Bayesian weighting proportional to individual signal-to-noise ratios
- High correlation → BCI confirms self-report (validation, less new info)
- Low correlation → BCI captures different construct (interesting, more total info)
- Both outcomes are useful. Neither replaces the other.

---

### 🟡 BCI bridge
`lyra_bci_bridge.py`

Receives EEG state from BR41N.IO pipeline, maps to cognitive state, feeds `/v1/cognitive/log`.

---

### 🟢 Replace post-task reflection with EEG
Only after BCI validity gate passes. Not before.

---

## Research Outputs

### 🟡 Paper 1
"Metacognitive discrepancy as predictor of execution failure in knowledge workers"

**Trigger:** 30-60 days data, any predictive signal in discrepancy → delta correlation.

**Venue candidates:** CHI, UIST, Behavior Research Methods.

---

### 🟡 Paper 2
"Sequential task abandonment in knowledge workers: evidence for a cascade failure model of daily execution"

**Independent of discrepancy hypothesis.** Fastest path to publication — data already being collected from Day 1, effect visible in 2 days.

**Core finding:** Skipping task N increases P(skip task N+1), modulated by category, time of day, and sequence position. Also incorporates unplanned execution rate as a secondary construct — measures whether the planning layer is being used at all.

**Venue candidates:** CHI, CSCW, Behavior Research Methods.

---

### 🟢 Paper 3
Cognitive-behavioral loop modeling. After ML layer validates.

---

## OpenClaw / Agent Layer

### 🔴 LYR-053 — Exec approval not auto-approved on Telegram
curl commands trigger approval requests on every backend call.
Fix: add curl to exec-approvals.json allowlist permanently. See current workaround.

### 🟡 LYR-059 — Haiku 4.5 uses curl instead of HTTP tool
Root cause: OpenClaw HTTP tool not reliable for Haiku. curl fallback triggers approvals.
Fix: either force HTTP tool usage in SKILL.md or ensure curl always allowlisted.

### ✅ LYR-061 — Insights fire before min_sessions_required
Fixed: MIN_SESSIONS=3 gate enforced. `_insight_discrepancy_signal()` returns None instead of noise message.

### 🟡 LYR-056 — Multi-task chaining not supported
"Schedule X then Y" creates only first task.
Fix: parse chained requests in agent or add batch create endpoint.

### 🟢 OpenClaw tool schema
Structured tool definitions instead of natural language SKILL.md.
More reliable instruction following, less prompt engineering.

---

## Infrastructure

### 🟢 Per-model timeout in OpenClaw
Blocked on upstream: openclaw/openclaw#43946
When shipped: set 120s timeout for Qwen3.5:9b fallback specifically.

### 🟢 CI tests for new features
Current GitHub Actions only covers basic pytest. Add:
- Stopwatch pause/resume integration test
- Discrepancy layer data integrity test
- Retroactive endpoint test

### 🟢 Demo GIF
Record 30-second Telegram flow: schedule → start → pause → resume → stop → insight.
Required for README, BR41N.IO submission, LinkedIn.

---

*See LYRA_BUGS.md for active bug tracker (LYR-001 through LYR-077).*
*See MANIFESTO.md for research and product philosophy.*
*See CLAUDE.md for developer context and agent architecture.*
