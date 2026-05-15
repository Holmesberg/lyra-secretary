# LyraOS

[![CI](https://github.com/Holmesberg/lyra-secretary/actions/workflows/ci.yml/badge.svg)](https://github.com/Holmesberg/lyra-secretary/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Repository](https://img.shields.io/badge/GitHub-lyra--secretary-181717?logo=github)](https://github.com/Holmesberg/lyra-secretary)

> A rule-governed behavioral measurement instrument with a productivity interface.

LyraOS helps users plan tasks, execute them with timers, recover from missed
plans, and inspect patterns in their own planning and execution traces. The
deeper system is not an AI wrapper: it is an explicit, probabilistic,
longitudinal instrumentation layer that treats plans as hypotheses and work
sessions as evidence.

The short version:

```text
observe -> canonicalize -> gate by provenance/exposure -> synthesize cautiously
```

![Insights layer screenshot](docs/insights-v2.png)

## Current Status

LyraOS is pre-alpha dogfood with the operator plus a small alpha cohort. It is
live at:

- Frontend: `https://lyraos.org`
- API: `https://api.lyraos.org`

This repository contains the product app, backend API, research/governance
contracts, operator tooling, and historical design notes. Current doctrine and
professor-facing orientation live in:

- [MANIFESTO.md](MANIFESTO.md)
- [docs/professor_review_packet.md](docs/professor_review_packet.md)
- [docs/behavioral_instrumentation_doctrine.md](docs/behavioral_instrumentation_doctrine.md)
- [docs/cortex_product_research_contract_v0.md](docs/cortex_product_research_contract_v0.md)
- [docs/cortex_contract_v0.md](docs/cortex_contract_v0.md)
- [archive/appstore/summary_of_app.md](archive/appstore/summary_of_app.md)

## What It Is

LyraOS is both:

- a low-friction planning and execution product
- a measurement-valid behavioral instrument

The product layer gives users a normal workflow: sign in, dump or create tasks,
start/stop timers, recover missed plans, view deadlines, and inspect insights.

The research layer interprets those traces only through explicit contracts:
observed facts stay separate from derived metrics and inferred hypotheses;
retroactive, repaired, external, exposed, and unknown-exposure rows retain
their provenance; stronger claims require clean-data profiles and exposure
state.

The core research question is:

```text
Are humans wrong about their own execution capacity in structured,
modelable ways?
```

## What It Is Not

LyraOS does not currently ship:

- autonomous rescheduling
- hidden calendar mutation
- validated adaptive scheduling
- confidence-backed behavioral recommendations
- stable personality or identity labels
- AI-generated truth about user behavior
- learning from exposed/intervened behavior without exposure modeling

AI is used as supporting infrastructure: asynchronous enrichment, operator
orchestration, implementation assistance, and interface glue. It is not the
core authority for behavioral truth.

## Shipped Product Surface

User-facing:

- Google sign-in through NextAuth
- brain-dump onboarding
- task planning and quick capture
- timer execution: start, pause, resume, stop, switch
- overdue recovery
- calendar and deadline views
- Moodle deadline import and submission detection
- read-only Google Calendar context
- Pulse dashboard
- Insights page with primary synthesis and confidence-tiered cards
- pause and resume prediction surfaces
- archetype survey/proximity, framed as probabilistic prior/proximity
- settings, export/deletion, and feedback

Operator-only:

- admin dashboard
- JARVIS
- OpenClaw workflows
- operator notifications
- topology verification
- exposure diagnostics and policy logs
- Notion outbound sync/retry plumbing

## Architecture

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

Research/governance layer:
  raw product events and rows
  -> Cortex read-time projections
  -> clean-data profiles
  -> output surface registry
  -> exposure ledger and render acknowledgement
  -> insights, diagnostics, predictions, and policy audits

Operator-only layer:
  JARVIS
  OpenClaw
  admin diagnostics
  operator notifications
```

Runtime topology is part of correctness. Public verification uses:

```bash
node scripts/verify_runtime_topology.mjs --topology public
```

Current public topology:

```text
frontend: https://lyraos.org
api:      https://api.lyraos.org
auth:     https://lyraos.org
```

## System Diagrams

Diagrams live in [docs/diagrams](docs/diagrams). Regenerate them with:

```bash
python docs/diagrams/generate_diagrams.py
```

### System Architecture

![System architecture](docs/diagrams/architecture.png)

### Task State Machine

![Task state machine](docs/diagrams/state-machine.png)

### Task Lifecycle

![Task lifecycle sequence](docs/diagrams/data-flow.png)

### Undo Path

![Undo sequence](docs/diagrams/data-flow-undo.png)

## Technology Stack

| Layer | Current stack |
| --- | --- |
| Frontend | Next.js 15.5.15, React 18, TypeScript 5.6 |
| Styling/UI | Tailwind CSS, Radix, Lucide, Tremor, Schedule-X, Sonner, Motion |
| Auth | NextAuth.js 4 with Google OAuth |
| Backend | FastAPI 0.109, Uvicorn, Python |
| ORM/migrations | SQLAlchemy 2 typed models, Alembic |
| Database | Supabase Postgres in public runtime; SQLite for dev/tests |
| Hot state | Redis |
| Workers | APScheduler |
| Operator AI/tooling | JARVIS and OpenClaw, operator-only |

## Local Development

Prerequisites:

- Docker Desktop with Compose V2
- Node.js for the frontend
- Python environment matching the backend requirements

Configure environment:

```bash
cp .env.example .env
```

Start backend dependencies and API:

```bash
docker compose up -d --build
docker compose exec backend alembic upgrade head
```

Run the frontend locally:

```bash
cd frontend
npm install
npm run dev
```

Local URLs:

- Frontend: `http://localhost:3000`
- Backend health: `http://localhost:8000/v1/health`
- Swagger UI: `http://localhost:8000/docs`

Local topology verification:

```bash
node scripts/verify_runtime_topology.mjs --topology local
```

## API Shape

All backend routes are mounted under `/v1`.

Major route modules:

| Module | Responsibility |
| --- | --- |
| `health.py` | health, environment invariants, topology report |
| `users.py` | `/users/me`, consent, onboarding stamps, export/deletion |
| `tasks.py` | task CRUD, state transitions, recovery, LLM binding actions |
| `stopwatch.py` | start, pause, resume, stop, switch, status |
| `query.py` | range task queries and last-task lookup |
| `brain_dump.py` | brain-dump parse and commit |
| `deadlines.py` | deadline CRUD and state transitions |
| `calendar.py` | Google Calendar read-only events and outcomes |
| `moodle.py` | Moodle iCal and Web Services integration |
| `analytics.py` | insights, Cortex diagnostics, bias/prediction endpoints |
| `exposures.py` | render acknowledgement and exposure utilities |
| `jarvis.py` | operator-only JARVIS chat/confirm/health/stream |
| `admin.py` | operator-only dashboard |

## Research And Governance

The key measurement rules:

- bearer/JWT is runtime identity authority
- request scope must resolve before user data reads or writes
- user-owned ORM reads are scoped through request context
- raw SQL must scope manually
- derived metrics are recomputed at read time
- latent constructs are not persisted as observed facts
- `UNKNOWN` never defaults to clean, neutral, bounded, zero, or average
- repaired/retroactive rows stay out of measured-execution baselines unless a
  successor profile admits them
- behavior-shaping outputs must be registered before render
- exposure state gates baseline interpretation

Important governance files:

| File | Role |
| --- | --- |
| [MANIFESTO.md](MANIFESTO.md) | top-level doctrine and pre-registration artifact |
| [docs/professor_review_packet.md](docs/professor_review_packet.md) | external-review orientation |
| [docs/behavioral_instrumentation_doctrine.md](docs/behavioral_instrumentation_doctrine.md) | rule/probabilistic instrumentation doctrine |
| [docs/cortex_contract_v0.md](docs/cortex_contract_v0.md) | canonical metric and clean-data profile contract |
| [docs/cortex_product_research_contract_v0.md](docs/cortex_product_research_contract_v0.md) | product/research boundary and exposure ledger doctrine |
| [docs/adaptive_scheduling_progressive_inference.md](docs/adaptive_scheduling_progressive_inference.md) | future-gated adaptive scheduling contract |
| [docs/deployment_architecture.md](docs/deployment_architecture.md) | public topology and operational deployment |
| [docs/openclaw_orchestration_contract_v0.md](docs/openclaw_orchestration_contract_v0.md) | operator-only OpenClaw boundary |

## Privacy And Security Notes

LyraOS is pre-alpha product research and operator dogfood with a small alpha
cohort. Unless a separate institutional protocol is approved, it should not be
represented as an IRB-approved human-subjects study.

Known current security/privacy debts:

- Google refresh tokens are plaintext security debt.
- Moodle iCal URLs are plaintext security debt.
- Public privacy/terms copy has been improved from placeholders but still needs
  production-grade legal review before broader release.
- Cloudflare Tunnel from the operator host remains an operational dependency.

## Historical Notes

Some files preserve older names such as "Lyra Secretary," earlier architecture
designs, prototype OpenClaw assumptions, and pre-alpha bug trackers. Treat those
as lineage unless current governance docs explicitly promote them.

The root bug tracker has been archived at [archive/LYRA_BUGS.md](archive/LYRA_BUGS.md).
The local Obsidian vault (`LyraOS/`), `.assistant runtime/` runtime state, `agent bootstrap doc`,
and the local `notebooks/` working directory are ignored and no longer tracked.

## License

This project is licensed under the [MIT License](LICENSE).
