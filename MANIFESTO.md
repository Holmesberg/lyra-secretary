# Lyra Secretary — Manifesto v1.11
*Written: April 4, 2026. Day 1 of the discrepancy experiment.*
*Revised: April 5, 2026. Day 2 — cascade failure discovery, validity threats.*
*Revised: April 8, 2026. Day 4 — kill criterion, pre-registered analysis rules.*
*Revised: April 10, 2026. Day 7 — duality reframe, BCI complementary-signal model, VT-5 decision.*
*Revised: April 14, 2026. Day 11 — framing clarification (research as QC infrastructure); VT-19 & VT-20; Rules 8 & 9; profile taxonomy methodological note; retention-before-polish scope clarification.*
*Revised: April 16, 2026. Day 13 — Rule 11 no-nudge control days (VT-21 detection protocol); Rule 10 reserved.*
*Revised: April 17, 2026. Day 14 — VT-22 scope inflation hypothesis; Rules 10 & 12 (readiness-direction, mediation test); brain dump field elevated.*

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

**Companion principle (Apr 16, 2026):** the retention-before-polish ordering is one axis; `docs/design_patterns/rules_vs_agency.md` §Structural Invariants vs Behavioral Constraints is the other. *A structural invariant is a non-negotiable constraint that protects measurement integrity (single mutation authority, voided_at on every Task query, research-field NULL-not-default); a behavioral constraint is a user-facing rule that should stay soft unless it directly protects an invariant.* Research discipline stays *invisible* to the user by being expressed as structural invariants the system enforces silently, not as behavioral constraints the user has to work around. Every proposed hard-block rule must pass the diagnostic test in that doc before shipping.

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

## External Data Exclusion Rule
*Added: April 21, 2026. Pre-registered alongside the Google Calendar integration.*

When the system imports events from third-party sources (Google Calendar today; Notion, ICS, Outlook in future phases), those rows MUST carry an explicit `external_source` marker and MUST NOT be included in H1 analysis, `bias_factor` computation, or any research aggregate that assumes Lyra-native planning context.

Imported events were planned under a different affordance set with different measurement conditions — no `pre_task_readiness`, no scope commitment via description, no intent-to-measure. Including them would contaminate the H1 test set with data from a different instrument.

Implementation: imported events live in Redis (ephemeral) or in `external_event_outcome` (user-marked attendance), never in the `task` table. If a future integration persists imported items as Lyra plans, those rows carry `external_source` and every H1 query filters `WHERE external_source IS NULL`. See `docs/integrations_architecture.md §Research-integrity rules`.

---

## System Architecture

```
Web UI (Next.js)                        ─┐
Telegram (operator-only, not alpha)      ├→ FastAPI Backend → TaskManager → Postgres (prod) / SQLite (dev) + Redis → Notion
OpenClaw agent (testing/dev, not alpha)  ─┘                ↕
                                                      APScheduler
                                  (reminders, overflow, sync retry, overdue
                                   task detection, pause prediction)
```

**Key design decisions:**
- UTC internally, local time at boundaries — never mix
- Immutable history — executed tasks are permanent data points
- 30-second undo window via Redis
- Pause/resume support — prayer breaks excluded from delta
- Hard Rules in SKILL.md — AI agent cannot confirm without backend response

**User-facing vs internal interfaces (clarified April 21, 2026):** Alpha users interact via the Web UI only. Telegram and OpenClaw remain operator-only development/testing tools until components are integrated into the Lyra codebase proper. User-facing Telegram + LLM-parsed task creation ship post-retention-validation. See `docs/strategic_decisions_april_21.md §5` and `docs/building_phases.md §Phase 4.5 Tier 4`.

**Production deployment (April 16, 2026+):** Postgres via Supabase eu-west-1 (primary); SQLite retained at `.env.backup-sqlite-2026-04-16` for fast revert. Fronted by Cloudflare Tunnel from the operator's laptop at `lyraos.org` + `api.lyraos.org`. See `docs/deployment_architecture.md` for stack + recovery playbook.

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

### VT-17d: Retroactive self-report stratification (permissive acceptance rate)
*Added: April 22, 2026. Separate pre-registration with its own window start. Does NOT modify VT-17's frozen formula — parallel secondary analysis only.*

**Motivation.** Two VT-17 firings in the operator's first-week data (2026-04-21 and 2026-04-22) correctly predicted food breaks but logged `user_response='no_response'` because the operator took the breaks outside the app and didn't click Pause. VT-17's frozen formula requires a `pause_event` row in the acceptance window; absent that row, the prediction scores as a miss even when phenomenologically correct. This is an instrument-coverage gap, not a prediction failure.

**Instrument extension (shipped 2026-04-22).** A retroactive-confirmation chip on `/today` lets the operator answer "did you pause around X?" for any `no_response` firing whose predicted time has no `pause_event` within ±10 min. Chip suppression window (±10 min) is deliberately wider than VT-17's acceptance window so operators who paused *near* the prediction aren't patronized. Chip answers flow to `pause_prediction_log.user_response` as either `self_reported_yes` or `self_reported_no`. On `self_reported_yes`, a `pause_event` is created with `self_reported_retroactively=true` (alembic 030); this flag excludes it from `clock_anchor` + `work_rhythm` predictor training (no self-reinforcement) and from VT-17's primary acceptance matching (no mechanical acceptance of later firings).

**VT-17d permissive acceptance-rate formula (frozen at launch 2026-04-22):**
```
acceptance_count_permissive(user, window=7d)
  := count of pause_prediction_log rows where
       fired_at ∈ window
       AND user_response IN ('pause_now', 'self_reported_yes')
       AND parent_firing_id IS NULL
total_fires_permissive(user, window=7d)
  := count of pause_prediction_log rows where
       fired_at ∈ window AND parent_firing_id IS NULL
acceptance_rate_permissive := acceptance_count_permissive / total_fires_permissive
```

**Thresholds** (per-user, applied once the operator has been exposed to the chip for ≥7 days): permissive rate ≥ 0.40 = ship VT-17; < 0.20 = kill VT-17. Same thresholds as VT-17 strict, applied to the permissive rate. The decision uses whichever rate fires first.

**Reporting requirement.** The Paper 1 writeup MUST report VT-17 strict + VT-17d permissive side-by-side. If the rates diverge substantially (|permissive − strict| ≥ 0.15), the in-app capture gap is a load-bearing confound; the paper discusses it explicitly. If they converge (|difference| < 0.05), retroactive confirmation isn't adding decision-shifting signal and VT-17's original formula is adequate.

**Validity threats introduced by VT-17d itself.**
- **17d-α: Retroactive confirmation bias.** Users asked "did you pause?" may be more likely to answer yes than no, inflating acceptance_rate_permissive. Mitigation: the chip offers equal visual weight to Yes / No / dismiss. Track the Yes : No ratio per user; if >3:1 systematically, flag as possible confirmation bias.
- **17d-β: Memory confabulation.** Users confirming pauses up to 24h post-hoc may remember incorrectly. Mitigation: chip freshness window is 24h (CHIP_FRESHNESS_HOURS); older firings drop out. Pre-registered analysis stratifies self_reported_yes by `(now − predicted_at)` to check whether confirmation rate decays with time.
- **17d-γ: Predictor drift masking.** Retroactive pauses are excluded from predictor training (see instrument extension above) to prevent self-reinforcement, but this means the predictor's training corpus skews toward operators who DO log pauses in real time. Pre-registered analysis compares training-set pause distributions against retroactive-confirmation distributions; if they diverge, the predictor is being trained on a biased subset.

**Status:** VT-17d shipped 2026-04-22 alongside alembic 030 (pause_event.self_reported_retroactively bool), `POST /v1/pause_predictions/{id}/confirm`, `GET /v1/pause_predictions/pending-confirmation`, and the `PauseConfirmChip` UI. Window start for per-user VT-17d evaluation: first `no_response` firing after feature launch time. Formula frozen at launch per MANIFESTO pre-registration discipline.

### VT-18: *[Reserved — number skipped during April 14 batch insertion. No validity threat assigned.]*

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

**Detection protocol (formalized April 16, 2026):** pre-registered analysis Rule 11 adds a within-user control condition — randomly suppress `micro_mirror` / `calibration_nudge` / `/insights` on ~1-in-7 days beginning trusted-user week 2 — to generate paired nudge-active vs no-nudge day observations. Rule 11 specifies both the VT-21 detection criterion (systematic shift in `planned_duration_minutes` between nudge-exposed and nudge-suppressed days, controlling for category × time_of_day) and the necessity-of-nudge decision criterion (re-evaluate the mechanism if no-nudge days match or beat nudge-active days on calibration at N ≥ 30 paired days per user).

**Status:** VT-21 candidate documented April 15, 2026. Detection protocol formalized April 16, 2026 via pre-registered analysis Rule 11. Stratified analysis required for any post-surface H1 correlation reporting.

### VT-22: Scope Inflation Masquerading as Time Estimation Error
*Discovered: April 17, 2026. Emerged from readiness-inversion anomaly in operator data.*

**Threat:** The standard planning-fallacy frame (Buehler et al. 1994) interprets `duration_delta_minutes` as time estimation error — the user underestimated how long the task would take. But if `pre_task_readiness` predicts delta in the *inverse* direction (high readiness → larger overrun, low readiness → smaller overrun or underrun), this is a surprising finding that the standard frame does not predict. Several competing hypotheses could explain the readiness inversion:

**Competing hypotheses (none confirmed, all testable):**
- **(a) Scope inflation (primary candidate):** High readiness doesn't worsen time estimation — it expands the scope attempted within the stated window. Users add features, go deeper, polish. The time estimate was correct for the stated scope; the scope expanded during execution. Low readiness → scoped down → scope matched the estimate.
- **(b) Task-type confound:** High readiness may correlate with harder/more ambitious task selection. Users choose difficult tasks when feeling sharp, easy tasks when drained. The readiness signal is a proxy for task difficulty, not a causal mechanism.
- **(c) Time-of-day confound:** High readiness clusters in the morning; morning tasks may systematically differ in overrun characteristics. The readiness signal is a proxy for time-of-day, not independent.
- **(d) Motivation distortion:** High readiness may correlate with intrinsic motivation. Intrinsically motivated sessions run long because the user *wants* to continue, not because they misjudged. Low-motivation sessions finish early because the user is eager to stop.
- **(e) Novelty vs maintenance:** High readiness sessions may skew toward novel tasks (building, creating); low readiness toward maintenance (reviewing, fixing). Novel tasks have higher inherent variance.
- **(f) Domain confound:** High readiness may correlate with ambitious domains (development, building) that independently produce larger deltas. The readiness-delta relationship disappears when stratified by category.

**Status: HYPOTHESIS, not finding.** The readiness inversion is observed in operator (n=1) data. The scope inflation explanation is the most architecturally interesting because it produces a different intervention (scope adjustment vs time adjustment) and elevates the brain dump field to primary measurement status. But competing explanations (b)–(f) must be ruled out before the scope inflation mechanism is treated as confirmed. Rule 10 (readiness-direction analysis) and Rule 12 (mediation test) are designed to distinguish between these hypotheses.

**If scope inflation (a) is confirmed:**
- `delta` reinterprets as "how much confidence inflated ambition beyond what fits in the allocated window" — a more specific, more actionable claim than the standard planning-fallacy frame
- H1 reinterprets as: confidence predicts scope inflation rate → time overrun is downstream effect (survives VT-19 better because mechanism operates at planning time)
- Calibration nudge pivots from time-adjustment ("push 60 to 83 min") to scope-adjustment ("when you feel this sharp, consider smaller scope, not longer time")
- `task.description` field (Alembic 023) becomes **primary** measurement surface capturing stated scope; `scope_density = description_item_count / planned_minutes` becomes the key metric
- Archetype taxonomy gains scope-stable vs scope-inflating dimension

**If competing hypotheses (b)–(f) explain the inversion instead:**
- Standard planning-fallacy frame stands; delta remains a time estimation error signal
- Calibration nudge continues as time-adjustment
- Brain dump remains a Phase 5 corpus accumulator without elevated measurement status
- Readiness signal still useful but as a confounded predictor, not a causal mechanism

**Pre-registered falsification test (Rule 12 below):**
- Test whether readiness × delta correlation is mediated by implicit scope expansion
- When brain dump data is available: compute `scope_density` per task, test mediation model `readiness → scope_density → delta`
- When brain dump data is not available: infer scope expansion from execution pattern complexity (pause count, within-session duration variance)
- If readiness predicts delta but scope_density accounts for the relationship when controlled for, delta is a scope problem not a time problem
- If scope_density does NOT mediate the relationship, the standard time-estimation frame stands and VT-22 is falsified

**Status:** VT-22 documented April 17, 2026. Pre-registered before trusted-user data arrives. Falsification test committed as Rule 12. Phase 6+ investigation; no code changes to calibration system until multi-user data confirms the mediation.

### VT-23: External-Source Attendance Self-Report
*Added: April 21, 2026. Pre-registered before any `external_event_outcome` data lands. Implemented in the Google Calendar integration same day (schema) and April 22 (/today UI).*

**Threat:** The "Did you attend?" control on past Google Calendar events (Path B 2026-04-21) invites users to self-report attendance on imported events. Three validity threats compound:
- **Selection bias:** users only mark events they remember
- **Recency bias:** marks cluster near fresh events, leaving a sparse tail
- **Social desirability:** "attended" is overclaimed for events the user feels they should have attended

**Mitigation:**
- `external_event_outcome` is stored in its own table, not in `task` — the H1 test set never sees imported data (enforced by the External Data Exclusion Rule above)
- Event title + start/end snapshotted at mark time so the self-report survives later GCal edits by the user
- The signal participates in retention + product research only, not H1

**Kill criterion:** at n≥20 calendar-connected users, if <15% of past GCal events get marked within 7 days of elapsing, the signal is too sparse for retention or research use. Revisit after the 2026-05-21 retention checkpoint.

**Status:** VT-23 pre-registered April 21, 2026. Implemented April 21 (DB schema, migration 027) and April 22 (/today UI + `POST /v1/calendar/attendance`). See `docs/strategic_decisions_april_21.md §6.1` and `docs/integrations_architecture.md §Research-integrity rules`.

### VT-24: *[Reserved — no validity threat assigned at this number. Keep sequence contiguous; next new VT uses 25.]*

### VT-25: Archetype-Reveal Narrative Internalization — DRAFTED, INACTIVE
*Drafted: April 22, 2026. Activates when the archetype reveal UI ships in v1.1. Until then, this threat does not apply — Rule 13 ships silent shrinkage only (no visible archetype label for the user).*

**Threat:** Showing a user their archetype label (e.g., "your profile: Procrastinator") may cause label-internalization — the user's subsequent `planned_duration_minutes` and `pre_task_readiness` inputs could entangle with the label rather than reflect underlying cognitive state. This is the same class of instrument-intervention threat as VT-21 (narrative internalization from calibration_nudge and micro_mirror) but with a stronger manipulation — an explicit categorical identity label vs. a continuous magnitude nudge.

**Why Rule 13 does NOT activate VT-25.** Rule 13 ships the shrinkage blend silently — every user consumes `bias_factor_final` transparently via the calibration_nudge magnitude but is never told "you are a Procrastinator." The archetype is a computational handle, not a surfaced identity. No label-internalization pathway exists until a reveal UI ships.

**Distinguishing analyses — frozen at reveal-feature launch (not at this drafting):**
- **25a. Pre-vs-post-reveal within-user planning shift.** For users who see their archetype at session 5–7 (per `docs/building_phases.md §Phase 5 progressive revelation`), compute the shift in mean `planned_duration_minutes` over the 10 sessions preceding vs 10 sessions following the reveal moment, stratified by the archetype's prior_bias_factor direction. **Label-internalization detected:** users assigned high-prior archetypes (procrastinator, diffuse_average, lark_low_discipline) inflate plans by ≥15% post-reveal relative to pre-reveal, controlling for category and time_of_day.
- **25b. Cross-user bias_factor trajectory — reveal-shown vs reveal-suppressed.** Using a within-subject A/B via the Rule 11 no-nudge-day framework adapted for archetype reveals: if some users see the reveal and others don't (by experimental suppression), compare the bias_factor convergence trajectory over sessions 5–15, paired by archetype. **Self-fulfilling prophecy detected:** shown users' personal bias_factor moves toward their archetype prior faster than suppressed users', indicating the reveal is *inducing* the prior rather than the prior predicting natural behavior.

**Mitigation if detected:**
- Demote reveal copy from identity-framing ("you are a Procrastinator") to pattern-framing ("your first-10-sessions data resembles the Procrastinator prior — subject to change as you accumulate more data")
- Add explicit medium-confidence framing at every reveal surface (per `docs/building_phases.md:167` "Phase 5 progressive revelation")
- Consider suppressing reveal entirely for users whose 25a analysis shows strong label-internalization and running silent-shrinkage-only for those users

**Status:** Drafted April 22, 2026 alongside Rule 13. INACTIVE until reveal UI ships (expected v1.1, post-Spring-School per `docs/strategic_decisions_april_22.md §5`). When activated, distinguishing analyses 25a + 25b become frozen pre-registration — no post-hoc threshold tuning permitted.

### VT-26: Category-Semantic Drift Between User Labels and Research Priors
*Added April 23, 2026 — Day-18 data sweep surfaced per-category RESEARCH_PRIOR drift exceeding archetype σ: for u=1 (n=4–7 per cell) observed sum-ratios diverged from published priors by `work` +0.67, `study` −0.93, `planning` +0.92 vs the frozen `RESEARCH_PRIORS` dict. The shrinkage formula assumes user-typed category labels (`"study"`) carry the same semantic as the published-study definition they were keyed to (Newby-Clark 2000 for "study"). If user labels drift from research semantics, the prior being blended in is the wrong prior for that user — and shrinkage actively pulls small-n predictions away from truth.*

**Threat:** Rule 13's canonical blend uses `archetype_prior_for_cell = RESEARCH_PRIORS[category].bias_factor × archetype_scaling`. The lookup is by category string, which is user-free-form (or mapped via `category_mapping` keyword seed). If operator's `"study"` = focused revision of familiar material (short, finishes early) while Newby-Clark's "study" = novel-topic mastery (long, overruns), the prior is systematically wrong for this user. At small n, shrinkage dominates (`pw = min(1, n/30)`), so wrong-prior predictions propagate into calibration_nudge, new-task-modal suggestions, and the /insights blend panel. Cold-start UX quality for off-prior users is degraded for ~30 cell-sessions before personal data dominates.

**Distinguishing analyses — frozen at April 23, 2026 drafting:**
- **26a. Cross-user per-category MAE at small n.** For users with ≥50 total executed sessions AND ≥10 per-category cells, compute prediction MAE (|predicted bias_factor_final − observed sum-ratio|) stratified by personal_weight bucket: (pw < 0.2, 0.2 ≤ pw < 0.5, 0.5 ≤ pw < 0.8, pw ≥ 0.8). **Drift confirmed:** low-pw MAE per category is systematically higher than high-pw MAE in specific categories (same direction across users) indicating a category-label prior mismatch rather than random noise.
- **26b. Within-user per-category stationarity.** For users with ≥30 executed sessions in a category, split in half chronologically. If observed sum-ratio is stable across halves (within ±0.10) but differs from `RESEARCH_PRIORS[category]` by ≥0.30, the user's stable pattern for that category label differs from the research prior — consistent with label-semantic drift (not within-user behavioral change). Report per user per category.

**Mitigation if detected:**
- Document label-semantic drift per user as a known limitation of the cold-start blend
- Consider a UI refinement: when a user creates their first task in a category, surface the research-prior source ("Lyra's prior for 'study' is based on Newby-Clark 2000's definition of novel-topic mastery — does that match what you mean by 'study'?") with a one-tap recategorize affordance
- Phase 6+: migrate from string-match `category` → semantic-cluster category (LLM-inferred + user-confirmed)
- Do NOT retroactively adjust `RESEARCH_PRIORS` mid-experiment window — that's a Rule 13 violation

**Status:** Drafted April 23, 2026 after Day-18 operator-data pass (u=1, n=43). n too small for conclusions; distinguishing analyses require cross-user coverage that activates once 3+ trusted users pass 50 executed sessions each (expected ~2026-05-15 at current activity rate).

### VT-27: Pause-Prediction Confidence-Function Calibration
*Added April 23, 2026 — Day-18 sweep: operator's 5 pause-prediction firings show a consistent shape (confidence bucket 50–59% → 0% observed hit rate, bucket 60–69% → 75% observed hit rate at n=5 total firings). n is an order of magnitude too small for conclusions, but the shape is directionally consistent with correct calibration. This VT pre-registers the threshold analysis so that when n accumulates we can read the signal cleanly.*

**Threat:** The pause-predictor's `confidence` scalar is currently a function of `sample_size` + `mechanism`-specific variance (see `services/pause_predictor.py`). If the function is mis-calibrated — e.g. the 50–59% bucket actually hits 30% of the time, or the 70–79% bucket hits 95% — then VT-17's acceptance-rate measurement is reading a shifted distribution. Users who see "65% clock pattern" banners form internal expectations that are either over- or under-calibrated to reality, and the kill-criterion-based VT-17 decision (acceptance ≥ 0.40 ships / ≤ 0.20 kills) becomes entangled with the confidence-function error rather than the predictor's raw skill.

**Distinguishing analyses — frozen at April 23, 2026 drafting:**
- **27a. Per-bucket hit rate at n≥30 firings per bucket.** Once `pause_prediction_log` accumulates ≥30 firings in each 10-pp confidence bucket (50s, 60s, 70s, 80s) across all users, compute observed hit rate per bucket (hit defined per VT-17d: `user_response` ∈ {`pause_now`, `self_reported_yes`} OR a `pause_event` exists within the predicted_at ±10-min window regardless of response flag). **Calibration confirmed:** observed rate tracks bucket midpoint within ±10pp.
- **27b. Per-mechanism calibration stability.** Same analysis stratified by `mechanism` ∈ {`clock_anchor`, `session_rhythm`}. If one mechanism shows acceptable calibration and the other drifts, kill the miscalibrated mechanism rather than retraining globally.
- **27c. Sample_size-regression.** Fit observed hit rate ~ confidence + sample_size. If sample_size is a significant predictor after controlling for confidence (p < 0.05), the confidence function is under-weighting sample_size and the low-n firings are over-confident (or vice versa).

**Mitigation if detected:**
- Re-estimate the confidence function using the accumulated empirical hit-rate-per-bucket curve (isotonic regression)
- Amend Rule 12's VT-17 acceptance window only if the mechanism survives 27a; otherwise deactivate the predictor rather than tune around miscalibration
- Do NOT change the confidence function mid-experiment-window without pre-registering the amendment

**Status:** Drafted April 23, 2026 after Day-18 operator-data pass (n=5 firings, below threshold for 27a/b/c). Activates empirically once pause_prediction_log per-bucket n reaches 30 across the active cohort.

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
*Manifesto v1.6 — revised April 16, 2026 (Rule 11: no-nudge control days — VT-21 detection protocol; Rule 10 reserved)*
*Manifesto v1.7 — revised April 17, 2026 (VT-22: scope inflation hypothesis; Rules 10 + 12: readiness-direction analysis + scope inflation mediation test; brain dump field elevated to potential primary measurement surface)*
*Manifesto v1.8 — revised April 22, 2026 (VT-23 external-source attendance self-report absorbed from strategic_decisions_april_21.md §6.1; External Data Exclusion Rule absorbed as top-level section; System Architecture diagram updated — OpenClaw + Telegram clarified as operator-only, Postgres promoted to primary DB reflecting April 16 Supabase migration; structural-invariants gloss added to Companion principle §line 60; preamble added to pre-registered analysis rules)*
*Manifesto v1.9 — revised April 22, 2026 evening (VT-17d retroactive-confirmation stratified acceptance-rate pre-registered — parallel to VT-17 strict formula, no modification of VT-17. Triggered by 2 observed predictions that correctly anticipated operator food breaks taken outside the app; closes the in-app-capture gap with alembic 030 `pause_event.self_reported_retroactively`, new confirm/pending-confirmation endpoints, retroactive chip on /today, and exclusion of retroactive pauses from predictor training + VT-17 primary matching to prevent self-reinforcement.)*
*Manifesto v1.10 — revised April 22, 2026 late-evening (Rule 13: archetype-prior shrinkage is the canonical `bias_factor` computation. Pre-registered BEFORE the first shrinkage-blended value reaches any user-facing surface. Formula, archetype priors, RESEARCH_PRIORS dict, and skip-path Diffuse Average default are all frozen. Triggered by 2026-04-22 trusted-user feedback "doesn't REALLY get me" and the operator's decision to accelerate clustering from Phase 5 into trusted-user week 2. VT-25 "Archetype-Reveal Narrative Internalization" drafted — inactive until reveal UI ships in v1.1.)*
*Manifesto v1.11 — revised April 23, 2026 (H3 Internal Conflict Signatures drafted as PROVISIONAL — multi-faction behavioral-signature framework reading the same data H1 reads through a competing-systems lens. Five signatures S1–S5 each specify disconfirming prediction first, confirming prediction second. Zero active at drafting; earliest activation months out at current growth. Diagnostic-only — confirmed signatures surface as pattern names in /insights, never as nudges. VT-26 "Category-Semantic Drift" + VT-27 "Pause-Predictor Confidence Calibration" pre-registered in same day's sweep. LYR-105/107/110 correctness bugs fixed alongside.)*

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

Twelve pre-registered analysis rules follow, frozen before analysis. Rules 1–9 lock the test set and reporting format. Rules 10–12 address specific validity threats (readiness-direction per VT-22, no-nudge control days per VT-21, scope-inflation mediation per VT-22).

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

10. **Readiness-direction analysis for scope inflation (VT-22).** *(Added April 17, 2026.)* Report the within-user Spearman ρ between `pre_task_readiness` and `duration_delta_minutes` with sign preserved. If the correlation is **negative** (high readiness → more negative delta, i.e. larger overruns), the standard time-estimation-error interpretation of delta is challenged per VT-22 (scope inflation hypothesis). Report this ρ alongside the primary H1 ρ. Additionally report mean `planned_duration_minutes` stratified by readiness quintile — if high-readiness sessions have systematically shorter planned durations than low-readiness sessions for the same category, the readiness signal is modulating planning ambition, not execution quality. This analysis is interpretive context for H1, not a replacement for the kill criterion.

11. **No-nudge control days (VT-21 detection protocol).** *(Added April 16, 2026.)* Beginning at trusted-user week 2 (after minimum 7 days of nudge-active baseline), suppress all `micro_mirror`, `calibration_nudge`, and `/insights` surfaces on randomly selected days at a 1-in-7 target frequency. Within-user, compare distributions of `duration_delta_minutes`, `skip_rate`, and `initiation_delay_minutes` between nudge-active and no-nudge days. Report paired effect sizes with confidence intervals. **Necessity-of-nudge decision criterion:** at N ≥ 30 paired day-observations per user, if no-nudge days produce statistically equivalent or better calibration, re-evaluate the necessity of the nudge mechanism. **VT-21 detection criterion:** if nudge-active days show systematically different `planned_duration_minutes` distributions than no-nudge days, controlling for category and time_of_day, narrative internalization is confirmed per VT-21. **Stratification requirement:** all post-nudge-deployment H1 analysis is stratified by nudge-exposure status at the session level (surface-fired vs surface-suppressed), using the `reflection_view_log` shipped in LYR-098 Commit 2b as the authoritative exposure flag.

12. **Scope inflation mediation test (VT-22 falsification).** *(Added April 17, 2026.)* When `task.description` data is available (≥ 50 tasks with non-empty descriptions per user), compute `scope_density = description_item_count / planned_duration_minutes` for each task. Run a mediation analysis: `pre_task_readiness → scope_density → duration_delta_minutes`. **If scope_density mediates the relationship** (readiness → delta attenuation ≥ 40% when controlling for scope_density, Sobel test p < 0.05): delta is primarily a scope inflation signal, not a time estimation error signal. Calibration nudge architecture pivots from time-adjustment to scope-adjustment in Phase 6+. **If scope_density does NOT mediate** (attenuation < 20%): the standard time-estimation frame stands, VT-22 is falsified, and the description field remains a Phase 5 corpus accumulator without elevated measurement status. **Interim analysis (before brain dump data):** use `pause_count` and within-session duration variance as proxy scope-complexity indicators. Report the readiness → proxy_complexity → delta mediation path as an exploratory supplement. This interim analysis is NOT a basis for the pivot decision — only the brain-dump-based mediation is authoritative.

13. **Archetype-prior shrinkage is the canonical `bias_factor` computation.** *(Added April 22, 2026 — pre-registered BEFORE the first shrinkage-blended `bias_factor_final` value is consumed by any user-facing surface. Triggered by the 2026-04-22 "doesn't REALLY get me" trusted-user feedback and the operator's decision to accelerate clustering from Phase 5 into trusted-user week 2. See `docs/strategic_decisions_april_22.md §5`.)*

    **Formula — frozen at launch.** For any `(user_id, category, time_of_day)` lookup, the canonical `bias_factor_final` consumed by the scheduler + calibration_nudge + insights surfaces is:
    ```
    personal_weight          = min(1.0, n_sessions_in_cell / 30)
    prior_weight             = 1.0 − personal_weight
    archetype_scaling        = archetype.prior_bias_factor / 1.30
    archetype_prior_for_cell = RESEARCH_PRIORS[category].bias_factor × archetype_scaling
    bias_factor_final        = prior_weight × archetype_prior_for_cell
                             + personal_weight × personal_sum_ratio_for_cell
    ```
    where `personal_sum_ratio_for_cell = sum(executed_duration_minutes) / sum(planned_duration_minutes)` over the filtered session set defined below.

    **Operational definition of `n_sessions_in_cell`:** tasks matching the requesting user's `user_id` with category = requested category, `time_of_day` bucket = requested bucket, and ALL of:
    - `state = 'EXECUTED'`
    - `voided_at IS NULL`
    - `initiation_status != 'retroactive'`
    - `initiation_status != 'system_error'`
    - `executed_duration_minutes IS NOT NULL`
    - `planned_duration_minutes >= 5`

    Cell granularity is `(category, time_of_day)`. `time_of_day` follows the existing `_time_of_day(local_dt)` bucketizer (morning / afternoon / evening / night). The cascade from `(cat, tod)` → `(cat)` → global fallback in `_adaptive_calibration` continues to apply for the *personal* portion of the blend; the archetype prior always uses the requested category's research prior.

    **Archetype prior values frozen at Rule 13 launch** (seeded in alembic 015, citations in `docs/methodology.md §1`):
    - `disciplined_lark` — prior_bias_factor 0.95, σ 0.15
    - `disciplined_owl` — prior_bias_factor 1.05, σ 0.20
    - `diffuse_average` — prior_bias_factor 1.30, σ 0.30
    - `procrastinator` — prior_bias_factor 1.80, σ 0.40
    - `lark_low_discipline` — prior_bias_factor 1.50, σ 0.35

    **`RESEARCH_PRIORS` dict frozen at Rule 13 launch** (per-category literature priors, in `backend/app/services/bias_factor_service.py`):
    - `development` 1.50 — Buehler et al. 1994; Connolly & Dean 1997
    - `work` 1.45 — Buehler et al. 1994
    - `study` 1.40 / `academic` 1.40 — Newby-Clark et al. 2000
    - `exercise` 1.15 / `fitness` 1.15 — Roy et al. 2005
    - default 1.35 — Kahneman & Tversky 1979 (planning-fallacy mean)

    **Default archetype when user has no ArchetypeAssignment:** `diffuse_average` (population midpoint). A user who skipped the survey and was stamped with `ArchetypeAssignment(archetype_id='diffuse_average', completed=False)` receives the same blend as a user with no assignment at all; the `completed` flag separates the two populations for retention analysis, NOT for prior selection.

    **Scope of this pre-registration:**
    - The formula exactly as written above
    - The `n_sessions_in_cell` operational definition
    - The 5 archetype prior values
    - The `RESEARCH_PRIORS` dict values + default
    - The `archetype_scaling = archetype.prior_bias_factor / 1.30` composite rule
    - The `diffuse_average` fallback for users without an assignment

    **Freedoms preserved (not protocol violations):**
    - Correctness bug fixes (documented post-hoc in an amendment noting what changed, why it was a bug, what retroactive reanalysis applies)
    - Gate-4-authorized threshold tuning at n ≥ 200 users × 90 days per `methodology.md §Gate 4` — when Gate 4 fires, the `n/30` linearization is tunable per pre-authorized remediation, and an amendment to Rule 13 replaces the threshold with a dated note

    **Protocol violations (require new pre-registration before change):**
    - Changing the discipline_z composite weights (0.30 / 0.40 / 0.30)
    - Modifying any of the 5 archetype prior values mid-window
    - Modifying the `RESEARCH_PRIORS` dict values mid-window
    - Adding per-cell archetype priors (ArchetypePrior table) without a new Rule-13 amendment
    - Changing the filter criteria that define `n_sessions_in_cell`
    - Changing the `/ 1.30` normalization anchor in the composite scaling rule

    **Reporting requirement.** Any H1 or bias_factor-adjacent analysis run on data collected after 2026-04-22 must report the distribution of `personal_weight` values across the sessions used in the analysis. The "archetype-prior-dominant" subset (`personal_weight < 0.5`) is flagged for sensitivity analysis — if the headline result changes substantially when restricting to `personal_weight ≥ 0.5`, the blend is doing visible work and must be discussed explicitly in the writeup.

    **Implementation anchor.** The canonical implementation is `blend()` in `backend/app/services/bias_factor_service.py` (wired into `GET /v1/analytics/bias_factor/lookup` in Phase C of the 2026-04-22 ship). Any alternative computation path anywhere in the codebase MUST delegate to this function — no re-implementation in endpoints or frontends.

---

## H3 — Internal Conflict Signatures (PROVISIONAL)

*Drafted April 23, 2026. Status: **PROVISIONAL**. Each signature below is individually provisional and activates only when its n threshold is met AND its disconfirming prediction is specified in advance. Signatures may activate or deactivate independently. The H3 family as a whole does not carry a single kill criterion — individual signatures that falsify are deactivated and documented; remaining signatures continue.*

### Why this exists

H1 frames the user as a single agent estimating time badly. VT-22 adds a scope-inflation alternative: the planning self over-commits, the execution self under-delivers, the gap = planned−executed. H3 generalizes the VT-22 shape to a **multi-faction model**: human as internal coalition, observable failure as a balance-of-power outcome rather than an estimation error. Competing-systems framing is classical (Minsky's Society of Mind 1986; Internal Family Systems 1995; Fishbach & Woolley 2015 on goal conflict). H3's contribution is not the theory — it's specifying **behavioral signatures already recorded in Lyra's schema** that would let the competing-systems reading earn or lose evidence without new instruments.

### Relationship to H1 and VT-22

- **H1** remains the falsifiable scaffolding (Kill Criterion above, unchanged).
- **VT-22** is the scope-inflation alternative, with its own mediation test (analysis rule 12).
- **H3** reads the same data through a multi-faction lens. It does not replace H1. It does not depend on VT-22 crossing significance — the signatures can confirm or fail independently. If VT-22 crosses *and* ≥2 H3 signatures confirm at threshold, the competing-systems reading gains explanatory weight. If VT-22 crosses alone with H3 signatures null, scope-inflation is real but the multi-faction generalization was over-reach.

### Frictionless-inference constraint

Every H3 signature must be computable from **fields already in the schema on 2026-04-23**. No new questionnaires, no new capture surfaces. If a signature requires a new field to operationalize, it is ineligible until the field ships under a standard LYR-xxx.

### Signatures

Each signature specifies disconfirming prediction FIRST (what pattern falsifies the reading), then confirming prediction, activation threshold, product implication, deactivation path, and known confounds. A signature that never meets its activation threshold stays PROVISIONAL indefinitely — neither confirmed nor falsified, just unread.

---

### S1 — Creation-to-Start Latency as Avoidance Index

**Claim.** Per-category latency between `task.created_at` and the first `stopwatch_session.start_time_utc` indexes an avoidance faction. Categories where the avoidance coalition wins show systematically longer latency.

**Operational definition.** For each (user, category) pair with ≥ 5 executed sessions, compute median minutes from `created_at` to first `start_time_utc` for `live` initiations only (`initiation_status='live'`, excluding retroactive). Compute per-user Spearman ρ between `median_latency_per_category` and `skip_rate_per_category` (the skip rate is the parliament's expressed veto; the latency is the parliament's delay tax).

**Disconfirming prediction (specified first).** S1 is **falsified** if, at n ≥ 5 categories per user with ≥ 5 sessions each:
- Within-user Spearman ρ(median_latency, skip_rate) is between −0.20 and +0.20, AND
- Bootstrap 95% CI on that ρ includes zero, AND
- The pattern is non-replicating across ≥ 3 users.

Falsification means latency is scheduling preference, not avoidance — some users schedule far in advance for reasons unrelated to internal conflict.

**Confirming prediction.** Within-user Spearman ρ(median_latency, skip_rate) ≥ +0.40 at n ≥ 5 categories, replicating across ≥ 3 users at trusted-user-alpha cohort.

**Activation threshold.** ≥ 3 users with ≥ 5 categories each populated ≥ 5 sessions. Estimated earliest date: 2026-06-15 at current trusted-user growth.

**Product implication if confirmed.** `/insights` surfaces a per-category "avoidance latency" chip: *"Your 'study' tasks wait 3.2× longer between creation and start than your average. The pattern predicts a 56% skip rate in this category."* This is **diagnostic**, not prescriptive — the product names the pattern and leaves the user to decide what to do.

**Deactivation if falsified.** Signature removed from product surface. Finding documented in `docs/operator_findings_log.md` with the bootstrap CI and replication attempt. No change to H1 or VT-22.

**Known confounds.** (a) Cascade failure (morning-skip → all-day-shift) inflates latency for same-day-created tasks that get reshuffled. Stratify by same-day-created vs advance-scheduled. (b) Retroactive initiation is excluded by filter. (c) New-user cold-start period (first 7 days) has different latency distribution than steady-state — exclude first 7 days per user.

---

### S2 — Same-Session Switching with Self-Initiated Pause Reason as Escape Signature

**Claim.** Pause events where `pause_initiator='user'` and `pause_reason` ∈ {`distraction`, `mental_fatigue`, `internal_interruption`}, followed within the same day by the user starting a *different* task, signal an **escape-faction win** — distinct from legitimate external interruption.

**Operational definition.** For each user, classify pause_events into two groups:
- **ESCAPE candidates**: `pause_initiator='user'`, `pause_reason` ∈ {`distraction`, `mental_fatigue`, `internal_interruption`}, followed within 60 minutes by the user starting a different task.
- **INTERRUPTION**: all other pauses.

Compare the ratio ESCAPE / total_pauses across categories. Categories with high escape ratio are categories where the escape faction has power.

**Disconfirming prediction (specified first).** S2 is **falsified** if, at n ≥ 30 pause_events per user:
- The pause_reason distribution conditional on switching is statistically indistinguishable from the distribution conditional on not switching (chi-square p > 0.20), AND
- The ESCAPE ratio is approximately uniform across categories (within-user σ(escape_ratio_per_category) < 0.10), AND
- Pattern does not replicate across ≥ 3 users.

Falsification means switching after a pause is contextually driven (external pressure, schedule demand) and does not signal a distinct escape coalition.

**Confirming prediction.** chi-square p < 0.05 for the conditional distribution difference, AND within-user σ(escape_ratio_per_category) ≥ 0.20 (strong per-category variance), AND replication across ≥ 3 users.

**Activation threshold.** ≥ 3 users with ≥ 30 total pause_events each. Operator currently at 59 pause_events; u=2 at 2, u=5 at 2, u=6 at 1. Estimated earliest date: late 2026-Q2 at current growth.

**Product implication if confirmed.** `/insights` surfaces per-category escape-ratio with the distinction called out: *"In 'study' sessions, 40% of your pauses are followed by switching to a different task — vs 8% in 'development'. The pattern is specific to this category."* Confirmation does NOT imply the product pushes back on switching. It NAMES the pattern.

**Deactivation if falsified.** Signature removed. No change to the pause-prediction VT-17 pipeline (orthogonal concerns).

**Known confounds.** (a) Fatigue is monotonic across the day — session_index_in_day correlates with pause_reason, so stratify by first-half / second-half of day. (b) Category scheduling correlates with time-of-day (study in morning, dev in afternoon), so control for time_of_day. (c) The `mental_fatigue` reason is semantically close to legitimate exhaustion — its inclusion in ESCAPE is contestable. If S2 activates, report results with and without `mental_fatigue` and flag the sensitivity.

---

### S3 — Post-Overrun Scope Trajectory as Contrition / Stubbornness / Avoidance

**Claim.** After an overrun session (`bias_factor > 1.5` on executed_duration/planned_duration), the user's next session in the same category shows one of three trajectories that reveal which faction learned: **contrition** (reduced planned_duration, ≥ 20% smaller), **stubbornness** (same planned_duration, within ±10%), or **avoidance** (category skipped entirely for ≥ 72h).

**Operational definition.** For each user, for each overrun session where `executed_duration/planned_duration > 1.5` and the session count in that category is ≥ 5, look ahead to the NEXT same-category session (if any). Classify the next session:
- **CONTRITION**: `next.planned_duration_minutes ≤ 0.80 × overrun.planned_duration_minutes`
- **STUBBORNNESS**: `0.90 × overrun.planned_duration_minutes ≤ next.planned_duration_minutes ≤ 1.10 × overrun.planned_duration_minutes`
- **INFLATION**: `next.planned_duration_minutes > 1.10 × overrun.planned_duration_minutes`
- **AVOIDANCE**: no same-category session within 72 hours (cross-reference skip/void/no-creation together)

**Disconfirming prediction (specified first).** S3 is **falsified** if, at n ≥ 20 overrun-with-followup pairs per user:
- The trajectory distribution is indistinguishable from uniform-over-categories (chi-square p > 0.20 vs the user's baseline category distribution), AND
- Within-user, categories do not show systematic preference for one trajectory over others (each category's most-common trajectory is tied within ±10%), AND
- Pattern does not replicate across ≥ 3 users.

Falsification means post-overrun behavior is contextual noise, not a coalition signal.

**Confirming prediction.** Systematic within-user per-category trajectory preference (chi-square p < 0.05) AND replication across ≥ 3 users showing the SAME CATEGORY taking the SAME TRAJECTORY (e.g. "study → avoidance" across multiple users).

**Activation threshold.** ≥ 3 users with ≥ 20 overrun-with-followup pairs each. Operator has ~10 overruns at n=43 — close to half-threshold. Cross-user requires ~6-8 weeks at current growth.

**Product implication if confirmed.** The `/insights` "Archetype fit" card extends with a trajectory label per category: *"Your pattern after study overruns: 60% avoidance, 30% stubbornness, 10% contrition."* The avoidance percentage is the operationalized "identity resistance index" the essay described.

**Deactivation if falsified.** Signature removed. S3 is the most complex of the signatures and most likely to fail for lack of clean per-category sample sizes — a null result here does not diminish S1/S2/S4/S5.

**Known confounds.** (a) Cascade failure across days can force same-category avoidance for reasons unrelated to the overrun (a day shifts, the study block falls off). Stratify by whether the next-day calendar was already populated. (b) VT-21 (narrative internalization): if a calibration_nudge fired post-overrun and the user internalized it, the contrition classification is the *nudge* speaking, not the user. Use `reflection_view_log` to stratify by whether a nudge was viewed between the two sessions. (c) Small per-category n inflates variance.

---

### S4 — Across-Category Variance as Coalition-Specific Competence

**Claim.** Users with genuine internal coalitions show **high variance in bias_factor across categories** — the coalition that runs 'development' is not the one that runs 'study'. Users whose behavior is a single-agent calibration error show **low variance across categories** — error is unified.

**Operational definition.** Per user at ≥ 3 categories with ≥ 5 sessions each, compute:
- `across_σ` = standard deviation of `bias_factor_final` across categories (one value per category, SD across the set)
- `within_σ` = mean of per-category standard deviations of `bias_factor_final` computed over the sessions in that category

If coalition-specific competence exists, `across_σ > within_σ` systematically. If single-agent noise, `across_σ ≈ within_σ`.

**Disconfirming prediction (specified first).** S4 is **falsified** if, at n ≥ 5 users with ≥ 3 categories ≥ 5 sessions each:
- Per-user ratio `across_σ / within_σ` has median ≤ 1.2 across users, AND
- The ratio has 95% CI including 1.0, AND
- F-test of `across_σ²` vs `within_σ²` per user fails to reject uniform-variance null (p > 0.20) in ≥ 60% of users.

Falsification means calibration error is global (one user, one noise level across categories), not coalition-specific.

**Confirming prediction.** Median ratio ≥ 1.8, 95% CI excludes 1.0, F-test rejects uniform-variance null in ≥ 60% of users.

**Activation threshold.** ≥ 5 users with ≥ 3 categories ≥ 5 sessions each. Operator is the only user currently eligible (n=43 with 6 categories ≥ 2 sessions). Realistic date: late 2026-Q2.

**Product implication if confirmed.** `/insights` introduces a per-user "coalition coherence" number: a single scalar (ratio of across-category SD to within-category SD) that distinguishes "single-agent" users from "multi-coalition" users. Single-agent users get simpler nudges (one calibration model). Multi-coalition users get category-differentiated surfaces (each category treated as a different internal actor with its own track record).

**Deactivation if falsified.** Signature removed. The calibration_nudge continues treating each category independently as it already does; the "coalition coherence" scalar never surfaces.

**Known confounds.** (a) Categories differ in inherent variance for reasons unrelated to internal coalitions (e.g. `study` is inherently more variable than `exercise`). Use the archetype-scaled research prior's σ as the expected-variance baseline per category — report residual variance above that baseline. (b) Task-type heterogeneity within a category (not all 'development' tasks are the same) inflates within-σ and masks the signal. Sensitivity analysis with title-keyword-based sub-categories.

---

### S5 — Post-Overrun Readiness Shift as Self-Honest vs. Self-Protecting

**Claim.** After a session with significant negative `duration_delta_minutes` (overrun) and low `post_task_reflection` (sub-par performance self-rating), the user's next `pre_task_readiness` in the same category shifts downward (self-honest update) OR stays flat / rises (self-protection by a faction that maintains identity).

**Operational definition.** For each user, for each session where `duration_delta_minutes < -15 AND post_task_reflection ≤ 2 AND pre_task_readiness ≥ 4` (a "confident-but-failed" session), compute:
- `readiness_shift = next_same_category_session.pre_task_readiness - this_session.pre_task_readiness`
- Classify:
  - **SELF-HONEST**: `readiness_shift ≤ -1` (readiness drops by ≥ 1 point on 5-point scale)
  - **FLAT**: `-1 < readiness_shift < +1`
  - **SELF-PROTECTING**: `readiness_shift ≥ +1` OR the user rates ≥ 4 readiness on next session after a low-reflection failure

**Disconfirming prediction (specified first).** S5 is **falsified** if, at n ≥ 15 confident-but-failed-with-followup pairs per user:
- Wilcoxon signed-rank on `readiness_shift` has p > 0.20 AND |median shift| < 0.5 points, AND
- The SELF-HONEST / FLAT / SELF-PROTECTING distribution is indistinguishable from the user's baseline readiness-transition distribution (chi-square p > 0.20), AND
- Pattern does not replicate across ≥ 3 users.

Falsification means readiness rating is not responsive to recent performance — either the instrument is ceiling-saturated (VT-12), or readiness and performance are genuinely independent for this user, or the timescale of update is longer than session-to-session.

**Confirming prediction.** Consistent within-user SELF-HONEST dominance (median shift ≤ -0.5, p < 0.05) OR consistent within-user SELF-PROTECTING dominance (≥ 40% of post-failed-session ratings stay ≥ 4, p < 0.05 vs baseline).

**Activation threshold.** ≥ 3 users with ≥ 15 confident-but-failed-with-followup pairs. Operator is eligible at n ≈ 8 currently — roughly half-threshold. Cross-user replication: 2026-Q3.

**Product implication if confirmed.** Users classified SELF-HONEST get weight-1.0 on their readiness scores in blended predictions. Users classified SELF-PROTECTING get downweighted readiness (weight 0.5) in the blend, because their ratings don't track performance. This is a **per-user instrument calibration**, not a user-facing label.

**Deactivation if falsified.** Readiness continues being used at weight-1.0 uniformly. Signature removed.

**Known confounds.** (a) VT-1 Hawthorne: just being measured may cause readiness to adjust for reasons unrelated to coalition dynamics. Report S5 alongside VT-1 results. (b) VT-12 scale saturation: if a user anchors at readiness=5 regardless, S5 classifies them SELF-PROTECTING when they may just have a compressed range. Require within-user readiness SD ≥ 0.8 as a precondition for S5 classification. (c) VT-21 narrative internalization: nudge-exposed sessions have readiness entangled with the nudge. Stratify by `reflection_view_log` exposure.

---

### H3 amendment protocol

- New signatures may be added to H3 at any time. Each new signature specifies its disconfirming prediction BEFORE its confirming prediction AND before any data is read against it. The git commit introducing the signature is the pre-registration timestamp.
- Individual signatures may be retired after falsification, with a dated entry in `docs/operator_findings_log.md` capturing the falsifying analysis and its bootstrap CIs.
- **Forbidden:** reading the data, THEN formulating the signature. Every signature must be registered before its activation threshold is met on the data.
- **Forbidden:** loosening a signature's falsification threshold post-hoc. Tightening is permitted with documented rationale.

### Reporting requirement

Any H3-adjacent analysis that confirms or falsifies a signature must publish:
- The filter set applied (matching or deviating from Rule 13's `n_sessions_in_cell` definition — any deviation is called out)
- The bootstrap CI on the primary statistic
- The cross-user replication attempt and its outcome
- Confounds addressed and confounds acknowledged-but-unaddressed

### Relationship to product

H3 is **diagnostic**, not prescriptive. Confirmed signatures surface as **pattern names** in `/insights` — *"your post-overrun trajectory in study is avoidance"* — and never as nudges or interventions. The theoretical framing (parliament / coalitions / factions) stays in `MANIFESTO.md` and `docs/methodology.md`; the user-facing surface uses concrete behavioral language ("pattern", "tendency", "trajectory"). No user ever sees the word "faction" or "coalition" in the product.

### Status

PROVISIONAL. Zero signatures active at drafting time. Earliest activation (S1 latency-avoidance) requires ≥ 3 users × ≥ 5 categories × ≥ 5 sessions — months out at current growth. The signatures are pre-registered now to preserve falsifiability when the data lands; they are **not** acted upon today.
