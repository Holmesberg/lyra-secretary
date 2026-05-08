# Alignment Audit Prompt — Lyra Secretary

**Purpose:** reconcile every canonical document against actual code state. Find drift, file findings as a punch list, halt before mutating anything.

**Run mode:** read-only investigation. Do not edit code or docs during the audit. Produce a single findings report; the operator decides what to fix and in what order.

**Time budget:** assume one full agent session. Use subagents for parallel surface audits where independent.

---

## 0. Operating rules

1. **Sources of truth, in priority order**, when two sources disagree:
   1. Code (FastAPI routes, Alembic migrations, scheduler registrations, state machine enums, SQLAlchemy models, frontend route handlers).
   2. `docs/manifesto.md` — research-integrity rules (Rules 1-17) and pre-registered VT hypotheses.
   3. `docs/building_phases.md` and `docs/project_history.md` — canonical forward/backward project narrative.
   4. `CLAUDE.md` — operator + agent reference.
   5. `openclaw/skills/lyra-secretary/SKILL.md` — agent-facing endpoint contract.
   6. `README.md` — public-facing summary.
   7. Everything else (parked ideas, dogfood findings, archived specs).

   When code and docs disagree, **the code wins** unless the doc is the manifesto and the discrepancy is research-integrity-relevant — in which case the *code is the bug*, flag it as P0.

2. **Do not fix anything during the audit.** Every finding must be filed; the operator decides batch sequencing. The exception: typos in the agent-facing SKILL.md that would break a tool call MAY be flagged P0 with a proposed one-line fix in the report, but still not applied.

3. **Halt-for-review checkpoints:** after each section below, post a brief progress note. If you discover a P0 finding (research-integrity violation, cross-tenant data leak, broken state machine), halt and surface immediately rather than continuing.

4. **Cite specific lines.** Every finding must reference `file:line` for both sides of the discrepancy. "CLAUDE.md says 10 tables but I count 11" without line refs is not a finding, it's a feeling.

5. **Use the three-way comparison pattern.** For every claim a doc makes about code, locate (a) the doc claim with line ref, (b) the code reality with line ref, (c) any other doc that also makes the claim. A claim that appears in only one doc is "unverified"; a claim that appears in two docs but contradicts code is "drift"; a claim that appears in three docs and contradicts code is "systemic drift" and warrants a structural fix proposal.

---

## 1. Schema alignment

**Goal:** verify `CLAUDE.md` table list, `docs/building_phases.md` schema claims, and any ER diagram in `docs/diagrams/` match actual Alembic migrations and SQLAlchemy models.

**Steps:**

1. List every `CREATE TABLE` from `backend/alembic/versions/*.py`. Build the canonical table list.
2. Cross-reference against `backend/app/db/models.py` (or wherever `__tablename__` is declared) to confirm every migrated table has a model and vice versa.
3. Compare against `CLAUDE.md` "Database schema (N tables)" section.
4. Compare against `docs/building_phases.md` and `docs/project_history.md` schema descriptions.
5. For each table, verify the column list in code matches any schema description in docs. Pay attention to:
   - Nullable vs NOT NULL drift
   - Enum values (`task.status`, `task.category`, `pause_event.reason_code`, etc.) — every enum value mentioned in any doc must exist in code, every code enum value should be documented somewhere
   - Foreign keys (the LYR-103 `external_event_outcome` FK delete-cascade bug is the template — every FK should have an explicit on-delete behavior matching documented user-deletion semantics)
   - Indexes — claimed indexes must exist; missing indexes on documented hot paths are findings

**Specific checks:**

- `CLAUDE.md` claims 10 tables. Verify count.
- `external_event_outcome` is described as the template for external-data isolation. Verify the `external_source` field exists on every table that imports external data (currently `task` per CLAUDE.md), and verify no other table has imported external data without that field.
- `pause_event` and `pause_prediction_log` exist per VT-17 commit messages. Verify the actual columns match the manifesto's VT-17 acceptance-rate analysis spec.
- `archetype` and `archetype_assignment` exist per Alembic 031/032. Verify their column lists support manifesto Rule 13 (shrinkage blend) and Rule 17 (label-reinforcement measurement).

**Deliverable:** a single table:

| Table | In code | In CLAUDE.md | In project_history | In building_phases | Status |
|-------|---------|--------------|--------------------|--------------------| -------|

with one row per table-or-claim, and a column-level findings list for any table flagged "drift".

---

## 2. Endpoint alignment

**Goal:** every FastAPI route is documented in exactly one place (SKILL.md for agent-facing) with correct method, path, required fields, and response shape.

**Steps:**

1. Enumerate every route in `backend/app/api/v1/endpoints/`. Capture (method, path, auth requirement, request fields with required/optional, response fields).
2. Compare against `openclaw/skills/lyra-secretary/SKILL.md`.
3. Compare against `CLAUDE.md` endpoint mentions (e.g., "POST /v1/tasks/swap", "POST /v1/stopwatch/update-completion").
4. Compare against `README.md` endpoint counts ("34 endpoints" per the Apr 17 audit commit).
5. Check the frontend: every endpoint called from `frontend/app/**` and `frontend/lib/**` must exist in the backend; every backend endpoint should either be called from frontend, called from OpenClaw, or be scheduler-internal.

**Specific checks:**

- `POST /v1/parse` is marked deprecated in CLAUDE.md. Verify it still works (still has callers) and that the deprecation note in CLAUDE.md is consistent with whether SKILL.md still lists it.
- The "X-Idempotency-Key" header pattern: every mutation endpoint that should support idempotency must read the header and write to Redis with the documented 30s TTL. Find any mutation endpoint that doesn't.
- `GET /v1/notifications/pending` is OpenClaw-drained per CLAUDE.md. Verify it exists and that the polling cadence matches the documented 30s.
- `POST /v1/notifications/push` is "scheduler-internal" per CLAUDE.md. Verify it has internal-only auth or is unreachable from frontend.
- Per-user scope: every endpoint that takes a `task_id`, `session_id`, or similar must verify ownership against the JWT. The Phase 3.2 / 3.3 cross-tenant leaks (commits 4cf2168, 137353) are the template — find any endpoint that fetches by ID without filtering by `current_user.id`.

**Deliverable:** a CSV-format table of every endpoint with columns: `method, path, in_skillmd, in_claudemd, in_readme, frontend_callers, openclaw_callers, scheduler_only, ownership_check, status`. Status ∈ {`aligned`, `drift`, `undocumented`, `orphan`}.

---

## 3. Background job alignment

**Goal:** APScheduler job count and cadence match every doc that mentions them.

**Steps:**

1. Read `backend/app/workers/scheduler.py` and enumerate every `add_job` call. Capture (job name, function, trigger interval, args, jitter).
2. CLAUDE.md says 8 jobs with specific cadences. Verify each by name and interval.
3. The CI gate ("fix(ci): update APScheduler job count gate from 7 to 8") implies a test asserts the count. Verify it still asserts 8 and that the test enumerates the jobs by name (not just count).
4. For each job, verify the documented behavior:
   - Reminders every 1 min
   - Notion sync retries every 5 min
   - Timer overflow alerts every 2 min
   - Overdue task detection every 30 min
   - Stale session recovery every 15 min, sweeps unclosed sessions older than 12h
   - Orphan task recovery every 15 min, EXECUTING with no open session → SKIPPED
   - VT-17 pause prediction every 1 min per-user (fires + logs + enqueues notification)
   - VT-17 outcome reconciliation every 5 min (closes pause_prediction_log acceptance windows)

5. Verify each job correctly scopes work per-user (post Phase 2a). A job that operates globally without a per-user loop or per-user filter is a P0 multi-tenant bug.

**Deliverable:** a job-by-job table with `name, interval_in_code, interval_in_claudemd, per_user_scoped, ci_gate_asserts, behavior_matches_doc`.

---

## 4. State machine alignment

**Goal:** the documented state machine (`PLANNED → EXECUTING ⇄ PAUSED → EXECUTED`, plus `SKIPPED` and `DELETED` terminals) matches `services/state_machine.py` exactly.

**Steps:**

1. Read `services/state_machine.py`. Extract the transition table.
2. Compare against the diagram in `CLAUDE.md`, `README.md`, `openclaw/skills/lyra-secretary/SKILL.md`, and any diagram in `docs/diagrams/`.
3. Verify terminal-state immutability: find every code path that mutates a task and confirm it rejects mutations on EXECUTED, SKIPPED, DELETED. (The `voided_at` audit commits 1/4 through 4/4 are the template — they did this for voiding; do it for state.)
4. Verify the "Single Mutation Authority" claim: every task write must go through `services/task_manager.py`. Grep for direct `task.status = ` assignments outside `task_manager.py` and any direct `db.add(Task(...))` or `db.commit()` for task changes outside the manager. Each is a finding.
5. Verify the early-stop gate: `services/stopwatch_manager.py` should refuse stop at <50% planned duration without an explicit override. Confirm the override surface exists end-to-end (frontend → endpoint → service).

**Deliverable:** a transition matrix in the report, with each cell marked `allowed (code)`, `allowed (docs)`, `mismatch`, or `not in either`.

---

## 5. Multi-tenant isolation audit

**This is P0.** The Phase 3.2/3.3 cross-tenant leaks were caught in dogfood. Assume more exist.

**Steps:**

1. **Redis key namespace audit:** grep every `redis.set`, `redis.get`, `redis.delete`, `redis.lpush`, `redis.hset` and similar. Every key must include the user_id. Patterns to find:
   - Idempotency keys
   - Undo cache (per-user-scoped per voided_at audit 3/4 — verify)
   - Active stopwatch session
   - Notion failed-sync queue
   - Pause prediction notification queue
   - Any new key introduced since Apr 18

2. **Database query audit:** every `select(Model)` that doesn't filter by `user_id` or by a column that transitively belongs to the user (e.g., `task_id` where the task's `user_id` is checked) is a finding. Pay special attention to:
   - Background job queries
   - Insights/analytics endpoints
   - The `/v1/tasks/last` endpoint (the voided_at audit 3/4 already touched this — verify it stuck)
   - Conflict detector queries (the `voided_at` exclusion was added in commit b7ed2247 — verify the user_id filter is also there)

3. **JWT subject audit:** every endpoint must use `Depends(get_current_user)` or equivalent. Find any endpoint that takes user input but doesn't verify the JWT.

4. **Cross-user bleed in research queries:** the manifesto's H1 / VT-22 / VT-25 analyses MUST scope to a single user when computing per-user metrics. Find any analytics SQL that aggregates across users without explicit `GROUP BY user_id`.

**Deliverable:** a P0 findings list. Each entry is a code location + a specific user-data leak vector.

---

## 6. Research integrity audit

**This is also P0.** The research validity claim is the product's core differentiator.

**Steps:**

1. **External data isolation (manifesto External Data Exclusion Rule):** every research query that reads from `task` must include `WHERE external_source IS NULL`. Grep `analytics/`, `services/insights*`, the operator notebook, and any VT-17 / VT-22 / VT-25 query. Each missing filter is a P0.

2. **VT pre-registration vs implementation:** for each VT (17, 17d, 22, 23, 25 — confirm the full list against the manifesto):
   - The manifesto declares the hypothesis, the metric, the kill criterion, and any pre-registered analysis.
   - Verify the data is being captured (table + column exists, write path fires).
   - Verify the analysis code computes the pre-registered metric (not a substitute).
   - Verify the kill criterion is checkable (data sufficient, threshold defined).

3. **Manifesto rules in code:**
   - Rule 13 (shrinkage blend in `bias_factor_lookup`): verify the formula in code matches the rule. Verify winsorization (commit 4853bfb9) is applied.
   - Rule 17 (label-reinforcement measurement, sqrt(N) damping, display floor): verify in code.
   - Rule 11 (no-nudge control days): verify the toggle exists and the assignment is logged for analysis.
   - All other numbered rules: verify each has at least one corresponding code or test reference.

4. **`reflection_view_log` instrumentation (LYR-098):** verify every reflection-surface impression writes a row, with `view_id` returned on `/stopwatch/stop`, stamped via `/reflection_view/{id}/viewed` and `/dismissed`. Find any impression that fires without logging — that's a contamination of the VT-21 stratified analysis.

5. **`pause_prediction_log` acceptance windows:** verify the reconcile_responses job correctly closes windows. Verify the inferred-response logic matches the pre-registered VT-17d permissive-acceptance definition.

**Deliverable:** a VT-by-VT table: `hypothesis, metric, captured?, analysis_code_path, kill_criterion_checkable?, status`.

---

## 7. Bug status alignment

**Steps:**

1. Read `LYRA_BUGS.md` and extract every LYR-### with its current status (open/fixed/wontfix).
2. For each entry, search the git log for a commit that closes it. Status mismatches are findings.
3. For each "fixed" entry, verify the fix actually exists in the code (grep for the symptom or for the fix's specific change).
4. Reverse direction: search the git log for `LYR-\d+` references in commit messages; every referenced bug must have an entry in `LYRA_BUGS.md`. Untracked LYR numbers are findings.
5. Note the LYR-### numbering ceiling (currently appears to be ~113 per recent commits) and whether numbering is dense or sparse.

**Deliverable:** a status-drift table with `lyr_id, status_in_doc, status_in_code, last_relevant_commit, status`.

---

## 8. Doc surface count audit

**This is the cheapest finding category and should be done last.**

**Steps:**

1. Every numeric claim in CLAUDE.md, README.md, project_history.md, building_phases.md must be re-derived from code. Examples:
   - "10 tables" — count Alembic CREATE TABLEs
   - "34 endpoints" — count FastAPI routes
   - "8 jobs" — count APScheduler add_jobs
   - "5 PAUSED → ... transitions" — count state machine entries
   - Any count of LYRA_BUGS open/fixed
   - Any count in deployment_architecture.md

2. SKILL.md size: per CLAUDE.md, must be ≤150 lines. Verify with `wc -l` and reject if over.

3. Three-way SKILL.md sync: per CLAUDE.md, three locations must match exactly. Diff:
   - `openclaw/skills/lyra-secretary/SKILL.md` (source of truth)
   - `/mnt/c/Users/alina/openclaw/skills/lyra-secretary/SKILL.md` (host)
   - `docker exec openclaw-openclaw-gateway-1 cat /home/node/.openclaw/skills/lyra-secretary/SKILL.md` (container)
   Any diff is a finding.

4. Archived docs: every doc moved to `archive/` should have a banner pointing to its successor. Verify. Also verify no living doc still links to an archived doc as canonical.

**Deliverable:** a count-claims table with `claim, location, doc_value, code_value, status`, plus the SKILL.md three-way diff result.

---

## 9. Configuration alignment

**Steps:**

1. Read `.env.example` and list every variable.
2. Grep every `os.getenv` / `os.environ.get` / Pydantic `BaseSettings` field in the codebase. Each must be in `.env.example` (or be optional with a documented default).
3. Verify CLAUDE.md's "Required vars" list is current: `DATABASE_URL`, `REDIS_URL`, `NOTION_API_KEY`, `NOTION_DATABASE_ID`, `USER_TIMEZONE`, `SECRET_KEY ≥ 32 chars`. Any new required variable since the doc was written is a finding.
4. Verify Supabase pooler details (port 6543, sslmode=require, eu-west-1) match `deployment_architecture.md`.
5. Verify the SQLite fallback file (`.env.backup-sqlite-2026-04-16`) still exists and works (don't actually run it; verify schema parity with current Postgres state).

**Deliverable:** an env-var table with `var_name, in_env_example, in_claudemd, in_code, required, default, status`.

---

## 10. Frontend integration alignment

**Steps:**

1. `frontend/lib/integrations.ts` is the integration registry per CLAUDE.md. Every entry must have:
   - A backend OAuth callback at `frontend/app/api/integrations/<provider>/callback/route.ts`
   - An entry in the backend `GET /v1/integrations` response
   - A row in the `Settings → Integrations` UI

2. The "incremental OAuth" rule per CLAUDE.md: NextAuth sign-in must request only `openid email profile`. Verify `frontend/lib/auth.ts` (or wherever NextAuth is configured) has no sensitive scopes. A sensitive scope in sign-in config is a P0 (breaks signup).

3. Verify Cloudflare Tunnel is serving `npm run start` (production build), not `npm run dev`. Check the systemd unit / startup script / process manager. The Apr 25 perf incident proves this can regress silently.

---

## 11. Output format

Produce a single markdown report at `docs/audits/alignment_audit_YYYY-MM-DD.md` with this structure:

```
# Alignment Audit — {date}

## Summary
- P0 findings: N (list bullets)
- P1 findings: N
- P2 findings: N
- Sections completed: N/11

## P0 findings
For each: title, file:line both sides, impact, proposed fix (one line), no code change applied.

## P1 findings
Same format.

## P2 findings
Same format.

## Section-by-section deliverables
(Tables and findings from sections 1-10 in order.)

## Structural recommendations
What systemic changes would prevent the next audit. Examples:
- "Kill the project_history vs building_phases distinction; merge into one canonical doc."
- "Extend the APScheduler count CI gate to also assert exact job names."
- "Add a CI step that diffs SKILL.md across the three locations."
- "Add a pre-commit hook that re-derives every numeric claim from code."

## Sign-off
Operator must mark each P0 finding as triaged before any fixes are applied.
```

---

## 12. What this audit is not

- It does not regenerate diagrams.
- It does not edit code.
- It does not edit docs (even typos — except as noted in section 0).
- It does not run the test suite (the audit assumes tests pass; if they don't, that's a separate failure).
- It does not benchmark performance.
- It does not assess design quality, only alignment.

---

## 13. Halt criteria

Halt and surface immediately, before continuing the audit, if you find:

- A P0 multi-tenant data leak (a query without user scoping, a Redis key without user namespacing).
- A P0 research-integrity violation (an analytics query without `external_source IS NULL`, a VT instrument that doesn't capture the pre-registered metric).
- A state machine transition allowed in code but not in any doc, or vice versa, that would make a task unreachable from a terminal state.
- A documented endpoint that doesn't exist in code (broken contract for callers).
- A SKILL.md three-way diff (the agent is reading stale docs).

For each halt finding, post a one-paragraph summary and wait for operator sign-off before resuming.
