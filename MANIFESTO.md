# Lyra Secretary — Manifesto v1.2
*Written: April 4, 2026. Day 1 of the discrepancy experiment.*
*Revised: April 5, 2026. Day 2 — cascade failure discovery, validity threats updated, repo alignment pass.*

---

## What This Is

Lyra Secretary is not a productivity app.

It is a measurement instrument for human self-perception and its relationship to execution. The scheduling is a delivery mechanism. The data is the product.

The central question: **Are humans wrong about themselves in a structured way that predicts failure?**

If yes — the error is modelable, correctable, and eventually preventable.
If no — the data tells us that too, and we pivot.

Everything in this system exists to answer that question cleanly.

---

## The Core Variables

**Delta** — the gap between what you planned and what you executed.
```
delta = planned_duration - executed_duration
```
This is ground truth. It cannot lie. It is the thing you trust.

**Discrepancy** — the gap between how you felt before a task and how you actually performed during it.
```
discrepancy = |pre_task_readiness - post_task_reflection|
signed_discrepancy = post_task_reflection - pre_task_readiness
```
This is the thing you test. It may or may not predict delta.

Epistemic caveat: post_task_reflection is a self-report of a continuous internal process recalled at session end. This is not moment-to-moment sampling — it is the user's memory of their average cognitive state during the task, which is systematically biased toward peak and end experiences (Kahneman's peak-end rule). post is noisier than it appears. This doesn't break the model but means discrepancy scores carry recall bias. Acknowledged as a validity threat in the research framing.

**Initiation delay** — the gap between when you planned to start and when you actually started.

**Unplanned execution rate** — tasks you executed without scheduling. Discovered on Day 1.
```
unplanned_tasks / total_tasks
```
This is the third variable nobody measures. See dedicated section below.

---

## The Three Behavioral Classes

| Class | Description | Measured |
|-------|-------------|----------|
| Planned → Executed | Normal flow with delta + discrepancy | ✅ |
| Planned → Not executed | Abandoned or skipped tasks | ✅ |
| Unplanned → Executed | Task started without scheduling | ✅ v1.4 |

The third class was discovered on Day 1 of the experiment. It reveals whether the planning layer is even being used — which is upstream of delta itself.

---

## The Two Failure Modes

**Estimation failure** — you planned 1 hour, it took 2. Delta is large. This is what most apps measure.

**Initiation failure** — you bypassed the system entirely. Unplanned execution rate is high. This is what no app measures.

Lyra measures both.

---

## The Core Hypothesis

> High perceived readiness → systematic underestimation of task duration → execution overrun

The discovery from Day 1: when pre_task_readiness is 4-5, actual time is consistently 1.5-2x the planned duration. The model:

```
actual_time ≈ planned_time × bias_factor(pre_state, task_category)
```

Where `bias_factor ≈ 1.5-2.0` when pre ≥ 4. This is an early observation from a single subject on Day 1. Requires validation across sessions and subjects before the multiplier is meaningful.

---

## The Prediction Direction

```
discrepancy → delta
```

Not the reverse. Discrepancy is the predictive lens. Delta is ground truth.

Phase 1 (current): test whether discrepancy contains predictive information about delta.
Phase 2 (if signal exists): context → predicted discrepancy → predicted delta.
Phase 3 (BCI, conditional): validated EEG markers → true state → predicted delta.

### The Temporal Clarification

Discrepancy and delta are both observed at the same moment — when a task ends. So discrepancy is NOT a real-time forward predictor within a single session. The prediction operates historically:

```
past discrepancy patterns → model → future delta predictions
```

After N sessions, the system learns: "When this person rates readiness 4-5 on coding tasks in the morning, their discrepancy tends to be high and their delta tends to be large." That learned model then applies to the next session before it starts.

The forward prediction comes from the model, not from a single session's discrepancy. This lag is a feature — the system gets more accurate over time. But it requires honest framing: Lyra is a learning instrument, not a real-time sensor. Value compounds across sessions.

---

## What We Are NOT Building

- A todo list
- A time tracker
- A mood journal
- A gamified habit app
- A calendar

We are building a system that learns how a specific human is wrong about themselves and uses that to make them more accurate over time.

---

## System Architecture

```
Telegram → OpenClaw (AI agent) → FastAPI Backend → TaskManager → SQLite + Redis → Notion
                                        ↕
                                   APScheduler
                          (reminders, overflow, sync retry,
                           abandoned task detection)
```

**Key design decisions:**
- UTC internally, local time at boundaries — never mix
- Immutable history — executed tasks are permanent data points
- 30-second undo window via Redis
- Pause/resume support — prayer breaks excluded from delta
- Hard Rules in SKILL.md — AI agent cannot confirm without backend response

---

## The Analytics Stack

**Research layer** — for the experiment:
- per-session delta, discrepancy, initiation delay
- time-of-day performance
- session sequence position
- pause count and total paused minutes
- unplanned execution rate per day

**Product layer** — for the user:
- discrepancy score (abs)
- signed discrepancy (direction of error)
- depletion rate
- behavioral insights (rule-based, day 3-4 mirror moments)

**Insights engine** — fires after session 3:
- time-of-day bias detection
- readiness-outcome correlation
- estimation accuracy trend
- abandonment pattern
- best performing category
- discrepancy signal

---

## The Most Original Variable

Unplanned execution rate is the differentiator.

Every productivity system measures estimation error (delta). Nobody measures whether the planning layer is being used at all.

This variable answers a different question — not "how wrong were your estimates" but "did you even estimate."

| Pattern | Meaning |
|---------|---------|
| High delta + low unplanned rate | Bad estimator — uses the system, miscalibrated |
| Low delta + high unplanned rate | Good estimator who bypasses planning |
| High delta + high unplanned rate | Reactive execution — no model possible yet |
| Low delta + low unplanned rate | Calibrated, structured — the target state |

The third pattern is where most people actually live. Lyra is the first system that can detect it, measure it, and eventually interrupt it — not by forcing logging, but by making the value of the planning layer visible over time.

### The Three Behavioral Profiles

**Profile 1: Calibrated Executor**
- Low unplanned rate, low delta
- Uses the planning layer, estimates accurately
- The target state. Lyra's value here is confirmation and trend monitoring.
- Detectable via: unplanned_rate < 0.15, avg |delta| < 10 min, execution rate > 0.8

**Profile 2: Reactive Executor**
- High unplanned rate, variable delta
- Executes effectively but bypasses planning entirely
- Good work happens — it's just not structured. The planning layer adds no value yet.
- Detectable via: unplanned_rate > 0.4, initiation_status mostly "retroactive" or unplanned
- Intervention: Layer 3 gentle interception, not forced logging

**Profile 3: Overplanner**
- High task creation rate, low execution rate, long initiation delays
- Feels productive during planning. Delta never computed because timer never starts.
- The planning layer becomes the activity itself.
- Detectable via: high create count + low EXECUTING transition rate + high avg initiation delay
- No other system distinguishes this from genuine productivity.

Each profile needs a different intervention. Lyra must detect which profile applies before offering corrections — giving a Reactive Executor estimation feedback is useless; giving an Overplanner more planning tools is harmful.

This taxonomy deserves its own paper independent of the discrepancy hypothesis.

---

## The Cascade Failure Discovery

*Discovered: April 5, 2026. Day 2 of the experiment.*

Observation: Skipping Gym at 6am cascaded into skipping SWE backlog at 7:30am, skipping CSE281 at 2pm, and restructuring the entire afternoon.

This is not noise. This is a behavioral pattern nobody has measured cleanly.

### The Cascade Hypothesis

Skipping task N increases the probability of skipping task N+1, with effect size modulated by:
- **Task category** — does skipping fitness cascade differently than skipping study?
- **Time of day** — morning skips more damaging than afternoon skips?
- **Sequence position** — first task of day is load-bearing
- **Initiation delay of task N** — partial start vs full skip

### Why This Is Researchable Now

The data structure already captures everything needed:
- Which task was skipped (`state = SKIPPED`)
- Sequence position (`session_index_in_day`)
- Category
- Time of day
- What came before and after (timestamp ordering)
- Whether the cascade continued (subsequent states)

No additional instrumentation needed. The signal is already being collected.

### The Independent Research Finding

This does not depend on the discrepancy hypothesis surviving.

Even if discrepancy → delta shows no signal:
- The cascade pattern is a standalone finding
- Measurable from existing data
- Potentially publishable independently

### Paper 2 (faster path than Paper 1)

Title candidate: *"Sequential task abandonment in knowledge workers: evidence for a cascade failure model of daily execution"*

Core finding: Skipping task N increases P(skip task N+1), modulated by category, time of day, and sequence position.

Why faster than Paper 1:
- Doesn't require discrepancy signal validation
- Structure already captured in DB from Day 1
- Effect visible in 2 days of data
- No ML needed — pure behavioral statistics

Venue candidates: CHI, CSCW, Behavior Research Methods

### Cascade Metrics to Add to Analytics

1. **cascade_score** per day: `consecutive_skips / total_planned_tasks`

2. **first_task_completion_rate**: Did the first planned task of the day execute? Correlation with `rest_of_day_completion_rate`

3. **skip_propagation_probability**: `P(task N+1 skipped | task N skipped)` — segmented by: same category, different category, same time block

4. **morning_anchor_score**: Boolean — did the first morning task (before 9am) execute? Track correlation with `total_day_delta`

### Sleep as Leading Indicator

Sleep hours may be the strongest upstream predictor of cascade failure — stronger than readiness, category, or time of day.

The hypothesis: sleep < 6h → morning anchor skip → cascade. If true, sleep is the leading indicator and cascade is the trailing one. The intervention shifts from "don't skip the first task" to "protect your sleep."

Testable with existing data + one new field: `sleep_hours` (optional, captured at first task start or retroactively). If sleep correlates with first-task skip rate and cascade_score more strongly than pre_task_readiness does, sleep becomes the primary input to the prediction model.

This is not a wellness feature. It is a measurement correction: without sleep data, the bias_factor model attributes morning overruns to estimation error when they may be fatigue artifacts.

**Status:** `sleep_hours` field not yet implemented. Add to v1.5 as optional morning check-in.

---

## The Desirability Assumptions

| ID | Assumption | Risk | Test |
|----|-----------|------|------|
| DA-1 | Users feel enough frustration from underestimating tasks to want correction | If no pain, no usage | Ask: how often do tasks take longer than expected? |
| DA-2 | Users accept being told they're wrong | Resistance to correction | Show pattern, ask "would you follow this adjustment?" |
| DA-3 | Users rate readiness consistently for 14+ days | Biggest retention risk | 10-day experiment, current test |
| DA-4 | Mirror moment creates retention | Insight interesting once, ignored after | Check logging frequency before/after first insight |
| DA-5 | Users prefer auto-adjustment over manual planning | Power users want control | A/B: manual vs Lyra-adjusted estimate |

**The single kill assumption across all three:**
> Users will tolerate being wrong about themselves long enough to benefit from correction.

**Hidden dependency:** This assumes correction feels like recognition, not accusation. "Your readiness-4 estimates need 1.8x adjustment" lands very differently depending on whether the user already suspects this about themselves or is hearing it for the first time.

The product gap: there is no onboarding model for the moment of first correction. DA-2 marks it as a risk but doesn't define what acceptance looks like in practice. Operationalizing that moment — framing, timing, tone — is the retention variable most likely to determine whether the insight compounds or kills the user before value accumulates.

---

## The Viability Assumptions

| ID | Assumption | Risk | Test |
|----|-----------|------|------|
| VA-1 | Insight is strong enough to charge for | Free alternatives everywhere | ≥20-30% say yes to $3-5/month |
| VA-2 | Using Lyra reduces estimation error over time | No improvement = no retention | Track error = actual/planned, check ↓ trend |
| VA-3 | Retention survives cognitive friction | Most apps die here | ≥30-40% retention at day 7 |
| VA-4 | Telegram + Notion is sufficient UX | Friction causes drop-off | Observe complaints, measure dropoff |
| VA-5 | One developer can maintain and iterate solo | Complexity accumulates | Can you run 14 days without system breakdown? |

---

## The Experiment

**Subject:** Ali Nasser (test subject zero)
**Period:** April 4 - April 15, 2026 (10 days)
**Hypothesis:** |pre - post| predicts delta across sessions

**Sacred variables:**
- pre_task_readiness — always captured, never assumed
- post_task_reflection — always captured after stop, never skipped
- delta — always recorded, never manually edited
- timestamps — always correct

**Sacred rules:**
- No skipping sessions
- No editing data after the fact
- Pause before prayer, discard if forgot
- Tasks max 90 minutes — load-bearing, not arbitrary (see below)
- Before sleep: 2-minute retroactive log for untracked sessions

**The 90-minute cap — decision, not preference:**
The cap bounds delta variance, keeps sessions statistically comparable, and prevents a 3-hour deep work block from polluting the model with a single outlier delta. Sessions over 90 minutes must be split into sub-tasks before starting. Each sub-task gets its own pre/post readiness capture. Splitting changes the measurement: each split is an independent data point, not a continuation. This is intentional — long blocks have multiple cognitive phases and averaging them loses the signal.

**The single-subject problem:**
Ali Nasser is the worst possible generalization target. Highly self-aware, systematically reflective, already primed to notice metacognitive patterns. If discrepancy predicts delta for this subject, it tells us almost nothing about whether it predicts delta for someone who has never thought about metacognition in their life.

Phase 1B recruitment must deliberately target subjects who are NOT like the primary researcher — different cognitive styles, different planning habits, different relationships to self-monitoring.

Day 2 revealed another specificity: Ali's cascade failures are morning-anchor dependent — skipping the first task (fitness, 6am) cascades into the rest of the day. This may be a personality-specific pattern, not a universal one. Phase 1B subjects must explicitly include people who are NOT morning-dependent — those whose day structure doesn't hinge on a single anchor task — to test whether cascade failure is a general phenomenon or a morning-routine artifact.

**Success condition at Day 5-7:**
> "I can predict when I'll fail before I start."

Not perfectly. Better than random.

---

## The Phase Map

**Phase 0 — Validate signal (now)**
Run 10-day experiment. Does discrepancy contain predictive information about delta?

**Phase 1A — No signal**
Drop discrepancy as core variable. Keep delta as primary. Introduce estimation error, drift, friction, consistency. Build behavioral system (product first, ML later). BCI becomes optional enhancement, not core.

**Phase 1B — Signal exists**
Scale to 10-30 users. Deliberately recruit subjects unlike the primary researcher. Validate stability across subjects and cognitive styles. Then ML layer. Then BCI as signal enhancement.

**Phase 2 — Scale**
Adaptive planning engine. Auto-calibrate estimates based on historical bias per user per task category. No ML needed yet — pure behavioral.

**Phase 3 — BCI integration (conditional)**
Entry point: BR41N.IO hackathon, April 2026.

Critical validity gate before BCI replaces post-task reflection:
EEG cognitive state ≠ self-reported readiness. They may correlate strongly, weakly, or not at all. Required validation:
- Simultaneous EEG + self-report sessions
- Correlation analysis between EEG markers and pre/post scores
- If r > 0.6: BCI enhances the model
- If r < 0.4: BCI is a parallel signal, not a replacement

BCI is not rhetorical vision. It is a testable hypothesis that requires its own experimental validation before integration.

**Phase 4 — Research**
Paper 1: "Metacognitive discrepancy as predictor of execution failure" — after 30-60 days data.
Paper 2: "Sequential task abandonment in knowledge workers" — cascade failure model + unplanned execution rate. Independent of discrepancy hypothesis. Data already being collected from Day 1.
Paper 3: cognitive-behavioral loop modeling — after ML layer works.

---

## The Unplanned Execution Solution Layers

**Layer 1 — Retroactive capture (v1.4)**
`POST /v1/stopwatch/retroactive` — log completed sessions after the fact. Tagged as `initiation_status: "retroactive"`. End-of-day friction: minimum.

**Layer 2 — Pattern detection (v1.4)**
`unplanned_execution_rate` in analytics. Detect structured vs chaotic days. Correlate with delta, discrepancy, sleep.

**Layer 3 — Gentle interception (v1.5)**
When user is active in Telegram without active timer: "Are you starting something?" One tap. Not a reminder — a soft capture hook.

**Layer 4 — Pre-commitment (v1.5)**
Night-before anchor scheduling. 2-3 blocks only. Anchor-based planning is more resilient than full-day planning.

**Layer 5 — Signal framing (model)**
Not "user forgot to log." Yes "system detected unstructured execution event." This is data, not error.

---

## Two Documents, Not One

This manifesto is internal documentation. When the audience changes:

**For researchers:** The methodology document should isolate the measurement instrument from the product layer. Clean operational definitions, session protocol, validity threats, and statistical analysis plan. No mention of startup or funding. Key threats to address: peak-end bias in post measurement, single-subject generalization limits, temporal lag in prediction.

**For founders/investors:** The pitch isolates the product insight. "We can predict when you'll fail before you start" — with bias_factor as the proof point. No mention of research methodology or academic framing. Key hook: we measure whether the planning layer is being used at all. Nobody else does this.

These are separated when the audience requires it. Right now both live here intentionally — this is Day 1.

---

## What Success Looks Like

**Before ML:**
Lyra corrects your time estimates based on your historical bias. You say 1 hour. Lyra says 1h45. You finish in 1h50. That's a product.

**After signal validation:**
Lyra knows your overconfidence profile by task type and time of day. "Your morning coding estimates need 1.8x adjustment. Your afternoon study sessions are accurate."

**After subject 2-30:**
The bias_factor is no longer personal — it's a distribution. Some people consistently overestimate. Some underestimate. Some are accurate but bypass planning entirely. Lyra knows which type you are within 5 sessions.

---

## Validity Threats and Mitigations

*Added: stress test of the manifesto's assumptions and measurement model.*

### VT-1: Hawthorne Effect on Readiness Capture
**Threat:** The act of rating readiness changes task approach. A person who rates themselves "2" may try harder to compensate; a person who rates "5" may coast. The measurement instrument is not passive — it intervenes.

**Mitigation:** Run a control period (3-5 days) where tasks are tracked with delta only, no readiness capture. Compare delta distributions between measurement-on and measurement-off periods. If distributions differ significantly, the readiness capture itself is a confound. If they don't differ, the instrument is passive enough.

**Status:** Not yet tested. Should be designed into Phase 1B protocol.

### VT-2: 5-Point Scale Resolution
**Threat:** A 1-5 Likert scale has only 5 discrete values. "Readiness 4" after a full night's sleep and "readiness 4" after a 2am session are the same number representing different states. The scale is too coarse for the precision the bias_factor model claims.

**Mitigation:** Add contextual metadata alongside the rating: sleep hours (optional), prior task count today, time since last break. These cost nothing to capture and can be analyzed as covariates. If they improve prediction, the 1-5 scale was losing signal. If they don't, the scale is sufficient. Do NOT switch to a 1-100 slider — it adds decision fatigue and creates false precision. Instead, let context variables carry the nuance.

**Status:** Metadata fields not yet implemented. Add to v1.5 backlog.

### VT-3: Signed vs Absolute Discrepancy
**Threat:** `|pre - post|` = 3 could mean overconfidence (pre=5, post=2) or underconfidence (pre=2, post=5). These are opposite failure modes requiring opposite interventions. Using abs() as the primary metric hides the direction of error.

**Mitigation:** Already partially addressed — `signed_discrepancy` exists in the analytics layer. But the manifesto and insights engine should use signed as primary, abs as secondary. Overconfidence (positive signed) and underconfidence (negative signed) should be tracked and reported separately. The bias_factor model should split on direction.

**Status:** signed_discrepancy computed but not foregrounded in insights. Needs insights engine update.

### VT-4: Category Taxonomy Validity
**Threat:** The bias_factor model depends on per-category analysis, but "development" could mean CSS debugging or distributed systems architecture. The static keyword seed table doesn't capture task complexity, which likely affects delta more than category label.

**Mitigation:** Add optional `complexity` field (1-3: routine / moderate / novel) to task creation. Analyze whether complexity is a stronger predictor of delta than category. If so, replace or augment category in the bias_factor model. This is cheap to capture — one extra number at creation time.

**Status:** Not yet implemented. Add to v1.5.

### VT-5: Session Splitting Artifact
**Threat:** The 90-minute cap forces splitting long tasks into sub-tasks. But the second sub-task inherits cognitive state from the first — they are not independent observations. This violates the statistical assumption of independence that underlies per-session analysis.

**Mitigation:** Tag split sessions with a `parent_session_id` so they can be analyzed both independently AND as a group. Allow >90min sessions but flag them in analytics with a warning rather than hard-blocking. Let the data show whether long sessions have genuinely different delta characteristics. The cap is a guideline, not an enforcement — the system should measure accurately regardless of session length.

**Status:** `parent_session_id` not implemented. 90-minute cap is protocol-level, not system-enforced.

### VT-6: No Control for External Interruptions
**Threat:** Delta measures planned vs actual, but "actual" includes interruptions (Slack, phone calls, unplanned meetings). A 30-minute interruption during a 60-minute task looks like a 90-minute execution — a 30-minute delta that has nothing to do with estimation accuracy.

**Mitigation:** Extend the pause system. Currently pause supports prayer/break. Add an `interruption` pause type that logs the cause. Distinguish: planned pause (prayer), voluntary pause (break), involuntary pause (interruption). All paused time is excluded from delta, but interruption frequency is a separate analytical signal — high interruption rate correlates with role type and environment, not cognitive state.

**Status:** Implemented in v1.4. `pause_reason` (6 enum values: mental_fatigue, distraction, task_difficulty, external_interruption, intentional_break, prayer) and `pause_initiator` (self/external) added to `POST /v1/stopwatch/pause`. Migration 004.

### VT-7: Anchor Scheduling Has No Evidence Base
**Threat:** The manifesto claims "anchor-based planning is more resilient than full-day planning" but cites no evidence. This drives a major v1.5 feature (Layer 4 pre-commitment).

**Mitigation:** This is testable with existing data after 14 days. Compare days with full schedules (>4 planned tasks) vs days with 2-3 anchor blocks. Measure unplanned_execution_rate and average delta for each group. If anchored days show better metrics, build the feature. If not, deprioritize.

**Status:** Requires 14+ days of data. Analysis can be added to insights engine.

### VT-8: Missing "Why" Behind Unplanned Execution
**Threat:** The system detects unplanned execution but doesn't capture why it happened. Was the task unexpected? Did the user forget to log? Was planning friction too high? Without "why," the intervention layer (Layer 3) can't be calibrated.

**Mitigation:** When retroactive logging (Layer 1), add optional `unplanned_reason` enum: `unexpected_task` / `forgot_to_log` / `planning_friction` / `spontaneous_decision`. Different reasons need different interventions: friction → simplify input, forgetting → gentle interception, spontaneous → anchor planning.

**Status:** Implemented in v1.4. `unplanned_reason` field (unexpected/forgot/friction/spontaneous) added to `POST /v1/stopwatch/retroactive` and Task model. Migration 008.

### VT-9: No Cognitive Degradation Model
**Threat:** The manifesto assumes cognitive state is stable within a session. But for 45-90 minute blocks, attention degrades. post_task_reflection captures the average (or rather, the peak-end recall), but the trajectory matters — a session that starts focused and ends distracted is different from one that starts slow and enters flow.

**Mitigation:** Short-term: track session duration vs reflection score. If longer sessions consistently have lower reflection, degradation is real and measurable without BCI. Medium-term: BCI provides the moment-to-moment data that self-report cannot. Long-term: model the cognitive trajectory per session, not just the endpoint.

**Status:** Duration-reflection correlation can be computed from existing data. Add to analytics.

### VT-10: First Correction Moment is Undesigned
**Threat:** DA-2 ("users accept being told they're wrong") is the most dangerous assumption. The manifesto identifies the risk but offers no operational mitigation beyond "design the phrasing."

**Mitigation:** Before showing any correction, pre-survey the user's self-model: "Do you think your morning coding estimates are usually accurate?" If they already suspect they overestimate, the correction is welcome (recognition). If they believe they're accurate, the correction needs progressive framing — show the raw data first, let them draw the conclusion, then offer the adjustment. The system should never say "you're wrong" — it should say "here's what your data shows" and let the user decide whether to act on it.

**Status:** No pre-survey or progressive framing designed. Critical for Phase 1B onboarding. Add to v1.5 backlog.

### VT-11: System-Generated Data Contamination
**Threat:** AI agent acting autonomously can create false behavioral data — starting timers, filling readiness/reflection scores, bypassing early-stop gates. Discovered when Claude Code agent autonomously executed a Lyra build task during testing (LYR-078). Zero-duration session with self-filled pre/post ratings. The system cannot distinguish human-initiated from agent-initiated sessions.

**Mitigation:** `POST /v1/tasks/{task_id}/void` marks corrupted sessions as `initiation_status="system_error"`, excluded from all analytics but preserved in history. Prevention requires agent-side guardrails (exec-approval enforcement) rather than backend detection — the backend sees identical HTTP requests regardless of source.

**Status:** Void endpoint implemented in v1.4. Prevention depends on OpenClaw exec-approval fixes (LYR-071, LYR-078).

---

## What This Is Really About

You are testing two things:

1. **Can the gap between how a person thinks they are and how they actually perform be measured, learned, and eventually closed?** This is the discrepancy hypothesis — the original question.

2. **Does skipping one task cause the next to fall?** This is the cascade failure discovery — observed on Day 2, independent of discrepancy, and potentially the faster path to a publishable finding.

Not "can I be more productive."
Not "can I build a startup."

If discrepancy predicts delta — the product, the paper, the BCI, the startup are all downstream.
If cascade failure is real — Paper 2 ships first, independent of whether discrepancy pans out.
If neither — you still have a working adaptive scheduler, 62 commits of solid engineering, an international hackathon entry, and the clearest possible signal to pivot before overinvesting.

Either way, you win.

The experiment has started. Stay in measurement mode.

---

*"The system is not trying to make you productive. It's trying to make you accurate."*

*Lyra Secretary v1.4 — April 5, 2026*
*Manifesto v1.2 — revised April 5, 2026 (cascade failure discovery added)*
