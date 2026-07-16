# Parked Evolutionary Authority Control-Plane Pilot

---
authority: parked-infrastructure-plan
may_authorize_code: false
runtime_owner: none
status: candidate governance pilot pending founder activation
product_name: LyraOS
schema_authority: none
runtime_policy_authority: none
deployment_authority: none
required_final_reviewer: founder
plan_date: 2026-07-16
---

## 1. Goal

Test whether LyraOS can replace duplicated architecture declarations with:

- a small, architecture-independent Trace Constitution;
- revocable bindings from semantic authority roles to current code;
- a generated, non-authoritative Architecture Twin;
- proof packets scoped to each change.

The pilot must increase architectural freedom, not merely centralize current
topology.

## 2. Non-Goals

- no capability compiler that generates runtime policy;
- no central feature manifest;
- no universal ontology or semantic-field registry;
- no runtime command bus, policy engine, or event-sourcing conversion;
- no generated output-surface registry cutover;
- no product dependency on governance tooling;
- no WorkSprint, DecisionEpisode, or other product feature;
- no schema migration or production instrumentation;
- no weakening of current authority, exposure, privacy, or CI gates.

## 3. Candidate Repository Shape

The exact file format remains a pilot decision. The conceptual separation is
mandatory:

```text
governance/
  constitution/
    invariants/
    scenarios/
  bindings/
    authority-leases/
  observatory/
    extractors/
    generated/          # ignored and disposable
  change-proof/
    schema/
    generated/          # CI artifact, not runtime input
```

Constitution files may not name current paths, symbols, tables, query keys, or
frameworks. Bindings may name them because bindings are explicitly
replaceable. Generated output is never authoritative.

## 4. Design Rules

### 4.1 Constitution rules

- Express predicates over semantic transitions and evidence.
- Promote only cross-domain, incident-proven, or irreversible-boundary rules.
- Keep provisional product formulas and feature lifecycle local.
- Require positive, negative, idempotency, ordering, and cross-user scenarios
  where applicable.
- Permit `UNKNOWN` rather than fabricating an observation.

### 4.2 Authority-lease rules

- One active holder per semantic write role.
- A role names semantic scope, not a class or route.
- A holder binding names current code and can be replaced.
- Splits, merges, and renames update bindings, not constitutional predicates.
- Shadow reads and comparisons are allowed; dual-write authority is not.
- A transfer records old holder, new holder, proof, rollback, and effective
  version.

### 4.3 Architecture-twin rules

- Prefer extraction from code, runtime registration, ORM metadata, and tests
  over copied path lists.
- Carry source references, confidence, and unknown edges.
- Report structural drift; do not decide product behavior.
- Never become a production import, build prerequisite, or runtime service.
- Regeneration or deletion has zero product effect.

### 4.4 Change-proof rules

- Generate impact from a diff rather than expanding a permanent feature
  manifest.
- Require a human-authored explanation only for unresolved semantic effects,
  authority transfer, or rollback.
- Archive compact evidence with the seam ledger; discard bulky generated
  topology.
- Adjacent observations remain issues, not implicit contract expansion.

## 5. Pilot Sequence

### Phase 0: Freeze Existing Evidence, Not Existing Architecture

Record current outputs from:

- mutation-surface registry and scanner;
- output-surface registry and lifecycle tests;
- preservation registry and scanner;
- Python user-data registry and ownership manifest;
- clean-data contracts;
- frontend invalidation tests;
- current CI and S1c gates.

These are parity evidence. They are not declared the target architecture.

### Phase 1: Extract Eight Or Fewer Stable Trace Predicates

Start only with rules already demonstrated by shipped behavior or incidents:

1. one active canonical writer per truth role;
2. candidate evidence cannot silently become canonical truth;
3. browser render requires authenticated owner acknowledgement;
4. decision, delivery, render, interaction, mutation, and outcome are distinct;
5. lifecycle terminalization is explicit and idempotent;
6. operator reads produce no product mutation;
7. user-owned assets have export/delete/retention treatment;
8. clean-data and claim authority cannot be bypassed.

For each predicate, add framework-neutral positive and negative fixtures. Do
not encode current owner paths in the predicate.

### Phase 2: Bind Two Current Domains

Pilot:

1. `task.lifecycle.write.v1`;
2. `exposure.browser_render.ack.v1`.

Each lease points to current holders and references existing characterization
proof. The pilot must distinguish semantic role changes from holder-only
refactors.

### Phase 3: Build The Disposable Architecture Twin

Read current code and registries to report:

- likely commit/write sites;
- routes reaching current holders;
- relevant ORM and Redis effects;
- registered output surfaces;
- frontend invalidation domains;
- export/delete coverage;
- current tests and browser paths.

The twin must label uncertain edges. It must not require developers to copy
all findings into a new canonical manifest.

### Phase 4: Generate One ChangeProofPacket

Use a historical or synthetic refactor diff for one pilot domain. Generate:

- semantic roles affected;
- binding changes;
- constitutional predicates at risk;
- focused proofs required;
- privacy, exposure, cleanup, and rollback impact;
- unresolved observations.

Compare its usefulness and maintenance cost with the current seam preflight,
registries, and scanners.

### Phase 5: Run Counterarchitecture Fixtures

Without changing production code, test the governance model against synthetic
alternate topologies:

- rename and split the task holder;
- replace a query-key binding with a different cache adapter;
- normalize one logical data asset across two tables;
- merge route modules;
- remove a founder-only feature.

Only holder bindings and observations may change. If constitutional predicates
or product identities must change solely because topology changed, the pilot
fails.

### Phase 6: Decide Whether Any Existing Artifact Can Retire

The first eligible removals are documentation-only duplicate owner/path
tables. Runtime registries and executable user-data policy are not cutover
targets in this pilot.

Retire one duplicated artifact only if:

- its unique semantics have a clear surviving owner;
- the new view is cheaper to maintain;
- deleting it weakens no current gate;
- rollback is demonstrated;
- founder approval is explicit.

Otherwise retain the current system and delete the pilot.

## 6. Optional Follow-On: Test-Time Effect Sandbox

This is a separate future decision, not part of the first pilot.

If static scans still miss material write drift, a test-only harness may:

- enter a declared semantic authority scope;
- observe SQLAlchemy, Redis, and external adapter effects;
- compare actual effects with the active lease;
- emit normalized legal or illegal traces.

The sandbox must remain absent from the production request path. It must prove
more than existing targeted tests before adoption.

## 7. Verification Cadence

Per pilot seam:

1. schema/parser tests if a machine format is used;
2. focused positive and negative trace scenarios;
3. deterministic twin-output check;
4. current scanner and affected tests;
5. counterarchitecture fixture;
6. deletion/rollback check;
7. commit.

At the pilot checkpoint:

- full S1c;
- exact-head CI;
- no browser run unless runtime-consumed behavior changes;
- no public deploy, restart, migration, or authority transfer.

## 8. Flexibility Acceptance Criteria

The pilot continues only if all are true:

- stable predicates contain no current paths, tables, query keys, or framework
  names;
- a holder can be renamed or split by changing bindings only;
- two different implementation topologies can satisfy the same scenarios;
- deleting generated output has no runtime effect;
- no generated artifact becomes runtime input;
- current runtime registries remain executable owners;
- the twin exposes uncertainty instead of claiming false completeness;
- one change packet replaces material manual reconstruction;
- at least one duplicated declaration becomes deletable;
- total governance maintenance decreases after compatibility evidence is
  removed.

## 9. Stop Conditions

Stop and delete the pilot if:

- the constitution begins naming product features or implementation holders;
- every feature needs a new top-level governance concept;
- generated topology becomes required to build or run the product;
- developers must update both code and copied twin declarations;
- current paths or tables become hard architectural gates;
- the pilot needs arbitrary escape blobs;
- trace fixtures merely restate current function calls;
- a refactor requires constitutional edits despite unchanged behavior;
- no current governance artifact can be retired;
- the pilot delays founder-loop usefulness without removing a named present
  risk.

## 10. Recommended First Decision

Do not approve a governance rewrite or compiler build.

If this direction is activated later, approve one bounded documentation and
test-harness spike:

```text
two semantic roles
+ no more than eight stable predicates
+ one disposable architecture twin report
+ one change proof packet
+ two counterarchitecture fixtures
+ zero runtime consumers
```

The spike either proves that governance can survive architecture replacement,
or it is deleted. It does not earn a second phase merely by functioning.

## 11. Hard Stop

This parked plan authorizes no code, trace engine, authority lease,
Architecture Twin, test sandbox, generated artifact, registry replacement, CI
change, runtime behavior, schema, route, deployment, or authority transfer.
