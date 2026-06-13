# Research Optionality And Friction-Tested Methodology

**Status:** Product-research doctrine note.
**Created:** 2026-05-18.
**Purpose:** Capture the publishable research paths, the friction-shaped
instrument-design insight, the research/product oscillation, and the future
neuroadaptive sequence without upgrading any future claim into present truth.
**Governance:** Subordinate to `MANIFESTO.md`.

This document does not authorize publication claims, IRB claims, BCI claims,
autonomous adaptation, hidden interventions, or broader cohort scaling. It is a
sequencing and optionality map.

---

## 1. Targeted Publish Paths

The manifesto already behaves like a pre-registered research program. The
papers are latent in the instrument; they should be written only after the
architecture is reviewed and the relevant validity gates are satisfied.

| Path | Working title | Dependency | Near-term value |
| --- | --- | --- | --- |
| Paper 0 | Measurement Integrity Before Agency Claims | Clean-data, exposure, provenance, and slice-invariance examples from LyraOS bug hunts and cohort-readiness work | Methods / construct-validity contribution |
| Paper 1 | Metacognitive discrepancy as predictor of execution failure in knowledge workers | H1 eligible paired sessions, VT analyses, exposure stratification | Core hypothesis test |
| Paper 2 | Sequential task abandonment in knowledge workers: evidence for a cascade failure model of daily execution | Enough daily sequences across users, VT-20 structural controls | Fast behavioral trace paper |
| Paper 3 | Unplanned execution rate: a missing variable in personal productivity research | Construct definition plus operator/alpha demonstration | Instrument/measurement contribution |
| Paper 4 | Planning confidence predicts scope inflation, not time estimation error | VT-22 mediation evidence via scope-density traces | Highest-impact if confirmed |

The recommended sequence remains:

```text
stabilize instrument
  -> professor/researcher architecture review
  -> small cohort with constant feedback
  -> validity gates
  -> papers
```

Publication is quality-control infrastructure, not the product's primary goal.

### Paper 0 - Measurement Integrity Before Agency Claims

The newest paper direction is methodological:

```text
Systems that optimize human behavior too early make invalid agency claims.
LyraOS is a case study in trying not to do that.
```

The argument is that productivity and AI-assistant systems often jump from
events and metrics directly to claims about agency, focus, motivation,
avoidance, discipline, recovery, or improvement. LyraOS's more publishable
contribution may be the architecture that refuses that jump until variables
survive clean-data checks, provenance checks, exposure contamination checks,
and slice-invariance tests.

Paper 0 can be written before the strongest predictive papers if it stays
honest: it is a methods and construct-validity paper, not proof that LyraOS has
already optimized behavior.

Canonical note:
`docs/measurement_integrity_before_agency_claims.md`.

## 2. Friction-Tested Instrument Design

The important methodological insight:

```text
The architecture was shaped by friction, not isolated theorizing.
```

The design pattern:

```text
reality collision
  -> validity threat
  -> architectural response
  -> executable invariant
```

Examples:

| Friction | Architectural response |
| --- | --- |
| Claude/Codex intervention contaminated baseline behavior | Exposure Ledger and exposure-aware clean-data admission |
| Readiness inversion in operator data | VT-22 scope-inflation hypothesis and mediation test |
| Day-2 morning skip cascade | Cascade hypothesis and structural-dependency controls |
| Missing/ambiguous timer transitions | Observability-repair doctrine and repair-not-truth boundary |
| Baseet two-app flow friction | Provider-agnostic execution substrate and adapter boundary |
| Scheduler/Supabase outage alert noise | Scheduler degradation taxonomy and dedup/backoff contracts |
| Security hardening risk | Governance-only audit table and provider-failure auth/scoping invariant |

The git history is part of the methodology because it preserves when the
instrument changed, which friction caused the change, and which validity threat
or contract was created before stronger claims were made.

## 3. Research/Product Symmetry

LyraOS is strongest when product and research remain symmetric:

```text
Product friction reveals measurement threats.
Research constraints harden product behavior.
```

The product creates low-friction execution traces. The research layer prevents
those traces from being overinterpreted. The research layer is therefore not a
sidecar; it is quality control for product intelligence.

This symmetry is also why scaling must be cautious. More users do not only add
data; they add intervention effects, provider failures, cohort heterogeneity,
and new validity threats.

## 4. Neuroadaptive Sequence

The BCI/neuroadaptive arc is future-gated.

The breakthrough is not a "BCI productivity app." The deeper possibility is:

```text
longitudinal behavioral traces can semantically ground noisy cognitive-state
signals.
```

BCI signals are noisy, ambiguous, non-stationary estimates. LyraOS can make
them useful only if the behavioral substrate is already valid:

```text
execution instrumentation
  -> exposure validity
  -> longitudinal traces
  -> adaptive inference
  -> bounded cohorts
  -> behavioral model validation
  -> neuroadaptive integration
```

Until those gates hold, BCI remains a complementary-signal hypothesis, not a
product claim.

## 5. Why The Freeze Matters

The bottleneck is no longer idea generation.

The bottleneck is containment:

- sequencing,
- contracts,
- runtime verification,
- data isolation,
- exposure discipline,
- provider boundaries,
- and maintenance reliability.

The freeze is not a rejection of creativity. It converts conceptual emergence
into compounding structure.

Mantra:

```text
No new features unless they fix a boundary, test an invariant, or reduce
operational risk.
```

## 6. Next Architecture Priorities

Two scalability risks should be handled before further provider expansion or
adaptive-message experiments:

1. Provider adapter normalization:
   - governed by `docs/provider_adapter_contract.md`;
   - prevents Baseet/Moodle/Calendar/Jira dialects from leaking into Cortex.

2. Drift rollup scalability:
   - governed by `docs/drift_rollup_contract.md`;
   - keeps execution-drift metrics fast without turning derived rollups into
     observed truth.

These are maintenance tasks, but they are also research-methodology tasks. The
instrument is the science.
