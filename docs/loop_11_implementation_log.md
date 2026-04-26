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
| Run `alembic upgrade head` against a fresh dev SQLite + verify downgrade cycle | This commit's verification | 15min | Tested via ORM only; need to verify the migration file itself executes |
| Backend CRUD endpoints for deadline (POST/GET/PUT/DELETE /v1/deadlines) | Phase F (deferred) | 3–4h | Schema is live but unwriteable from API without these |
| Parser Pass 2 — keyword-overlap inference | Phase G (deferred) | 2–3h | Currently only Pass 1 (explicit) works |
| Reconciliation jobs: `deadline_met` writer + `deadline.state='missed'` sweeper | Phase H (deferred) | 2–3h | `task_deadline_outcome` rows never get written without this |
| Analytics: `GET /v1/analytics/deadline-shape` + per-deadline bias_factor query | Phase I (deferred) | 3–4h | Rules 14, 15 cannot fire without these queries |
| Frontend deadline list + CRUD UI | Phase J (deferred) | 3–4 days | Users can't create/manage deadlines yet |
| Frontend task-creation deadline picker | Phase K (deferred) | 2–3 days | Tasks can't be bound to deadlines from UI yet |
| Soft-warning UX + RCT split-cohort flag | Phase L (deferred) | 2 days | Rule 16 stays INACTIVE until this ships |
| Deadline-progress dashboard + planning prompt | Phase M (deferred) | 1 week | Highest-leverage user-facing surface per `deadline_mechanism_design.md:85-110` |
| B-13 — `analytics.py:130` voided_at filter fix | Bundle with Phase I | 5min | Out-of-scope for this commit |

---

*This log is the audit trail for the Loop 11 thesis-instrument commit. Future sessions reviewing this work should start here, then read the approved plan, then read the MANIFESTO v1.12 diff. SIR step 7 (operator review) was completed via plan-mode approval before any code was written.*
