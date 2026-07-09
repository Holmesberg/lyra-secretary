# Measurement Integrity Before Agency Claims

**Status:** paper-direction note; not an implementation plan.
**Created:** 2026-06-12.
**Authority:** explanatory research framing only.
**May authorize code:** false.
**Runtime owner:** none.

This note captures a publishable direction that emerged from LyraOS bug hunts,
operator dogfood, cohort-readiness work, and exposure/clean-data doctrine.

It does not authorize new product claims, new user prompts, autonomous
adaptation, hidden interventions, or cohort expansion.

## Working Thesis

```text
A variable is not trustworthy because it is computable.
It becomes trustworthy only after surviving contamination checks,
slice-invariance tests, and intervention-aware interpretation.
```

The proposed paper direction is:

```text
Measurement Integrity Before Agency Claims
```

Internal implementation shorthand:

```text
Agency Claim Gate
```

The paper title should stay outward-facing. Inside LyraOS, the implementation
language should stay boring: claim gates, clean profiles, provenance, exposure,
and promotion rules.

The argument is methodological, not mystical:

Before any productivity, AI-assistant, personal-informatics, or learning system
claims something about focus, motivation, avoidance, discipline, recovery,
agency, or improvement, it must prove that its variables survive validity
checks.

## Core Claim

Many systems jump too quickly:

```text
events -> metrics -> agency claim
```

Examples:

- task completed -> the user was productive;
- delayed start -> the user procrastinated;
- repeated pauses -> the user was distracted;
- more app usage during finals -> retention improved;
- completion rate changed after a prompt -> the prompt helped.

LyraOS instead treats that jump as invalid until the intermediate construct is
defended:

```text
events
  -> metrics
  -> construct validity
  -> bounded claim
```

No Level 3 agency claim should be made directly from Level 0/1 traces.

This ladder is necessary but not sufficient. A second axis runs through every
level:

```text
             provenance
                 ^
                 |
events -> metrics -> constructs -> agency claims
```

An event is already different before it becomes a metric depending on whether
it was:

- directly observed by Lyra;
- self-reported;
- provider-derived;
- AI-generated or AI-enriched;
- retroactively repaired;
- imported from another system;
- produced after a user-facing exposure;
- operator/test/synthetic.

Provenance is not metadata decoration. It changes what the system is allowed to
compute, compare, publish, and learn from.

| Level | Examples | Failure mode |
| --- | --- | --- |
| Level 0 - Events | clicks, tasks, timestamps, sessions, provider rows | treating logs as behavior |
| Level 1 - Metrics | duration, delay, drift, completion, re-entry | treating computed values as constructs |
| Level 2 - Constructs | recovery friction, planning reliability, pressure load | underdefining what the metric means |
| Level 3 - Agency claims | "you procrastinate", "you work better under pressure", "you are improving" | claiming psychology or agency without validity |

LyraOS doctrine can be summarized as:

```text
No agency claim without construct defense.
No construct defense without clean-data profile.
No clean-data profile without exposure accounting.
No exposure accounting without asking whether Lyra changed the behavior.
```

This is the central claim-promotion rule.

## Four Invalid-Claim Cases

The paper should be concrete. Its strongest form is not:

```text
here is LyraOS's philosophy
```

It is:

```text
here are cases where ordinary systems would make invalid agency claims,
and here is how LyraOS withholds or weakens the claim.
```

### Case 1 - Delay Is Not Procrastination

Naive system:

```text
task delayed
-> procrastination
```

LyraOS:

```text
task delayed
-> provider imported late
-> execution may have happened outside the planning layer
-> claim withheld
```

The system may show a recoverable scheduling fact, but it may not infer
avoidance, discipline, motivation, or procrastination.

### Case 2 - Pauses Are Not Distraction

Naive system:

```text
repeated pauses
-> distracted user
```

LyraOS:

```text
repeated pauses
-> notification or nudge exposure occurred
-> later traces may be contaminated by the system's own intervention
-> claim withheld or exposure-stratified
```

The system may preserve the pause topology and recovery outcome. It may not
turn pause frequency into an identity or attention claim.

### Case 3 - Finals Usage Is Not Simple Retention

Naive system:

```text
more app usage during finals
-> retention increased
```

LyraOS:

```text
more app usage during finals
-> pressure-triggered return hypothesis
-> longitudinal validation required
```

The safe interpretation is that the instrument may become more valuable under
pressure. That is not yet proof of habit, product-market fit, improved agency,
or behavioral change.

### Case 4 - Completion Is Not Productivity

Naive system:

```text
completed 90%
-> highly productive
```

LyraOS:

```text
provider-only rows
-> retroactive repair
-> dirty trace
-> no productivity claim
```

The system may report a bounded completion or repair fact. It may not claim
productivity, competence, focus, or improvement from dirty or provider-only
rows.

## Why LyraOS Points At This

The original product question looked like:

```text
plan -> execute -> compare planned vs actual -> generate insight
```

Reality broke that model.

Users do not simply execute plans. They also:

- start work outside the planning layer;
- revise the plan after acting;
- use the system more when pressure rises;
- ignore the system when the week is calm;
- repair traces retroactively;
- respond to prompts that change future behavior;
- import provider context that is structure, not truth;
- create rows that are both measurement and intervention.

So the serious model became:

```text
Was there a plan?
Was it accepted?
Was execution linked to it?
Was the trace clean?
Was the user exposed to a system prompt?
Did the prompt alter later behavior?
Was the row repaired, imported, stale, retroactive, or provider-derived?
Can this metric survive slicing?
```

That shift is the paper's methodological center.

In the final paper, this section should move from narrative to observation.
Target empirical shape:

```text
Observation O1:
X% of execution occurred outside accepted plans.

Observation O2:
Y% of rows required retroactive repair or dirty-state exclusion.

Observation O3:
Pressure windows changed usage frequency.

Observation O4:
Exposure to Lyra outputs changed subsequent trace interpretation.
```

Those observations should motivate the architecture more strongly than prose
alone. Until cohort data is stable, these remain placeholders, not claims.

## ClaimCompiler As Operational Method

The contribution is not only conceptual. LyraOS attempts to operationalize the
paper through a claim gate:

```text
admitted evidence
-> EvidencePacket
-> ClaimCompiler
-> registered output surface
-> exposure lifecycle
```

ClaimCompiler is interesting because it makes the methodology executable. It
does not merely say "be careful with validity." It refuses to emit stronger
claims than the evidence, provenance, clean profile, sample size, and exposure
state allow.

The important architectural claim:

```text
bounded claim emission is a system behavior, not a writing style.
```

If the evidence cannot support a construct, the system should suppress,
weaken, or reframe the output before it reaches the user.

## Agency Is Not Visible In Completion Alone

The strongest correction from LyraOS dogfood is:

```text
Agency is not visible in completion.
Agency is visible in the boundary between planned execution,
unplanned execution, recovery, and reinterpretation.
```

This is why unplanned execution rate is not a side metric. If a user executes
outside the planning layer, then planning accuracy, estimation error, schedule
adherence, focus quality, and deadline drift can all become misleading in that
slice.

The math can be correct while the construct is invalid.

## Finals / Pressure Interpretation

If users return more during finals, the naive product interpretation is:

```text
retention improved during finals
```

The LyraOS interpretation is more cautious:

```text
the instrument becomes valuable when planning pressure rises and execution
reality becomes harder to hold mentally
```

That frames LyraOS less as a daily habit app and more as an agency-support
instrument under pressure.

This claim is still a hypothesis. It requires cohort analysis, retention
windows, qualitative feedback, and clean separation between operator use,
trusted users, and provider-assisted contexts.

## Required Validity Gates

Any paper in this direction should require:

- clean-data admission rules for each metric;
- dirty-reason distribution, not only a clean trace ratio;
- exposure contamination accounting;
- provider-truth boundaries;
- repaired/retroactive/stale row exclusion or explicit labeling;
- operator/test/synthetic row exclusion;
- slice-invariance checks across pressure windows, user cohorts, task classes,
  and provider contexts;
- falsifiers for every promoted construct;
- qualitative user review when a metric may be psychologically loaded.

## Safe Paper Framing

Safe:

```text
Systems that optimize human behavior too early make invalid agency claims.
LyraOS is a case study in trying not to do that.
```

Unsafe:

```text
LyraOS proves agency can be optimized.
LyraOS detects procrastination.
LyraOS knows when users avoid work.
LyraOS measures focus.
```

## Relationship To Existing Publish Paths

This direction is a methods paper that can precede or constrain the existing
behavioral papers.

Suggested slot:

| Path | Working title | Role |
| --- | --- | --- |
| Paper 0 | Measurement Integrity Before Agency Claims | Methods / construct-validity paper |
| Paper 1 | Metacognitive discrepancy as predictor of execution failure in knowledge workers | Behavioral hypothesis test |
| Paper 2 | Sequential task abandonment in knowledge workers | Daily execution sequence paper |
| Paper 3 | Unplanned execution rate | Construct / measurement contribution |
| Paper 4 | Planning confidence predicts scope inflation, not time estimation error | Mediation paper if VT-22 survives |

Paper 0 does not require the strongest predictive results first. It does
require rigorous examples of how LyraOS discovered, represented, and defended
against invalid measurement claims.

## One-Sentence Abstract

Productivity and AI-assistant systems often infer agency from event traces
without defending construct validity; LyraOS provides a case-study architecture
for delaying agency claims until variables survive clean-data, provenance,
exposure, and slice-invariance checks.
