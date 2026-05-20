# Lyra Secretary — Unified Pre-Launch Audit Script

**Purpose:** a single re-runnable sweep covering safety + alignment + operational + cross-cutting concerns. Combines the two prompts the operator ran on 2026-04-30 (safety + alignment) plus the gaps both missed.

**When to run:**
- Before every external-cohort expansion (trusted-user → wider alpha → public)
- After any sprint touching schema, endpoints, scheduler, or state machine
- Quarterly as a baseline regression check
- After any production incident (post-mortem hook)

**How to run:**
- Spawn 3 parallel Explore agents using the briefings in §15 below
- Each agent covers a distinct section cluster
- Synthesize findings into `docs/audits/audit_YYYY-MM-DD.md` using the §16 output template
- Operator reviews; P0 findings block the next ship until fixed

**How to update:**
- After each major ship, append new surfaces / endpoints / VTs to the relevant section's checklist
- See §17 "What to update per ship" cheatsheet at the bottom

**Operating rules:**
1. **Code wins** when docs disagree, EXCEPT manifesto research-integrity rules (then code is the bug).
2. **REPORT ONLY by default** — operator decides which findings to fix and in what order.
3. **Halt-for-review on P0** — multi-tenant data leak, research-integrity violation, broken state machine, broken SKILL.md three-way sync.
4. **Cite file:line both sides** — every finding references both the doc claim and the code reality.

---

## §1 — Schema alignment

**Goal:** every documented table/column matches actual Alembic migrations + SQLAlchemy models.

**Checklist:**
- [ ] List every `CREATE TABLE` from `backend/alembic/versions/*.py`
- [ ] Cross-reference against `__tablename__` in `backend/app/db/models.py`
- [ ] Compare against `agent bootstrap doc` "Database schema (N tables)" section
- [ ] Verify column-level: nullable vs NOT NULL, enum values, FK on-delete behavior, index claims
- [ ] Verify `external_source` field exists on every table that imports external data (template: `external_event_outcome`, `deadline` post-alembic-041)
- [ ] H2 queries (Rules 14–16) default to `WHERE external_source IS NULL` — verify per query
- [ ] VT-17 schema: `pause_event` + `pause_prediction_log` columns match manifesto spec
- [ ] Rule 13 schema: `archetype_assignment` columns support shrinkage blend formula

**Output table:**

| Table | In code | In agent bootstrap doc | In project_history | In building_phases | Status |
|---|---|---|---|---|---|

**Quick commands:**
```bash
ls backend/alembic/versions/*.py | wc -l                       # migration count
grep -h "^class.*Base" backend/app/db/models.py | wc -l        # model count
grep -h "__tablename__" backend/app/db/models.py | wc -l       # table count
```

---

## §2 — Endpoint alignment

**Goal:** every FastAPI route is documented in exactly one canonical place with correct contract.

**Checklist:**
- [ ] Enumerate every route in `backend/app/api/v1/endpoints/*.py`
- [ ] Compare against `openclaw/skills/lyra-secretary/SKILL.md`
- [ ] Compare against `agent bootstrap doc` endpoint mentions
- [ ] Compare against `README.md` endpoint counts
- [ ] Frontend cross-check: every endpoint in `frontend/lib/**` exists in backend; every backend endpoint has a caller (frontend OR OpenClaw OR scheduler-internal)
- [ ] X-Idempotency-Key header coverage on every mutation
- [ ] Per-user ownership check on every endpoint accepting an ID
- [ ] **5xx exception leak audit:** `grep -rn "status_code=500, detail=str(e)" backend/app/api/` — must return 0
- [ ] Deprecated endpoints (e.g. `POST /v1/parse`) flagged consistently across SKILL.md + agent bootstrap doc

**Output table (CSV-shaped):**

| method | path | in_skillmd | in_bootstrap_doc | in_readme | frontend_callers | openclaw_callers | scheduler_only | ownership_check | leaks_5xx | status |
|---|---|---|---|---|---|---|---|---|---|---|

**Quick commands:**
```bash
grep -rn "@router\." backend/app/api/v1/endpoints/ | wc -l           # route count
grep -rn "status_code=500, detail=str(e)" backend/app/api/           # leak count (target: 0)
grep -rn "X-Idempotency-Key\|x-idempotency-key" backend/             # idempotency coverage
```

---

## §3 — Background job alignment

**Goal:** APScheduler job count + cadence + scoping + misfire grace match docs.

**Checklist:**
- [ ] Read `backend/app/workers/scheduler.py` — enumerate every `add_job` call
- [ ] Verify count matches agent bootstrap doc "N background jobs"
- [ ] Verify CI gate `tests/test_state_consistency.py:test_apscheduler_job_count` asserts the right count
- [ ] Per-job: trigger interval matches doc, per-user scoping correct, misfire grace configured
- [ ] **Misfire grace:** `BackgroundScheduler(job_defaults={"misfire_grace_time": ...})` — non-default required for laptop-sleep recovery
- [ ] Each job is internally idempotent (safe to replay on wake)

**Output table:**

| job_name | function | interval_in_code | interval_in_bootstrap_doc | per_user_scoped | ci_gate_asserts | misfire_grace | idempotent |
|---|---|---|---|---|---|---|---|

**Quick commands:**
```bash
grep -c "scheduler.add_job\|add_job(" backend/app/workers/scheduler.py
grep "misfire_grace_time" backend/app/workers/scheduler.py
```

---

## §4 — State machine alignment

**Goal:** documented state machine matches `services/state_machine.py` exactly.

**Checklist:**
- [ ] Extract transition table from `services/state_machine.py`
- [ ] Compare against agent bootstrap doc, README.md, SKILL.md, and any diagram in `docs/diagrams/`
- [ ] Verify terminal-state immutability — every code path that mutates a task rejects EXECUTED, SKIPPED, DELETED
- [ ] **Single Mutation Authority:** `grep -rn "task.state =\|task.state=\|Task.state =" backend/app/ | grep -v "task_manager.py"` — must return 0 outside the manager
- [ ] Early-stop gate (<50% planned duration) wired end-to-end (frontend → endpoint → service)
- [ ] Voided_at handling: voided rows excluded by every Task query/mutation by default

**Output transition matrix:**

| from \ to | PLANNED | EXECUTING | PAUSED | EXECUTED | SKIPPED | DELETED |
|---|---|---|---|---|---|---|
| PLANNED | — | ✓ | — | — | ✓ | ✓ |
| EXECUTING | — | — | ✓ | ✓ | ✓ | — |
| PAUSED | — | ✓ | — | ✓ | ✓ | — |
| EXECUTED | — | — | — | — | — | — |
| SKIPPED | — | — | — | — | — | ✓ |
| DELETED | — | — | — | — | — | — |

(fill from code, mark mismatches with docs)

---

## §5 — Multi-tenant isolation

**P0 SECTION.** Halt-for-review on any finding.

**Checklist:**
- [ ] Redis key namespace: every `redis.set/get/delete/lpush/hset` includes user_id
- [ ] Database queries: every `db.query(Model)` (where Model has user_id) is auto-scoped via `before_compile` hook OR has explicit `.filter(Model.user_id == ...)`
- [ ] Raw SQL via `db.execute(text(...))` bypasses auto-scoping — every raw-SQL site explicitly parameterizes user_id
- [ ] JWT subject: every endpoint uses `Depends(get_current_user)` or equivalent
- [ ] Cross-user research aggregation: every analytics SQL grouping across users uses `GROUP BY user_id`
- [ ] Background jobs: each iterates users explicitly (`for_each_user` helper) — no global queries
- [ ] Frontend persisted cache: localStorage cleared on every signOut path (explicit + auto-401 + session expiry)
- [ ] Test: `tests/test_multiuser_isolation_adversarial.py` covers cross-user attempts; verify count grows with new endpoints

**Quick commands:**
```bash
grep -rn "db.execute(text" backend/app/                              # raw SQL sites
grep -rn "redis\.\(set\|get\|delete\|lpush\|hset\)" backend/app/    # Redis writes
grep -rn "db.query(Task)\|db.query(StopwatchSession)" backend/app/  # task queries
```

---

## §6 — Research integrity

**P0 SECTION.** Halt-for-review on any finding.

**Checklist:**
- [ ] **External-source isolation (VT-29):** every research query reading `task` OR `deadline` includes `WHERE external_source IS NULL` UNLESS opt-in `?include_external=true`
- [ ] VT pre-registration vs implementation table:

| VT # | Hypothesis | Metric | Captured? | Analysis path | Kill criterion checkable? | Status |
|---|---|---|---|---|---|---|

- [ ] Manifesto rules in code:
  - Rule 11 (no-nudge control days): toggle exists, assignment logged
  - Rule 12 (scope-inflation mediation): scope_density column exists, mediation test pre-registered
  - Rule 13 (shrinkage blend, Kish correction, winsorization): formula matches `bias_factor_service.py`
  - Rule 14–16 (deadline distance hypothesis): query filter on external_source verified
  - Rule 17 (label-reinforcement, sqrt(N) damping, display floor): in code
  - Rule 18 (deadline contamination of H1 — added Apr 22): pre-registration shipped
- [ ] `reflection_view_log` instrumentation: every reflection-surface impression writes a row, view_id returned on /stopwatch/stop, stamped via /reflection_view/{id}/viewed and /dismissed
- [ ] `pause_prediction_log` acceptance windows: reconcile_responses job correctly closes windows; inferred-response logic matches VT-17d permissive-acceptance definition
- [ ] Saturated posterior 99% display cap (`feedback_saturated_posterior_display_cap`) enforced at every surface that shows an archetype %
- [ ] Voiding gameability check: at current alpha N (≤30), manual review of voided_count > 5 per user. Defer rate-limiting until n grows.

**Quick commands:**
```bash
grep -rn "external_source.is_(None)\|external_source IS NULL" backend/app/    # filter sites
grep -rn "VT-\|MANIFESTO Rule" backend/app/                                    # research-rule references in code
```

---

## §6A — May 19, 2026 Telemetry Pre-Flight Ledger

**Generated:** 2026-05-19.
**Target gate:** architecture-freeze review before the next external cohort.
The previous May 21 framing is de-scoped; this is not a rush deadline.
**Status:** implementation gaps found against the research-governance contract.
This ledger is the patch pipeline for the next alpha gate; keep it separate
from the reusable checklist above so future audits can compare dated code
reality against this snapshot.

### Primary Discrepancy Matrix

| Vector / requirement | Implemented status | Codebase location | Risk level | Immediate action |
| --- | --- | --- | --- | --- |
| Cortex sign isolation | Partially isolated | `backend/app/services/cortex.py`; `backend/app/db/models.py` | Medium | Keep `active_delta_minutes = executed - planned` isolated from legacy `duration_delta_minutes = planned - executed`; audit new analytics loops for token mixups. |
| Substrate Kill timeline | Qualitative only | `MANIFESTO.md` Substrate Kill Criterion | Low | Pre-register the clean-session floor and evaluation window before the next research readout. |
| OpenClaw automated voiding | Verified | `backend/app/api/v1/endpoints/tasks.py`; `openclaw/skills/lyra-secretary/SKILL.md` | Zero | No action; system-error/test traces have a void path. |
| `is_anchor` time stripping | Implemented in current patch | `backend/alembic/versions/053_task_anchor_and_rct_arm.py`; `backend/app/db/models.py`; `backend/app/services/bias_factor_service.py`; `backend/app/services/cortex.py`; `backend/app/services/output_surfaces.py` | High / P0 for clean calibration | Keep anchors in descriptive history, but exclude them from clean bias-factor / measured-execution calibration. |
| Rule 11 nudge suppression | Implemented in current patch | `backend/app/services/output_surfaces.py`; `backend/app/api/v1/endpoints/stopwatch.py`; `backend/app/api/v1/endpoints/analytics.py` | High | Deterministic post-baseline 1-in-7 suppression now records `rule11_no_nudge` vs `rule11_active`; keep analysis claims gated on enough paired days. |
| VT-12a readiness-duration metric | Not implemented | Backend metric absent; notebook/readout only | Low | Keep as post-aggregation notebook analysis until it becomes product-critical. |
| Soft-warning RCT arming | Arm stamp implemented in current patch; warning UI still inactive | `backend/alembic/versions/053_task_anchor_and_rct_arm.py`; `backend/app/services/task_manager.py` | High / P0 for Rule 16 | Keep deterministic `(user_id mod 2)` arm stamped on task creation; only analyze when the warning surface is live. |
| Winsorization isolation | Verified | `backend/app/services/archetype_proximity_service.py` | Zero | No action; raw ledger durations remain unmutated. |

### Architecture-Freeze Hard Gates

1. [x] Add `Task.is_anchor` with migration backfill for obvious prayer/sleep rows.
2. [x] Exclude `is_anchor = true` from `bias_factor_service.blend()`, direct
   `_adaptive_calibration()` consumers, Cortex measured-execution queries, and
   clean output-surface candidates.
3. [x] Add deterministic RCT arm stamping at task creation using `user_id % 2`.
4. [x] Surface the new fields in task read APIs so audits can inspect them.
5. [x] Add contract tests for anchor exclusion and RCT arm determinism in
   `backend/tests/test_task_anchor_and_rct_arm.py`.
6. [x] Add Rule 11 deterministic no-nudge suppression for
   `stopwatch.micro_mirror`, `stopwatch.calibration_nudge`,
   `task.creation_nudge`, and `analytics.insights`.

### Deferred, But Still Required Before Claims

- VT-12a stays a notebook/crosswalk calculation until alpha data volume is
  large enough to justify a backend endpoint.
- Substrate Kill Criterion needs a concrete `n` and timeline. Suggested floor:
  do not run the kill readout below `n >= 100` clean, non-anchor, non-voided,
  non-auto-closed execution sessions across the evaluation cohort.

### VT-26 Semantic Prior Trap

`CategoryMapping` is currently a keyword-to-category mapper. It does not know
whether "study" means light review, deep problem-solving, lecture catch-up, or
exam rehearsal. Until task operational type exists, shrinkage priors can
over-allocate early users based on category semantics alone. Do not interpret
early prior behavior as evidence of user execution style without enough clean
personal rows.

### Parser / NIM Guardrail

Structured local-inference parsing must strip reasoning wrappers before JSON
parsing and should prefer hard JSON-mode or zero-temperature settings where
available. Raw schema endpoints must reject contaminated payloads instead of
silently coercing malformed model output into task facts.

---

## §7 — Bug tracker alignment

**Checklist:**
- [ ] Read `LYRA_BUGS.md`, extract every LYR-### with current status
- [ ] For each "fixed" entry, verify the fix exists in code (grep for the symptom or the fix's specific change)
- [ ] Reverse direction: `git log | grep -oE "LYR-[0-9]+"` — every referenced bug must be in the doc
- [ ] LYR numbering ceiling: dense or sparse?

**Output table:**

| lyr_id | status_in_doc | status_in_code | last_relevant_commit | status |
|---|---|---|---|---|

---

## §8 — Doc count alignment

**Checklist (re-derive every numeric claim from code):**
- [ ] agent bootstrap doc "N tables" — count Alembic CREATE TABLEs
- [ ] agent bootstrap doc / README.md "N endpoints" — count `@router.` decorators
- [ ] agent bootstrap doc "N background jobs" — count `add_job` calls
- [ ] State machine "N transitions" — count cells in `state_machine.py` map
- [ ] LYRA_BUGS.md open/fixed counts
- [ ] `wc -l openclaw/skills/lyra-secretary/SKILL.md` ≤ 150 (per agent bootstrap doc hard rule)
- [ ] **SKILL.md three-way sync diff:**
  ```bash
  diff openclaw/skills/lyra-secretary/SKILL.md /mnt/c/Users/alina/openclaw/skills/lyra-secretary/SKILL.md
  docker exec openclaw-openclaw-gateway-1 cat /home/node/.openclaw/skills/lyra-secretary/SKILL.md | diff - openclaw/skills/lyra-secretary/SKILL.md
  ```
  Any diff is P0.
- [ ] Archived docs: every `archive/*.md` has a banner pointing to its successor; no living doc links to archived as canonical

**Output table:**

| claim | location | doc_value | code_value | status |
|---|---|---|---|---|

---

## §9 — Configuration alignment

**Checklist:**
- [ ] `.env.example` lists every variable
- [ ] Every `os.getenv` / `os.environ.get` / Pydantic `BaseSettings` field is in `.env.example` OR has a documented default
- [ ] agent bootstrap doc "Required vars" list current: `DATABASE_URL`, `REDIS_URL`, `NOTION_API_KEY`, `NOTION_DATABASE_ID`, `USER_TIMEZONE`, `SECRET_KEY` ≥ 32 chars
- [ ] Supabase pooler details (port 6543, sslmode=require, eu-west-1) match `deployment_architecture.md`
- [ ] SQLite fallback file (`.env.backup-sqlite-2026-04-16`) still exists; schema parity with current Postgres state

**Output table:**

| var_name | in_env_example | in_bootstrap_doc | in_code | required | default | status |
|---|---|---|---|---|---|---|

---

## §10 — Frontend integration alignment

**Checklist:**
- [ ] `frontend/lib/integrations.ts` registry: every entry has (a) backend OAuth callback at `frontend/app/api/integrations/<provider>/callback/route.ts`, (b) entry in backend `GET /v1/integrations` response, (c) row in Settings → Integrations UI
- [ ] **Incremental OAuth:** NextAuth sign-in requests ONLY `openid email profile` (no sensitive scopes). Sensitive scope in sign-in = P0 (breaks signup).
  ```bash
  grep -rn "scope" frontend/lib/auth.ts frontend/app/api/auth/                  # check NextAuth config
  ```
- [ ] Cloudflare Tunnel serves `npm run start` (production build), NOT `npm run dev`. Apr 25 incident proves this can regress silently.
  ```bash
  ps -ef | grep "next start\|next dev"                                          # current process
  ```

---

## §11 — Behavioral safety (added in unified script)

**Goal:** every user-facing surface scanned for harm potential — judgment-feeling copy, premature labeling, surveillance perception, dependence creation.

**Checklist:**
- [ ] Read these memories first:
  - `feedback_warm_tone_copy.md` — no research vocabulary in user-visible strings
  - `feedback_label_reinforcement_framing.md` — "reinforcement" not "internalization"
  - `feedback_saturated_posterior_display_cap.md` — clamp at 99%
  - `feedback_progressive_revelation_canon.md` — Type 3 Illusion Preserver routing, not ad-hoc calm-mode
  - `feedback_trust_copy_register.md` — "Still learning" over silence over AI-padding
  - `feedback_dismiss_not_mute.md` — dismiss ≠ punish
- [ ] micro_mirror text: enumerate every branch, flag any judgment language
- [ ] calibration_nudge text: enumerate every branch, flag confidence claims that exceed data
- [ ] Conflict detection messages: informative not blocking
- [ ] Readiness/reflection slider labels: state words (Tired, Low, Steady) not identity words (Drained, Lazy)
- [ ] Pause prediction banner: observational ("you usually") not predictive-feeling ("Lyra knows")
- [ ] Archetype reveal gates: session-≥5 enforced, saturated-posterior cap applied
- [ ] Toast/banner dismissal: doesn't reduce functionality
- [ ] Locked-preview tiles (insights): patient/motivating, not shaming
- [ ] No do_not_add violations slipped in: "Mission" / "Threat Queue" / "Operator Mode" / social cards / sound effects

**Per-surface classification:**
| Surface | File:line | SAFE / CAUTION / RISK | Notes |
|---|---|---|---|

---

## §12 — Operational safety (laptop sleep + recovery)

**Goal:** enumerate every failure mode during a typical operator-laptop sleep cycle + document recovery.

**Checklist:**
- [ ] **APScheduler misfire grace:** `BackgroundScheduler(job_defaults={"misfire_grace_time": 86400, "coalesce": True})` — required for sleep-replay
- [ ] Stale session recovery job runs every 15 min, closes sessions > 12h
- [ ] Orphan task recovery job catches EXECUTING tasks with no open session
- [ ] cloudflared tunnel auto-reconnects on wake (verify with `ps -ef | grep cloudflared`)
- [ ] Docker containers auto-resume from sleep (Redis volume preserved, backend rehydrates)
- [ ] Next.js `next start` survives sleep (or the operator restarts manually — document which)
- [ ] In-flight HTTP requests during tunnel drop: client-side timeout + retry path

**Output: morning recovery checklist for operator:**
```bash
# 1. Backend + Redis up?
docker-compose ps
# Expected: both Up

# 2. Backend health?
curl http://localhost:8000/v1/health/env-invariants
# Expected: {"all_ok": true, ...}

# 3. Stale jobs caught up? (see logs)
docker-compose logs --tail=50 backend | grep -E "stale_session|orphan_task|moodle_ics_sync"

# 4. Frontend running?
curl -o /dev/null -w "%{http_code}" http://localhost:3000/
# Expected: 200

# 5. Tunnel healthy?
curl -o /dev/null -w "%{http_code}" -I https://lyraos.org/
# Expected: 200 or 302

# 6. Last Moodle sync recent?
# (in Supabase SQL editor)
SELECT user_id, moodle_last_synced_at FROM "user"
  WHERE moodle_ics_url IS NOT NULL ORDER BY moodle_last_synced_at DESC LIMIT 5;
# Expected: most recent < 7h ago
```

---

## §13 — Privacy + persistence + credentials

**Checklist:**
- [ ] Credential at-rest storage: every credential-equivalent field (`google_refresh_token`, `moodle_ics_url`, future Notion token) — current trust class documented (plaintext in v1, Fernet Phase 6+)
- [ ] No credential field returned in any API response (`/users/me`, `/integrations`, `/users/me/export`)
- [ ] Account deletion: every user-owned row purged (hard delete) or anonymized (retain-for-research). User row deletion wipes credential columns by virtue of column-on-row.
- [ ] `frontend/lib/clear-persisted-cache.ts` called on:
  - Explicit signOut (sidebar + mobile drawer)
  - Auto-401 sign-out path
  - Session-expiry useEffect
  (verify by grep)
- [ ] React Query persistence key versioned (`lyra-rq-cache:v1`) so a deploy can invalidate everyone's cache
- [ ] GDPR: informed-consent UI surfaces what data is collected in plain language

**Quick commands:**
```bash
grep -rn "clearPersistedCache\(\)" frontend/                # cache-clear sites
grep -rn "google_refresh_token\|moodle_ics_url" backend/app/api/  # leak-via-API check
```

---

## §14 — Cross-cutting gaps (the ones both audits missed)

**Checklist:**
- [ ] **Latency budgets per endpoint** — measure `time_total` for every route, target: SSR < 800ms warm cache, < 2s cold
- [ ] **Accessibility (a11y)** — ARIA labels, keyboard nav, color contrast (WCAG AA at minimum), screen-reader semantics on hero numbers
- [ ] **Frontend bundle size** — `du -sh frontend/.next/static/chunks/` and break down which routes ship the most JS
- [ ] **Test coverage gap map** — `pytest --co -q | wc -l` (test count) + identify surfaces with zero tests
- [ ] **Network resilience** — single API call failure mid-action: does the UI roll back optimistic state cleanly?
- [ ] **Browser console error noise** — open every page with devtools, count uncaught errors / warnings / failed network requests
- [ ] **Onboarding happy-path E2E** — fresh account → consent → brain-dump → first session → reflection. End-to-end without errors?
- [ ] **Logging completeness + signal-to-noise** — every error logged once, no log spam, log-level appropriate
- [ ] **Backup / restore drill** — Supabase backup exists, restore process tested at least once
- [ ] **GDPR consent UI** — what's actually disclosed to the user vs what's actually collected

---

## §15 — Agent briefings for parallel execution

Spawn three Explore agents in one batch using these briefings:

**Agent A — Schema + Endpoints + Jobs + State Machine + Multi-tenant (§§1–5)**
> You are auditing schema/endpoint/job/state-machine/multi-tenant alignment for the Lyra Secretary project at `/mnt/d/Projects/Lyra Secretary v0.1`. Today is YYYY-MM-DD. Read-only investigation; do not modify any file. Cover §§1–5 of `docs/pre_launch_audit_script.md`. Cite file:line for every finding. Halt + surface immediately on any P0 (cross-tenant leak, broken state machine, broken three-way SKILL.md sync).

**Agent B — Research Integrity + Behavioral + Privacy (§§6, 11, 13)**
> You are auditing research integrity, behavioral safety, and privacy/persistence for the Lyra Secretary project at `/mnt/d/Projects/Lyra Secretary v0.1`. Today is YYYY-MM-DD. Read-only. Cover §§6, 11, 13 of `docs/pre_launch_audit_script.md`. Critical context: read `MANIFESTO.md` Rules 1–18, plus the feedback memories listed in §11. Halt + surface immediately on any P0 (research-integrity violation, identity-cementing copy, credential leak in API response).

**Agent C — Operational + Doc-counts + Config + Frontend Integrations + Cross-cutting (§§3 misfire-grace, §§7–10, 12, 14)**
> You are auditing operational, configuration, doc-count, and cross-cutting safety for the Lyra Secretary project at `/mnt/d/Projects/Lyra Secretary v0.1`. Today is YYYY-MM-DD. Read-only. Cover §3 misfire-grace check, §§7–10, §12, §14 of `docs/pre_launch_audit_script.md`. Build the morning recovery checklist using §12's template + the actual current Docker / Cloudflare Tunnel / next-start setup.

---

## §16 — Output template (`docs/audits/audit_YYYY-MM-DD.md`)

```markdown
# Pre-launch audit — YYYY-MM-DD

## Summary
- P0 findings: N
- P1 findings: N
- P2 findings: N
- Sections completed: N/14

## P0 findings (must fix before next ship)
| Title | File:line both sides | Impact | Proposed fix |

## P1 findings (must fix before next external-cohort expansion)
| Title | File:line | Impact | Proposed fix |

## P2 findings (monitor / track)
| Title | File:line | Impact | Monitoring plan |

## Section-by-section deliverables
(Tables from §§1–14 in order)

## Structural recommendations
What systemic changes would prevent the next audit from finding the same issues.

## Sign-off
- [ ] Operator marked each P0 as triaged
- [ ] Sprint plan updated with chosen fixes
- [ ] Audit doc committed to git
```

---

## §17 — What to update per ship (cheatsheet)

| When you ship... | Update this section |
|---|---|
| New Alembic migration | §1 schema (table count, column-level) + §8 doc counts |
| New endpoint | §2 endpoint table + §10 frontend integration check + SKILL.md three-way sync |
| New APScheduler job | §3 jobs table + bump CI gate count + verify misfire grace covers it |
| State machine transition | §4 transition matrix + every doc that references it |
| New credential storage | §13 trust class + leak-via-API grep + account-deletion completeness |
| New behavioral surface (copy / nudge / chip) | §11 per-surface classification + run through the 6 feedback memories |
| New chart / aggregation | §6 research integrity (`external_source IS NULL` filter) + §14 latency budget |
| New manifesto VT or Rule | §6 VT-pre-reg-vs-impl table |
| New integration (Moodle, Notion, etc.) | §10 frontend integration + §13 credential storage + §6 VT contamination check |
| New persistence-layer key | §5 multi-tenant Redis namespace + §13 cache-hygiene |

**Red flags that demand a full audit re-run:**
- Any P0 incident in production (post-mortem hook)
- Adding a non-trivial OAuth provider
- Changing the auto-scoping ContextVar pattern
- Migrating to a new database engine
- Adding the first non-operator-controlled cohort (public signup, paid users)

---

## §18 — What this script intentionally does NOT cover

These are deliberate scope cuts. If they become priorities, add separate sections:

- **Performance benchmarking** — synthetic load tests, profiling. Use a separate perf budget doc.
- **Design quality / aesthetics** — alignment audit ≠ visual review.
- **Code style / refactor opportunities** — that's a separate health check.
- **Cost projections** — Supabase tier, Cloudflare bandwidth, Resend volume. Track in `docs/cost_audit.md` if needed.
- **Vendor lock-in / portability** — separate strategic concern.
- **Marketing / positioning copy** — out of scope.

---

*Maintained: 2026-04-30. Update the version stamp + add a "what changed" note at the top whenever the script itself evolves.*
