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

If AI synthesis is reopened, the preferred reasoning host is OpenClaw running a
GPT-class synthesis model. This keeps future AI synthesis behind one operator
reasoning boundary instead of scattering synthesis across parked Jarvis
compatibility code, frontend components, workers, or ad hoc endpoint code.

This identifies preferred future ownership only. It does not authorize runtime
AI synthesis, model integration, prompt execution, user-facing draft
generation, or OpenClaw-to-product wiring.

The allowed future path is:

```text
Cortex clean profile
-> Admission / Coverage Gate
-> EvidencePacket
-> ClaimCompiler admissibility check
-> OpenClaw/GPT draft synthesis
-> ClaimCompiler / output-surface policy check
-> registered surface with exposure lifecycle
```

AI synthesis must:

- cite evidence packet IDs or safe source refs;
- preserve competing hypotheses and uncertainty;
- state sample sizes, exclusions, and dirty reasons;
- stay downstream of deterministic claim gates;
- use registered output surfaces and exposure logging.
- remain a draft until ClaimCompiler and the target output surface accept it.

AI synthesis must not:

- create confidence;
- claim causality;
- assign identity labels;
- infer motivation, discipline, avoidance, focus, agency, productivity, or
  competence;
- hide evidence or turn operator hypotheses into user-facing truth.
- mutate task, deadline, timer, provider, notification, exposure, or insight
  state directly.

Admission/Coverage Gate, EvidencePacket, and ClaimCompiler have separate
authority:

- Admission/Coverage Gate decides whether rows are eligible for a claim
  computation.
- EvidencePacket packages eligible evidence for one bounded claim.
- ClaimCompiler decides whether that bounded claim may emit.

EvidencePacket must not become a hidden second admission gate, and
ClaimCompiler must not accept packets whose row eligibility is undeclared.

If ClaimCompiler or surface policy rejects an AI draft, OpenClaw may propose a
new draft from the same evidence packet. That loop must remain an operator or
system drafting loop, not reinforcement learning over private user behavior.

## Behavior-Transition Math Boundary

Behavior-transition equations may later produce diagnostic evidence packets.
They may not directly publish insights or change scheduling. Any future packet
must declare clean profile, denominator, exposure policy, window, uncertainty,
and falsification criteria before ClaimCompiler may consider it.

## Current Stop Line

Do not begin new synthesis or behavior-transition runtime work until the
operator cockpit is clear, Wave 5B browser verification passes, and Wave 6
final cohort-readiness proof passes.

## Related Authority Docs

Read this note with:

- `docs/architecture_freeze_priority_hold_2026_05_20.md`;
- `docs/single_authority_contract.md`;
- `docs/openclaw_orchestration_contract_v0.md`;
- `docs/parked/behavior_transition_equation_stack.md`;
- `docs/parked/uncertainty_reduction_computation_council_2026_06_29.md`;
- `docs/operator_dashboard_contract.md`.
