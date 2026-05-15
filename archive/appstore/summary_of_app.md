# LyraOS - Comprehensive Product And Architecture Summary

> **Snapshot date:** 2026-05-14
> **Repository state:** 470 commits, 50 Alembic migrations, 82 backend test files
> **Status:** Pre-alpha dogfood with operator plus small alpha cohort

This document is a factual summary of the current LyraOS app and architecture.
It distinguishes shipped product behavior from operator-only tooling and
future-gated research concepts. It should not be read as authorization for new
inference, automatic rescheduling, hidden behavioral intervention, or expanded
user-burden surfaces.

---

## 1. Product Identity

LyraOS is a low-friction planning and execution product built around a
research-grade behavioral measurement system.

It is not a generic todo app and it is not pure research software. The app helps
users plan tasks, execute them with timers, recover from missed plans, and view
patterns in their own planning/execution data. The research layer interprets
those traces under explicit provenance, clean-data, exposure, and uncertainty
contracts.

The central product question is:

```text
Why do people plan well and still fail themselves?
```

The central research question is:

```text
Are humans wrong about their own execution capacity in structured,
modelable ways?
```

Current doctrine:

- preserve runtime identity authority through bearer/JWT
- resolve request scope before user data reads or writes
- keep product friction low
- preserve measurement validity
- treat insights as time-local, context-bound hypotheses
- never collapse behavior into a stable user identity label
- register user-facing output surfaces before render
- treat nudges, predictions, and insights as exposure candidates
- fail closed when exposure state is unknown
- verify topology before trusting browser verification

Canonical governance lives in:

- `MANIFESTO.md`
- `docs/cortex_contract_v0.md`
- `docs/cortex_product_research_contract_v0.md`
- `docs/context_window_blast_radius_contract.md`
- `docs/deployment_architecture.md`
- `docs/adaptive_scheduling_progressive_inference.md`
- `docs/openclaw_orchestration_contract_v0.md`

---

## 2. Current System Shape

```text
Next.js web app
  -> NextAuth Google identity
  -> frontend backendToken JWT
  -> FastAPI v1 API
  -> request user scope middleware
  -> service-layer mutation authorities
  -> SQLAlchemy models / Supabase Postgres
  -> Redis hot state and queues
  -> APScheduler workers

Research and governance layer:
  raw product events and rows
  -> Cortex read-time projections
  -> clean-data profiles
  -> output surface registry
  -> exposure ledger and render acknowledgement
  -> insights, diagnostics, predictions, and policy audits

Operator-only layer:
  JARVIS
  OpenClaw
  Telegram operator notifications
  admin dashboard
```

The user-facing product is the web app. JARVIS, OpenClaw, admin diagnostics,
and operator Telegram flows are not public research surfaces unless a successor
contract explicitly admits them.

---

## 3. Technology Stack

### Frontend

| Layer | Current stack |
| --- | --- |
| Framework | Next.js 15.5.15, App Router |
| Language | TypeScript 5.6 |
| Runtime | React 18 |
| Styling | Tailwind CSS, custom dark visual system |
| Auth | NextAuth.js 4 with Google OAuth |
| Server state | TanStack Query v5 with persisted cache support |
| Calendar UI | Schedule-X |
| UI primitives | Radix, Lucide, Tremor, Sonner, Motion |
| Public topology endpoint | `/api/topology` |

### Backend

| Layer | Current stack |
| --- | --- |
| Framework | FastAPI 0.109, Uvicorn |
| Language | Python |
| ORM | SQLAlchemy 2 typed models |
| Migrations | Alembic, 50 revisions |
| Database | Supabase Postgres for public runtime; SQLite supported for dev/tests |
| Hot state | Redis |
| Workers | APScheduler `BackgroundScheduler` |
| Settings | Pydantic v2, pydantic-settings |
| Public topology endpoint | `/v1/health/topology` |

### AI And Operator Runtime

| Surface | Current role |
| --- | --- |
| LLM enrichment worker | Async task enrichment; not critical-path |
| NVIDIA NIM | Optional hosted model path for operator/JARVIS and enrichment |
| Ollama | Local fallback for enrichment |
| JARVIS | Operator-only in-app assistant with confirmation-gated writes |
| OpenClaw | Operator-only multi-agent orchestration/runtime |

### Deployment

| Layer | Current shape |
| --- | --- |
| Public frontend | `https://lyraos.org` |
| Public API | `https://api.lyraos.org` |
| Edge | Cloudflare Tunnel from operator host |
| Containers | Docker Compose |
| Backend port | `8000` |
| Frontend port | `3000` |
| Runtime topology verifier | `node scripts/verify_runtime_topology.mjs --topology public` |

Ports, hostnames, CORS policy, auth semantics, and production wires are kernel
surfaces. They should not change without explicit operator approval and live
verification.

---

## 4. Authentication, Identity, And Scoping

LyraOS uses Google sign-in through NextAuth for identity. The frontend mints a
backend JWT (`backendToken`) signed with `NEXTAUTH_SECRET`; the backend verifies
that token using `JWT_SECRET`.

Important invariant:

```text
frontend NEXTAUTH_SECRET == backend JWT_SECRET
```

If those secrets diverge, Google login can appear to succeed while the backend
rejects `/v1/users/me`, causing the app to sign the user out and return them to
the landing page.

Current identity rules:

- bearer/JWT is the runtime identity authority
- backend middleware resolves the authenticated user before request handling
- first Google login auto-provisions a `User` row
- user-owned ORM reads are scoped through `ContextVar`-based request scope
- Redis hot keys are namespaced by user id
- raw SQL must scope manually
- frontend requests never override backend suppression or user scope

The app also has an account deletion path and tests around deletion of modern
auxiliary rows. Deletion work is part of product trust and data hygiene, not a
research shortcut.

---

## 5. Public Frontend Routes

| Route | Purpose |
| --- | --- |
| `/` | Landing page with LyraOS positioning and real Insights screenshot |
| `/today` | Main task execution surface |
| `/pulse` | Operational dashboard, quick capture, deadlines, system insight |
| `/calendar` | Schedule-X calendar with Lyra tasks and Google Calendar overlay |
| `/deadlines` | Native and Moodle-imported deadline management |
| `/insights` | Behavioral insight cards, synthesis, confidence tiers |
| `/table` | Raw task table with filters and bulk actions |
| `/settings` | Integrations, account controls, archetype/settings surfaces |
| `/admin/dashboard` | Operator-only admin and cohort dashboard |
| `/privacy` | Privacy page |
| `/terms` | Terms page |

There is no standalone onboarding route. Onboarding is a component-level gate
inside the authenticated app shell.

---

## 6. Core User-Facing Product Features

### Planning And Task Capture

- manual task creation
- task title and description
- planned start/end time
- planned duration
- category selection
- deadline binding
- duplicate/conflict checks
- LLM-assisted enrichment suggestions after creation
- quick capture through Pulse
- brain-dump parse and commit flow
- task table review and filtering

### Brain-Dump Onboarding

The onboarding flow asks the user to dump tasks and deadlines in free text.
The backend parses it, proposes task/deadline items, and commits rows through
normal task/deadline authorities.

Important details:

- parse endpoint is pure and does not write database state
- commit endpoint writes tasks/deadlines
- no starter/meta task should be created
- users with only skipped/deleted/voided task history can be shown onboarding
  again even if `onboarding_completed_at` was stamped
- meaningful onboarding is treated as `onboarding_completed_at` plus active
  non-skipped task history

### Execution Flow

- start task
- pause task
- resume task
- stop task
- switch from one paused task to another
- completion percentage updates
- pre-task readiness where already part of the flow
- post-task reflection where already part of the flow
- scope outcome capture
- pause reason capture where already part of the flow
- active timer banner
- overrun and completion check-ins
- undo support where Redis has stored enough context

### Recovery Flow

- mark overdue planned/skipped tasks done retroactively
- mark tasks abandoned/skipped
- delete or void tasks depending on path
- recover active timer state from Redis/database
- worker repair for stale sessions
- worker repair for orphan executing tasks

Retroactive completion is a product recovery affordance. It is not measured
real-time execution evidence.

---

## 7. Calendar, Deadlines, And External Context

### Native Deadlines

LyraOS supports native deadline rows separate from tasks. Tasks may bind to
deadlines, and deadline outcomes are reconciled after execution.

Deadline features:

- deadline CRUD
- planned/active/completed/missed states
- task-deadline binding
- frozen `TaskDeadlineOutcome` rows
- missed deadline sweep
- mark overdue done from product recovery surfaces

### Google Calendar

Google Calendar is a read-only integration.

Current behavior:

- user connects Calendar from Settings
- refresh token is stored on `User`
- events are fetched as ambient calendar context
- Google events render on the calendar
- Google events are not silently converted into tasks
- attendance/outcome reporting is tracked separately through
  `ExternalEventOutcome`

### Moodle iCal

Moodle iCal import persists LMS events as Lyra `Deadline` rows.

Current behavior:

- private Moodle iCal URL stored on user
- sync every 6 hours
- events upsert by external source/id
- imported rows are tagged `external_source='moodle_ics'`
- imported deadline rows are handled as external context, not natural Lyra
  planning evidence by default

### Moodle Web Services

Moodle Web Services can detect submitted/graded assignments and mark matching
Moodle deadlines complete.

Current behavior:

- per-user Moodle token support
- submission/grade status detection
- conservative matching by assignment title and due time
- backfill for Moodle assignments absent from the iCal window
- new Moodle WS tokens are Fernet-encrypted with `fernet:` prefix

---

## 8. Insights And Behavioral Feedback

The `/insights` page is a product mirror and a research-sensitive exposure
surface. It shows deterministic, data-triggered cards rather than open-ended
AI interpretation.

Current structure:

```text
Primary synthesis
High confidence cards
Medium confidence cards
Emerging patterns
```

Current insight types include:

- primary synthesis
- not-started/abandonment pattern
- pause pattern
- start delay
- readiness signal
- time-of-day bias
- estimation accuracy trend
- best category
- worst category
- discrepancy signal
- retroactive rate
- morning anchor cascade
- archetype divergence
- calibration maturation

The primary synthesis card is rule-composed from source insights and user data.
The text template is constrained, but the card appears, changes, or disappears
based on current evidence. It is descriptive synthesis, not a prescription.

Example of the intended safe shape:

```text
Planning drift is currently clustering around study tasks and late-day
execution.
```

Forbidden shape without future evidence:

```text
You should study in the morning.
```

The `work` category is quarantined from category claims because it was a legacy
fallback/default bucket and can contaminate interpretation.

---

## 9. Output Surface Registry

Behavior-shaping outputs must be registered before render. The registry source
of truth is:

```text
backend/app/core/output_surface_registry.json
```

Runtime output writes and exposure-safe emission go through:

```text
backend/app/services/output_surfaces.py
```

Registered surface families currently include:

- stopwatch micro-mirror
- stopwatch calibration nudge
- task creation nudge
- worker reminder
- worker pause prediction
- worker resume prediction
- analytics archetype proximity
- analytics insights
- analytics insights primary synthesis
- insight sub-surfaces for estimation trend, initiation delay, retroactive
  rate, time-of-day bias, readiness, abandonment, best/worst category,
  discrepancy, pause pattern, morning anchor cascade, archetype divergence,
  and calibration maturation

Each surface declares:

- `truth_class`
- `usage_class`
- `channel`
- `exposure_category`
- `signal_targets`
- `clean_profile`
- `min_n`
- `time_window_days`
- `fallback_mode`
- `operator_only`
- `legacy_adapter`
- `render_policy_version`
- interruptiveness and salience metadata

Frontend render acknowledgement is supported through the exposure acknowledgement
path. Render acknowledgement is governance telemetry and should not block the
user's current view.

---

## 10. Exposure Ledger v0

Exposure Ledger v0 is implemented as a causal firewall and replay boundary. It
is not an attribution engine and does not prove an exposure caused later
behavior.

The ledger answers:

```text
Can this measurement still be interpreted as baseline under the current
exposure horizon policy?
```

Core states:

- `NONE`
- `EXPOSED`
- `INTERVENTION`
- `UNKNOWN`

Only `NONE` can certify baseline-clean under the current policy. Missing ledger
state returns `UNKNOWN`, not `NONE`.

Implemented atoms:

- `ExposureDecisionEvent`
- `ExposureRenderEvent`
- `ExposureAckEvent`
- `SuppressionEvent`
- `ExposurePolicyEffectLog`

Legacy adapters:

- `ReflectionViewLog`
- `CalibrationNudgeEvent`
- `PausePredictionLog`
- `ResumePredictionLog`

Deferred by design:

- attention proxies
- temporal association atoms

Temporal association must remain correlational. It must not be described as
causal response linkage.

---

## 11. Cortex Product-Research Architecture

Cortex is the read-time canonicalization layer for research-grade metrics. It
does not silently rewrite product state.

Core metric vocabulary:

| Symbol | Name | Meaning |
| --- | --- | --- |
| `P` | planned active minutes | user plan |
| `E` | executed active minutes | execution excluding pauses |
| `W` | wall-clock elapsed minutes | elapsed real time |
| `B` | paused minutes | total pause duration |
| `m` | execution multiplier | `E / P` |
| `z` | log execution multiplier | `log(E / P)` |

Clean-data profiles:

- `measured_execution`
- `planning_calibration`
- `pause_process`
- `descriptive_history`

Important rules:

- derived metrics are recomputed at read time
- latent constructs are not persisted as observed facts
- unknowns never become neutral defaults
- repaired/retroactive data is excluded from measured-execution baselines
  unless a successor profile explicitly admits it
- exposed or unknown-exposure rows do not silently update clean learning paths

---

## 12. Prediction, Calibration, And Research Surfaces

### Bias Factor / Execution Multiplier

The legacy `bias_factor` path estimates how actual task duration compares to
planned duration. It blends personal history with seeded archetype/category
priors using sample-size weighting.

Cascade:

1. category x time-of-day x duration bucket
2. category x time-of-day
3. category
4. research prior

This is a product-facing estimate and research hypothesis. It is not a stable
identity trait.

### Archetype Survey And Proximity

LyraOS has a survey-backed archetype system and a dynamic archetype proximity
surface.

Current safeguards:

- archetype outputs are hypotheses
- proximity is time-local
- no stable identity label should be treated as fact
- posterior displays are gated by enough evidence
- baseline evidence is exposure-aware

### Pause Prediction

Pause prediction uses historical pause patterns and work rhythm signals.

Current mechanisms include:

- clock-anchor timing
- category-specific pause rhythm
- pause prediction logs
- cooldown and firing windows
- reconciliation of user response windows

### Resume Prediction

Resume prediction fires while a task is paused when pause duration approaches
historical category/time-of-day patterns or a cold-start fallback.

Current mechanisms include:

- category/time-of-day p75 duration
- absolute cold-start floor
- per-session cooldown
- resume prediction logs

### Inference Engine

The inference engine can classify behavioral hypotheses such as friction,
flow, scope creep, under-plan, and disagreement classes. These remain inferred
labels, not observed truth.

---

## 13. Adaptive Scheduling Direction

Adaptive scheduling is not currently autonomous scheduling.

Current status:

- descriptive synthesis is feasible and partially implemented through the
  Insights primary synthesis card
- low-authority experiment language is documented as a future direction
- validated adaptive scheduling is not shipped
- automatic rescheduling is not authorized
- hidden calendar mutation is not authorized

The intended future loop is:

```text
observe
  -> synthesize
  -> suggest a small experiment
  -> measure the result
  -> adapt confidence
```

The unlock model is evidence-driven, not arbitrary gamification. Stronger
guidance should appear only as the system accumulates enough clean,
longitudinal evidence for a specific user and context.

Future-gated stages:

- raw tracking
- descriptive insights
- bounded synthesis
- operator-only experiment suggestions
- measured experiment outcomes
- local adaptive confidence

No public adaptive scheduling, intervention suggestions, or confidence-backed
recommendations should ship without the future contract items listed in
`docs/adaptive_scheduling_progressive_inference.md`.

---

## 14. Brain Dump And Parsing Details

Current brain-dump parsing is deterministic and lives in the backend service
layer.

The parser can:

- split raw text into candidate items
- classify tasks versus deadlines
- parse date/time with `dateparser`
- infer durations where supported
- strip scheduling tokens from titles
- score confidence
- suggest task-deadline bindings

The product also supports a Pulse quick-capture modal that uses the same typed
brain-dump client path.

LLM enrichment is separate. It runs asynchronously after task creation and
must not silently replace user-visible canonical fields.

---

## 15. LLM Enrichment

LLM enrichment is a background worker, not a critical-path task creation
dependency.

Current behavior:

- selects pending tasks
- attempts configured hosted model path when available
- falls back to local model path where configured
- validates structured output
- writes suggestions into `llm_*` fields
- does not silently overwrite user-confirmed deadline bindings
- supports sticky rejection to avoid repeated unwanted suggestions

Potential enrichment fields:

- priority
- sub-items
- inferred deadline id
- deadline candidates
- alternative suggestions

LLM output is suggestion/proposal material, not observed truth.

---

## 16. JARVIS

JARVIS is an operator-only in-app assistant.

Current properties:

- only available to operator users
- reads Lyra context
- exposes a curated tool registry
- executes read tools immediately
- queues write tools for explicit confirmation
- writes `JarvisInvocation` audit rows
- can support task creation, focus-session start, deadline completion, Moodle
  sync, and hypothesis logging through confirmation-gated tools

JARVIS output is operator tooling. It is not Lyra product research data unless
a successor contract explicitly admits operator-session analysis.

---

## 17. OpenClaw

OpenClaw is an operator-only multi-agent runtime external to the product app.

Current role:

- orchestration and adversarial review
- codebase exploration
- implementation assistance
- operator research synthesis

OpenClaw must not:

- bypass Lyra auth, topology, exposure, or clean-data constraints
- become public user-facing research output
- merge agent claims into product truth without contract promotion
- treat local operator runtime traces as Lyra product research data

The runtime topology contract and context-window blast-radius contract exist
partly because OpenClaw/Codex work can span many layers at once.

---

## 18. Persistence Model

Current model families include:

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

### Research And Inference Rows

- `Archetype`
- `ArchetypeAssignment`
- `CategoryMapping`
- `CalibrationNudgeEvent`
- `ReflectionViewLog`
- `PausePredictionLog`
- `ResumePredictionLog`

### Exposure And Governance Rows

- `ExposureDecisionEvent`
- `ExposureRenderEvent`
- `ExposureAckEvent`
- `SuppressionEvent`
- `ExposurePolicyEffectLog`

### Operator Rows

- `JarvisInvocation`

All analytics/research reads must respect `voided_at` discipline where
applicable.

---

## 19. Task State Machine

```text
PLANNED   -> EXECUTING, SKIPPED, DELETED
EXECUTING -> PAUSED, EXECUTED, SKIPPED
PAUSED    -> EXECUTING, SKIPPED
EXECUTED  -> immutable
SKIPPED   -> DELETED
DELETED   -> immutable
```

Important details:

- `EXECUTED` and `DELETED` are terminal
- `PAUSED -> EXECUTED` is handled by auto-resume before stop
- `TaskManager` is the task mutation authority
- `DeadlineManager` is the deadline mutation authority
- overdue recovery may stamp retroactive completion but does not create a
  measured stopwatch trace
- voiding a task must clear or invalidate related live/session state

---

## 20. Background Jobs

APScheduler runs in-process. Jobs are designed to be idempotent where replay on
wake is expected.

| Job | Cadence | Purpose |
| --- | --- | --- |
| `reminders` | 1 minute | upcoming task reminders |
| `notion_sync` | 5 minutes | retry failed Notion syncs |
| `timer_overflow` | 2 minutes | check overflowing stopwatch sessions |
| `overdue_tasks` | 30 minutes | detect and skip overdue unstarted tasks |
| `stale_session_recovery` | 15 minutes | close old unclosed stopwatch sessions |
| `orphan_task_recovery` | 15 minutes | recover EXECUTING tasks without open session |
| `pause_prediction` | 1 minute | fire/log/queue pause predictions |
| `reconcile_responses` | 5 minutes | reconcile pause prediction outcomes |
| `reconcile_deadline_outcomes` | 30 minutes | write task-deadline outcome rows |
| `sweep_missed_deadlines` | 1 hour | mark overdue active deadlines missed |
| `llm_enrichment` | 5 seconds | async semantic task enrichment |
| `resume_prediction` | 2 minutes | fire resume banner while paused |
| `moodle_ics_sync` | 6 hours | import Moodle iCal deadlines |
| `moodle_submissions_sync` | 6 hours | detect Moodle submissions and complete deadlines |

---

## 21. API Surface

All backend routes are mounted under `/v1`.

| Module | Responsibility |
| --- | --- |
| `health.py` | health, env invariants, topology report |
| `parse.py` | single task parse and deadline preview |
| `query.py` | range task queries and last-task lookup |
| `tasks.py` | task CRUD/state transitions/recovery/LLM binding actions |
| `stopwatch.py` | start, pause, resume, stop, switch, status |
| `undo.py` | Redis-backed undo |
| `notifications.py` | notification queue/operator bridge |
| `analytics.py` | insights, diagnostics, Cortex analytics, bias/prediction endpoints |
| `users.py` | `/users/me`, consent, onboarding stamps, account export/deletion |
| `pause_predictions.py` | pause prediction response and confirmation |
| `reflection_view.py` | reflection exposure/view/dismiss logging |
| `calendar.py` | Google Calendar read-only events/outcomes |
| `integrations.py` | integration availability/status |
| `admin.py` | operator dashboard |
| `deadlines.py` | deadline CRUD/state transitions |
| `feedback.py` | alpha feedback |
| `brain_dump.py` | brain-dump parse and commit |
| `moodle.py` | Moodle iCal/WS connect, preview, sync |
| `jarvis.py` | operator-only JARVIS chat/confirm/health/stream |
| `exposures.py` | render acknowledgement and exposure utilities |
| `skill_check.py` | OpenClaw skill ping |

---

## 22. Runtime Topology

Runtime topology is part of correctness. Browser smoke is not trusted until the
frontend, backend, auth base, API origin, and CORS contract agree.

Topology artifacts:

- `runtime_topology.json`
- frontend `/api/topology`
- backend `/v1/health/topology`
- `scripts/verify_runtime_topology.mjs`

Current public topology:

```text
frontend: https://lyraos.org
api:      https://api.lyraos.org
auth:     https://lyraos.org
```

The verifier checks:

- frontend topology class
- compiled API origin
- NextAuth URL
- backend topology class
- CORS behavior
- auth provider URL shape
- cross-topology poisoning

---

## 23. Security, Privacy, And Credential Status

Current security posture:

- Google identity through NextAuth
- backend bearer JWT validation
- per-user request scoping
- user-namespaced Redis hot keys
- operator-only gates for admin/JARVIS
- account export and deletion surfaces
- secrets must not be logged or returned through API responses

Credential status:

- Moodle WS token: Fernet-encrypted for new connections
- Google refresh token: plaintext security debt
- Moodle iCal URL: plaintext security debt
- Notion token: environment/configured integration secret

Known privacy/legal debt:

- public privacy and terms pages exist but may still need production-grade
  review and hosted-model disclosure language
- public marketing copy must avoid overclaiming adaptive scheduling

---

## 24. Testing And Verification

The repository contains backend tests for:

- config and topology invariants
- multi-user isolation
- task state transitions
- stopwatch and pause/resume behavior
- deadline behavior
- brain-dump parsing
- LLM parser guards
- Cortex metrics
- exposure ledger behavior
- output surface registry
- insights and primary synthesis
- account deletion auxiliary rows
- Moodle and integration paths

Current operational gate discipline:

- re-anchor before continuing after context drift
- run focused tests for the touched layer
- run backend CI-equivalent for backend changes when available
- verify runtime topology before browser smoke
- browser smoke before push
- watch CI after push
- do not push without browser verification

Recent local caveat: some ad hoc test attempts can fail if the local/container
environment lacks test dependencies. That is an environment issue, not proof
that the feature is verified.

---

## 25. Current Known Risks And Debts

1. Cloudflare Tunnel from the operator host is still an operational dependency.
2. Google refresh tokens and Moodle iCal URLs remain plaintext.
3. Analytics code is large and mixes product analytics, research diagnostics,
   and operator diagnostics.
4. Exposure Ledger v0 has no attention proxies or temporal association atom.
5. Historical exposure coverage is adapter-based rather than physically
   backfilled.
6. Adaptive scheduling is not validated beyond descriptive/operator dogfood
   concepts.
7. JARVIS and OpenClaw are powerful operator tools and must not become hidden
   product research authorities.
8. Frontend persisted cache can create confusing stale-state moments if auth
   transitions are not cleared correctly.
9. Any new research input risks violating the fixed observation surface.
10. The `work` category remains contaminated legacy data and should stay
    quarantined from category-level insight claims.
11. The public landing page describes adaptive scheduling as a direction; copy
    must remain careful not to imply autonomous scheduling is live.
12. Runtime auth depends on `NEXTAUTH_SECRET` and backend `JWT_SECRET` staying
    aligned.

---

## 26. Shipped vs Future-Gated

### Shipped/User-Facing

- Google sign-in
- brain-dump onboarding
- task planning
- timer execution
- pause/resume/stop/switch
- overdue recovery
- calendar view
- deadlines
- Moodle import/submission detection
- Google Calendar read-only context
- Notion sync
- Pulse dashboard
- Insights page
- primary synthesis insight card
- confidence-tiered insight cards
- pause and resume prediction surfaces
- archetype survey/proximity
- settings and integrations
- account export/deletion
- feedback widget

### Shipped/Operator-Only

- admin dashboard
- JARVIS
- OpenClaw workflows
- operator notifications
- topology verification discipline
- exposure diagnostics and policy logs

### Future-Gated / Not Publicly Shipped

- automatic rescheduling
- hidden calendar mutation
- validated adaptive scheduling
- intervention suggestions beyond carefully bounded/operator-only experiments
- confidence-backed behavioral recommendations
- learning from exposed/intervened behavior without stratified exposure modeling
- new required user input for research enrichment

---

## 27. One-Line Summary

LyraOS is a planning and execution app whose deeper architecture is a
measurement-valid behavioral instrument: users plan and work normally, the
system preserves the trace, Cortex interprets it under clean-data constraints,
the exposure ledger protects baseline validity, and stronger guidance is only
allowed when evidence, topology, identity, and governance all hold together.
