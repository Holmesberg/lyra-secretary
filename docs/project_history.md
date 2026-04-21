# Project History

Retrospective canonical document. What has happened in the project's build history, from inception to the current phase. Updated at phase boundaries.

**Last updated:** April 21, 2026 (Phase 4.5 active — Path B committed, first external activations observed)

---

## Pre-project (before April 2026)

Lyra Secretary originated from a thesis question: **can the gap between how a person thinks they perform and how they actually perform be measured, learned, and eventually closed?**

The operator (Aly Nasser) designed a single-subject experimental framework where:
- A user plans tasks with estimated durations
- The system records actual execution durations
- The delta between planned and executed (duration_delta_minutes) becomes the core metric
- Pre-task readiness (1-5) and post-task reflection (1-5) capture cognitive state around each session
- The discrepancy between readiness and reflection (discrepancy_score) tests whether self-prediction accuracy correlates with planning accuracy

This became the H1 hypothesis: users whose self-prediction improves (readiness-reflection gap shrinks) will also show improving planning accuracy (duration delta shrinks).

The experimental design was single-subject initially (operator as sole user, 10-day validation window April 4-15), with multi-user alpha planned for April 30 if the signal validated.

Key pre-project decisions:
- SQLite + Redis + Notion sync (lightweight, portable, operator already uses Notion)
- FastAPI backend with APScheduler for background jobs
- OpenClaw as the conversational agent layer (separate Docker stack)
- All times stored UTC internally, converted to Africa/Cairo for display
- Research instrument first, productivity tool second

---

## Phase 0: Core Pipeline (early April 2026)

**Goal:** Get the basic task lifecycle working end-to-end.

**Commits:** c878536 through febdecf (~15 commits)

**Key deliverables:**
- Project structure, database layer, task service + state machine (c878536, 0c5bf59, c5291ea)
- Parser for natural language task creation via dateparser (4dc446a)
- Task CRUD with state machine: PLANNED -> EXECUTING -> EXECUTED, plus SKIPPED and DELETED
- Stopwatch timer lifecycle: start, stop, delta computation
- Notion sync: tasks appear in Secretary Dashboard on create (d5deae4)
- Full pipeline: Telegram -> OpenClaw -> FastAPI -> Notion end-to-end (febdecf)
- OpenClaw skill definition (SKILL.md) with behavioral hard rules

**Architectural decisions solidified:**
- Single Mutation Authority: all task writes go through TaskManager (services/task_manager.py)
- State machine enforcement via services/state_machine.py — transitions are explicit, not implicit
- Redis for ephemeral state (active stopwatch, undo cache, idempotency keys)
- Notion as external sync target, not primary storage
- Half-open interval `[start, end)` for conflict detection

**What broke:**
- Notion datetime timezone double-conversion (LYR-019) — fixed by sending +02:00 offset explicitly
- Redis/stopwatch desync recovery needed (LYR-040/041)
- State machine enum .value errors in transition checks

---

## Phase 1: Measurement Layer (April 4-7)

**Goal:** Add the research instrumentation that makes Lyra a measurement instrument, not just a scheduler.

**Commits:** b26953f through 5226501 (~25 commits)

**Key deliverables:**
- v1.2 Discrepancy measurement: pre_task_readiness, post_task_reflection, initiation_delay_minutes, initiation_status (b26953f)
- v1.3 Behavioral insights engine: rule-based pattern detection, auto-mark insights as delivered (b4fd774)
- Pause/resume support with PAUSED state in state machine (2804ecb, 9e7c650)
- Mark-abandoned endpoint: EXECUTING|PAUSED -> SKIPPED (a94c0b5)
- Retroactive session logging for untracked sessions (897eb15)
- Micro-mirrors: one-line behavioral observations at stop time (6430a12)
- Unplanned execution tracking with reason enum (6430a12)
- Cascade analytics: skip propagation probability, morning anchor score (6430a12)
- Bias factor computation per category (5226501)
- Category taxonomy freeze: 11 categories, planning -> self_reflection merge (281e230)
- Immutable session_index_in_day for cascade chain position (d92f1bf)
- Task completion percentage on StopwatchSession (d938dec)
- Calibration nudge on stop: reference class forecasting per category (e2254df)

**Architectural decisions solidified:**
- Readiness and reflection are mandatory captures, not optional — SKILL.md Hard Rules 3 and 4
- Early-stop gate at 50% planned duration: requires explicit confirmation to stop early
- Zero-duration sessions transition to SKIPPED, not EXECUTED (preserves EXECUTED immutability for real work)
- Task void endpoint separates "corrupted data" from "cancelled plan" semantics
- Conflict detector excludes DELETED/SKIPPED/EXECUTED tasks
- Parent_task_id and interruption_type for tracking task switching
- Task substitution tracking (replaces_task_id / replaced_by_task_id)

**What was learned:**
- The cascade failure discovery (Day 2): skipping one task causes the next to fall. Independent of H1, potentially faster to publish (Paper 2)
- Motivated underestimation pattern observed in operator data — users may plan short deliberately for dopamine, not because they misjudge (H4 candidate, methodology.md)
- The 10-day experiment validated that delta and discrepancy data could be collected reliably

---

## Phase 2: Multi-User Migration (April 8-9)

**Goal:** Transform the single-user backend into a multi-tenant system for alpha launch.

**Commits:** 2961d10 through aa6152b (~5 commits)

**Key deliverables:**
- Phase 1 (engineering): Multi-user backend migration — User table, user_id columns on Task and StopwatchSession (2961d10, alembic 013-014)
- Phase 2a: Per-user APScheduler jobs via for_each_user() pattern + Notion gating per user (3cccccd)
- Phase 2b: JWT auth (HS256 via jose), Next.js scaffold, Google OAuth documentation (aa6152b)
- CORS middleware for cross-origin frontend dev (aa02b4f)

**Architectural decisions solidified:**
- SQLAlchemy `before_compile` hook in app/db/scoping.py rewrites ORM queries to filter by user_id from ContextVar
- ContextVar set by UserScopeMiddleware from JWT claims (X-User-Id header during development)
- User_id has NO default value — writes must pass it explicitly (prior default=1 silently funneled cross-tenant writes to operator, LYR-093)
- Operator is user_id=1, is_operator=true
- JWT signed with shared NEXTAUTH_SECRET, 12-hour expiration

**What broke:**
- The default user_id=1 on Task and StopwatchSession created a silent cross-tenant write vulnerability that wasn't caught until Phase 3.2

---

## Phase 3: Frontend Build (April 9-10)

**Goal:** Build the web UI that replaces Telegram/OpenClaw as primary interface.

**Commits:** e9f5d76 through 1373538 (~10 commits)

### Phase 3.0 — Today View
- Today view with task list, timer flow, state-colored pills (e9f5d76)
- App layout with backend error surfacing (d7d9f82)

### Phase 3.1 — Research Layer UI
- Visible research layer: readiness/reflection display, pause UI, task source 'web' (413d204)

### Phase 3.2 — P0 Cross-Tenant Write Leak
- **Critical fix:** user_id default=1 caused all writes to funnel to operator account (4cf2168)
- Adversarial multi-user isolation tests added (test_multiuser_isolation_adversarial.py)
- CI skip marker for Redis-dependent tests (430f120)

### Phase 3.3 — P0 Read Leak + UX Fixes
- Stopwatch read leak: user B saw user A's active timer (1373538)
- Pause/resume int/float type mismatch fixed
- Completion percentage input validation (rejected 500%)

**Architectural decisions solidified:**
- CONTRIBUTING.md multi-user isolation testing rule: any PR touching write paths must include adversarial test
- Synthetic user IDs 98/99 for isolation tests (never 1, to avoid operator data)
- Frontend uses @tanstack/react-query with 10s refetch interval
- NextAuth SessionProvider wraps all routes

**What broke and what it taught:**
- Cross-tenant leaks are the highest-severity bug class in a multi-user research instrument — one user's data corrupting another's invalidates both. This drove the multi-tenant isolation gate (gate #10) and the before_compile hook architecture.

---

## Phase 4: Schedule-X Calendar Integration (April 10-11)

**Goal:** Ship a calendar view that makes the full schedule visible and directly manipulable.

**Commits:** 277097e through a1c07a1 (~15 commits)

**Key deliverables:**
- Phase 4 prerequisite batch: schema refactor specs, useCurrentTime hook design, stale recovery design (277097e, 663d471)
- Phase 4 alignment audit: 5 new bugs found, 8 P0 fixes identified (f271aac)
- PLANNED rows sort ascending (next-up first) with partitioned comparator (57839d5)
- useCurrentTime shared hook: 60s tick for cross-day rollover + stale modal fix, LYR-099 (2c18be9)
- Pause reason picker on ActiveTimerBanner: 6-reason dropdown (f3af1df)
- Schedule-X calendar view at /calendar: day/week/month, 5 state-colored calendars, drag/resize PLANNED tasks, click-to-edit/view, 62-day query window (e085671)
- Final calendar close with 4 runtime bug fixes (a1c07a1):
  1. Temporal.PlainDate dual-realm crash — fixed by temporal-polyfill/global import
  2. Time grid cropped at ~7AM — fixed by calc viewport height
  3. Overlapping events text obscured — fixed by eventOverlap: false
  4. Drag TypeError from plugin version mismatch — fixed by runtime method alias shim

**Architectural decisions solidified:**
- Browser-verify HARD GATE: frontend commits don't land on main until operator confirms in browser (added after Schedule-X shipped with 4 runtime bugs that passed all automated gates)
- WSL cold-restart rule: pkill + rm -rf .next + npm run dev before every browser-verify (HMR unreliable)
- Cross-route browser-verify for shared components: if a component is used by multiple routes, all routes must be verified
- Stale-closure safety via useRef for callback data in Schedule-X event handlers
- Runtime shim for upstream library version mismatches (documented, with watch-for-update note)

**What broke:**
- Schedule-X selectedDate required plain string "YYYY-MM-DD" but received Temporal.PlainDate — tsc accepted it, dev server compiled it, page crashed at runtime
- This single incident drove the browser-verify HARD GATE, the most impactful process change in the project

---

## Phase 4 Close -> Phase 4.5 Bridge (April 11-14)

**Goal:** Close out Phase 4 bugs, ship missing features, harden for alpha.

**Commits:** c636e42 through present (~35 commits)

### Voided_at audit batch (April 13) — 5 commits

The voided_at field sets a timestamp but does NOT change task state. Every query filtering by state alone leaked voided tasks. Systematic audit found 14 bugs + 1 found by automated script = 15 total.

- Background jobs skip voided tasks: reminders, timer_overflow, overdue_tasks, stale_session_recovery, notion_sync (2af80f0)
- Mutation endpoints reject voided tasks: complete, skip, swap, reschedule, start, stop, update-completion (2afd063)
- /tasks/last filters voided + undo cache per-user scoped (7823424)
- Automated audit script + skill_check leak fix (05d3e0a)
- Conflict detector excludes voided tasks (b7ed224)

15 new regression tests across 3 test files. Total suite: 94 tests, all passing.

### Feature deliverables

- Notion-style data table at /table with CSV export (417efae)
- SKIPPED ghost banner fix + mark_abandoned Redis cleanup + stale threshold lowered to 12h (2accd65)
- POST /v1/stopwatch/update-completion + early-stop override for high-completion fast tasks (e8b5061)
- 5-state system consistency gate tests (fb68040)
- Multi-tenant Redis key namespacing: notifications, last_operated_task, notion sync queue (8f1704a)
- Mid-task completion estimate surfaced distinctly at stop time (b2b0610)
- End-time primary input on new task modal (948bd2d)
- Day navigation on Today view (948bd2d)
- Settings page: Export JSON + Delete account with two-stage major warning pattern + anonymized research retention (current session)
- GET /v1/users/me/data-summary endpoint for delete comprehension stage (current session)
- Alembic 019: anonymized retention columns (post_deletion_retained_at, original_user_id_hash)

### Documentation deliverables

- voided_at audit verification checklist with contamination queries (docs/voided_at_audit_verification.md)
- Phase 6 calibration architecture spec (docs/phase_6_architecture_backlog.md)
- Cohort start dates and contamination notes in MANIFESTO (VT-14)
- Anonymized Retention Policy + Two-Class Research Framing in MANIFESTO (VT-15, VT-16)
- Do Not Add list: 11 rejected architectural directions (docs/do_not_add.md)
- Two-stage destruction pattern (docs/design_patterns/two_stage_destruction.md)
- Orienting principles for Phase 6 (branch-laying, custodianship, data sovereignty, architect-side constraints)

### Process improvements

- Durable verification gate suite: 12 gates formalized (memory/feedback_verification_gates.md)
- voided_at guard pattern: durable rule for all Task queries (memory/feedback_voided_at_guard.md)
- 24-hour documentation rule: architectural conversations get documented within 24h
- Compression cycles: every ~10 days, review and prune 20-30% of dogfood/backlog items

**Architectural decisions solidified:**
- voided_at guard pattern: every DB query or mutation on Task must include voided_at check
- Two-class research framing: hypothesis research (H1, stable cohort) vs product research (churn patterns, all data) — different populations, different epistemic standards (VT-16)
- Custodianship trust frame: Lyra follows personal-history product conventions (Apple Photos, Bear), not productivity tool conventions (Notion, Linear)
- Data sovereignty surface: Settings page is the architectural unit for data access, export, deletion, backup status
- Anonymized retention as deletion default: behavioral data preserved without identifying info for product research, with user opt-out

### Contamination audit results (April 13)
- 4 contaminated rows found (3 overdue job -> SKIPPED, 1 stale recovery auto-close)
- All test data, zero real operator task impact
- Decision: Option C (accept and document in MANIFESTO)
- Pre-registered: cohort=operator clean analytics begin April 13, 2026

---

## Current Phase: Phase 4.5 — Pre-Alpha Polish (April 13-18 target)

Active phase. Goal: harden everything shipped so far, close remaining P0/P1 items from dogfood, prepare for trusted-user handoff.

See docs/building_phases.md for forward-looking detail on remaining work and phase scoping.

---

## Phase Numbering Note

This document and building_phases.md use **engineering phase numbering** (Phase 1 = multi-user migration, Phase 4 = calendar, etc.). MANIFESTO.md uses **research phase numbering** (Phase 0 = validate signal, Phase 3 = BCI, Phase 4 = papers). These are different numbering systems applied to the same project.

Mapping:
| Engineering | Research (MANIFESTO) |
|-------------|---------------------|
| Phases 0-1 (core + measurement) | Phase 0 (validate signal) |
| Phase 2 (multi-user) | — (infrastructure, no research equivalent) |
| Phases 3-4.5 (frontend + polish) | Phase 0 continued (still validating) |
| Phase 5 (onboarding) | Phase 1B entry (scale to 10-30 users) |
| Phase 6 (post-validation) | Phase 2 (adaptive engine) |
| Phase 8+ (BCI) | Phase 3 (BCI integration) |

---

## Commit Statistics

As of April 14, 2026:
- ~120 commits on main
- 19 Alembic migrations
- 94 backend tests passing
- 14 API endpoints (backend/app/api/v1/endpoints/)
- 6 service modules (backend/app/services/)
- 5 background jobs (backend/app/workers/jobs/)
- 4 frontend routes (/today, /calendar, /table, /settings)
- 5 VTs added during Phase 4.5 alone (VT-11, VT-14, VT-15, VT-16, and voided_at audit driving the pattern)

---

## April 18-21, 2026 — First external users + Path B commit

**External user activations.** First non-operator sessions logged 2026-04-18 (user_id 4 + 5, two sessions each, user_id 5 hit a stale-session auto-close). First textbook external activation 2026-04-20 (user_id 6, three clean EXECUTED sessions in a six-hour window, 79-min average, zero auto-closes). As of 2026-04-21: 99 total sessions across 5 of 7 signups, operator dominates at 87/99. D1 return = 0/2 for external users; D3 + D7 = 2/2.

**Brand unification push (2026-04-19 → 2026-04-20, 12 commits).** Phase 1→6 of the app-shell brand-unification plan shipped end-to-end in a single session: `refactor(globals)` → `feat(app-shell)` → `feat(timer-banner)` → `feat(insights)` → `fix(today)` → `fix(calendar)` → `chore(mobile)` → `refactor(typography)` → `chore(sweep)`. Authenticated routes now wear the landing's neural-noir palette with preserved operational density. Chakra Petch dropped from the authenticated bundle.

**Path B strategic commitment (2026-04-21).** Dogfood finding: 0/9 external-user tasks had >30 min planning lead. External users are pure reactive executers; the "planning fallacy" thesis assumes a planning behavior that doesn't exist in the wild. Committed to **engineering planning as a habit** rather than accommodating reactive execution. See `docs/strategic_decisions_april_21.md` for full reasoning, kill criterion pre-registered for 2026-05-21.

**Taxonomy edit (2026-04-21).** `self_reflection` → `planning` un-merged (reversing the April 8 merge). Six task rows + nine category_mapping rows migrated in prod. Seven new planning-oriented keywords seeded (brain dump, schedule, outline, agenda, roadmap, priorities, weekly review). Path B ratifies the category surface as an invitation to plan rather than a label for people who already do.

**new-task-modal 3-bug fix (2026-04-21).** AM/PM slip recovery + duration always-recompute + calibration-nudge guard on invalid ranges. Dogfood-driven; operator-observed bug report with screenshot.
