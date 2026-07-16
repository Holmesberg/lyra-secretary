# Plan-Execution Dynamics Ontology

---
authority: concept-note
may_authorize_code: false
runtime_owner: none
status: repository-grounded ontology proposal pending founder review
product_name: LyraOS
schema_authority: none
metric_authority: none
model_authority: none
experiment_authority: none
public_claim_authority: none
required_final_reviewer: founder
draft_review_date: 2026-07-15
---

## Catalogue And Foundation, Not Backlog

This document makes a family of product and research questions well-posed. It
does not make their answers valid and does not authorize their implementation.

## Hard Stop

This document does not authorize:

- a schema migration or immutable plan table;
- a plan score, productivity score, friction score, or user-quality score;
- a new prediction family or adaptive policy;
- automatic scheduling, recovery, mutation, or intervention selection;
- an ID3, CART, survival, Bayesian, causal, or AI model in runtime;
- a new user-facing insight, claim, dashboard, or Pressure Map behavior;
- a task dependency graph, passive tracking, or provider expansion;
- a causal claim about why a person acted, paused, deviated, or recovered;
- any change to Cortex admission, ClaimCompiler, exposure truth, or current
  runtime thresholds.

Movement from this ontology into code requires a separately approved seam with
characterization proof, an authority owner, privacy and retention review,
exposure treatment, rollback, and an explicit claim ceiling.

## 1. Thesis

LyraOS should model the relationship between a bounded decision episode and
its observed execution without turning that relationship into a judgment
about the person.

The candidate decision-support unit is not a task, a plan, or a user trait. It
is a bounded, named episode projection in which one or more obligations become
actionable, a decision is accepted or explicitly left unresolved, execution
may occur, and a declared policy evaluates closure. A `DecisionEpisode` is not
canonical observed identity and must not become a universal persisted event.
A versioned plan is optional evidence within an episode projection:

```text
provenance-bearing source evidence
-> bounded DecisionEpisode projection
   -> optional PlanLineage
   -> execution and work contribution
   -> outcome and recovery evidence
   -> measurement regime
-> decision support
```

LyraOS may participate in that trajectory through estimates, Pressure Map
projections, reminders, predictions, recovery options, or other visible
surfaces. That participation must remain reconstructible:

```text
decision episode
+ optional plan lineage
+ execution
+ outcome
+ system exposure
+ observation quality
= interpretable plan-execution evidence
```

The ontology therefore asks:

> Under observable conditions, what decision became active, what happened
> during execution, which obligations moved, what evidence is missing, and
> how did LyraOS participate?

It does not ask:

> What kind of person is this, and what single score describes them?

## 2. Why A Single Cost Function Is Insufficient

A scalar such as `L(P, E, X, Z)` is attractive because it permits ranking and
optimization. It is not currently defensible as the primary ontology.

Plan-execution evidence contains unlike quantities:

- minutes, timestamps, and ratios;
- categorical scope and recovery outcomes;
- deadline outcomes;
- missingness and provenance;
- user corrections and self-report;
- system prompts, suggestions, and accepted mutations.

No observed dataset can uniquely determine the normative exchange rate between
being late, spending more active time, changing scope, interrupting work, or
receiving another prompt. A scalar would silently encode product values and
could reverse rankings when its weights change.

The ontology uses a vector first. Scalarization is a later decision aid only
when all of the following are explicit:

- the decision being supported;
- the user or protocol that owns the preferences;
- the dimensions allowed to trade off;
- the weights or lexicographic constraints;
- the missing-value policy;
- the uncertainty policy;
- the validity window;
- the rollback and appeal path.

When preferences are not explicit, LyraOS should preserve Pareto-incomparable
alternatives rather than invent a universal winner.

### 2.1 Local decisions do not get local values for free

Surface-specific decision contracts are necessary, but they are not allowed to
invent independent philosophies of what matters. A future contract must draw
from one versioned objective vocabulary and one decision-time preference
snapshot.

An objective definition fixes its meaning, unit, sign, valid horizon,
admissible evidence, and prohibited interpretation. A preference snapshot
records the user-owned ordering or protocol constraint that applies to the
current decision. Pressure Map, recovery, and prompt policy may use different
subsets and horizons, but they may not silently reverse the same preference or
redefine the same objective.

The discipline is:

- one contract per decision family, not per endpoint or component;
- the canonical surface owner proposes the contract;
- the founder approves normative trade-offs and any new objective;
- measurement review constrains evidence admission and interpretation;
- executable fixtures enforce shared hard constraints and preference
  consistency across contracts;
- a strict recommendation conflict under the same evidence, action set,
  horizon, and preference snapshot is a contract defect.

Different recommendations are permitted when the action set, horizon, or
explicit user preference is genuinely different. The `DecisionTrace` must name
that difference. Naming a local objective is not enough; its relation to the
shared vocabulary must be testable.

## 3. Canonical Conceptual Objects

These are conceptual contracts. They are not database models.

### 3.1 `ObligationEvidence`

Represents work or a commitment that may require attention.

Minimum concepts:

- stable obligation reference when one exists;
- user-entered, provider-derived, or system-proposed source;
- due-time evidence and provenance;
- scope description and confidence;
- relation to canonical task and deadline state;
- contradiction and supersession state;
- whether the obligation is confirmed, candidate, stale, or unresolved.

Provider structure may identify an obligation or due time. It does not prove
effort, execution, learning, or completion.

### 3.2 `DecisionEpisode` Projection

Represents one bounded, policy-versioned view of a decision-to-closure
interval. It is deliberately not a generic event container or canonical
source event.

An episode opens only when all of the following are identifiable:

- one decision family and canonical owner;
- one user and bounded obligation set;
- one opening event such as explicit activation, accepted plan, timer start,
  or confirmed recovery action;
- one decision-time evidence snapshot;
- one closure policy and observation window.

It contains only evidence needed to reconstruct that decision, its execution,
its system exposures, and its closure. Unrelated telemetry, later analytics,
and arbitrary task history do not belong inside it.

An episode projection classifies closure as `resolved`, `partially_resolved`, `superseded`,
`abandoned`, `expired`, or `unknown`. Closure records the evidence available at
that time and the policy that classified it; it does not erase late
corrections. Episode projections may reference one another through explicit
`supersedes`, `recovery_for`, `continues`, or `contributes_to` relations.
Temporal proximity alone does not create a relationship.

If opening, membership, or closure cannot be reconstructed deterministically
from provenance-bearing source evidence without hindsight, the projection is
invalid. A domain-named workflow such as a future explicit Sprint may support
one bounded episode projection; that does not justify a universal episode
schema.

#### Fragment discipline

Commands, projections, corrections, and exposures do not become episode
fragments merely because they participate in one product loop. A future plan
may document a bounded domain fragment only when it has a real user decision,
an explicit opening boundary, irreducible new evidence, and a closure that is
useful in that domain.

The first implementation of a concept uses a local Data Delta:

```text
CREATE | REFERENCE | SNAPSHOT | DERIVE | FORBID_COPY
```

This table belongs to the approved product plan, not to a universal semantic
field registry. Shared infrastructure is considered only after two independent
implemented domains require identical meaning, ownership, missingness, and
lifecycle semantics. Product usefulness, evidence authority, cohort
transportability, and abstraction reuse remain separate gates; they must not
be collapsed into one promotion ladder.

### 3.3 `PlanLineage`

Represents an optional proposed or accepted intention within a
`DecisionEpisode`. A plan is decomposed rather than treated as one opaque
object:

- `ForecastComponent`: estimated effort, timing, uncertainty, and source;
- `CommitmentComponent`: obligations and minimum or optional scope accepted;
- `ConstraintComponent`: deadlines, availability, capacity, and protected
  boundaries;
- `PreferenceComponent`: decision-time priorities or lexicographic choices;
- `ActivationEvent`: when and how the plan became active;
- `RevisionEvent`: before/after values, timing, initiator, observable trigger,
  acceptance, and supersession.

Minimum concepts:

- plan identity and version;
- proposal time and acceptance time;
- acceptance actor and mechanism;
- source and estimate provenance;
- included obligations;
- planned active-time ranges;
- planned windows or blocks;
- ordering and optional relations;
- declared slack or unresolved capacity;
- scope assumptions;
- deadline assumptions;
- uncertainty at acceptance;
- predecessor and supersession relation;
- system exposures preceding acceptance.

An unaccepted draft is not an accepted plan. A system-created default is not
user intention merely because it exists in a task row.

A domain workflow may carry one bounded predecessor/successor relation without
implementing this conceptual object in full. Such a relation must be called
lineage honestly, remain queryable, and stay domain-owned. It does not justify
a generic lineage table, root identifier, revision graph, or shared service.

### 3.4 `OutcomeCriterionSnapshot`

Represents what counted as a satisfactory outcome at decision time. It is
versioned and time-bound so later outcomes cannot rewrite the original
criterion through hindsight.

Minimum concepts:

- criterion version and captured-at time;
- obligation and scope references;
- minimum, optional, protected, and explicitly excluded outcomes;
- deadline or timing tolerance;
- source and acceptance actor;
- uncertainty and unresolved criteria;
- supersession relation when the criterion legitimately changes.

### 3.5 `ExecutionEvidence`

Represents what LyraOS observed or the user later reported.

Minimum concepts:

- stopwatch-observed active intervals;
- wall-clock interval;
- pause events and explicit reasons;
- task switches and parent-child session relations;
- retroactive, recovered, corrected, or provider-indicated provenance;
- completion percentage and its self-reported status;
- scope relation and its self-reported status;
- unresolved, censored, or missing execution;
- raw and effective projections without overwriting either.

Elapsed time is not completed scope. Provider completion is not stopwatch
execution. Auto-recovered time is not direct observation.

### 3.6 `WorkContributionEvidence`

Represents which obligations an execution episode advanced. It prevents one
timer session from being forced into exactly one task outcome.

Minimum concepts:

- execution reference and one or more obligation references;
- `complete`, `partial`, `untouched`, `replaced`, `irrelevant`, or `unknown`
  contribution state;
- shared, approximate, user-confirmed, or unknown attribution;
- optional active-time allocation without requiring false precision;
- correction and supersession history.

One execution may advance several obligations. Contribution is not inferred
from adjacency or a shared category.

### 3.7 `OutcomeEvidence`

Represents consequences that are distinct from adherence.

Minimum concepts:

- completion, partial completion, abandonment, or unresolved state;
- deadline met, missed, displaced, or unknown;
- scope preserved, reduced, expanded, replaced, or unknown;
- resulting plan changes;
- downstream obligations displaced or left open;
- explicit user correction;
- later evidence that contradicts the first outcome;
- censoring and observation window.

A plan can be followed exactly and still produce an undesirable outcome. A
plan can be violated and still produce a desirable outcome.

### 3.8 `RecoveryEvidence`

Represents repair after a disruption or mismatch.

Minimum concepts:

- triggering interruption, miss, stale state, or plan revision;
- resume, reschedule, shrink, split, defer, drop, complete elsewhere, mark
  irrelevant, or remain unresolved;
- decision and action timestamps;
- user confirmation versus system proposal;
- resulting canonical mutation;
- later outcome and censoring;
- competing exposures during the recovery window.

Selecting a recovery action is not proof that recovery succeeded.

### 3.9 `ExposureContext`

Represents how LyraOS participated.

Minimum concepts:

- decision and eligibility;
- delivered candidate and exact surface version;
- authenticated browser render acknowledgement;
- interaction, dismissal, expiry, suppression, or `lost_unrendered`;
- accepted mutation;
- signal target and contamination horizon;
- concurrent or competing exposures;
- quiet-hours and burden state.

Queue insertion and delivery are not browser render. Exposure is context for
interpretation, not proof of causal effect.

### 3.10 `MeasurementRegime`

Represents how evidence could be produced during an episode. It names:

- available capture routes and their versions;
- prompted, known-unprompted, provider-derived, retroactive, corrected, and
  recovered observation classes;
- active system surfaces and exposure completeness;
- missingness, censoring, and clock conditions;
- privacy, retention, and account eligibility constraints;
- regime changes during the episode.

Two otherwise similar episodes are not directly comparable when their
measurement regimes differ materially.

### 3.11 `ObservationQuality`

Represents whether a projection can support a particular computation.

Minimum concepts:

- recorded, observed, self-reported, derived, inferred, or latent class;
- source and method version;
- missing fields;
- linkage quality;
- clock coherence;
- correction and recovery status;
- retroactive or synthetic status;
- censoring;
- exposure completeness;
- clean-profile eligibility and exclusion reasons;
- privacy or retention restrictions.

Unknown is a state, not zero.

### 3.12 `DecisionProjection`

Represents the named, versioned view of canonical evidence consumed by one
decision family. It contains:

- decision-family and projection version;
- source projection (`raw_observation`, `effective_user_history`,
  `clean_calibration`, or another registered source);
- objective and quality dimensions selected;
- time horizon and observation window;
- aggregation, denominator, missingness, and uncertainty rules;
- exposure and burden slice;
- admissibility and privacy restrictions.

A projection may select or aggregate registered evidence. It may not redefine
an atomic feature, change its sign, or silently substitute one source
projection for another.

### 3.13 `DecisionContract`

Represents one bounded decision family such as pressure orientation, recovery
transformation, or prompt delivery. It declares:

- canonical owner and version;
- named `DecisionProjection`;
- available actions and alternatives;
- shared objective definitions and active preference snapshot;
- hard constraints and dimensions allowed to trade off;
- uncertainty and missingness treatment;
- question and burden budget;
- tie-breaking and resolution modes;
- rollback, appeal, and expiry behavior.

The contract may recommend, compare, ask, fall back to descriptive output, or
abstain from selection. It does not own evidence truth or canonical mutation.

### 3.14 `ResolutionCoverageContract`

Represents the product cost of unresolved decisions without converting a
coverage target into pressure to fabricate an answer. It declares:

- supported resolution modes: `recommend`, `compare`, `ask_one`,
  `descriptive_fallback`, or `unavailable`;
- allowed abstention reasons;
- target coverage by context and evidence capability;
- maximum repeated unresolved encounters;
- question, interruption, and latency budgets;
- fallback order;
- the rate or failure condition that blocks promotion or disables the surface.

Exceeding a coverage boundary makes the surface fail its usefulness gate. It
never authorizes a weak ranking. A surface can abstain from choosing a winner
while still showing bounded alternatives, uncertainty, or one useful next
action.

### 3.15 `DecisionTrace`

Records the contract and projection versions, active preferences, considered
actions, filtered alternatives, decisive evidence, resolution mode, question
or abstention reason, and resulting user-visible output. It explains why two
surfaces differed without turning model-generated rationale into provenance.

## 4. Mathematical Separation

Let:

```text
P_v = accepted plan version v
T   = observed execution trace
O   = work outcome evidence
C   = observable context available at the decision point
H   = admissible prior history
Z   = LyraOS exposure and intervention context
E*  = registered canonical evidence and derived-feature families
```

Define canonical feature families rather than one materialized vector for every
consumer:

```text
Y* = {
  deadline_displacement,
  scope_resolution,
  active_time_calibration,
  initiation_displacement,
  temporal_displacement,
  interruption_footprint,
  downstream_displacement,
  recovery_latency
}
```

`Y*` contains registered consequences and plan-execution relations. It does
not contain instrumentation quality or system burden.

Define observation quality separately:

```text
Q* = {
  plan_acceptance_known,
  plan_version_known,
  execution_provenance,
  correction_status,
  recovery_status,
  linkage_quality,
  censoring,
  exposure_completeness,
  clean_profile
}
```

Define system burden separately:

```text
B* = {
  rendered_prompt_count,
  interruptiveness,
  dismissals,
  snoozes,
  accepted_system_suggestions,
  system_caused_mutations
}
```

`Y*`, `Q*`, and `B*` are canonical feature families, not a single fixed payload
computed once for every consumer. Each decision family consumes an explicit
projection:

```text
Pi[s,v](E*, context, horizon) -> (Y[s], Q[s], B[s])
```

For example, Pressure Map may consume displacement and capacity over a longer
horizon, while prompt delivery may consume proximal risk and recent burden.
Both projections must reuse the same registered atomic definitions. Any new
aggregation is versioned in `Pi[s,v]`; surface-aware computation may not hide
inside the meaning of `Y*`.

The prospective object is a distribution, not a point:

```text
R[s](P_v | C, H, Pi[s,v]) = distribution over Y[s]
```

The exposure-conditioned descriptive object is:

```text
R_observed[s](P_v | C, H, Z, Pi[s,v])
```

It must not be relabeled as unassisted or intrinsic plan risk. Strong causal
claims require an approved study design that identifies the effect of `Z`.

## 5. Candidate Outcome Dimensions

Every dimension remains provisional until its formula, units, sign,
denominator, exclusions, clean profile, uncertainty, and construct boundary are
registered.

| Dimension | Candidate observables | Interpretation ceiling |
| --- | --- | --- |
| Deadline displacement | signed completion-to-due interval | Work finished before/after recorded due time; not importance or learning |
| Scope resolution | confirmed completion and scope relation | Work outcome as reported/recorded; not quality unless separately observed |
| Active-time calibration | `E/P`, `log(E/P)`, `E-P` | Difference between accepted active-time estimate and observed active time |
| Initiation displacement | actual start minus accepted start/window | Timing relation; not procrastination or motivation |
| Temporal displacement | interval movement and plan revisions | Plan changed; not necessarily harmful |
| Interruption footprint | pauses, switches, open threads, interval union | Structural execution footprint; not distraction or fragmentation score |
| Downstream displacement | later accepted obligations moved, missed, or unresolved | Temporal association; not causal cascade without stronger design |
| Recovery latency | disruption to explicit resolution or censoring | Time to a recorded resolution; not resilience or recovery success |

## 6. Plan States

The ontology must preserve these distinct states:

| State | Meaning |
| --- | --- |
| `no_plan` | Work occurred without a prior accepted intention |
| `draft` | A plan candidate existed but was not accepted |
| `accepted` | The user or canonical authority explicitly accepted the plan |
| `superseded` | A later accepted version replaced this version |
| `withdrawn` | The plan was explicitly removed before execution |
| `partially_observed` | Acceptance or execution evidence is incomplete |
| `synthetic_default` | Runtime created a planning value for compatibility or operation |
| `retroactive` | Planning/execution evidence was entered after work occurred |

`no_plan` is neither zero cost nor user failure. It is a distinct planning
condition. `synthetic_default` and `retroactive` rows cannot be used as clean
plan calibration evidence merely because planned and executed values match.

## 7. Conformance Is Not Outcome

Plan conformance asks how observed events relate to the accepted plan.

Outcome evaluation asks what happened to the work and later obligations.

These must remain separate because:

- exact adherence can preserve a bad plan;
- deviation can be an intelligent response to new information;
- scope expansion can be valuable or harmful;
- rescheduling can protect a deadline or create downstream displacement;
- interruptions can be planned, necessary, avoidable, or unresolved;
- missing observation can mimic smooth execution.

A future alignment engine may describe deviations such as late start, extra
step, omitted block, reordered work, scope expansion, interruption, or early
termination. It may not treat every deviation as loss.

## 8. Plan Shape And Feasible Regions

A plan should not always be represented as one exact schedule.

Candidate plan-shape concepts include:

- duration interval rather than exact duration;
- acceptable start window rather than exact start;
- deadline or precedence constraint;
- minimum viable scope and expandable scope;
- protected buffer;
- optional or deferrable obligation;
- parallel, ordered, or independent work;
- known uncertainty;
- explicit no-capacity or unknown-capacity state.

This permits LyraOS to distinguish:

```text
plan failed
```

from:

```text
one exact point forecast was missed, but execution remained inside the
accepted feasible region
```

## 9. Plan Transformations

Future plan support may compare transformations without automatically applying
them:

- split;
- shrink scope;
- defer;
- reorder;
- add buffer;
- widen a start window;
- protect a deadline;
- remove an optional obligation;
- convert exact duration to an uncertainty range;
- request missing information.

Each transformation is a proposal with provenance. Only canonical user or
deterministic authority may accept it.

## 10. Interpretable Regime Discovery

The ontology makes interpretable conditional models possible after evidence
gates pass.

A future shallow tree could identify supported execution regimes such as:

```text
tight slack
+ uncertain scope
+ multiple short blocks
-> higher observed probability of temporal displacement
```

The leaf must report:

- included feature conditions;
- sample and user support;
- outcome distribution, not identity label;
- exposure state;
- missingness;
- calibration and holdout result;
- transportability ceiling;
- abstention conditions.

Classic ID3 is not the default recommendation because it targets categorical
classification through information gain and is vulnerable to sparse,
high-cardinality feature choices. Candidate methods include shallow regression
trees, conditional inference trees, survival trees for censored time outcomes,
and reviewed rule lists. No method is authorized here.

Hard invariants remain outside the model:

```text
authority and admission gates
-> deterministic versioned features
-> interpretable model in shadow
-> uncertainty and abstention
-> deterministic policy
-> explicit user confirmation
```

The model may discover a conditional partition. It does not own task truth,
exposure truth, claim authority, or mutation.

## 11. Root-Cause Boundary

The ontology enables mechanism signatures, not automatic root-cause claims.

For example, an overrun can be decomposed into observable candidates:

- scope expanded;
- active work took longer than accepted;
- pause overhead increased wall time;
- work started later than the accepted window;
- the plan was superseded;
- another obligation displaced it;
- execution was recovered or retroactively entered;
- important evidence is missing.

These can support competing hypotheses. They do not establish why the person
acted as they did.

Forbidden interpretations include motivation, discipline, focus, avoidance,
procrastination, competence, resilience, productivity, or clinical state.

## 12. Cold Start And Personalization

Cold-start support may use:

- explicit user estimates;
- versioned research or population ranges;
- task-semantic ranges;
- confirmed provider structure;
- survey-conditioned priors only within their validated construct ceiling;
- unknown or unresolved state.

Personal evidence may gradually update plan-shape expectations when it is:

- clean-profile admitted;
- linked to a known plan version;
- not retroactive or synthetic;
- separated by estimate source;
- exposure-aware;
- sufficiently supported;
- recalibrated under distribution shift.

Personalization means conditional evidence about plan-execution relations. It
does not mean assigning a stable identity to the user.

## 13. Required Projection Names

Any future computation must name which projection it uses:

| Projection | Purpose |
| --- | --- |
| `raw_observation` | Preserve instrument-recorded and source-recorded facts |
| `effective_user_history` | Apply append-only user corrections for audit and product history |
| `clean_calibration` | Exclude corrected, retroactive, recovered, contaminated, incoherent, or otherwise ineligible rows |
| `latest_plan_compatibility` | Compare current mutable task plan with execution, explicitly not historical plan quality |
| `versioned_plan_analysis` | Future-only projection requiring an accepted plan-version contract |

No projection silently substitutes for another.

Consumer projections are separate from source projections. A consumer must
name both, for example:

```text
pressure_orientation.v1 over effective_user_history
prompt_delivery.v2 over clean_calibration
```

Cross-projection fixtures must prove that shared atomic features retain the
same units, signs, and values and that registered aggregations reconcile with
their components.

## 14. Global Invariants

- Plan acceptance is explicit or unknown.
- A `DecisionEpisode` projection is bounded by one decision family, an opening
  event, an obligation set, a decision-time snapshot, and a closure policy.
- `DecisionEpisode` is not canonical identity or a generic telemetry
  container.
- Provenance-bearing source events precede episode reconstruction.
- `PlanLineage` is optional; planless work remains representable.
- Plan versions are not inferred from the latest mutable row.
- Outcome criteria are frozen at decision time and versioned when revised.
- One execution may contribute to several obligations without fabricating an
  exact time split.
- Plan absence is not zero or failure.
- Provider evidence is not execution truth.
- Stopwatch time is not scope completion.
- Adherence is not outcome quality.
- Recovery action is not recovery success.
- A rendered suggestion is behavior-shaping exposure.
- System-assisted estimates are not independent user estimates.
- Raw, corrected, and clean-calibration views remain distinguishable.
- Linked entities and time intervals are counted once.
- Unknown, censored, suppressed, and unrendered remain explicit.
- A model may rank only within its stated preference and evidence contract.
- Local contracts may select objectives but may not redefine them.
- An explicit preference snapshot is shared across contracts until the user or
  governing protocol changes it.
- Excessive abstention fails surface usefulness; it never compels an
  unsupported recommendation.
- Strict cross-surface conflicts under equivalent decision context fail the
  coherence suite.
- A tree leaf is an execution regime, not a person type.
- AI may propose candidates but cannot own facts, weights, claims, or mutation.

## 15. Example

Suppose a user accepts:

```text
Write report
planned active range: 90-120 minutes
accepted start window: 14:00-15:00
deadline: 20:00
scope: introduction + analysis + conclusion
```

Observed evidence:

```text
started: 15:20
active: 135 minutes
wall: 190 minutes
one 35-minute task-switch pause
scope: conclusion deferred
completed enough to submit at 19:40
Lyra rendered one recovery suggestion; user dismissed it
```

An honest interpretation is:

- start occurred after the accepted window;
- active time exceeded the accepted range by 15 minutes;
- wall time included a recorded task-switch pause;
- accepted scope was reduced;
- the recorded deadline was met;
- the recovery suggestion was rendered and dismissed;
- the plan deviated, but the deadline outcome was successful.

An invalid interpretation is:

> The plan had high cost because the user procrastinated and became
> distracted.

## 16. Questions This Ontology Makes Well-Posed

- Which plan shapes remain feasible under ordinary uncertainty?
- Which accepted estimates are calibrated by source and context?
- Where does slack disappear during execution?
- Which deviations protect outcomes and which displace later obligations?
- Which recovery transformations are selected and later followed by resolved
  work?
- Which missing variable would most change the comparison between two plans?
- Which execution regimes recur without being identity labels?
- How do visible LyraOS surfaces alter the evidence-generating process?
- When does personal history outperform a conservative cold-start prior?
- When should the system abstain?

## 17. Questions It Does Not Answer

- Why a person behaved as they did.
- Which intervention causes improvement.
- Whether a plan was intrinsically good.
- Whether deviation indicates low motivation or poor discipline.
- Whether one founder-specific regime generalizes to a cohort.
- Whether an AI explanation is true.
- How to choose normative weights for all users.

## 18. Literature Anchors

- Roijers, Vamplew, Whiteson, and Dazeley, [A Survey of Multi-Objective
  Sequential Decision-Making](https://arxiv.org/abs/1402.0590). Supports
  retaining multiple objectives and Pareto alternatives when scalarization is
  impossible, infeasible, or undesirable.
- Quinlan, [Induction of Decision
  Trees](https://doi.org/10.1007/BF00116251). Establishes the classic ID3
  framing and its categorical information-theoretic basis.
- Hothorn, Hornik, and Zeileis, [Unbiased Recursive Partitioning: A
  Conditional Inference
  Framework](https://www.zeileis.org/papers/Hothorn%2BHornik%2BZeileis-2006.pdf).
  Motivates separating variable selection from split estimation to reduce
  recursive-partitioning bias.
- de Leoni, Maggi, and van der Aalst, [Aligning Event Logs and Declarative
  Process Models for Conformance
  Checking](https://research.tue.nl/en/publications/aligning-event-logs-and-declarative-process-models-for-conformanc/).
  Supports describing alignment and deviation between a process model and an
  observed trace.
- Klasnja et al., [Microrandomized Trials: An Experimental Design for
  Developing Just-in-Time Adaptive
  Interventions](https://pmc.ncbi.nlm.nih.gov/articles/PMC4732571/). Supports
  explicit decision points, availability, proximal outcomes, and randomized
  treatment assignment before causal intervention claims.

## Hard Stop Repeated

This ontology authorizes no runtime metric, model, tree, plan table, schema,
prediction, intervention, prompt, automatic mutation, user-facing claim, or
experiment. It is a foundation for later falsification and founder decisions.
