---
authority: concept-note
may_authorize_code: false
runtime_owner: none
created: 2026-06-29
---

# Refactor And Spaghetti Audit - 2026-06-29

Status: read-only audit snapshot. This document records the multi-agent
refactor audit and local hotspot scan. It does not authorize code changes,
runtime refactors, Jarvis deletion, schema migrations, AI synthesis, or new
features.

## Executive Verdict

LyraOS is not a bad rewrite candidate. It is high-velocity research software
with several concentrated god modules, duplicated state machines, and authority
drift around mutation, exposure, provider truth, and behavioral claims.

Current spaghetti severity:

```text
overall: 7 / 10
```

The code is not uniformly tangled. The debt clusters around a small number of
large modules and a few duplicated runtime ownership patterns.

The highest-risk issue is not duplicate UI. The highest-risk issue is duplicate
truth authority:

1. multiple surfaces can mutate or shape canonical task/deadline/timer truth;
2. multiple modules compute behavior meaning with different clean filters;
3. notification, exposure, and render semantics still have multiple paths;
4. provider facts can still enter native-looking truth through different paths;
5. operational boot/topology scripts can disagree about which runtime is real.

The core correction principle remains:

```text
One owner per truth class.
Many producers.
Many views.
One mutation path.
One claim path.
```

Read this audit with:

- `docs/AUTHORITY.md`;
- `docs/single_authority_contract.md`;
- `docs/architecture_freeze_priority_hold_2026_05_20.md`;
- `docs/claim_compiler_and_synthesis_boundary.md`;
- `docs/archive/legacy/ai/openclaw_orchestration_contract_v0.md`.

## Audit Method

This snapshot came from:

- six read-only sub-agent audits:
  - backend API/service architecture;
  - frontend app/components;
  - database/data ownership;
  - tests/fixtures/CI;
  - ops/runtime/topology;
  - docs/code drift;
- local source-size scan;
- local debt-keyword scan;
- current git status check.

No files were edited by the agents. No full test suite was run for this audit.
One agent collected `1049` backend tests and `5` inference-engine tests, and
ran the static topology contract successfully.

## Codebase Shape

Scanned source/script areas:

```text
source/script files: about 430
Python: about 74k lines across 317 files
TSX: about 22k lines across 84 files
```

Largest current hotspots:

| Lines | File | Read |
|---:|---|---|
| 3129 | `backend/app/api/v1/endpoints/analytics.py` | Analytics monolith. |
| 2150 | `backend/app/services/jarvis_tools.py` | Operator/assistant tool island. |
| 1676 | `backend/app/services/stopwatch_manager.py` | Stopwatch lifecycle god service. |
| 1639 | `backend/app/db/models.py` | Giant ORM model file. |
| 1542 | `backend/app/api/v1/endpoints/operator.py` | Cockpit metrics and invariant logic inline. |
| 1512 | `frontend/components/new-task-modal.tsx` | Draft, parser, deadline, nudge, submit, exposure logic fused. |
| 1325 | `backend/app/services/task_manager.py` | Task mutation, parser, exposure, cache, integration effects. |
| 1213 | `frontend/app/(app)/today/page.tsx` | Dense execution page with many state paths. |
| 1055 | `backend/app/services/exposure_ledger.py` | Exposure logic plus compatibility paths. |
| 1049 | `frontend/app/(app)/calendar/page.tsx` | Schedule view plus mutation affordances. |
| 978 | `frontend/components/pulse/PulseAcademicPressureMap.tsx` | Planning, estimation, task creation, conflicts, UI fused. |
| 962 | `backend/app/api/v1/endpoints/tasks.py` | Task route writes still bypass some manager boundaries. |
| 940 | `backend/app/services/brain_dump_parser.py` | Capture parser plus binding/candidate logic. |
| 895 | `backend/app/services/output_surfaces.py` | Surface registry, render, suppression, legacy adapters. |

The largest files are not just long. Several are long because they combine
transport, policy, mutation, exposure, diagnostics, and presentation shaping.

## Severity By Area

| Area | Severity | Why |
|---|---:|---|
| Backend routes/services | 8 / 10 | `analytics.py`, `operator.py`, `task_manager.py`, and `stopwatch_manager.py` mix orchestration, queries, mutation, exposure, and response shaping. |
| Data model/provenance | 7.5 / 10 | Giant ORM file, nullable truth fields, manual user-data registry, provider provenance strings, and export/delete coverage risk. |
| Frontend | 6.5 / 10 | Big components and duplicated state machines, but screen roles are mostly recoverable. Cache invalidation and stopwatch/brain-dump duplication are the main risks. |
| Ops/runtime | 8 / 10 | Public boot path split-brain, duplicated topology/env assumptions, Cloudflare/OpenClaw relay fragility, and Docker build context risk. |
| Tests/CI | 6 / 10 | Good test volume, weaker gate fidelity. Redis tests may skip, Alembic migrations are not fully exercised, browser smoke is operational rather than CI-grade. |
| Docs/code drift | 7 / 10 | New authority docs are stronger, but older docs and public copy still imply stale or inflated authority. |

## Immediate Sharp Footguns

These are not aesthetic refactors. They are risk reducers.

1. **Docker build context may include ignored secrets/data.**
   - Files: `backend/Dockerfile`, missing `.dockerignore`,
     `backend/.env`, `backend/lyra.db`, `docker-compose.yml`.
   - Risk: Git ignores secrets/data, but Docker does not. `COPY . .` can pull
     local secret/data files into the image build context.
   - First fix when implementation resumes: add Docker ignore coverage and
     split dev bind-mount image from production image behavior.

2. **Public runtime boot authority is split.**
   - Files: `scripts/start_public_after_reboot.ps1`,
     `scripts/restart_frontend_wsl.ps1`,
     `scripts/restart_public_frontend.ps1`,
     `scripts/watch_public_runtime.ps1`.
   - Risk: multiple scripts start/restart public frontend differently, with
     different WSL/process/topology assumptions.
   - Direction: make one public frontend restart path authoritative.

3. **Notification/exposure render truth still has two modes.**
   - Files: `backend/app/services/output_surfaces.py`,
     `backend/app/services/notification_lifecycle.py`,
     `backend/app/workers/jobs/reminders.py`,
     `backend/app/workers/jobs/pause_prediction.py`,
     `backend/app/workers/jobs/resume_prediction.py`,
     `backend/app/workers/jobs/timer_overflow.py`.
   - Risk: timer overflow is close to the correct queued-then-browser-render
     pattern; reminders/pause/resume still have paths that can log render at
     enqueue/fire time.
   - Direction: all notification workers should create queued decisions and
     let browser render create render truth. Acknowledgement, dismissal, and
     action are separate interaction outcomes.

4. **Jarvis write authority remains live in code.**
   - Files: `backend/app/api/v1/endpoints/jarvis.py`,
     `backend/app/services/jarvis_tools.py`,
     `openclaw/skills/lyra-secretary/SKILL.md`.
   - Risk: docs now say Jarvis should be parked/read-only unless reauthorized,
     but code still contains mutation-capable assistant paths.
   - Direction: server-stored pending invocation IDs first; then route any
     remaining writes through canonical managers; then park or remove.

5. **Moodle WS can bypass canonical deadline mutation paths.**
   - Files: `backend/app/services/moodle_submissions_sync.py`,
     `backend/app/services/deadline_manager.py`,
     `backend/app/services/moodle_ics_sync.py`.
   - Risk: provider backfill can create deadline rows directly while iCal uses
     manager-owned paths.
   - Direction: route provider backfill through provider-aware deadline
     mutation authority.

## Refactor Strategy

Do not start by splitting the largest files. That would move the knots without
removing them.

Safer sequence:

1. Add `.dockerignore`, ownership manifests, and guardrails.
2. Centralize query semantics and provenance vocabulary.
3. Seal mutation boundaries.
4. Normalize notification/exposure lifecycle.
5. Normalize provider fact import paths.
6. Extract frontend cache/mutation contracts.
7. Split large files after the boundaries exist.

The sequence matters because a move-only split of a god module before ownership
guardrails can create many smaller god modules.

## Backend Refactor Candidates

### 1. Analytics API Monolith

Files:

- `backend/app/api/v1/endpoints/analytics.py`

Risk:

- about 3.1k lines;
- mixes analytics queries, insight generation, exposure writes, Redis
  cooldowns, operator diagnostics, bias/deadline/archetype metrics;
- some read endpoints commit exposure rows.

Direction:

- split into route-thin endpoints plus services:
  - insights;
  - deadline analytics;
  - bias factor;
  - archetype;
  - operator diagnostics;
- do this only after Cortex clean-query ownership is centralized.

### 2. Operator/Admin Dashboards

Files:

- `backend/app/api/v1/endpoints/operator.py`;
- `backend/app/api/v1/endpoints/admin.py`;
- `frontend/app/(app)/operator/page.tsx`;
- `frontend/app/(app)/admin/dashboard/page.tsx`.

Risk:

- cross-user scoping is disabled by necessity inside operator logic;
- cohort, privacy, provider, notification, and state-invariant logic are
  computed inline;
- admin dashboard can disagree with operator cockpit.

Direction:

- create `operator_dashboard_service` with named metric builders;
- make cross-user query boundary explicit;
- fold useful admin dashboard remnants into operator or mark historical.

### 3. Task Mutation Boundary Leak

Files:

- `backend/app/services/task_manager.py`;
- `backend/app/api/v1/endpoints/tasks.py`.

Risk:

- `TaskManager` claims single mutation authority, but routes still directly
  mutate/commit task fields for void, skip, LLM binding, and deadline binding;
- manager owns parser, deadline heuristics, Notion queueing, Redis/cache,
  onboarding stamps, and exposure writes.

Direction:

- introduce focused command services:
  - `TaskLifecycleCommands`;
  - `TaskDeadlineBindingCommands`;
  - `TaskIntegrationEffects`;
- route all task writes through canonical commands.

### 4. Stopwatch Lifecycle God Service

Files:

- `backend/app/services/stopwatch_manager.py`;
- `backend/app/api/v1/endpoints/stopwatch.py`;
- `frontend/components/active-timer-banner.tsx`;
- `frontend/components/pulse/PulseFocusCard.tsx`.

Risk:

- DB session state, Redis active/pause state, task transitions, interruption
  handling, stale repair, Notion queueing, and feedback surfaces are coupled;
- stop flow can have multiple commits and post-effects.

Direction:

- split into:
  - `StopwatchStateStore`;
  - `SessionLifecycleService`;
  - `TaskExecutionFinalizer`;
  - post-commit effects.

### 5. Auth/Scoping/Topology Coupling

Files:

- `backend/app/main.py`;
- `backend/app/api/deps.py`;
- `backend/app/core/security.py`;
- `backend/app/db/scoping.py`;
- `backend/app/services/runtime_topology.py`.

Risk:

- identity resolution, auto-provisioning, audit/mail side effects,
  test-only identity headers, topology assumptions, and ORM auto-scoping are
  spread across layers;
- scoping can be invisible and no-op when unset.

Direction:

- centralize into:
  - `IdentityResolver`;
  - `UserProvisioningService`;
  - explicit `RequestUserContext`;
- reduce dependence on global context variables.

## Frontend Refactor Candidates

### 1. Cache And Mutation Contract

Files:

- `frontend/components/active-timer-banner.tsx`;
- `frontend/components/pulse/PulseFocusCard.tsx`;
- `frontend/components/pulse/BrainDumpQuickModal.tsx`;
- `frontend/components/integrations-section.tsx`;
- `frontend/components/providers.tsx`;
- `frontend/app/(app)/today/page.tsx`.

Risk:

- query keys and invalidations are hand-written across the app;
- optimistic update shapes are duplicated.

Direction:

- create a `queryKeys` module;
- create `invalidateDomain()` helpers for task, stopwatch, deadline,
  notification, integration, and insight domains.

### 2. New Task Modal

Files:

- `frontend/components/new-task-modal.tsx`.

Risk:

- about 1.5k lines;
- combines draft state, time math, calibration nudge, exposure acking,
  parser preview, create/edit/interruption submits, and deadline picker.

Direction:

- extract:
  - `useTaskDraft`;
  - `useCreationNudge`;
  - `useDeadlinePreview`;
  - `useTaskSubmit`;
  - `DeadlinePickerSlot`.

### 3. Frontend Task API God Module

Files:

- `frontend/lib/tasks.ts`.

Risk:

- one module owns task types, CRUD, stopwatch, notifications, analytics, bias
  lookup, categories, retroactive logging, and LLM binding.

Direction:

- split into domain clients:
  - `tasks`;
  - `stopwatch`;
  - `notifications`;
  - `analytics`;
  - `llm-bindings`;
- keep a temporary re-export shim.

### 4. Stopwatch State Machines

Files:

- `frontend/components/active-timer-banner.tsx`;
- `frontend/components/pulse/PulseFocusCard.tsx`;
- `frontend/components/pulse/RadialFocusTimer.tsx`;
- `frontend/app/(app)/today/page.tsx`.

Risk:

- pause/resume/start/stop/switch behavior, elapsed anchoring, and optimistic
  rollback are implemented with subtle differences.

Direction:

- extract `useStopwatchController`;
- extract `useElapsedTimer`;
- migrate banner first, then Pulse focus, then Today handlers.

### 5. Brain Dump Flow Duplication

Files:

- `frontend/components/onboarding-flow.tsx`;
- `frontend/components/pulse/BrainDumpQuickModal.tsx`;
- `frontend/lib/brain-dump.ts`.

Risk:

- parse/confirm/review-failure state machine, binding choice logic, failure
  copy, and local time helpers exist in multiple places.

Direction:

- create a shared brain-dump reducer;
- keep onboarding and Pulse modal as shells.

## Data Model Refactor Candidates

### 1. User Data Ownership Manifest

Files:

- `backend/app/services/user_data_registry.py`;
- `backend/app/api/v1/endpoints/users.py`;
- `backend/tests/test_raw_sql_user_scope_scan.py`;
- `backend/app/db/models.py`.

Risk:

- export/delete/scoping coverage is hand-maintained;
- intentional retention exceptions are not represented as a full ownership
  manifest;
- future user-owned tables can be missed.

Direction:

- create a model/table ownership manifest with:
  - export policy;
  - delete policy;
  - retain/anonymize policy;
  - secret redaction policy;
  - runtime purge policy;
  - test coverage generation.

### 2. Canonical Clean Data Query Specs

Files:

- `backend/app/db/models.py`;
- `backend/app/db/scoping.py`;
- `backend/app/api/v1/endpoints/analytics.py`;
- `backend/app/services/cortex.py`.

Risk:

- filters like `voided_at IS NULL`, `external_source IS NULL`, and
  `data_quality_flag IS NULL` are partly repeated and partly comment-enforced.

Direction:

- add shared query helpers for active/native/clean profiles before moving more
  analytics code.

### 3. Provider Connection Model

Files:

- `backend/app/db/models.py`;
- `backend/app/api/v1/endpoints/integrations.py`;
- `docs/integrations_architecture.md`;
- `backend/app/utils/encryption.py`.

Risk:

- `User` owns identity, consent, onboarding, Google, Moodle iCal, Moodle WS,
  sync status, and disconnect reason;
- this will not scale past a few integrations.

Direction:

- introduce `integration_connection` / credential-state rows later;
- migrate provider fields out of `User` only after the registry and tests are
  ready.

### 4. Provenance Vocabulary Registry

Files:

- `backend/app/db/models.py`;
- `backend/app/services/cortex.py`;
- `backend/app/core/research_contracts.py`.

Risk:

- provenance appears as `source`, `external_source`,
  `deadline_match_source`, `completion_source`, `time_provenance`,
  `provenance`, and provider authority labels.

Direction:

- centralize constants/enums before tightening migrations or analytics.

## Ops And Runtime Refactor Candidates

### 1. Public Boot Path

Files:

- `scripts/start_public_after_reboot.ps1`;
- `scripts/restart_frontend_wsl.ps1`;
- `scripts/restart_public_frontend.ps1`;
- `scripts/watch_public_runtime.ps1`.

Risk:

- several scripts start/restart the same public frontend in different ways.

Direction:

- nominate one public frontend restart authority;
- make the other scripts call it or rename them local-only.

### 2. Runtime Topology Values

Files:

- `runtime_topology.json`;
- `frontend/scripts/public-topology.mjs`;
- `frontend/app/api/topology/route.ts`;
- `frontend/lib/api.ts`;
- `backend/app/services/runtime_topology.py`;
- `backend/app/core/config.py`.

Risk:

- `localhost`, `lyraos.org`, and `api.lyraos.org` are copied across JS, TS,
  Python, tests, and scripts.

Direction:

- make `runtime_topology.json` drive frontend env, backend CORS defaults, and
  verifier expectations.

### 3. Env Surfaces

Files:

- `.env.example`;
- `.env`;
- `backend/.env`;
- `frontend/.env.local`;
- `docker-compose.yml`;
- `backend/app/core/config.py`;
- `frontend/lib/auth.ts`.

Risk:

- config comes from multiple env files and Compose interpolation paths;
- `.env.example` can lag runtime settings.

Direction:

- define one env manifest with owner, runtime, sensitivity, and redacted
  verification.

### 4. OpenClaw Relay Reliability

Files:

- `scripts/openclaw_operator_relay.mjs`;
- `scripts/start_openclaw_operator_relay.ps1`;
- `backend/app/services/operator_notifier.py`.

Risk:

- relay uses list pop semantics; an item can be removed before Telegram send;
- send failure handling is weaker than malformed JSON requeue;
- relay is copied to `/tmp` and supervised by `nohup`.

Direction:

- move toward stream/in-flight ack semantics;
- package relay as a service/sidecar with healthcheck and restart policy.

## Tests And CI Refactor Candidates

### 1. DB Test Lifecycle And Factories

Files:

- `backend/tests/conftest.py`;
- `backend/tests/test_analytics_deadline_shape.py`;
- `backend/tests/test_multiuser_isolation_adversarial.py`.

Risk:

- shared in-memory SQLite plus scattered cleanup makes schema changes fragile.

Direction:

- metadata-driven cleanup;
- shared user/task/deadline/session factories.

### 2. Redis Integration Split

Files:

- `backend/tests/test_state_consistency.py`;
- `backend/tests/test_stopwatch_switch.py`;
- `backend/tests/test_wave2_idempotency.py`;
- `backend/tests/test_brain_dump_endpoint.py`.

Risk:

- many Redis-dependent tests can skip when live Redis is unavailable.

Direction:

- introduce Redis pytest marker;
- fake Redis for deterministic behavior tests;
- CI Redis service for integration tests.

### 3. Alembic Verification

Files:

- `backend/tests/conftest.py`;
- `backend/tests/test_migration_033_deadline_foundation.py`;
- `.github/workflows/ci.yml`.

Risk:

- tests use `Base.metadata.create_all`;
- many Alembic revisions are not exercised by CI.

Direction:

- add `alembic upgrade head` on fresh DB;
- add model-vs-migrated-schema parity check.

### 4. Browser Smoke Harness

Files:

- `scripts/browser_smoke_two_users.mjs`;
- `scripts/browser_stress_operator_readonly.mjs`;
- `scripts/verify_runtime_topology.mjs`.

Risk:

- cookie parsing, topology defaults, account assumptions, and assertions are
  duplicated;
- scripts are good operational tools but weak CI gates.

Direction:

- shared Playwright/auth/topology helpers;
- local seeded-auth mode;
- minimal CI smoke later.

## Docs And Code Drift Candidates

### 1. Authority Chain Has Multiple Top Docs

Files:

- `docs/AUTHORITY.md`;
- `docs/current_transition_state.md`;
- `docs/archive/legacy/planning/building_phases.md`;
- `docs/AGENT_HANDOFF.md`;
- `docs/audits/doc_alignment_findings_2026_06_04.csv`.

Risk:

- older docs still imply they are the primary source of truth.

Direction:

- make `AUTHORITY.md` the live map;
- split authorizing vs contextual transition state;
- mark roadmap/handoff docs historical or subordinate.

### 2. Public AI-Readable Copy Outruns Freeze

Files:

- `README.md`;
- `frontend/public/llms.txt`;
- `frontend/public/lyraos.md`;
- `docs/architecture_freeze_priority_hold_2026_05_20.md`;
- `docs/claim_compiler_and_synthesis_boundary.md`.

Risk:

- public copy can imply AI-native behavioral prediction while freeze docs
  explicitly prohibit AI synthesis and claim inflation.

Direction:

- create one current product-facts source;
- regenerate public copy from bounded claims.

### 3. Deadline And Academic Docs Read Too Active

Files:

- `docs/archive/legacy/provider_academic/deadline_mechanism_design.md`;
- `docs/archive/legacy/provider_academic/academic_execution_substrate.md`;
- `docs/archive/legacy/provider_academic/academic_asset_velocity_and_evidence_fusion_plan.md`;
- `docs/archive/legacy/provider_academic/provider_adapter_contract.md`.

Risk:

- some docs mix parked passive tracking or intervention ideas with active
  substrate language.

Direction:

- add non-authorizing banners where missing;
- move valid invariants into active contracts;
- keep passive/provider-specific ideas parked.

## Existing Double-Minded Surfaces To Preserve In Refactor Planning

This audit builds on the prior redundancy audit. Keep these fracture lines in
scope during refactors:

| Fracture | Required boundary |
|---|---|
| Jarvis vs OpenClaw | OpenClaw is operator reasoning shell; Jarvis is parked/read-only/thin compatibility unless reauthorized. |
| Parser vs brain dump vs LLM enrichment | Deterministic extraction and `deadline_heuristic.score_deadlines()` own candidate scoring; LLM enrichment annotates only. |
| Notifications vs exposure vs relay | Queue insertion is not exposure; delivery is not exposure; browser render creates exposure-render truth; dismissal/ack/action are interaction outcomes. |
| Analytics vs Cortex vs ClaimCompiler | Analytics endpoints expose compiled products only; Cortex/registered computation modules own clean-profile computations; ClaimCompiler owns bounded claim emission. |
| Moodle iCal vs Moodle WS | Provider facts route through canonical provider/deadline/evidence paths. |
| Pulse / Today / Calendar / Table | Many views are fine if authority is clear. |

## Suggested Refactor Waves

### Wave R0 - Safety Rails Before Extraction

Scope:

- `.dockerignore`;
- env manifest;
- topology manifest ownership;
- `surface_authority_registry.json` or equivalent markdown registry for every
  mutation-capable surface;
- user-data ownership manifest;
- clean-data query helper specs;
- provenance vocabulary registry;
- frontend `queryKeys` and `invalidateDomain()`.

Goal:

```text
Make wrong authority easier to detect before moving code.
```

### Wave R1 - Runtime And Exposure Authority

Scope:

- one public frontend boot authority;
- one OpenClaw relay/delivery path;
- notification workers use queued decision plus browser render truth, with
  ack/dismiss/action stored as separate interaction outcomes;
- Jarvis direct writes frozen or routed through canonical managers;
- Moodle WS backfill through canonical deadline manager path.

Goal:

```text
Remove duplicate runtime truth authority.
```

### Wave R2 - Test Gate Fidelity

Scope:

- metadata-driven DB cleanup;
- domain factories;
- Redis marker/fake/svc split;
- Alembic `upgrade head` CI smoke;
- reusable browser smoke harness;
- static architecture scans grouped as explicit guardrails.

Goal:

```text
Make refactors less scary before splitting large modules.
```

### Wave R3 - Frontend Domain Extraction

Scope:

- split `frontend/lib/tasks.ts` behind a re-export shim;
- extract task modal hooks;
- extract stopwatch controller and elapsed timer hooks;
- extract brain dump reducer/presentation primitives;
- extract academic pressure pure planning functions.

Goal:

```text
Reduce duplicated UI state machines without changing product behavior.
```

### Wave R4 - Backend Domain Extraction

Scope:

- analytics service split after Cortex query helpers exist;
- operator dashboard service;
- task lifecycle/binding command services;
- stopwatch state store/lifecycle/finalizer split;
- output surface registry/gate/writer/diagnostics split;
- model-file move-only split after ownership tests exist.

Goal:

```text
Turn god modules into domain modules without changing authority.
```

### Wave R5 - Docs And Public Copy Alignment

Scope:

- mark stale top docs historical/subordinate;
- create deletion/parking ledger per active stabilization wave;
- rewrite Moodle/provider docs to candidate/provenance language;
- align public AI-readable copy with freeze and ClaimCompiler boundary.

Goal:

```text
Stop stale docs from resurrecting old architecture.
```

## What Not To Do

Do not:

- begin a grand rewrite;
- split `models.py`, `analytics.py`, or `stopwatch_manager.py` before
  guardrails exist;
- delete Jarvis before freezing or routing write authority;
- add new AI synthesis or behavior equations during the freeze;
- add new provider adapters before provider facts and provenance are normalized;
- treat UI overlap as the core problem;
- refactor tests after deleting the behavior they protect.

## Current State In One Sentence

LyraOS has a coherent product loop and strong research instincts, but its code
now needs authority-sealing refactors: fewer sovereign modules, clearer
mutation paths, stricter exposure truth, safer provider facts, and a more
boring runtime topology.
