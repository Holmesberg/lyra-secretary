# Lyra Secretary v1.5 - Comprehensive Technical Summary

> **Snapshot date:** 2026-05-09
> **Repository state:** 437 commits, 47 Alembic migrations, 74 backend test files
> **Status:** Pre-alpha dogfood, operator plus small alpha cohort

---

## 1. System Identity

Lyra Secretary is a low-friction productivity product wrapped around a
research-grade behavioral measurement system.

It is not a generic todo app. It is a controlled observational system embedded
in a product, built to study whether humans are wrong about their own execution
capacity in structured, modelable ways.

Primary research question:

```text
Are humans wrong about themselves in a structured, modelable way that predicts failure?
```

The product layer helps users plan, execute, recover, and return. The research
layer interprets the behavioral trace under explicit clean-data, exposure, and
provenance contracts.

The current doctrine is:

- mirror, do not judge
- keep the user-burden surface fixed by default
- maximize information gain per unit user friction
- never treat derived metrics or latent hypotheses as observed truth
- do not treat post-exposure behavior as natural baseline unless the exposure
  context gate returns clean

Canonical governance lives in:

- `MANIFESTO.md`
- `docs/cortex_contract_v0.md`
- `docs/cortex_product_research_contract_v0.md`
- `docs/openclaw_orchestration_contract_v0.md`

---

## 2. Current Architecture At A Glance

```text
Next.js Web UI
  -> FastAPI v1 API
  -> Service layer mutation authorities
  -> SQLAlchemy models / Supabase Postgres
  -> Redis hot state and queues
  -> APScheduler workers

Research/inference side:
  raw events
  -> Cortex read-time projections
  -> Exposure Ledger baseline gate
  -> bias factor / pause / archetype / diagnostics

Operator tooling:
  JARVIS in-app assistant
  OpenClaw multi-agent runtime
  Telegram notifications
```

The user-facing product is the web app. Telegram, JARVIS, and OpenClaw are
operator-only unless a successor contract explicitly promotes them.

---

## 3. Technical Stack

### Frontend

| Layer | Technology |
| --- | --- |
| Framework | Next.js 15.5.15, App Router |
| Language | TypeScript 5.6 |
| Runtime | React 18 |
| Styling | Tailwind CSS, custom dark visual system |
| Server state | TanStack Query v5 with persisted query support |
| Auth | NextAuth.js with Google OAuth |
| UI libraries | Radix primitives, Lucide icons, Tremor charts, Schedule-X calendar, Motion, Sonner |

### Backend

| Layer | Technology |
| --- | --- |
| Framework | FastAPI 0.109, Uvicorn |
| Language | Python 3.11 |
| ORM | SQLAlchemy 2.0 typed models |
| Migrations | Alembic, 47 revisions |
| Primary database | Supabase Postgres in production, SQLite in dev/tests |
| Cache / hot state | Redis |
| Background jobs | APScheduler `BackgroundScheduler` |
| Validation/settings | Pydantic v2, pydantic-settings |

### AI / Operator Runtime

| Surface | Runtime |
| --- | --- |
| JARVIS cloud model | NVIDIA NIM OpenAI-compatible API, default `moonshotai/kimi-k2.6` |
| JARVIS local fallback / enrichment | Ollama, default `qwen2.5:3b` |
| OpenClaw synthesis | `nvidia/moonshotai/kimi-k2.6` |
| OpenClaw implementation/adversary | `openai-codex/gpt-5.5` via Codex OAuth |
| OpenClaw exploration/adversary | `google/gemini-2.5-flash` |

Structured parser calls disable model-native thinking when strict JSON is
required. Operator chat may enable Kimi thinking. Non-operator users stay on
local/Ollama paths unless a later privacy contract changes that.

### Infrastructure

| Layer | Technology |
| --- | --- |
| Public host | `lyraos.org` and `api.lyraos.org` |
| Edge | Cloudflare Tunnel from operator host |
| Containers | Docker / Docker Compose |
| Notifications | Telegram Bot API for operator alerts and prediction flows |
| External sync | Notion, Google Calendar, Moodle iCal, Moodle Web Services |

---

## 4. Frontend Architecture

### 4.1 App Routes

| Route | Purpose |
| --- | --- |
| `/` | Landing page with live product/research positioning |
| `/today` | Main execution surface: task list, timer controls, quick capture |
| `/calendar` | Schedule-X calendar with Lyra tasks and Google Calendar overlay |
| `/pulse` | Operational dashboard and fast capture/recovery surface |
| `/deadlines` | Native and Moodle-imported deadline management |
| `/insights` | User-facing behavioral pattern summaries and archetype proximity |
| `/settings` | Integrations, timezone, archetype survey, account settings |
| `/admin/dashboard` | Operator-only system and cohort dashboard |
| `/table` | Raw task table with filters and bulk actions |
| `/privacy`, `/terms` | Legal pages |

There is no standalone `/onboarding` route in the current app tree.
Onboarding is a component-level flow gated inside the app shell.

### 4.2 Important Components

| Component | Role |
| --- | --- |
| `app-shell.tsx` | Authenticated layout, sidebar, JARVIS launcher |
| `active-timer-banner.tsx` | Persistent stopwatch, pause/resume/stop, switch, overrun check-in |
| `task-row.tsx` | Task list actions, state affordances, overdue recovery |
| `new-task-modal.tsx` | Task creation, time/duration picking, deadline binding, calibration nudge |
| `onboarding-flow.tsx` | Brain-dump onboarding ritual |
| `BrainDumpQuickModal.tsx` | Pulse quick-capture brain dump |
| `readiness-modal.tsx` | Existing pre-task self-report |
| `reflection-modal.tsx` | Existing post-task self-report, scope outcome, completion percentage |
| `retroactive-modal.tsx` | Retroactive completion flow |
| `pause-prediction-banner.tsx` | Pause prediction surface |
| `resume-prediction-banner.tsx` | Resume prediction surface |
| `pause-confirm-chip.tsx` | Retroactive pause confirmation |
| `archetype-proximity-display.tsx` | Dynamic posterior display for archetype proximity |
| `archetype-survey.tsx` | 29-item archetype survey and skip/default flow |
| `llm-enrichment-chip.tsx` | Deadline binding candidate confirmation |
| `integrations-section.tsx` | Google Calendar and Moodle integration cards |
| `JarvisChatModal.tsx` | Operator-only JARVIS chat UI with confirmation actions |

### 4.3 UI Inference Boundary

The frontend can display insights, nudges, predictions, and mirrors, but those
surfaces are intervention candidates. Any future learning path that consumes
post-exposure behavior must go through exposure context evaluation first.

---

## 5. API Surface

All backend routes are mounted under `/v1`.

| Module | Main responsibility |
| --- | --- |
| `analytics.py` | Discrepancy, insights, Cortex diagnostics, exposure policy logs, cascade, bias factor, pause prediction, deadlines, archetypes |
| `tasks.py` | Create, reschedule, delete, void, mark abandoned, mark overdue done, swap, LLM binding confirmation/rejection |
| `stopwatch.py` | Start, pause, resume, stop, status, switch, completion update, readiness correction, retroactive logging |
| `users.py` | `/users/me`, onboarding/tutorial stamps, archetype survey/skip, consent, export, deletion summary, deletion |
| `query.py` | Range-based task querying and last-task lookup |
| `brain_dump.py` | Brain-dump parse and commit |
| `deadlines.py` | Deadline CRUD and state transitions |
| `calendar.py` | Google Calendar events and attendance reports |
| `moodle.py` | Moodle iCal preview/connect/sync and Web Services connect/sync |
| `integrations.py` | Integration status |
| `pause_predictions.py` | Pause prediction response and confirmation endpoints |
| `reflection_view.py` | Reflection exposure/view/dismiss logging |
| `jarvis.py` | Operator JARVIS ask, confirm, health, stream |
| `admin.py` | Operator dashboard and alpha funnel |
| `health.py` | Health and environment invariant checks |
| `feedback.py` | Alpha feedback and operator resolution |
| `notifications.py` | Push/pending/operator notification bridge |
| `parse.py` | Single task parse and deadline preview |
| `undo.py` | Redis-backed undo |
| `skill_check.py` | OpenClaw skill ping |

---

## 6. Persistence Model

### 6.1 Core Tables

| Table/model | Purpose |
| --- | --- |
| `Task` | Core lifecycle object: planned/executed time, state, self-reports, deadlines, LLM enrichment, voiding, substitution |
| `StopwatchSession` | Timer sessions, paused time, completion percentage, data quality flags |
| `PauseEvent` | Pause/resume events with reason, initiator, active elapsed snapshot, retroactive flag |
| `Deadline` | Native and imported deadline records |
| `TaskDeadlineOutcome` | Frozen-at-compute deadline outcome for executed deadline-bound tasks |
| `User` | Account, timezone, operator flag, integration tokens, onboarding/funnel stamps |
| `Archetype` | Seeded archetype priors |
| `ArchetypeAssignment` | Survey/skip assignments plus raw responses |
| `CategoryMapping` | Keyword-to-category seed mapping |
| `ExternalEventOutcome` | Google Calendar attendance self-reports |
| `Feedback` | Alpha bug/suggestion channel |
| `JarvisInvocation` | Operator tool-call audit and pending confirmation state |

### 6.2 Exposure Ledger Tables

Exposure Ledger v0 is implemented as append-only event atoms plus a diagnostic
policy log.

| Table/model | Purpose |
| --- | --- |
| `ExposureDecisionEvent` | Candidate eligibility, show/suppress/delay/fail decisions |
| `ExposureRenderEvent` | Exact rendered stimulus with content hash and snapshot |
| `SuppressionEvent` | Eligible exposure withheld from the user and why |
| `ExposurePolicyEffectLog` | Operator diagnostic snapshot of gate state distributions and ledger-incomplete rates |

Attention proxies and temporal association events are intentionally deferred.
Temporal association must remain correlational only and must not be named as a
causal response link.

### 6.3 Legacy Exposure Sources

The exposure gate also reads existing partial logs through adapters:

- `ReflectionViewLog`
- `CalibrationNudgeEvent`
- `PausePredictionLog`
- `ResumePredictionLog`

Historical coverage is adapter-based in v0; there is no physical backfill.

---

## 7. Task State Machine

```text
PLANNED   -> EXECUTING, SKIPPED, DELETED
EXECUTING -> PAUSED, EXECUTED, SKIPPED
PAUSED    -> EXECUTING, SKIPPED
EXECUTED  -> immutable
SKIPPED   -> DELETED
DELETED   -> immutable
```

Important invariants:

- `EXECUTED` and `DELETED` are immutable.
- `PAUSED -> EXECUTED` is not direct; stopwatch stop auto-resumes first.
- Overdue `PLANNED` or `SKIPPED` tasks may be marked done from product recovery
  surfaces, but this path stamps `initiation_status='retroactive'` and is
  excluded from Cortex measured-execution and planning-calibration baselines.
- `TaskManager` is the single mutation authority for tasks.
- `DeadlineManager` is the single mutation authority for deadlines.

---

## 8. Execution Engine

`StopwatchManager` owns live execution state.

Redis hot keys:

- `active_stopwatch:{user_id}`
- `pause_state:{user_id}`
- undo/idempotency/cache keys namespaced by user

Main flows:

- `start()` stamps initiation delay, creates a `StopwatchSession`, transitions
  `PLANNED -> EXECUTING`, and lazy-stamps first timer start.
- `pause()` creates a `PauseEvent`, records reason/initiator, and transitions
  `EXECUTING -> PAUSED`.
- `resume()` closes the pause, adds paused duration, and transitions
  `PAUSED -> EXECUTING`.
- `stop()` auto-resumes if needed, deducts pauses, guards zero-duration
  sessions, completes the task, and computes stop-time mirrors.
- `switch()` pauses the current task and resumes a paused target atomically.

Recovery:

- `_recover_from_db()` reconstructs state from open sessions and paused tasks.
- `_get_active()` validates Redis state on status poll.
- `orphan_task_recovery` and `stale_session_recovery` workers repair long-lived
  broken states.
- Voiding a task clears associated live stopwatch state.

---

## 9. Cortex Core v0

Cortex is a read-time canonicalization layer in `backend/app/services/cortex.py`.
It does not write state.

Canonical metric vocabulary:

| Symbol | Name | Definition | Space |
| --- | --- | --- | --- |
| `P` | `planned_active_minutes` | planned active work duration | minutes |
| `E` | `executed_active_minutes` | executed active work duration excluding pauses | minutes |
| `W` | `wall_clock_elapsed_minutes` | elapsed wall time | minutes |
| `B` | `paused_minutes` | paused duration | minutes |
| `m` | `execution_multiplier` | `E / P` | ratio |
| `z` | `log_execution_multiplier` | `log(E / P)` | log-ratio |
| - | `active_delta_minutes` | `E - P` | minutes |
| - | `wall_delta_minutes` | `W - P` | minutes |

`bias_factor` remains a legacy/product alias for `execution_multiplier`.
`duration_delta_minutes` remains a legacy property with opposite sign
(`planned - executed`) and must not become the primary Cortex metric.

Cortex clean-data profiles:

- `measured_execution`
- `planning_calibration`
- `pause_process`
- `descriptive_history`

Baseline helpers now call exposure context and fail closed on `UNKNOWN`,
`EXPOSED`, or `INTERVENTION`.

---

## 10. Exposure Ledger v0

Exposure Ledger v0 is a measurement-validity firewall, not an attribution
engine.

Core question:

```text
Can this measurement still be interpreted as baseline under the current
exposure horizon policy?
```

`is_exposed(user_id, event_time, signal_target, horizon_policy_version)` returns
an `ExposureContaminationResult`:

- `state`: `NONE | EXPOSED | INTERVENTION | UNKNOWN`
- `exposure_ids`
- `exposure_categories`
- `signal_target`
- `checked_window_start`
- `checked_window_end`
- `horizon_policy_version`
- `unknown_reason`
- `policy_effect_reason`

`NONE` is the only baseline-clean state. `UNKNOWN` is fail-closed.

Versioned policy lives in `backend/app/core/exposure_horizon_policies.json`.
Current targets include:

- `duration_behavior`
- `planning_estimate`
- `readiness_self_report`
- `reflection_self_report`
- `pause_behavior`
- `deadline_behavior`

Policy auditability is implemented through:

- Cortex diagnostics read-time policy effect counts
- operator-only `POST /v1/analytics/exposure_policy/effect_log`
- `ExposurePolicyEffectLog` rows for state distributions, unknown rates, and
  ledger-incomplete rates

This prevents the horizon policy from becoming invisible truth.

---

## 11. Inference And Learning Paths

### 11.1 Bias Factor / Execution Multiplier

`bias_factor_service.blend()` computes the legacy adaptive estimate while
delegating baseline eligibility to exposure-aware helpers.

Rule 13 blend:

```text
personal_weight   = min(1.0, n_sessions / 30)
archetype_scaling = archetype.prior_bias_factor / 1.30
archetype_prior   = RESEARCH_PRIORS[category] * archetype_scaling
bias_factor_final = (1 - personal_weight) * archetype_prior
                    + personal_weight * personal_ratio
```

Adaptive cascade:

1. category x time_of_day x duration_bucket
2. category x time_of_day
3. category
4. research prior

### 11.2 Inference Engine

`inference_engine.py` classifies hypotheses such as valence and disagreement.
These are inferred labels, not observed truth.

Current valence classes:

- `friction`
- `flow`
- `scope_creep`
- `under_plan`
- `neutral`

Current disagreement classes:

- `optimism_collapse`
- `capacity_surprise`
- `flow_overrun`
- `friction_completion`

### 11.3 Archetype Proximity

`archetype_proximity_service.py` computes Bayesian posterior proximity over
five seeded archetypes using exposure-gated baseline evidence.

Important safeguards:

- square-root effective-sample-size damping
- winsorized observed execution multipliers
- no identity claim; proximity is a time-local posterior hypothesis
- exposed or unknown rows may appear in diagnostics but not baseline archetype
  evidence

### 11.4 Pause And Resume Prediction

Pause predictor mechanisms:

- `clock_anchor`: historical hour/day pause timing
- `work_rhythm`: category-specific time-to-first-pause rhythm

Resume predictor:

- per-category/time-of-day pause duration p75
- absolute cold-start floor
- cooldown and max-fires protection

Prediction logs are exposure-sensitive. Pause/resume training excludes
retroactive self-reports and now gates baseline evidence on `pause_behavior`.

---

## 12. Feedback Mechanisms

Lyra mirrors behavior back to the user without judging it.

Current feedback surfaces:

- micro-mirrors at stop
- calibration nudges at stop
- creation-time calibration nudges
- `/insights` behavioral pattern cards
- archetype proximity display
- pause prediction banners
- resume prediction banners
- deadline binding chips
- overrun/completion check-ins

These surfaces are product value and research contamination at the same time.
They must be treated as exposure candidates before later behavior is considered
naturalistic baseline.

---

## 13. Brain Dump And Parsing

`brain_dump_parser.py` is deterministic and does not depend on an LLM.

Current deterministic parse:

1. split raw text into segments
2. classify segment as task or deadline
3. extract time/date via `dateparser`
4. extract duration from explicit durations and time ranges
5. strip title tokens
6. compute confidence
7. suggest task-deadline bindings

The app also supports a quick-capture brain-dump surface in Pulse. The current
contract forbids casually increasing required user variables; passive or LLM
assistance may reduce friction but must preserve provenance.

---

## 14. LLM Enrichment

`llm_enrichment` is an async worker, not a critical-path dependency.

Flow:

1. select tasks with `llm_parse_status='pending'`
2. attempt NVIDIA NIM when configured
3. fall back to Ollama for transient NIM unavailability
4. validate JSON with Pydantic
5. write `llm_*` fields as suggestions, not canonical truth

LLM enrichment can populate:

- `llm_priority`
- `llm_sub_items`
- `llm_inferred_deadline_id`
- `llm_deadline_candidates`
- `llm_alternative_suggestion`

Trust-not-rewrite contract:

- user-visible or explicit deadline bindings are not silently overwritten
- LLM disagreement is stored as an alternative suggestion
- user confirmation is required to promote a suggestion into canonical state
- sticky rejections prevent repeated suggestion resurfacing

---

## 15. JARVIS And OpenClaw

### 15.1 JARVIS

JARVIS is an operator-only in-app AI assistant.

Agent loop:

1. build Lyra context and tool list
2. call NVIDIA NIM chat completions
3. execute read tools immediately
4. queue write tools for user confirmation
5. cap loop iterations to prevent runaway calls

Write tools require explicit confirmation:

- `create_task`
- `start_focus_session`
- `mark_deadline_done`
- `sync_moodle_now`

JARVIS output is operator tooling, not user behavioral data.

### 15.2 OpenClaw

OpenClaw is a separate Docker stack and operator-only multi-agent runtime.

Current contract:

- Kimi K2.6: synthesis/adjudication
- Codex/GPT-5.5: implementation and structural adversary
- Gemini 2.5 Flash: exploration and epistemic adversary
- local/Gemini fallback: memory summaries

OpenClaw must preserve disagreement, uncertainty, and provenance. It must not
become product research data, bypass Cortex clean-data profiles, or silently
merge agent outputs into consensus.

OpenClaw reaches Lyra via Docker network bridge:

```text
openclaw-gateway -> http://backend:8000
```

The external OpenClaw runtime also carries a local copy of the orchestration
contract.

---

## 16. External Integrations

### Google Calendar

- read-only import
- not persisted as tasks
- rendered as ambient calendar context
- Redis event cache
- OAuth refresh token stored on `User`

### Moodle iCal

- persisted as `Deadline` rows with `external_source='moodle_ics'`
- upserted by external source/id
- private iCal URL stored on `User`
- sync runs every 6 hours

### Moodle Web Services

- detects submitted/graded assignments
- auto-marks matching Moodle deadlines complete
- token is Fernet-encrypted with `fernet:` prefix for new connections

### Notion

- task mirror
- sync deferred through Redis queue
- retry worker drains the queue every 5 minutes

### Telegram

- operator notifications
- pause/resume prediction delivery and command bridge
- not a general alpha user surface

---

## 17. Caching, Scoping, And Security

### Redis Uses

- live stopwatch state
- pause state
- undo cache
- `/users/me` cache
- task range cache
- Notion retry queue
- Google Calendar event cache
- notification queue

### Multi-User Scoping

`app/db/scoping.py` stores current user id in a `ContextVar` and injects
`user_id` filters into ORM queries for user-owned models.

Rules:

- request middleware sets current user id
- background jobs must set current user id per user iteration
- Redis keys are user-namespaced
- raw SQL bypasses auto-scoping and must scope manually

### Credential Status

- `moodle_ws_token` is Fernet-encrypted for new connections
- `google_refresh_token` and `moodle_ics_url` remain plaintext security debt
- secrets must not be logged or returned in API responses

---

## 18. Background Jobs

APScheduler runs in-process with 24-hour misfire grace and coalescing.

| Job | Cadence | Purpose |
| --- | --- | --- |
| `reminders` | 1 min | upcoming task alerts |
| `timer_overflow` | 2 min | overrun/session overflow detection |
| `pause_prediction` | 1 min | VT-17 pause prediction |
| `resume_prediction` | 2 min | resume prediction while paused |
| `reconcile_responses` | 5 min | close pause prediction acceptance windows |
| `notion_sync` | 5 min | retry failed Notion syncs |
| `llm_enrichment` | 5 sec | async LLM task enrichment |
| `orphan_task_recovery` | 15 min | EXECUTING tasks with no active session |
| `stale_session_recovery` | 15 min | unclosed sessions older than threshold |
| `overdue_tasks` | 30 min | auto-skip unstarted overdue tasks |
| `reconcile_deadline_outcomes` | 30 min | write deadline outcome rows |
| `sweep_missed_deadlines` | 1 hr | active deadlines past due -> missed |
| `moodle_ics_sync` | 6 hr | import Moodle iCal deadlines |
| `moodle_submissions_sync` | 6 hr | detect Moodle submissions |

---

## 19. Integrity Guards

Critical guardrails:

- every analytics/research query must filter `voided_at IS NULL`
- `initiation_status='system_error'` and `retroactive` are excluded from
  measured-execution baselines
- external-import deadline-bound rows are excluded from planning calibration
- Cortex is read-only
- derived metrics are recomputed at read time
- latent constructs must never be persisted as observed truth
- `UNKNOWN` never defaults to clean, neutral, bounded, zero, or average
- exposure-gated baseline helpers must be used for learning paths
- repair prompts may ask users to confirm missing lifecycle transitions, but
  inferred transitions cannot silently become measured truth
- no new user-burden variables without successor contract or explicit amendment

---

## 20. Testing And Governance

Backend tests cover:

- multi-user isolation
- task state transitions
- stopwatch/pause/resume behavior
- Cortex metric invariants
- exposure ledger fail-closed behavior
- bias-factor blend behavior
- archetype proximity behavior
- pause/resume prediction behavior
- integration and recovery edge cases

Governance docs:

| Document | Purpose |
| --- | --- |
| `MANIFESTO.md` | Highest-priority research/product constitution |
| `docs/cortex_contract_v0.md` | Canonical Cortex variables, profiles, invariants |
| `docs/cortex_product_research_contract_v0.md` | Product/research boundary and exposure ledger doctrine |
| `docs/openclaw_orchestration_contract_v0.md` | Operator multi-agent runtime contract |
| `docs/calibration_contract.md` | Inference-engine calibration rules |
| `docs/repo_alignment_audit/` | May 2026 alignment audit registries |
| `docs/building_phases.md` | Implementation phasing and shipped/deferred items |

The manifesto must be updated whenever a change touches doctrine, ontology,
measurement semantics, product/research boundaries, or long-term architecture.

---

## 21. Known Risks And Debts

1. Legal/privacy pages still need production-grade text and explicit hosted-LLM
   disclosure.
2. Google refresh tokens and Moodle iCal URLs remain plaintext.
3. Analytics endpoint module is large and mixes older product analytics with
   operator diagnostics.
4. JARVIS tools remain high-entropy operator code and should not become a
   hidden research authority.
5. Exposure Ledger v0 lacks attention proxies and temporal association atoms.
6. Horizon policy is a hypothesis; policy effect logs are needed to detect gate
   drift.
7. Existing historical exposure coverage is adapter-based, not backfilled.
8. Some frontend insight surfaces predate the full exposure ledger and need
   migration to dual-write.
9. Cloudflare Tunnel from the operator host is an operational floor until
   hosting moves off the laptop.
10. React Query state can still desynchronize during complex live-session
    mutation chains.

---

## 22. One-Line Summary

Lyra Secretary is a low-friction scheduling and execution product whose real
architecture is a falsifiable behavioral measurement instrument: product events
become raw observations, Cortex canonicalizes them, the Exposure Ledger gates
baseline validity, and inference systems are allowed to learn only when that
measurement context stays explicit.
