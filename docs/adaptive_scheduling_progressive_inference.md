# Adaptive Scheduling Progressive Inference

**Status:** Product-research concept note.
**Created:** 2026-05-13.
**Purpose:** Capture the emerging adaptive scheduling direction, its evidence
requirements, and its current feasibility without authorizing automatic
scheduling behavior.

This document does not authorize autonomous rescheduling, calendar mutation,
new intervention surfaces, or stronger user-facing claims. It defines the
shape of a future capability and the evidence thresholds it must respect.

## Core Realization

LyraOS should not present adaptive scheduling as "AI predicts your life."

The defensible product shape is:

```text
observed traces
  -> local metrics
  -> descriptive synthesis
  -> bounded experiment suggestions
  -> measured adaptation
  -> local adaptive confidence
```

The system earns stronger guidance only as it accumulates enough clean,
longitudinal evidence for a specific user.

This loop is rule-based and probabilistic before it is AI-powered. The
adaptive claim should come from explicit traces, declared metrics, clean-data
profiles, and exposure-safe comparisons. LLM or operator tooling may help with
enrichment and synthesis, but it is not the core intelligence substrate.

The strongest framing is:

> Lyra has seen enough about how this kind of task behaves in this context to
> suggest a small scheduling experiment.

Not:

> Lyra has generated your optimal schedule.

See also `docs/behavioral_instrumentation_doctrine.md` for the broader
instrumentation philosophy behind this stance.

## Progressive Epistemic Capability

The unlock system should be evidence-driven, not arbitrary gamification.

Each stage corresponds to increased signal density and increased legitimacy of
stronger claims:

| Stage | Evidence State | Capability |
| --- | --- | --- |
| 0 sessions | no execution evidence | raw task planning and history only |
| 1-2 eligible sessions | sparse traces | exact trace readback |
| 3-15 eligible sessions | early repeated traces | descriptive insights |
| 30+ eligible sessions | enough repeated structure for comparison | bounded synthesis |
| 50+ clean sessions plus stable signal | enough longitudinal evidence to test placement changes | experiment suggestions |
| repeated experiment outcomes | local effect evidence | adaptive scheduling suggestions |
| repeated validated improvement | stable user-specific effect | confidence-backed recommendations |

These numbers are defaults, not promises. Some users will need more evidence
when traces are sparse, noisy, contaminated, or unevenly distributed across
task categories and time windows.

The product copy should communicate evidence accumulation:

> Adaptive scheduling is still calibrating. Lyra needs more clean execution
> data before it can suggest task placement patterns reliably.

Avoid level language such as:

> Level 7 unlocked.

## Current Feasibility As Of 2026-05-13

Current operator data is enough for descriptive synthesis, but not enough for
validated adaptive scheduling.

Observed operator signals:

- `/v1/analytics/insights` reports `42` clean eligible sessions.
- Operator history contains `116` historical task events.
- Study tasks show a high not-started rate: `12/25` (`48%`).
- Study currently appears as the widest planning-error category, but category
  claims must avoid contaminated legacy buckets such as `work`.
- Night executed tasks ran about `50` minutes over plan on average in the
  current clean insight window.
- Estimation error increased by `27.0` minutes over the last 10 sessions.
- Start delay averaged about `11` minutes across eligible executed tasks.
- Readiness comparison exists, but is not yet enough to make readiness the main
  explanatory variable.

Feasible now:

- Descriptive synthesis:
  - "Planning drift currently clusters around academic or study work and
    late-day execution."
  - "Study tasks are more likely to fail before execution when placed later in
    the day."
- Low-authority experiment framing:
  - "Try moving one study block earlier and compare whether it starts more
    reliably."

Not feasible yet:

- "You should study in the morning."
- "Morning study is optimal for you."
- automatic rescheduling.
- hidden calendar mutation.
- validated claims that moving study earlier improves outcomes.

Important counter-signal:

Earlier placement may improve start reliability, but it does not automatically
solve duration accuracy. Some morning study/build sessions still produced large
duration drift. Therefore, current evidence supports a placement experiment,
not a scheduling rule.

## Evidence-Constrained Adaptive Scheduling

Adaptive scheduling should optimize first for execution reliability, not
maximal productivity.

Execution reliability means:

- more planned tasks actually start,
- initiation delay decreases,
- not-started rates decrease,
- completion reliability improves,
- duration drift becomes less chaotic.

This is more believable and more trust-building than claiming the system has
found an optimal life schedule.

Good adaptive scheduling copy:

> Study tasks scheduled after 7 PM currently show higher non-start rates and
> larger drift. Want to test one earlier study block tomorrow?

Better when measuring an actual experiment:

> Earlier study placement reduced initiation delay in the last two matched
> attempts. Lyra is still treating this as a hypothesis.

Bad copy:

> You should always study in the morning.

> Optimal schedule generated.

> Lyra knows your best work time.

## Intervention Boundary

Descriptive synthesis and intervention hypotheses are different truth classes.

Descriptive synthesis:

> Your execution drift currently clusters around late-day academic planning.

Intervention hypothesis:

> Try moving one study block earlier this week and compare execution drift.

Validated intervention:

> Across repeated matched attempts, earlier study placement has reduced
> not-started rate for this user.

Only the first is feasible today. The second may be feasible as operator-only
experimentation. The third requires repeated outcomes after suggestions are
shown and logged.

Intervention surfaces must:

- be registered output surfaces,
- declare `truth_class=intervention`,
- log exposure,
- record the proposed experiment,
- record whether the user accepted, ignored, or rejected it,
- compare downstream outcomes against the exact intervention target,
- fail closed when exposure state or outcome data is unknown.

## Operator-Only First

Adaptive scheduling should begin as operator-only.

Reasons:

- This surface combines trust, usefulness, creepiness, overclaiming, and
  behavioral transformation.
- The first thing to validate is not optimization. The first thing to validate
  is whether the suggestion feels behaviorally plausible and timely.
- Operator dogfooding can detect whether the system feels helpful,
  generic, invasive, arbitrary, or emotionally mistimed.

Operator-only acceptance question:

> Did this suggestion feel like it came from my actual traces?

Not:

> Did Lyra optimize the day?

## Unlock UX

The unlock should reinforce evidence-first behavior.

Good:

```text
Adaptive scheduling is still calibrating.

Lyra needs more longitudinal execution data before it can suggest task
placement patterns reliably.

Progress: 27 / 50 clean sessions
```

Better when the user has enough volume but no stable signal:

```text
Adaptive scheduling has enough sessions, but no stable placement effect yet.
Lyra will keep showing descriptive patterns until an experiment-worthy signal
appears.
```

Avoid:

- streaks,
- productivity XP,
- arbitrary levels,
- pressure copy,
- monetization-like lock language.

The user should feel:

> I am teaching the system how I work.

Not:

> I am grinding points.

## Cold-Start Priors And Archetype Decay

Adaptive systems have a cold-start problem: before enough local longitudinal
evidence exists, purely personal inference is sparse and often unhelpful.

The archetype system should therefore be framed as a cold-start prior
mechanism, not personality typing.

Bad framing:

```text
You are a procrastinator archetype.
```

Better framing:

```text
Users with similar early behavioral/topological patterns historically showed
similar execution-drift structures. Lyra treats this only as an initial
hypothesis until your own traces dominate.
```

The intended authority flow is:

```text
cold-start prior
  -> personal traces accumulate
  -> prior is reinforced, weakened, or locally adjusted
  -> user sees calibration drift
  -> no stable identity claim is made
```

This means archetype authority must decay as personal evidence accumulates.
Personal longitudinal traces eventually dominate cluster-derived priors.

Good user-facing copy:

```text
Your starting profile expected academic tasks to run about 40% over plan.
Your recent trace data is currently 12% under plan. Lyra is treating this as
calibration drift, not as a fixed identity.
```

Even better:

```text
Your traces are moving away from your starting profile on academic tasks. The
profile expected +40% over plan; your recent data is 12% under. Treat this as
the model recalibrating, not as a label about you.
```

Forbidden copy:

```text
Lyra knows your personality.
```

```text
You are no longer this type.
```

```text
You should schedule this way because your archetype says so.
```

Archetypes may be most valuable internally for:

- prior shaping,
- confidence initialization,
- cold-start scheduling hypotheses,
- and comparison against emerging personal traces.

They must not become stable user identity claims.

## Minimum Future Contract

Before shipping adaptive scheduling beyond operator-only mode, define:

- surface registry entries for synthesis and intervention surfaces,
- clean-data profiles for placement experiments,
- category provenance or category-contamination rules,
- matched-comparison logic for "earlier vs later" task placement,
- exposure targets for scheduling suggestions,
- render acknowledgement and acceptance/rejection logging,
- rollback and undo behavior for any suggested schedule change,
- copy rules for low-authority experiment language,
- current-data eligibility diagnostics,
- no-autonomous-mutation rule unless explicitly overridden by a future
  contract.

Minimum future gates:

- at least `50` clean sessions or stronger task-specific threshold,
- enough samples in the relevant category and time-window slice,
- stable directional effect, not only one high-strength outlier,
- an explicit effect threshold for the contract, such as `r >= 0.6` or a
  successor matched-outcome threshold, before a placement suggestion can be
  treated as adaptive rather than exploratory,
- no contaminated legacy category bucket,
- exposure-safe downstream outcome comparison,
- operator-only browser smoke before public exposure.

## Current Product Direction

The core product loop emerging is:

```text
observe
  -> synthesize
  -> suggest a small experiment
  -> measure the result
  -> adapt confidence
```

This is the actual behavioral value layer. The task manager, timer, and
dashboard are instrumentation surfaces. The adaptive reflective loop is the
product's deeper claim.

The architecture should protect that loop by making stronger guidance feel
earned, local, reversible, and evidence-bound.
