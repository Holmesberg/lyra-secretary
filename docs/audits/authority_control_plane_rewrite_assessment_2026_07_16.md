# Authority Control-Plane Rewrite Assessment

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

## 1. Question

Would rewriting LyraOS authority and governance infrastructure remove enough
duplication, drift, and implementation friction to justify replacing the
current registry stack?

The answer is **yes, conditionally**.

The valuable rewrite is not a runtime policy engine, universal ontology, or
larger central registry. It is a build-time **Capability Contract Compiler**
that turns bounded capability declarations into several mechanically checked
views of the same architecture.

Rewrite the control plane. Preserve the product authorities.

## 2. Current Repository Reality

LyraOS currently distributes governance across several partially overlapping
sources:

| Current source | What it does well | Structural problem |
| --- | --- | --- |
| `docs/AUTHORITY.md` | Human-readable constitution and freeze doctrine | Mixes stable doctrine, current phase, historical context, and registry pointers |
| `docs/single_authority_contract.md` | Strong one-owner invariant | Repeats doctrine from the authority map and cannot mechanically prove ownership |
| mutation-surface registry | Names 18 mutation-capable surfaces, owners, paths, and writes | Hand-maintained and separate from route, cache, privacy, and output declarations |
| output-surface registry | Executable policy for 27 behavior-shaping surfaces | Surface policy is detached from the feature, mutation, preservation, and privacy declarations |
| preservation registry | Tracks 45 shipped, partial, historical, dead, and parked capabilities | Repeats owners, runtime paths, writes, output IDs, contracts, proof, and rollback |
| Python user-data registry | Executable export/delete authority for user-owned rows | Correctly executable, but its documentation manifest repeats a manually copied section list |
| clean-data registry and contracts | Protect provenance and claim admission | Vocabulary and owners are not linked mechanically to the capabilities that consume them |
| frontend query-key contract | Centralizes invalidation recipes | Mutation impact is maintained separately from backend mutation ownership |
| CI scanners | Catch missing owners and known forbidden patterns | Several scanners parse paths and text independently rather than one typed architecture graph |

This infrastructure is not bad. It reflects real failures that were fixed one
boundary at a time. Its weakness is that every new capability must be described
several times in different shapes.

## 3. What The Current Control Plane Cannot Answer Directly

No single current source can answer:

- Which command owns this write, and which frontend projections must refresh?
- Which behavior-shaping surfaces can result from that command?
- Which output policy, clean profile, claim ceiling, and browser acknowledgement
  apply to the surface?
- Which user-owned rows, Redis keys, export sections, and delete paths does the
  capability introduce?
- Which characterization, browser, cleanup, and rollback proofs preserve it?
- Which parked concept would accidentally compete with its authority?
- If the capability is removed, which routes, surfaces, queries, registries,
  docs, and tests must move together?

Engineers currently reconstruct these answers by joining registries mentally.
That is exactly where duplicate structures and stale governance appear.

## 4. Alternatives Considered

### A. Keep every registry and add more cross-scanners

Lowest immediate risk, but it compounds maintenance. Every scanner must learn
the same identifiers, paths, and exceptions. Reject as the long-term design.

### B. Replace everything with one central mega-manifest

This makes joins easy but creates a governance god object. It will accumulate
feature fields, ontology fields, deployment details, metrics, and arbitrary
exceptions. Reject.

### C. Introduce a runtime command bus or policy engine

This could enforce mutation ownership dynamically, but it would put governance
on the product request path, force broad mutation rewrites, and create a new
operational failure domain. Reject for the current product stage.

### D. Federated capability contracts plus a compiler

Recommended. Each bounded capability declares only its cross-boundary contract.
A build-time compiler validates references and emits the global views needed by
runtime adapters, CI, documentation, and reviewers.

## 5. Recommended Architecture

```text
capability contract fragments
-> Capability Contract Compiler
-> validated authority graph
-> generated projections
   - mutation ownership scan input
   - output-surface registry projection
   - preservation report
   - user-data coverage report
   - query invalidation obligations
   - proof and rollback index
   - human-readable authority map
```

The compiler is build-time infrastructure. It never decides a user request,
mutates product state, emits a claim, creates exposure truth, or selects an
intervention.

### 5.1 Contract unit

One contract describes one stable capability boundary, not one component,
route, table, or future idea. Examples:

- `task.lifecycle`;
- `stopwatch.execution`;
- `brain_dump.commit`;
- `academic.pressure_map`;
- `output.exposure_ledger`;
- a later approved `work_sprint`.

### 5.2 Minimal contract vocabulary

```yaml
id:
status: shipped | partial | parked | historical | retired
owner:
runtime_paths:
truth:
  owns:
  references:
commands:
  - id:
    handler:
    writes:
    invalidates:
queries:
surfaces:
data_assets:
access:
clean_profiles:
claim_ceiling:
proof:
rollback:
```

This vocabulary describes boundary obligations. It does not enumerate every
database field, UI state, formula, or future ontology concept.

### 5.3 Authority graph

The compiler normalizes contracts into typed nodes and edges:

```text
Capability --owns--> TruthClass
Command --writes--> DataAsset
Command --invalidates--> QueryDomain
Capability --renders--> OutputSurface
OutputSurface --requires--> CleanProfile
DataAsset --uses--> ExportDeletePolicy
Proof --verifies--> ContractEdge
Capability --rolled_back_by--> RollbackPath
```

This is an architecture graph, not a behavioral knowledge graph and not a
DecisionEpisode schema.

## 6. What Should Be Generated

### Generate first

- human-readable owner and blast-radius reports;
- preservation-registry projection;
- mutation scanner configuration;
- cross-registry drift findings;
- missing proof, rollback, privacy, and output-policy findings.

These outputs do not affect runtime behavior and are the safest parity targets.

### Generate after parity

- the runtime output-surface JSON, byte-for-byte equivalent to the current
  registry before cutover;
- a machine-readable invalidation obligation matrix consumed by frontend
  contract tests.

### Validate, but do not generate

- Python export/delete queries and deletion order;
- custom redaction logic;
- SQLAlchemy relationships and migration order;
- canonical service mutation logic;
- browser render acknowledgement;
- clean-data formulas;
- rollback commands.

These remain executable code because generation would hide domain-specific
semantics. The compiler proves coverage and references; it does not synthesize
behavior.

## 7. Optional Second-Order Primitive

A later API standard may return a non-persisted `MutationImpact` envelope:

```json
{
  "command_id": "task.reschedule",
  "changed_truth": ["task.plan"],
  "invalidate": ["tasks", "calendar", "pressure_map"],
  "entity_refs": ["task:..."],
  "mutation_ref": "..."
}
```

This could remove frontend cache guesswork and link exposure outcomes to
canonical mutations. It is deliberately not part of the first compiler seam.
It earns implementation only if static invalidation obligations remain a real
source of stale-state defects after the compiler exists.

It must remain a command result, not a universal persisted event log.

## 8. How This Helps The Founder Core Loop

For a future WorkSprint contract, one declaration could establish:

- WorkSprint owns accepted intent and closure boundary only;
- Task and Stopwatch remain referenced authorities;
- activation writes Sprint/member/session linkage;
- Pressure Map and Today queries must invalidate;
- Start, closure, and recovery surfaces require browser-owned exposure truth;
- Sprint rows enter export/delete and cleanup proof;
- operator access remains read-only;
- characterization, browser, supersession, and rollback proof are mandatory.

This catches duplication before migration without designing a universal field
registry or episode platform.

## 9. Main Risks

### Governance schema inflation

Mitigation: contracts describe capability boundaries only. New top-level keys
require a compiler schema change and a demonstrated cross-capability need.

### Generated-code opacity

Mitigation: generate data and reports, not domain mutation logic. Generated
files are deterministic, diffable, and carry source references.

### Big-bang cutover

Mitigation: shadow compilation and parity checks precede every authority
transfer. One projection becomes authoritative at a time.

### Compiler becomes a release bottleneck

Mitigation: keep local validation fast, error messages capability-scoped, and
warning-only rules separate from mechanical hard failures.

### Governance becomes the product

Mitigation: no runtime dependency, no user-facing governance UI, and a strict
budget: the compiler must remove more repeated declarations and scans than it
adds.

## 10. Rewrite Decision

The current registries should not be discarded immediately. Their accumulated
invariants are the specification and parity oracle for the rewrite.

The recommended decision is:

> Build a shadow Capability Contract Compiler, prove it can reconstruct the
> current control plane, then replace hand-maintained projections one at a time.
> Keep canonical product services, exposure lifecycle, user-data execution,
> and clean-data formulas outside the compiler.

This is a substantial governance rewrite with bounded product risk. It solves
more than the WorkSprint problem while avoiding a universal runtime framework.

## 11. Hard Stop

This assessment authorizes no compiler, generated artifact, registry cutover,
runtime policy, route, migration, feature, deployment, or authority transfer.
