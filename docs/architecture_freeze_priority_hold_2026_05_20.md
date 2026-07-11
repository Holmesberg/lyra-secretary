# Architecture Freeze Priority Hold

**Date:** 2026-05-20
**Status:** Temporary priority hold; preserve for later, do not implement now.

This note exists so the May 20 evidence/synthesis breakthrough is not lost
while LyraOS deliberately pauses architecture expansion.

The branch `feature/evidence-packet-claim-compiler` already introduced the
first containment layer:

```text
raw traces -> EvidencePacket -> ClaimCompiler -> existing registered surface
```

That is enough for the current pass. The next move is stabilization, not a new
conceptual layer.

---

## Hard No For The Current Cycle

Do not implement these now:

- AI synthesis over evidence packets.
- public cascade or sequence-disruption interventions.
- new adaptive authority.
- new behavioral ontology.
- neuroadaptive or digital-twin architecture.
- new user-facing analytics claims.
- external "execution physics" positioning.

The deterministic evidence layer is still unstable. Packet grammar, suppression
semantics, clean-data ownership, discrepancy interpretation, and cascade
implications are still settling. Adding persuasive synthesis now would risk
turning unstable math into fluent language.

This is not restraint for its own sake. It is operational compression.

---

## Preserved Breakthrough

The breakthrough worth preserving is the separation between:

```text
behavioral inference
```

and:

```text
behavioral synthesis
```

Deterministic analytics and claim compilation should own evidence, confidence,
suppression, and provenance. If an AI synthesis layer exists later, it must sit
downstream of evidence packets and translate competing hypotheses into
inspectable language. It must not create confidence, causality, identity, or
hidden evidence.

The preferred future reasoning boundary for that layer is:

```text
LyraOS
-> ReasoningRuntimeContract
-> OpenClawAdapter
```

LyraOS should have one AI reasoning contract rather than multiple embedded
assistant minds. OpenClawAdapter remains a candidate drafting and
operator-reasoning adapter only; ClaimCompiler, Cortex, canonical services, and
the exposure lifecycle keep their existing authority.

This identifies preferred future ownership only. It does not authorize runtime
AI synthesis, model integration, prompt execution, user-facing draft
generation, or reasoning-adapter-to-product wiring.

This is promising, but not ready for implementation.

---

## Highest Later Priority

When the freeze lifts, preserve this order:

1. Stabilize deterministic evidence packets and claim suppression semantics.
2. Improve pressure-map usefulness and immediate value density.
3. Strengthen clean-data, exposure, and output-surface ownership.
4. Measure cascade detection quality as diagnostics before interventions.
5. Improve runtime reliability and low-friction execution traces.
6. Only then revisit dormant decision points, hosted-model budgets, and AI
   synthesis.

EvidencePacket and ClaimCompiler must remain invisible infrastructure unless
they materially improve correctness, auditability, or safety. Users should feel
less chaos, not more epistemic machinery.

---

## Revisit Conditions

Do not reopen AI synthesis or public cascade intervention until most of these
are true:

- finals/academic pressure has cleared enough for cold review;
- at least one stable evidence cycle has passed without packet grammar churn;
- current browser/API smoke and CI/CD proof remain normal;
- hosted-public proof records frontend/backend build IDs, or explicitly records
  deployment lag;
- current cohort traces expose real user value or friction;
- suppression semantics are boring and well-tested;
- primary product bottlenecks are empirical, not conceptual;
- the next implementation plan can name exactly what user pain decreases.

If those conditions are not met, keep the ideas parked.

---

## Kill Or Demote Criteria

Demote the evidence architecture if it becomes visible complexity tax without
improving correctness, auditability, or claim suppression.

Keep AI synthesis parked if deterministic evidence remains unstable, if output
copy starts collapsing uncertainty, or if the synthesis layer becomes a way to
make weak signals sound stronger.

Keep cascade intervention parked if the signal remains diagnostic but the
intervention timing, exposure design, proximal outcome, and suppression
criteria are not defined.

Stop using "execution physics" in external-facing scientific language unless
the project can define the relevant state, input, disturbance, objective,
stability risk, and evidence boundary. Internally the metaphor can guide
design; externally it must not outrun validation.

---

## Governing Links

Read this note with:

- `docs/current_transition_state.md`
- `docs/cross_domain_breakthrough_audit_2026_05_20.md`
- `docs/single_authority_contract.md`
- `docs/cortex_contract_v0.md`
- `docs/cortex_product_research_contract_v0.md`
- `docs/tightened_docs/15_long_term_repo_strategy.md`
- `docs/tightened_docs/17_immediate_freeze_targets.md`

The immediate operating mode is architecture idleness: keep the current
structure still long enough for users, traces, reliability, and academic
constraints to push back.
