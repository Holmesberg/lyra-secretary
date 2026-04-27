# Loop 11 Foundation — Implementation Log

**Build session:** 2026-04-26
**Approved plan:** `~/.claude/plans/giggly-launching-lynx.md`
**MANIFESTO version bumped:** v1.11 → v1.12 (Rules 14/15/16 + Rule 12 amendment)
**Migration:** alembic 033 (`033_deadline_mechanism_foundation.py`)
**Test count:** 328 → 360 (32 added across 3 new test files; zero existing tests broken)

This log captures **every bug, design tension, and assumption gap** caught during planning and implementation. Documented per operator discipline (`feedback_always_document` memory) so future sessions don't re-derive what was already worked through.

Bugs are categorized by **stage caught** and **resolution status**.

---

## Bugs caught during PLAN-mode review (before code)

### B-01 — EXECUTED-task immutability violation (BLOCKER, resolved before code)

**Surfaced by:** research-integrity audit agent during 3-domain SIR scan.
**Source:** original Loop 11 spec at `docs/feedback_loops_closure_plan.md:333-347` proposed writing `deadline_met` directly to the `task` row during reconciliation.
**Conflict:** `backend/app/services/state_machine.py:29,61-64` defines EXECUTED as immutable (`is_mutable` returns False). Writing post-execution columns to a task row would silently break this invariant.
**Resolution:** new `task_deadline_outcome` table mirroring the `external_event_outcome` template (Alembic 027). Frozen-at-compute-time semantics → research-reproducible. Operator confirmed Option A via `AskUserQuestion`.
**File:** `backend/app/db/models.py` — new `TaskDeadlineOutcome` class.

### B-02 — VT-21 RCT pre-registration was missing (BLOCKER, partially resolved)

**Surfaced by:** research-integrity audit agent.
**Source:** `docs/deadline_mechanism_design.md:223-228` notes the soft-warning UX is a closed-loop intervention contaminating VT-21 measurement; pre-registration of a split-cohort RCT is required before user data is collected with the UX live.
**Conflict:** the design doc itself flags this gap but does NOT resolve it. Spec line 252 says "Do NOT build until pre-registrations are committed to MANIFESTO."
**Resolution (this commit):** Rule 16 (`MANIFESTO.md` v1.12) pre-registers the RCT design — `(user_id mod 2)` arm partition, 4-week comparison, kill criterion, 20-user × 30-task floor, no post-hoc tuning. Rule is INACTIVE until UX surface ships (Phase L of the deferred plan), so today's commit does NOT yet trigger the RCT.
**Remaining work:** when Phase L ships the soft-warning, code must read `(user_id mod 2)` and gate the surface accordingly.

### B-03 — Markdown false positives in bullet counter (KNOWN APPROXIMATION)

**Surfaced by:** plan-time review.
**Issue:** `^\s*[-*•·]` matches dashes inside fenced code blocks. A description containing ` ```bash\n- ls\n``` ` would count `- ls` as a bullet.
**Decision:** v1 instrument approximation. Documented in `extract_scope_bullets` docstring. Not fixed in this commit. Eventual writeup must acknowledge.
**File:** `backend/app/services/parser.py` — module-level docstring near `BULLET_PATTERN`.

### B-04 — Sign convention in Rule 14 ambiguous (FIXED in plan)

**Surfaced by:** real-time bug-catch pass on draft plan.
**Issue:** original Rule 14 wording said "Spearman ρ between (due_at_utc - executed_end_utc) and delta" without specifying sign meaning. Reader must guess whether positive ρ supports H2 or refutes it.
**Resolution:** Rule 14 now explicitly defines `deadline_distance_minutes = (due_at_utc − executed_end_utc).total_seconds() / 60` with "positive when met (executed before deadline), negative when missed."
**File:** `MANIFESTO.md` line 1061.

### B-05 — `_validate_active_deadline` parameter-passing wrong (FIXED in plan)

**Surfaced by:** plan review.
**Issue:** initial draft passed `user_id` as a parameter. Codebase convention (`backend/app/workers/jobs/_per_user.py:28-52`) reads `current_user_id` from a ContextVar, not from a method param.
**Resolution:** helper renamed to `_validate_bindable_deadline` (also fixes B-06 below) and reads from ContextVar via `_require_current_user()`.
**File:** `backend/app/services/task_manager.py` — new `_validate_bindable_deadline` method.

### B-06 — `_validate_active_deadline` name was wrong post state-machine extension (FIXED in plan)

**Surfaced by:** operator decision 2026-04-26 to extend deadline state enum.
**Issue:** "active" implies state must be exactly `'active'`. After adding `'planned'` to the enum, both states should be bindable. Original name would have signaled wrong intent.
**Resolution:** renamed to `_validate_bindable_deadline`. Validation logic accepts `state IN ('planned', 'active')`.
**File:** `backend/app/services/task_manager.py`.

### B-07 — Deadline state-default would have been wrong (FIXED in plan)

**Surfaced by:** plan review after operator's `planned`/`skipped` extension.
**Issue:** original `deadline_mechanism_design.md:141` had `default 'active'`. With the state enum now including `'planned'`, the default should be `'planned'` — deadlines should start dormant and auto-transition to `'active'` on first task bind. Without this fix, "active deadlines" queries (Phase H reconciliation, Phase F endpoints) would have been polluted with empty-shell deadlines that no task ever bound to.
**Resolution:** migration 033 sets `server_default="planned"`; ORM model `Deadline` sets `default="planned"`; auto-transition logic in `create_task` promotes to `'active'` on first bind.
**Files:** `backend/alembic/versions/033_deadline_mechanism_foundation.py`, `backend/app/db/models.py`.

### B-08 — `task_deadline_outcome.voided_at` wasn't in original spec (FIXED in plan)

**Surfaced by:** symmetry audit during plan drafting.
**Issue:** if a task is voided post-EXECUTED (LYR-095 scenario), its outcome row needs to be invalidatable. Without a `voided_at` column on `task_deadline_outcome`, future analytics queries would have to LEFT JOIN `task` and filter `task.voided_at IS NULL` everywhere — easy to forget, leaks voided rows into research signal.
**Resolution:** column added to both migration and ORM. Operator did not object during the plan-mode `Open surfacing #2`.
**Files:** migration 033, `backend/app/db/models.py:TaskDeadlineOutcome`.

### B-09 — `complete_task` write timing was implicit (FIXED in plan)

**Surfaced by:** plan-mode review.
**Issue:** `task.scope_bullet_count_at_execute` write must happen BEFORE the state-machine transition to EXECUTED, while task is still mutable (PAUSED/EXECUTING). After EXECUTED, the immutability invariant blocks the write — but only at the StateMachine layer, not at the ORM layer, so a misplaced write would silently succeed in tests but break in production.
**Resolution:** plan and code make the ordering explicit with a comment. The write at `task_manager.py:complete_task` happens AFTER `executed_duration_minutes` is set but BEFORE `self.state_machine.transition(task, EXECUTED)`.
**File:** `backend/app/services/task_manager.py:complete_task`.

### B-10 — Migration ordering invariant (VERIFIED, not a bug)

**Issue checked:** does `deadline` table exist before the FK column on `task` is added that references it?
**Verification:** migration upgrade() creates tables in this order: (1) `deadline`, (2) `task_deadline_outcome`, (3) adds columns to `task`. The `deadline_id` FK on task references the already-created `deadline` table. ✓
**File:** `backend/alembic/versions/033_deadline_mechanism_foundation.py:upgrade()`.

---

## Bugs caught during IMPLEMENTATION

### B-11 — Test-fixture timezone offset bug (FIXED in test)

**Surfaced by:** first run of `test_create_task_with_deadline.py` — all 12 tests failed with `ValueError: start_in_past`.
**Root cause:** `TaskManager.create_task` calls `to_utc(start)` which treats naive datetimes as Cairo local time (UTC+3) and converts to UTC. The test fixture used `datetime.utcnow() + timedelta(hours=2)` — when treated as Cairo and converted to UTC, this lands 1 hour in the past, tripping the past-time guard at `task_manager.py:209`.
**Resolution:** bumped fixture offset to `+timedelta(hours=24)`, comfortably clearing the guard regardless of TZ. Documented the pitfall in the helper docstring so future tests don't re-hit it.
**File:** `backend/tests/test_create_task_with_deadline.py:_create_task_args` docstring.
**Lesson for future tests:** don't use `utcnow() + small_offset` as a "future time" — TZ conversions can land you in the past. Either use `now_utc()` (TZ-aware) or pad with hours.

### B-12 — Description docstring SyntaxWarning (FIXED in test)

**Surfaced by:** pytest output `SyntaxWarning: invalid escape sequence '\s'`.
**Root cause:** `test_scope_bullet_counter.py` docstring contained `\s` outside a raw string. Python 3.12 warns on unknown escape sequences in regular strings.
**Resolution:** prefixed docstring with `r"""` for raw-string semantics.
**File:** `backend/tests/test_scope_bullet_counter.py:1`.

---

## Pre-existing issues NOT fixed in this commit (filed for future)

### B-13 — Missing `voided_at` filter in analytics summary count

**Source:** `backend/app/api/v1/endpoints/analytics.py:130`
```python
voided_count = db.query(Task).filter(Task.initiation_status == "system_error").count()
```
**Issue:** counts system-error tasks for research summary but does NOT filter `voided_at IS NULL`. Per `feedback_voided_at_guard` memory, every Task query should filter voided rows. This is a MINOR violation — the count is in `/analytics/discrepancy` summary, not in any kill-criterion path.
**Decision:** out of scope for Loop 11 commit. File a follow-up under LYR-NNN to bundle with the next analytics-touching commit.

### B-14 — `task.scope_outcome` enum vs new `scope_bullet_count_*` columns

**Issue:** `task.scope_outcome` (Alembic 024, values `stuck_to_plan | expanded | reduced`) is a **user self-report** of scope outcome at execute time. The new `scope_bullet_count_at_plan/execute` columns are **automated counts** of the description bullets at two timepoints. These are DIFFERENT signals.
**Decision:** keep both. `scope_outcome` captures the user's narrative ("I expanded scope"); `scope_bullet_count_*` captures objective measure. A future cross-analysis can ask: when `scope_outcome='expanded'`, did `scope_bullet_count_at_execute > scope_bullet_count_at_plan`? Worth its own pre-registered analysis rule when n is sufficient.
**File this in:** future `parked_ideas.md` entry once dataset density justifies.

---

## Verified non-issues (audited but no action needed)

### V-01 — `re.UNICODE` flag redundancy

`extract_scope_bullets` uses `re.MULTILINE` only (operator review removed a redundant `re.UNICODE` flag — Python 3 enables Unicode by default for str patterns). Bullet pattern matches U+2022 `•` and U+00B7 `·` correctly without the flag. Verified in `test_scope_bullet_counter.py::test_unicode_bullets`.

### V-02 — `server_default=sa.func.now()` cross-DB compat

Verified by checking existing migration patterns (`030_pause_event_retroactive_flag.py` uses `sa.false()` server_default). SQLAlchemy's abstraction handles Postgres `now()` and SQLite `CURRENT_TIMESTAMP` transparently.

### V-03 — Auto-transition idempotency

Concern: two concurrent task-creates targeting the same `planned` deadline. **Verified safe**: each task-create runs in its own DB transaction. The first commits with `state='active'`; the second reads `state='active'` (no-op via the `if state == 'planned'` guard). No race in this specific transition.

**Note for Phase H** (deferred): the `state='missed'` reconciliation job is NOT idempotent across concurrent runs because two scheduler instances could both write to the same row. Phase H must use `INSERT ... ON CONFLICT` (Postgres) or row-level locking. Filed as a Phase H requirement.

### V-04 — `ValueError → HTTP 400` mapping

Verified at `backend/app/api/v1/endpoints/tasks.py:131-138`. The catch-all `except ValueError as e: raise HTTPException(status_code=400, detail=str(e))` handles all new error types (`deadline_not_found`, `deadline_voided`, `deadline_terminal_state`) without modification. ✓

### V-05 — Existing call-sites of `create_task`

Two callers found: `tasks.py:65` (API endpoint, updated to pass `deadline_id`) and `stopwatch_manager.py:449` (internal, keeps default `deadline_id=None`). Backward compatible. ✓

---

## Implementation order summary (chronological)

1. **Phase A** (1h) — MANIFESTO v1.12: Rules 14/15/16 + Rule 12 amendment. Committed independently as `593fce0`.
2. **Phase B** (45m) — Alembic migration 033 written + syntax-checked. NOT yet run against any DB.
3. **Phase C** (1h) — `Deadline`, `TaskDeadlineOutcome` ORM classes; 5 new task columns + 2 relationships; new `schemas/deadline.py`; `TaskCreateRequest` + `TaskDetail` extended.
4. **Phase D** (30m) — `extract_scope_bullets` helper added to `parser.py`. 13 unit tests pass.
5. **Phase E** (2h) — `_validate_bindable_deadline` helper; `create_task` signature + body updated; `complete_task` re-sample hook added; API endpoint dispatch updated. Migration test (7 tests) and create-task-with-deadline test (12 tests, with B-11 timezone fix) added.
6. **Verification** — full pytest suite: 360 passed (was 328), zero regressions.

Total elapsed: ~5h vs. plan estimate 6–10h.

---

## Outstanding follow-ups

| Item | Phase | Cost | Reason |
|------|-------|------|--------|
| Run `alembic upgrade head` against Supabase | Operator | 15min | Tested via ORM only; permission denied during agent run, deferred to stable-wifi session |
| Frontend deadline list + CRUD UI | Phase J (deferred) | 3–4 days | Users can't create/manage deadlines yet |
| Frontend task-creation deadline picker | Phase K (deferred) | 2–3 days | Tasks can't be bound to deadlines from UI yet |
| Soft-warning UX + RCT split-cohort flag | Phase L (deferred) | 2 days | Rule 16 stays INACTIVE until this ships |
| Deadline-progress dashboard + planning prompt | Phase M (deferred) | 1 week | Highest-leverage user-facing surface per `deadline_mechanism_design.md:85-110` |

---

## Backend Phases F–I + G — second commit (2026-04-26 same session)

After the foundation commit (`f43a234`), Phases F + G + H + I + B-13 fix were
shipped in one bundled backend commit. Frontend phases J–M remain deferred
(need operator design input on UX and the soft-warning RCT timing).

### Phase F — Deadline CRUD endpoints (~2h)

- New service `backend/app/services/deadline_manager.py` — single mutation
  authority mirroring `TaskManager`. Reads `current_user_id` from ContextVar,
  enforces voided_at filtering, validates state-transition graph.
- New endpoints `backend/app/api/v1/endpoints/deadlines.py`:
    `POST   /v1/deadlines`             create (state defaults to 'planned')
    `GET    /v1/deadlines`              list with optional `state` filter,
                                       optional `?include_voided=true`
    `GET    /v1/deadlines/{id}`         get one (404 if not found OR cross-user)
    `PUT    /v1/deadlines/{id}`         update fields + state transitions
    `DELETE /v1/deadlines/{id}`         soft-delete (sets voided_at)
- Registered in `backend/app/api/v1/router.py`.
- 22 tests in `test_deadline_endpoints.py`.

State transition enforcement (USER_TRANSITIONS_FROM map in deadline_manager.py):
    planned → {active, skipped}
    active  → {completed, skipped}
    completed | missed | skipped → {} (terminal; void via DELETE)

Cross-user access returns 404 (not 403) — avoids existence-leak signal.

### B-13 — analytics.py:130 voided_at filter fix (5min)

Bundled while in the analytics file. Original query counted `system_error`
tasks for research summary without the discipline filter. Now explicitly
filters `voided_at IS NOT NULL` AND `initiation_status == 'system_error'`.
Same count in practice (system_error implies voided in current code paths)
but the filter makes the discipline acknowledgment explicit.

### Phase H — Reconciliation jobs (~1.5h)

Two new APScheduler jobs registered alongside the existing 8:

1. **`reconcile_deadline_outcomes`** (every 30 min)
   - File: `backend/app/workers/jobs/reconcile_deadline_outcomes.py`
   - For EXECUTED, non-voided, deadline-bound tasks without an outcome row,
     compute `deadline_met` and `delay_minutes` and write to
     `task_deadline_outcome` (new table from alembic 033).
   - Idempotent: LEFT JOIN filter excludes already-reconciled rows.
   - Skips voided deadlines and voided tasks per voided_at_guard.
2. **`sweep_missed_deadlines`** (every 1 hour)
   - File: `backend/app/workers/jobs/sweep_missed_deadlines.py`
   - For Deadline rows in 'active' state past `due_at_utc`, transition to
     'missed'. Planned deadlines past due_at stay planned (deliberate —
     planned = user never bound a task; not the same as "ran out of time").
   - Voided deadlines skipped.
- 19 tests across `test_reconcile_deadline_outcomes_job.py` and
  `test_sweep_missed_deadlines_job.py`.
- `test_state_consistency.py:test_apscheduler_job_count` updated 8→10.

### Phase I — `/v1/analytics/deadline-shape` (~1.5h)

- File: appended to `backend/app/api/v1/endpoints/analytics.py`.
- Pre-registered against MANIFESTO Rules 14 + 15.
- Auto-scoped to current user via `get_current_user_id()`.
- voided_at_guard applied to all three tables (TaskDeadlineOutcome, Task, Deadline).
- Response shape:
    `summary` — total / met / missed / met_rate / mean_delay / median_delay
    `by_match_source` — stratified by user_explicit / parser_auto / user_corrected
                        (Rule 14 stratification)
    `by_scope_bullet_count_band` — 0 / 1-3 / 4-6 / 7+ buckets (Rule 12 amendment)
    `per_deadline` — per-deadline aggregation including
                     `bias_factor_observed = mean(signed delta) / mean(planned)`
                     for Rule 15 within-user σ computation downstream.
- 9 tests in `test_analytics_deadline_shape.py`.

### Phase G — Parser Pass 2 keyword-overlap inference (~1h)

- New helper `infer_deadline_binding(title, candidates)` in `parser.py`.
- Asymmetric ratio (over `task_tokens` not `deadline_tokens`) — a task whose
  title is fully contained in a deadline description matches strongly even
  if the deadline has many unrelated words.
- Stoplist: short common words (`the`, `a`, `to`, etc) + scheduling fillers
  (`today`, `tomorrow`, `morning`, etc) + tokens shorter than 3 chars.
- Threshold: ratio ≥ 0.5 AND ≥ 1 non-stoplist shared token.
- Tie-break: highest ratio first; on ties, earliest `due_at_utc` wins.
- Wired into `TaskManager.create_task`: when `deadline_id` is None, Pass 2
  loads bindable candidates (state ∈ planned|active, voided_at IS NULL) and
  picks the best match if any. Sets `deadline_match_source='parser_auto'`,
  confidence equal to the overlap ratio.
- 16 tests in `test_parser_pass2_keyword_binding.py` covering pure-function
  semantics, integration via TaskManager, voided/terminal exclusion, and
  cross-user invisibility.

### Bug-catch log additions (Phases F-I-G)

- **B-15 — `set_current_user_id` not enough for TestClient tests.** UserScopeMiddleware reads `X-User-Id` header and overwrites ContextVar per-request, so prior `set_current_user_id(user_a.user_id)` calls are clobbered. Initial Phase F tests passed by accident because all operations defaulted to user_id=1. Fixed by passing `headers={"X-User-Id": str(uid)}` on every TestClient call. Removed the "no_auth → 401" test since the middleware always falls back to user_id=1 in dev for X-User-Id absent — testing the 401 path requires sending a *bad* Bearer token, not "no header at all."

- **B-16 — APScheduler job-count gate.** Adding the two Phase H jobs broke `test_state_consistency.py:test_apscheduler_job_count` which hardcoded the expected count at 8. Updated to 10 with the new job names listed in the docstring. This is by design — the test is a trip-wire for "did someone add/remove a job without updating the documentation?"

- **B-17 — Pass 2 vs Pass 1 ordering in create_task.** Pass 2 inference was almost-wired to fire even when `deadline_id` was provided, which would have overridden the user's explicit choice silently. Fixed by guarding on `if deadline_id is not None` for Pass 1 vs `else` for Pass 2 — explicit binding always wins.

- **B-18 — Test fixture timezone offset (recurrence of B-11).** New Phase G tests initially used `datetime.utcnow() + timedelta(hours=2)` which is in the past after Cairo→UTC conversion. Bumped all to `+timedelta(hours=24)`. The B-11 lesson is repeating itself; consider extracting a `_future_start()` helper into `conftest.py`.

### Test totals

- Before today's session: 328
- After foundation commit `f43a234`: 360 (+32)
- After Phases F-I-G (this commit): 426 (+66 from foundation; +98 from baseline)

All 426 pass. Zero pre-existing test regressions.

---

## 2026-04-27 — Phases J + K (frontend deadline list page + picker integration)

Phase J — `/deadlines` list page (`frontend/app/(app)/deadlines/page.tsx`):
- Three sections — Active deadlines (state ∈ planned|active), Completed,
  Missed/Skipped — sorted by due_at_utc (active asc; completed by
  completed_at desc; terminal by due_at desc).
- Empty state + new-deadline CTA + per-row Edit / Void affordances.
- "Void" requires a click-confirm step to defend against accidental
  soft-deletes; the row stays visible until the API returns 204.
- Sidebar entry added to `app-shell.tsx` between Calendar and Table.

Phase J supplement — single `<DeadlineModal mode="create" | "edit">`
component (`frontend/components/deadline-modal.tsx`):
- Mirrors the `ReflectionModal` dialog pattern.
- Edit mode adds Mark complete / Mark skipped buttons when the deadline
  is in `planned` or `active` state (terminal-state rows hide them).
- Default due-at = +7 days at 17:00 local on create.

Phase K — Pass 2 deadline-binding preview, parser endpoint + modal hookup:
- Backend `POST /v1/parse/deadline-preview` in
  `backend/app/api/v1/endpoints/parse.py`. Read-only inference; reuses
  the existing `infer_deadline_binding` helper so the preview can never
  disagree with what creation would actually bind. Filters:
  voided_at IS NULL, state ∈ {planned, active}.
- Frontend `lib/deadlines.ts` (NEW) — full CRUD client + preview client.
- Frontend `lib/tasks.ts` `CreateTaskInput` extended with optional
  `deadline_id`, threaded through all three create call sites in
  `new-task-modal.tsx` (happy path, soft-conflict force, paused-conflict
  interruption).
- `NewTaskModal` deadline picker (`DeadlinePickerSlot` subcomponent):
  three modes — bound (clear button), suggestion (confirm / pick another /
  no deadline), idle (+ bind link). 500ms debounce on title+description
  changes; race-safe via AbortController; suppressed when the user has
  manually picked.

Tests:
- `test_parse_deadline_preview.py` (NEW, 8 tests): no-candidates empty
  payload, strong match returns binding, weak match below 0.5 threshold
  returns null, voided/terminal-state filters, cross-user invisibility.
  The 401-unauth path is unreachable through TestClient because
  `UserScopeMiddleware` defaults to user_id=1; documented in the test
  header rather than swept under the rug.

### Bug-catch log additions (Phases J-K)

- **B-19 — `api()` always parses JSON.** The shared HTTP client at
  `frontend/lib/api.ts` calls `res.json()` unconditionally, which blows
  up on 204 No Content responses. The deadline soft-delete (DELETE
  /v1/deadlines/{id}) returns 204, so `voidDeadline` had to drive
  `fetch` directly and tolerate the empty body. Did not refactor the
  shared client because the existing JSON-only contract is load-bearing
  for every other caller.

- **B-20 — Race-safe parser preview.** Without an `AbortController`,
  fast typing can let a slow Pass-2 response from "study s" overwrite
  a fresh response from "study session". Aborting on every input change
  keeps the latest-wins invariant.

- **B-21 — Picker query gated on showPicker.** The bindable-deadlines
  list query is `enabled: showPicker` so we don't fetch the user's full
  deadline list every time the modal opens — only when the user reaches
  for the manual picker. Shaves 1 GET off the common path.

### Test totals (J + K)

- Before this session: 463 (post-Loop-1 ship)
- After Phase K (this commit): 471 (+8 preview-endpoint tests)

All 471 pass. Zero pre-existing test regressions. Frontend tsc clean,
production build emits `/deadlines` at 4.75 kB / 143 kB First Load.

---

*This log is the audit trail for the Loop 11 thesis-instrument commit. Future sessions reviewing this work should start here, then read the approved plan, then read the MANIFESTO v1.12 diff. SIR step 7 (operator review) was completed via plan-mode approval before any code was written.*
