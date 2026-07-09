---
authority: parked
may_authorize_code: false
runtime_owner: none
---

# Behavior Transition Equation Stack

Status: parked research direction. This document preserves the equation
families discussed during freeze review. It does not authorize runtime code,
new analytics claims, adaptive behavior, AI synthesis, or user-facing insight
surfaces.

## Freeze Boundary

```text
raw traces -> clean profile -> behavior-change projection -> EvidencePacket ->
ClaimCompiler -> registered surface
```

Only the first two links are current runtime concerns. The equation stack may
be revisited only after deterministic evidence packets, claim suppression,
exposure accounting, and the operator cockpit are stable.

Forbidden during the active freeze:

- AI synthesis over these equations.
- User-facing behavior-change claims.
- Cascade, sequence-disruption, or adaptive interventions.
- Identity, motivation, discipline, avoidance, focus, agency, or productivity
  claims.
- Runtime equations that silently change recommendations or scheduling.

## Equation Families To Preserve

| Family | Candidate methods | Safe interpretation |
|---|---|---|
| Level shift / change point | likelihood ratio, CUSUM, Mann-Whitney | A distribution may have shifted across two clean windows. |
| Variance collapse | F-test, sample entropy | Execution variance may have narrowed or widened. |
| Recovery decay | AR(1), phi, impulse response | Recovery latency may show different persistence after interruptions. |
| Topology shift | rolling Pearson/Spearman coupling changes | Coupling between planning, pressure, execution, or recovery metrics may have changed. |
| Metacognitive shift | KL/Jensen-Shannon divergence between planned and actual duration distributions | The shape of planning-vs-execution mismatch may have changed. |

These are diagnostic projections, not truth about the user.

## Admission Gates

Any future implementation plan must define:

- clean-data profile and denominator;
- included/excluded row classes;
- dirty reason distribution;
- exposure policy and unknown-exposure handling;
- minimum sample size and window length;
- measurement space: minutes, ratio, or log-ratio;
- falsification criteria;
- output surface and claim boundary;
- read-only behavior and mutation prohibition.

Unknowns must stay unknown. Provider-only, repaired, auto-closed,
retroactive, exposure-contaminated, voided, deleted, operator, test, and
synthetic rows must be excluded or explicitly bucketed.

## Output Boundary

Allowed future output shape:

```text
observational metric delta with uncertainty and exclusions
```

Forbidden output shape:

```text
Lyra improved the user's focus, discipline, recovery, agency, or productivity
```

AI may later translate admitted evidence packets into inspectable language only
after the freeze lifts. AI may not create confidence, causality, identity,
hidden evidence, or stronger claims than the deterministic packet permits.

## Promotion Conditions

Do not promote this stack until:

1. `/operator` is decision-grade and read-only.
2. Wave 5B browser verification passes.
3. Wave 6 final cohort-readiness proof passes.
4. Clean trace denominator and dirty reason distribution are stable.
5. Exposure render linkage is reliable.
6. A new feature plan names the exact user pain decreased by the equation.
