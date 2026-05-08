# Lyra Secretary v1.5 — Comprehensive Technical Summary

> **Snapshot date:** 2026-05-08 · ~410 commits · 45 Alembic migrations
> **Status:** Pre-alpha dogfood, single operator + small alpha cohort

---

## 1. Core Purpose & Philosophy

Lyra Secretary is a **research-grade behavioral inference system** with a working productivity layer on top.

**Primary research question:**
> *"Are humans wrong about themselves in a structured, modelable way that predicts failure?"*

It answers this by obsessively tracking the **Planning vs. Execution Gap (Δ)** — the difference between what a user *plans* to do and what they *actually* do — and layering on a rich **Discrepancy Measurement Layer** (readiness, reflection, initiation delay, pauses, scope drift). The system learns behavioral patterns from this high-resolution data and mirrors them back to the user through calibration nudges, micro-mirrors, and predictive alerts.

**Design axiom:** Mirror, don't judge. Every user-facing surface is deliberately neutral in tone (no "great job!" or "you failed"). The system observes and reflects; the user interprets.

---

## 2. Technical Stack

### Frontend
| Layer | Technology |
|---|---|
| Framework | Next.js 14/15 (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS, custom "Neural-Void" dark theme (`signal` cyan, `ember` red, `parchment` off-white, `void` near-black) |
| Server State | TanStack Query (React Query) with optimistic mutations |
| Auth | NextAuth.js → Google OAuth |
| Components | Radix UI primitives, Lucide icons, Tremor charts, Schedule-X calendar |

### Backend
| Layer | Technology |
|---|---|
| Framework | FastAPI (Python 3.11+) |
| Database | PostgreSQL on Supabase (eu-west-1) |
| ORM | SQLAlchemy 2.0 (`Mapped`/`mapped_column`) |
| Migrations | Alembic (45 revisions) |
| Cache / Real-time | Redis (stopwatch state, pause state, undo cache, `/me` cache, Notion queue, GCal event cache) |
| Background Jobs | APScheduler `BackgroundScheduler` (14 registered jobs) |
| LLM (Cloud) | NVIDIA NIM via OpenAI-compat API (Llama 3.3 70B default) — operator-only JARVIS + async enrichment |
| LLM (Local) | Ollama HTTP API — fallback enrichment path for non-operator users |

### Infrastructure
| Layer | Technology |
|---|---|
| Hosting | `lyraos.org` via Cloudflare Tunnel |
| Containers | Docker (backend + frontend services) |
| Notifications | Telegram Bot API (operator alerts, pause/resume predictions) |
| External Sync | Notion API (task mirror), Google Calendar (read-only import), Moodle LMS (iCal deadlines + Web Services submissions) |

---

## 3. Frontend Architecture

### 3.1 Pages (App Router)
| Route | Purpose |
|---|---|
| `/today` | Main daily view — task list with stopwatch controls, brain-dump quick-add |
| `/calendar` | Schedule-X week/day calendar with Lyra tasks + Google Calendar overlay |
| `/pulse` | Analytics dashboard — Tremor charts for delta trends, bias factors, category breakdowns |
| `/deadlines` | Deadline management — native + Moodle-imported, state transitions, task bindings |
| `/insights` | Archetype proximity display, behavioral pattern summaries |
| `/settings` | Integration connections (Google Calendar, Moodle), archetype survey, timezone |
| `/admin` | Operator-only — user management, system health, void tools |
| `/table` | Raw task table view with sorting/filtering |
| `/onboarding` | Brain-dump onboarding flow (gated by `onboarding_completed_at`) |
| `/privacy`, `/terms` | Legal pages (placeholder — needs production text) |

### 3.2 Key Components (30+ components)
- **`app-shell.tsx`** (12KB) — Layout shell with sidebar navigation, JARVIS chat drawer
- **`active-timer-banner.tsx`** (27KB) — Persistent stopwatch banner with pause/resume/stop, overrun check-in, task-switch chip, pause-reason modal
- **`new-task-modal.tsx`** (48KB) — Task creation with calibration nudge, deadline binding chips (Tier 1-4), time/duration pickers
- **`onboarding-flow.tsx`** (19KB) — Two-step brain-dump onboarding (dump → confirm → review failures)
- **`llm-enrichment-chip.tsx`** (18KB) — Deadline binding suggestion UI with tiered confidence display
- **`archetype-survey.tsx`** (13KB) — 29-item psychometric questionnaire for archetype assignment
- **`archetype-insights-card.tsx`** (14KB) — Bayesian posterior proximity display with trend comparison
- **`retroactive-modal.tsx`** (13KB) — Log completed tasks after the fact with readiness/reflection
- **`reflection-modal.tsx`** (7KB) — Post-task reflection (1-5 scale), scope outcome, completion percentage
- **`readiness-modal.tsx`** (3KB) — Pre-task readiness (1-5 scale) at stopwatch start
- **`pause-prediction-banner.tsx`** / **`resume-prediction-banner.tsx`** — VT-17 prediction UI with accept/dismiss/snooze
- **`pause-confirm-chip.tsx`** — Retroactive pause confirmation from prediction
- **`tutorial-overlay.tsx`** (8KB) — First-use guided tour
- **`consent-modal.tsx`** — Research consent gate
- **`void-modal.tsx`** — Task void with reason selection
- **`feedback-modal.tsx`** — Alpha-cohort bug/suggestion submission
- **`integration-card.tsx`** / **`integrations-section.tsx`** (24KB) — Google Calendar + Moodle connection UI
- **`deadline-modal.tsx`** / **`deadline-row.tsx`** — Deadline CRUD with state transitions
- **`external-event-row.tsx`** — Google Calendar event display in /calendar

### 3.3 JARVIS Chat UI (`components/jarvis/`)
Operator-only in-app chat assistant. SSE streaming via `ReadableStream`. Shows tool-call chips, pending confirmation actions (Confirm/Cancel), and behavioral pattern cards.

---

## 4. API Surface (21 endpoint modules)

| Module | Size | Key Endpoints |
|---|---|---|
| `analytics.py` | 67KB | Alpha funnel, bias factors, category stats, delta trends, pattern summaries, archetype proximity, reflection engagement |
| `users.py` | 28KB | `/me` (cached), profile, onboarding stamps, skip-onboarding, google-refresh-token, archetype survey, consent, tutorial |
| `tasks.py` | 25KB | CRUD, reschedule, void, swap, llm-confirm, llm-reject-binding |
| `stopwatch.py` | 18KB | Start, stop, pause, resume, switch, status, check-early-stop, overrun-check-in |
| `admin.py` | 16KB | User list, system health, NIM health, void tools (operator-only) |
| `query.py` | 15KB | `/tasks/query` — range-based task fetching with Redis caching |
| `moodle.py` | 13KB | Connect, disconnect, preview, sync-now, submissions status |
| `brain_dump.py` | 11KB | Parse + commit (onboarding + quick-add modal) |
| `pause_predictions.py` | 11KB | Prediction log, response recording, accept/dismiss/snooze |
| `jarvis.py` | 8KB | `/ask` (agent loop), `/confirm` (write-tool execution), `/health`, `/stream` |
| `calendar.py` | 7KB | Google Calendar events fetch, refresh-token storage |
| `health.py` | 7KB | DB, Redis, Notion, Ollama, NIM connectivity checks |
| `feedback.py` | 6KB | Alpha feedback submission + listing |
| `deadlines.py` | 5KB | CRUD, void, state transitions |
| `integrations.py` | 5KB | Integration status (Google, Moodle, Notion) |
| `parse.py` | 4KB | Single-task NLP parse endpoint |
| `undo.py` | 4KB | Redis-backed undo for last action |
| `notifications.py` | 3KB | Telegram notification preferences |
| `reflection_view.py` | 2KB | ReflectionViewLog creation for dwell tracking |
| `skill_check.py` | 1KB | Feature-flag checks for progressive disclosure |

---

## 5. Domain Model (Database Entities)

### 5.1 `Task` — The Core Entity (~50 columns)

**Planning columns** (set at creation):
- `planned_start_utc`, `planned_end_utc`, `planned_duration_minutes`
- `confidence_score` — parser confidence at creation

**Execution columns** (set at stopwatch stop):
- `executed_start_utc`, `executed_end_utc`, `executed_duration_minutes`

**Research instrument columns:**
- `pre_task_readiness` (1–5) — "How ready do you feel?" (set at stopwatch start)
- `post_task_reflection` (1–5) — "How focused were you?" (set at stop)
- `initiation_delay_minutes` — gap between planned and actual start
- `initiation_status` — `not_started | initiated | retroactive | abandoned | system_error | user_skipped`
- `pause_count`, `scope_outcome` (`grew | shrank | same | unsure`)
- `scope_bullet_count_at_plan` / `scope_bullet_count_at_execute` — regex-counted bullets for scope-drift measurement

**Computed properties** (Python `@property`, NOT DB columns):
- `duration_delta_minutes` = `planned - executed` (positive = early, negative = overrun)
- `discrepancy_score` = `abs(readiness - reflection)`
- `signed_discrepancy` = `reflection - readiness` (positive = restorative)
- `is_mutable` — `False` for `EXECUTED` or `DELETED`

**Deadline binding** (Loop 11):
- `deadline_id` (FK), `deadline_match_confidence` (0–1.0), `deadline_match_source` (`user_explicit | parser_auto | user_corrected | heuristic_exact_title | heuristic_startswith | heuristic_substring | llm_auto_confirmed`)

**LLM enrichment** (async background worker):
- `llm_parse_status` (`pending → enriched | unavailable | failed`)
- `llm_priority` (1–5), `llm_sub_items` (JSON), `llm_parsed_at`
- `llm_inferred_deadline_id`, `llm_deadline_candidates` (JSON array), `llm_deadline_match_confidence`
- `llm_alternative_suggestion` (JSON — trust-not-rewrite contract: stores disagreeing LLM suggestion without overwriting user's binding)
- `llm_binding_rejected_at` — sticky rejection; prevents re-popping suggestion chips

**Void system:**
- `voided_at`, `voided_reason` (`test_contamination | duplicate | system_error | data_quality | other`), `void_reason_detail`
- **CRITICAL INVARIANT:** Every analytics/research query MUST filter `voided_at IS NULL`

**Substitution chain:** `replaces_task_id` / `replaced_by_task_id` — links task that was deleted-then-replaced in same time slot within 10min

**Other:** `session_index_in_day` (immutable), `reschedule_count`, `parent_task_id`, `interruption_type`, `notion_page_id`, `user_id` (mandatory)

### 5.2 `StopwatchSession`
- `start_time_utc`, `end_time_utc`, `auto_closed` (bool)
- `paused_at_utc`, `total_paused_minutes` (float — sub-minute precision)
- `pause_reason`, `pause_initiator`
- `original_pre_task_readiness` — audit trail when user corrects mid-session
- `task_completion_percentage` — from overrun check-in flow
- `data_quality_flag` — NULL = clean; non-NULL = contaminated (excluded from research)

### 5.3 `PauseEvent`
- `paused_at_utc`, `resumed_at_utc`, `duration_minutes`
- `pause_reason` (NOT NULL), `pause_initiator` (NOT NULL)
- `active_elapsed_at_pause_seconds` — snapshot of work time at pause moment
- `self_reported_retroactively` — excluded from predictor training to prevent self-reinforcement

### 5.4 `Deadline`
- State graph: `planned → active → completed | missed | skipped | voided`
- `external_source` / `external_id` — for Moodle iCal imports (partial unique index)
- `completed_at`, `imported_at`, `category_hint`

### 5.5 `User`
- `timezone`, `archetype_id` (FK), `is_operator`
- `onboarding_completed_at`, `first_task_at`, `first_timer_started_at`, `d1_return_at`
- `google_refresh_token` (plaintext — Phase 6+ encryption debt)
- `moodle_ics_url`, `moodle_ws_token` (Fernet-encrypted via alembic 044), `moodle_last_synced_at`, `moodle_disconnect_reason`
- `tutorial_completed_at`, `tutorial_skipped_at`, `archetype_retrofit_dismissed_at`
- `consent_given_at`, `consent_version`

### 5.6 Other Entities
- **`Archetype`** — 5 behavioral clusters (`prior_bias_factor`, `prior_sigma`)
- **`ArchetypeAssignment`** — per-user survey results + raw 29-item responses
- **`TaskDeadlineOutcome`** — post-execution reconciliation (frozen-at-compute-time)
- **`CalibrationNudgeEvent`** — creation-nudge fire + user decision + executed outcome
- **`ReflectionViewLog`** — per-impression engagement (dwell_seconds, outcome)
- **`PausePredictionLog`** / **`ResumePredictionLog`** — VT-17 research artifacts
- **`CategoryMapping`** — keyword→category lookup for auto-inference
- **`ExternalEventOutcome`** — Google Calendar attendance self-reports
- **`Feedback`** — alpha bug/suggestion channel
- **`JarvisInvocation`** — tool-call audit trail (`executed | pending_confirmation | rejected | failed`)

---

## 6. State Machine (`state_machine.py`)

```
PLANNED ──→ EXECUTING, SKIPPED, DELETED
EXECUTING ─→ PAUSED, EXECUTED, SKIPPED
PAUSED ────→ EXECUTING, SKIPPED
EXECUTED ──→ (immutable)
SKIPPED ───→ DELETED
DELETED ───→ (immutable)
```

**Key invariants:**
- `EXECUTED` and `DELETED` are **immutable** — all mutations raise `ImmutableTaskError`
- `PAUSED → EXECUTED` is **not direct** — stopwatch `stop()` auto-resumes to `EXECUTING` first
- `swap_tasks()` is the only operation that can reactivate a `SKIPPED` task

---

## 7. TaskManager — Single Mutation Authority

ALL task modifications flow through `TaskManager`. No other service writes to Task directly.

### 7.1 `create_task()` — 12-step pipeline
1. **Time conversion:** naive local (Cairo) → UTC
2. **Past-time guard:** rejects start < now - 5min
3. **Conflict detection:** `ConflictDetector.detect()` → classified `ConflictResult`
4. **Deadline binding** (3-pass cascade):
   - Pass 1: explicit `deadline_id` → `source='user_explicit'`, confidence=1.0
   - Pass 2: `score_deadlines()` heuristic → auto-bind if score ≥ 0.6 + margin ≥ 0.2 → `source='heuristic_*'`
   - Pass 3: legacy `infer_deadline_binding()` keyword overlap → `source='parser_auto'`
5. **Category inference** from keyword→category table
6. **Scope bullets** regex count from description
7. **Session index** computation (immutable per local-tz day)
8. **Pre-populate `llm_deadline_candidates`** from heuristic for instant chip rendering
9. **Calibration nudge logging** (all-or-none CalibrationNudgeEvent + ReflectionViewLog)
10. **Onboarding stamp** — first task ever → stamps `onboarding_completed_at` + `first_task_at`
11. **Cache invalidation** — busts `/me` cache + task-range cache
12. **Notion sync** — deferred to Redis queue + **substitution detection** within 10min

### 7.2 `complete_task()`
- Computes `executed_duration_minutes`, re-samples `scope_bullet_count_at_execute`
- Stamps `CalibrationNudgeEvent.executed_duration_minutes` (inline reconciliation)
- Transitions `EXECUTING → EXECUTED` via state machine

### 7.3 Other Mutations
- `create_retroactive_task()` — bypasses past-time check, conflict detection, state machine; creates directly as `EXECUTED`
- `start_task()` — `PLANNED → EXECUTING`
- `skip_task()` / `delete_task()` — soft transitions
- `swap_tasks()` — atomically swaps SKIPPED↔PLANNED time slots
- `reschedule_task()` — updates time, increments `reschedule_count`, resets LLM enrichment

---

## 8. StopwatchManager — Execution Engine

### 8.1 Redis-Backed Hot State
- **`active_stopwatch:{user_id}`** — session_id, task_id, title, start_time
- **`pause_state:{user_id}`** — paused_at timestamp
- Redis = source of truth during live session; DB = recovery source

### 8.2 `start()` — stamps `initiation_delay_minutes`, transitions `PLANNED → EXECUTING`, creates `StopwatchSession`, sets Redis state, stamps `first_timer_started_at` (lazy-once)

### 8.3 `pause()` / `resume()`
- **Pause:** creates `PauseEvent` with reason + initiator + `active_elapsed_at_pause_seconds`, transitions `EXECUTING → PAUSED`
- **Resume:** calculates pause duration, adds to `total_paused_minutes`, transitions `PAUSED → EXECUTING`

### 8.4 `stop()` — completion pipeline
1. If paused → auto-resume (counts final pause duration)
2. **Zero-duration guard:** active_elapsed == 0 and completion < 80% → routes to `SKIPPED`
3. Calls `TaskManager.complete_task()` with pause-deducted duration
4. Computes **micro_mirror** and **calibration_nudge** (see §13)
5. Checks for orphaned paused-parent sessions

### 8.5 `switch()` — atomic source-pause + target-resume
1. Pauses source (creates PauseEvent with `reason="task_switch"`)
2. Closes target's open PauseEvent
3. Transitions target `PAUSED → EXECUTING`
4. Swaps Redis active stopwatch

### 8.6 Recovery
- **`_recover_from_db()`:** Priority: (1) EXECUTING task with open session, (2) most-recently-paused PAUSED task, (3) None
- **`_get_active()` self-heal:** validates Redis-bound task on every status poll
- **`void_cleanup()`:** immediate stopwatch clear when task is voided

### 8.7 Active Elapsed Calculation
```python
active_seconds = max(0, (now - session_start) - total_paused - current_pause_duration)
```
All datetimes `strip_tz()`'d before subtraction.

---

## 9. Conflict Detection (`conflict_detector.py`)

**All conflicts currently SOFT** (force-overridable):
- `executing_overlap` — overlap with EXECUTING task
- `planned_overlap` — overlap with PLANNED/PAUSED task
- `duplicate_title` — same title (case-insensitive) on same UTC date

Half-open interval: `A.start < B.end AND B.start < A.end`. No HARD conflicts in the current model.

---

## 10. DeadlineManager — Single Mutation Authority for Deadlines

Mirrors TaskManager pattern. All deadline writes flow through this service.

### State Transition Graph (user-actionable)
```
planned ─→ active, completed, skipped
active  ─→ completed, skipped
completed → planned  (reopen)
missed    → planned  (reopen)
skipped   → planned  (reopen)
voided    → (no transitions)
```

### Key Operations
- `create_deadline()` — creates in `planned` state
- `upsert_external_deadline()` — idempotent create-or-update for Moodle imports, keyed on `(user_id, external_source, external_id)`. Voided rows are NOT resurrected.
- `update_deadline()` — validates state transitions against `USER_TRANSITIONS_FROM` map
- `void_deadline()` — soft-delete via `voided_at`; allowed from any state

---

## 11. Inference Engine & Bias Factor

### 11.1 Bias Factor (`bias_factor_service.py`)
Core adaptive scheduling primitive. **Canonical formula (MANIFESTO Rule 13):**

```
personal_weight     = min(1.0, n_sessions / 30)
archetype_scaling   = archetype.prior_bias_factor / 1.30
archetype_prior     = RESEARCH_PRIORS[category] × archetype_scaling
bias_factor_final   = (1 − personal_weight) × archetype_prior + personal_weight × personal_ratio
```

**Adaptive calibration cascade** (most specific → broadest, first with ≥3 sessions wins):
1. `category × time_of_day × duration_bucket` (short/medium/long)
2. `category × time_of_day`
3. `category` only
4. Research prior (cold start)

**Population priors** (frozen at launch, from Buehler 1994, Kahneman & Tversky 1979):
- development: 1.50, work: 1.45, study/academic: 1.40, exercise: 1.15, default: 1.35

### 11.2 Valence Classification (`inference_engine.py`)
Classifies each EXECUTED task into 5 structural classes:
- **friction:** overrun + low focus (≤2) + ≥3 pauses + scope unchanged
- **flow:** overrun + high focus (≥4) + ≤1 pause
- **scope_creep:** overrun + medium focus (3) + scope grew ≥50%
- **under_plan:** underrun + high focus + ≤1 pause
- **neutral:** within ±15% of plan, or data unavailable

### 11.3 Disagreement Classification
- **optimism_collapse:** readiness ≥4, reflection ≤2
- **capacity_surprise:** readiness ≤2, reflection ≥4
- **flow_overrun:** reflection ≥4, executed ≥1.3× planned
- **friction_completion:** reflection ≤2, |delta| ≤15%

### 11.4 Archetype Proximity (`archetype_proximity_service.py`)
Bayesian posterior over 5 archetypes from task history (MANIFESTO Rule 17):

```
log_posterior_i = log(1/5) + (Σ log_likelihood_i) / sqrt(N)
posterior = softmax(log_posteriors)
```

- **sqrt(N) damping** (Rule 17 v1.15) — tasks within one user's window are not iid; treats cluster as sqrt(N) effective independent observations
- **Winsorization** — caps observed bias_factor at [0.30, 3.0] to prevent outliers from dominating
- **Trend comparison** — `compute_proximity_trend()` computes current vs prior window posteriors + delta per archetype
- **Cold start** — uniform 1/N distribution when no qualifying tasks in window

---

## 12. Pause & Resume Prediction (VT-17)

### 12.1 Pause Predictor (`pause_predictor.py`)
Two mechanisms:

**clock_anchor:** hour-of-day × weekday-bucket median minute. Predicts a pause near that minute if historical pauses cluster there.

**work_rhythm:** per-category median time from `executed_start` to first pause. Projects `predicted_at = start + median_delta`.

**Gating** (ALL must hold): ≥7 days history, ≥5 samples in bucket, lead time in [2, 3] minutes, confidence ≥ 0.40.

**Confidence formula:**
```
confidence = min(0.95, 0.30 + 0.30 × min(n/15, 1.0) + 0.40 × max(0, 1 - stdev/30))
```

**Training data integrity:** retroactive self-reports excluded to prevent self-reinforcement.

### 12.2 Resume Predictor (`resume_predictor.py`)
Single mechanism: per-(category, time_of_day) p75 of pause duration. Fires when `paused_for ≥ max(p75, ABSOLUTE_FLOOR)`.

**Key parameters:**
- `ABSOLUTE_FLOOR_MINUTES = 10` — never nudges a fresh pause regardless of p75
- `COOLDOWN_MINUTES = 60` — prevents spamming (was 5min, caused 25 nudges in 8h)
- `MAX_FIRES_PER_SESSION = 3` — stops pinging after user clearly ignores
- **Cold-start:** `COLD_START_FLAT_CAP = 30min`, mechanism=`cold_start_synthetic`

### 12.3 Reconciliation Jobs
- `reconcile_responses` (5 min) — closes acceptance windows, sets `user_response` to `pause_now | dismiss | snooze | no_response`
- `reconcile_deadline_outcomes` (30 min) — writes `TaskDeadlineOutcome` rows for EXECUTED deadline-bound tasks

---

## 13. Feedback Mechanisms ("Mirrors")

### 13.1 Micro-Mirrors (`_compute_micro_mirror()` in stopwatch_manager.py)
One-line behavioral observation at stopwatch stop. Priority cascade:
1. Initiation delay > 10 min → "Started X min late"
2. Delay ≤ 0 → "Started on time"
3. Delta < -20 → "Ran X min over plan"
4. Delta > 20 → "Finished X min early"
5. 0 pauses on 30+ min session → "0 pauses this session"
6. ≥3 pauses → "X pauses this session"
7. Fallback → ratio: "Planned X min, took Y — Z× your estimate"

### 13.2 Calibration Nudge at Stop (`_compute_calibration_nudge()`)
Reference-class forecast when category has ≥3 EXECUTED sessions. Shows avg delta, underestimate count, direction. Fires at n≥3 (pre-registered floor for cold-start engagement loop).

### 13.3 Creation Nudge (in NewTaskModal)
Inline warning when `bias_factor_final` suggests unrealistic estimate. User decision (`accepted` / `dismissed`) logged atomically via `CalibrationNudgeEvent` + `ReflectionViewLog`.

---

## 14. Brain Dump Parser (`brain_dump_parser.py`)

**Deterministic heuristic parser** — NO LLM dependency. Operator-locked: "deterministic over magic" for the onboarding moment.

### Algorithm
1. **Split** raw text on commas / newlines / semicolons / " then " / " + "
2. **Classify** each segment as task vs deadline via keyword set + leading action verb detection
3. **Extract time** via `dateparser` with phrase rewrites ("this weekend" → "saturday", "tonight" → "today 20:00") + future-bumping
4. **Extract duration** via regex ("60 min", "1.5 hours", time ranges like "2-4pm")
5. **Strip title** — removes date tokens, duration tokens, trailing prepositions, leading bullets
6. **Compute confidence** per signal strength

### Classification Priority
1. Leading action verb → **TASK** (even when deadline keyword present: "study for midterm" = task)
2. Deadline keyword without verb → **DEADLINE**
3. Date alone → task with low confidence
4. Bare segment → task with very low confidence

### Confidence Bands
- ≥0.85 — action verb + date, OR deadline keyword + date
- 0.45–0.85 — one signal but ambiguous
- <0.45 — bare segment (flagged in UI for edit)

### Binding Suggestions
For each task, runs `score_deadlines()` against parsed deadlines:
- ≥0.85 → **tier1_auto** (pre-checked in UI)
- 0.45–0.85 → **tier2_ask** (UI shows Yes/No pills)
- <0.45 → **tier3_skip** (not shown)

---

## 15. LLM Enrichment Pipeline (`llm_parser.py`)

Async background worker that enriches tasks after creation. NOT on the critical path.

### Dual-Backend Architecture
1. **NVIDIA NIM first** (when configured) — cloud, faster, more reliable
2. **Ollama fallback** — local, no data transfer, for non-operator users
3. NimConfigError (bad key) → `failed` (no Ollama fallback for config errors)
4. NimUnavailable (5xx/timeout) → falls through to Ollama

### Enrichment Fields
- `llm_priority` (1–5), `llm_sub_items` (scope breakdown), `llm_parsed_at`
- `llm_deadline_candidates` — ranked list with confidence scores

### Trust-Not-Rewrite Contract
Operator-locked invariant: "Do not silently rewrite canonical after user has seen it."
- **Existing source is tentative** (NULL or `parser_auto`) → LLM may populate candidate list
- **Existing source is user-visible** (`heuristic_*`, `user_explicit`, `user_corrected`, `llm_auto_confirmed`) → LLM stores alternative suggestion only, NEVER rewrites `deadline_id`
- Strong disagreement (LLM confidence ≥0.85 + different deadline) → stores in `llm_alternative_suggestion` for "Possible better match" chip

### Idempotency & Guards
- Voided-at re-check on refetch (prevents writing to soft-deleted rows)
- Terminal status check (enriched/unavailable/failed → skip)
- Pydantic validation of LLM output with 1 retry on JSON parse failure

---

## 16. JARVIS Agent (`jarvis_agent.py` + `jarvis_tools.py`)

Operator-only in-app AI assistant powered by NVIDIA NIM.

### Agent Loop Semantics
1. Build system prompt (Lyra context + clock + timezone + tool list)
2. Send messages + tools to NIM (temperature=0.2, max_tokens=900)
3. **No tool calls** → return as final answer
4. **READ tool calls** → execute immediately, append results, loop
5. **WRITE tool calls** → DO NOT execute, queue as pending confirmation, append stub result
6. Hard cap at **8 iterations** (defense against runaway loops)

### Read Tools (9 tools, execute immediately)
`list_today_tasks`, `list_deadlines`, `get_focus_minutes`, `get_overdue_count`, `get_top_course`, `get_pattern_summary`, `get_active_session`, `analyze_behavioral_signature`, `query_dark_columns`, `propose_pattern_hypothesis`

### Write Tools (4 tools, require user confirmation)
`create_task`, `start_focus_session`, `mark_deadline_done`, `sync_moodle_now`

### Discovery Layer (`analyze_behavioral_signature`)
Returns ~24 behavioral signals: pause-reason distribution, recovery latency, hesitation chain, schedule volatility, context-switch graph, post-pause transitions, valence distribution, disagreement events, snooze chains, reflection engagement, per-signal confidence tiers.

### Anti-Hallucination Rules
- Every tool result includes `covered_signal_categories` and `NOT_covered_dont_speculate_about_these`
- Agent MUST refuse to answer about NOT_covered signals
- Confidence scales with sample size: n<5 = cold_start, 5≤n<30 = tentative, n≥30 = confirmed

### NVIDIA NIM Client (`nvidia_nim_client.py`)
- OpenAI-compatible wrapper over `integrate.api.nvidia.com`
- Default model: `meta/llama-3.3-70b-instruct`
- **Error hierarchy:** `NimUnavailable` (5xx/timeout/429 → fallback), `NimConfigError` (4xx → fail)
- `chat_completion()` (single-shot) + `chat_completion_stream()` (SSE for chat UI)
- `health_check()` — 1-token probe for status indicator
- Privacy: only `is_operator=True` accounts hit NIM; other users stay on Ollama-only

---

## 17. External Integrations

### 17.1 Google Calendar (`calendar_sync.py`)
**Read-only** — imports user's primary calendar events as ambient scheduling context.
- Events are **NOT persisted** to `task` table — fetched on demand, cached in Redis (60s TTL)
- Rendered as read-only grey background blocks in `/calendar`
- Skips all-day events and declined events
- Access token cached in Redis (45min TTL), auto-refreshes via `google.oauth2.credentials`
- 401 → clears `google_refresh_token`, surfaces "Reconnect needed"

### 17.2 Moodle iCal Sync (`moodle_ics_sync.py`)
**Persisted** — imported events become `Deadline` rows with `external_source='moodle_ics'`.
- Parses `.ics` via `icalendar` library; skips RRULE recurring events and all-day events
- Extracts course codes from CATEGORIES field (e.g., "CSE281 (UG2023) - Intro to AI" → `CSE281`)
- `_widen_time_window()` overrides Moodle's `preset_time=recentupcoming` to pull full history
- Connect flow: preview endpoint → user confirms → URL stored → 6h sync cycle
- 4xx → clears URL + sets `moodle_disconnect_reason`
- Authtoken redacted in all log emissions
- Cap: 500 events per sync (defensive)

### 17.3 Moodle Web Services Sync (`moodle_submissions_sync.py`)
Auto-marks deadlines complete when Moodle reports a graded submission.
- `moodle_ws_token` stored Fernet-encrypted (alembic 044)
- Matches submissions to deadlines via `external_id` (Moodle assignment cmid)
- 6h sync cycle, parallel to iCal sync

### 17.4 Notion (`notion_client.py`)
Two-way task mirror. Sync deferred to Redis queue (was inline 1-8s per create before P0 fix).
- `sync_task()` — creates/updates Notion page
- `archive_page()` — archives on task delete
- Queue drained every 5min by APScheduler

---

## 18. Caching Architecture

### 18.1 `/me` Cache (`me_cache.py`)
- 30s TTL per user_id, keyed `me:{user_id}:v1`
- Busted on user-row mutations (~10 endpoints)
- Lazy-stamp side effects (`d1_return_at`, onboarding backfill) fire on cache MISS only
- Redis-down = graceful fallthrough (endpoint runs queries directly)

### 18.2 Tasks Range Cache (`tasks_range_cache.py`)
- Caches `/tasks/query` range payloads per user
- Invalidated on task create/update/delete/void

### 18.3 Undo Cache
- Redis-backed last-action cache per user
- Supports undo for create, delete, skip operations

---

## 19. Encryption (`encryption.py`)

Fernet symmetric encryption for credential-class secrets.
- Key derived from `settings.SECRET_KEY` via HKDF/SHA-256
- Storage format: `"fernet:" + base64_token` (prefix = migration marker)
- Values without prefix treated as legacy plaintext (backward compatible)
- Currently used for: `moodle_ws_token` (alembic 044)
- **Debt:** `google_refresh_token` and `moodle_ics_url` remain plaintext (Phase 6+)

---

## 20. Multi-Tenancy & Scoping (`scoping.py`)

**Structural defense against cross-user data leaks.**
1. `set_current_user_id()` called in per-request auth dependency
2. Stored in `contextvars.ContextVar` (concurrent-request safe)
3. SQLAlchemy `before_compile` event hook auto-injects `.filter(entity.user_id == current_user_id)` on every query
4. `User` table is exempt (PK is user_id)
5. Raw `db.execute(text(...))` bypasses auto-scoping — must scope manually
6. Background jobs must call `set_current_user_id()` per iteration via `_per_user.py` helper
7. Redis keys namespaced to `str(user_id)` — static key was the Phase 3.2 cross-user timer leak

---

## 21. Background Job Scheduler

14 APScheduler jobs with `misfire_grace_time=24h`:

| Job | Interval | Purpose |
|---|---|---|
| `reminders` | 1 min | Upcoming task alerts |
| `timer_overflow` | 2 min | Detect overrunning sessions |
| `pause_prediction` | 1 min | VT-17 pause prediction (10-min cooldown) |
| `resume_prediction` | 2 min | Resume-banner when paused ≥ p75 |
| `reconcile_responses` | 5 min | Close VT-17 acceptance windows |
| `notion_sync` | 5 min | Retry failed Notion syncs |
| `llm_enrichment` | 5 sec | Async LLM parser (max 1 instance, cap 3/cycle) |
| `orphan_task_recovery` | 15 min | EXECUTING tasks with no active session |
| `stale_session_recovery` | 15 min | Auto-close sessions > 12h old |
| `overdue_tasks` | 30 min | Auto-skip unstarted overdue tasks |
| `reconcile_deadline_outcomes` | 30 min | Write task_deadline_outcome rows |
| `sweep_missed_deadlines` | 1 hr | Transition past-due deadlines to `missed` |
| `moodle_ics_sync` | 6 hr | Pull .ics deadlines per connected user |
| `moodle_submissions_sync` | 6 hr | Auto-mark deadlines complete on Moodle submission |

---

## 22. Integrity Guards & Recovery

- **voided_at discipline:** every analytics query MUST filter `voided_at IS NULL`
- **Orphan recovery:** 15-min sweep catches EXECUTING tasks with no active StopwatchSession
- **Stale session recovery:** auto-closes sessions > 12h old (forgotten timers), marks `auto_closed=True`
- **Pause event closure:** `_close_open_pause_events()` seals dangling opens on cleanup
- **Zero-duration guard:** prevents 0-second sessions from recording as EXECUTED
- **Self-heal on status poll:** `_get_active()` validates Redis-bound task on every `/v1/stopwatch/status`
- **Data quality flags:** pre-April-15 sessions flagged and excluded from research
- **LYR-093 hardening:** `_require_current_user()` fails closed (no default to operator user_id=1)
- **Substitution detection:** links recently-deleted tasks to their replacements within 10min
- **VT-17 training integrity:** retroactive self-reports excluded from predictor training data

---

## 23. Project Governance Artifacts

| Document | Purpose |
|---|---|
| `MANIFESTO.md` | Constitution — 17+ rules, H1 kill-criterion, pre-registered formulas |
| `docs/calibration_contract.md` | Phase 2-6 inference engine spec (R1–R11) |
| `docs/dogfood_findings_living.md` | Real-time bug/UX friction log |
| `docs/jarvis_hypothesis_log.md` | AI-discovered behavioral patterns |
| `docs/feedback_loops_closure_plan.md` | 11 feedback loops tracked to closure |
| `docs/methodology.md` | Archetype clustering methodology |
| `docs/deadline_mechanism_design.md` | Loop 11 deadline binding spec |
| `docs/data_utilization_inventory_2026_05_02.md` | 196+ signal inventory |
| `docs/building_phases.md` | Implementation tiers and VT pre-registrations |

---

## 24. Known Risks & Blockers

1. **Legal:** Privacy Policy and ToS are placeholders; must disclose NVIDIA NIM data transfer
2. **Onboarding:** ~50% Brain Dump abandonment — needs skip/guided-tour mechanism
3. **Frontend cache:** React Query state can desync with DB during multi-task switching
4. **D1 return stamp:** reports 0% for trusted users despite actual return activity
5. **Credentials at rest:** `google_refresh_token` and `moodle_ics_url` stored plaintext (Fernet only for `moodle_ws_token`)
6. **Cairo timezone edge:** UTC-date duplicate-title detection shifts boundary by 2h
7. **"Coming Soon" UI:** placeholder components must be hidden for App Store submission
8. **Notion sync latency:** deferred to Redis queue but still fails silently on prolonged outage
