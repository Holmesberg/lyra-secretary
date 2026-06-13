---
authority: parked
may_authorize_code: false
runtime_owner: none
supersedes:
superseded_by:
---

# Parked Governance Specs

Status: parked pressure memory. This document preserves the Wave 7-11
governance design while explicitly denying implementation authority.

These specs must not be treated as permission to add runtime systems,
schema fields, background jobs, public claims, agent powers, or enforcement
middleware. They can be promoted only by a later active implementation plan
that names the current boundary failure, target files, tests, and rollback
criteria.

## Governing Principle

```text
A component may compute richly.
It may only publish, mutate, infer, prescribe, or govern through an explicit
authority boundary.
```

Future-proof with seams, not systems. Preserve the insight now; instantiate
machinery only when current product pressure proves it is needed.

## Already Implemented Before This Parking

- Explicit public insight translation replaced underscore filtering as the
  public publication boundary.
- EvidencePacket was slimmed to minimal claim evidence plus active gates.
- Exposure snapshots were redacted and separated from internal audit envelopes.
- Provider-facing pressure-map fields were neutralized away from Moodle-specific
  names.
- Pressure Map was classified as a diagnostic planning surface with suggestion
  authority and explicit user-confirmation mutation limits.

## Parked Wave 7: Agent / JARVIS / OpenClaw Authority

Pressure forecast:
- Agent tools may gain operational capability faster than their authority is
  modeled.
- Client-supplied `name,args` confirmation flows can blur advisory output and
  mutation authority.
- OpenClaw/JARVIS review output can start behaving like doctrine if not kept
  operator-scoped.

Parked design:

```text
ToolSpec(
  name,
  authority = read | advisory | confirm_required | operator_mutation,
  allowed_callers,
  exposure_class,
  stores_behavioral_evidence = false
)
```

Rules to promote later:
- Mutations execute only from server-stored pending invocation IDs.
- Client requests cannot resubmit arbitrary tool `name,args` as confirmation.
- Operator-only remains operator-only.
- JARVIS/OpenClaw output is operator exposure, not behavioral truth.
- Agent reviews cannot mutate docs, code, or doctrine without an explicit
  implementation command.

Promotion trigger:
- A real mutation-capable agent flow is exposed to a non-operator user, or a
  tool confirmation path can be shown to accept client-forged arguments.

Parked files:
- `backend/app/services/jarvis_tools.py`
- `backend/app/api/v1/endpoints/jarvis.py`

## Parked Wave 8: Repair Jobs And Mutation Quarantine

Pressure forecast:
- Product repair jobs may mutate operational state correctly while accidentally
  polluting clean behavioral evidence.
- Repaired or inferred states can become hidden inputs to H1, bias factors,
  Cortex baselines, or ClaimCompiler evidence.

Parked rule:

```text
Product repair may mutate operational state.
Repaired or inferred state must not enter clean analytics evidence unless an
explicit clean-data rule admits it.
```

Rows or transitions to quarantine later:
- stale session recovery;
- orphan task recovery;
- overdue sweeps;
- inferred completion or skip repair;
- provider submission confirmation.

Promotion trigger:
- A repair-derived row is used by analytics, baseline, ClaimCompiler, pressure
  inference, or public insight generation without an explicit clean-data label.

Parked files:
- `backend/app/workers/jobs/stale_session_recovery.py`
- repair/reconciliation jobs that mutate task or session state.

## Parked Wave 9: Test Suite As Membrane System

Pressure forecast:
- Tests can preserve speculative architecture by asserting decorative fields,
  exact copy, static generator lists, or historical doctrine phrasing.

Strict categories to promote later:
- `runtime_safety_invariant`
- `privacy_scoping_invariant`
- `publication_boundary`
- `security_boundary`
- `provider_adapter_boundary`
- `output_surface_boundary`
- `copy_safety_semantics`

Loose or migratable assertions:
- exact prose;
- decorative internal fields;
- static generator snapshots;
- historical doc phrasing;
- speculative architecture.

Keep strict:
- auth and user scope;
- output surface registration;
- exposure emission and suppression;
- provider-blind core behavior;
- clean-data boundaries;
- redaction;
- no direct exposure-ledger bypass.

Promotion trigger:
- A simplification or boundary fix is blocked mainly by tests asserting
  implementation decoration instead of runtime behavior or safety invariants.

Parked files:
- `backend/tests/test_claim_compiler.py`
- `backend/tests/test_insights.py`
- `backend/tests/test_academic_pressure_map.py`
- `backend/tests/test_output_surfaces.py`
- `backend/tests/test_scalability_research_docs_contract.py`

## Parked Wave 10: Public / AI-Readable Copy Alignment

Pressure forecast:
- Public docs, landing copy, `llms.txt`, and AI-readable markdown can become
  authority-bearing even when runtime systems are gated.

Required stance when promoted:
- Lyra is an execution intelligence / behavioral instrumentation system.
- AI synthesis is downstream and gated.
- Adaptive scheduling is future-gated or bounded.
- No copy implies autonomous mutation, diagnosis, identity truth, or
  provider-fed AI authority.

Promotion trigger:
- Public/AI-readable copy starts implying current authority for autonomous
  mutation, diagnosis, identity classification, cascade intervention, or
  provider-fed AI inference.

Parked files:
- `frontend/app/layout.tsx`
- `frontend/public/lyraos.md`
- `frontend/public/llms.txt`
- landing and public orientation pages.

## Parked Wave 11: Global Enforcement Checks

Pressure forecast:
- Boundary rules may drift unless executable checks eventually exist.
- The risk is real, but implementing global enforcement too early can make the
  governance substrate heavier than the product.

Parked checks:

1. Every user-facing interpretive endpoint should eventually:
   - use a registered output surface;
   - emit render or suppression exposure;
   - expose `truth_class`;
   - declare clean-profile semantics;
   - use a public translator or response model.

2. Every provider-sensitive code path should eventually:
   - avoid provider-name branches outside adapter/UI allowlists;
   - hash or redact external IDs;
   - exclude raw URLs/tokens from snapshots/logs.

3. Every public UI surface should eventually:
   - render public DTOs;
   - avoid raw internal fields;
   - avoid forbidden copy unless surface authority explicitly permits it.

4. Every implementation-authorizing doc should eventually:
   - declare authority status;
   - be supersession-aware;
   - not conflict with the current transition state.

Promotion trigger:
- A real boundary regression reaches CI, runtime verification, or user-visible
  output because the invariant existed only as prose.

## Parked / Deleted Log

Parked for later:
- JARVIS/OpenClaw typed tool authority.
- Repair-job quarantine taxonomy.
- Global test taxonomy migration.
- Public/AI-readable copy authority sweep.
- Global enforcement middleware or static checks.

Not implemented now:
- New runtime governance tables.
- New DB migrations.
- New agent mutation authority.
- New repair quarantine columns.
- New public claims.
- AI synthesis promotion.
- Cascade intervention promotion.
- Baseet live integration.

Reason:
- Waves 7-11 are valuable future pressure forecasts, but they do not currently
  justify runtime machinery. They should remain explicit seams and documented
  triggers until real user/provider/agent pressure demands promotion.
