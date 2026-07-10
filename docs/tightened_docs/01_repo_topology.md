# 01 Repo Topology

**Audit date:** 2026-05-08

**Status:** First-pass alignment audit. Treat this as a map of verified anchors
and unresolved areas, not as a complete proof of every file's runtime behavior.
Counts and paths reflect the May 8 audit snapshot and may be stale relative to
current HEAD.

## Evidence Standard

- **Verified code evidence:** file exists and was inspected or found by `rg`.
- **Doc evidence:** repository documentation states a claim, but code was not
  fully traced in this pass.
- **Uncertain:** the repo contains signals of a subsystem, but ownership or
  current runtime status remains unverified.

## Top-Level Map

| Path | Purpose | Layer | Ontology ownership | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| `backend/` | FastAPI app, DB models, task/stopwatch services, analytics, workers | substrate through inference | Owns canonical persistence and most implemented behavior | production/research mix | 45 migrations, 21 endpoint modules, 72 backend tests plus inference tests |
| `frontend/` | Next.js app, operational UI, onboarding, insights, timers, JARVIS UI | UI/product and exposure | Owns user-facing copy and intervention surfaces | production/prototype mix | Large stateful surfaces: `today`, `calendar`, `table`, `new-task-modal` |
| `docs/` | Product, research, governance, plans, stress tests | governance/research | Owns declared theory, not ground truth | research/legacy/speculative mix | Contains many active and historical claims; must be verified against code |
| `docs/tightened_docs/` | This audit output | governance | Owns alignment findings, not implementation truth | historical audit snapshot | First-pass registry generated 2026-05-08 |
| `archive/` | Historical specs, old migration SQL, scripts, PDFs | legacy/archive | No active ontology ownership unless promoted | archive | Potentially useful lineage; not runtime truth |
| `notebooks/` | Operator analytics notebook and local environment | research/prototype | Exploratory analysis only | prototype/legacy | Has embedded `.venv`; should stay out of runtime assumptions |
| `openclaw/` | External agent skill/gateway integration | operator tooling/integration | Operator notification/control bridge | prototype/legacy risk | Skill sync rules exist in `agent bootstrap doc` |
| `scripts/` | One-off bench/stress scripts | experiments | No canonical ownership | prototype | Must not become implicit source of truth |
| `backups/` | SQLite backup | archive | Historical data only | archive | `lyra_pre_pivot_apr09.sqlite` predates current schema |
| `.github/` | Agent instructions | governance | Agent behavior rules | active | Now references Cortex contract |
| `.assistant runtime/` | Local assistant runtime artifacts | governance/operator | Local agent memory/plans | uncertain | Not fully audited |

## Backend Subsystems

| Path | Purpose | Grade | Evidence |
| --- | --- | --- | --- |
| `backend/app/db/models.py` | Core persistence ontology | production-grade but ontology-dense | `Task`, `Deadline`, `StopwatchSession`, `PauseEvent`, prediction logs, nudge logs, reflection logs, JARVIS audit |
| `backend/app/db/scoping.py` | ORM auto-scoping by current user | production-grade safety layer | ContextVar and `before_compile` filter; raw SQL bypass is documented |
| `backend/app/services/task_manager.py` | Main task mutation authority | production-grade/high-risk | 910 lines; owns creation, completion, deadline binding, Notion queue |
| `backend/app/services/stopwatch_manager.py` | Execution engine and timer state | production-grade/high-risk | 1203 lines; owns Redis hot state, pause/resume/stop/switch/recovery |
| `backend/app/services/cortex.py` | Cortex v0 canonicalization helpers | governance/research-grade | Read-time metrics and diagnostics only; no writes |
| `backend/app/services/cortex_clean_profiles.py` | Cortex clean-data profile owner | governance/research-grade | Central measured-execution, planning-calibration, baseline, and pause-process row eligibility helpers; read-only |
| `backend/app/services/inference_engine.py` | Shared valence/disagreement/confidence helpers | research-grade | Uses latent class labels; must stay bounded by contract |
| `backend/app/services/bias_factor_service.py` | Legacy/adaptive execution multiplier pipeline | research-grade active legacy | Uses `bias_factor` alias and Rule 13 shrinkage |
| `backend/app/services/pause_predictor.py` | Pause prediction | research-grade intervention | VT-17 predictor, confidence heuristic, logs via worker |
| `backend/app/services/resume_predictor.py` | Resume prediction | research-grade intervention | Sibling predictor with cold-start cap |
| `backend/app/services/jarvis_*` | Operator LLM tooling and tool registry | operator-only research/prototype | `jarvis_tools.py` is 2007 lines; high entropy risk |
| `backend/app/workers/` | APScheduler jobs | production/research mix | 14 registered jobs in `scheduler.py` |
| `backend/alembic/versions/` | Schema history | production archive | 45 migrations; ontology lineage source |
| `backend/tests/` | Runtime invariants and regression tests | active governance | 72 files; includes multiuser and Cortex tests |

## Frontend Subsystems

| Path | Purpose | Grade | Risk |
| --- | --- | --- | --- |
| `frontend/app/(app)/today/page.tsx` | Main execution surface | production-grade/high-risk | Timer, readiness, reflection, prediction banners, micro-mirrors |
| `frontend/components/new-task-modal.tsx` | Planning input and calibration nudge surface | production/high-risk | Can contaminate planned duration if nudges anchor users |
| `frontend/components/readiness-modal.tsx` | Pre-task self-report | production/instrumentation | Must be named as self-report, not readiness truth |
| `frontend/components/reflection-modal.tsx` | Post-task self-report | production/instrumentation | Must be reflection input, not focus truth |
| `frontend/components/pause-*`, `resume-*` | Predictive interruption surfaces | intervention | Exposure logging is partial and Phase 1 incomplete |
| `frontend/app/(app)/insights/page.tsx` | User-facing inferred patterns | exposure/intervention | Must obey calibration contract and Cortex boundaries |
| `frontend/components/archetype-*` | Archetype survey/proximity display | research exposure | Identity drift and posterior overclaim risk |
| `frontend/components/jarvis/*` | Operator chat UI | operator tooling | Must remain operator-only |
| `frontend/lib/*` | API client wrappers and derived client helpers | UI/product glue | Some client aggregation exists; audit before treating as canonical |

## Major Risk Concentrations

1. `backend/app/services/jarvis_tools.py`: very large operator analytics tool
   that combines many concepts and confidence systems.
2. `backend/app/api/v1/endpoints/analytics.py`: 1528 lines; many older
   user-facing and operator-facing metrics share the same endpoint module.
3. `frontend/components/new-task-modal.tsx`: planning input plus calibration
   intervention in one surface.
4. `frontend/app/(app)/today/page.tsx`: live execution, prediction exposure,
   readiness/reflection, and reflection logging in one surface.
5. `docs/`: high-volume theory layer; several docs may be stale or aspirational.

## Immediate Topology Finding

The repo is not a simple app. It is a layered measurement system whose runtime
truth lives mainly in `backend/app/db/models.py`, `task_manager.py`,
`stopwatch_manager.py`, workers, and endpoint call paths. The documentation layer
contains valuable theory, but it also contains historical claims that must be
treated as hypotheses until re-verified.
