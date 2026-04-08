# Multi-User Migration Plan

*Status: design only. No implementation in this document.*
*Drafted Apr 8 2026. Targets the post-Apr 15 product phase.*
*Companion to `clustering_spec.md` — that doc assumes this migration has happened.*

---

## Goal

Convert Lyra Secretary from a single-tenant single-subject system into a multi-user product where every row in every table is owned by exactly one user, every endpoint is authenticated, and every background job is per-user-scoped — without losing the operator's existing 4+ days of data and without breaking the Apr 4–15 measurement window.

This is a **carefully sequenced migration**, not a rewrite. The single-user codebase is mostly correct — it just lacks an ownership column. Most of the work is mechanical: add `user_id` everywhere, scope every query, gate every endpoint. The hard parts are auth, the operator's grandfathered data, and the background jobs.

---

## Non-goals (explicit)

- **No** team / org / shared-task features. Each user is a sealed island. Sharing is a separate product question.
- **No** self-serve signup until after the migration is verified. The operator stays "user 1" for the first weeks.
- **No** changes to the state machine, the analytics layer, or the bias_factor model. Those are all single-user-correct already and become per-user-correct for free once `user_id` exists.
- **No** changes to the Apr 4–15 experimental data. The operator's existing 56 task rows must come through with full fidelity, including session_index_in_day, reschedule_count, signed_discrepancy, etc.
- **No** Notion sync changes in this migration. Each user will eventually need their own Notion workspace ID and API key, but that is a follow-up.

---

## Constraints

1. **The Apr 4–15 experiment must not be disrupted.** The migration cannot run before Apr 16. Period.
2. **Operator data must survive 1:1.** No row may be lost, no field may be silently nulled. Backfill the operator as `user_id = 1` and verify row counts match before and after.
3. **No downtime longer than 5 minutes.** This is a single-user system today, but the migration window cannot eat a full day of data collection.
4. **The operator's existing API clients (the OpenClaw skill, the Telegram bot, any local scripts) must keep working** with at most one configuration change (an auth token added to a header). Endpoint URLs and payloads do not change.
5. **The DB is SQLite.** Some constraints (deferred FKs, ALTER TABLE limitations) require an Alembic migration that recreates affected tables rather than in-place mutation. Plan around it.

---

## Phases (sequenced — do not parallelize)

### Phase 0 — Pre-migration freeze (1 day, Apr 16)

- Stop accepting new tasks for ~10 min while the migration runs.
- Take a full DB snapshot to `lyra_pre_multiuser_backup_apr16.sqlite`. Verify the backup loads in a separate sqlite3 session and row counts match.
- Tag the git repo: `pre-multiuser-migration`.
- Disable APScheduler jobs for the duration of the migration.

### Phase 1 — Schema (alembic migration 013)

Add the `user` table and `user_id` columns. Backfill the operator as `user_id = 1`.

```sql
CREATE TABLE user (
    user_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email              VARCHAR(255) UNIQUE NOT NULL,
    password_hash      VARCHAR(255) NOT NULL,        -- argon2id
    timezone           VARCHAR(64)  NOT NULL,        -- IANA, e.g. Africa/Cairo
    notion_api_key     VARCHAR(255),                 -- nullable; per-user Notion is later
    notion_database_id VARCHAR(64),
    created_at         DATETIME NOT NULL,
    -- Archetype fields (populated by clustering_spec implementation, nullable now)
    archetype                VARCHAR(40),
    archetype_assigned_at    DATETIME,
    instrument_scores        JSON
);

-- Then add user_id to every owning table:
ALTER TABLE task              ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1 REFERENCES user(user_id);
ALTER TABLE stopwatch_session ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1 REFERENCES user(user_id);
-- category_mapping stays global (it's a static seed table, not user data).

-- Indexes — every per-user query must hit one of these:
CREATE INDEX idx_task_user_state    ON task(user_id, state);
CREATE INDEX idx_task_user_start    ON task(user_id, planned_start_utc);
CREATE INDEX idx_stopwatch_user     ON stopwatch_session(user_id);
```

The `DEFAULT 1` plus the seeded `user_id=1` row for the operator does the backfill in one shot. After the migration runs, drop the default (a follow-up alembic step) so future inserts must specify `user_id` explicitly.

**Verify:** `SELECT COUNT(*) FROM task WHERE user_id IS NULL` returns 0. Same for `stopwatch_session`. Same for any new table introduced after this doc is written.

### Phase 2 — Auth layer (FastAPI dependency)

Add `app/api/deps.py::get_current_user(token: str = Depends(oauth2_scheme))`. Single source of authentication. Issues short-lived JWTs from a `POST /v1/auth/login` endpoint. Password hashing via `argon2-cffi` (already in the requirements ecosystem; add it).

Replace `Depends(get_db)` with `Depends(get_db), user: User = Depends(get_current_user)` on every endpoint. The `user` object is then passed to TaskManager / analytics endpoints, which scope every query.

**The operator gets a long-lived token** (180 days, no refresh required) for their existing clients. Document the token issuance flow in `DOCKER.md`.

### Phase 3 — Service layer scoping

Every query that currently looks like:

```python
db.query(Task).filter(...)
```

becomes:

```python
db.query(Task).filter(Task.user_id == user.user_id, ...)
```

This is mechanical but exhaustive. **Required helper:** add a base query class or a SQLAlchemy event hook that automatically injects `user_id = current_user.user_id` on every query against owning tables. This is the only sane way to prevent a future endpoint from forgetting to scope and silently leaking data across users.

Recommended: SQLAlchemy `@event.listens_for(Query, "before_compile", retval=True)` hook that walks the query and adds the filter if the entity has a `user_id` column. Implement once, audit once, then trust it.

`TaskManager` constructor signature changes from `TaskManager(db)` to `TaskManager(db, user)`. Every method that currently takes a `task_id` continues to take it, but the loaded task is verified to belong to `user.user_id` before any mutation. Cross-user access raises 404 (not 403 — 403 leaks the existence of the row).

### Phase 4 — Background jobs per-user

`workers/scheduler.py` currently runs three APScheduler jobs globally:
- reminders every 1 min
- Notion sync retry every 5 min
- timer overflow alerts every 2 min

These must become per-user-iterating:

```python
def reminder_job():
    for user in db.query(User).all():
        check_reminders_for(user)
```

For the operator-only deploy this is identical to today. With 100 users it's still trivial. With 10,000 users it needs a queue (Celery / RQ / arq) — but that's a scaling problem, not a multi-user problem. Out of scope for this migration.

The Redis namespace also needs per-user prefixing: `undo:{user_id}:{action_id}`, `idem:{user_id}:{key}`, `last_task:{user_id}`. The `RedisClient` wrapper takes a `user_id` in its constructor and prefixes every key.

### Phase 5 — Endpoint audit

After Phases 1–4 are merged, do a checklist pass against every endpoint in `app/api/v1/endpoints/`:

| Check | What it means |
|---|---|
| Has `Depends(get_current_user)` | Authenticated |
| Passes `user` to the service | Service layer can scope |
| Returns only this user's data | No cross-user leak in the response shape |
| Idempotency keys are user-scoped | Two users with the same key don't collide |

Build this as a test file `tests/test_multiuser_isolation.py` that creates two users, has each create a task, then asserts user A cannot see / read / mutate / delete user B's task on every endpoint. **This test is the migration's acceptance gate.** Phases 1–4 are not "done" until this test passes.

### Phase 6 — Operator cutover (Apr 16, ~5 min)

1. Stop the backend.
2. Run alembic upgrade head.
3. Insert the operator row: `email=ali@..., password_hash=..., timezone=Africa/Cairo, user_id=1`.
4. Issue the operator's long-lived token, save it to the OpenClaw skill config and the Telegram bot config.
5. Restart the backend.
6. Smoke test: `GET /v1/health`, `GET /v1/tasks/query?date=2026-04-16`, create a task, complete it, verify Notion sync.
7. Re-enable APScheduler.
8. Run the multi-user isolation test against the live system with a temporary second user, then delete that user.

If anything fails: roll back to `lyra_pre_multiuser_backup_apr16.sqlite` and re-tag the git branch as `multiuser-attempt-1-failed`. The single-user system continues running while the issue is diagnosed.

### Phase 7 — Second-user rollout (no earlier than Apr 23)

One week of operator-only multi-user-aware operation before any second user touches the system. This catches the cases the isolation test missed.

Then add a second user manually (no signup endpoint yet) — ideally a friend or willing tester, not a stranger — and run for a week with both users active. The first second-user is the smoke test for the migration in production.

Self-serve signup (`POST /v1/auth/register`) ships only after that second-user week is clean.

---

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Cross-user data leak via a forgotten query scope | Medium | Critical | The `before_compile` event hook in Phase 3 makes it structurally hard to forget. The isolation test in Phase 5 is the acceptance gate. |
| Operator's grandfathered data corrupted by the migration | Low | Critical | Phase 0 backup. Phase 1 verifies row counts pre/post. Phase 6 runs an end-to-end smoke test before declaring success. |
| Notion sync writes the wrong user's task to the wrong workspace | Low (operator-only initially) | High | Notion config is per-user from Phase 1 onward. Until Phase 7, only the operator has Notion creds, so the failure mode is contained. |
| Background jobs hammer the DB at scale | Low (single-digit users for a long time) | Low | Documented in Phase 4. Out of scope until N > 1000 users. |
| Auth token leak from a single user's misconfigured client | Medium | Medium | Tokens are 180-day not infinite. Add a `POST /v1/auth/revoke` endpoint in Phase 2. Document the rotation procedure. |
| Apr 15 experiment data subtly altered by the migration | Medium | Critical | The migration runs **after** Apr 15 only. No exceptions. Phase 0 is gated on the experiment having closed. |

---

## What stays the same

To make the scope of the change explicit, here is what does **not** change:

- The state machine.
- The conflict detector.
- The stopwatch / pause / resume / mark-abandoned logic.
- The discrepancy / cascade / insights / bias_factor analytics formulas (they just become per-user once `user_id` is in the query).
- The category taxonomy.
- The Notion sync format.
- The frontend / Telegram / OpenClaw skill payload shapes.
- The Apr 4–15 experimental data and its analysis pipeline.

The migration is **structurally invasive** (every endpoint and every query touched) but **semantically conservative** (no behavior changes for the operator). That asymmetry is what makes it safe to do as one migration rather than ten.

---

## Decision points deferred to implementation time

1. **JWT vs session cookies** — JWT is recommended for the API-first design, but if a web UI is added before this migration ships, sessions may be friendlier. Decide at Phase 2 start.
2. **Argon2id parameters** — defaults from `argon2-cffi` are fine for the personal-product phase. Tune only if signup latency complaints arrive.
3. **Email verification on signup** — yes for self-serve (Phase 7+), no for the operator and the manual second user. Ship verification with the public signup endpoint.
4. **Per-user feature flags** — out of scope for this migration. Add a separate `feature_flag` table later if needed.
5. **Data export per user (GDPR-style)** — should ship with self-serve signup, not before. Design a `GET /v1/me/export` endpoint that streams the user's tasks + sessions + analytics as JSON.
6. **Account deletion** — same as above. Hard-delete with a 30-day grace, not soft-delete, for compliance simplicity.

---

## What this plan does not solve

- **Horizontal scaling.** This is a single-process FastAPI + SQLite + APScheduler stack. It will run fine for the first few hundred users on a small VM. The day SQLite becomes the bottleneck, the migration is to Postgres + an external job queue, and that is a *separate, larger* migration with its own plan.
- **The cold-start problem.** That's `clustering_spec.md`'s job. This migration only adds the user row and the schema fields the clustering implementation will populate.
- **The product question of who Lyra is for.** The current operator profile (a single technical user running a self-experiment) is not the population the clustering spec assumes. Identifying the actual target user is a product / research question, not a migration question. Flag for the post-Apr-15 product phase.
