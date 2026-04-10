# Architecture Design

*Consolidated from: `multiuser_migration_plan.md`, `phase_4_prerequisites.md`.*
*Last updated: April 10, 2026.*

---

## 1. Multi-User Migration Plan

*Status: design only. Targets the post-Apr 15 product phase.*
*Companion to `docs/methodology.md` (clustering spec) — that section assumes this migration has happened.*

### Goal

Convert Lyra Secretary from single-tenant to multi-user: every row owned by exactly one user, every endpoint authenticated, every background job per-user-scoped — without losing the operator's Apr 4-15 data.

### Non-goals

- No team/org/shared-task features. Each user is a sealed island.
- No self-serve signup until migration is verified. Operator stays "user 1."
- No changes to state machine, analytics, or bias_factor model. Those become per-user-correct for free once user_id exists.
- No changes to the Apr 4-15 experimental data. All fields must survive with full fidelity.
- No Notion sync changes in this migration (per-user Notion is a follow-up).

### Constraints

1. Migration cannot run before Apr 16.
2. Operator data must survive 1:1 (backfill as user_id=1, verify row counts).
3. No downtime longer than 5 minutes.
4. Existing API clients keep working with at most one config change (auth token header).
5. DB is SQLite — some constraints require table recreation in Alembic.

### Phases (sequenced)

**Phase 0 — Pre-migration freeze (1 day, Apr 16)**
- Stop accepting tasks for ~10 min. Full DB snapshot. Git tag: `pre-multiuser-migration`. Disable APScheduler.

**Phase 1 — Schema (alembic migration)**
- Add `user` table with auth fields + archetype fields (nullable).
- Add `user_id` (INTEGER NOT NULL DEFAULT 1) to `task` and `stopwatch_session`.
- Indexes: `idx_task_user_state`, `idx_task_user_start`, `idx_stopwatch_user`.
- After migration: drop default so future inserts must specify user_id.

**Phase 2 — Auth layer**
- `get_current_user(token)` FastAPI dependency. JWTs from `POST /v1/auth/login`. Argon2id password hashing.
- Replace `Depends(get_db)` with `Depends(get_db), user = Depends(get_current_user)` on every endpoint.
- Operator gets 180-day long-lived token.

**Phase 3 — Service layer scoping**
- Every query adds `Task.user_id == user.user_id`.
- SQLAlchemy `before_compile` event hook auto-injects user_id filter on owning tables. *(Note: this is already implemented as of v1.5 — see `app/db/scoping.py`.)*
- `TaskManager(db, user)` — loaded tasks verified before mutation. Cross-user access returns 404 (not 403).

**Phase 4 — Background jobs per-user**
- Jobs iterate over all users. Redis keys prefixed per-user: `undo:{user_id}:...`, `idem:{user_id}:...`, etc. *(Note: per-user Redis namespacing already implemented via `StopwatchManager._user_key()` as of Phase 3.2.)*

**Phase 5 — Endpoint audit**
- Checklist: every endpoint has auth dependency, passes user to service, returns only that user's data, idempotency keys are user-scoped.
- Acceptance gate: `tests/test_multiuser_isolation.py` — two users, each creates a task, neither can see/mutate the other's. *(Note: already exists — both basic and adversarial suites.)*

**Phase 6 — Operator cutover (Apr 16, ~5 min)**
- Stop backend, run alembic, insert operator row, issue token, restart, smoke test, re-enable APScheduler.

**Phase 7 — Second-user rollout (no earlier than Apr 23)**
- One week operator-only before any second user. Self-serve signup ships only after second-user week is clean.

### Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Cross-user data leak via forgotten scope | Medium | Critical | `before_compile` hook + isolation test suite |
| Operator data corrupted by migration | Low | Critical | Phase 0 backup + row count verification |
| Notion sync writes wrong user's task | Low | High | Per-user Notion config; operator-only initially |
| Background jobs hammer DB at scale | Low | Low | Out of scope until N > 1000 |
| Auth token leak | Medium | Medium | 180-day tokens, revocation endpoint |
| Apr 15 data subtly altered | Medium | Critical | Migration runs AFTER Apr 15 only |

### What stays the same

State machine, conflict detector, stopwatch/pause/resume, analytics formulas, category taxonomy, Notion sync format, frontend payload shapes, Apr 4-15 data.

### Deferred decisions

1. JWT vs session cookies (decide at Phase 2 start)
2. Argon2id parameters (tune only if signup latency complaints)
3. Email verification (with self-serve signup, not before)
4. Per-user feature flags (separate table later if needed)
5. Data export / GDPR (with self-serve signup)
6. Account deletion (hard-delete with 30-day grace)

---

## 2. Phase 4 Prerequisites — Design Notes

*Status: design only. No code changes.*

These are implementation designs for Phase 4 coding. Each is self-contained and independent.

### 2.1 Schema refactor: `planned_start_utc` / `planned_end_utc` rename

**Current:** `task.start` and `task.end` (both DateTime, UTC). `end` is ambiguous with `executed_end`.

**Proposed:**

| Current | Proposed | Reason |
|---|---|---|
| `task.start` | `task.planned_start_utc` | Explicit about what it represents and its timezone |
| `task.end` | `task.planned_end_utc` | Disambiguates from `executed_end` |

**Migration plan:**
1. Add new columns (nullable)
2. Backfill from old columns
3. Drop old columns
4. Update all references: models, services, schemas, frontend
5. API response field names can stay `start`/`end` for backwards compatibility

**Risk:** High-touch refactor across every layer. Do in a single PR with comprehensive test run. Do NOT combine with other schema changes.

### 2.2 `useCurrentTime` hook — frontend time freshness

**Problem:** Today page uses `new Date()` at render time, never refreshed. Tab open past midnight shows yesterday's tasks. Timer banner relies on 10s polling for elapsed time.

**Proposed hook:**

```typescript
export function useCurrentTime(intervalMs: number = 60_000): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}
```

Usage: `todayLocal()` date rollover, header date display, optional 1s timer banner clock.

### 2.3 Stale session recovery job

**Problem:** If Redis is flushed while a stopwatch runs, the session row has `end_time IS NULL` forever. Task stays EXECUTING with no recovery.

**Proposed:** APScheduler job every 5 minutes. Finds sessions running >4 hours with no Redis active key. Auto-closes them with `auto_recovered = True` flag. Does NOT set `post_task_reflection` (user wasn't present).

Schema addition: `stopwatch_session.auto_recovered` (Boolean, default False).

Edge cases handled: Redis flush mid-session (caught at next tick), server crash within 5 min (existing rehydration handles it), multiple stale sessions per user (all processed).

### Implementation order

1. `useCurrentTime` hook (smallest scope, no backend changes)
2. Stale session recovery (independent backend change)
3. Schema refactor (largest scope, do last and in isolation)

All three are independent of Phase 4 analytics features and can be a Sprint 0 infrastructure batch.

---

## 3. Docker Networking (OpenClaw Bridge)

Lyra Secretary and OpenClaw run as separate Docker Compose stacks with separate networks. The OpenClaw gateway needs to reach `http://backend:8000`.

**Solution:** Add Lyra's network as external in OpenClaw's docker-compose.yml:

```yaml
services:
  openclaw-gateway:
    networks:
      - default
      - lyrasecretaryv01_default

networks:
  default:
  lyrasecretaryv01_default:
    external: true
```

The gateway container has a foot in both networks, resolving `backend` via Docker DNS.

**Verify:** `docker exec openclaw-openclaw-gateway-1 curl -s http://backend:8000/v1/health`

The `--allow-unconfigured` flag in OpenClaw allows `exec` calls to arbitrary commands including `curl` to the Lyra backend. See OpenClaw documentation for configuration.
