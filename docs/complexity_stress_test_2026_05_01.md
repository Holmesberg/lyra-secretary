# Complexity Stress Test — 2026-05-01

*Read-only audit. No code or docs were modified. Operator decides which kills land.*

## TL;DR

- **The system is built for ~50 power-user-equivalents but has 4 actively-engaged ones.** Surface count does not match user count by an order of magnitude. The operator has shipped 395 commits in 27 days and is now defending more concepts than the cohort can validate.
- **The instrumented research surfaces are over-built relative to the data.** 17 numbered analysis rules, ~25 active validity threats (VTs), 6 research log tables, 6 Loop instruments — and the active-user population (4) cannot generate enough rows in any single instrument to reach its own pre-registered floor before the week-6-8 retention checkpoint (Jun 18-25) decides whether the project ships at all.
- **Top kill recommendation:** delete the entire JARVIS operator-only chat assistant (1,580 LOC, alembic 042, 1 user, 0 research yield). It was added 2 days before this audit. Reversal cost: zero — the operator is its only user.
- **Estimated surface reduction if all top-10 kills land:** -3 tables, -19 endpoints, -4 jobs, -3 manifesto rules, -8 doc files, -1 nav route, -1 integration. That's roughly **-2,800 LOC backend + -1,500 LOC frontend + -2,100 lines of docs**.
- **Highest-confidence delete:** `analytics/cascade` endpoint + cascade dashboard math. Cascade was supposed to be "Paper 2 — faster path than Paper 1." It is not used by the frontend, has no tests beyond the scoring math, and the operator has not analyzed it once in 27 days.
- **Highest-confidence keep that surprised me:** `voided_at` discipline. Looks like ceremonial decoration; is actually doing work. Half the recovery-job postmortems trace to it. Keep.

## Kill list (ranked by impact-vs-risk)

| # | Target | Type | Owner (person, not doc) | Reversibility | Confidence | One-line case for deletion |
|---|--------|------|------------------------|---------------|------------|----------------------------|
| 1 | JARVIS operator chat assistant — `services/jarvis_agent.py` (305 LOC), `services/jarvis_tools.py` (818), `services/nvidia_nim_client.py` (257), `endpoints/jarvis.py` (200), `jarvis_invocation` table, alembic 042, 3 endpoints, 4 frontend components | endpoint+table+integration | Ali (2026-04-30, 2 days ago) | hours (single-feature revert) | **high** | 1,580 LOC operator-only feature with no users besides the operator and no research role. Latest addition; sunk cost is two days. |
| 2 | `cascade_score` analytics + `/v1/analytics/cascade` endpoint + frontend cascade card | endpoint+analysis | Ali (Apr 8 manifesto §"Cascade Failure Discovery") | days | **high** | Pitched as "Paper 2 — faster than Paper 1." Frontend doesn't render it. No row in operator_findings_log shows cascade analysis being read. 27 days dormant. |
| 3 | Moodle Web Services submissions sync — `moodle_submissions_sync.py` (566 LOC service + 95 LOC job + alembic 043 + 044 + endpoints) | integration | Ali (2026-05-01, today) | hours | **high** | Shipped today. Auto-marks deadlines complete. Solves "I submitted in Moodle but Lyra still shows overdue" — that is a 1-tap user action. 661 LOC + Fernet encryption to remove one tap from one user (operator). The ICS sync alone covers the data import. WS adds nothing the user can't do in 2 sec. |
| 4 | `resume_prediction` job + `resume_prediction_log` table + `resume_predictor.py` service + endpoint | job+table+service | Ali (alembic 038, 2026-04-28) | days | **med-high** | Sibling-of-VT-17 with no own pre-registration. Manifesto explicitly notes "No new MANIFESTO rule yet — sample-size threshold not crossed." Currently writes a row every 2 minutes per paused session. With 4 active users and one-paused-session-each on a typical day, the analysis set is empty. The pattern was copied because pause_prediction worked, not because resume showed evidence of mattering. |
| 5 | Pulse route — `frontend/app/(app)/pulse/page.tsx` + supporting components | route | Ali (preview-tagged, 2026-04-30) | hours | **med-high** | Marked `preview: true` in nav. Operator's preferred-but-not-yet-promoted dashboard. Three "dashboard-y" routes (today, pulse, insights) for a 4-user cohort is one too many. Keep `/today` (the verb), absorb the timer-as-hero idea into it, kill `/pulse`. |
| 6 | `/admin/dashboard` + `/admin/alpha_funnel` endpoints + admin frontend route | endpoint+route | Ali (alembic 037, alpha_funnel, 2026-04-28) | hours | **med** | "Operator-only" funnel for North Star metric ("% of new users who create a task AND start a timer within their first 3 minutes"). With n=7 trusted users, this is a SQL query the operator runs once a week, not a dashboard. Reading the operator_findings_log shows the manual queries are how the operator actually checks. |
| 7 | 12 of 25 documented validity threats (VT-1 through VT-13 except 12, plus 19, 20, 26, 27) — manifesto sections only, no code, no test, no data | manifesto rule | Ali (mostly Apr 14 batch insertion) | days (doc edit) | **med** | Decorative. None are referenced in code or tests. Half are restating analysis caveats that the analysis script will encode anyway. Active VTs to retain: 15, 16, 17, 17d, 17e, 21, 22, 23, 25, 29 (the ten with code or test references). Move the rest to an `archive/manifesto_v1.x_dropped_validity_threats.md` and stop adding more before the next 5 of them have a code home. |
| 8 | Doc consolidation: collapse 40 doc files → 8 — see §8 deep dive for the merge map | doc surface | unowned (5 alignment audits in 50 days) | days | **med** | Spec-vs-code drift IS the symptom. agent bootstrap doc says 10 tables (real: 16), says ~5 VTs (real: 25), says reminders job description that doesn't match the code. The audits keep finding drift because the surface count is unmaintainable, not because attention is lacking. |
| 9 | `parse.py` endpoint (`/v1/parse`, `/v1/parse/deadline-preview`) | endpoint | Ali (deprecation announced in agent bootstrap doc) | hours | **med** | agent bootstrap doc says "scheduled for deprecation. LLMs should call /v1/create directly with structured fields." It is still mounted, still consumed (by deadline-preview). Honor the deprecation: stop wiring it into new flows and remove the parse-chain endpoint when the brain dump fully owns parsing. |
| 10 | `archetype_assignment` as a table (15 LOC of schema + 220 LOC service + 311 LOC proximity service + 362 LOC bias_factor service) reduced to **two columns on `user`** | schema fold | Ali (alembic 015, 031, 032) | weeks (data migration) | **60% — flag for operator** | The instrument is real research; the data-modeling cost is not. Most users have one assignment, never re-fit. Active assignment data fits in `user.archetype_id`, `user.assignment_completed`, `user.raw_responses` JSON. The table buys nothing the column doesn't. The proximity recompute query rebuilds from `task` data each time — there's no historical row needed. **Confidence 60%** because re-fitting research at Phase 6 might want history. If you cap re-fits at 1/quarter, this folds. |

That is 10. The brief says stop at 10, surface, let the operator pick. Stopping.

## 10% add-back list

| # | Target | Why I changed my mind |
|---|--------|----------------------|
| 1 | Keep one of {`stale_session_recovery`, `orphan_task_recovery`} as a check-on-read for now, not delete both. | Initially I wanted to fold both into login-time checks. After re-reading the Apr 25 bug catalog (`dogfood_findings_living.md` items #3 and #6), the multi-tasking swap state machine produces ghost states that the operator would not recover from manually. Drop frequency to every 60 min, fold the two into one job, but don't kill the safety net entirely. |

That's 1.0/10 = exactly 10%. If I had to add a second I'd be reaching, which the brief warns is the failure mode in the other direction. Calibrated.

---

## Section deep dives

### 1. Concept count audit

| Surface | Counted | Reasonable for n=4 active users | Delta |
|---------|---------|---------------------------------|-------|
| Database tables | **16** | 8 | 2× |
| API endpoints (total) | **85** (31 GET, 48 POST, 5 DELETE, 1 PUT) | 30-40 | 2-2.8× |
| APScheduler jobs | **14** | 5 | 2.8× |
| Task states | 6 | 4 (PLANNED, EXECUTING, EXECUTED, SKIPPED) | 1.5× |
| Manifesto analysis rules | **17** | 5-6 (the ones with code) | 3× |
| VTs documented | **~25 active** (1-13, 15-17, 17d, 17e, 19-23, 25-27, 29) | 5-7 (the ones with code) | 4× |
| VTs in code | **10** | 5 | 2× |
| Archetypes | 5 | 5 | 1× — fine |
| Integrations | **6 active + 3 parked** (Notion, Telegram, GCal, Moodle ICS, Moodle WS, OpenClaw + Outlook/Slack/Gmail) | 2-3 | 2-3× |
| Doc files in `docs/` | **40+ md files, 10,386 lines** | 6-8 | 5× |
| UI routes (in nav) | **7** + admin/dashboard | 4 | 1.75× |
| Distinct notification types | 5 (reminders, timer_overflow, pause_prediction, resume_prediction, operator-Telegram) | 2-3 | 2× |

The brief said 2× is suspicious and 4× is overbuilt. **Three rows are at 4×: VTs documented (4×), doc files (5×), and analysis rules (3×)**. That is not random — those are the three surfaces that have *no consumer except their own future analysis*, and analysis is gated by retention which hasn't been validated yet.

agent bootstrap doc is already drifting from the code: it claims 10 tables (actual 16), ~14 jobs (correct), and "at least 5 VT pre-registrations" (actual 25). This is what produces the alignment audits. Audits aren't slipping; the substrate is.

**Worth saying once before moving on:** the 16-table number isn't because someone forgot to consolidate. Each table got added because the existing tables had the wrong shape for what was actually needed (e.g., `task_deadline_outcome` couldn't go on `task` because EXECUTED tasks are immutable). The architecture is correct. The complaint is that there are too many concepts for the cohort to validate them all simultaneously.

### 2. Manifesto rule pruning

The manifesto has **17 numbered analysis rules** (not the 5 of the prompt — drift × 3) plus ~25 active VTs.

**Rules with code OR test reference (KEEP — these have a consumer):**

- Rule 8 (secondary pre-only H1 test) — implicit in `analytics.py`
- Rule 11 (no-nudge control days) — `reflection_view_log.fired_at` is the exposure flag
- Rule 12 (scope inflation mediation, VT-22 falsification) — referenced in tests
- Rule 13 (archetype-prior shrinkage) — `bias_factor_service.py`, `analytics/bias_factor/lookup`, tested
- Rule 14 (H2 deadline-distance kill at n≥60) — referenced in `analytics.py` VT-29 note
- Rule 15 (per-deadline `bias_factor`) — referenced in tests
- Rule 17 (VT-25 archetype-reveal no-RCT design) — referenced in tests, archetype proximity service

**Rules WITHOUT code OR test (CANDIDATES for kill):**

- Rule 1 (exclude retroactive sessions from H1) — pure analysis-time SQL, doesn't need to be a manifesto rule
- Rule 2 (category taxonomy frozen Apr 4-15) — date passed; rule is historical
- Rule 3 (exclude voided sessions) — already enforced by every query (the voided_at memory)
- Rule 4 (exclude planned_duration < 5 min) — analysis-time SQL
- Rule 5 (prediction direction pre-registered) — interpretive, not enforceable
- Rule 6 (no post-hoc subsetting) — analysis discipline, not code
- Rule 7 (VT-12 distinguishing analyses in H1 report) — analysis-time
- Rule 9 (disattenuated correlation) — analysis-time
- Rule 10 (readiness-direction analysis) — analysis-time
- Rule 16 (soft-warning RCT) — INACTIVE per its own text; the deadline soft-warning UX hasn't shipped

That's **10 of 17 rules** that are either historical, analysis-time-only, or inactive. They are not load-bearing. They produce one specific failure mode: every product decision now has to round-trip through "does this break Rule N?" before it can ship. That is the actual cost of decorative rules — not their text, but their *gravity*.

**Recommendation:** move all analysis-time rules into a single `docs/h1_analysis_protocol.md` that lives next to the analysis script. Keep the manifesto for hypotheses, kill criteria, and rules that the *code* must enforce. The current manifesto is a 1,324-line document and the operator can no longer read it end-to-end before making a decision — that's the kill criterion for the document itself.

### 3. VT pruning

25 documented validity threats. 10 referenced in code. 5 referenced in tests. **15 VTs (60%) are pure documentation overhead.**

The 10 with code-side existence: VT-15, VT-16, VT-17, VT-17a, VT-17d, VT-21, VT-22, VT-23, VT-25, VT-29. These earn their keep — pause prediction, retroactive self-report, external-source contamination, archetype reveal, and external-deadline contamination are real research-integrity threats with consumers.

The 15 without code-side existence (VT-1 through VT-13 minus 12, plus 19, 20, 26, 27): most are analysis-time caveats that the H1 analysis script will encode anyway. They are not constraining product decisions; they are constraining *thinking* about product decisions. That cost is invisible but real — every operator question that adjacent to "could I add this feature" first asks "does it trip a VT?" and the operator has to scan 25 sections.

**Recommendation:** keep the 10 referenced VTs in the manifesto. Move the other 15 to `archive/manifesto_validity_threats_dropped_2026_05_01.md` with a one-line "moved out of active manifesto on date X because no code consumer" header on each. Stop adding new VTs to the manifesto until each existing VT either has a kill criterion *that has fired* or has produced an analysis row.

**Test:** at month +2, did any of the dropped VTs produce a finding? If not, the kill was correct.

### 4. Background job pruning

14 jobs. Actual cadence and value:

| # | Job | Cadence | Failure if stopped 1 week | Lazy alternative | Recommendation |
|---|------|---------|---------------------------|------------------|---------|
| 1 | reminders | 1 min | Telegram nudges go silent | none — it's the user-facing surface | KEEP |
| 2 | notion_sync | 5 min | Notion drifts; fix on retry | check on next /create call | FOLD into TaskManager retry-on-write with backoff |
| 3 | timer_overflow | 2 min | Operator misses overrun | check on /tasks/query open | LAZY — fold into the next /today render |
| 4 | overdue_tasks | 30 min | PLANNED tasks past their start time stay PLANNED | check on /tasks/query | LAZY — compute server-side on read |
| 5 | stale_session_recovery | 15 min | Ghost stopwatch banners persist | check on login | DROP to 60 min; fold with #6 |
| 6 | orphan_task_recovery | 15 min | EXECUTING tasks with no session persist | check on login | FOLD with #5 (one job, one query, both cleanups) |
| 7 | pause_prediction | 1 min | VT-17 instrument goes dark | none — measurement substrate | KEEP |
| 8 | reconcile_responses | 5 min | pause_prediction_log rows stay open | reconcile on next /tasks/query | LAZY — eliminate |
| 9 | reconcile_deadline_outcomes | 30 min | task_deadline_outcome rows missing | reconcile on /analytics/deadline-shape open | LAZY — eliminate (the analytics endpoint already runs the same query) |
| 10 | sweep_missed_deadlines | 1 hour | active deadlines past due stay active | check on /deadlines open | LAZY — compute on read |
| 11 | llm_enrichment | **5 SECONDS** | New tasks don't get LLM enrichment | already async via queue | KEEP cadence; add max_instances guard (already present) |
| 12 | resume_prediction | 2 min | Resume banners go silent | none — measurement substrate but see #4 in kill list | **DELETE — Kill list #4** |
| 13 | moodle_ics_sync | 6 hours | New Moodle deadlines don't import | n/a (external service) | KEEP |
| 14 | moodle_submissions_sync | 6 hours | Submissions stay marked overdue in Lyra | n/a (external service) | **DELETE — Kill list #3** |

**End-state target: 6 jobs.** Reminders, pause_prediction, llm_enrichment, one merged stale+orphan recovery (every 60 min), notion_sync (or fold into TaskManager), moodle_ics_sync.

The operator runs the backend on a laptop that sleeps overnight. Every job that wakes the laptop with no work to do is pure cost — including battery and developer-attention cost when the logs fill up with "no rows to process" lines. The lazy-on-read pattern is the natural fit for a single-laptop deployment.

**Worth flagging:** the misfire_grace_time + coalesce=true setting (set 2026-04-30) is a band-aid on the underlying problem that there are too many jobs for laptop-sleep-cycle ergonomics. The fix is fewer jobs, not better misfire handling.

### 5. Endpoint dedup

**85 endpoints. Frontend uses ~50.** The other 35 are split between OpenClaw, admin, and unused.

**Endpoints with no current human-facing consumer (delete candidates):**

- `/v1/analytics/discrepancy` — old endpoint, frontend doesn't reach it
- `/v1/analytics/cascade` — kill list #2; cascade dashboard never built
- `/v1/analytics/bias_factor` (parent — `/lookup` is used) — superseded by `/lookup`
- `/v1/analytics/pause_prediction` — VT-17 dashboard query, surfaced only via `/insights`
- `/v1/analytics/deadline-shape` — Phase I, never built into UI
- `/v1/analytics/calibration_nudge` — Loop 1 query, surfaced once
- `/v1/admin/dashboard` + `/v1/admin/alpha_funnel` — kill list #6
- `/v1/skill/ping` — OpenClaw-only; OpenClaw is operator-only per memory
- `/v1/tasks/last` — OpenClaw-only
- `/v1/tasks/{task_id}/sync` — manual Notion backfill, used once
- `/v1/tasks/swap` — OpenClaw-only (skip ↔ planned swap)
- `/v1/schedule/clear` — OpenClaw-only (operator-only feature)
- `/v1/notifications/push` — internal scheduler-only
- `/v1/parse` + `/v1/parse/deadline-preview` — kill list #9
- `/v1/jarvis/ask` + `/v1/jarvis/confirm` + `/v1/jarvis/health` — kill list #1
- `/v1/integrations/moodle/ws-*` — kill list #3 (3 endpoints)
- `/v1/pause_predictions/pending-confirmation` — retroactive confirmation chip; used rarely

That's **19 endpoints** that could go without removing any current capability that a human-facing UI uses. Some (admin, OpenClaw) might come back if those surfaces are ever launched broadly; right now they have one user (the operator).

**Worth flagging:** the `/v1/admin/feedback` + `/v1/admin/feedback/{id}/resolve` pair is admin-only, but feedback IS user-facing. Keep the user-facing `/v1/feedback` POST. The admin GET could be a SQL query (it's literally `SELECT * FROM feedback ORDER BY submitted_at DESC LIMIT 50`).

### 6. Schema folding

16 tables. By usage shape:

| Table | Rows (estimated) | Pattern | Fold candidate |
|-------|------------------|---------|----------------|
| `task` | core | mutated | KEEP |
| `stopwatch_session` | core | mutated | KEEP |
| `pause_event` | per pause | append | KEEP — VT-17 substrate |
| `pause_prediction_log` | per firing | append+reconcile | KEEP — VT-17 substrate |
| `resume_prediction_log` | per firing | append+reconcile | **DELETE — kill list #4** |
| `reflection_view_log` | per impression | append+stamp | possibly fold into stopwatch_session as columns; but used by VT-21 stratification — KEEP |
| `calibration_nudge_event` | per task creation nudge | append+reconcile | KEEP — Loop 1 substrate, low row count |
| `category_mapping` | seeded | static | KEEP — 1 query at task create |
| `user` | per user | mutated | KEEP |
| `archetype` | 5 rows | static | KEEP — lookup |
| `archetype_assignment` | per user (1-2) | mutated | **FOLD — kill list #10** |
| `external_event_outcome` | per attendance mark | append | low usage — KEEP for now (template per integrations doc) |
| `deadline` | per deadline | mutated | KEEP |
| `task_deadline_outcome` | per executed-and-deadline-bound task | append | KEEP — separate by EXECUTED-immutability constraint |
| `feedback` | per user submission | mutated | KEEP — user-facing |
| `jarvis_invocation` | per JARVIS tool call | append | **DELETE — kill list #1** |

**Net schema delta if all kills land:** -3 tables (`resume_prediction_log`, `archetype_assignment`, `jarvis_invocation`).

The "table with <100 rows after a month" heuristic from the brief: I cannot read row counts without hitting production, but two tables almost certainly meet it: `jarvis_invocation` (2 days old, operator-only) and `resume_prediction_log` (3 days old, 4 active users with maybe 1 paused session/day = ~12 firings/day, so ~36 rows total).

### 7. Integration pruning

| Integration | LOC (backend) | Connected users | Operator daily? | Verdict |
|------------|---------------|-----------------|-----------------|---------|
| Notion | 172 | 1 (operator) | yes | KEEP — works, low maintenance |
| Telegram | 129 | 1 (operator) | yes (the operator-Telegram thread) | KEEP |
| Google Calendar | ~ shared with calendar.py, ~200 | unknown, low | yes | KEEP — read-only inbound |
| Moodle ICS | 410 service + 68 job | 1 (operator) | weekly | KEEP — alpha differentiator for student users |
| Moodle WS | 566 service + 95 job | 1 (operator) | rarely | **DELETE — kill list #3** |
| OpenClaw | 149 lines SKILL.md + polling endpoints | 1 (operator) | not since Apr 29 per `openclaw_subscription_findings_2026_04_29.md` | **MARK PARKED** — keep code, remove from active maintenance, do not three-way-sync until external use is confirmed |

**OpenClaw specifically:** memory says "no external-facing feature may depend on OpenClaw until components are integrated into the Lyra codebase." The skill file gets three-way-sync ceremony on every edit, but the consumer is one user (the operator) who has the entire web UI. The operator-only memory is correct; the question is whether OpenClaw deserves *any* maintenance attention at all when web UI is faster to ship for the same operator.

**Worth flagging:** the parked Outlook/Slack/Gmail integrations in `integrations_architecture.md` are correctly parked. Don't build any of them before the existing 6 stop being net-negative.

### 8. Doc surface collapse

**40+ markdown files in docs/, 10,386 lines.** Five alignment audits in 50 days. The operator has explicitly named the symptom (drift); the cause is surface count.

**Recommended target: 8 doc surfaces.** Merge map:

```
docs/timeline.md  ←  project_history.md + building_phases.md +
                     dogfood_findings_living.md + sprint_2026_04_29.md +
                     strategic_decisions_april_22.md + april_24.md +
                     llm_latency_findings_2026_04_28.md +
                     today_latency_audit_2026_04_29.md +
                     manifesto_alignment_audit_2026_04_28.md +
                     root_cause_analysis_2026_04_29.md +
                     openclaw_subscription_findings_2026_04_29.md +
                     brain_dump_stress_test_2026_04_30.md +
                     loop_11_implementation_log.md +
                     voided_at_audit_verification.md

docs/research.md  ←  MANIFESTO.md + methodology.md +
                     design_patterns/structural_investigation_rule.md +
                     post_week_1_2_launch_survey.md +
                     heuristic_registry_2026_04_28.md +
                     feedback_loops_closure_plan.md +
                     insight_mechanisms_post_retention.md +
                     phase_6_architecture_backlog.md

docs/architecture.md  ←  architecture.md + deployment_architecture.md +
                         integrations_architecture.md +
                         moodle_lms_integration.md +
                         deadline_mechanism_design.md +
                         brain_dump_onboarding_design.md +
                         stale_session_recovery_policy.md +
                         design_patterns/notification_patterns.md +
                         design_patterns/rules_vs_agency.md +
                         design_patterns/two_stage_destruction.md +
                         do_not_add.md

docs/parked.md  ←  parked_ideas.md (slimmed)

agent bootstrap doc  ←  unchanged but kept current

README.md  ←  unchanged but slimmed

LYRA_BUGS.md  ←  unchanged

openclaw/skills/lyra-secretary/SKILL.md  ←  unchanged
```

Plus 1 additional surface for prompts (alignment_audit_prompt.md, complexity_stress_test_prompt.md, feedback_triage_recipe.md, pre_launch_audit_script.md, operator_interrogation_checklist.md, testing_patterns.md, import_integrations_capability_map.md → `docs/playbooks.md`).

That's 8 active doc surfaces. From 40 → 8 is an 80% reduction. The merge can happen in one sitting because most files are linear append-only logs.

**The duplication test, one example:** "external_source IS NULL" rule appears in agent bootstrap doc, MANIFESTO.md, integrations_architecture.md, and the Deadline model docstring. Pick one canonical location (the model docstring is closest to the constraint) and delete the others' copies, replacing with a one-line link.

### 9. UI route pruning

7 routes in nav + admin/dashboard:

| Route | What it does | Recommendation |
|-------|--------------|----------------|
| `/today` | Day-of task list, primary work surface | KEEP — the verb |
| `/pulse` | Timer-as-hero dashboard, "preview" tag | **DELETE** (kill #5) — fold timer-as-hero idea into `/today` |
| `/calendar` | Day/Week/Month calendar | KEEP — distinct primitive |
| `/deadlines` | Deadline list with bind status | KEEP — distinct primitive |
| `/table` | CSV-export-shaped table view | DEMOTE — admin only, hide from nav (the operator uses it; trusted users don't need it) |
| `/insights` | Reflection history + analytics | KEEP — the mirror |
| `/settings` | Settings, integrations, archetype profile | KEEP |
| `/admin/dashboard` | Operator-only funnel | **DELETE** (kill #6) — replace with a SQL query the operator runs by hand |

**End state: 5 nav routes + settings + (hidden) /table + (hidden) /onboarding marketing pages.**

The "dashboard-y" cluster (today + pulse + insights) is the textbook evidence of dashboard sprawl. The operator's reasoning ("/pulse is preferred-but-not-yet-promoted") *predicts* the future merge — accelerate it. Don't ship two routes that compete for the same eyeball-time; the user picks one and the other rots.

### 10. Archetype system

5 archetypes, 29-item survey, shrinkage-blended bias_factor, sqrt(N) ESS damping, winsorization to [0.30, 3.0], 99% display cap, 2% display floor, dynamic reveal, alembic 015 → 031 → 032.

Operator findings (Apr 29, n=7 trusted): 6/7 onboarded, **survey completion not separately reported but at most 6**. With one user (operator) showing extreme outlier behavior that broke the un-amended math (12 archetype amendments to handle 1 user's distribution).

The bias_factor MATH is correct. The QUESTION is: with 4 active users and 0 published research, is the 893-LOC archetype/bias-factor/proximity service stack producing user-visible value or research value?

**User-visible:** the calibration nudge surfaces a duration suggestion. Whether that suggestion is computed from "personal data + archetype shrinkage" vs. "personal data alone" likely doesn't matter to a user with <30 sessions in any cell. The shrinkage is *theoretically* important; operationally the personal data dominates by session 30 and most users are below 30.

**Research-visible:** the entire mechanism is pre-registered as Rule 13 plus VT-25 (archetype-reveal threat). Cannot be killed without retracting Rule 13. Rule 13 is one of the 7 "code-having" rules.

**Recommendation:** keep the architecture (it's correct and pre-registered). Fold `archetype_assignment` table into 3 columns on `user` (kill list #10, 60% confidence — flagged for operator). Don't ship more amendment versions until the next 5 users complete the survey AND show non-degenerate distributions. Each amendment is paying interest on a 1-user-anchored debt.

---

## What I refused to recommend killing

- **`voided_at` discipline + the voided_at_guard memory.** It looks like ceremonial decoration; reading the bug catalog it's doing real work. Half the recovery-job postmortems trace to "what about voided rows?". Keep it — the rule pays for itself in postmortem-prevention.

- **`pause_event` + `pause_prediction_log` + VT-17 substrate.** The most expensive thing in the codebase by row-count, and it might be the single mechanism that distinguishes Lyra from a generic timer. Keep it. The kill criterion is pre-registered (acceptance rate < 0.20 after 7 days kills the feature per-user); let the data make the call.

- **`reflection_view_log`.** Looks like a 5th log table; but it is the exposure flag for VT-21 stratified analysis (Rule 11), and that is the single instrument that distinguishes "the nudge worked" from "users who saw the nudge ALSO have these properties." Keep.

- **`calibration_nudge_event` (Loop 1).** Same shape as #2 but newer. Pre-registered, low row count, low write cost, and the analytics endpoint depends on it. Keep.

- **The brain dump (`brain_dump.py` + parser, 627+50 LOC).** Recently rewritten (Apr 28). Onboarding gate. Per the memory `project_relief_instrument_reframe`, chaos→structure is the user-facing mechanism. Killing this would amputate the actual product. Keep.

- **The state machine itself (PLANNED → EXECUTING ⇄ PAUSED → EXECUTED + SKIPPED + DELETED).** Looks like 6 states for what other apps do with 2. Reading the bug catalog, every multi-tasking and recovery bug traces to a state-machine decision that the alternative ("just track started_at and ended_at") would not have caught. Keep all 6.

- **The Structural Investigation Rule (`docs/design_patterns/structural_investigation_rule.md`).** Looks like the textbook overbuilt-process candidate. But the operator has explicitly named it as a working discipline (`feedback_structural_investigation` memory) and the manifesto-vs-code drift would be worse without it. Keep.

---

## Structural recommendations

These are the policies that would prevent the next overbuild. Pick one, not all five — adding policies is itself overbuild.

1. **APScheduler job ceiling: 5.** New jobs require explicit removal of an existing job. LIFO discipline. Forces the lazy-on-read alternative to be considered first.

2. **Manifesto rule + VT lifecycle.** Every rule and VT requires (a) a code or test reference within 30 days of being added, or (b) an analysis row produced within 60 days of being added. Fail either gate → auto-archive to `archive/manifesto_dropped_*.md` with a one-line reason. Removes the decorative half of both.

3. **Doc surface count locked at 8.** New doc requires deletion or merge of an existing one. Forces the "where does this go?" question on every new doc.

4. **VT instrument auto-retire if not analyzed within 60 days of first data row.** Avoids the "we built the instrument, then never ran the script" failure mode that the operator already named in `project_logging_friction.md`.

5. **The 4-user gate.** No new instrumented mechanism (job, log table, manifesto rule, VT) ships until the 4 currently-active trusted users have produced enough rows to validate the *previously-shipped* mechanism. Forces sequential validation, not parallel speculation.

If picking one — **#5**. It is the only one that addresses the upstream cause (parallel speculation). The other four address symptoms.

---

## A note before closing

The operator is a strong builder. Read of this codebase: it is unusually well-tested (16k LOC of tests), unusually well-documented internally (10k LOC of docs), and the architectural decisions are mostly correct. The complaint is not "this is bad code." The complaint is that **one operator with 4 active trusted users cannot validate 25 VTs, 17 rules, 14 jobs, 16 tables, 6 integrations, and 8 routes simultaneously** — and the cohort needs to be ~10× current size before that surface count earns its keep.

The kill list above is what gets the surface count back to a place where the next 27 days of operator effort lands on the 4 things that decide whether Lyra retains, instead of on the 16 things that don't.

Decisions belong to the operator. This audit is the axe; the swing is yours.

---

## Postscript — 2026-05-02 Reframe

After this audit ran, a follow-up conversation reframed the diagnosis. The audit identified the **symptom** (surface-area sprawl) but partially misdiagnosed the **disease**. The actual disease: data utilization gap, not complexity explosion. The substrate is rich; the inference layer that metabolizes it into user-visible value is the thin part.

Lyra's actual target is a behavioral inference engine, not a productivity app. The "research surface" was always proto-intelligence infrastructure; the "VTs and integrity rails" were epistemic brakes for a future adaptive system. Sensing layer over-built relative to cortex layer.

**Sections of this audit that the reframe re-classifies:**

- **Kill #1 (JARVIS):** wrong call. JARVIS is operator-only deeper-pattern-synthesis on operator's own data — the bootstrap-paradox-respecting playground for hypothesis discovery. Anti-LLM stance applies to *user-facing inference*, not operator-side analysis. JARVIS lives. Plan promotes it to Phase 2 of the system transition.
- **Kill #2 (cascade analytics):** partial reversal. The dashboard surface kill stands; the underlying math (skip propagation, P(skip N+1 | skip N), morning anchor) is cortex-layer intelligence and survives in the new inference_engine.
- **Kill #4 (resume_prediction):** reversed. Resume prediction is implicit-signal-based behavioral inference with confidence calibration — exactly the cortex layer to invest in. Don't kill substrate; the unused acceptance dashboard can still go.
- **Kill #10 (archetype_assignment fold):** category error. Schema layout, not complexity reduction; the math (Kish ESS, winsorization, posterior) is intact either way. Drop from the kill list.
- **VTs:** of the 16 VTs flagged decorative, ~10 are actually integrity rails for the cortex layer (VT-11 contamination, VT-19 endogeneity, VT-26 prior misspecification, VT-27 confidence calibration). Only ~3-6 are genuinely decorative (decided/shipped/addressed: VT-2, VT-7, VT-13).

**What survives unchanged:**

- Doc consolidation (40 → 8) — orthogonal to inference quality
- Surface kills (admin dashboard, /pulse fold-into-today, deprecated /parse, Moodle WS, audit-only endpoints)
- Structural recommendation #5 (4-user gate / no-new-mechanism-during-validation) — incorporated as hard gate in the transition plan

**The actionable replacement for this audit:** the 2026-05-02 system transition plan (operator-local: `/home/alina/.assistant runtime/plans/alright-listen-up-assistant runtime-delegated-garden.md`). Six phases (calibration contract → data utilization triage → JARVIS-as-discovery → inference engine → reflection surfaces → dark column retirement → top-7 implicit instrumentation) executing the breakthrough's actual prescription: collect more implicit signal + better math at every layer + filter useful hypotheses from constraining ones. The kill list above stays valid for the surface-sprawl half; the substrate-deletion half was wrong.

The deeper architectural target — "behavioral inference engine with productivity as interaction surface" — was always the project. This audit found a symptom; the reframe found the disease.
