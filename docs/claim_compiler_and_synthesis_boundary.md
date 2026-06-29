---
authority: concept-note
may_authorize_code: false
runtime_owner: none
---

# ClaimCompiler And Synthesis Boundary

Status: non-authorizing boundary note. This document records the current
separation between deterministic evidence compilation and future synthesis. It
does not authorize AI synthesis, new analytics claims, adaptive behavior, or
runtime schema expansion.

## Current Shipped Path

Current shipped insight authority is deterministic:

```text
analytics math -> EvidencePacket -> ClaimCompiler -> registered output surface
```

ClaimCompiler may compile only bounded claims from explicit evidence packets.
It must not infer new behavior, create latent labels, or upgrade weak evidence
into fluent certainty.

## Synthesis Vocabulary

| Term | Current status | Boundary |
|---|---|---|
| Deterministic synthesis | Existing implementation pattern | Rule-based compilation from admitted evidence. |
| AI synthesis | Parked | Future translation layer downstream of evidence packets only. |
| Operator synthesis | Operator-only | Human-facing debugging/hypothesis support, not product truth. |
| Behavior-transition synthesis | Parked | Future diagnostic projection, not current user-facing claim. |
| Adaptive recommendation | Forbidden in freeze | Requires a separate implementation plan and exposure/rollback gates. |

## AI Synthesis Rules If Reopened Later

AI synthesis must:

- cite evidence packet IDs or safe source refs;
- preserve competing hypotheses and uncertainty;
- state sample sizes, exclusions, and dirty reasons;
- stay downstream of deterministic claim gates;
- use registered output surfaces and exposure logging.

AI synthesis must not:

- create confidence;
- claim causality;
- assign identity labels;
- infer motivation, discipline, avoidance, focus, agency, productivity, or
  competence;
- hide evidence or turn operator hypotheses into user-facing truth.

## Behavior-Transition Math Boundary

Behavior-transition equations may later produce diagnostic evidence packets.
They may not directly publish insights or change scheduling. Any future packet
must declare clean profile, denominator, exposure policy, window, uncertainty,
and falsification criteria before ClaimCompiler may consider it.

## Current Stop Line

Do not begin new synthesis or behavior-transition runtime work until the
operator cockpit is clear, Wave 5B browser verification passes, and Wave 6
final cohort-readiness proof passes.
