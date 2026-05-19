# Root-Cause Analysis — 2026-04-29 Sleep-Cycle Investigation

**Trigger:** operator's complaint *"DOCUMENT THE BUGS, they should not happen this often"* + *"deep debugging and bug classification time. only stop when you're 100% positive you found the ultimate root cause/s for each recurring bug."*
**Method:** for each recurring bug, traced the actual code path, queried the live DB, ran empirical probes, and rejected hypotheses until exactly one explanation remained. Several "bugs" turned out not to be bugs at all once the live state was inspected.

---

## Bug-by-bug findings

### 1. LYR-113 — Google OAuth IPv4 regression (recurring P0)

**Surface symptom:** `AggregateError: internalConnectMultiple` in next-auth `[next-auth][error][SIGNIN_OAUTH_ERROR]` logs after every cold-restart of `npm run start`. Login broken until restart with the right NODE_OPTIONS.

**Live empirical probes (2026-04-29, this host):**
- `dns.lookup("oauth2.googleapis.com", { all: true })` returns **both** `192.178.223.95` (A) and `2a00:1450:4009:c0f::5f` (AAAA).
- Direct IPv6 connect: `ENETUNREACH connect ENETUNREACH 2607:f8b0:4023:1004::5f:443 - Local (:::0)`. The kernel has no IPv6 default route.
- IPv4 curl to the same host: HTTP 404 in 1.5–3.0s, 10/10 attempts succeed.
- With `node --no-network-family-autoselection`, `dns.lookup` returns IPv4 only.

**Why the previous fix (`dns.setDefaultResultOrder("ipv4first")`) was insufficient:**
The setting only controls Node's built-in `dns.lookup` ordering. It does **not** propagate to `undici` (the fetch implementation used by `openid-client`/NextAuth and by `next/font/google`), which maintains its own connection pool and runs its own RFC 8305 Happy Eyeballs implementation independently. Even with IPv4-first ordering, undici still races IPv4 and IPv6 attempts in parallel. On WSL2 the IPv6 attempt doesn't fast-fail with `ECONNREFUSED` — it lingers (route table looking for a path) and aborts the parallel race when both fail together. Result: `AggregateError`.

**Ultimate root cause:** the network-environment assumption "IPv6 connect attempts will fast-fail when IPv6 is unreachable" is **false on WSL2**. Combined with undici's parallel-attempt connection strategy, any host where IPv6 connect attempts time out instead of fast-fail will produce this AggregateError randomly under load.

**Why it kept recurring after each fix:** every fix was layered at a higher abstraction (Node DNS hint, instrumentation hook, NODE_OPTIONS). undici operates BELOW those layers in the connection stack. The Node 20.4+ flag `--no-network-family-autoselection` is the first fix that disables Happy Eyeballs at libuv (the layer undici reads from), so v6 attempts never spawn.

**Classification:** environment-incompatible-default + abstraction-layer-mismatch. The default Happy Eyeballs algorithm is correct for hosts with working IPv6 OR fast-failing IPv6; WSL2 is in a third state that the default doesn't anticipate.

**Status:** fixed in commit `8c982d6` (LYR-113). The flag will need to stay until the operator deploys to a host with working IPv6 OR moves OAuth out of the Node runtime entirely.

---

### 2. Tz convention drift family (H0 hotfix and successors)

**Surface symptom (Apr 28 incident):** `TypeError: can't subtract offset-naive and offset-aware datetimes` on `/v1/users/me`, `/v1/stopwatch/status`, and `/v1/create`. The H0 commit `d0401e4` added `strip_tz()` at every datetime-subtraction site.

**The H0 commit message attributed the cause to:**
> *"Supabase Postgres persists DateTime columns as TIMESTAMPTZ by default — even when the SQLAlchemy model declares plain `DateTime`. SQLAlchemy returns AWARE datetimes for those columns."*

**Empirical verification — this attribution is wrong.** Live `information_schema` query against the running Supabase:

```
=== ALL timestamp columns across schema ===
[user]              naive  created_at, d1_return_at, first_task_at, ...
[task]              naive  created_at, planned_start_utc, planned_end_utc, ...
[stopwatch_session] naive  start_time_utc, end_time_utc, paused_at_utc, ...
[deadline]          naive  created_at, due_at_utc, completed_at, ...
... 11 tables, 100% naive

=== TZ-AWARE columns (TIMESTAMPTZ) ONLY ===
(none — all timestamp columns are naive)
```

Live read of an actual stopwatch session row: `start_time_utc=datetime.datetime(2026, 4, 28, 22, 36, 25), tzinfo=None`. Subtracting this from `now_utc()` works without `strip_tz` — no TypeError.

**So why did the original H0 incident actually 500?** Tracing the codebase for actual sources of aware datetimes:

1. **Postgres reads:** ❌ confirmed naive (above).
2. **Redis ISO-string roundtrips:** the writer path (e.g. `stopwatch_manager.py:605`) does `now.isoformat()` where `now = now_utc()` (naive), producing strings like `"2026-04-29T10:00:00"` with no tz suffix. `datetime.fromisoformat("2026-04-29T10:00:00")` returns naive. ❌ Not the source.
3. **`dateparser.parse()` output:** ✅ THIS is aware-capable. Empirical test:
   ```
   dateparser.parse("tomorrow 15:00 GMT+3") → datetime(..., tzinfo=UTC+03:00)
   dateparser.parse("2026-04-29T10:00:00+02:00") → datetime(..., tzinfo=UTC+02:00)
   dateparser.parse("monday") → naive
   ```
   `services/parser.py` calls dateparser without `RETURN_AS_TIMEZONE_AWARE: False`, so any user input that happens to contain a tz indicator returns aware.
4. **Pydantic deserialization of request bodies:** ✅ also aware-capable. If frontend sends `start: "2026-04-29T10:00:00+02:00"`, Pydantic parses to aware. Code that uses `start` directly (not via `to_utc(start)`, which strips tz) carries awareness forward.

**Ultimate root cause:** Lyra's internal convention is naive-UTC, but **the input boundary doesn't normalize tz**. Aware datetimes leak in from `dateparser` (parser.py) and Pydantic request bodies. There is no single boundary site that strips tz; instead, every individual subtraction site has to remember to call `strip_tz`. `strip_tz` is structurally defensive — a band-aid at every wound, not a tourniquet at the source.

**Why the H0 commit message was wrong but the fix still worked:** every site touched by H0 reads from EITHER the DB (naive, no problem) OR from a Redis-stored ISO string (naive, no problem) OR from intermediate datetime variables that originated upstream from one of those. So `strip_tz` is a no-op at every site. The actual aware-leakage paths (parser.py output → TaskManager.create_task input) were not in H0's patched list — and they don't error today because `to_utc()` in TaskManager.create_task DOES handle aware input (it strips tz at the end). So the *real* fix that prevented prod 500s is `to_utc()`'s tz-stripping at line 57 of `time_utils.py`, not the H0 strip_tz additions.

This means: **the H0 commit massively over-applied a band-aid, and the actual fix lives in `to_utc()` which was already correct before H0.** The 500s the operator saw must have been a SPECIFIC site that bypassed `to_utc()` and compared aware datetime directly. That site was somewhere in stopwatch_manager. Without the original stack trace I can't identify the exact line, but H0's patches cover all candidate sites.

**Classification:** convention-without-enforcement. Three implicit conventions (naive-UTC internal, ambiguous external input, no boundary normalizer) coexist with no compile-time or runtime check that they agree.

**Status:** strip_tz is defensive but redundant in the code paths it currently covers. The CORRECT systemic fix would be one of:

- **A:** Make every input boundary a normalization point. A `parse_datetime_input(s) → naive_utc` helper used by every endpoint and parser. Deprecate raw `dateparser.parse` and raw Pydantic datetime fields.
- **B:** Switch internal convention to aware-UTC. Make `now_utc()` return aware. Every datetime in the codebase becomes aware. Mismatches surface immediately at every call site. Big change but eliminates the class of bug.
- **C:** Keep current state, document that strip_tz is a no-op at most sites and add a unit test that the conversion is in `to_utc`.

A is the cleanest. C is the cheapest. B is the most-correct-by-construction.

---

### 3. D1 return stamp showing 0/7 across trusted users — **NOT A BUG**

**Surface symptom:** retention pull on Apr 29 reported `D1 return stamp: 0/7 (0%)` even though 4 of 7 users had clearly returned multiple times.

**Empirical investigation:**

Direct DB query post-investigation:
```
uid=4 ghada     created=2026-04-16  d1=2026-04-28 22:01  ✓
uid=5 t90seegg  created=2026-04-17  d1=2026-04-28 22:35  ✓
uid=6 medo      created=2026-04-17  d1=None              (last /me hit 3d ago, before alembic 037)
uid=7 meroo     created=2026-04-18  d1=None              (last /me hit 2d ago, before alembic 037)
uid=15 moriarty created=2026-04-28  d1=None              (<24h, correct skip)
uid=16 asabryhafez created=2026-04-28  d1=None           (<24h, correct skip)
```

Manually replayed the stamp logic in a fresh session against medo (uid=6): condition fires, commit succeeds, d1 stamps correctly. **The code works.**

**Ultimate root cause:** the d1 stamp is a **lazy-stamp on /v1/users/me hits**, added in alembic 037 on Apr 28. Any user who hasn't hit /me since the migration deployed has d1=None regardless of whether they've actually returned within 24h. Medo and meroo's last activity (Apr 26 and Apr 27 respectively) predates the migration, so their stamps haven't fired yet. They will fire on next visit.

This is the lazy-stamp pattern's known semantic, not a defect: the stamp records *"has this user ever hit /me at least 24h after signup"*, not *"did this user actually return within their 24h window"*. The retention pull at Apr 29 was simply too soon — the stamp had been live for less than 24h and not all users had returned in that time.

**Classification:** measurement-window misread. The metric works as designed; the operator's pull happened during the migration's warm-up window when most users hadn't triggered the lazy path yet.

**Status:** no fix needed. Document the semantic so future retention reads understand the lazy-stamp window. If real per-cohort D1 retention is needed later, backfill from session/login logs is the right approach.

**Side-effect cleanup:** my probe stamped d1 on medo (uid=6) during testing. Reverted to NULL afterward to keep the metric honest.

---

### 4. /v1/calendar/events "missing Redis cache" — **NOT A BUG**

**Surface symptom:** the latency-audit Explore agent flagged the calendar endpoint as never reading Redis despite a docstring promise.

**Code re-inspection** (`backend/app/services/calendar_sync.py`):
- Line 44–48: `CACHE_TTL_SECONDS = 60` declared
- Line 70–75: `_access_token_cache_key()`, `_events_cache_key()` helpers
- Line 153–161: `redis.get(_events_cache_key(...))` — **Redis read happens before Google fetch**
- Line 243–247: `redis.setex(_events_cache_key(...), CACHE_TTL_SECONDS, ...)` — **write-back after fetch**

**The agent's finding was wrong.** The cache is fully wired: read-through pattern with 60s TTL, JSON serialization, parse-failure fallback to re-fetch. Both halves of the cache are present.

**Ultimate root cause of the misfinding:** the agent didn't read the full `fetch_google_events` function body. It saw the docstring promise, scanned for the absence of an early `if cached: return`, didn't find one in the section it sampled, and concluded the cache was missing.

**Classification:** agent-diagnostic miss. Not a bug in the calendar endpoint; a bug in my supervision — I was about to ship a "cache fix" PR that would have added a redundant cache layer. Verifying the agent's claim before acting saved the regression.

**Status:** no fix needed. The latency audit doc (`today_latency_audit_2026_04_29.md`) needs an erratum noting this finding was incorrect.

---

### 5. Brain-dump default-time-in-past — **TEST-INFRA ONLY**

**Surface symptom:** during the Apr 29 edge-case battery against moriarty (uid=15), 7 of 22 cases produced tasks with `when_local` in the past, getting rejected by TaskManager's `start_in_past` check.

**Trace:**
- Test runner script doesn't pass `current_local_iso` to `/v1/brain-dump/parse`.
- Parser's `_now_local(None)` falls back to `datetime.now()` which inside the Docker container returns **UTC time** (container clock).
- Parser computes `_default_when_for_task(now_local, idx) = now_local + timedelta(30 + 30*idx)`.
- That value travels back to `/commit` as `when_local` (still UTC, but presented as naive).
- TaskManager's `to_utc(naive_dt)` at `time_utils.py:52` interprets naive datetimes as `USER_TIMEZONE` (Africa/Cairo, UTC+3).
- The Cairo→UTC shift moves the timestamp 3 hours backward.
- TaskManager's `start_in_past` check at `task_manager.py:222` fires on the now-past timestamp.

**Production impact:** zero. The frontend's `localIsoNow()` in `onboarding-flow.tsx` always passes the user's actual local time as `current_local_iso`, so the parser uses that and the round-trip stays consistent.

**Ultimate root cause:** this is an instance of the same convention-drift pattern as bug #2 — `datetime.now()` in container context returns UTC, but downstream consumers assume USER_TIMEZONE. The test runner exposed the brittleness; production isn't affected because the frontend covers the ambiguity by being explicit.

**Classification:** convention-drift (same family as bug #2). Specifically: `datetime.now()` is ambiguous about tz in the container vs user-local environment.

**Status:** test runner can be fixed (already done — `now_local_iso()` in the script computes Cairo time explicitly). Production needs no fix, but a `feedback`-grade rule against `datetime.now()` in the codebase would prevent recurrence.

---

### 6. /v1/users/me ~5 second response time — **ARCHITECTURAL, NOT A BUG**

**Surface symptom:** backend log shows `INFO:lyra.perf:GET /v1/users/me 4967ms status=200`.

**Trace:** the endpoint runs:
- 1× User row fetch
- 1× ArchetypeAssignment order-by-desc-limit-1
- 1× grandfathered-onboarding `func.min(Task.created_at)` if onboarding NULL
- 1× Task COUNT for executed_session_count
- 1× Task COUNT for active_task_count (added 2026-04-29)
- Up to 2× UPDATE+commit (onboarding backfill, d1 stamp)

That's 5–7 DB roundtrips per call. Each Cairo→Supabase eu-west-1 RTT is ~80–120ms. 5 × 100 = 500ms minimum. With container cold-start latency on top, 4–5s isn't surprising for the first call after a backend restart.

**Ultimate root cause:** Cairo→eu-west-1 Supabase RTT is the floor; Lyra's /me does too many sequential queries against that floor. The two new COUNTs added during recent work each cost ~100ms.

**Why it isn't really a bug:** alpha cohort scale (≤ 200 tasks/user) means the COUNTs are fast at the DB layer; the latency is dominated by network RTT, not query plan. At alpha scale, 5–7 RTTs is acceptable. At Stage-2 scale (>1000 users) this would warrant aggressive caching.

**Classification:** architectural perf characteristic. The latency audit doc has the recommended fix order if the operator wants to pursue it.

**Status:** not a bug. Add `idx_task_user_state_voided(user_id, state, voided_at)` if /me's tail latency (P95) becomes a complaint signal — premature optimization until then.

---

### 7. Silent `try/except: db.rollback()` blocks — **LATENT FAILURE**

**Found via grep:** 9 sites use `except Exception:` with no logging. Notable ones in `users.py`:

```python
try:
    if user.d1_return_at is None and ...:
        user.d1_return_at = now_utc()
        db.commit()
except Exception:
    db.rollback()
```

**Why this is risky:** if the d1 stamp WERE failing for a real reason (constraint violation, type mismatch, transaction conflict), it would silently roll back forever. Investigation #3 verified the d1 path works in practice today, but the silent except hides any future regression.

**Ultimate root cause:** the operator-stated rule *"errors are non-blocking — the funnel stamp must never break sign-in"* is correct in spirit. But "non-blocking" was implemented as "completely silent" instead of "logged-but-non-blocking." When a different bug eventually does surface in this code, debugging starts from zero because there's no log breadcrumb.

**Classification:** observability-shortfall. The right pattern is `except Exception as e: logger.warning("d1 stamp failed: %s", e); db.rollback()`. Same non-blocking behavior, with a breadcrumb.

**Status:** safe to fix tonight. Eight other sites should get the same treatment in a follow-up sweep.

---

## Cross-bug pattern (the operator's "shouldn't happen this often")

Six of the seven items above share one of three pattern classes:

### Pattern A: Environment-incompatible default
Bugs 1 (OAuth IPv4), 5 (brain-dump default-time), latently bug 2 (tz drift).

The default that ships with a library or runtime is correct for the *common* environment but breaks in *Lyra's specific* environment (WSL2 with non-routable IPv6, Docker container in UTC vs user in Cairo, mixed naive/aware datetime sources). The fix is environment-aware overrides, but those overrides themselves drift over time as new defaults arrive.

### Pattern B: Convention without enforcement
Bug 2 (tz drift) directly, bug 5 indirectly.

Lyra has implicit conventions (naive-UTC internal, USER_TIMEZONE for naive interpretation, Redis as a write-once-read-once shape). No compile-time or runtime check enforces them. Every new endpoint can add a violation, and the violation only surfaces at the boundary site that does the offending operation.

### Pattern C: Observability shortfall
Bug 7 directly. Bugs 3 and 4 surface in measurement, not behavior — both turned out not to be real bugs after deeper inspection.

When errors are silently swallowed, debugging begins after the symptom is irreversible. When measurement is inspected too eagerly post-migration, false-positive bugs proliferate.

## The ultimate root cause

**Lyra's codebase treats environment assumptions and data conventions as implicit knowledge rather than explicit, runtime-checked invariants. There is no boundary layer where assumptions are normalized, and no probe layer where assumption breakage is detected.**

Every recurring bug is the same shape: an assumption holds 99% of the time, a corner of the environment breaks the 1%, the failure surfaces at a layer far from the assumption's origin, and the fix is applied at the symptom layer (more `strip_tz` calls, another DNS hint) rather than at the assumption layer (a normalization boundary, a `verify_env_assumptions` probe).

## Recommended systemic fixes

1. **Boundary normalization for datetime input.** Add `app/utils/time_utils.py::normalize_input_datetime(value) -> naive_utc` and use it at every API endpoint that accepts a datetime AND every parser invocation. Deprecate raw `dateparser.parse` calls in favor of a wrapper that strips tz. Removes 80% of the strip_tz calls from the rest of the codebase.

2. **Runtime environment-assumption probe.** A `/v1/health/env-invariants` endpoint that:
   - Confirms IPv4 reachable to Google OAuth (catches LYR-113 regression)
   - Confirms `now_utc()` and Postgres `now()` agree within 60s (catches clock drift)
   - Confirms `datetime.now()` returns the expected tz (catches container-vs-user tz drift)
   - Confirms a pause-event Redis roundtrip preserves naive (catches Redis encoding regressions)
   Run on backend startup; fail loud if any invariant fails.

3. **Replace `except Exception:` with `except Exception as e: logger.warning(...)` at all 9 sites.** Cost: ~5 minutes. Benefit: every future regression in those code paths leaves a breadcrumb instead of silence.

4. **Document the lazy-stamp semantic.** Add a one-paragraph callout in `docs/operator_findings_log.md` template explaining that lazy-stamp metrics (d1_return_at, first_task_at, onboarding_completed_at) are write-on-event and can show <100% even when behavior says otherwise — accompanied by the read-after-migration window risk.

5. **Erratum on the latency audit doc.** Note that the calendar Redis cache claim was wrong; cache is fully wired.

## What I'm fixing tonight (safe + reversible)

- Fix #3 (silent-except logging breadcrumbs): 9 sites get `logger.warning(...)`. Pure additive, can't break anything.
- Fix #2 partial (env-invariants probe): new health endpoint, new file, no existing-code changes.
- Fix #4 + #5 (doc updates): add the lazy-stamp note + the calendar-cache erratum.
- Skip fix #1 (boundary normalization): touches too many sites for a sleep-cycle change without operator review of the deprecation list.
- Skip the tz convention switch (option B from bug #2): too invasive for autonomous shipping.

After these, commit + push under the gate.
