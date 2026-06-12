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
