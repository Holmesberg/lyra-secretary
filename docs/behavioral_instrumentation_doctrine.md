# Behavioral Instrumentation Doctrine

**Status:** Product-research doctrine note.
**Created:** 2026-05-15.
**Purpose:** Record the architectural framing that LyraOS is primarily a
rule-governed behavioral measurement instrument, not an AI productivity app.

This document does not authorize new predictors, prompts, schema, UI, or
automatic scheduling. It clarifies the interpretation philosophy behind the
current architecture.

For the academic-provider version of this doctrine, including Baseet/LMS
adapter boundaries, passive activity traces, and the rule that planning
calibration requires accepted intention, see
`docs/academic_execution_substrate.md`.

---

## 1. Core Claim

LyraOS is a behavioral measurement instrument with a productivity interface.

The core intelligence substrate is not a black-box AI model. It is a
constrained feedback system built from:

- explicit behavioral traces,
- deterministic product state transitions,
- rule-based interpretation,
- probabilistic priors,
- longitudinal evidence accumulation,
- clean-data profiles,
- exposure modeling,
- uncertainty propagation,
- and falsifiable read-time metrics.

The AI components are supporting systems. They may enrich, orchestrate,
summarize, or assist operator work, but they are not the source of truth for
user-facing behavioral claims.

The substrate is action-first, not emotion-first. Lyra may use readiness,
reflection, sentiment, or self-report as evidence, but the core object is what
humans do under constraints:

```text
intention -> execution -> drift -> interruption -> consequence -> recalibration
```

Emotional interpretation must not substitute for action evidence.

## 2. Not An AI Wrapper

LyraOS should not be framed as:

- transformer magic,
- generic AI productivity,
- hidden user embeddings,
- fake personalization,
- black-box confidence theater,
- or an AI that understands the user's identity.

The serious claim is different:

```text
The system accumulates behavioral evidence, detects structure
probabilistically, and progressively earns stronger inference rights.
```

The alignment claim is also different:

```text
better alignment -> increased honesty
```

Lyra does not align by making the user maximally obedient to a plan. It aligns
by preserving reality contact between what was intended, what constraints were
present, what action occurred, and what consequence followed.

That makes the architecture closer to:

- HCI systems,
- cognitive instrumentation,
- adaptive behavioral systems,
- classical systems engineering,
- adaptive control,
- Bayesian-ish evidence accumulation,
- and longitudinal behavioral modeling.

This is a strength. The architecture is coherent because the model is forced
to be causal, structural, operational, and epistemically bounded instead of
outsourcing ambiguity to "the model will figure it out."

## 2.1 Trajectory Integrity

The deeper invariant is not productivity optimization. LyraOS treats repeated
human-system interactions as trajectory-shaping. A plan suggestion, pressure
map, insight, reminder, or future adaptive action can change what the user
does next and how they interpret themselves.

Therefore the instrument must optimize for reality contact before it optimizes
for retention, status, throughput, or any other proxy. The system should make
the relationship between intention, constraint, action, and consequence more
legible without turning that legibility into hidden pressure.

Operational consequences:

- measurement must preserve provenance and exposure context;
- stronger claims must be earned from clean repeated evidence;
- guidance must remain challengeable and reversible;
- sequencing matters because the order of revelation changes interpretation;
- proxy wins that reduce user agency are product failures even when short-term
  metrics improve.

## 3. AI Role Boundary

AI may be used as:

- asynchronous enrichment,
- suggestion generation,
- operator-only synthesis,
- implementation assistance,
- interface glue,
- or non-canonical semantic assistance.

AI must not become:

- a hidden authority over product state,
- a source of observed truth,
- an unregistered inference surface,
- a substitute for clean-data profiles,
- a replacement for exposure modeling,
- or a way to smuggle new user-burden variables into the product.

User-facing claims should remain inspectable, bounded, and reproducible from
raw traces and declared evaluation rules.

## 4. Attention As Scientific Capital

User attention is scarce scientific capital.

Every additional prompt:

- changes behavior,
- changes cognition,
- interrupts task flow,
- contaminates the measurement environment,
- increases retention risk,
- and can make user behavior more performative.

Therefore, ambiguity must not automatically be solved by asking the user more
questions.

The preferred direction is:

```text
sparse explicit input + dense passive structure
```

Influence cannot be eliminated. A mirror, pressure map, warning, reminder, or
duration suggestion can change later behavior. The invariant is:

```text
Influence is inevitable.
Unconscious influence is unacceptable.
```

Every behavior-shaping surface must therefore be visible, inspectable,
challengeable, and exposure-aware. Hidden optimization for retention,
engagement, or compliance is misaligned even if it improves short-term product
metrics.

The minimum useful loop is:

```text
sign in
  -> consent
  -> dump or create tasks
  -> start and stop timers
```

Signals such as pause reason, readiness, reflection, and completion percentage
are acceptable only because they live at natural task boundaries or already
exist in the current flow. They must not expand into a growing questionnaire
surface.

## 5. Weak Signals Over More Questions

The same behavioral loop observed through multiple weak signals is often more
valuable than endlessly increasing explicit user input.

LyraOS should infer cautiously through:

- timing,
- initiation delay,
- duration drift,
- pause topology,
- avoidance,
- recovery behavior,
- completion percentage,
- contextual repetition,
- external-deadline relationship,
- missingness,
- and longitudinal trace shape.

It should not depend on the user being a perfectly reliable introspective
narrator of why a task succeeded or failed.

### 5.1 Context Switching As Footprint, Not Cause

Explicit task switches, parent-child interruptions, parked work, and re-entry
latency are valuable execution-topology signals. They can show that a plan
became fragmented.

They do not, by themselves, explain why fragmentation happened.

The first product use is re-entry recovery:

```text
open threads -> recovery options
```

not insight or scoring:

```text
switches -> fragmentation score
```

User-facing copy should say "parked work," "open threads," "re-entry load,"
or "resume load." Do not expose `context_switching_footprint` in product UI.
Do not create a `fragmentation_score` or equivalent scalar judgment.

Hard tasks, unclear scope, genuine emergencies, excessive commitments,
deadline pressure, emotional avoidance, provider noise, and forgotten timers
can all produce similar switch signatures. Lyra may therefore treat
context-switching footprint as low-authority recovery intelligence, but it
must not turn it into a causal or psychological claim without controls,
falsification, and exposure accounting.

Metacognitive discrepancy can modify this signal: switched work that also
resembles prior over-plan work is stronger evidence of recovery friction than
switch topology alone. Even then, the safe claim is correlation until stronger
evidence accumulates.

Any future implementation must derive resolution outcomes before interpreting
switching: resumed, completed later, rescheduled, dropped, marked irrelevant,
stale/open at day end, or auto-closed. Without resolution outcome, the system
only knows that switching happened, not whether it mattered.

## 6. Missingness Is Signal

Missingness is part of the behavioral topology.

Examples:

- tasks not started,
- ignored prompts,
- absent readiness,
- abandoned planning,
- delayed initiation,
- skipped reflections,
- unconfirmed repair candidates,
- and overdue recovery actions.

These should not be smoothed into neutral defaults. They should remain
observable absences with provenance and uncertainty.

Important rule:

```text
missing data is not automatically unusable data,
but it is also not observed truth.
```

## 7. No Single Truth Source

No single signal should be trusted too much.

The system should triangulate across:

- explicit user input,
- observed task state transitions,
- stopwatch traces,
- pause/resume topology,
- timestamps,
- derived metrics,
- exposure states,
- recovery flows,
- missingness,
- and contextual repetition.

Self-report is an input, not psychological truth. Timer traces are high-value
instrumentation, not perfect cognition. Derived metrics are read-time
interpretations, not raw facts.

Provider and passive-activity rows obey the same rule. A resource open event,
Jira status, calendar block, or LMS import can be useful context without being
execution truth. Dirty upstream data is expected. Lyra should handle it through
evidence tiers, provenance, contradiction handling, cooldown repair prompts,
and graceful demotion from calibration, not by assuming clean provider data or
forcing constant manual cleanup.

## 8. Archetypes As Cold-Start Priors

The archetype system is coherent only when framed as a cold-start prior
mechanism, not personality typing.

Bad framing:

```text
You are a procrastinator archetype.
```

Better framing:

```text
Users with similar early behavioral/topological patterns historically showed
similar execution-drift structures. Lyra treats this as an initial hypothesis
until your own traces dominate.
```

The survey and archetype assignment exist to answer a real adaptive-systems
problem:

```text
How can the system bootstrap useful inference before enough local longitudinal
evidence exists?
```

This is a cold-start problem, not an identity problem.

## 9. Prior Decay And Evidence Override

Archetype authority must decay as personal evidence accumulates.

The intended flow is:

```text
cold-start prior
  -> personal traces accumulate
  -> prior is reinforced, weakened, or locally adjusted
  -> user sees calibration drift
  -> no stable identity claim is made
```

The strongest version is:

```text
initial similarity priors
  -> progressively overridden by personal longitudinal traces
```

Personal evidence must eventually dominate cluster identity.

The archetype system may be more useful internally than externally:

- prior shaping,
- confidence initialization,
- inference bootstrapping,
- cold-start scheduling hypotheses,
- and comparison against emerging personal traces.

It should not become a user-facing identity experience unless a successor
contract proves that the benefit outweighs identity-internalization risk.

## 10. Earned Adaptation Authority

Lyra is not permanently constrained to weak suggestions. It is constrained to
earned authority.

Current low-authority behavior exists because the instrument has not yet earned
stronger claims across enough clean traces, users, providers, and exposure
states. If future cohorts show stable predictive lift, trustworthy
recalibration effects, and acceptable user response, stronger automation can
become valid.

Authority ladder:

```text
weak evidence
  -> weak claims
  -> editable estimates
  -> bounded recommendations
  -> validated adaptive suggestions
  -> future-gated automation
```

The danger is not strong adaptation by itself. The danger is strong adaptation
without grounded validity. Any future autonomous scheduling or prediction must
show its evidence class, contamination state, override path, and kill criteria.

### Control-System Vocabulary Guard

Lyra may borrow from cybernetics, adaptive control, and cognitive systems
engineering, but those terms must not become decorative metaphors. Any future
control-system claim should define the following before entering product or
research doctrine:

| Term | Lyra interpretation | Overclaim to avoid |
| --- | --- | --- |
| `state` | Observable task/execution condition such as planned, executing, skipped, paused, pressure window, or recent cascade context. | Treating latent motivation or identity as directly observed state. |
| `control input` | A reversible suggestion, recovery option, buffer, reminder, or experiment proposal. | Hidden steering or calendar mutation without consent. |
| `disturbance` | External or internal disruption such as provider changes, fatigue, interruption, late start, or deadline compression. | Explaining every miss as a user defect. |
| `objective` | A bounded local aim such as reducing next-block skip risk or preserving sleep. | Optimizing productivity, engagement, or compliance globally. |
| `feedback` | Measured response after a visible surface or chosen action. | Assuming behavior changed naturally after Lyra intervened. |
| `stability` | Lower volatility or reduced cascade propagation under explicit metrics. | Claiming the person is stable, disciplined, or fixed. |
| `over-control` | The system creates dependence, pressure, or compliance while improving visible metrics. | Calling all metric improvement alignment. |

Control language is useful only when it increases precision. If it hides
uncertainty, it should be replaced with simpler measurement language.

## 11. Product Copy Shape

Good copy:

```text
Your starting profile expected academic tasks to run about 40% over plan.
Your recent trace data is currently 12% under plan. Lyra is treating this as
calibration drift, not as a fixed identity.
```

Also good:

```text
Your traces are moving away from your starting profile on academic tasks. The
profile expected +40% over plan; your recent data is 12% under. Treat this as
the model recalibrating, not as a label about you.
```

Bad copy:

```text
You are no longer this archetype.
```

```text
You are a disciplined worker.
```

```text
Lyra knows your personality.
```

## 12. Research-Facing Architectural Strength

The professor-facing strength is the combination of:

| Trait | Why It Matters |
| --- | --- |
| rule/probability-based core | intellectual discipline |
| adaptive loop thinking | systems maturity |
| exposure modeling | causal humility |
| explicit uncertainty | credibility |
| recursive dogfooding | instrument-in-use evidence |
| product polish | adoption and data-continuity support |
| longitudinal thinking | research maturity |
| no fake AI claims | claims discipline |

The architecture is strongest when it resists fake intelligence and earns
interpretive authority from traces over time.

## 12. Final Principle

LyraOS should become more adaptive by becoming more observant, not more
intrusive.

It should learn from the user's normal planning and execution loop while
preserving:

- low burden,
- inspectability,
- falsifiability,
- uncertainty,
- exposure separation,
- and the user's freedom not to become a questionnaire subject.
