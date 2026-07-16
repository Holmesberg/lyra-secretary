# Decision-Episode Repository Archaeology Audit

---
authority: audit-evidence
may_authorize_code: false
runtime_owner: none
status: read-only repository and Git-history audit
product_name: LyraOS
schema_authority: none
model_authority: none
experiment_authority: none
required_final_reviewer: founder
audit_date: 2026-07-16
---

## 1. Scope And Method

This audit executed the role-separated prompt in
`docs/audits/decision_episode_repository_archaeology_prompt.md`. It inspected
active runtime code, tests, registries, current and historical documentation,
and Git history. It made no runtime or schema change.

Seven independent role prompts were prepared. The shared agent service reached
its thread limit before a reliable seven-agent result set could be collected.
Rather than recurse into more audit infrastructure, the same seven scopes were
run as separate local passes and reconciled here. Findings are therefore
evidence-backed, but inter-agent agreement is not claimed.

Evidence labels:

- **high:** directly supported by current code/tests and a recoverable commit;
- **medium:** current code is clear but original intent or future utility needs
  interpretation;
- **low:** plausible connection with a material missing primitive;
- **speculative:** a research question, not a recovered capability.

## 2. Executive Findings

1. The repository already contains several narrow decision traces. The best is
   `CalibrationNudgeEvent`; it records proposal inputs, choice, later outcome,
   resolution, and voiding. A universal event platform is not the next step.
2. A universal canonical `DecisionEpisode` fails adversarial review. Opening,
   membership, and closure can be policy-mediated or hindsight-dependent. A
   bounded, domain-named Sprint projection may still be useful; append-only
   provenance-bearing source events must remain canonical.
3. LyraOS already has a three-registry control plane: mutation impact in query
   invalidation, output policy in the surface registry, and data ownership in
   the user-data registry. Future primitives should enter all three or fail
   promotion.
4. The repo already distinguishes safe abstention from useless paralysis.
   LyraSim's `unknown_fail_closed_rate` and `uncertainty_paralysis_rate` are a
   practical starting point for resolution coverage.
5. Current task rows cannot reconstruct accepted plan history. Rescheduling
   mutates plan fields and increments only a count. That count is a trigger for
   investigation, not plan lineage.
6. Two current defects can poison any future learning: callers may choose task
   creation lifecycle labels, and Pulse `Wins` appears to invert the canonical
   duration-delta sign.
7. The most defensible pre-cohort slice is one bounded Sprint workflow from
   Pressure Map through existing stopwatch execution and lightweight outcome
   reconciliation. It requires proof before schema.

## 3. Forgotten Intent Inventory

| Artifact | Original reason | Current behavior | Why the reason faded | Evidence | Confidence |
| --- | --- | --- | --- | --- | --- |
| Brain Dump commit | Turn an unstructured workload into confirmed tasks/deadlines without hidden writes | Write-free parse, editable review, idempotent commit, and explicit `created/reused/rejected/failed` outcomes | It became described as onboarding plumbing rather than an uncertainty-resolution mechanism | `backend/app/api/v1/endpoints/brain_dump.py:86-374`; `backend/app/schemas/brain_dump.py:17`; commit `324f980` | high |
| Scope bullet snapshots | Test whether scope shape helps explain estimate error and deadline outcomes | Counts scope bullets at plan and execution | Current product copy exposes duration more than scope criteria | `backend/app/db/models.py:185`; `backend/app/services/task_manager.py:378-400,723,877`; commit `9bdfd06`; `backend/tests/test_scope_bullet_counter.py` | high |
| `reschedule_count` | Record planning friction and repeated deferral | Increments while planned values are overwritten | The count survived, but the replaced plan values and reasons did not | `backend/app/db/models.py:140`; `backend/app/services/task_manager.py:1237-1239,1291`; commit `81c47a5` | high |
| Calibration nudge log | Answer whether a displayed estimate correction improves later calibration | Persists suggestion inputs, accept/dismiss choice, later duration outcome, resolution, and voiding | It is treated as one analytics feature rather than a complete local decision trace | `backend/app/db/models.py:1107-1174`; `backend/tests/test_calibration_nudge_event.py`; commit `207d2ba` | high |
| Reflection view log | Distinguish saved history from actually viewed intervention content | Stores exact payload, lifecycle, dwell, dismissal, and outcome links | Exposure Ledger later became the dominant vocabulary | `backend/app/db/models.py:1177-1241`; commit `3c62baa` | high |
| Exposure Ledger | Separate decision, render, acknowledgement, and outcomes | Persists policy/version/content hashes and browser-owned acknowledgement paths | Usually discussed as governance, not as the measurement regime required to interpret behavior | `backend/app/db/models.py:1244-1454`; `backend/tests/test_exposure_ledger_v0.py`; commit `1fa37c8` | high |
| Exposure policy effect log | Detect whether gating changes evidence quality | Records policy-gate effects such as unknown and ledger-incomplete rates | It looks like operator diagnostics, but it measures the instrument itself | `backend/app/db/models.py:1457-1489`; commit `0e2a71f` | high |
| Output surface registry | Give every behavior-shaping surface one inspectable policy classification | Registers truth/usage class, clean profile, signal target, render policy, interruptiveness, and salience | It predates `DecisionContract` vocabulary | `backend/app/core/output_surface_registry.json:1-98`; commit `3a62186` | high |
| Survey raw responses | Preserve evidence so scoring can be changed without forcing a retake | Stores completed/skipped distinction and all 29 answers | Later UI emphasized archetype labels instead of an inspectable cold-start prior | `backend/app/db/models.py:895-926`; commit `266afaf` | high |
| Dynamic archetype proximity | Replace identity-like static labels with changing evidence | Computes a damped posterior over recent task evidence | The feature remained named around archetypes rather than prior-to-personal updating | `backend/app/services/archetype_proximity_service.py:1-38,136-190`; commit `7e7ffb3` | high |
| Pressure projection primitives | Prevent double-counting while exposing demand and coverage uncertainty | Pure count-once range algebra with explicit identities | The UI action set remained narrower than the projection's orientation value | `backend/app/services/academic_pressure_projection.py:1-176`; `backend/tests/test_academic_pressure_projection.py`; commits `9ceb6d4`, `8bff98f` | high |
| Stopwatch switch topology | Preserve one active timer while representing interruptions and child sessions | Records explicit pause reasons, initiator, parent/child switch relations, and repaired state | It is treated as timer implementation rather than execution topology | `backend/app/db/models.py:958-1104`; `backend/app/services/stopwatch_manager.py:588-654,790-900` | high |
| Execution corrections | Preserve raw observation while allowing user-authoritative correction | Append-only correction rows feed effective projections | The stronger revision/provenance pattern is confined to execution | `backend/app/db/models.py:642-712`; `backend/tests` correction fixtures; commit `c256c86` for the UI path | high |
| Deadline completion provenance | Separate provider, user, and retroactive completion evidence | Stores completion source and time provenance | Deadline status is often consumed as one state despite different evidence ceilings | `backend/app/db/models.py:452-518`; commit `851ad64` | high |
| Behavioral signature aggregate | Consolidate read-only transition and recovery diagnostics for a former reasoning consumer | Computes pause distribution, recovery latency, schedule volatility, switch graph, disagreement, and reschedule outcomes | The original Jarvis consumer was retired, so the deterministic aggregate looks orphaned | `backend/app/services/behavioral_signature_aggregate.py:68-744`; commit `a90fda5`; direct model runtime retirement `37ebad2` | medium |
| User-data registry | Make export/delete complete and inspectable | Enumerates user-owned tables and deletion policy | It is seen as privacy plumbing rather than an ontology completeness check | `backend/app/services/user_data_registry.py:1-409`; commit `57ed0af` | high |
| Query-key invalidation helpers | Stop stale UI state after canonical mutations | Maps task, deadline, timer, integration, recovery, and undo mutations to affected projections | It is described as frontend cache hygiene rather than an impact graph | `frontend/lib/query-keys.ts:1-227`; `scripts/test_frontend_query_keys_contract.mjs`; commits `f238ef1`, `abeaafc` | high |
| LyraSim uncertainty metrics | Fail closed under unknown evidence without making the product inert | Separately scores unknown admission and no-safe-action paralysis | It is framed as simulation scoring, not resolution-coverage economics | `scripts/lyrasim/scorers/core.py:362-383,422-441`; `backend/tests/test_lyrasim_v0.py`; commit `b185c3e` | high |

## 4. Latent Power Map

| Existing artifact | New ontology role | Newly enabled computation | Product value | Missing primitive | Readiness |
| --- | --- | --- | --- | --- | --- |
| Calibration nudge event | Narrow decision/outcome trace exemplar | Outcome by proposal, choice, and later execution | Improve estimate correction without inventing a universal trace format | Projection cleanup and exposure parity | `after_substrate_repair` |
| Output surface registry + Exposure Ledger | Proto decision-policy constitution plus `MeasurementRegime` | Detect contract conflicts, burden conflicts, and exposure-incomplete outcomes | Fewer contradictory or unaccountable surfaces | Cross-registry consistency scanner | `after_one_minimal_primitive` |
| Query invalidation helpers | Mutation-to-projection impact graph | Identify which views must change after each command | Prevent stale Pressure Map/Today/Table decisions | Generate or test coverage against canonical mutation registry | `available_now` |
| User-data registry | Evidence-primitive coverage oracle | Detect new episode rows missing export/delete treatment | Makes privacy and deletion non-optional | Registry coverage gate for any later schema | `available_now` |
| Scope snapshots + deadline evidence | Partial outcome-criterion evidence | Scope drift by deadline context | Show when shrinking scope protected a deadline | Accepted criterion snapshot and user confirmation | `after_one_minimal_primitive` |
| Mutable plan fields + `reschedule_count` | Weak revision trigger | Identify repeated-revision candidates only | Ask for repair at the right moment | Append-only before/after revision evidence | `after_one_minimal_primitive` |
| Stopwatch + pause + switch graph | `ExecutionEvidence` topology | Active/wall time, interruption path, resumption, and switches | Recovery based on observable interruption mechanics | Episode boundary and contribution closure | `after_one_minimal_primitive` |
| Execution corrections + provenance flags | Observation capability lattice | Raw/effective/clean sensitivity and artifact classification | Honest history and recalibration | One registered `MeasurementRegime` projection | `available_now` |
| Survey + dynamic proximity | Inspectable cold-start prior | Compare prior, recent evidence, and divergence | Useful day-zero defaults that can yield to behavior | Valid target and transportability study | `cohort_dependent` |
| Behavioral aggregate | Candidate deterministic feature projection | Recovery latency, transition lift, schedule volatility, disagreement | Select a relevant recovery question or description | Validate signs, labels, clean admission, and current consumer | `after_substrate_repair` |
| LyraSim | Resolution-coverage and artifact-falsification harness | Compare safe abstention with useless paralysis | Prevent both fabricated certainty and constant "unknown" | Surface-specific fixtures | `after_one_minimal_primitive` |
| Pressure Map + current canonical actions | Bounded orientation contract | Count-once demand/coverage comparison and one action | Turn imported workload into an immediate decision | Episode activation and lightweight closure | `after_one_minimal_primitive` |

## 5. Unexpectedly Valuable Existing Features

### 5.1 Calibration nudge as the reference trace

It was built to answer one local analytics question. Its durable proposal,
choice, outcome, resolution, and voiding fields demonstrate that feature-
specific traces can preserve decision evidence without creating a universal
episode identity. Falsification: if its render lifecycle or later outcome
linkage is incomplete, it remains only a partial exemplar.

### 5.2 Output surface registry as constitution

The registry already centralizes classifications that local decision contracts
would otherwise redefine. A consistency scan can detect two surfaces using
incompatible clean profiles, salience, or truth classes. Falsification: if
runtime surfaces routinely bypass the registry, the registry is documentation,
not enforcement.

### 5.3 Query invalidation as an impact graph

The cache helpers encode which product projections depend on canonical task,
deadline, timer, integration, recovery, and undo mutations. This is useful for
stale-decision tests even if it never becomes a runtime graph. Falsification:
if invalidation lists are incomplete or route-specific, they first expose a
bug rather than a reusable ontology.

### 5.4 User-data registry as an ontology promotion gate

A future event that cannot be exported, deleted, retained, or redacted is not
ready to become canonical evidence. This turns privacy infrastructure into a
mechanical completeness test. Falsification: external or Redis-owned user data
must also be represented; SQL coverage alone is insufficient.

### 5.5 LyraSim as abstention-economics harness

Unknown admission and uncertainty paralysis are already separate failures.
That distinction is the core of a `ResolutionCoverageContract`: abstention may
be honest while repeated inability to help still fails the product. It does
not authorize a recommendation when evidence is weak.

### 5.6 Exposure policy effects as instrument diagnostics

`ExposurePolicyEffectLog` can detect changes in the evidence-generating system,
not merely user behavior. This is one legitimate use of architecture self-
explanation: identifying a measurement-regime shift. It is not a user-facing
insight.

### 5.7 Archetype history as prior-retirement precedent

Raw survey evidence was preserved for re-scoring; later proximity code added
non-IID damping and intentionally separated recent evidence from the survey-
anchored prior. The system already contains the principle "evidence may earn
the right to replace a prior," even though current constructs remain
provisional.

### 5.8 Behavioral aggregate as a deterministic feature store

The former reasoning consumer is gone, but the aggregate survived as a read-
only service. It contains useful candidate features and explicit "do not
speculate" coverage. Before reuse, its valence labels, signs, clean profiles,
and denominators must be audited.

### 5.9 Scope snapshots as partial outcome criteria

Plan-time and execute-time bullet counts do not establish task quality, but
they preserve a low-burden trace of scope change. Combined with deadline
evidence and user confirmation, they may support "minimum scope protected"
without a full task graph.

### 5.10 Correction events as a revision pattern

Execution correction already preserves before/after authority without
overwriting raw observation. Plan revision should copy this append-only pattern
only if a real blocked question justifies it; it should not force all changes
into one generic event.

### 5.11 Deadline provenance as an evidence-capability axis

Provider completion, explicit user completion, retroactive completion, and
timer observation support different claims. The fields make an evidence-
capability projection possible now, but not a unified "completion truth."

### 5.12 Undo plus invalidation as reversibility evidence

Undo is short-lived product state, not durable lineage. Combined with explicit
invalidation coverage, however, it supplies a practical rollback oracle for
bounded commands. It should stay a command-safety primitive, not be promoted
into historical plan evidence.

## 6. Idea Lineage Graph

```text
calibration nudge outcome log
-> answer whether a suggestion improved estimate accuracy
-> isolated analytics feature
-> DecisionEpisode and DecisionTrace vocabulary
-> feature-specific proposal/choice/outcome trace
-> reusable reference for bounded decision evidence

output surface registry
-> classify behavior-shaping surfaces
-> treated as static governance metadata
-> cross-contract coherence problem
-> decision-policy constitution
-> mechanical contradiction and burden checks

unknown fail-closed + uncertainty paralysis
-> keep simulations honest and useful
-> treated as scorer internals
-> abstention economics problem
-> ResolutionCoverageContract
-> safe fallback without permanent uselessness

survey raw answers + dynamic proximity
-> preserve re-scoring and mitigate identity labels
-> still named around archetypes
-> prior-to-personal evidence lifecycle
-> inspectable cold-start prior
-> cohort prior that personal evidence may retire

Pressure Map + stopwatch + recovery
-> orient workload, observe execution, repair disruption
-> separate product surfaces
-> bounded DecisionEpisode
-> one sprint projection and closure
-> reconstructible orientation-to-outcome loop
```

## 7. Cold-Start And Clustering Boundary

The questionnaire may initialize a prior over likely episode or plan regimes,
not a person identity. Current raw responses support future re-scoring, and
dynamic proximity demonstrates an inspectable separation from recent evidence.

The defensible sequence is:

```text
questionnaire response
-> provisional prior over episode-level parameters
-> first observed episodes under known measurement regimes
-> personal calibration
-> cohort-informed partial pooling when support exists
-> personal evidence increasingly dominates
```

Cluster episode shapes, revision trajectories, recovery paths, and execution
topologies before clustering users. A user-level cluster is retained only if
it improves a predefined cold-start target out of sample and remains a
probabilistic prior. First adversarial models should predict route, synthetic
status, retroactive status, correction state, and exposure completeness. If
those are easier to predict than outcomes, repair instrumentation before
interpreting latent structure.

No current evidence supports a minimum cohort size, stable cluster count, or
student default. Those remain cohort-dependent decisions.

## 8. Recombination Opportunities

| Existing components | New capability | Smallest missing primitive | Proof and stop condition |
| --- | --- | --- | --- |
| Pressure Map + selected obligations + stopwatch + recovery | Start one bounded sprint and reconcile which obligations moved | Narrow episode activation and closure snapshot | User changes one decision, closes in under roughly 30 seconds, and voluntarily reuses; stop if closure burden or stale state dominates |
| Brain Dump + Pressure Map missingness + deterministic resolution predicate | Ask one question that changes feasibility or dominance | One registered question family and trace | The answer changes the action set or safest resolution mode; stop if questions are frequent but non-decisive |
| Output registry + Exposure Ledger + LyraSim | Surface coherence and resolution-coverage suite | Static cross-registry fixtures | Detect known conflicts and paralysis without weakening unknown handling; stop if registry bypass is common |
| Survey prior + personal calibration + episode projection | Cold-start estimate range that can yield to personal evidence | Versioned prior contribution and retirement rule | Personal evidence changes the projection inspectably; stop if survey label predicts route artifacts or becomes identity copy |
| Scope snapshots + deadline provenance + user closure | Minimum-scope protection evidence | Time-bound outcome criterion | User can confirm preserved/reduced scope without false precision; stop if bullet count does not correspond to meaningful scope |

## 9. Pre-Adaptation Report

### Genuine pre-adaptations

- Calibration nudge event: complete local decision/outcome trace.
- Exposure Ledger: reconstructible system participation and browser render.
- Raw/effective correction split: provenance-preserving revision pattern.
- Count-once Pressure Map projection: deterministic decision substrate.

### Intentional long-term preservation

- Survey raw responses for future re-scoring.
- Historical model-enrichment columns retained pending migration authority.
- Provider and completion provenance retained below execution truth.

### Lucky reuse

- Query invalidation lists as a product projection impact map.
- User-data registry as an ontology coverage gate.
- LyraSim paralysis scoring as abstention economics.

### Overfitting risks

- `parent_task_id` represents stopwatch switch topology, not task dependency.
- `reschedule_count` is not revision history.
- Scope bullet counts are not outcome quality.
- Behavioral "valence" labels are heuristic outputs, not latent mechanisms.
- Exposure correlation is not treatment effect.
- Dynamic archetype posterior is not discovered user identity.

## 10. Adversarial Falsification

The ontology-adversary pass produced six findings that constrain every
positive result above:

1. **No canonical transition ledger exists today.** Task state can be selected
   by creation callers, pause/resume mutates state inline, and stale/orphan
   recovery can synthesize terminal state. Latest task state cannot support
   canonical episode reconstruction.
2. **Episode closure is policy-mediated.** In stale resolution, otherwise
   similar 120-minute execution is classified differently at 80% versus 79%
   self-reported completion (`backend/tests/test_stale_pause_resolution.py:
   192-240`, commit `484ee70`). A generic episode cannot pretend that closure
   was directly observed.
3. **Plan provenance loss is real, but full `PlanLineage` is not thereby
   justified.** A single append-only accepted snapshot or revision may be
   sufficient if a shipped user decision is demonstrably blocked.
4. **Many-to-many contribution is a missing fact.** Naming
   `WorkContributionEvidence` cannot create attribution. Unconfirmed
   contribution remains `unknown`; routine time allocation would create
   unacceptable burden and false precision.
5. **Contracts do not enforce formulas.** The Pulse sign defect exists despite
   canonical prose. Shared implementations and executable consumer fixtures
   are required before more contract vocabulary.
6. **Exposure stratification survives, causal interpretation does not.** A
   current contamination path can treat a render row as exposure while browser
   attention remains unconfirmed (`backend/app/services/exposure_ledger.py:
   741-808`). Episode packaging cannot remove reactivity or confounding.

Kill canonical `DecisionEpisode` whenever opening, membership, or closure
cannot be reconstructed without hindsight. Keep `DecisionTrace` as computed
debug provenance unless a specific user workflow proves a stronger domain
object is necessary.

## 11. Ranked Action Plan

### Before cohort

1. Fix label-corrupting defects before fitting or interpreting anything:
   caller-selected task creation state and Pulse duration-delta sign.
2. Verify every touched behavior-shaping surface creates browser-owned render
   truth and explicit unrendered terminal outcomes.
3. Run analysis-only raw/effective/clean and route-artifact falsification.
4. Test one Pressure Map to sprint vertical slice only after the current core
   loop gates pass and founder approval names the seam.
5. Add a cross-registry audit proving mutation impact, output policy, and
   export/delete coverage for that one slice.

### Collect during cohort

1. Transportability of estimate ranges and cold-start priors.
2. Whether episode-level regimes recur outside founder data.
3. Whether one clarification question changes a real decision without adding
   burden.
4. Missingness, correction, exposure, and recovery distributions by route.
5. Whether personal evidence eventually outperforms and retires cohort priors.

### Keep parked

- universal cost function;
- generalized DecisionEpisode platform;
- full PlanLineage or task graph;
- user clustering as identity;
- runtime ID3 or other learned ranking;
- probabilistic Value of Information;
- adaptive intervention policy;
- automatic plan or recovery mutation;
- causal or psychological claims;
- AI ownership of evidence, objectives, confidence, or mutation.

## 12. Final Synthesis

### A. Five Biggest Recovered Insights

1. Narrow feature-specific decision traces already exist and are safer than a
   universal event model.
2. Canonical source evidence is universal; an episode is a policy-versioned
   projection or domain-named workflow, and plan lineage is optional.
3. Three existing registries already span mutation impact, output policy, and
   data sovereignty.
4. Safe abstention and product paralysis can already be tested separately.
5. The strongest immediate value is a bounded orientation-to-execution loop,
   not a new analytics or AI layer.

### B. Five Underestimated Existing Features

1. `CalibrationNudgeEvent`.
2. Output surface registry.
3. Exposure policy effect log.
4. Query invalidation helpers.
5. LyraSim unknown/paralysis scoring.

### C. Three Strongest Product Recombinations

1. Pressure Map + selected obligations + stopwatch + recovery -> bounded
   sprint episode.
2. Brain Dump + decision-relevant missingness -> one useful clarification.
3. Survey prior + personal calibration -> cold-start range that can retire
   itself.

### D. Single Best Pre-Cohort Vertical Slice

```text
Pressure Map
-> select obligations
-> Start Sprint
-> existing timer
-> pause/switch/recover
-> lightweight "which obligations moved?" closure
```

Use one projection, `sprint_execution.v1`, one decision contract, one computed
debug trace, and at most one deterministic resolution question family. Call
the product workflow a Sprint. Do not persist a generic `DecisionEpisode`.
This is a parked recommendation, not implementation authority.

### E. Strongest Falsification Result

The new ontology is invalid at its center if `DecisionEpisode` is treated as
canonical identity. Current state mutations cannot reconstruct a universal
opening, membership, or closure without policy and hindsight. Current mutable
tasks also cannot reconstruct accepted historical plans. Naming either object
does not recover missing evidence.

### F. What Should Remain Untouched

- canonical task/deadline/stopwatch mutation owners;
- provider evidence below execution truth;
- browser-owned exposure acknowledgement;
- raw/effective/clean separation;
- current data export/delete guarantees;
- model runtime retirement;
- parked task graph, learned policy, experiments, and causal claims.

### G. Founder Decision Packet

**Discovered:** LyraOS contains narrow traces and registries that cover much of
the proposed boundary, but it does not contain a canonical transition ledger.
The missing piece is provenance-bearing source evidence and one bounded user
workflow, not a universal framework.

**Evidence versus inference:** current fields, tests, and commits establish the
existing traces. Their reuse as a sprint episode is an inference requiring a
separate product seam and real dogfood.

**Newly possible:** deterministic episode reconstruction, one useful
clarification, cross-surface coherence tests, and prior-to-personal cold-start
evaluation become well-posed after substrate repair.

**Recommended:** repair label integrity, run read-only falsification, then
consider one Pressure Map Sprint slice as a named product workflow.

**Not recommended:** generalized episode infrastructure, full plan graph,
runtime learned ranking, probabilistic VoI, automatic mutation, or AI policy.

**Reverse course when:** closure is burdensome, episode reconstruction remains
ambiguous, the slice is not voluntarily reused, route artifacts dominate, or
the same value is available from current simpler paths.

### H. What Surprised You?

Scores use 1 (low) to 5 (high). Confidence scores reflect repository evidence,
not confidence in future product success. No audit role was explicitly asked
to find these exact relationships; they emerged only after evidence from the
role-separated passes was compared.

| Rank | Emergent finding | Conceptual novelty | Product leverage | Research leverage | Confidence |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | The presumed `CanonicalTransitionLedger` does not exist. Current state is partly mutable and partly synthesized by recovery policy, so a universal episode would canonize hindsight unless source events are repaired first. | 5 | 5 | 5 | 5 |
| 2 | LyraOS already has a three-registry control plane: query invalidation maps mutation impact, the output registry maps decision/exposure policy, and the user-data registry maps retention and deletion. Together they can gate a new primitive without a universal framework. | 5 | 5 | 5 | 5 |
| 3 | LyraSim already prices both sides of abstention: admitting unknown evidence is unsafe, while offering no safe action creates `uncertainty_paralysis`. This is a concrete resolution-coverage test hiding inside simulation infrastructure. | 5 | 5 | 4 | 5 |
| 4 | `CalibrationNudgeEvent` is a miniature closed decision trace built before the new vocabulary existed: inputs, proposal, user choice, later outcome, resolution, voiding, and transactional linkage. | 5 | 5 | 5 | 5 |
| 5 | `ExposurePolicyEffectLog` does not merely measure users; it measures when a policy gate changes the instrument's evidence quality. Architecture self-explanation already has a legitimate domain use. | 5 | 3 | 5 | 5 |
| 6 | Query invalidation is an accidental dependency graph for product projections. It can reveal stale decision surfaces and define mutation-impact fixtures even if it never becomes runtime ontology. | 4 | 5 | 3 | 5 |
| 7 | The former reasoning consumer was removed, but the deterministic behavioral aggregate survived with explicit coverage and anti-speculation boundaries. Model retirement uncovered rather than destroyed a candidate feature store. | 4 | 4 | 5 | 4 |
| 8 | Survey evolution had already encoded "prior may yield to evidence": raw answers survive re-scoring, dynamic proximity is separate, and `sqrt(N)` damping acknowledges non-IID task evidence. The current vocabulary obscures that deeper lifecycle. | 4 | 4 | 5 | 5 |
| 9 | The asymmetry between append-only execution corrections and lossy plan rescheduling is architectural evidence: LyraOS already knows how to preserve revisions, but only where a real correction workflow forced it to. | 4 | 4 | 5 | 5 |
| 10 | `parent_task_id` looks graph-ready but represents stopwatch switching, not task dependency. The field is more valuable as a falsification guard against an attractive but false task graph than as a graph primitive. | 4 | 3 | 4 | 5 |

## 13. Hard Stop

This audit authorizes no runtime behavior, schema, episode model, plan lineage,
tree, cluster, prediction, prompt, experiment, user-facing claim, adaptive
policy, or AI integration. Promotion requires a new founder-approved seam.
