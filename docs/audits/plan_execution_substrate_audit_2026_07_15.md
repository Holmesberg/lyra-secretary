# Plan-Execution Substrate Audit

---
authority: audit-evidence
may_authorize_code: false
runtime_owner: none
status: static repository audit; findings require focused confirmation
product_name: LyraOS
schema_authority: none
metric_authority: none
model_authority: none
required_final_reviewer: founder
audit_date: 2026-07-15
audited_head: a134c1b81c590b1aca8b34eb620191092f35b122
---

## 1. Purpose And Scope

This audit maps the current repository against the proposed plan-execution
dynamics ontology.

It answers:

- which user-facing and substrate features currently exist;
- which are shipped, partial, dead, historical, or parked;
- which data can support plan-execution computation;
- which redundancies are harmful and which are intentional compatibility;
- which defects could contaminate future labels;
- what cannot be reconstructed without a new conceptual or schema primitive.

This was a static read-only audit of a clean `main` checkout at the SHA above.
It did not run the backend suite, frontend build, browser verification, hosted
public proof, production telemetry, or external-consumer discovery.

Therefore:

- `shipped` means mounted and end-to-end in this checkout, not live-public
  proof;
- `finding` means source-grounded audit evidence, not a closed bug;
- `computable` means the required observables appear to exist, not that the
  metric is validated or authorized;
- archived documents provide lineage only and cannot authorize work.

## 2. Executive Findings

1. LyraOS already contains most raw ingredients for a plan-execution evidence
   system: plans, deadlines, stopwatch sessions, pauses, corrections, provider
   candidates, exposures, notifications, recovery paths, and outcomes.
2. The missing center is an immutable, accepted, versioned plan. `Task` is a
   mutable lifecycle aggregate; rescheduling overwrites planned fields.
3. Current data can support a restricted latest-plan-versus-clean-execution
   projection, not historical plan-quality reconstruction.
4. Several metric and projection conventions conflict, including `E/P`,
   `E-P`, legacy `P-E`, raw execution, corrected execution, and clean
   calibration.
5. Some user-facing computations are owned locally by the frontend rather than
   by a registered metric authority.
6. Exposure infrastructure is strong but incompletely adopted; some paths
   still risk treating server-side reads as render truth.
7. The most dangerous redundancies are semantic, not file-size related:
   multiple lifecycle-policy owners, multiple projection meanings, and
   overlapping exposure representations.
8. Two static findings could directly corrupt future training labels: caller-
   selected task creation state and the inverted Pulse `Wins` delta test.

## 3. Current Entity And Event Graph

```text
User
  -> Task
       -> StopwatchSession
            -> PauseEvent
       -> TaskExecutionCorrection
       -> CalibrationNudgeEvent
       -> ReflectionViewLog
       -> PausePredictionLog
       -> ResumePredictionLog
       -> optional Deadline
            -> DeadlineCompletionEvent
            -> TaskDeadlineOutcome

Provider identity
  -> Deadline candidate or imported deadline
  -> completion candidate

ExposureDecisionEvent
  -> ExposureRenderEvent
  -> ExposureAckEvent
  -> NotificationLifecycleEvent
  -> SuppressionEvent
  -> ExposurePolicyEffectLog

Raw rows
  -> clean-profile admission and exposure gate
  -> Cortex derived evidence
  -> EvidencePacket
  -> ClaimCompiler and surface policy
  -> registered user-facing output
```

Hard joins include `task_id`, `session_id`, `deadline_id`, `exposure_id`, and
provider `(user_id, external_source, external_id)`. Notification and legacy
exposure associations are sometimes optional or soft.

## 4. Feature Inventory

Legend:

- `shipped`: mounted current workflow with canonical backend path;
- `partial`: mounted or implemented, but important parity/proof is incomplete;
- `dead`: code remains but no mounted current workflow exists;
- `historical`: retained for lineage or compatibility, not current product;
- `parked`: explicitly not authorized or implemented;
- `latent`: backend path exists without a first-party mounted workflow.

### 4.1 Platform, Identity, Consent, And Onboarding

| Feature | State | Current behavior | Plan-execution relevance |
| --- | --- | --- | --- |
| Google sign-in and session gate | shipped | NextAuth plus backend bearer identity provisions user-scoped state | Establishes user and tenancy scope; not behavioral evidence |
| Sign-out and app-shell route gate | shipped | Mounted global controls | Session boundary only |
| Terms and privacy | shipped | Public legal pages and accepted timestamp | Governance context; not plan cost |
| Research consent | shipped | Optional research-consent timestamp and retention behavior | Determines research admissibility, not outcome quality |
| Brain Dump onboarding | partial | Write-free parse, editable preview, explicit commit | Creates candidate obligations and plans; failed-row continuity is incomplete |
| Archetype survey | partial | Submit, skip, retake, assignment history | Provisional cold-start prior only; not identity truth |
| Archetype profile reveal | partial | Insights proximity/reveal surface | Exposure-sensitive meta-inference; render parity incomplete |
| Tutorial overlay | dead | Forced off in current layout | No preservation requirement beyond historical evidence |
| Activation email | partial/config-gated | Provisioning path exists; disabled by default | Transactional lifecycle only unless copy becomes behavior-shaping |

### 4.2 Capture, Obligations, And Planning

| Feature | State | Current behavior | Plan-execution relevance |
| --- | --- | --- | --- |
| New Task | shipped | Create and edit title, time, duration, category, description | Primary mutable plan representation |
| Custom categories | shipped | User-defined string category | Candidate context feature; high-cardinality risk |
| Exact-once task submission | shipped | Frontend lock plus backend Redis reservation | Prevents duplicate plan hypotheses |
| Conflict detection and override | shipped | Executing conflicts block; planned/paused overlaps can be forced | Captures user-accepted overlap, not proof of feasibility |
| Deterministic deadline suggestion | shipped | Candidate scoring; explicit confirmation binds | Candidate plan context with legacy `llm_*` storage |
| Deadline workspace | shipped | Create, edit, void, state transitions, binding correction | Obligation and due-time authority |
| Deadline completion events | shipped substrate | Canonical and candidate completion evidence | Outcome evidence, not stopwatch execution |
| Global undo | shipped | Restores supported task/session mutations through Redis undo state | Reversibility and mutation lineage |
| Minimal floating quick-add | historical | Dedicated old surface no longer mounted | No current product authority |
| Deprecated `/parse` | compatibility | Legacy parse route retained | Preserve until callers are disproved |

### 4.3 Orientation And Workspaces

| Feature | State | Current behavior | Plan-execution relevance |
| --- | --- | --- | --- |
| Pulse hub | partial | Composes capture, execution, pressure, recovery, and summaries | Primary loop hub; contains local metric authority drift |
| Today | shipped | Plan and execute current work, corrections, retroactive entry | Canonical execution workflow |
| Calendar day/week/month | partial | Inspect and reschedule tasks; drag/resize path | Mutates latest plan but does not preserve plan versions |
| Deadlines | shipped | Inspect obligations and repair bindings | Deadline outcome context |
| Table | shipped | Filter, audit, export, correct execution | Effective user-history projection |
| Pressure Map | partial | Read-only ranges, coverage, uncertainty, confirmed task draft | Candidate plan comparison surface; not capacity truth |
| System Insight chart | partial/local | Client calculation from task query | Unregistered metric semantics and weak dedicated coverage |
| Recovery Rhythm chart | partial/local | Client calculation from task query | Descriptive only; not recovery success |
| Approximate free block | partial/local | Task-only interval gap in Pulse | Not calendar-complete or capacity authority |

### 4.4 Execution And Correction

| Feature | State | Current behavior | Plan-execution relevance |
| --- | --- | --- | --- |
| Stopwatch start | shipped | Opens one active session and task execution | Observed execution begins, subject to provenance |
| Pause and explicit reason | shipped | Records paused state and append-only `PauseEvent` | Interruption evidence; reason is selected/self-reported |
| Resume | shipped | Continues paused session | Re-entry event |
| Switch | shipped | Pauses parent and starts child task/session | Creates interruption topology and possible overlapping occupancy |
| Stop | shipped | Finalizes active duration and outcome fields | Execution evidence; optional outcome fields limit interpretation |
| Stale resolution | shipped/partial | Explicit and automatic recovery paths | Recovered traces require distinct quality class |
| Execution correction | shipped | Append-only correction sidecar | Effective history changes; raw observation remains |
| Retroactive work entry | shipped | User reports earlier work | Self-reported/reconstructed; excluded from clean calibration |
| Google-event attendance | shipped, weakly covered | Records attended/missed/unknown external event | External outcome, not task execution |
| Future-task warning | latent | Backend response exists without mounted UI | No user-visible preservation requirement yet |

### 4.5 Recovery And Re-Entry

| Feature | State | Current behavior | Plan-execution relevance |
| --- | --- | --- | --- |
| Re-entry queue | partial | Resume, resolve, done, drop, reschedule | Recovery proposal/action surface |
| Retroactive confirmation | shipped | Resolve stale or missed evidence explicitly | Reconstructed evidence with contamination flags |
| Shrink | missing/partial contract | Documented concept, no complete direct action | Candidate future plan transformation |
| Split | partial | Pressure Map preview can create blocks; re-entry parity incomplete | Candidate plan transformation |
| Mark irrelevant | missing | Documented recovery outcome not directly represented | Needed to distinguish unresolved from no-longer-relevant |
| Keep/park | partial | State can remain paused/planned, but explicit outcome parity is weak | Recovery semantics remain distributed |
| Interruption-chain visualization | parked | No current mounted feature | Future diagnostic only |

### 4.6 Predictions, Notifications, And Behavior-Shaping Outputs

| Feature | State | Current behavior | Plan-execution relevance |
| --- | --- | --- | --- |
| Creation nudge | shipped/partial proof | Suggests duration adjustment; Use/Keep | Changes accepted estimate and contaminates later calibration |
| Stop micro-mirror | partial | Bounded deterministic stop result | Exposure-sensitive interpretation |
| Calibration nudge | partial | Suggestion plus accept/dismiss event | Intervention context, not independent user estimate |
| Pause prediction | partial | Scheduled predictor and generic notification | Existing behavior-shaping family; exposed history differs from baseline |
| Resume prediction | partial | Scheduled predictor and bounded reminders | Existing family; eligibility distinct from pause |
| Rich pause action banner | dead | Component remains unmounted | Generic notification is the shipped surface |
| Rich resume action banner | dead | Component remains unmounted | Generic notification is the shipped surface |
| Web notifications | shipped | Redis queue plus durable lifecycle and browser ACK | Delivery/render/outcome substrate |
| Reminders | shipped | Scheduled task reminders | High scheduling exposure |
| Timer overflow | shipped | Warns after accepted duration plus buffer | Execution intervention |
| Task-end prediction | historical/unshipped | No current user workflow | Must remain parked |
| Next-task readiness | parked | Not implemented | New prediction family; forbidden during freeze |

### 4.7 Insights, Measurement, And Operator Surfaces

| Feature | State | Current behavior | Plan-execution relevance |
| --- | --- | --- | --- |
| Deterministic Insights | partial | Fifteen generators plus synthesis/packaging | Descriptive and hypothesis outputs; some render paths incomplete |
| Archetype proximity | partial | Likelihood-based execution proximity | Provisional meta-inference, not identity posterior |
| Cortex | shipped substrate | Read-only evidence and clean-profile projection | Canonical derived-feature boundary |
| ClaimCompiler | shipped substrate | Bounded claim packaging | Does not verify all underlying row lineage itself |
| Exposure Ledger | shipped substrate, partial adoption | Decision, render, ACK, suppression, policy logs | Required to separate system participation from baseline |
| Operator cockpit | shipped/partial trust | Read-only readiness and integrity diagnostics | System quality, not individual outcome cost |
| LyraSim | shipped test substrate | Deterministic authority/contamination scenarios | Tests invariants, not human behavior validity |
| Feedback | shipped | User bug/feedback modal and backend storage | Product evidence; not behavioral outcome by default |
| Feedback administration | latent | List/resolve backend APIs without mounted admin UI | Operational only |

### 4.8 Integrations, Export, And Deletion

| Feature | State | Current behavior | Plan-execution relevance |
| --- | --- | --- | --- |
| Google Calendar | partial | OAuth, event reads, attendance evidence | Commitment context; events are not execution truth |
| Moodle iCal | shipped | Imports deadlines with provider provenance | Obligation structure |
| Moodle Web Services | partial | Submission/completion candidates | Candidate outcome only |
| Integration freshness | shipped | Connection and sync-state summaries | Observation quality and missingness |
| JSON export | shipped | Registry-driven user data export | Strongest current raw analysis source, snapshot semantics undocumented |
| CSV export | shipped | User-facing task/session summary | Capped and lossy; insufficient as research source |
| Account deletion | shipped | Registry-driven hard delete or retained anonymization | Retention and research admissibility |
| Direct model runtime | historical | Provider runtime retired | Historical fields remain for lineage/export/delete |
| Provider expansion | parked | No new adapters authorized | Not part of current plan-execution work |

## 5. Data Evidence Classes

### 5.1 Recorded planning hypotheses

Current `Task` fields include:

- planned start and end;
- planned active duration;
- title, category, and description;
- scope bullet count at plan;
- source and confidence fields;
- deadline binding and match provenance;
- reschedule count;
- interruption parent and type;
- readiness and reflection fields.

These describe the current mutable task plan. They do not reconstruct every
accepted historical version.

### 5.2 Application-observed execution

Current evidence includes:

- stopwatch start and end;
- active duration;
- wall duration;
- pause start, resume, duration, reason, and initiator;
- session and task relations;
- deadline snapshots;
- browser exposure events.

Observation becomes weaker when data is retroactive, auto-closed, recovered,
corrected, timestamp-imputed, or provider-derived.

### 5.3 Self-reported evidence

Examples include:

- completion percentage;
- scope outcome;
- readiness and reflection;
- retroactive work;
- attendance confirmation;
- selected pause reason;
- correction values.

Self-report is evidence. It must not be mislabeled as direct instrument
observation.

### 5.4 Derived or inferred evidence

Examples include:

- active and wall deltas;
- execution multiplier;
- topology hypothesis;
- deadline candidate scoring;
- pressure intervals;
- archetype proximity;
- pause and resume predictions;
- provider fuzzy matches;
- exposure admission status.

Derived values require a method version and remain recomputable. Inferred
values require a claim ceiling and competing explanations.

## 6. Main Structural Blocker: No Accepted Plan Version

`Task` currently combines:

- the latest plan;
- lifecycle state;
- mutable content;
- execution summary;
- outcome and inference fields.

`TaskManager.reschedule_task` overwrites planned start, end, duration, title,
category, description, and deadline-related fields, then increments
`reschedule_count`. The magnitude and content of prior plan versions are lost.

Consequences:

- historical plan churn cannot be measured exactly;
- the plan accepted at execution start may be unknown;
- a later edit can change the apparent planning hypothesis;
- candidate-plan comparison lacks a stable training label;
- plan survival and transformation lineage cannot be reconstructed;
- cascade analysis cannot reliably attach downstream movement to the plan that
  preceded it.

Current no-schema analyses must say `latest_plan_compatibility`, not historical
plan quality.

## 7. Projection Drift

At least three legitimate projections exist:

| Projection | Current examples | Risk |
| --- | --- | --- |
| Raw observation | Original Task/session values | Can preserve known errors or stale recovery artifacts |
| Effective user history | Query/Table/Pulse apply latest correction | Can be mistaken for clean measured execution |
| Clean calibration | Cortex excludes corrected/retroactive/dirty rows | May differ from what the user sees in history |

Calendar and legacy analytics do not consistently use the same effective
projection as Query/Table/Pulse. This is harmful only when consumers fail to
name the projection they intend.

Append-only correction sidecars are intentional and should remain.

## 8. Ranked Redundancies And Semantic Risks

### 8.1 Harmful or high-risk overlap

| Rank | Overlap | Why it matters |
| --- | --- | --- |
| 1 | Mutable plan and execution summary in `Task` | Erases accepted plan history and destabilizes labels |
| 2 | `E/P`, `E-P`, and legacy `P-E` | Reverses signs and user-facing interpretations |
| 3 | Raw, effective, and clean actuals | Consumers silently answer different questions |
| 4 | StateMachine, StopwatchManager, recovery jobs, endpoint orchestration | Transition legality and side effects have several semantic owners |
| 5 | Pulse local metrics versus backend/Cortex metrics | Frontend can create unregistered behavioral claims |
| 6 | Multiple exposure-related event stores | Complete system participation requires cross-store reconstruction |
| 7 | Active deterministic inference in retired `llm_*` namespace | Provenance and confidence semantics become misleading |
| 8 | Generic integration status built from provider-specific User fields | Connection and provenance state can disagree |
| 9 | Recovery state spread across task, session, pause, stale jobs, and UI | No complete recovery episode or terminal outcome |
| 10 | Pressure computation in backend and recovery-block planning in frontend | Estimate method and user-facing action can drift |

### 8.2 Intentional compatibility to preserve until disproved

- raw observations plus append-only corrections;
- deprecated parse and notification compatibility routes;
- query `date`/`day` compatibility;
- Schedule-X runtime shim;
- historical Jarvis and model-era rows needed for export/deletion/lineage;
- separate pause and resume predictor families;
- provider-specific User fields pending an approved connection model;
- historical documentation snapshots with explicit non-authorizing labels.

Large files or parallel modules are not redundant merely because they are
large or structurally similar.

## 9. Static Findings Requiring Focused Confirmation

### 9.1 Caller-selected creation state

`TaskCreateRequest` accepts `state`, `source`, and `confidence_score`. The
`/create` endpoint forwards those fields to `TaskManager.create_task`, which
persists the requested state directly.

Risk:

- a caller may create `EXECUTED`, `EXECUTING`, or `PAUSED` state without the
  expected transition, timestamp, or stopwatch evidence;
- downstream clean profiles could receive semantically invalid rows if other
  gates do not exclude them;
- future plan-execution models could learn from fabricated lifecycle labels.

The mounted frontend may submit only defaults. The public request contract
still requires a focused negative test before this finding is closed.

Relevant sources:

- `backend/app/schemas/task.py`;
- `backend/app/api/v1/endpoints/tasks.py`;
- `backend/app/services/task_manager.py`;
- `backend/app/services/state_machine.py`.

### 9.2 Pulse `Wins` sign inversion

The canonical legacy `Task.duration_delta_minutes` is:

```text
planned - executed
```

Positive means finished early. Negative means overrun.

`winsToday` currently increments when the effective or raw delta is `<= 0`.
Its comment says that means no overrun, but under the current property it means
exact duration or overrun. The function also treats null as zero.

Risk:

- the primary Pulse summary can reward overruns and exclude early completion;
- the user-facing interpretation conflicts with Cortex sign conventions;
- any future outcome label derived from `Wins` would be inverted.

Relevant sources:

- `backend/app/db/models.py`;
- `frontend/lib/pulse-aggregations.ts`;
- `frontend/components/pulse/PulseGreeting.tsx`.

### 9.3 Exposure admission weaker than browser-ACK doctrine

Some current exposure lookup/admission paths rely on render-row existence or
user/time/category matching rather than exact authenticated ACK correlation.

Risk:

- unrelated or premature render evidence can contaminate a calibration window;
- a server-created render row can be treated more strongly than browser truth;
- concurrent exposures can be collapsed into one diagnostic association.

This requires family-by-family focused verification, not a global rewrite.

### 9.4 Unreachable stale-recovery branch

The stale-session recovery job appears to continue paused sessions into an
explicit reflection path before a later automatic `EXECUTED` branch can run.
The later branch and its counter may therefore be historical/unreachable.

Risk is primarily maintainability and misleading behavior description, not
confirmed current data corruption.

## 10. Registry And Documentation Drift

The shipped-feature preservation registry omits or understates:

- global undo;
- feedback and bug reports;
- Google-event attendance;
- Pulse System Insight and Recovery Rhythm charts;
- authentication, legal, and session behavior;
- config-gated activation email;
- current Pulse partial-error handling.

Other drift:

- generic "pause and resume prediction surfaces" wording can imply the dead
  rich banners are shipped;
- Pressure Map action metadata names `POST /v1/tasks`, while canonical task
  creation is `/v1/create`;
- `docs/current_transition_state.md` names `refactor/freeze-closure` as active
  while this audited checkout is clean `main`;
- historical `daily_friction_score` and identity-heavy archetype language
  conflict with active measurement doctrine;
- provider and asset-velocity documents contain recoverable ideas but cannot
  authorize effort, completion, or execution inference.

## 11. Currently Defensible Restricted Projection

For rows that pass stronger analysis-time admission, LyraOS can describe:

```text
[
  start_lag,
  active_delta,
  log_execution_multiplier,
  wall_delta,
  pause_overhead,
  session_or_switch_count,
  completion_shortfall,
  scope_relation,
  deadline_displacement,
  explicit_recovery_latency,
  exposure_state,
  observation_quality
]
```

Required exclusions or strata include:

- no known accepted plan;
- synthetic one-hour immediate-start plan;
- retroactive `planned = executed` records;
- auto-closed and recovered traces;
- corrected rows for clean calibration;
- voided, anchor, operator, and synthetic test rows;
- incoherent timestamps;
- provider-native completion treated as execution;
- unknown or incomplete exposure context.

This is a descriptive vector. It has no validated weights, universal ranking,
causal meaning, or user-facing authority.

## 12. What Remains Unavailable

Without accepted plan versions:

- revision magnitude;
- plan survival;
- exact plan churn;
- accepted-plan sequence and bundle comparison;
- transformation lineage;
- revision-aware cascade analysis;
- historical candidate-plan risk;
- precise counterfactual scenario comparison.

Without stronger outcome evidence:

- work quality;
- learning or comprehension;
- whether an overrun was valuable;
- whether exact adherence was beneficial.

Without approved experiments:

- causal intervention effect;
- root cause;
- unprompted natural rhythm under exposed use;
- safe adaptive-policy learning;
- population-generalized thresholds.

## 13. Recommended Remediation Order

This is ordering advice, not implementation authority.

1. Focus-confirm caller-selected create-state behavior.
2. Focus-confirm and correct the Pulse `Wins` sign contract.
3. Name raw, effective, clean-calibration, and latest-plan projections.
4. Tighten clean-profile execution to match declared provenance requirements.
5. Finish browser-owned exposure truth for touched families.
6. Characterize timer/switch interval overlap and occupancy double counting.
7. Decide whether an accepted plan-version contract is necessary and obtain
   schema approval before implementation.
8. Only then evaluate a plan-dynamics computation or interpretable model.

## 14. Audit Limitations

- No runtime or hosted-public state was inspected.
- No external API consumers were enumerated.
- No browser path was exercised.
- No test suite or build was run for this audit.
- Local development data is unsuitable for behavioral prevalence or model
  validation; it may still support invariant and non-identifiability checks.
- File size, lack of a frontend caller, or archived wording alone does not
  prove safe deletion.

## 15. Hard Stop

This audit does not authorize fixing, deleting, extracting, migrating, or
shipping any finding. Each behavior-affecting finding requires its own declared
seam, proof obligation, rollback, and founder-approved authority where
applicable.
