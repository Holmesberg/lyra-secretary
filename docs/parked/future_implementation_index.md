---
authority: parked
may_authorize_code: false
runtime_owner: none
promotion_condition: >
  A future active implementation request names the product pressure,
  target files, tests, rollback path, clean-data impact, exposure impact,
  and authority boundary being changed.
---

# PARKED Future Implementation Index

Status: parked implementation memory. This folder preserves future product and
research pressure without authorizing runtime work.

PARKED is not a backlog. PARKED means:

```text
preserve the idea
deny implementation authority
name the promotion trigger
keep complexity out of the current product loop
```

## Hidden Invariants From The Docs Scan

Three doc-review agents independently converged on these invariants:

| Invariant | Classification | Current Authority | Notes |
| --- | --- | --- | --- |
| Capability is not authority. A component may compute richly, but may only publish, mutate, infer, prescribe, or govern through an explicit authority boundary. | active doctrine | `docs/AUTHORITY.md`, `docs/parked_governance_specs.md` | This constrains all future PARKED promotion. |
| Lyra is an execution-state instrument, not an AI planner. | active doctrine | `docs/behavioral_instrumentation_doctrine.md`, `docs/core_product_loop_wave_plan.md` | AI can assist parsing/enrichment/operator review but does not become truth authority. |
| Truth is layered: observed, self-reported, derived, inferred, latent, repaired, external, and unknown must stay distinct. | active doctrine | `docs/cortex_contract_v0.md`, tightened registries | Cortex is read-time canonicalization, not mutation. |
| Every mirror is also an intervention. | active doctrine | `MANIFESTO.md`, `docs/tightened_docs/12_intervention_exposure_risks.md` | Exposure-aware behavior is required before later learning consumes post-surface traces. |
| Product value comes from recoverable execution, not "more tasks." | active doctrine | `docs/core_product_loop_wave_plan.md` | The loop is capture/import -> confirmation -> execution tracking -> recovery. |
| Brain dump, pressure map, timers, resume banners, email delivery, and some exposure/event logs exist. | already implemented | runtime code + current docs | Implementation status must still be browser-verified per wave gates. |
| Unknown stays unknown. | active doctrine | `docs/cortex_contract_v0.md` | Unknown must not silently become zero, neutral, average, clean, or no-exposure. |
| Provider data is structure until confirmed. | active doctrine | provider/pressure docs | Calendar/LMS/email/browser traces can provide context; they are not execution truth without user confirmation and provenance. |
| Open threads should support re-entry recovery before insight. | parked hypothesis | `docs/context_switching_footprint_hypothesis.md` | Product copy uses "open threads" or "parked work," not `context_switching_footprint`. |
| No scalar judgment surfaces. | active doctrine | Manifesto H8 + semantic/integrity docs | No identity, focus, motivation, avoidance, worth, productivity, fragmentation, or switching scores. |
| Estimate provenance is necessary before AI/cohort/system estimates shape calibration. | future implementation idea | parked docs only | Does not authorize schema or UI changes yet. |
| Provider-blind recurring obligation middleware is needed for global schedule integration. | future implementation idea | parked docs only | Does not authorize provider adapters yet. |
| Passive browser extension capture may reduce friction. | unsupported / speculative | parked docs only | Explicitly postponed; does not authorize runtime tracking. |
| Lyra as validated research instrument. | unsupported / speculative | parked docs only | Current state is instrument candidate, not validated instrument. |

## Classification Rules

- **Already implemented** means runtime behavior exists and still needs normal
  testing/browser verification.
- **Active doctrine** means current docs constrain implementation but do not by
  themselves add features.
- **Parked hypothesis** means plausible, documented, and killable, but not an
  active implementation plan.
- **Future implementation idea** means useful direction with promotion
  criteria, but no runtime authority.
- **Unsupported / speculative** means conceptually interesting but currently
  lacks sufficient product pressure, validation, or governance maturity.

## Future Implementation Docs

The docs below are parked references. Their titles may contain "plan" because
they preserve implementation pressure, but none of them authorize code,
schema, UI, background jobs, notifications, claims, or provider adapters.

| Doc | Purpose | Promotion Trigger |
| --- | --- | --- |
| `lyra_execution_instrument_literature_map.md` | Map Lyra's tracked constructs to existing research instrument families. | Needed before external research framing, fellowship/paper positioning, or instrument validation work. |
| `open_threads_reentry_recovery_plan.md` | Preserve the open-thread/re-entry implementation path. | Trusted users fail to resume parked work or report losing task continuity. |
| `estimate_provenance_and_cold_start_plan.md` | Separate user estimates, system priors, AI estimates, and accepted planning windows. | Estimates appear useful but calibration becomes uninterpretable. |
| `provider_middleware_and_recurring_obligations_plan.md` | Park provider-blind schedule/obligation middleware, recurrence, ICS, sheets, meetings. | Existing manual capture cannot represent repeated/external obligations without clutter. |
| `passive_capture_extension_gate.md` | Park browser-extension/passive capture until complexity and governance can handle it. | Explicit timers remain a retention blocker and confirmation-gated passive evidence can be implemented without surveillance drift. |
| `future_research_design_and_validity_plan.md` | Park research-design methods, falsification gates, exposure handling, and sample thresholds. | Lyra moves from trusted-user product iteration toward publishable research. |

## Promotion Template

Every future implementation doc promoted from PARKED must answer:

- What product failure made this necessary now?
- Which authority boundary changes?
- Which files will change?
- Which tests/browser checks prove the invariant?
- What clean-data profile is affected?
- What exposure state is introduced?
- What can be rolled back?
- What is the kill criterion?

## Required Authority Links

- `MANIFESTO.md`
- `docs/AUTHORITY.md`
- `docs/behavioral_instrumentation_doctrine.md`
- `docs/cortex_contract_v0.md`
- `docs/cortex_product_research_contract_v0.md`
- `docs/core_product_loop_wave_plan.md`
- `docs/product_research_assumption_register.md`
- `docs/tightened_docs/05_metric_registry.md`
- `docs/tightened_docs/06_inference_registry.md`
- `docs/tightened_docs/07_research_integrity_risks.md`
- `docs/tightened_docs/09_semantic_conflicts.md`
- `docs/tightened_docs/12_intervention_exposure_risks.md`
- `docs/tightened_docs/14_governance_model.md`
