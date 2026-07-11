# AI Capability Completion Map

---
authority: concept-note
may_authorize_code: false
runtime_owner: none
status: repository-wide capability survey pending founder review
product_name: LyraOS
schema_authority: none
public_api_authority: none
pricing_authority: none
experiment_authority: none
required_final_reviewer: founder
draft_review_date: 2026-07-11
---

## Catalogue, Not Backlog

**A candidate's presence in this document records a possibility to evaluate;
it does not create implementation priority, sequencing, commitment, or
authority.**

## Hard Stop

This document maps possible uses of reasoning systems. It does not authorize
any runtime AI, prompt, adapter, schema, experiment, threshold change,
automatic mutation, user-visible AI output, entitlement, price, public claim,
or deployment change.

The active freeze and all authority boundaries in `docs/AUTHORITY.md` remain in
force. A candidate in this map may move into implementation only through a
separately approved seam with characterization proof, privacy review,
exposure reconstruction, deterministic fallback, and an explicit authority
ceiling.

## 1. Completion Thesis

LyraOS should not become a deterministic system with an AI system sitting on
top of it. It should become a complete decision substrate in which each method
does the work it is best qualified to do.

```text
authoritative state and user corrections
-> exact rules and state machines
-> parsers, retrieval, search, and graph operations
-> constraint solving and optimization
-> descriptive statistics and probabilistic estimation
-> classical ML where labels and evaluation support it
-> simulation and falsification
-> bounded reasoning-runtime augmentation for residual ambiguity
-> deterministic validation and claim compilation
-> registered surface and browser-proven exposure
-> explicit user action through canonical mutation authority
```

AI is therefore a **residual capability layer**. It may widen a candidate set,
recognize semantic edge cases, propose competing explanations, identify
missing variables, or improve wording. It does not replace a cheaper, more
inspectable, more reproducible method when that method can solve the problem.

Residual does not mean marginal. The reasoning layer should create a dramatic
product improvement by resolving the highest-cost semantic gaps at each stage
and carrying their provenance through the full loop. The authority ceiling is
narrow; the capability ambition is not.

The test for every proposed use is:

> What uncertainty remains after exact rules, structured parsing, retrieval,
> search, constraints, statistics, classical ML, simulation, and explicit user
> confirmation have had first refusal?

If the answer is unclear, AI has no role yet.

## 2. Two Independent AI Value Channels

### 2.1 Runtime augmentation

A separately authorized reasoning runtime may process a minimized,
provenance-bearing packet and return a structured candidate. This path is for
semantic ambiguity or hypothesis breadth that cannot be represented adequately
by the deterministic substrate.

```text
LyraOS
-> EvidenceAdmissionGate
-> EvidencePacket
-> ReasoningRuntimeContract
-> OpenClawAdapter
-> structured candidate
-> deterministic validation
-> OutputClaimCompiler and SurfacePolicy
```

Runtime augmentation is initially suitable only for founder/cohort-sponsored
shadow evaluation. User-visible use requires a later protocol and exact
exposure proof.

### 2.2 AI-to-deterministic distillation

The complete no-runtime baseline, including any future free packaging, can
benefit from AI without invoking AI for that user.

```text
versioned deterministic baseline
-> shadow AI reviews residual misses and edge cases
-> human adjudication and privacy review
-> candidate rule, lexicon, parser case, prior, fixture, or test
-> independent holdout and regression evaluation
-> versioned deterministic artifact
-> no-runtime baseline release
```

Examples include:

- adding validated date or obligation phrases to a parser lexicon;
- deriving a new deterministic ambiguity guard from repeated deadline-binding
  failures;
- turning recurring semantic decompositions into explicit templates;
- generating adversarial fixtures that become permanent tests;
- identifying a useful feature for a calibrated statistical or classical-ML
  model;
- discovering stable recovery-option categories that literature and user
  evidence can support;
- improving deterministic public or recovery copy through reviewed templates.

The deterministic artifact must be understandable without the generating model. Model
output, confidence, or hidden rationale may not be compiled into a rule merely
because it appears repeatedly. Promotion requires a named construct, explicit
logic, independent evidence, versioning, and rollback.

Distillation additionally requires frozen train/adjudication/holdout splits,
contamination checks, corpus consent and licensing, deletion propagation,
locale/provider stratification, artifact lineage, and exposure-impact review.
An AI-derived prior does not become deterministic merely because it was
serialized; its derivation, uncertainty, population and rollback remain part
of its provenance.

## 3. Method-Selection Ladder

Use the lowest sufficient layer. Later layers may challenge earlier layers,
but they do not silently replace their authority.

Human confirmation has two positions in this ladder. Existing explicit forms
and corrections receive first refusal before reasoning is invoked. If a
reasoning candidate is produced, a second explicit confirmation may authorize
the canonical command. Neither confirmation grants the model mutation access.

| Layer | Best use | Required property | Typical LyraOS examples |
| --- | --- | --- | --- |
| Exact state machine | Valid transitions and terminal truth | Total, inspectable transition rules | Task lifecycle, stopwatch, notification and exposure lifecycle |
| Symbolic parser/rules | Stable syntax and explicit policy | Deterministic and versioned | Dates, duration phrases, canonical status, eligibility gates |
| Retrieval/search | Find known user-owned facts | Scoped, attributable results | Existing deadlines, prior similar tasks, source artifacts |
| Graph operations | Explicit relations and reachability | Confirmed edges and cycle policy | Parent/child work, dependency proposals after confirmation |
| Constraint solver/operations research | Feasible plans under explicit constraints | Objective and constraints are visible | Calendar placement, load balancing, recovery-plan preview |
| Descriptive/robust statistics | Summaries of observed behavior | Units, denominator, exclusions, missingness | Medians, quantiles, intervals, estimate error |
| Probabilistic/time-to-event methods | Uncertainty and event timing | Calibration and censoring are explicit | Pause/resume hazard, duration intervals, workload uncertainty |
| Classical ML | Repeated labeled prediction with stable features | Holdout evaluation, drift and abstention | Ranking residuals, anomaly detection, semantic classifier |
| Simulation | Stress and counterexample generation | Assumptions are inspectable | LyraSim, schedule feasibility, policy burden |
| Human confirmation | Meaning, preference, and irreversible choice | User sees the actual candidate and effect | Binding, dependency, plan, recovery action |
| Reasoning runtime | Residual semantics and hypothesis breadth | Structured, attributable, bounded output | Decomposition, competing hypotheses, missing-variable questions |

This ladder explicitly includes methods beyond determinism, heuristics,
statistics, and generative AI: information retrieval, fuzzy matching,
knowledge representations, graph algorithms, operations research, Bayesian
models, survival analysis, anomaly detection, ranking, clustering, calibrated
classifiers, simulation, property-based testing, formal constraints, and human
adjudication all remain first-class options.

## 4. Authority Ceiling

| Object or decision | Canonical authority | Maximum AI role |
| --- | --- | --- |
| User identity and tenant scope | Identity resolver and request context | None |
| Task/deadline/provider fact | Canonical manager or provider normalizer | Candidate extraction or mapping only |
| Task relation/dependency | Explicit user confirmation or future deterministic contract | Proposed edge with evidence only |
| Timer/session finalization | Stopwatch state machine and finalizer | Anomaly question only |
| Clean-data admission | Clean profile and admission gate | Identify possible missingness; no decision |
| Metric definition and unit | Metric registry and deterministic code | Draft review note only |
| Probability/confidence | Calibrated method and named semantics | Never invent or upgrade |
| Intervention eligibility/timing | Versioned deterministic policy | Candidate option or wording only |
| Experiment assignment | Experiment registry/randomization authority | None |
| Claim publication | OutputClaimCompiler and SurfacePolicy | Structured draft below claim ceiling |
| Exposure/render/outcome truth | Browser lifecycle and exposure ledger | None |
| Mutation | Canonical command after explicit request | No direct tool authority |
| Consent/retention/delete | User and privacy contract | Explanation only |
| Deploy/restart/repair | Human operator and runbook | Diagnosis or plan draft only |

## 5. Capability Inventory By Product Loop

### 5.1 Capture, parsing, and import

| ID | Current substrate | Residual gap | Preferred completion method | Bounded AI role | Prerequisite |
| --- | --- | --- | --- | --- | --- |
| CAP-01 | `brain_dump_parser.py`, brain-dump preview/commit, editable frontend flow | Long, ambiguous, multilingual, or irregular prose | Extend grammar/lexicon, retrieval over user facts, fuzzy ranking | Add decomposition or field candidates with evidence spans | Golden corpus, disagreement artifact, unchanged heuristic fallback |
| CAP-02 | Same-dump and existing-deadline matching in `deadline_heuristic.py` | Semantic matches missed by token overlap | Retrieval, embeddings or classical ranker evaluated against confirmed binds | Re-rank or add candidates; never bind | Candidate provenance, per-candidate rejection, no silent preselection |
| CAP-03 | Explicit NewTask fields and category inference | Implied category, duration unit, or hidden sub-actions | Deterministic templates and user defaults | Propose editable category/sub-items | Every proposed field independently reviewable |
| CAP-04 | Provider-specific Moodle/iCal normalizers | Unstructured course labels and inconsistent source descriptions | Provider mapping tables, schema rules, retrieval | Interpret inside the provider-aware adapter and propose a provider-neutral fact | Provider identity/provenance remains attached; no credentials/raw export enter reasoning |
| CAP-05 | Disabled link/file capture affordances | Documents and links contain possible obligations | Safe fetch, MIME parser, OCR, metadata extraction, column mapping | Summarize source and propose obligations/dates | SSRF/malware/size gates, source citation, explicit import commit |
| CAP-06 | Typed brain-dump capture | Voice is decorative/unavailable | Browser or on-device speech recognition | Transcription and segment candidates only | Microphone consent, transient audio, editable transcript |
| CAP-07 | Flat tasks plus deadline links | Multi-step work loses structure | Minimal confirmed grouping/edge contract, cycle checks | Propose parent-child/support/block/follows edges | No schema until approved; no edge becomes truth without confirmation |
| CAP-08 | Provider completion evidence | Provider status may contradict user state | Deterministic precedence and reconciliation UI | Explain contradiction and ask one bounded question | Preserve both source facts and correction lineage |
| CAP-09 | Manual correction paths | Repeated parser corrections are not systematically learned | Error taxonomy, active-learning queue, deterministic distillation | Cluster residual errors and propose parser fixtures | Privacy-minimized corpus and human labels |
| CAP-10 | Idempotent commit paths | Candidate duplication across imports or reruns | Stable source IDs, canonical fingerprints, fuzzy duplicate review | Explain why two records may be duplicates | AI never supplies idempotency key or deletes a row |

### 5.2 Pressure, planning, and scheduling

| ID | Current substrate | Residual gap | Preferred completion method | Bounded AI role | Prerequisite |
| --- | --- | --- | --- | --- | --- |
| PLN-01 | `academic_pressure.py` obligation classes and low-authority ranges | Title-based complexity misses semantics | Type priors, confirmed history, hierarchical intervals | Add competing complexity/type candidates | Range provenance and abstention; no workload truth |
| PLN-02 | Pressure coverage questions | Questions are visible but not canonical correction commands | Explicit correction workflow and source trust hierarchy | Draft the smallest clarifying question | Answer must enter through a canonical correction contract |
| PLN-03 | Pressure recovery-option labels and plan preview | Options can feel decorative or incomplete | Constraint-based plan preview with editable rows | Propose decomposition and option variants | Dismiss creates nothing; commit is explicit and idempotent |
| PLN-04 | Calendar drag/resize and soft conflicts | No multi-objective placement assistance | CP-SAT/interval scheduling, slack and priority constraints, simulation | Explain tradeoffs among solver-generated plans | AI cannot move events; objective and constraints displayed |
| PLN-05 | User duration plus deterministic nudge | Cold-start and unusual tasks lack personal evidence | Robust cohort-safe ranges, nearest-neighbor retrieval, Bayesian shrinkage | Draft assumptions or semantic analogues | AI estimate excluded from clean user-estimate calibration |
| PLN-06 | Visible academic load | Missing obligations and double-counting risk | Coverage ledger, exact relation accounting, graph dedupe | Identify suspected missing or duplicate structure | Deterministic accounting repaired before model use |
| PLN-07 | Today/Pulse ordering | Multiple eligible tasks lack meaningful tie-breaking | Stable urgency/slack/commitment ranking and user pins | Semantic tie-breaker or concise explanation | Ranking is exposure; option set and policy version logged |
| PLN-08 | Deadline clusters | Fixed windows may miss interacting obligations | Graph/interval analysis and Monte Carlo load simulation | Name a plausible interaction requiring confirmation | No causal or emotional interpretation |
| PLN-09 | Repeated commitments | Recurrence is provider-specific and partially parked | RFC-compliant bounded recurrence expansion | Explain series anomalies or proposed mapping | Timezone, EXDATE, horizon, dedupe, correction contract |
| PLN-10 | Plan feasibility | Planned blocks can exceed available capacity | Constraint checks and scenario analysis | Summarize infeasibility and ask which constraint may move | No automatic reprioritization or deletion |

### 5.3 Execution and correction

| ID | Current substrate | Residual gap | Preferred completion method | Bounded AI role | Prerequisite |
| --- | --- | --- | --- | --- | --- |
| EXE-01 | Stopwatch state machine, DB/Redis recovery | Forgotten timers and contradictory traces | State constraints, robust anomaly detection, LyraSim | Ask whether a bounded anomaly needs correction | AI cannot infer or finalize time |
| EXE-02 | Explicit pause reasons and events | Free text or route differences may lose context | Controlled vocabulary plus optional note | Propose mapping from note to existing reason | User confirms; raw note does not become latent trait |
| EXE-03 | Pause predictor medians/confidence gates | Residual timing variation | Survival/hazard model or calibrated classifier | Shadow residual/contradiction review only | Exposure-adjusted evaluation before visible use |
| EXE-04 | Resume predictor percentile/cold cap | Re-entry context is thin | Time-to-event model, recency and explicit task state | Draft a low-pressure cue or missing context question | Deterministic cooldown/burden owns eligibility |
| EXE-05 | Switch and stale-session commands | Interruption chains lose why/what-next context | Explicit suspended-goal note and recovery episode | Summarize the last confirmed state | No inferred motivation/focus/avoidance |
| EXE-06 | Post-stop reflection and corrections | User may not know which correction is needed | Deterministic discrepancy checks and concise choices | Explain contradictory fields in plain language | Append-only correction remains canonical |
| EXE-07 | Planned versus executed duration | Semantic task differences limit comparable history | Typed task features, robust matching, hierarchical models | Suggest comparable prior tasks with evidence refs | No hidden similarity becomes calibration truth |
| EXE-08 | One active timer invariant | Complex work may involve related tasks | Explicit grouping and switch semantics | Suggest candidate relationship, not parallel timer | State machine remains total and singular |

### 5.4 Intervention and recovery

| ID | Current substrate | Residual gap | Preferred completion method | Bounded AI role | Prerequisite |
| --- | --- | --- | --- | --- | --- |
| REC-01 | Re-entry queue and stale-session resolution | Keep/shrink/split/reschedule/drop are not uniformly executable | `RecoveryEpisode` state machine and canonical commands | Add option candidates allowed by current state | Literature-backed option vocabulary and explicit outcome tracking |
| REC-02 | Missed-plan actions | Same action may be wrong for different constraints | Deterministic eligibility plus one clarifying question | Formulate the question and candidate rationale | No psychological attribution; no default action |
| REC-03 | Creation nudge and reminders | Static wording may not fit context | Reviewed templates and constrained grammar | Draft smoother wording within fixed semantic slots | Exact wording/hash/version logged before later analysis |
| REC-04 | Pause/resume banners | Prompt timing changes observed behavior | Deterministic burden, cooldown, quiet hours and no-treatment policy | Wording candidate only | Decision, delivery, browser render and outcome correlated |
| REC-05 | Pressure-map recovery | Generic advice is less useful than executable structure | Solver-generated plan alternatives and editable preview | Semantic decomposition or explanation | No action until preview confirmation |
| REC-06 | Notification suppression | Unknown relevance or duplicated surfaces | Deterministic suppression policy and dedupe | Identify possible semantic duplicate for review | AI never marks delivered/rendered/suppressed truth |
| REC-07 | Recovery outcome | Clicking an action is not proof of recovery | Explicit proximal/distal outcome windows | Summarize outcome evidence after window closes | No success claim from action alone |
| REC-08 | Intervention option breadth | Deterministic policy may miss an edge-case option | Literature registry and bounded option catalogue | Add candidate option below catalogue authority | Human/literature review before option can become selectable |
| REC-09 | Burden/receptivity | Prompt fatigue and ignored prompts are informative | Deterministic burden counters, missingness models, MRT later | Explain or hypothesize burden in shadow only | No silent personalization or causal claim |
| REC-10 | Recovery language quality | Intuitive wording can shame or overclaim | Literature-derived semantic constraints and reviewed templates | Realize approved meaning in smoother language | Semantic equivalence, accessibility, safety and exposure tests |

### 5.5 Evidence, hypotheses, insights, and research

| ID | Current substrate | Residual gap | Preferred completion method | Bounded AI role | Prerequisite |
| --- | --- | --- | --- | --- | --- |
| INS-01 | Cortex projections and clean profiles | Evidence is distributed and missingness is hard to inspect | Canonical EvidencePacket and Admission/Coverage Gate | Summarize admitted evidence only | Runtime never sees excluded or untyped rows |
| INS-02 | Deterministic insight generators | One observation has many plausible causes | Causal diagrams, stratification, sensitivity checks | Generate competing hypotheses and contradictions | Hypotheses remain plural and evidence-linked |
| INS-03 | OutputClaimCompiler | Ordinary generators bypass one claim path | Route all claim-bearing output through compiler | Draft below an explicit claim ceiling | Compiler can reject without fallback publication |
| INS-04 | Confidence labels with mixed semantics | Count tiers, scores and probabilities are conflated | Typed confidence semantics and calibration | Explain the named confidence basis only | AI cannot create or upgrade confidence |
| INS-05 | Longitudinal traces | Narrative synthesis is fragmented | Robust trend/change-point methods and drift decomposition | Draft a concise synthesis with exact evidence refs | Separate user change, policy drift, provider drift and missingness |
| INS-06 | Hypothesis adjudication | Corrections and later contradictions are scattered | Versioned `HypothesisSet` and adjudication states | Add support/contradiction/missing-variable candidates | No forced single explanation |
| INS-07 | Archetype priors and proximity | Identity-like labels can reify weak models | Hierarchical priors, decay, calibration and no-label alternatives | Translate uncertainty, not assign identity | Personal evidence eventually dominates; sensitive copy blocked |
| INS-08 | Cascade/context-switch hypotheses | Correlation can be mistaken for cause | Matched comparisons, DAGs, experiment design | Generate confounder checklist | No failure/focus/motivation/fragmentation claim |
| INS-09 | Literature ledger | Relevant evidence is broad and transportability is uncertain | Curated retrieval, evidence tables, human review | Search, extract and compare findings with citations | No runtime rule or effect size imported automatically |
| INS-10 | Experiment design | Deterministic labels are not experiments | Registry, randomization, estimands, power/simulation | Draft protocol alternatives and analysis code | Founder/research approval owns protocol and promotion |
| INS-11 | Qualitative feedback | Free text is hard to synthesize | Search, embeddings, clustering and human coding | Cluster themes and summarize with source IDs | Prompt injection/redaction; no auto-resolution |
| INS-12 | Public claims | Copy can outrun implementation | Static claim scans and authority diffing | Draft corrections with repo citations | Human review; never auto-publish |

### 5.6 Operations, support, and engineering

| ID | Current substrate | Residual gap | Preferred completion method | Bounded AI role | Prerequisite |
| --- | --- | --- | --- | --- | --- |
| OPS-01 | Operator cockpit and deterministic invariants | Failures can be hard to classify | Error taxonomy, rule-based attribution, row-safe diagnostics | Summarize redacted evidence and rank hypotheses | No production repair or invasive forensics |
| OPS-02 | Runtime topology/build-ID verifiers | Logs span several processes | Deterministic probes and dependency graph | Explain a failed topology branch | Verifier remains pass/fail authority |
| OPS-03 | CI/static authority scans | New drift patterns are not encoded yet | AST/schema scans, SAST, property tests | Review diffs and propose permanent gates | AI finding is advisory until encoded and allowlisted |
| OPS-04 | Worker outcomes and queues | Repeated failures are noisy | Durable jobs, leases, DLQ, anomaly detection | Cluster redacted failures and draft replay plan | No retry/replay authority |
| OPS-05 | Security audit | Incident evidence can be complex | SIEM rules, DLP, anomaly detection, human commander | Summarize already-redacted events | Security data never enters behavioral inference |
| OPS-06 | Export/delete registry | Schema coverage may drift | Generated registry checks and purge receipts | Compare schema descriptions and explain receipt | No retention/redaction/delete decision |
| OPS-07 | Integration errors | Provider-specific failures are obscure | Error-code registry and retrieval-grounded runbooks | Draft user/operator explanation | Never receive credentials, tokens or raw export |
| OPS-08 | Accessibility/localization | Approved meaning may be hard to express clearly | Design system, translation memory, human review | Draft plain-language/localized variants | Semantic equivalence and accessibility review |
| OPS-09 | Documentation authority | Stale plans can mislead agents and humans | Archive/status metadata and static reference scan | Detect contradictions and draft reconciliation | AI cannot promote a parked document |
| OPS-10 | Test generation | Edge-case combinations exceed hand-written cases | Property/model-based tests, fuzzing, combinatorial generation | Propose adversarial fixtures from code/docs | Generated tests require deterministic oracle |
| OPS-11 | Incident/postmortem synthesis | Evidence is distributed across logs/artifacts/issues | Timestamped evidence manifest and correlation IDs | Draft timeline and unresolved questions | Human owns causality and corrective action |
| OPS-12 | Product support | Users need explanations without hidden actions | Searchable docs, diagnostic codes, escalation | Retrieval-grounded answer draft | No account mutation or behavioral attribution |

### 5.7 Evidence status for the catalogue

The `Current substrate` column names either an implemented owner, a partial
surface, or the nearest documented prerequisite. It does not imply every row
already has runtime support.

| Candidate area | Status on 2026-07-11 | Repository evidence |
| --- | --- | --- |
| CAP-01 through CAP-04, CAP-08 through CAP-10 | Implemented/partial | `brain_dump_parser.py`, `deadline_heuristic.py`, `task_manager.py`, Moodle/iCal normalizers and brain-dump tests |
| CAP-05 through CAP-07 | Absent or decorative/documented | Disabled link/voice controls, parked provider docs, dependency proposal contract |
| PLN-01 through PLN-03, PLN-06 through PLN-10 | Implemented/partial | `academic_pressure.py`, Pressure Map UI, calendar/task state and `academic_pressure_map_contract.md` |
| PLN-04 and solver portions of PLN-07/PLN-10 | Absent | No production feasibility/placement optimizer exists |
| EXE-01 through EXE-08 | Implemented/partial | Stopwatch manager/store/state machine, pause/resume predictors, correction and recovery tests |
| REC-01 through REC-10 | Partial/documented | Re-entry queue, notification/output surfaces, `stale_session_recovery_policy.md`, literature map and future `RecoveryEpisode` contract |
| INS-01 through INS-05, INS-07 through INS-08, INS-11 through INS-12 | Implemented/partial | Cortex, clean profiles, analytics generators, ClaimCompiler, archetype/cascade services, feedback and public copy |
| INS-06, INS-09 and INS-10 | Documented, not runtime | Future `HypothesisSet`, literature ledger expectations and `ExperimentRegistry` contract |
| OPS-01 through OPS-07 and OPS-09 through OPS-11 | Implemented/partial | Operator services, topology/CI scans, workers, security audit, user-data registry, refactor ledger and evidence manifests |
| OPS-08 and OPS-12 | Partial/mostly absent | Existing static copy and support docs; no complete localization/accessibility or product-support reasoning substrate |

Before implementation, each candidate must replace this grouped survey with
exact owner refs and an `implemented`, `partial`, `documented`, or `absent`
status in its approved seam.

### 5.8 Highest-leverage compounding loop

The goal is not to scatter small AI conveniences across the app. The dramatic
product gain comes from six bounded augmentations that compound while sharing
one provenance chain:

1. **Capture completeness:** semantic parsing adds missed obligations,
   decompositions and relation candidates to the editable deterministic
   preview.
2. **Pressure fidelity:** admitted structure plus retrieval/statistical ranges
   yields better missing-variable questions and solver-ready constraints.
3. **Executable planning:** constraint solvers produce feasible alternatives;
   reasoning explains tradeoffs and the user confirms one plan.
4. **Continuity during execution:** exact state, anomalies and suspended-goal
   context produce a concise, factual re-entry packet instead of generic copy.
5. **Literature-bound intervention and recovery:** deterministic policy owns
   eligibility, burden and timing; reasoning selects no action but can realize
   an approved option in context-sensitive language and propose missing
   recovery alternatives for review.
6. **Evidence compounding:** invocation, candidate, confirmation, canonical
   mutation, browser-rendered stimulus, interaction and later outcome remain
   linked. Competing-hypothesis synthesis improves, while repeatable residual
   wins are distilled back into the no-runtime baseline.

```text
messy input
-> richer confirmed structure
-> more faithful pressure model
-> feasible confirmed plan
-> cleaner execution and interruption evidence
-> more useful bounded recovery
-> reconstructible exposure and outcome
-> better hypotheses and deterministic distillation
```

This is the priority path. Low-leverage AI copy, generic chat, novelty features
and operator convenience must not displace work that strengthens this loop.

## 6. Explicit No-AI Zones

AI is structurally inferior or too dangerous for:

- authentication, authorization, tenant scope, operator-role checks, and
  credential/profile binding;
- transaction boundaries, idempotency keys, canonical deduplication, and state
  transition validity;
- provider completion truth, authoritative task/deadline state, timer
  finalization, or exposure lifecycle truth;
- clean-data admission, metric definitions, units, sign conventions,
  denominators, exclusion rules, and experiment randomization;
- confidence creation, causal promotion, sensitive behavioral labels,
  identity claims, diagnosis, or medical/clinical personalization;
- consent, privacy classification, retention, export completeness, deletion,
  provider revocation, or production-data repair;
- notification eligibility, quiet hours, burden ceilings, refractory periods,
  no-treatment decisions, or kill switches;
- automatic task creation, scheduling, rescheduling, recovery mutation,
  acknowledgment, dismissal, or irreversible action;
- deployment, restart, rollback, migration, worker replay, or incident command;
- public publication or automatic response to user feedback.

An AI system may explain a deterministic result in some of these domains, but
the explanation must not be confused with the result and must not receive the
secret or private material the result protects.

## 7. Structured Invocation Classes

Every future invocation must declare one class. Free-form "assistant" access is
not an invocation class.

| Class | Allowed output | Maximum visibility | Examples |
| --- | --- | --- | --- |
| `semantic_parse_candidate` | Fields plus evidence spans | Editable preview | Brain dump, import mapping |
| `relation_candidate` | Typed edge plus support/contradiction | Editable preview | Parent-child or dependency proposal |
| `estimate_assumption_candidate` | Range assumptions, never confidence | Shadow or explicit suggestion | Cold-start duration semantics |
| `hypothesis_expansion` | Competing hypotheses and missing variables | Shadow by default | Insight synthesis |
| `evidence_summary` | Referenced, bounded summary | Compiler-controlled | Longitudinal packet summary |
| `recovery_option_candidate` | Option from allowed action vocabulary | Policy-controlled suggestion | Resume/shrink/split/reschedule |
| `wording_realization` | Text preserving approved semantic slots | Registered surface only | Recovery/reminder wording |
| `operator_diagnostic_draft` | Ranked causes and next read-only checks | Operator only | CI/topology/queue triage |
| `distillation_candidate` | Proposed rule/test/lexicon/feature | Never user-visible directly | Free-tier improvement pipeline |
| `semantic_query_candidate` | Allowlisted read-only query AST plus evidence refs | Scoped results preview | Search/Table query |
| `provider_normalization_candidate` | Provider-neutral fact retaining source provenance | Import preview/operator quarantine | Provider edge cases |
| `feedback_synthesis` | Source-linked themes, duplicates and reproduction hints | Operator only | Feedback triage |
| `support_answer_draft` | Retrieval-grounded explanation with escalation | User-visible after validation | Integration/product support |
| `localization_accessibility_review` | Meaning-preserving variant and detected barriers | Human-reviewed draft | Locale, RTL, readability, accessibility |
| `simulation_scenario_candidate` | Adversarial trace or fixture | Test-only | LyraSim/property testing |
| `repository_review_draft` | Cited contradiction, authority or CI finding | Developer/operator only | Docs/code/static review |
| `privacy_receipt_explanation` | Plain-language explanation of canonical receipt | User-visible after validation | Export/delete/retention status |

Every class needs a JSON schema, input privacy class, retention policy, maximum
claim risk, timeout, retry limit, fallback, validator, allowed consumer, and
explicit statement that no tools or mutations are available.

AI-generated LyraSim traces are adversarial test candidates only. They are not
empirical observations, construct validation, user evidence, or a product
oracle; deterministic simulators and scorers decide whether a scenario is
well-formed and what invariant it exercises.

### 7.1 Privacy and lifecycle ownership

The user-data registry covers current database and runtime state; it does not
yet cover a future reasoning/evaluation plane. Before any shadow invocation,
the ownership manifest must account for:

- input packets, prompts and structured outputs;
- exact or reconstructible rendered stimuli;
- embeddings, indexes, caches and retrieval artifacts;
- evaluator labels, adjudication records and distillation corpora;
- adapter/vendor logs, retries, dead letters and quota records;
- model, runtime, prompt, policy and capability provenance;
- derived rules, priors and fixtures whose source rows are later withdrawn.

Each artifact needs an owner, privacy class, consent basis, export behavior,
retention window, withdrawal semantics, deletion/purge path, external receipt
or unresolved-copy status, and downstream distillation impact. Account deletion
currently can retain research rows by default and durable DB deletion can finish
before Redis purge succeeds; those existing boundaries must be resolved or
explicitly carried into any future runtime contract.

Feedback synthesis has an additional boundary: current feedback can fan user
text and identity toward operator channels. Redaction, prompt-injection
isolation, tenant scope, consent and deletion propagation must precede any
reasoning over that text.

### 7.2 Accessibility and localization

Every visible invocation class must declare locale, timezone/date semantics,
reading level, action-label parity and screen-reader behavior. RTL layout,
translation-memory provenance, cognitive readability and semantic-equivalence
tests are part of the surface contract. A fluent translation is not acceptable
if it changes uncertainty, claim ceiling, action meaning, burden or safety copy.

## 8. Evaluation And Promotion

### 8.1 Baseline-first evaluation

AI must be evaluated against the strongest appropriate non-AI baseline, not
against an intentionally weak heuristic.

For each candidate record:

- deterministic baseline version;
- retrieval/solver/statistical/classical-ML baseline where applicable;
- eligible cases and abstentions;
- baseline-only correct cases;
- AI-only correct candidates;
- agreement and disagreement;
- user corrections;
- privacy or authority violations;
- latency, quota and failure rate;
- downstream outcome window only when the design supports it.

### 8.2 Promotion ladder

```text
documentation candidate
-> offline fixture evaluation
-> operator-only review
-> cohort-sponsored shadow mode
-> adjudicated residual-lift report
-> separately approved visible preview
-> registered exposure-complete experiment
-> evidence-backed promotion, demotion, or retirement
```

No stage is skipped because output appears fluent. A candidate can also be
distilled into the deterministic layer instead of becoming a runtime feature.

### 8.3 Minimum promotion evidence

- measurable residual improvement over a named baseline;
- no regression on baseline-correct or safety-critical cases;
- useful abstention behavior;
- output-schema and evidence-reference validity;
- cross-user isolation and prompt-injection resistance;
- exact model/runtime/prompt/policy version provenance;
- deterministic fallback under timeout, quota, revocation and malformed output;
- browser-proven exposure for any visible output;
- explicit correction and later-outcome capture;
- rollback and kill path;
- no new claim authority hidden inside wording.

## 9. Complete No-Runtime Baseline And Possible Free Packaging

Regardless of later packaging, the deterministic no-runtime baseline must be a
complete execution product for research and honest fallback, not a crippled
advertisement for AI. Its minimum durable value is:

- capture and import into editable canonical previews;
- obligation-aware planning and an honest pressure map;
- calendar placement and one-active-timer execution;
- interruption-safe recovery with executable choices;
- corrections, export/delete, privacy and provenance;
- deterministic summaries whose evidence and limits are visible.

AI can improve that baseline through four bounded pipelines:

1. **Residual discovery:** shadow review finds where parsers, rules, templates,
   tests, or statistical features miss recurring cases.
2. **Artifact distillation:** reviewed misses become deterministic lexicons,
   guards, templates, priors, constraints, fixtures, or classical models.
3. **Quality assurance:** AI proposes adversarial tests and contradiction scans;
   deterministic oracles decide whether they pass.
4. **Documentation and copy refinement:** reviewed wording becomes a versioned
   static template with no runtime dependency.

No-runtime users may not receive a lower-integrity fallback. If an AI-only
feature is unavailable, LyraOS shows the deterministic product state, not
fabricated language or a hidden founder-account fallback.

Whether this baseline becomes a permanent free tier, a trial, a research
entitlement, or part of another package is an unresolved founder/business
decision. This concept note has no pricing authority.

## 10. Runtime Funding And Product Entitlement

Product entitlement, runtime funding, runtime connection, and research
assignment remain independent state machines. This map does not decide price.

One possible staged posture, not an approved packaging decision, is:

| Stage | Product | Runtime | User-visible AI |
| --- | --- | --- | --- |
| No-runtime baseline | Complete deterministic execution loop | None | None |
| Research-preview Pro U1 | Pro-shaped deterministic product | None | None |
| Research-preview Pro U2 | Same product | Founder/cohort-sponsored isolated runtime | Shadow only |
| Research-preview Pro U3 | Same product | Cohort-sponsored isolated runtime | Separately approved bounded preview |
| Later commercial/institutional | Free, Pro, or institution entitlement | User-connected, institution-sponsored, or later approved funding | Capability and consent dependent |

Founder-sponsored runtime is temporary research custody, not "LyraOS uses the
founder account." The product boundary remains `ReasoningRuntimeContract`; the
adapter, funding source, and connection mode must be replaceable.

### Packaging principles

- **Possible Free** would include the complete deterministic execution loop,
  basic bounded descriptive summaries, correction, provenance, consent,
  export, and delete.
- **Pro** may later sell depth, convenience, richer history, semantic
  assistance, and bounded synthesis. It must not sell correctness, data rights,
  or relief from intentionally degraded deterministic behavior.
- **Institution** may later fund cohort provisioning, integrations, support,
  governance, privacy-safe aggregate service design, and sponsored runtime. It
  must not become individual student risk scoring or surveillance.
- **Research-preview Pro** is temporary validation packaging. It is neither a
  price commitment nor evidence that AI permanently belongs in Pro.

Reasoning connection itself need not define Pro forever. A later plan may test
user-connected reasoning for free or paid users independently of product
entitlement. This remains unresolved; no code currently implements any of the
four entitlement/funding/connection/assignment state machines.

### Value and economics to measure before pricing

Product value metrics should include time to first clean loop, complete-loop
rate, return under pressure, time to next action after drift, resolved recovery
episodes, repeated clean loops, and reported usefulness/trust.

Reasoning contribution metrics should include incremental accepted candidates
over the strongest baseline, correction/rejection rate, unsupported additions,
agreement/disagreement, later support, abstention, latency, quota exhaustion,
and cost per accepted incremental contribution.

Institutional reporting should remain opt-in and aggregate: cohort activation,
unresolved-load reduction, support burden, and recovery utility. It must not
publish individual productivity, motivation, focus, worth, or risk scores.

Founder sponsorship is research expense with a sunset. Institution
sponsorship is a contracted cohort budget. User-connected runtime can move
model consumption outside LyraOS billing, but LyraOS still bears adapter,
validation, audit, privacy, and support costs. No business model is credible
until deployment/operator labor and those non-model costs are measured.

Sponsor-funded runtime requires allowlisted cohorts, global and per-subject
budgets, concurrency/payload limits, bounded retries, idempotent invocation
IDs, explicit quota outcomes, isolation, kill switches, and a visible return
to the deterministic product. It may never silently switch to another user,
provider, profile, or funding source.

## 11. Prerequisite Sequence

1. Finish the current deterministic refactor and preserve documented behavior.
2. Correct existing render/exposure gaps and register behavior-shaping client
   surfaces.
3. Make brain dump, pressure-map corrections/plans, execution, and recovery
   useful without AI.
4. Centralize metric, confidence, provenance and clean-data semantics.
5. Define minimal relation, EvidencePacket, HypothesisSet, RecoveryEpisode,
   DecisionRecord, ExposureLifecycle, OutcomeWindow and invocation contracts.
6. Build offline corpora and deterministic baselines; do not add runtime calls.
7. Establish cohort consent, isolation, retention, quota and kill protocols.
8. Run founder/cohort-sponsored shadow evaluation through the abstract runtime
   boundary.
9. Distill repeatable residual improvements into no-runtime deterministic
   artifacts.
10. Request a new plan before any user-visible AI, experiment, schema, adapter
    wiring, or commercial entitlement change.

## 12. Repository Contradictions To Resolve Before Runtime AI

- Public copy and historically named `llm_*` fields/components can imply a
  direct model path even though active NIM/Ollama enrichment is retired.
- Some client-only Pulse insight/recovery surfaces shape behavior without full
  output-surface registration and render/outcome correlation.
- Current confidence language mixes sample-size tiers, heuristic scores,
  posterior-like values and probabilities.
- Pressure-map coverage questions are not yet canonical correction commands;
  some recovery options remain labels rather than executable actions.
- The reasoning-runtime/ClaimCompiler ordering must be expressed consistently:
  admission and deterministic evidence precede reasoning; reasoning returns a
  draft; compiler and surface policy decide publication.
- Historical provider, AI and planning docs must not authorize runtime paths.
- Runtime security, tenancy, quota, credential, export/delete and adapter purge
  contracts remain prerequisite work, not AI features.
- Brain-dump documentation now records that manager-owned per-item commits
  intentionally permit partial success; transaction ownership remains a
  characterized prerequisite before any atomicity refactor.
- Brain-dump preview carries category/duration source metadata that is not
  durably preserved through canonical commit, risking provenance collapse.
- The deprecated parse path still encourages a direct create path whose source
  can default to `manual`; future AI-origin candidates must use the same
  explicit preview/confirmation boundary as ordinary capture.
- Provider matching and import skip telemetry have under-characterized greedy,
  malformed, recurring and missing-course cases; classical matching and
  quarantine come before AI adjudication.
- Stopwatch DB/Redis transitions and stale-recovery policy contain split-truth
  and documentation-drift risks that must be closed before AI explains them.
- Public copy, historically named `llm_*` storage and a remaining LLM-labelled
  chip can imply model execution after direct enrichment retirement.
- Entitlement, runtime funding, runtime connection and research assignment are
  concept-only state machines today; privacy, terms and cohort policy must not
  describe them as shipped.
- Public JSON-LD currently advertises a zero-price offer while Terms reserve
  future pricing. Packaging and permanent-free claims require one explicit
  founder decision before public-copy alignment.
- Account deletion may retain research rows by default, and Redis/runtime purge
  can fail after durable DB deletion. Future prompts, indexes, labels, caches,
  vendor logs and distillation corpora cannot be added until deletion and
  external purge receipts cover them.
- Feedback can fan user-authored content and identity into operator channels.
  Redaction, prompt-injection isolation, tenant boundaries, consent and
  deletion propagation must precede AI feedback synthesis.
- Current negative retirement gates can miss a renamed generic provider client
  or alternate outbound path. Runtime reintroduction prevention needs broader
  import/config/dependency/outbound-host coverage before any adapter seam.
- No executable evaluation plane exists for frozen baselines, blinded labels,
  adjudication, runtime epochs, model invocation, distillation or comparative
  residual-lift reports.

## 13. Deliberately Unresolved Founder Decisions

This survey does not choose:

- the first runtime AI use case;
- whether the first visible use is parsing, recovery wording, or synthesis;
- a price, quota, Pro bundle, or institution contract;
- the final adapter hosting or user-connection UX;
- task-relation schema or general dependency graph;
- the first intervention family or recovery mechanism;
- prompt wording, model route, fine-tuning, online learning, or policy learning;
- retention of exact prompts versus redacted reconstructible stimuli;
- cohort size, experimental design, promotion threshold, or generalizability.

## Hard Stop Repeated

This is an initial repository-wide survey, not a claim of exhaustiveness and
not authorization to implement any candidate. It authorizes no code and does
not expand the active freeze sequence. Deterministic refactor, contract work,
literature review, fixture/baseline construction, documentation alignment and
runtime AI remain subject to `docs/current_transition_state.md`, founder
approval, and a new scoped plan where required.
