# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Docker (primary dev workflow)
```bash
docker-compose up -d --build
docker-compose exec backend alembic upgrade head
docker-compose exec backend python app/db/seed.py
curl http://localhost:8000/v1/health
```

### Local development
```bash
cd backend/
pip install -r requirements.txt pytest
export PYTHONPATH=.
pytest tests/
pytest tests/test_timezone_contract.py   # run a single test file
```

### Diagram regeneration
```bash
pip install matplotlib
python docs/diagrams/generate_diagrams.py
```

### Frontend — production serving (lyraos.org via Cloudflare Tunnel)
```bash
cd frontend/
npm run build       # ~1-2 min; rebuild after every code change
npm run start       # serves :3000 — this is what Cloudflare Tunnel forwards
```

**Critical:** never use `npm run dev` for traffic served at lyraos.org. The Apr 25 perf incident (`commit TBD`) found the operator was serving `next dev` over the tunnel, shipping ~12MB unminified bundles per page load. Production builds tree-shake to ~190KB initial load for `/today`. Use `dev` only for local iteration on `localhost:3000`.

### Frontend — local development
```bash
cd frontend/
npm run dev         # localhost:3000, hot-reload, full source maps
```

## Architecture

Lyra Secretary is a measurement-backed adaptive task scheduler. It records **planned vs. executed duration** per task to learn behavioral patterns, with a research layer that validates whether its own insights actually predict anything. The `duration_delta_minutes` field (planned − executed) is the core metric.

### Layers

```
Client (Web UI / Telegram / OpenClaw agent)
  ↓ HTTPS (lyraos.org + api.lyraos.org via Cloudflare Tunnel) / localhost in dev
API (FastAPI) — backend/app/api/v1/endpoints/
  ↓ DI via get_db() / get_redis()
Services — backend/app/services/
  ↓
Postgres (Supabase eu-west-1, prod) | SQLite (local dev) + Redis + Notion API
```

**Production deployment** (from April 16, 2026): `https://lyraos.org` (frontend) and `https://api.lyraos.org` (backend) served via Cloudflare Tunnel from the operator's laptop. Primary DB is Supabase Postgres (`xrrboaxptttdzednaxwk`, eu-west-1 pooler on port 6543, sslmode=require). SQLite fallback kept at `.env.backup-sqlite-2026-04-16` for fast revert. Full architecture + recovery playbook in `docs/deployment_architecture.md`.

Background jobs (APScheduler — 14 jobs as of 2026-05-01) run inside the FastAPI process: reminders every 1 min, Notion sync retries every 5 min, timer overflow alerts every 2 min, overdue task detection every 30 min, stale session recovery every 15 min (paused-for-48h → EXECUTED if executed ≥50% planned else SKIPPED; never-paused-for-48h → SKIPPED), orphan task recovery every 15 min (catches EXECUTING tasks with no open session → SKIPPED), VT-17 pause prediction every 1 min per-user (fires + logs + enqueues notification), VT-17 outcome reconciliation every 5 min (closes pause_prediction_log acceptance windows), Loop 11 deadline outcome reconciliation every 30 min (writes task_deadline_outcome rows for EXECUTED deadline-bound tasks), missed-deadline sweep every hour (active → missed transitions), LLM enrichment every 5s (Ollama/NIM async parser for priority/sub-items/deadline candidates), VT-resume-prediction every 2 min (fires resume banner when paused-for ≥ historical p75), Moodle LMS .ics sync every 6 h per connected user (alembic 041, 2026-04-29), Moodle WS submissions sync every 6 h auto-marking deadlines complete on submission detection (alembic 043, 2026-05-01). All jobs run with a global 24h misfire_grace_time + coalesce=true (set 2026-04-30) so APScheduler replays missed jobs on operator-laptop wake instead of dropping them silently.

### Single Mutation Authority

**All task writes go through `TaskManager` (`services/task_manager.py`).** Endpoints never modify tasks directly. This enforces the state machine, conflict detection, Notion sync, and the undo cache in one place.

### Task State Machine

```
PLANNED → EXECUTING ⇄ PAUSED → EXECUTED (immutable)
        ↘ SKIPPED  (immutable terminal, from PLANNED|EXECUTING|PAUSED)
PLANNED → DELETED   (soft delete, immutable)
SKIPPED → DELETED   (soft-delete cleanup only)
```

PAUSED is non-terminal: it must resolve to EXECUTED (via auto-resume on stop)
or SKIPPED (via `POST /v1/tasks/{id}/mark-abandoned`).

Transitions are enforced by `services/state_machine.py`. Completed/skipped/deleted tasks cannot be mutated.

### Redis responsibilities
- Active stopwatch session (survives restart — rehydrated from SQLite)
- Undo cache (30-second TTL per action)
- Idempotency keys (30-second TTL, via `X-Idempotency-Key` header)
- Notion failed-sync queue (retried by APScheduler)

### Key service files
| File | Responsibility |
|------|---------------|
| `services/task_manager.py` | All task CRUD, the one place that calls everything else |
| `services/state_machine.py` | Validates and applies state transitions |
| `services/conflict_detector.py` | Half-open interval `[start, end)` overlap detection |
| `services/stopwatch_manager.py` | Timer lifecycle: start, stop, pause/resume; early-stop gate at <50% planned duration |
| `services/parser.py` | NLP (dateparser) → structured task fields. `parse_chained(text)` handles "then"-separated compound requests. |
| `services/notion_client.py` | Notion API sync; failures enqueued in Redis |
| `services/telegram_notifier.py` | Telegram bot delivery for reminders and overflow alerts |
| `workers/scheduler.py` | APScheduler setup wired into FastAPI lifespan |

### Database schema (10 tables)
- **task** — core entity with planned/executed time pairs, state, Notion page ID
- **stopwatch_session** — one-to-many with task; tracks individual timer runs
- **pause_event** — one-to-many with stopwatch_session; full pause/resume history (VT-17 pause-prediction data source)
- **pause_prediction_log** — fired pause predictions + inferred user responses (VT-17 acceptance-rate analysis)
- **reflection_view_log** — per-fired reflection-surface impression (LYR-098; micro_mirror / calibration_nudge / future archetype reveals); view_id returned on /stopwatch/stop, stamped via /reflection_view/{id}/viewed and /dismissed; feeds /insights history and VT-21 stratified analysis
- **category_mapping** — static keyword→category lookup seeded at init (not learned)
- **user** — authenticated users; retention cohort, consent, anonymized-deletion fields
- **archetype** — static chronotype × discipline profile with prior bias_factor
- **archetype_assignment** — per-user archetype snapshot at onboarding (re-fit later)
- **external_event_outcome** — user-marked outcomes on imported calendar events (Apr 21 alembic 027); H1 queries MUST filter `WHERE external_source IS NULL` to exclude these from research analysis (template per `docs/integrations_architecture.md`)

### OpenClaw integration
OpenClaw runs in a separate Docker Compose stack. Connect the two via Docker network bridge (see `docs/architecture.md §3`). The agent skill definition lives at `openclaw/skills/lyra-secretary/SKILL.md` and must be copied to `~/.openclaw/skills/lyra-secretary/`. Notification delivery is poll-based: the backend enqueues payloads into Redis via `POST /v1/notifications/push` (scheduler-internal) and the agent drains `GET /v1/notifications/pending` every 30 s. No direct push channel to the OpenClaw gateway is used.

## Structural Investigation Rule

Before implementing any feature that touches measurement, data flow, or research-relevant fields, read `docs/design_patterns/structural_investigation_rule.md`. The short version: scan the data domain, the implementation domain, and the research-integrity domain; surface findings (spec-vs-reality gaps, design tensions, VT/Hard Rule adjacencies, reusable infrastructure); propose 2–3 options with pro/con including rejected options; pre-register measurement and kill criteria; halt for operator review before writing code. The full rule — including what triggers it, what exceptions exist, and the motivating incident — is in that doc. Non-optional for any feature with measurement implications.

## Calibration Contract (2026-05-02 system transition)

Before adding any user-facing surface that displays inferred behavior, read `docs/calibration_contract.md`. Doctrine: comparative context before input, confidence tiers required (cold_start / tentative / confirmed at per-user-N, not aggregate), banned vocabulary list, warm tone register, retreat under low confidence, ReflectionViewLog namespace discipline (`telemetry_*` prefix for telemetry, unprefixed for impressions, every payload has event_class + schema_version). Operator-overfit guard: rules promoted from JARVIS-on-operator-data are tagged `operator-only` or `potentially-general`; only the latter ships to non-operator users. Anchor inference to behavioral primitives (transition friction, recovery latency, abandonment topology, action/declaration divergence) not diagnostic categories or topology-specific traits. Full plan in `/home/alina/.claude/plans/alright-listen-up-claude-delegated-garden.md` (operator-local). Companion docs (Phase 1+ landing): `docs/data_utilization_inventory_2026_05_02.md` (signal triage), `docs/jarvis_hypothesis_log.md` (Phase 2 discovery log), `docs/inference_engine_architecture.md` (Phase 3 design), `docs/reflection_view_log_schemas.md` (Phase 6 payload schemas), `docs/dark_column_retirement_log.md` (Phase 5).

The 2026-05-02 reframe: the system's actual problem is data utilization, not complexity. Lyra is a behavioral inference engine, not a productivity app — sensing layer over-built, cortex layer under-built. Every reflection surface added must metabolize signal into user-visible value, with calibrated confidence. See `docs/complexity_stress_test_2026_05_01.md` for the original audit (now postscripted with the reframe).

**Endgame (Phase 7+, Under Provision):** the inference engine is substrate for a calibrated secretary that autonomously plans/recalibrates user time around deadlines. Phase 3 inference outputs must be planning-layer-compatible. Reflection surfaces are the Phase 4 user-visible NOW; the planning layer is the user-visible LATER. Don't lock the inference engine into UI-display shape only.

## System transition — rigorous gates (memory contract)

**These gates are non-negotiable for Claude Code (and any agent using this repo).** Do not advance to the next transition phase by renaming docs or “calling it done.” Verify each criterion against files in git.

**Two calendars:** `docs/building_phases.md` (product/alpha) and the May 2026 **transition** below use **different** phase numbers — reconcile explicitly when you ship (`docs/AGENT_HANDOFF.md` §2).

### Transition phases ↔ hard gates

| Trans. phase | Gate name | Must be true before advancing | Verify in repo |
|--------------|-----------|------------------------------|----------------|
| **0** | Calibration doctrine | No user-facing inferred-behavior change ships without `docs/calibration_contract.md` compliance | Every reflection/telemetry PR: Enforcement checklist at bottom of calibration doc (R1–R10 + R11 where applicable) |
| **1** | Data utilization inventory | Operator disposition table signed | `docs/data_utilization_inventory_2026_05_02.md` §7 (checkboxes + sign-off note) |
| **2** | JARVIS discovery soak | Hypothesis log shows **≥3 PROMOTED** and **≥2 REJECTED**, rejections show **discrimination** (not silent agrees) | `docs/jarvis_hypothesis_log.md` — count **Promoted** vs **Rejected** sections; empty = gate **closed** |
| **3** | Inference engine (expand) | **`docs/inference_engine_architecture.md`** exists and matches code **before** adding new user-facing writers or analytics contracts | Stub forbidden for merge if PR adds inference outputs — at minimum **DRAFT** with threshold table + signal registry |
| **3→4** | Operator-overfit (R8) | Before non-operator reflection copy from promoted hypotheses: **operator + 2 trusted users** show **discrimination**, not signature clone | `docs/calibration_contract.md` R8; halt until operator signs analysis |
| **4** | Reflection surfaces | **R11:** no new blocking round-trips on render paths; prefetched `/me` / `tasks/query`; PR notes **<50ms** smoke vs baseline | `docs/calibration_contract.md` R11 |
| **5** | Dark-column retirement | Writers retired per inventory; **`docs/dark_column_retirement_log.md`** updated when columns drop writers | `docs/data_utilization_inventory_2026_05_02.md` RETIRE rows |
| **6** | Implicit telemetry | Each new `telemetry_*` type documented **before** first write; `ReflectionViewLog` **fire-and-forget** (client never awaits) | `docs/reflection_view_log_schemas.md` (create/update in same PR as schema) |

**Existing code anchors:** `backend/app/services/inference_engine.py` holds **valence + disagreement + R2 tier helpers** — any duplicate classification logic elsewhere must stay in sync or call this module. JARVIS remains **403** for non-operators (`backend/app/api/v1/endpoints/jarvis.py`).

### Mandatory halt conditions (do not “just ship”)

1. **Measurement / research fields touched** → Structural Investigation Rule (`docs/design_patterns/structural_investigation_rule.md`) **before** code — no bypass.
2. **New reflection_type or telemetry** → schema doc + `event_class` discipline (`calibration_contract` R6–R7).
3. **Phase 2 gate empty** → do **not** claim Phase 3 “complete” for user-facing inference — complete **PROMOTED/REJECTED** log first.
4. **Banned vocabulary** on user strings (`calibration_contract` R4) — grep/copy-review on any new UI or API copy.

### Quick verification commands

```bash
# JARVIS / inference primitives (isolated; avoids full tests/conftest if needed)
cd backend && set PYTHONPATH=. && pytest tests_inference_engine/ --confcutdir=tests_inference_engine -q

# Full backend slice (requires venv with deps, e.g. Python 3.11)
cd backend && set PYTHONPATH=. && pytest tests/test_jarvis_phase2_discovery_tools.py tests/test_jarvis_endpoints.py -q
```

## Configuration

Copy `.env.example` to `.env`. Required vars: `DATABASE_URL`, `REDIS_URL`, `NOTION_API_KEY`, `NOTION_DATABASE_ID`, `USER_TIMEZONE` (IANA, e.g. `Africa/Cairo`). `SECRET_KEY` must be ≥ 32 chars. All times are stored as UTC internally; `USER_TIMEZONE` controls display conversion via `utils/time_utils.py`.

## SKILL.md Editing Rules

- Keep `openclaw/skills/lyra-secretary/SKILL.md` **under 150 lines total**.
- Verification preamble must stay first (before Hard Rules).
- Hard Rules must stay at the top, numbered, unchanged structure.
- Every endpoint: method, path, required fields (*), key response fields only — one line.
- Never add prose explanations, curl examples, or markdown tables — bullet points only.
- After any edit, run `wc -l` and reject if over 150.
- **Three-way sync required after ANY SKILL.md edit** — all three locations must match:
  ```bash
  # 1. Source of truth (already edited):
  #    openclaw/skills/lyra-secretary/SKILL.md
  # 2. Copy to host:
  cp "openclaw/skills/lyra-secretary/SKILL.md" "/mnt/c/Users/alina/openclaw/skills/lyra-secretary/SKILL.md"
  # 3. Copy into container:
  docker exec openclaw-openclaw-gateway-1 rm -f /home/node/.openclaw/skills/lyra-secretary/SKILL.md
  docker cp "openclaw/skills/lyra-secretary/SKILL.md" openclaw-openclaw-gateway-1:/home/node/.openclaw/skills/lyra-secretary/SKILL.md
  # 4. Restart gateway:
  cd /mnt/c/Users/alina/openclaw && docker-compose restart
  ```
- Never edit one location without updating the other two.

## Endpoint deprecations

- `POST /v1/parse` — scheduled for deprecation. LLMs should call `/v1/create` directly with structured fields extracted from user input. Use `/v1/parse` only as a last resort for genuinely ambiguous time expressions (e.g. "later", "this evening"). The endpoint now returns `{ tasks: [...], compound: bool }` and supports "then"-chained compound requests via `TaskParser.parse_chained()`.

## Integrations

Third-party integrations (Google Calendar, Notion, ICS, future Outlook/Slack/Gmail) use **incremental OAuth**: sign-in requests only identity scopes (`openid email profile`), and each integration requests its own scopes from Settings → Integrations when the user clicks Connect. Never add sensitive scopes to the NextAuth sign-in config — that breaks signup for anyone not on the Google Cloud Console Testing-mode user list.

Canonical pattern: `docs/integrations_architecture.md`. Adding-a-new-integration checklist + security rules + research-integrity rules all live there. Registry: `frontend/lib/integrations.ts`. Backend status endpoint: `GET /v1/integrations`. OAuth routes: `frontend/app/api/integrations/<provider>/{connect,callback}/route.ts`.

**External data stays out of the `task` table** unless marked with an explicit `external_source` field. The `external_event_outcome` table (Alembic 027) is the template for user-marked outcomes on imported data. H1 research queries must filter `WHERE external_source IS NULL` if this invariant is ever broken.

## Known issues

See `LYRA_BUGS.md` for active bugs. See `archive/lyra_final_spec.md` for the historical product spec (superseded by `docs/building_phases.md` and `docs/project_history.md` as canonical forward/backward-looking documents).
