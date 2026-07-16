# Parked Capability Contract Control-Plane Migration Plan

---
authority: parked-infrastructure-plan
may_authorize_code: false
runtime_owner: none
status: candidate governance rewrite pending founder activation
product_name: LyraOS
schema_authority: none
runtime_policy_authority: none
deployment_authority: none
required_final_reviewer: founder
plan_date: 2026-07-16
---

## 1. Goal

Replace repeated hand-maintained governance declarations with federated
capability contracts compiled into mechanically consistent control-plane views.

Preserve:

- canonical mutation services;
- exposure and browser-render truth;
- executable export/delete behavior;
- clean-data formulas and ClaimCompiler;
- current feature behavior and public API;
- current CI gates until replacement parity is proven.

## 2. Non-Goals

- no runtime policy engine or command bus;
- no generic event sourcing;
- no universal ontology or semantic-field registry;
- no automatic code, migration, or deletion generation;
- no new user-facing governance surface;
- no WorkSprint or other product feature implementation;
- no weakening of existing hard gates during migration.

## 3. Target Repository Shape

```text
contracts/
  schema/capability-contract.schema.json
  capabilities/*.json
  generated/
    authority-graph.json
    mutation-scan.json
    output-surfaces.json
    preservation-report.json
    invalidation-obligations.json
    user-data-coverage.json
    authority-map.md
tools/capability_contracts/
  load.py
  validate.py
  compile.py
  compare.py
```

Generated files are deterministic and carry a source-contract hash. Runtime
code may consume a generated projection only after exact parity and explicit
authority transfer.

## 4. Contract Design Rules

- One file per stable capability boundary.
- One owner per truth class; references do not imply ownership.
- Commands name handlers, writes, invalidation obligations, and rollback.
- Output surfaces retain their existing policy vocabulary.
- User-data declarations name model/table and policy references, while Python
  retains export queries, redaction, deletion order, and retention behavior.
- Proof references must resolve to existing tests/scripts or be explicitly
  marked missing.
- Parked and historical capabilities cannot claim runtime paths, writes, or
  active output surfaces.
- Local Data Delta fields remain in product plans; they do not enter the
  capability schema unless two implemented capabilities need the same boundary
  concept.

## 5. Migration Sequence

### Phase 0: Freeze The Parity Oracle

Capture exact current outputs from:

- mutation-surface registry and scanner;
- output-surface registry and tests;
- preservation registry and scanner;
- user-data runtime manifest and ownership document;
- clean-data registry;
- query-key invalidation contract;
- active authority documentation;
- current CI and S1c commands.

Add fixtures for counts, IDs, schema versions, hard failures, allowlists, and
known warnings. Existing registries remain authoritative.

### Phase 1: Compiler Skeleton In Shadow

- Define the narrow JSON Schema.
- Parse capability fragments and produce a normalized graph.
- Validate duplicate IDs, missing owners, invalid status combinations, broken
  paths/symbol references, unknown surfaces, and cycles in ownership.
- Generate reports only into ignored temporary output.
- Add negative self-tests proving the compiler rejects conflicting owners,
  active paths on parked capabilities, missing privacy treatment, and unknown
  proof references.

No generated artifact is consumed by runtime or CI hard gates yet.

### Phase 2: Two Existing Capability Pilots

Encode:

1. `task.lifecycle`, because it exercises writes, privacy, invalidation,
   rollback, and preservation;
2. `academic.pressure_map`, because it exercises projection, clean evidence,
   output policy, exposure, user action, and browser proof.

The compiler compares each pilot with every existing registry and reports
field-level disagreements. Existing sources win every disagreement during
shadow mode.

### Phase 3: Read-Only Generated Views

Generate and review:

- authority graph;
- owner/blast-radius documentation;
- preservation projection;
- mutation scanner input;
- user-data coverage report;
- invalidation obligation report.

Acceptance requires semantic parity, stable diffs, useful errors, and a net
reduction in repeated declarations for the two pilots.

### Phase 4: First Authority Transfer

Transfer the least risky projection first: the human-readable preservation and
authority reports. Keep the old JSON as a generated compatibility artifact so
existing scanners continue to run.

Authority transfer requires:

- old and new outputs equivalent under frozen fixtures;
- old scanner and compiler both green on the same exact SHA;
- a negative test where each catches the same missing-owner defect;
- rollback to the handwritten artifact demonstrated;
- explicit founder approval.

### Phase 5: Mutation And Invalidation Gates

- Make the authority scanner consume generated mutation declarations.
- Make frontend tests consume generated invalidation obligations while keeping
  actual invalidation functions hand-written.
- Require every declared command to have one canonical owner and a tested
  invalidation implementation.
- Do not generate frontend mutation behavior.

### Phase 6: Output-Surface Projection

- Encode current output policy fields without changing their meaning.
- Generate byte-for-byte stable output-surface JSON.
- Run the entire output-surface, exposure, operator, and browser-owned-render
  suites against both artifacts.
- Cut runtime reads over only after explicit approval and rollback rehearsal.

### Phase 7: User-Data Coverage

- Compare declared user data assets to SQLAlchemy model metadata and the Python
  registry.
- Hard-fail new user-owned models missing export/delete treatment.
- Keep custom export queries, redaction, delete order, retention, and Redis
  purge in executable Python.
- Generate the documentation manifest from runtime coverage rather than
  copying section names manually.

### Phase 8: Consolidate Documentation And Remove Duplicates

- Reduce `docs/AUTHORITY.md` to stable constitutional rules and generated
  control-plane links.
- Merge unique doctrine from `single_authority_contract.md` into the
  constitution, then archive the duplicate document.
- Replace handwritten registry tables with generated reports.
- Delete compatibility artifacts only after all consumers migrate and rollback
  is no longer needed.

## 6. Verification Cadence

Per compiler seam:

1. schema/unit tests;
2. focused positive and negative contract fixtures;
3. deterministic-output/hash check;
4. old-versus-new parity report;
5. current scanner and affected runtime tests;
6. explicit rollback check;
7. commit.

At macro-checkpoints:

- full S1c;
- backend and frontend contract suites;
- exact-head CI;
- no browser run unless a runtime-consumed artifact changes;
- full mounted browser and operator read-only proof before any runtime registry
  cutover.

## 7. Hard Acceptance Criteria

The rewrite continues only when it demonstrates all of the following:

- no existing hard invariant is weakened;
- one capability declaration replaces at least two repeated manual
  declarations;
- generated diffs are deterministic and reviewable;
- custom domain semantics remain in executable owners;
- local validation is fast enough for ordinary seams;
- errors identify one capability and one actionable edge;
- adding a user-owned table, mutation command, or output surface cannot pass CI
  without its required cross-boundary declarations;
- deleting a capability produces a complete blast-radius report;
- governance code and declarations shrink after compatibility files are
  removed.

## 8. Stop Conditions

Stop and retain the current registries if:

- the compiler needs arbitrary per-capability escape blobs;
- generated behavior becomes harder to review than handwritten behavior;
- custom export/delete or output semantics are lost;
- the contract schema grows faster than implemented capability needs;
- parity requires weakening a current gate;
- runtime code depends on the compiler service being available;
- the first two pilots do not remove meaningful duplication;
- implementation work delays founder product-loop usefulness without reducing
  a named present risk.

## 9. Recommended First Decision

Do not approve a complete rewrite yet. Approve only a documentation-to-shadow
compiler spike with two existing capabilities and no runtime consumer.

The spike succeeds when it can answer, from one graph:

```text
who owns the write?
what must refresh?
what may render?
what data must export/delete?
what proof and rollback are required?
```

If it cannot answer those questions more simply than the current stack, delete
the spike.

## 10. Hard Stop

This parked plan authorizes no code, compiler, generated file, registry
cutover, CI change, runtime behavior, schema, route, deployment, or authority
transfer.
