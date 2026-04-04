# Lyra Secretary — Feature Backlog
*Last updated: April 4, 2026*

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

### 🔴 Unplanned execution rate in analytics
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

### 🟡 Bias factor computation endpoint
`GET /v1/analytics/bias_factor`

Returns per-category, per-time-of-day multipliers:
```json
{
  "bias_factors": {
    "development_morning": 1.8,
    "development_afternoon": 1.4,
    "study_morning": 1.2,
    "fitness_any": 1.1
  },
  "sessions_required": 5,
  "ready": true
}
```

Used by: adaptive planning feature (v1.5).

---

### 🟡 Backfill endpoint for pre-fix tasks
`POST /v1/tasks/{task_id}/sync`

Force Notion sync for tasks created before timezone pipeline fix. Resolves LYR-015.

---

### 🟡 Pause reason classification
Add `pause_reason` enum to pause endpoint: `prayer` / `break` / `interruption`.

Distinguishes planned pauses from involuntary interruptions. Interruption frequency is an analytical signal — high rate correlates with environment, not cognitive state. All pause types excluded from delta.

Resolves validity threat VT-6 (see MANIFESTO.md).

---

### 🟡 Fix conflict detection on immutable tasks (LYR-070)
Filter candidate tasks in `conflict_detector.py` to `state IN ('PLANNED', 'EXECUTING')` before checking overlap. EXECUTED/SKIPPED/DELETED tasks should not block new task creation.

---

### 🟡 Enforce min_sessions in insights engine (LYR-061)
Insights fire after 1 session with noise data. Threshold check must enforce `min_sessions_required=3` before any insight is generated.

---

### 🟢 Unplanned reason capture
Add optional `unplanned_reason` enum to retroactive endpoint: `unexpected_task` / `forgot_to_log` / `planning_friction` / `spontaneous_decision`.

Different reasons need different interventions:
- friction → simplify input
- forgetting → gentle interception
- spontaneous → anchor planning

---

### 🟢 Duration-reflection correlation analysis
Track session duration vs post_task_reflection score. If longer sessions consistently show lower reflection, cognitive degradation within sessions is measurable without BCI.

Computable from existing data — add to `GET /v1/analytics/discrepancy` research layer.

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

## v1.6 — Multi-user

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
- Run simultaneous EEG + self-report sessions
- Compute correlation between EEG markers and pre/post scores
- If r > 0.6: proceed
- If r < 0.4: BCI is parallel signal only, not replacement

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
"Unplanned execution rate as a measure of planning layer adherence"

**Independent of discrepancy hypothesis.** Can be written earlier.

**Core finding:** measures whether a planning system is actually being used, not just whether estimates are accurate. New construct, underexplored in literature.

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

### 🟡 LYR-061 — Insights fire before min_sessions_required
Threshold check not enforced. Single-session "insights" are noise.
Fix: enforce min_sessions check in insights engine.

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

*See LYRA_BUGS.md for active bug tracker (LYR-001 through LYR-070).*
*See MANIFESTO.md for research and product philosophy.*
*See CLAUDE.md for developer context and agent architecture.*
