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
| Analytics endpoints | Which compiled analytics product should be exposed? | Clean filters, metric definitions, confidence semantics, claim authority, or mutation. |
| Cortex / registered computation modules | What admitted pattern exists under a declared clean profile? | Publication authority or mutation. |
| Admission / Coverage Gate | Is this row eligible for a claim computation? | Claim packaging, language generation, or publication. |
| EvidencePacket | How should eligible evidence be packaged for a bounded claim? | Row admission, provider DTO authority, output grammar, or claim emission. |
| ClaimCompiler | Can this deterministic claim safely emit? | New meanings, AI synthesis, or adaptive intervention. |
| Output surface translator | What may this user-facing surface publish? | Evidence eligibility. |
| Pressure Map | Where should repair attention go? | Automatic task/calendar mutation or student-risk scoring. |
| Exposure Ledger | What behavior-shaping output was shown or suppressed? | Universal behavioral memory. |
| Agent council / parked JARVIS / OpenClaw | What should a human consider? | Silent doctrine, code, or runtime mutation. |

`docs/single_authority_contract.md` adds the stricter cross-surface rule:
one owner per truth class, many producers, many views, one mutation path, and
one claim path. If future AI synthesis is reopened, OpenClaw/GPT is the
preferred reasoning host, but it remains downstream of Admission/Coverage,
EvidencePacket packaging, ClaimCompiler, and output-surface policy. This
identifies preferred future ownership only. It does not authorize runtime AI
synthesis, model integration, prompt execution, user-facing draft generation,
or OpenClaw-to-product wiring. OpenClaw/GPT is not a mutation owner.

The current refactor-risk snapshot is recorded in
`docs/audits/refactor_spaghetti_audit_2026_06_29.md`. That audit is
documentation-only and should be used to order stabilization work, not to
authorize a rewrite.

The S1a safety-rail registries are:

- `docs/registries/mutation_surface_authority_registry.json`
- `docs/registries/runtime_topology_ownership_manifest.json`
- `docs/registries/user_data_ownership_manifest.json`
- `docs/registries/clean_data_provenance_registry.json`
- `docs/registries/identity_scoping_ownership.md`
- `docs/registries/refactor_stabilization_ledger.md`

`scripts/scan_authority_surfaces.py` remains report-only by default, but S1c
has promoted selected allowlisted modes into CI hard gates. CI currently fails
on missing mutation-surface owners and worker-job write drift via
`--fail-on-missing --fail-on-worker-write-drift`. New hard-fail modes require
explicit owner exceptions or allowlists before promotion.

The parked uncertainty-reduction council synthesis is recorded in
`docs/parked/uncertainty_reduction_computation_council_2026_06_29.md`. It may
inform operator diagnostics and post-freeze planning only; it does not authorize
runtime computation, AI synthesis, or user-facing insights.

---

## 4. Current Phase Constraints

For the evidence-packet branch:

- no new public analytics claims,
- no AI synthesis promotion,
- no public cascade intervention,
- no public context-switching causal claim,
- no new adaptive authority,
- no Baseet live integration,
- no DB migration unless a later implementation plan explicitly authorizes it.

`docs/context_switching_footprint_hypothesis.md` and Manifesto H8 authorize
documentation and future read-only derived metrics only. They do not authorize
passive tracking, automatic mutation, user-facing failure prediction, or
psychological explanations for why a user switched tasks.

Baseet and Moodle are provider edges. They may preserve local vocabulary for UI,
but Cortex, clean-data admission, ClaimCompiler, and adaptive logic must consume
provider-blind primitives.

### Standing Freeze Doctrine

These rules apply to every freeze-closure seam, even when a seam-specific plan
does not repeat them:

- Freeze remains active. Do not add runtime AI synthesis,
  OpenClaw-to-product GPT wiring, new user-facing insight types,
  behavior-transition equations, causal pressure-return claims,
  productivity/focus/motivation/avoidance scores, passive tracking, new
  provider adapters, schema migrations, or new public behavioral claims without
  explicit user approval and a new plan.
- Exposure doctrine is global. Queue insertion is not exposure. Delivery is not
  exposure. Browser render creates render truth. Dismissal, acknowledgement,
  action, expiry, suppression, or `lost_unrendered` create terminal
  lifecycle/outcome truth. No seam may treat queued, delivered, or pending
  disappearance as render proof.
- Verification account roles are fixed. `LYRA_COOKIE_ALINASSERSABRY` is the
  legacy env name for the operator account and must remain read-only. It may
  verify `/operator`, topology, privacy, and readiness only. It must never
  create/edit/delete tasks, start timers, acknowledge notifications, dismiss
  user-facing surfaces, or mutate product state.
- `LYRA_COOKIE_HOLMESBERG` is the legacy env name for the mutable chaos/dogfood
  account. It may create tasks, deadlines, timers, brain dumps, pressure-map
  previews, and other synthetic rows only with unique prefixes and
  cleanup/void proof.
- Browser verification must use real account cookies unless a test is
  explicitly labeled fixture-only. Mocked auth, API interception, seeded
  fixtures, and local-current proxying may support proof, but they must be
  labeled and may not be cited as hosted-public user proof.
- Cleanup is part of verification, not cleanup after verification. A mutable
  browser run is incomplete until synthetic rows, timers, Redis/runtime residue,
  and gated cleanup gaps are recorded as cleaned, voided, or explicitly
  harmless.

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
it. It must also record the browser/API/export proof used for the wave, the
CI/CD proof state after push, whether proof was local-current or hosted-public,
and any deployment/build lag that changes what the proof demonstrates. Silent
cuts and silent verification gaps are not allowed.
