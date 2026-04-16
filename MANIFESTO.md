# Lyra Secretary — Manifesto v1.4
*Written: April 4, 2026. Day 1 of the discrepancy experiment.*
*Revised: April 5, 2026. Day 2 — cascade failure discovery, validity threats.*
*Revised: April 8, 2026. Day 4 — kill criterion, pre-registered analysis rules.*
*Revised: April 10, 2026. Day 7 — duality reframe, BCI complementary-signal model, VT-5 decision.*
*Revised: April 14, 2026. Day 11 — framing clarification (research as QC infrastructure); VT-19 & VT-20; Rules 8 & 9; profile taxonomy methodological note; retention-before-polish scope clarification.*

---

## Framing: Research as Quality-Control Infrastructure
*Added: April 14, 2026.*

Lyra's core thesis is behavioral correction at scale. Measurement discipline, pre-registered hypotheses, validity threats, and eventual research publication serve this thesis by producing product accuracy users can trust. Research outputs are not Lyra's primary deliverable — they are quality-control and credibility infrastructure for the product.

This distinction matters for strategic decisions. "Kill H1 if correlation fails" is not abandoning the project; it is identifying that a specific cold-start prediction mechanism didn't work and iterating to the next candidate. "Publish Paper 1" is not the goal; it is a side-effect that simultaneously sharpens the measurement instrument and builds user trust in the product's claims.

All subsequent sections should be read through this framing.

---

## What This Is

Lyra Secretary is a measurement-backed productivity tool. Most productivity tools assume their insights are accurate. Lyra tests its own.

The tool layer delivers scheduling, timer management, and behavioral feedback. The research layer validates whether those insights actually predict anything. Neither is primary. The tool fails if the research is invalid — you are acting on noise. The research is academic if the tool is not used — you have no data.

The central question: **Are humans wrong about themselves in a structured way that predicts failure?**

If yes — the error is modelable, correctable, and eventually preventable.
If no — the data tells us that too, and we pivot.

Everything in this system exists to answer that question cleanly, while delivering enough value that the operator keeps using it long enough to generate the data.

---

## Shipping Philosophy — Retention Mechanism First

*Added: April 14, 2026. Locks the pre-alpha shipping order after the feedback/output-loop audit.*

Lyra has two failure modes a pre-alpha can hit:

1. **Correctness failure.** The instrument ships with bugs, edge-case mishandling, or state inconsistency. This is visible, fixable, and ordinary engineering.
2. **Retention-mechanism failure.** The instrument ships correct but invisible. Users are told "we are measuring you" but never see the measurement come back. The feedback/output loop that makes Lyra feel like a *mirror* rather than a *logger* is what closes the Error → Exposure → Adjustment triplet (see `docs/phase_6_architecture_backlog.md` §"Calibration as Learning Velocity, Not Performance"). Without that loop, no correctness work will save retention, because there is nothing to retain to.

**Pre-alpha shipping order is retention mechanism first, correctness polish last.**

What this means operationally:

- Every research-relevant signal the backend already computes — `micro_mirror`, `calibration_nudge`, `duration_delta_minutes`, `signed_discrepancy`, `is_future_task`, `mid_task_completion_pct`, `task_completion_percentage`, `initiation_delay_minutes`, `insights[]` — must have a visible user-facing surface before the alpha ships. Computed-but-discarded is worse than not computed, because it burns the server work without closing the loop for the user.
- Correctness fixes (e.g., edit-click vs multi-select checkbox, modal stale-defaults, stale-session-recovery verification) matter, but they do not ship before the surfaces. A polished product with no feedback loop churns faster than a rough product that mirrors back.
- "Insights unlock in N sessions" framing applies: measurement-state progress is legitimate and desired (see `docs/do_not_add.md` §Gamification — PERMITTED section). It is not a streak, it is not a badge, it is an honest statement of when the instrument has enough data to say something.
- Onboarding that forces users through the instrument battery *before they see the product* is retention-hostile and is deferred to May 1+. Direct entry to `/today` with progressive instrument capture ships first.

Concretely ordered in `docs/building_phases.md` §Phase 4.5 under Tier 1 (retention architecture), Tier 2 (operator-verifiable bugs), Tier 3 (infrastructure), Tier 4 (onboarding ceremony). Tier 1 is the shipping gate for the alpha. Tiers 2–4 can slip a week; Tier 1 cannot.

This section is load-bearing for the retention outcome. The May 21 retention checkpoint is the test of whether this philosophy survived contact with ten non-operator users. If retention fails *and* Tier 1 shipped completely, the finding is "the feedback loop wasn't enough" and Phase 1A pivot (delta-only) activates. If retention fails *and* Tier 1 slipped, the finding is unreadable — we shipped a logger and measured logger retention.

**Companion principle (Apr 16, 2026):** the retention-before-polish ordering is one axis; `docs/design_patterns/rules_vs_agency.md` §Structural Invariants vs Behavioral Constraints is the other. Research discipline stays *invisible* to the user by being expressed as structural invariants the system enforces silently, not as behavioral constraints the user has to work around. Every proposed hard-block rule must pass the diagnostic test in that doc before shipping.

### Scope of the retention-before-polish principle
*Added: April 14, 2026.*

The retention-before-polish ordering **applies to**:
- UI bugs (timer glitches, rendering issues, slow loads)
- State-machine edge cases that users can notice and report
- Feature completeness (non-critical affordances)

It **does NOT apply to**:
- Correctness of computations users attribute to the product's understanding of them (`bias_factor` calculations, `calibration_nudge` output, insights)
- Data cleanliness underlying those computations
- Measurement pipeline integrity

Research basis: Li et al. 2010 and Epstein et al. 2015 show personal informatics users disengage rapidly when early insights appear inaccurate, before habit forms. Wrong insights in a self-tracking context produce trust collapse that bugs do not.

Practical implication: clean the data pipeline before routing `micro_mirror`, `calibration_nudge`, or insights to users. Tests that assert current computation outputs on fixture data must exist before UI surfacing. This is a **precondition** for Tier 1 retention shipping, not a parallel activity.

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

We are building a system that learns how a specific human is wrong about themselves and uses that to make them more accurate over time. The product value is the accuracy improvement. The research value is proving whether the accuracy improvement is real.

We are not building a planning tool that requires planning effort. The system should make planning nearly invisible by Day 14. Friction score is the product metric that proves this.

---

## System Architecture

```
Web UI (Next.js)            ─┐
Telegram → OpenClaw (agent)  ├→ FastAPI Backend → TaskManager → SQLite + Redis → Notion
                             ─┘        ↕
                                  APScheduler
                         (reminders, overflow, sync retry,
                          overdue task detection)
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

The 3 behavioral profiles are the research typology — they describe the phenomenon being studied. The 5 operational archetypes (see `docs/methodology.md §1`) are the product clustering — they describe how the product assigns priors to specific users. These are different abstraction levels, not different counts of the same thing.

This taxonomy deserves its own paper independent of the discrepancy hypothesis.

**Methodological note on profile taxonomy** *(added April 14, 2026)*: The three profiles (Calibrated Executor, Reactive Executor, Overplanner) are currently descriptive heuristics derived from operator dogfood data. They are not validated clusters. Formal clustering validation (Gaussian mixture model, stability analysis, silhouette scores per Jain 2010; model-based clustering per Murphy 2004) requires n ≥ 50 users minimum and is deferred to Phase 5.5 post-alpha. Until validated, profiles should be treated as a communication tool for describing observed patterns, not as research findings about user types.

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
Entry point: BR41N.IO hackathon, October 2026 (Path B in `docs/building_phases.md` — preferred for research clarity over the earlier April slot).

BCI and self-report are two noisy estimators of an underlying cognitive state. Neither is ground truth. The integration model combines them with Bayesian weighting proportional to each source's individual signal-to-noise ratio — estimated per user from simultaneous EEG + self-report sessions.

Required validation before integration:
- Simultaneous EEG + self-report sessions (minimum 20 per subject)
- Per-source SNR estimation: test-retest reliability of EEG markers vs self-report scores
- Correlation analysis between EEG markers and pre/post scores

Interpretation of correlation outcomes:
- **High correlation:** BCI confirms self-report. Validating, but BCI adds less new information — the combination improves precision through averaging, not through capturing a new construct.
- **Low correlation:** BCI and self-report capture different constructs. This is *interesting*, not bad — the combination carries more total information than either source alone, and the Bayesian weights will reflect which source is more predictive of delta for each user.
- **Both outcomes are useful.** Neither replaces the other. The question is not "does BCI replace self-report" but "what is the optimal weighting of two imperfect signals for predicting delta."

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

**Decision (Apr 10, 2026):** Mitigation (parent_session_id column + tagged split sessions) not implemented as of v1.5. Decision deferred to Paper 1 analysis phase: either implement the mitigation before running the H1 correlation, or acknowledge the session-independence limitation in the paper's limitations section. Current default: acknowledge rather than fix, because the 90-minute cap has been protocol-enforced by the operator since Day 1 and real splitting has been rare in practice.

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

### VT-12: 5-Point Scale Saturation at the Ceiling
**Threat:** Related to but distinct from VT-2 (coarse resolution). The 5-point Likert ceiling causes *compression* at the top of the scale: operator rates most sessions 4 or 5 on readiness, collapsing the readiness distribution into a narrow band regardless of true variation in cognitive state. A scale that saturates at the top cannot distinguish "genuinely sharp" from "socially desirable self-presentation" from "rating inflation from measurement fatigue." If most sessions pile up at 4–5, the H1 correlation is being tested on a degenerate predictor — not because discrepancy doesn't predict delta, but because pre_task_readiness has no room left to vary downward as the operator gains practice at self-rating.

**Mitigation (three pre-registered distinguishing analyses for the H1 report, see analysis rule 7 below):**
1. **Motivated-underestimation correlation (VT-12a).** Report the within-subject correlation between `pre_task_readiness` and `planned_duration_minutes`. If high readiness co-occurs with shorter plans ("I'm sharp, I'll knock this out"), the readiness signal is entangled with planning ambition — not a pure cognitive-state estimate. Report this correlation alongside the H1 ρ.
2. **Readiness=5 variance analysis (VT-12b).** Among sessions rated readiness=5, report the variance of `duration_delta_minutes`. If delta variance is high at readiness=5, the ceiling is hiding real state variation (the scale can't distinguish "sharp enough to plan accurately" from "overconfident"). If delta variance is low at readiness=5, the ceiling is capturing a genuinely stable sharp state.
3. **Task category distribution by readiness (VT-12c).** Report the cross-tab of readiness ratings × task category. If readiness=5 concentrates in one or two categories (e.g., familiar dev tasks), the scale is acting as a proxy for task familiarity rather than cognitive state. This distinguishes readiness-as-state from readiness-as-task-stance.

**Status:** VT-12 documented April 14. Scale is not changed (VT-2 already decided against a 1-100 slider). The three distinguishing analyses are committed to the H1 report under analysis rule 7.

### VT-13: Category-Type Semantic Drift
**Threat:** The `category` field in the Task model blurs two semantically distinct classes: **estimable** tasks (planning meaningfully predicts duration — dev, writing, study) and **time_anchored** tasks (duration is fixed by external schedule — prayer, sleep, meals, meetings). Bias_factor analysis, per-category delta distributions, and the H1 correlation all treat both classes as if their planned_duration was a genuine self-estimate. For time_anchored tasks it is not — it is a clock value. Contaminating the bias_factor corpus with time_anchored rows produces a model that claims to predict estimation bias but is partly fitting clock regularity.

**Mitigation:** Add `category_type` enum to the category_mapping table (values: `estimable`, `time_anchored`) OR an `is_anchor` boolean on Task. Exclude `category_type = 'time_anchored'` (equivalently `is_anchor = true`) rows from bias_factor computation, from the H1 correlation, and from the cascade_score denominator. Retain them as behavioral data (they still inform scheduling, unplanned-execution, and initiation-delay analyses) but tag them at analysis time. This is a schema change, not a philosophical one — prayer, sleep, and meals stay as first-class categories in the product.

**Status:** VT-13 documented April 14. Schema change promoted from Phase 6 to Phase 5 pre-alpha (see `docs/dogfood_findings_living.md` — `category_type` / `is_anchor` bundle). H1 analysis on April 15 runs on a dataset with `is_anchor=true` rows excluded in the query, even if the schema landing slips past the analysis date — the exclusion is applied by title-keyword filter as a fallback (prayer, sleep, meal, eat, lunch, dinner, breakfast).

## Cohort start dates and contamination notes

Operator (cohort=operator) data spans Apr 5 — present.

Pre-Apr-13 contamination (4 rows):
- 3 voided tasks were auto-transitioned to SKIPPED by
  the overdue_tasks job before the voided_at filter
  was added (commit 2af80f0). These rows have
  state=SKIPPED but voided_at IS NOT NULL.
- 1 voided task had its stopwatch session auto-closed
  by stale_session_recovery 38 minutes after voiding,
  producing a 65.5-hour paused-session ghost (LYR-103).
- All 4 rows are test tasks created during dogfood
  development. None affect real behavioral analytics.

Analytic exclusion: All queries against operator data
filter voided_at IS NULL. The contaminated rows are
naturally excluded by this filter regardless of their
state value. Pre-registered: cohort=operator clean
analytics begin Apr 13, 2026 (post-audit-fix date).
Pre-Apr-13 data is usable for instrument validation
but not for primary H1 correlation analysis.

VT-14: Pre-fix bug class allowed background jobs to
mutate voided task state. Mitigated commit batch
Apr 13 (commits 2af80f0, 2afd063, 7823424, 05d3e0a).
All known affected rows enumerated above.

### VT-15: Anonymized Retention Trust-Correlated Bias
**Threat:** Users who opt out of anonymized research retention on account deletion may differ systematically from users who accept retention. Users with lower trust in the system are more likely to opt out, removing their behavioral patterns from the product research corpus. The retained dataset is not a representative sample of all users who left.

**Mitigation:** Track opt-out rate as a separate behavioral signal. Report it alongside any product research findings derived from retained data. If opt-out exceeds 30%, flag all retention-based findings as potentially biased.

**Status:** VT-15 documented April 14. Retention checkbox ships with two-stage delete account flow.

### VT-16: Cross-Population Methodology Error
**Threat:** Lyra produces data for two distinct research populations with different inclusion criteria. Confusing the populations across analyses is a methodology error that invalidates both sets of findings.

**Mitigation:** Pre-register population definitions. Population 1 (hypothesis research): cohort=alpha_v1, 30+ sessions, stable measurement conditions, H1 falsification. Population 2 (product research): all available user behavior including churn patterns and cohort=deleted_anonymized. Tag all analyses with which population they draw from. Code review for cross-population contamination.

**Status:** VT-16 documented April 14. Two-class framing below.

### VT-17: Instrument-Intervention Threat (Pause Prediction)
**Threat:** Lyra's Phase 4.5 Tier 1.5 pause-prediction notifications fire predicted pause times back to the user as a behavioral suggestion ("you usually pause around 8:15 AM — on break?"). If the notification itself changes pause behavior — by anchoring pause timing to the prediction, or by inducing pauses that would not otherwise occur — then the pause data collected during the notification window is no longer an observation of natural pause behavior. It is partly a measurement of the instrument measuring itself.

**Distinguishing analyses** (pre-registered before feature activation — to be run at the end of the 7-day acceptance window per user):
- **VT-17a — Pause-time anchor drift.** For each user with a notification window ≥ 7 days, compute Spearman ρ between day-index-within-window and `|actual_pause_time − predicted_pause_time|`. Negative ρ = pause time is drifting toward the prediction (suggestion anchoring). Report ρ with n and p. Threshold for "anchoring detected": ρ ≤ −0.40 with p < 0.05 and n ≥ 20 pause events.
- **VT-17b — Induced pause rate.** Paired comparison per user of pauses-per-active-session in the baseline window (pre-notification, ≥ 7 days) vs. the notification window. Wilcoxon signed-rank. Threshold for "induced pauses detected": pause rate increase ≥ 50% with p < 0.05.
- **VT-17c — Natural-vs-prompted split.** For users who have both notified and un-notified mornings within the notification window (prediction gated ≥ 3 pauses on ≥ 3 distinct days per hour-cell, so some mornings won't fire), compare the distribution of first-pause-of-day times between the two subsets. Mann-Whitney U. Threshold for "prompted behavior detected": shift in median ≥ 5 minutes toward prediction time with p < 0.05.

**Mitigation:**
- Feature is gated by the Tier 1.5 kill criterion (acceptance rate < 0.20 after 7 days kills the feature per-user). VT-17a/b/c findings can independently trigger a kill even if acceptance rate is within range.
- If VT-17a or VT-17c trips, pause-time predictions are reported in Phase 6 analysis as "conditional on no-notification baseline" only — predictions fired during the notification window are excluded from bias_factor inputs for pause-timing categories.
- Pre-registered acceptance_rate formula (below) is frozen at feature launch; no post-hoc redefinition.

**Pre-registered acceptance-rate formula (pause prediction kill criterion):**
```
acceptance_count(user, window=7d)
  := count of pause_prediction_log rows where
       fired_at ∈ window
       AND EXISTS a pause_event with paused_at_utc
           ∈ [predicted_at − 1 min, predicted_at + lead_minutes + 5 min]
       AND user_id matches
total_fires(user, window=7d)
  := count of pause_prediction_log rows where
       fired_at ∈ window AND parent_firing_id IS NULL
       (snoozes excluded from denominator — re-fires are new events)
acceptance_rate := acceptance_count / total_fires
```
Thresholds (per-user, not aggregate): acceptance_rate ≥ 0.40 = ship; < 0.20 = kill. Window starts at each user's first pause_prediction_log row. Formula is frozen at launch; any change is a new pre-registration with its own window start.

**Status:** VT-17 documented April 14, 2026. Pre-registered before any pause_prediction_log data lands. Distinguishing analyses and acceptance-rate formula are immutable.

### VT-19: Post-task endogeneity in `signed_discrepancy`
**Threat:** `post_task_reflection` is captured after the user observes session outcome. Outcome knowledge contaminates post-ratings through hindsight bias (Fischhoff 1975), effort heuristic (Kahneman), and reconstructive memory (Koriat 1997). Because `signed_discrepancy = post_task_reflection − pre_task_readiness` includes `post_task_reflection`, correlations between `signed_discrepancy` and `duration_delta_minutes` may reflect mechanical coupling rather than psychological prediction. Related to common-method bias (Podsakoff et al. 2003) but with additional temporal information leakage.

**Mitigation:** Secondary H1 test using `pre_task_readiness` alone vs. `duration_delta_minutes` (pre-registered in Rule 8). If the pre-only correlation is meaningfully weaker than the signed-discrepancy correlation, interpret with caution. Phase 3 BCI markers provide eventual independent validation of pre-state reliability.

**Status:** VT-19 documented April 14, 2026. Secondary analysis pre-registered (Rule 8). Phase 3 BCI markers provide eventual independent validation of pre-state reliability.

### VT-20: Cascade hypothesis confounded by structural task dependency
**Threat:** The observed cascade pattern `P(skip N+1 | skip N)` may reflect task graph dependency rather than psychological cascade. Tasks that logically depend on each other (gym → post-workout breakfast), share time blocks, or share context naturally co-skip without requiring a psychological mechanism. Ego depletion — the implicit psychological model underlying cascade — failed replication (Hagger et al. 2016; Carter et al. 2015).

**Mitigation:** Structural dependency analysis. For each cascade event, compute whether task N and task N+1 share category, share time block, or share keyword overlap in titles. Report the cascade effect **with and without** structural controls. If the effect substantially attenuates under controls, the cascade is primarily structural. If the effect survives, a psychological mechanism is supported — not ego depletion per se, but schedule disruption + re-planning cost (González & Mark 2004).

**Status:** VT-20 documented April 14, 2026. Structural analysis added as a pre-registered rule for Paper 2. The cascade cell in `notebooks/operator_analytics.ipynb` is annotated to require the with-and-without-controls report at Paper 2 analysis time.

### VT-21 candidate: Narrative-layer influence on subsequent measurements
**Threat:** Surfaced `micro_mirror` and `calibration_nudge` text become part of the user's mental model of the task. Future `planned_duration_minutes` estimates and readiness ratings may be influenced by internalized narrative ("I usually overrun on dev"). The instrument's outputs change the measured behavior — same class as VT-17 (pause prediction intervention) but different mechanism (narrative internalization vs prompted action).

**Mitigation:** Track surface-fired vs surface-not-fired session metadata via `reflection_view_log` (shipping in LYR-098 Commit 2b). Compare subsequent `planned_duration_minutes` distributions and readiness ratings between surface-exposed and surface-naive sessions per category × time_of_day. If post-exposure estimates systematically shift toward bias_factor suggestions, narrative internalization is confirmed and analysis must be stratified.

**Status:** VT-21 candidate documented April 15, 2026. Detection analysis added to operator interrogation checklist Day 30 milestone. Stratified analysis required for any post-surface H1 correlation reporting.

## Anonymized Retention Policy

Anonymized retention serves product research only:
- Retention/churn pattern analysis
- Phase 6 user-typology classification (Calibrator / Acknowledger / Illusion Preserver / Overcorrector)
- Identifying which features fail for users who leave

Pre-registered exclusion: cohort=deleted_anonymized rows are excluded from H1 primary correlation analysis. The H1 dataset consists of users who completed at least 30 sessions under stable measurement conditions (cohort=alpha_v1, post-retention-validation period). Churned-user data informs product design but does not contribute to hypothesis testing.

Future publication of any findings derived from retained data would require separate re-consent from affected users and is not covered by this policy.

## Two-Class Research Framing

Lyra produces data for two distinct research uses:

1. **Hypothesis research** (Paper 1, H1 falsification): requires stable measurement conditions, 30+ sessions per user, cohort=alpha_v1 exclusively. Churned-user data excluded by pre-registration.

2. **Product research** (retention management, Phase 6 design): includes all available user behavior including churn patterns. Anonymized retention of deleted-account data permitted with user consent to enable this work.

Different data populations serve different research questions. Confusing the populations across analyses is a methodology error and is documented as VT-16.

---

## What This Is Really About

You are testing two things:

1. **Can the gap between how a person thinks they are and how they actually perform be measured, learned, and eventually closed?** This is the discrepancy hypothesis — the original question.

2. **Does skipping one task cause the next to fall?** This is the cascade failure discovery — observed on Day 2, independent of discrepancy, and potentially the faster path to a publishable finding.

Not "can I be more productive."
Not "can I build a startup."

If discrepancy predicts delta — the product, the paper, the BCI, the startup are all downstream.
If cascade failure is real — Paper 2 ships first, independent of whether discrepancy pans out.
If neither — you still have a working adaptive scheduler, 118+ commits of solid engineering, an international hackathon entry, and the clearest possible signal to pivot before overinvesting.

Either way, you win.

The experiment has started. Stay in measurement mode.

---

*"The system makes you productive by making you accurate — and it proves its accuracy claims with data, not marketing."*

*Lyra Secretary v1.5 — April 10, 2026*
*Manifesto v1.3 — revised April 10, 2026*
*Manifesto v1.4 — revised April 14, 2026 (VT-12, VT-13, analysis rule 7, Shipping Philosophy)*
*Manifesto v1.5 — revised April 15, 2026 (VT-19, VT-20, VT-21 candidate; Rules 8–9; profile taxonomy note; retention-scope clarification)*

---

## Kill Criterion — H1 (Discrepancy → Delta)

*Committed: April 8, 2026. Day 4 of the discrepancy experiment.*
*This is a pre-registered falsification rule, fixed before the analysis. It is not interim analysis. It is the rule the analysis must obey.*

### Hypothesis under test (H1, signed form)

> Operator overconfidence — captured as a negative `signed_discrepancy` (`post_task_reflection − pre_task_readiness < 0`, i.e. felt ready but performed below expectation) — systematically predicts execution overrun (`duration_delta_minutes < 0`, i.e. executed longer than planned, per the manifesto's delta sign convention).
>
> Operationally: across paired sessions, `signed_discrepancy` and `duration_delta_minutes` should be **positively** correlated (both move negative together when overconfidence produces overrun, both move positive together when underconfidence accompanies underrun).

This is the signed reformulation of the original `|pre − post| → |delta|` hypothesis. It is more falsifiable (predicts a *direction*, not just a magnitude) and more actionable (overconfidence and underconfidence require opposite corrections — see VT-3).

### Falsification rule

At the close of the experiment, H1 is **falsified** if **all three** of the following hold on the analysis-eligible session set (EXECUTED, `initiation_status != "system_error"`, both `pre_task_readiness` and `post_task_reflection` populated):

1. **n ≥ 60 paired sessions** are available. (Hard floor. Not lowered under any circumstance. If the experiment ends with fewer than 60 pairs, H1 is neither confirmed nor falsified — the experiment is inconclusive and must be extended or rerun.)

2. **Spearman ρ between `signed_discrepancy` and `duration_delta_minutes` is < 0.20**, AND the 95% bootstrap CI for that ρ includes zero.

3. **No learning improvement**: the same correlation computed on the second half of the data (later sessions, ordered by `planned_start_utc`) is not larger than on the first half by more than Δρ ≥ 0.10. This protects against killing a hypothesis that is sharpening as the operator becomes more practiced at self-rating. The Δρ ≥ 0.10 threshold ensures that a *meaningful* improvement trend survives — a trivial 0.01 bump in the second half is noise, not learning. If the second-half ρ exceeds the first-half ρ by ≥ 0.10 but neither half individually reaches 0.20, H1 status is **TRENDING** (not falsified, not confirmed) and the experiment extends by 30 sessions.

All three must hold. Failing any one of them leaves H1 alive (TRENDING or CONFIRMED depending on effect size and CI).

### Why ρ < 0.20

Below this threshold the signal would be weaker than known noise sources in single-item Likert self-report (test-retest reliability typically ~0.5–0.7), meaning the construct could not survive its own measurement error even if real. The threshold was set conservatively *before* the post-April-15 literature review and may be tightened — but never loosened — once the lit review is complete.

### Pivot consequence (if H1 is falsified)

- `pre_task_readiness` and `post_task_reflection` capture move to **optional / research-only mode**. They are no longer prompted in the default flow.
- The system continues tracking `duration_delta_minutes`, `cascade_score`, `unplanned_execution_rate`, and `initiation_delay_minutes` as primary signals.
- Phase 1A of the Phase Map is entered: delta becomes the sole primary variable, the metacognitive layer is deprecated as a default capture, and Paper 2 (cascade failure) becomes the primary research output.
- The bias_factor model is rebuilt without the readiness inputs and tested for whether delta history alone carries enough signal to drive scheduling adjustments.

This is a real consequence with real code changes attached, not a rhetorical commitment. If the criterion fires, the capture flow changes within one week of the result.

### Sign convention note

The manifesto defines `delta = planned_duration − executed_duration`, so **overrun = delta < 0** and **underrun = delta > 0**. Under the H1 hypothesis stated above, overconfidence (signed_discrepancy < 0) should co-occur with overrun (delta < 0), which produces a **positive** Spearman ρ between the two signed variables. The criterion uses ρ as defined under this convention. Any future sign flip in the delta definition must trigger a corresponding rewrite of this section.

### What is NOT in scope of this criterion

- The cascade hypothesis is independent and has its own (forthcoming) criterion. H1 falsification does not falsify cascade.
- The bias_factor magnitude claim (`1.5–2.0` for high readiness) is a separate, downstream question. H1 only concerns whether *any* directional signal exists.
- Sleep as a leading indicator is explicitly out of scope for the April 15 analysis. It is Paper 2 territory and requires schema changes that will not be made mid-experiment.

### Day 4 anomaly note (Apr 8 diagnostic)

A median-split of `pre_task_readiness` against `duration_delta_minutes` on the n=18 paired sessions available on Day 4 showed that **low-readiness sessions outperformed sharp ones by 58 minutes** on average — the opposite of the naive planning-fallacy prediction. This is *not* H1 itself (H1 uses `signed_discrepancy = post − pre`, not `pre` alone) and does not constitute evidence for or against H1. Possible explanation: conservative planning under low readiness rather than better execution — i.e. when the operator feels drained, plans are scaled down, so the resulting delta is smaller. Examine in the April 15 analysis by comparing the distribution of `planned_duration_minutes` across low- vs high-readiness sessions before drawing any execution-side conclusions.

### Pre-registered analysis rules (committed before April 15 analysis is run)

These rules are fixed in advance to remove analyst degrees of freedom on the day of analysis. Any deviation must be explicitly justified in the writeup.

1. **Exclude retroactive sessions from the H1 test set.** Rows with `initiation_status = 'retroactive'` are excluded from the Spearman ρ computation. Reason: retroactive sessions have `planned_duration` set equal to `executed_duration` by definitional construction (see FEATURES.md, retroactive endpoint behavior — "Sets planned = executed (delta = 0 by definition)"). Their delta is 0 by fiat, not by measurement, and they would pull the H1 correlation toward zero in a way that looks like a null result but is actually an artifact of how the data was logged. Retroactive sessions remain valid for cascade analysis (Paper 2), which uses state transitions rather than delta.

2. **Category taxonomy is frozen for the Apr 4–15 window.** The set of valid categories is fixed (see `docs/product.md §1`). New keywords mapping into existing categories may be added at any time. New *categories* may not be created until after the window closes. Reason: per-(category, time_of_day) bias-factor estimation requires monotonic bucket counts; introducing a new category mid-window redistributes mass and produces false-negative bias estimates. The Apr 8 merge of `planning` → `self_reflection` is the last taxonomy edit of the window and was performed because the two categories were semantically identical (meta-work *about* the system) and one was an accidental seed-time fork.

3. **Exclude voided sessions.** Rows with `voided_at IS NOT NULL` are excluded from the H1 test set. Voided sessions are operator-flagged data quality rejects (duplicates, test entries, data_quality issues). Including them would inject known-bad data into the correlation. This exclusion was added on Apr 9, 2026, after the void mechanism was implemented in Phase 3.2.

4. **Exclude sessions with `planned_duration_minutes < 5`.** Very short planned durations (e.g., 1–4 minutes) produce delta values that are dominated by startup overhead rather than genuine planning-fallacy signal. The 5-minute floor prevents these rows from inflating ρ with noise. This threshold matches the minimum meaningful session length observed during dogfood.

5. **Prediction direction is pre-registered.** The H1 hypothesis predicts a **positive** Spearman ρ between `signed_discrepancy` and `duration_delta_minutes` (see Sign convention note above). A statistically significant *negative* ρ would be a surprising finding requiring its own explanation, not a confirmation of H1. Analysis must report the observed sign explicitly and not interpret a negative ρ as "the hypothesis works but in the other direction."

6. **No post-hoc subsetting.** The analysis may not split the data by category, time_of_day, or any other covariate and report the best-performing subset as the "real" result. Category-stratified analysis is permitted as an *exploratory* supplement (clearly labeled) but the primary result is the whole-sample ρ. If a category-stratified analysis reveals a strong signal in one category that is absent in others, this is reported as a hypothesis for future testing, not as confirmation of H1.

7. **H1 report must include the three VT-12 distinguishing analyses.** The H1 writeup reports VT-12a (within-subject ρ between `pre_task_readiness` and `planned_duration_minutes`), VT-12b (variance of `duration_delta_minutes` at readiness=5), and VT-12c (cross-tab of readiness × category) alongside the primary Spearman ρ. These are pre-registered companion analyses, not post-hoc supplements. Their purpose is to distinguish "H1 failed because the predictor is null" from "H1 failed because the 5-point scale saturated at the ceiling" from "H1 failed because readiness is a proxy for task familiarity." Without these three analyses, a null result on the primary ρ is under-determined — the experiment cannot be read. A failing primary ρ that also shows VT-12a ≥ 0.3, low VT-12b variance, and concentrated VT-12c distribution means the measurement instrument itself needs redesign before H1 can be tested again; a failing primary ρ with VT-12a near zero, high VT-12b variance, and flat VT-12c means the hypothesis is genuinely unsupported and Phase 1A (delta-only pivot) activates.

8. **Report the secondary pre-only H1 test alongside the primary.** *(Added April 14, 2026.)* In addition to the primary H1 test (Spearman ρ between `signed_discrepancy` and `duration_delta_minutes`), report the secondary test of `pre_task_readiness` alone vs. `duration_delta_minutes`. If the pre-only correlation is substantially weaker than the signed-discrepancy correlation, interpret the signed-discrepancy result with caution per VT-19 (post-task endogeneity): the stronger signed-discrepancy correlation may reflect mechanical coupling between `post_task_reflection` and session outcome rather than psychological prediction.

9. **Report the disattenuated correlation estimate alongside the observed ρ.** *(Added April 14, 2026.)* In addition to the observed Spearman ρ used for the kill criterion decision, report the disattenuated correlation estimate per classical test theory (Spearman 1904), using test-retest reliability estimates for `pre_task_readiness` and `post_task_reflection`. Explicitly acknowledge that disattenuation requires reliability estimates not directly measured in this protocol — published single-item Likert reliability ranges will be used as proxies. The disattenuated value is interpretive context for the primary result, **not a basis for changing the kill criterion post-hoc**. The kill criterion decision is made on the observed ρ.
