# Decision-Episode Repository Archaeology Prompt

---
authority: audit-template
may_authorize_code: false
runtime_owner: none
status: reusable read-only prompt
product_name: LyraOS
schema_authority: none
model_authority: none
experiment_authority: none
required_final_reviewer: founder
review_date: 2026-07-16
---

## Purpose

Act as a cross-functional architecture, product, research, and repository-
archaeology team for LyraOS. Recover latent design intelligence already in the
repository before proposing new primitives.

The central question is:

> What did LyraOS already build, document, test, or preserve without fully
> understanding why, and which artifacts become powerful now that a better
> ontology exists?

## Candidate Frame, Not Doctrine

```text
CanonicalTransitionLedger
-> DecisionEpisode
   -> optional PlanLineage
      -> ForecastComponent
      -> CommitmentComponent
      -> ConstraintComponent
      -> PreferenceComponent
      -> ActivationEvent
      -> RevisionEvent
   -> ExecutionEvidence
   -> WorkContributionEvidence
   -> OutcomeCriterionSnapshot
   -> OutcomeEvidence
   -> RecoveryEvidence
   -> MeasurementRegime
-> canonical Y*/Q*/B* feature families
-> named consumer projection
-> bounded DecisionContract
-> DecisionTrace
-> recommendation / comparison / one useful question / fallback / abstention
```

The product goal is not more descriptive metrics. It is better real decisions:
priority reallocation, minimum plan repair, beneficial deviation, early
self-correction, revision-aware recalibration, useful clarification, recovery,
and one useful next action.

The research goal is not personality classification. It is discovery of
repeatable structures in episodes, plan shapes, revisions, execution
topologies, interruptions, recoveries, measurement regimes, and outcomes.

## Hard Constraints

- Begin and end read-only with respect to runtime code and data.
- Do not implement schema, models, predictions, prompts, experiments, runtime
  behavior, or user-visible claims.
- Archived and concept documents are evidence of intent, not implementation
  authority.
- Distinguish original intent, current behavior, inferred latent value, and
  speculative future value.
- Cite source paths, line numbers, tests, documents, and commits.
- Give every inferred rationale a confidence label.
- Do not call a pattern a trait, cause, behavioral truth, or generalizable
  regime without sufficient evidence.
- Prefer recovered value over new primitives.
- A recovered capability matters only if it improves a user decision, reduces
  burden, improves recovery or cold start, increases identifiability, or
  enables a defensible computation.
- Preserve counterexamples and negative findings.
- Attempt to kill canonical `DecisionEpisode`: if its opening, membership, or
  closure requires hindsight or surface policy, retain source events and use a
  named projection or domain-specific workflow instead.
- Do not assume a canonical transition ledger exists. Verify event provenance
  before reconstructing any episode.

## Sources

Inspect active source, tests, fixtures, migrations, APIs, services, frontend
surfaces, registries, authority docs, concept notes, parked and archived plans,
audits, research notes, issues, Git history, deleted or renamed files,
comments, TODOs, feature flags, dead components, compatibility paths, exports,
operator tools, and exposure infrastructure.

Use Git history to find features with strong original rationales whose current
names or consumers no longer explain them.

## Role-Separated Passes

Run independent passes with non-overlapping responsibilities. Agent fan-out is
optional; role separation and evidence reconciliation are mandatory.

1. **Repository archaeologist:** recover first commit, original problem,
   terminology, pivots, surviving intent, and confidence.
2. **Latent capability mapper:** identify existing inputs, missing inputs,
   ontology dependencies, product use, research use, burden, and evidence
   ceiling.
3. **Forgotten insight historian:** recover parked mechanisms, unusual
   invariants, renamed ideas, and concepts preserved for later.
4. **Product recombination analyst:** find high-leverage combinations of
   existing systems requiring at most one small primitive.
5. **ML and representation analyst:** separate useful episode-level structure
   from route, synthetic-row, correction, and exposure artifacts. Cluster
   episodes before users.
6. **Ontology adversary:** attempt to show that each capability is merely
   renamed, founder-specific, evidence-incomplete, burdensome, or better served
   by a deterministic rule.
7. **Integration architect:** identify one bounded vertical slice, one
   projection, one decision family, one trace, and one useful question.

Do not ask any role to search for surprises. Surprises are derived only after
independent findings are compared.

## Required Deliverables

### 1. Forgotten Intent Inventory

| Artifact | Original reason | Current behavior | Why forgotten | Evidence | Confidence |
| --- | --- | --- | --- | --- | --- |

### 2. Latent Power Map

| Artifact | Isolated meaning | New role | Computation | Product value | Missing primitive | Readiness |
| --- | --- | --- | --- | --- | --- | --- |

Readiness is one of: `available_now`, `after_substrate_repair`,
`after_one_minimal_primitive`, `cohort_dependent`, `model_dependent`,
`experiment_dependent`, or `invalid`.

### 3. Unexpectedly Valuable Existing Features

For 10-20 cases, state original purpose, prior limitation, connecting
abstraction, enabled computation, user experience, missing evidence, and
falsification condition.

### 4. Idea Lineage Graph

```text
old artifact
-> local problem
-> why disconnected
-> ontology shift
-> unified role
-> product computation
```

### 5. Cold-Start And Clustering Architecture

Cover questionnaire prior, early observations, personal calibration, cohort
partial pooling, eventual personal dominance, episode versus user clustering,
sparse support, uncertainty, distribution shift, and artifact detection.

### 6. Recombination Opportunities

```text
component A + component B + optional small primitive -> new capability
```

For each, name value, evidence quality, burden, reversibility, and proof.

### 7. Pre-Adaptation Report

Separate genuine pre-adaptation, lucky reuse, intentional preservation, and
overfitting the new ontology onto old code.

### 8. Ranked Action Plan

Separate `before_cohort`, `collect_during_cohort`, and `keep_parked`. Every item
names the user problem, reused artifacts, smallest missing primitive, proof,
rollback, and stop condition.

## Final Synthesis

End with:

### A. Five biggest recovered insights
### B. Five underestimated existing features
### C. Three strongest product recombinations
### D. Single best pre-cohort vertical slice
### E. Strongest falsification result
### F. What should remain untouched
### G. Founder decision packet
### H. What surprised you?

For H, list exactly 10 findings that no role was explicitly asked to find.
They must be emergent observations derived after comparing evidence, not
restatements of assigned questions. Rank each by:

- conceptual novelty;
- product leverage;
- research leverage;
- confidence.

## Standard

The standard is not "many connections were found." The standard is:

> Forgotten intent was recovered, a genuinely enabled computation was
> demonstrated, and the smallest product change that turns existing
> architecture into user value was identified.
