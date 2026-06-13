# 14 Governance Model

**Purpose:** Rules to keep the repo understandable and scientifically safer over years.

## Naming Governance

- New meaning-bearing names require registry entry in
  `03_ontology_registry.md` or successor.
- Do not create synonyms for canonical Cortex metrics.
- Legacy aliases must include canonical mapping and deprecation status.
- Avoid psychologically loaded names unless the construct is explicitly latent.

## Ontology Governance

Every new concept must answer:

1. Is it observed, self_reported, derived, inferred, latent, or speculative?
2. What existing concept does it replace or refine?
3. What data makes it identifiable?
4. What would falsify it?
5. What user exposure can contaminate it?

If these cannot be answered, the concept is not admitted.

## Research Governance

- Operator-only findings do not generalize by default.
- JARVIS proposals require falsifier, evidence fields, and generality tag.
- Promoted hypotheses need rejected hypotheses nearby; all-green logs are
  suspicious.
- Context-switching hypotheses must separate consequence topology from causal
  explanation before entering any product surface.
- External imports and retroactive data must stay out of native calibration
  unless the profile allows them.
- Research value alone cannot justify new required user inputs. Any
  user-burdening variable requires a successor contract or explicit amendment
  documenting identifiability gain, retention risk, clean-data impact, and
  burden offset.
- Retention is a research precondition: without longitudinal usage, the
  inference layer loses the data stream it claims to model.

## Documentation Requirements

Every measurement/inference change must document:

- contract touched
- invariant relied on
- clean-data profile
- provenance assumptions
- uncertainty left unresolved
- tests added or intentionally not applicable

Code without documentation is incomplete for Cortex-adjacent work.

## Invariant Protection Rules

- No schema mutation without invariant justification.
- No derived metric persistence unless a contract explicitly allows it.
- No latent persistence as observed fact.
- No unified productivity/worth score.
- No user-facing inferred copy without confidence and exposure tracking plan.
- Cortex projections that leave the current process must carry
  `cortex_schema_version_at_evaluation`.
- `unknown` must propagate through projections and aggregations unless a
  clean-data profile explicitly excludes it and declares denominator semantics.
- Cortex must remain read-only: no ORM writes, Redis writes, external sync
  writes, notifications, or state repair.
- Derived metrics must be functions of raw observables, not other derived
  metrics, unless the contract defines the transformation.
- Inference must not consume service-layer caches, Redis stopwatch state, UI
  state, or generated summaries as behavioral evidence.
- Dependency direction must be checked as a DAG, not only by direct imports.

## Semantic Review Checklist

Before merge:

- Does this change mix observed and latent language?
- Does it introduce a new name for an existing metric?
- Does it change sign convention?
- Does it change a clean-data filter?
- Does it expose a user to a claim that future learning will consume?
- If this mentions switching, interruption, or fragmentation, does it avoid
  claiming why it happened?
- If this adds a switching/re-entry surface, does it support open-thread
  recovery actions instead of insight-first copy or a fragmentation score?
- If this interprets task switches, does it include resolution outcome
  (`resumed`, `completed_later`, `rescheduled`, `dropped`,
  `marked_irrelevant`, `stale_open_end_of_day`, or `auto_closed`)?
- Does it rely on docs that code does not verify?
- Does it add a user-burden variable for research value rather than product
  completion, accessibility, latency, clarity, or bug repair?
- Does it convert `unknown` into neutral, bounded, zero, average, or
  no-exposure?
- Does a structural move alter a metric, threshold, clean-data filter, or
  user-facing inference output?
- Does Cortex gain a write path or dependency path back into services or
  inference?

## AI-Assisted Coding Constraints

- AI output must cite repository evidence.
- AI must mark uncertainty rather than smoothing it.
- AI must not expand ontology for elegance.
- AI must not promote speculative docs into implementation without operator
  review.
- AI must not remove research artifacts without classification and archive path.
- AI must not perform broad module moves before characterization tests,
  clean-data profile centralization, unknown-propagation tests, and dependency
  DAG checks exist.

## Single-Operator Maintainability

The repo should optimize for:

- small canonical owners
- explicit registries
- fewer magic thresholds
- documented lineage
- stable invariants
- readable failure modes

It should not optimize for:

- clever abstractions
- broad dashboards
- speculative predictors
- more ontology
- more AI-generated summaries
