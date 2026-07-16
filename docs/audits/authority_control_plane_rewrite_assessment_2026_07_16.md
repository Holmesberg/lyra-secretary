# Evolutionary Authority Control-Plane Assessment

---
authority: audit-evidence
may_authorize_code: false
runtime_owner: none
status: documentation-only repository-grounded architecture assessment
product_name: LyraOS
schema_authority: none
runtime_policy_authority: none
required_final_reviewer: founder
audit_date: 2026-07-16
---

## 1. Revised Question

Can LyraOS replace duplicated governance infrastructure without turning the
current services, tables, routes, frontend framework, or product vocabulary
into a permanent architecture?

The earlier answer proposed federated capability contracts compiled into a
global authority graph. That would reduce duplication, but it contains a
serious failure mode: a sufficiently successful compiler could preserve the
current implementation more effectively than it preserves LyraOS's truth
invariants.

The corrected answer is:

> Govern legal truth transitions, not today's component topology.

The recommended control plane has four deliberately unequal parts:

1. a small **Trace Constitution** containing architecture-independent
   invariants;
2. **revocable authority leases** binding semantic roles to current
   implementations;
3. a disposable, generated **Architecture Twin** that observes the current
   repository;
4. per-change **Proof Packets** that demonstrate what a change preserved.

No generated view becomes runtime truth. No current path, table, service,
query key, or UI module becomes constitutional.

## 2. Why The Compiler Proposal Was Still Too Conservative

The repository currently repeats real information across:

- `docs/AUTHORITY.md` and `docs/single_authority_contract.md`;
- the mutation-surface registry;
- the output-surface registry;
- the shipped-feature preservation registry;
- the executable Python user-data registry and its documentation manifest;
- clean-data contracts;
- frontend query-key contracts;
- static scanners and CI allowlists.

A capability compiler could join these declarations. But the proposed
contract vocabulary included `runtime_paths`, handlers, writes, invalidation
keys, queries, surfaces, data assets, tests, and rollback paths. Once those
fields drive hard gates or generated runtime registries, ordinary architecture
change becomes contract migration.

That creates five forms of ossification:

1. **Component ossification:** `TaskManager` can become mistaken for the
   permanent meaning of task lifecycle authority.
2. **Storage ossification:** current tables can become the vocabulary through
   which all future data ownership must be expressed.
3. **Frontend ossification:** React Query keys can become architectural
   concepts instead of one cache implementation's bindings.
4. **Capability ossification:** today's feature boundaries can become the
   required decomposition for future product work.
5. **Governance inversion:** product code starts serving the compiler's schema
   instead of governance describing and testing product truth.

Reducing duplicate files is not worth creating a second, slower programming
language for LyraOS.

## 3. Architectural Inversion

The durable object is not a capability manifest. It is a legal semantic trace.

```text
user/system intent
-> candidate or decision
-> authorized canonical mutation
-> derived projection
-> delivery attempt
-> authenticated browser render
-> interaction
-> later outcome
```

Not every workflow contains every step. The constitution defines which
transitions are legal and which evidence is required when a step exists.

A trace is a normalized proof object. It need not be a new production event
table or event-sourced architecture. It may be reconstructed in tests from
existing rows, API results, browser acknowledgements, Redis state, and
instrumented writes.

This means a monolith, modular monolith, split service, different database
layout, different frontend cache, or later event-driven implementation can all
conform to the same constitution.

## 4. Layer One: Trace Constitution

The constitution contains only rules expected to survive a major rewrite.

Current candidate invariants include:

- one active write authority per semantic truth role;
- provider/import/parser output remains candidate or structure until a
  canonical authority accepts it;
- browser-rendered exposure requires authenticated acknowledgement from the
  owning user and client instance;
- decision, delivery, render, interaction, mutation, and later outcome are not
  interchangeable;
- terminal lifecycle transitions are explicit, ordered, idempotent, and
  reconstructible;
- operator reads do not mutate user or product state;
- every user-owned durable or runtime data asset has export, deletion,
  retention, and cleanup treatment;
- clean-data admission and claim ceilings cannot be bypassed by presentation,
  provider, analytics, or reasoning layers;
- parked, historical, and retired behavior cannot acquire active write or
  render authority silently;
- rollback preserves canonical evidence or explicitly classifies what cannot
  be restored.

These are predicates over behavior, not declarations about file placement.

### 4.1 Constitutional promotion rule

A rule enters the hard constitution only when at least one condition holds:

- it protects two independent current product paths;
- it prevents recurrence of a demonstrated serious incident;
- it guards an irreversible privacy, identity, deletion, or canonical-truth
  boundary.

Feature-specific preferences, provisional formulas, current module shapes,
and hypothetical future needs remain local.

### 4.2 Counterfactual flexibility test

Every proposed hard rule must answer:

> Could LyraOS replace the current service, database layout, frontend
> framework, or cache library while still satisfying this rule?

If not, the rule is an implementation binding or observation. It cannot be
constitutional.

## 5. Layer Two: Revocable Authority Leases

The constitution names semantic roles rather than permanent owners:

```text
task.lifecycle.write.v1
deadline.canonical.write.v1
stopwatch.execution.write.v1
exposure.browser_render.ack.v1
user_data.export_delete.v1
claim.publish.v1
```

An authority lease records which current implementation holds one role:

```yaml
role: task.lifecycle.write.v1
holder:
  symbol: app.services.task_manager.TaskManager
scope:
  - task.canonical_state
status: active
supersedes: null
transfer_proof:
  - task_lifecycle_characterization
```

The role is stable only while its semantics are stable. The holder is always
replaceable. A service may be renamed, split, merged, or rewritten by changing
the lease and proving a handoff. The constitutional rule is that one active
holder exists, not that `TaskManager` exists.

Leases are trigger-reviewed when their holder or semantic scope changes. They
do not require calendar-based renewal, which would add ceremony without
evidence.

During a handoff:

- one implementation retains active write authority;
- another may run read-only, shadow, or comparison logic;
- dual-write authority is forbidden unless a separately approved migration
  protocol defines reconciliation and rollback;
- transfer completes only after old and new traces satisfy the same
  constitutional scenarios.

## 6. Layer Three: Generated Architecture Twin

The Architecture Twin is generated cartography of the current repository. It
may observe:

- routes and handlers;
- service symbols and import edges;
- ORM models, tables, and commit sites;
- Redis and external-effect adapters;
- output-surface registrations;
- frontend query domains and invalidations;
- export/delete registrations;
- tests, browser paths, and rollback references.

Its output is useful for impact analysis and drift detection, but it has no
authority. It must carry confidence and unknown edges rather than inventing
completeness.

The twin follows three hard rules:

1. product runtime never imports or calls it;
2. generated topology is not committed as canonical architecture;
3. deleting and regenerating it cannot alter product behavior.

Path changes and module splits therefore update the twin automatically or
produce a binding warning. They do not require changing constitutional truth.

## 7. Layer Four: Proof-Carrying Changes

Instead of permanently encoding every current feature in one global schema,
each meaningful change produces a temporary `ChangeProofPacket` containing:

- semantic roles touched;
- observed implementation bindings changed;
- constitutional predicates at risk;
- expected writes and forbidden writes;
- exposure, privacy, export/delete, and cleanup impact;
- focused positive and negative proof;
- rollback path;
- unresolved architecture-twin edges.

The packet is generated from the diff, leases, twin, and selected tests. It is
a CI/review artifact and ledger input, not a runtime object or expanding
forever-registry.

This changes the governance question from:

```text
Did every manifest describe the new architecture?
```

to:

```text
Did this change preserve the legal traces and explicitly transfer any role it
moved?
```

## 8. Optional Enforcement: Test-Time Semantic Effect Sandbox

Static path scans cannot prove what code actually writes. A future bounded
experiment may instrument test runs, not production requests:

```text
enter authority lease scope
-> execute canonical command
-> observe ORM/Redis/external effects
-> map effects to semantic truth roles
-> reject undeclared or foreign writes
-> emit normalized trace
```

Possible implementation points include SQLAlchemy flush hooks, instrumented
Redis adapters, and browser/API correlation fixtures. Production runtime does
not depend on the sandbox.

This could eventually replace brittle `db.commit()` path heuristics with
observed effect proof. It is not authorized here and should not be attempted
unless the first two pilots show that current static scans miss material
authority drift.

## 9. What Remains Local

The following must not be promoted into a universal governance vocabulary
merely because they exist:

- WorkSprint fields or lifecycle;
- DecisionEpisode fragments;
- Pressure Map formulas and horizons;
- survey priors and predictor thresholds;
- frontend cache keys;
- ORM field names;
- route layout;
- provider-specific DTOs;
- recovery option sets;
- current output copy.

They remain local domain design. If multiple independently useful product
paths later require identical semantics, a shared protocol can be proposed
then.

## 10. How This Supports Product Evolution

A later WorkSprint implementation would request a local authority role such as
`work_sprint.intent.write.v1`. Its lease could initially bind to one modular
monolith command. WorkSprint scenarios would prove that it:

- owns accepted intent and closure evidence only;
- references rather than copies task, deadline, stopwatch, and exposure truth;
- routes confirmed canonical changes through existing authorities;
- preserves browser-owned exposure and user-data treatment.

Later, WorkSprint could be split, collapsed into a simpler Next Move flow, or
deleted. Only its local lease and scenarios change. The global constitution
does not learn that WorkSprint is a permanent feature.

That is the desired asymmetry:

```text
product ontology may evolve quickly
constitutional truth changes rarely
implementation bindings are disposable
generated topology is always replaceable
```

## 11. Adversarial Tests For Ossification

Any control-plane rewrite must survive these counterfactuals before adoption:

1. Rename and split `TaskManager`; update only the holder lease. No
   constitutional predicate changes.
2. Replace React Query with another cache; trace rules remain unchanged and
   only observed bindings disappear or change.
3. Merge two route modules; no feature or truth-role identity changes.
4. Replace one table with two normalized tables; export/delete and truth-role
   scenarios still pass after binding updates.
5. Remove the Architecture Twin entirely; runtime and user behavior remain
   unchanged.
6. Implement the same legal trace through a deliberately different test
   architecture; both implementations pass the same scenarios.
7. Delete a failed founder-only feature; no global ontology migration is
   required.

Failure of any test means governance has frozen implementation shape.

## 12. What To Retire And What To Preserve

Preserve initially:

- executable output-surface policy;
- executable user-data export/delete registry;
- current clean-data and claim enforcement;
- current browser-render acknowledgement;
- existing registries as parity evidence;
- existing CI hard gates.

Retire only after demonstrated replacement value:

- duplicated human-readable owner tables;
- repeated path lists used only for documentation;
- scanners whose only purpose is reconstructible by the twin;
- preservation entries that have become generated change evidence rather than
  enduring feature contracts.

Do not plan a generated runtime-registry cutover. Runtime policy should remain
near executable behavior unless a separate future decision proves that moving
it improves the product and failure model.

## 13. Rewrite Decision

Do not build the previously proposed Capability Contract Compiler.

The stronger candidate is a shadow spike that proves three things with two
existing domains:

1. stable trace predicates can be expressed without current paths or tables;
2. current holders can be represented as revocable leases;
3. a generated twin and change packet can answer impact questions without
   becoming runtime input.

Pilot domains:

- task lifecycle, to exercise canonical writes, invalidation, export/delete,
  and rollback;
- browser-owned exposure, to exercise decision, delivery, authenticated
  render, interaction, terminal outcomes, and cross-user rejection.

If this does not delete more repeated governance than it adds, or if product
work begins conforming to the tool rather than the invariants, delete the
spike.

## 14. Hard Stop

This assessment authorizes no trace engine, authority lease, Architecture
Twin, test instrumentation, generated artifact, registry replacement, CI
change, runtime policy, route, migration, feature, deployment, or authority
transfer.
