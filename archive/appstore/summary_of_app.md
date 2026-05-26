# LyraOS - Current Product And Architecture Summary

> **Snapshot date:** 2026-05-24
> **Repository state:** Pre-alpha, actively dogfooded, small alpha cohort,
> evidence-packet / ClaimCompiler branch with LyraSim product-seam increments
> in progress.
> **Status:** Factual architecture summary. This document is descriptive, not
> implementation authorization.

This summary reflects the current repo shape after the May authority,
pressure-map, LyraSim, kill-switch, and university-review framing work. It is
grounded in the checked-in app, backend services, docs, and scripts. It should
not be read as permission to add inference, autonomous scheduling, live Baseet
integration, public AI synthesis, hidden telemetry, or new user-burden surfaces.

---

## 1. Product Identity

LyraOS is a generalized execution-state modeling system wrapped in a planning
and recovery product.

The current student-facing framing is deliberately simpler:

```text
academic load becomes visible
plans become executable
drift becomes recoverable
```

The deeper product substrate is broader than students. LyraOS models recurring
obligations, intentions, execution sessions, interruptions, drift,
recalibration, exposure, provenance, and authority. Academic use is the first
high-pressure domain because courses, deadlines, resources, and recurring work
make the intention/execution gap unusually visible.

At the doctrine level, LyraOS is the first operational organ of a broader
deterministic/probabilistic worldview: repeated human-system interactions
shape trajectory, and technology amplifies whatever target the system actually
optimizes. Lyra's target is reality contact, not hidden proxy optimization.

Current core loop:

```text
plan -> anchor session -> drift happens -> recover -> calibrate
```

Current doctrine:

- partial structure is useful, but not truth;
- user confirmations are high-signal anchors, not perfect ground truth;
- provider data is context and obligation structure, not execution truth;
- passive or ambiguous activity must not become focus, mastery, learning, or
  completion claims;
- stronger capability must be earned by clean longitudinal evidence;
- uncertainty should reduce claim authority, not erase safe recovery actions;
- sequencing is part of alignment because revelation order changes
  interpretation and future behavior;
- capability that nudges, prioritizes, ranks, or adapts is trajectory-shaping
  authority and must stay bounded;
- governance exists to keep the product simple and bounded, not to become the
  product.

---

## 2. Current Architecture In One Pass

```text
Next.js web app
  -> NextAuth Google identity
  -> backendToken JWT
  -> FastAPI /v1 API
  -> UserScopeMiddleware
  -> request-scoped SQLAlchemy reads/writes
  -> Supabase Postgres
  -> Redis hot state and queues
  -> APScheduler repair/sync/prediction jobs

Product/research interpretation:
  raw rows and events
  -> Cortex read-time projections
  -> clean-data profiles
  -> EvidencePacket
  -> ClaimCompiler
  -> output surface registry
  -> exposure ledger
  -> bounded user-facing claims, nudges, pressure, insights, and recovery

Provider/module layer:
  Google Calendar, Moodle, future Baseet, future provider adapters
  -> provider-blind facts and evidence classes
  -> pressure/recovery surfaces

Operator-only layer:
  admin dashboard, JARVIS, OpenClaw, topology verification,
  notifications, diagnostics, and adversarial review
```

The app is not currently an OS-level telemetry product. The repo is converging
on sparse, trustworthy causal anchors: explicit starts/stops, pauses,
completion updates, corrections, confirmations, and low-friction recovery
questions.

---

## 3. Technology Stack

### Frontend

| Layer | Current stack |
| --- | --- |
| Framework | Next.js App Router |
| Language | TypeScript |
| Auth | NextAuth with Google OAuth |
| Server state | TanStack Query with persisted localStorage cache |
| Styling | Tailwind CSS with the Lyra dark/cyan visual system |
| Main surfaces | Landing, Pulse, Today, Calendar, Deadlines, Insights, Table, Settings |

### Backend

| Layer | Current stack |
| --- | --- |
| Framework | FastAPI |
| Language | Python |
| ORM | SQLAlchemy typed models |
| Migrations | Alembic |
| Database | Supabase Postgres in public runtime; SQLite remains useful for tests/dev |
| Hot state | Redis |
| Workers | APScheduler |
| Auth | Bearer JWT from frontend NextAuth session |

### AI And Tooling

| Surface | Current role |
| --- | --- |
| LLM enrichment | Async task enrichment suggestions, not truth authority |
| NVIDIA NIM / Ollama paths | Optional model paths for enrichment/operator workflows |
| JARVIS | Operator-only assistant with confirmation-gated writes |
| OpenClaw/Codex | Operator development, review, and orchestration tooling |

The user-facing behavioral core remains rule-governed, probabilistic,
inspectable, and constrained by clean-data and exposure contracts.

---

## 4. Runtime Topology

Current public topology:

```text
frontend: https://lyraos.org
api:      https://api.lyraos.org
auth:     https://lyraos.org
```

Topology is treated as correctness, not deployment trivia.

Relevant artifacts:

- `runtime_topology.json`
- frontend `/api/topology`
- backend `/v1/health/topology`
- `scripts/verify_runtime_topology.mjs`
- `scripts/browser_smoke_two_users.mjs`
- `docs/deployment_architecture.md`

Browser verification is meaningful only when frontend origin, API origin,
auth base URL, CORS, and runtime topology agree.

---

## 5. Authentication, Scoping, And Data Boundaries

Runtime identity authority is bearer/JWT, resolved by
`UserScopeMiddleware` in `backend/app/main.py`.

Current invariants:

- Google sign-in happens through NextAuth.
- The frontend forwards a backend JWT as `Authorization: Bearer`.
- The backend verifies it with `JWT_SECRET`.
- First valid login can provision a `User` row.
- `X-User-Id` is test-only and cannot authenticate normal runtime HTTP.
- Bearer identity beats test identity if both are present.
- Backend reads/writes are request-scoped through a `ContextVar`.
- Operator/admin/JARVIS routes require operator authority.
- Account export and deletion exist in `/v1/users/me`.

This matters because a locally hacked frontend or extension can create shadow
usage, but it does not write to the backend unless it has a valid authenticated
API path.

---

## 6. Current User-Facing Surfaces

| Route | Purpose |
| --- | --- |
| `/` | Public landing page and product framing |
| `/pulse` | Operational dashboard: quick capture, deadlines, pressure, recovery, system insight |
| `/today` | Main task execution surface |
| `/calendar` | Schedule view with Lyra tasks and Google Calendar overlay |
| `/deadlines` | Native and imported deadline management |
| `/insights` | Deterministic insight cards and primary synthesis |
| `/table` | Raw task table, filters, bulk actions, CSV export |
| `/settings` | Integrations, archetype survey, export/delete, account controls |
| `/admin/dashboard` | Operator-only dashboard |

There is no standalone onboarding route. Onboarding is a component-level gate
inside the authenticated app shell.

---

## 7. Planning, Capture, And Brain Dump

LyraOS supports:

- manual task creation;
- quick capture on Pulse;
- title, description, category, planned start/end, and planned duration;
- deadline binding;
- conflict and duplicate checks;
- task table review/filtering;
- CSV export from the table;
- full JSON export from Settings;
- brain-dump parsing for low-friction onboarding and capture.

Brain-dump parsing is split into a pure parse step and a commit step. The parse
path proposes candidate tasks/deadlines; the commit path writes through normal
task/deadline authorities. No starter/meta task should be created merely to
mark onboarding.

Important current distinction:

```text
brain dump = useful capture surface
not = proof of execution, clean calibration, or provider truth
```

Brain dump may become less central for the academic module if provider
deadline/resource supersession is strong enough, but it remains useful for
other modules and free-form planning.

---

## 8. Execution, Timers, And Recovery

Core execution features:

- start task;
- pause task;
- resume task;
- stop task;
- switch active work from one paused task to another;
- update task completion percentage while active;
- capture readiness/reflection where the existing flow asks for it;
- undo where Redis has sufficient context;
- active timer banner;
- pause/resume prediction surfaces.

Recovery features:

- mark overdue tasks done retroactively;
- abandon/skip tasks;
- delete or void tasks depending on path;
- append execution corrections;
- recover timer state from Redis/database;
- background repair for stale sessions and orphan executing tasks.

Critical measurement rule:

```text
retroactive completion and repaired sessions are recovery evidence,
not clean measured execution by default
```

This rule is now central because real data contains stale sessions, outliers,
extension/local shadow usage, and other messy states.

---

## 9. Task And Deadline State

Task state machine:

```text
PLANNED   -> EXECUTING, SKIPPED, DELETED
EXECUTING -> PAUSED, EXECUTED, SKIPPED
PAUSED    -> EXECUTING, SKIPPED
EXECUTED  -> immutable
SKIPPED   -> DELETED
DELETED   -> immutable
```

`TaskManager` owns task mutation. `DeadlineManager` owns deadline mutation.
Deadline rows are separate from tasks and can represent native or external
obligations.

Deadline behavior includes:

- CRUD/state transitions;
- planned/active/completed/missed states;
- task-deadline binding;
- missed-deadline sweeps;
- frozen task-deadline outcome rows;
- recovery marking for overdue work.

Provider or submission signals may inform recovery or obligation state, but
they must not silently become clean execution truth.

---

## 10. Providers, Modules, And The Baseet Reframe

LyraOS core should remain provider-agnostic. Providers and modules translate
domain-specific structure into provider-blind primitives.

Current provider/module surfaces:

- Google Calendar read-only context;
- Moodle iCal deadlines;
- Moodle Web Services submission/grade detection;
- Notion outbound sync/retry plumbing;
- planned/future Baseet academic module.

Current Baseet lesson:

```text
Baseet is likely a strong obligation/resource substrate,
but a weak behavioral substrate.
```

That means Baseet can provide:

- courses;
- deadlines;
- resources;
- possible progress candidates;
- pressure topology.

It should not be treated as:

- continuous execution truth;
- focus signal;
- mastery signal;
- proof of study;
- proof of completion.

The architecture now points toward:

```text
sparse academic structure
+ explicit user confirmations
+ local/session anchors
-> bounded pressure and recovery
```

not OS-level continuous observability.

---

## 11. Academic Pressure Map

`backend/app/services/academic_pressure.py` produces a bounded workload-pressure
snapshot from existing deadlines, planned tasks, and read-only calendar
context.

Current properties:

- no new persistence required for V1 pressure maps;
- uses ranges instead of fake exact certainty;
- distinguishes native obligations from external obligations;
- uses provider-boundary metadata such as source class, evidence class,
  provider kind, raw authority level, and redaction status;
- emits recovery options as low-authority suggestions;
- does not claim behavioral personalization;
- does not feed clean learning paths;
- does not mutate tasks or calendars by itself.

Pressure Map authority:

```text
surface_role: diagnostic_planning_surface
authority_rung: suggestion
mutation_permission: explicit_user_confirmation_required
```

This is currently the most realistic Baseet-adjacent product seam.

---

## 12. Kill Switches And Containment

Pre-scale containment switches live in `backend/app/core/kill_switches.py` and
settings.

Current switches:

- `LYRA_SAFE_MODE=read_only_pressure`
- `LYRA_BASEET_PRESSURE_INPUT_ENABLED`
- `LYRA_PROVIDER_PROGRESS_SIGNALS_ENABLED`
- `LYRA_RECOVERY_NUDGES_ENABLED`

Current behavior:

- read-only pressure safe mode disables provider progress signals;
- read-only pressure safe mode disables recovery nudges;
- Baseet pressure input can be disabled independently;
- recovery nudges can be disabled independently.

The purpose is containment, not bureaucracy: if a provider-derived pathway
starts producing bad pressure or bad recovery, the system can degrade toward a
read-only pressure map instead of mutating or nudging.

---

## 13. Insights, EvidencePacket, And ClaimCompiler

The `/insights` page is a product mirror and exposure-sensitive surface. It
renders deterministic cards, confidence tiers, and primary synthesis. It is
not open-ended AI interpretation.

Current insight families include:

- primary synthesis;
- abandonment/not-started pattern;
- pause pattern;
- start delay;
- readiness signal;
- time-of-day bias;
- estimation accuracy trend;
- best/worst category;
- discrepancy signal;
- retroactive rate;
- morning anchor cascade;
- archetype divergence;
- calibration maturation.

The evidence-packet branch centralizes claim governance:

```text
already-computed analytics output
-> EvidencePacket
-> ClaimCompiler
-> bounded claim candidate
-> registered output surface
```

`EvidencePacket` is intentionally narrow. It carries clean profile, sample
count, scalar observed metrics, source refs, prohibited claims, and suppression
reason. It must not become a provider DTO, output grammar, raw payload bag, or
future AI synthesis container.

`ClaimCompiler` compiles existing deterministic claims only. It suppresses
claims when evidence is insufficient or prohibited claim tags are crossed.

---

## 14. Output Surfaces And Exposure Ledger

Behavior-shaping outputs must be registered before render. The registry lives
at:

```text
backend/app/core/output_surface_registry.json
```

Runtime contract code lives in:

```text
backend/app/services/output_surfaces.py
backend/app/services/exposure_ledger.py
```

Output surfaces declare:

- truth class;
- usage class;
- channel;
- exposure category;
- signal targets;
- clean profile;
- minimum sample count;
- time window;
- fallback mode;
- operator-only status;
- render policy version;
- authority metadata.

Exposure Ledger v0 is a causal firewall and replay boundary. It answers:

```text
can this later measurement still be interpreted as baseline?
```

Core exposure states:

- `NONE`
- `EXPOSED`
- `INTERVENTION`
- `UNKNOWN`

Only `NONE` can certify baseline-clean under current policy. Missing exposure
state becomes `UNKNOWN`, not `NONE`.

---

## 15. Cortex And Clean Data

Cortex is the read-time canonicalization layer for research-grade metrics. It
does not silently rewrite product state.

Core vocabulary:

```text
planned active minutes
executed active minutes
wall-clock elapsed minutes
paused minutes
execution multiplier
log execution multiplier
```

Clean-data profiles:

- `measured_execution`
- `planning_calibration`
- `pause_process`
- `descriptive_history`
- `deadline_completion_behavior`

Rules:

- derived metrics are recomputed at read time;
- latent constructs are not persisted as observed facts;
- unknowns never become neutral defaults;
- repaired/stale/retroactive/provider-only data is excluded from clean
  measured-execution baselines unless a successor profile admits it;
- exposed or unknown-exposure rows do not silently update clean learning paths.

---

## 16. Prediction, Priors, And Progressive Capability

Current prediction/calibration surfaces include:

- bias factor / execution multiplier;
- category and time-of-day priors;
- archetype survey and dynamic proximity;
- pause prediction;
- resume prediction;
- inference-engine hypotheses.

These are bounded estimates and hypotheses, not identity truth.

The strategic direction is progressive capability:

```text
few clean anchors -> descriptive help
more clean anchors -> better estimates
many clean anchors -> bounded recommendations
validated history -> optional adaptive scheduling
```

Potential future unlock language such as “50 clean sessions to unlock adaptive
scheduling” is a product/research direction, not a shipped capability.

Adaptive scheduling remains future-gated. The current system may describe,
summarize, and suggest low-authority recovery paths, but it must not silently
reschedule or auto-manage users.

---

## 17. Research Doctrine

The current research stance is not “track psychology.” It is:

```text
instrument the gap between intention and execution
while preserving authority boundaries
```

Important doctrines:

- `docs/behavioral_instrumentation_doctrine.md`
- `docs/cortex_contract_v0.md`
- `docs/cortex_product_research_contract_v0.md`
- `docs/research_mapping.md`
- `docs/adaptive_scheduling_progressive_inference.md`
- `docs/execution_anomaly_edge_case_register.md`
- `docs/design_patterns/sequential_revelation_doctrine.md`

Current conceptual primitives from `backend/app/core/research_contracts.py`:

- provider connection;
- obligation;
- academic asset;
- activity event;
- intention;
- execution event;
- outcome;
- interruption;
- exposure;
- drift;
- recalibration;
- trust state;
- provenance;
- authority level;
- redaction status.

Sequential revelation doctrine is now a design principle:

```text
understanding is staged at the rate humans can metabolize it
```

This applies to presentations, onboarding, insight surfaces, recovery prompts,
and future adaptive flows.

Trajectory-integrity doctrine is now the deeper philosophical invariant:

```text
optimize for contact with reality
not for obedience to plans, institutional convenience, or product vanity
```

This does not make Lyra anti-technology or anti-optimization. It makes Lyra
anti-hidden-proxy optimization. Engagement, retention, status, productivity,
and institutional convenience are not allowed to outrank user agency,
provenance, exposure awareness, reversibility, or correction.

---

## 18. LyraSim

LyraSim is the synthetic pressure-and-ambiguity harness. Its active roadmap is:

```text
docs/lyrasim_pressure_ambiguity_roadmap.md
```

V0 harness log:

```text
docs/lyrasim_stress_harness.md
```

LyraSim purpose:

```text
ambiguous trace -> bounded hypothesis -> safe output/recovery
not:
ambiguous trace -> confident surveillance claim -> polluted learning loop
```

Current implemented scenario families include:

- `task_started_never_stopped`;
- `baseet_resource_open_idle_45m`;
- `baseet_stale_task_progress_candidate`;
- `baseet_background_video_fakeout`;
- `baseet_multidevice_upload_collision`;
- `baseet_reverse_progress_signal`;
- `baseet_duplicate_stale_deadline_pressure`;
- `execution_outlier_single_trace_does_not_generalize`.

LyraSim now reports findings summaries, resolution rungs, safe-action types,
safe-action availability, uncertainty paralysis, self-report prompt
availability, and safe-action spam diagnostics.

Product-seam validation is earned only when generated scenario data enters a
real product service or endpoint and the report names that seam. Stubbed runs
remain harness validation only.

---

## 19. Execution Anomalies And Client Integrity

The repo now treats execution anomalies as first-class design pressure.

Known anomaly families:

- stale sessions;
- auto-closed sessions;
- extreme duration outliers;
- retroactive completion;
- repaired sessions;
- provider-only progress candidates;
- background video/resource fakeouts;
- multi-device collisions;
- reverse provider progress;
- extension/local shadow usage that bypasses backend persistence.

Core rule:

```text
one anomalous trace may become a bounded review hypothesis;
it must not become a stable user pattern by itself
```

The extension/local-storage incident adds another doctrine:

```text
client state is not trustworthy evidence by default
```

This does not invalidate Lyra. It reinforces the need for explicit causal
anchors, provenance, clean-data gates, and recovery-first UX.

---

## 20. API Surface

All backend routes mount under `/v1`.

| Module | Responsibility |
| --- | --- |
| `health.py` | Health, env invariants, topology |
| `parse.py` | Single task parse and deadline preview |
| `query.py` | Task range queries and last-task lookup |
| `tasks.py` | Task CRUD, state transitions, recovery |
| `stopwatch.py` | Start, pause, resume, stop, switch, status |
| `undo.py` | Redis-backed undo |
| `notifications.py` | Notification queue/operator bridge |
| `analytics.py` | Insights, diagnostics, Cortex analytics, bias/prediction endpoints |
| `users.py` | `/users/me`, consent, onboarding stamps, export/deletion |
| `pause_predictions.py` | Pause prediction responses |
| `reflection_view.py` | Reflection exposure/view/dismiss logging |
| `calendar.py` | Google Calendar read-only events/outcomes |
| `integrations.py` | Integration status |
| `admin.py` | Operator dashboard |
| `deadlines.py` | Deadline CRUD/state transitions |
| `feedback.py` | Alpha feedback |
| `brain_dump.py` | Brain-dump parse/commit |
| `moodle.py` | Moodle iCal/WS connect, preview, sync |
| `jarvis.py` | Operator-only JARVIS |
| `exposures.py` | Render acknowledgement and exposure utilities |
| `academic.py` | Academic pressure map |
| `skill_check.py` | OpenClaw skill ping |

---

## 21. Background Jobs

APScheduler runs in process. Jobs are designed to be idempotent where replay on
wake is expected.

| Job | Purpose |
| --- | --- |
| `reminders` | Upcoming task reminders |
| `notion_sync` | Retry failed Notion syncs |
| `timer_overflow` | Check overflowing stopwatch sessions |
| `overdue_tasks` | Detect and skip overdue unstarted tasks |
| `stale_session_recovery` | Close old unclosed sessions |
| `orphan_task_recovery` | Recover executing tasks without open sessions |
| `pause_prediction` | Fire/log/queue pause predictions |
| `reconcile_responses` | Reconcile pause prediction outcomes |
| `reconcile_deadline_outcomes` | Write task-deadline outcome rows |
| `sweep_missed_deadlines` | Mark overdue active deadlines missed |
| `llm_enrichment` | Async semantic task enrichment |
| `resume_prediction` | Fire resume banner while paused |
| `moodle_ics_sync` | Import Moodle iCal deadlines |
| `moodle_submissions_sync` | Detect Moodle submissions and complete deadlines |

---

## 22. Persistence Model

Model families include:

### Core Product Rows

- `User`
- `Task`
- `StopwatchSession`
- `PauseEvent`
- `TaskExecutionCorrection`
- `Deadline`
- `DeadlineCompletionEvent`
- `TaskDeadlineOutcome`
- `ExternalEventOutcome`
- `Feedback`

### Research / Inference Rows

- `Archetype`
- `ArchetypeAssignment`
- `CategoryMapping`
- `CalibrationNudgeEvent`
- `ReflectionViewLog`
- `PausePredictionLog`
- `ResumePredictionLog`

### Exposure / Governance Rows

- `ExposureDecisionEvent`
- `ExposureRenderEvent`
- `ExposureAckEvent`
- `SuppressionEvent`
- `ExposurePolicyEffectLog`
- security/audit rows where present in the current model layer

### Operator Rows

- `JarvisInvocation`

All analytics/research reads must respect user scoping, `voided_at`, clean-data
profile, and exposure state where applicable.

---

## 23. Operator-Only Systems

JARVIS is an operator-only assistant. It can read context, call curated tools,
and queue writes for explicit confirmation. It is not a public user feature.

OpenClaw/Codex workflows are operator-side development and research tools. They
may propose, review, and implement code under operator authority, but they do
not own doctrine, runtime mutation, or user-facing truth.

Agent council work is useful for adversarial interpretation after new scenario
families, warnings, catastrophic failures, or suspicious passes. It should not
become an automatic judge of every tiny simulation pass.

---

## 24. Security, Privacy, And Data Access Posture

Current posture:

- bearer/JWT runtime auth;
- operator-only gates for admin/JARVIS;
- per-user scoped reads/writes;
- account export and deletion;
- no individual instructor dashboard in the intended university framing;
- student-facing personal layer;
- research/export layer should be explicit-consent, pseudonymized/aggregated,
  exposure-aware;
- institutional layer should remain aggregate and thresholded, not
  individually traceable.

Known security/privacy debts:

- public deployment still depends on operator-hosted Cloudflare Tunnel;
- Google refresh tokens and Moodle iCal URLs are security-sensitive;
- some credential storage remains legacy/plaintext debt depending on provider;
- public privacy/legal posture needs real review before broad deployment;
- client/extension-local shadow usage can bypass product instrumentation;
- client-shadow recovery must use the canonical read-only protocol and script,
  never improvised/generated DevTools code;
- frontend persisted cache requires careful auth clearing.

---

## 25. Current User Activity Read

As of the May 24 production aggregate check:

- backend-visible non-operator users: 18;
- non-operator users with any tasks: 12;
- non-operator users with sessions: 7;
- non-operator backend-visible tasks: 107;
- non-operator backend-visible sessions: 32;
- top visible non-operator users show real but shallow use;
- one trusted hidden extension/local user reportedly tracked about 133 sessions
  outside the expected backend instrumentation path.

Interpretation:

```text
backend-visible retention is weak-to-moderate;
hidden/local usage may contain the strongest retained-use signal;
observability is incomplete.
```

This is a product lesson, not proof of product-market fit. The immediate
research need is reality contact: interviews, recovered shadow data where
consented, and small-cohort testing of the pressure/session/recovery loop.

---

## 26. Shipped vs Future-Gated

### Shipped / User-Facing

- Google sign-in;
- brain-dump onboarding;
- task planning;
- timer execution;
- pause/resume/stop/switch;
- completion percentage updates;
- overdue and stale-session recovery;
- calendar and deadline views;
- Moodle iCal / Moodle WS surfaces;
- Google Calendar read-only context;
- Pulse dashboard;
- academic pressure map;
- Insights page and primary synthesis;
- confidence-tiered insight cards;
- pause and resume prediction surfaces;
- archetype survey/proximity;
- settings, integrations, export/delete;
- feedback widget.

### Shipped / Operator-Only

- admin dashboard;
- JARVIS;
- OpenClaw/Codex workflows;
- operator notifications;
- topology verification scripts;
- exposure diagnostics and policy logs;
- LyraSim harness and product-seam tests.

### Future-Gated / Not Publicly Shipped

- live Baseet integration;
- autonomous rescheduling;
- hidden calendar/task mutation;
- OS-level telemetry;
- passive activity inference as execution truth;
- AI synthesis over evidence packets;
- public cascade intervention;
- hypothesis-based interventions;
- adaptive scheduling;
- archetype-driven recommendations;
- institutional individual-risk dashboards.

---

## 27. Current Known Risks And Debts

1. Reality contact is still too thin relative to the ambition.
2. Backend-visible user retention is shallow, while extension/local usage shows
   instrumentation blind spots.
3. Provider data can easily be overread unless pressure/recovery seams stay
   strict.
4. Baseet is likely strong structure but weak behavioral continuity.
5. Adaptive scheduling requires more clean evidence than most users currently
   provide.
6. Prompt/confirmation fatigue is a real product risk.
7. Stale sessions and extreme outliers can distort estimates if not handled.
8. Governance complexity can become product complexity if not kept behind the
   scenes.
9. Cloudflare Tunnel/operator-hosted deployment remains operational debt.
10. Some provider credentials/secrets need stronger production-grade handling.
11. Analytics code remains broad and mixed across product, research, and
    operator concerns.
12. Public/university language must sell value first and avoid surfacing
    objections before reviewers understand the product.

---

## 28. Immediate Strategic Frame

The current best next question is not:

```text
Can Lyra perfectly model execution reality?
```

It is:

```text
What is the minimum viable truthful utility?
```

The realistic near-term loop:

```text
see pressure
anchor a session
drift happens
receive a low-friction recovery choice
confirm enough truth to improve the next estimate
```

Commercially and scientifically, Lyra should now validate:

- whether students/users reopen the pressure and recovery loop;
- which confirmations feel useful rather than annoying;
- how sparse causal anchors can be before value collapses;
- whether recovered hidden/power-user data shows a durable value loop;
- whether provider modules can provide useful structure without behavioral
  overclaiming.

The architecture remains coherent, but its claims have narrowed:

```text
not omniscient cognition tracking
not one-provider behavioral truth
not autonomous planner

yes bounded execution-state modeling
yes pressure topology
yes sparse confirmations
yes recovery from drift
yes progressively earned confidence
```
