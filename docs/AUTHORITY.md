# LyraOS Authority Map

**Status:** Canonical implementation-governance map.
**Created:** 2026-05-21.
**Purpose:** Prevent capability from silently becoming publication, mutation,
inference, intervention, or doctrine authority.

This document is the current cross-repo authority hierarchy. It does not
authorize new product features by itself. It tells agents and engineers which
documents may authorize code, which layers own which decisions, and how to
detect authority drift.

---

## 1. Authority Metadata

Active non-archived docs should be understood as carrying one of these statuses:

```yaml
authority: canonical | active-contract | implementation-plan | concept-note | external-orientation | historical | parked
may_authorize_code: true | false
runtime_owner: backend | frontend | docs | operator | none
supersedes:
superseded_by:
```

Defaults until a doc is explicitly tagged:

| Document class | Default authority |
| --- | --- |
| `MANIFESTO.md` | Canonical philosophy; historical sections are non-authorizing unless current transition docs promote them. |
| `docs/current_transition_state.md` | Active branch authority. |
| `docs/architecture_freeze_priority_hold_2026_05_20.md` | Active freeze authority. |
| Cortex, provider, output-surface, exposure, and security contracts | Active contracts. |
| Product/public orientation docs | External orientation; cannot authorize runtime authority alone. |
| Roadmaps, project history, evolution docs, parked ideas, archive docs | Historical or parked unless promoted by current transition state. |

No agent or engineer may treat an aspirational doc as implementation permission
unless it has active authority metadata or is cited by the active transition
state.

---

## 2. Authority Ladder

Every behavior-shaping surface should occupy one rung:

```text
observed_trace
derived_metric
interpretation
suggestion
intervention
adaptation
mutation
operator_only_action
```

Capability and authority are separate:

```text
A component may compute richly.
It may only publish, mutate, infer, prescribe, or govern through an explicit
authority boundary.
```

Capability can also become trajectory-shaping pressure. A surface that
prioritizes, warns, nudges, ranks, recommends, or adapts may change what the
human does next even if it never mutates a row. Authority review must therefore
ask not only "can this compute?" but "what human trajectory does this steer?"

---

## 3. Layer Ownership

| Layer | Question it may answer | Authority it does not own |
| --- | --- | --- |
| Inbound API | Is this payload legitimate to receive? | Semantic interpretation. |
| Provider adapter | What provider-blind fact did this provider event mean? | Claim publication or clean-data admission. |
| Analytics | What pattern exists in admitted data? | Public truth or mutation. |
| EvidencePacket | Is this evidence admissible for a bounded claim? | Provider DTO, output grammar, or synthesis container. |
| ClaimCompiler | Can this deterministic claim safely emit? | New meanings, AI synthesis, or adaptive intervention. |
| Output surface translator | What may this user-facing surface publish? | Evidence eligibility. |
| Pressure Map | Where should repair attention go? | Automatic task/calendar mutation or student-risk scoring. |
| Exposure Ledger | What behavior-shaping output was shown or suppressed? | Universal behavioral memory. |
| Agent council / JARVIS / OpenClaw | What should a human consider? | Silent doctrine, code, or runtime mutation. |

---

## 4. Current Phase Constraints

For the evidence-packet branch:

- no new public analytics claims,
- no AI synthesis promotion,
- no public cascade intervention,
- no new adaptive authority,
- no Baseet live integration,
- no DB migration unless a later implementation plan explicitly authorizes it.

Baseet and Moodle are provider edges. They may preserve local vocabulary for UI,
but Cortex, clean-data admission, ClaimCompiler, and adaptive logic must consume
provider-blind primitives.

---

## 5. Review Rule

Any future change that increases capability must state whether it also changes:

- publication authority,
- mutation authority,
- inference authority,
- intervention authority,
- trajectory-shaping authority,
- clean-data admission,
- exposure behavior,
- provider trust,
- or operator/agent authority.

If the answer is unclear, the change is not ready.

Every stabilization wave must also leave a deletion and parking ledger. The
ledger must say what was removed from runtime, what was moved to another layer,
what stayed parked, and the exact condition that would justify reintroducing
it. Silent cuts are not allowed.
