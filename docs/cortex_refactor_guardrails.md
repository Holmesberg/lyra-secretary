# Cortex Refactor Guardrails

**Status:** Pre-refactor safety contract.

**Purpose:** Define the failure classes, hard boundaries, and sequencing gates
that must be satisfied before LyraOS performs broad structural refactors around
Cortex, inference, services, or analytics.

This document does not authorize new inference, new schema, or new user-facing
claims. It exists to prevent semantic correctness from being replaced by folder
tidiness.

---

## 1. Core Refactor Risk

The highest-risk refactor failure is over-modularization before semantic
stabilization.

That failure mode looks clean from the outside: folders become neat, files move
into named layers, and imports appear organized. But if the invariants are not
behavior-tested first, the same row can still mean different things depending on
which path evaluates it.

Refactor order therefore must be:

1. lock characterization tests
2. centralize clean-data profiles
3. enforce unknown propagation
4. enforce dependency direction
5. only then move module families

---

## 2. Real Failure Classes

### 2.1 Temporal Inconsistency Drift

Mechanism:

- Old events were collected under earlier semantics.
- New Cortex logic interprets them under newer semantics.
- Different modules evaluate the same historical row differently.

Result:

- Same data can produce incompatible conclusions depending on code path.

Safeguards:

- Every Cortex-derived projection that leaves the current process must include
  `cortex_schema_version_at_evaluation`.
- Version means evaluation version, not storage version.
- Aggregates across evaluation versions must declare the version boundary.
- Golden-output tests must pin representative rows across contract versions
  before interpretation rules change.

Initial implementation target:

- `cortex_schema_version_at_evaluation = "cortex_contract_v0"` for current
  Cortex diagnostics and research exports.

### 2.2 Silent Fallback Behavior Explosion

Mechanism:

- `unknown` is converted into `neutral`, `bounded`, `0`, `average`,
  `no exposure`, or another convenient default.
- Aggregates become smoother while losing identifiability.

Result:

- Missingness becomes fake evidence.
- Unknown provenance becomes false negative evidence.
- Latent ambiguity disappears from dashboards and models.

Safeguards:

- Unknown must propagate unless a clean-data profile explicitly excludes it.
- Every aggregation must report or define the denominator treatment for unknowns.
- Topology classifiers must default to `unknown`, not `bounded`.
- Exposure state must default to `observed_exposure_unknown`, not
  `observed_no_exposure`.

Initial implementation target:

- Unknown propagation tests for Cortex projections, topology classification, and
  exposure classification before structural refactor continues.

### 2.3 Hidden Bidirectional Dependency Loops

Mechanism:

- Services call Cortex.
- Cortex indirectly calls inference or services through utilities.
- Inference indirectly depends on services or API state.

Result:

- The system may still run, but causal interpretation becomes unclear.
- Operational state can leak into measurement logic.
- Refactors become impossible to reason about from imports alone.

Safeguards:

- Enforce a dependency DAG, not only direct import checks.
- Forbidden return paths must fail CI:
  - `cortex -> services`
  - `cortex -> inference`
  - `inference -> services`
  - `inference -> api`
  - `services -> api`
- Refactor one module family per commit so dependency breaks are reviewable.

Initial implementation target:

- Static dependency DAG test for backend packages before broad module moves.

### 2.4 Calibration Contamination Through Feedback Loops

Mechanism:

- User sees a prediction, nudge, reflection, or insight.
- User behavior changes in response.
- The system logs the new behavior as if it were naturalistic observation.

Result:

- The model learns from behavior it helped create.
- Self-fulfilling predictions can look like predictive accuracy.
- User adaptation becomes indistinguishable from model improvement.

Safeguards:

- Exposure must be classified at inference time, not only at event capture.
- Minimum inference-time classes:
  - `observed_no_exposure`
  - `observed_exposed_prediction`
  - `observed_intervention`
  - `observed_exposure_unknown`
- Adaptive inference must exclude or stratify exposed and unknown-exposure rows
  until Phase 1 exposure ledger exists.

Initial implementation target:

- No adaptive inference expansion before exposure ledger design is approved.

---

## 3. Hard Boundaries

### 3.1 Read-Only Cortex

Cortex is a projection and invariant layer. It must be physically incapable of
mutating domain state.

Forbidden inside Cortex modules:

- `db.add`
- `db.delete`
- `db.commit`
- `db.flush`
- Redis writes
- Notion writes
- notification sends
- TaskManager or StopwatchManager mutations

Allowed:

- read ORM rows
- compute projections
- raise invariant errors

### 3.2 Metric Immutability

Derived metrics are functions of raw observables only.

Forbidden:

- derived metric A consuming derived metric B unless the contract declares the
  transformation
- learning metrics consuming user-facing copy
- learning metrics treating prior model outputs as raw observations

Allowed:

- raw observables -> named Cortex metric
- raw observables + evaluation version -> recomputed projection

### 3.3 Inference Isolation

Inference must be stateless over the raw event stream and declared Cortex
projections.

Forbidden as behavioral evidence:

- service-layer caches
- Redis stopwatch state
- UI state
- unstamped operator notes
- generated summaries

Allowed:

- persisted raw observables
- Cortex projections with clean-data profile
- provenance-tagged exposure/intervention artifacts

---

## 4. Required Guardrails Before Structural Refactor

These are Priority 1. Do not continue broad folder restructuring until they
exist.

1. Characterization tests for golden Cortex outputs.
2. Dependency DAG enforcement for backend layers.
3. Central clean-data profile owner.
4. Unknown-propagation tests.
5. Evaluation-version stamp checks.
6. Read-only Cortex static checks.

The point is not to make the architecture pretty. The point is to prevent the
architecture from silently changing what old rows mean.

---

## 5. During-Refactor Rules

- Move one module family per commit.
- Preserve aliases when renaming meaning-bearing concepts.
- Do not change inference outputs in a structural commit.
- Do not tune thresholds in a structural commit.
- Do not add new psychological vocabulary in a structural commit.
- Document every layer boundary touched by the change.
- Run characterization tests before and after each move.

---

## 6. Stop Conditions

Pause the refactor if any of these occur:

- an unknown becomes a default without a documented resolution rule
- a derived metric is persisted as truth
- Cortex imports a service or inference module
- inference reads service-layer cache state as behavioral evidence
- a latent label appears in a database write path
- a structural move changes a user-facing inference result
- a module move requires inventing new ontology to make the folder structure fit
