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
- External imports and retroactive data must stay out of native calibration
  unless the profile allows them.

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

## Semantic Review Checklist

Before merge:

- Does this change mix observed and latent language?
- Does it introduce a new name for an existing metric?
- Does it change sign convention?
- Does it change a clean-data filter?
- Does it expose a user to a claim that future learning will consume?
- Does it rely on docs that code does not verify?

## AI-Assisted Coding Constraints

- AI output must cite repository evidence.
- AI must mark uncertainty rather than smoothing it.
- AI must not expand ontology for elegance.
- AI must not promote speculative docs into implementation without operator
  review.
- AI must not remove research artifacts without classification and archive path.

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
