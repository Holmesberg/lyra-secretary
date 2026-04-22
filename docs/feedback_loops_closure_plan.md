# Feedback Loops — Closure Plan

*Captured: 2026-04-22.*

Ten loops were identified in the 2026-04-22 structural stress test.
Each captures a signal somewhere in the stack but doesn't route the
output back to the user or to a subsequent decision — so the
measurement accumulates without acting. This document specifies what
it would take to close each loop.

**Priority framing:** loops are ranked by their dependency on the
refined thesis (see `product_thesis_refined_april_22.md`). Loops that
directly support the structured-deadline-failure question are P0.
Loops that support it indirectly are P1. Loops that are nice-to-have
once the core is instrumented are P2.

| # | Loop | Current state | Priority | Effort |
|---|---|---|---|---|
| 1 | Calibration nudge → behavior change | Fires, no persistent log of outcome | P0 | ~2h |
| 2 | Pre-task readiness → next-task prediction | Captured, not consumed | P1 | 4h |
| 3 | Archetype priors → cold-start predictions | Table exists, 0 assignments | P2 | 12h (intake) |
| 4 | VT-17 acceptance rate visibility | Computed, not surfaced | P1 | 2h |
| 5 | Reflection surfaces → behavior change (VT-21) | Data logged, analysis missing | P1 | 4h |
| 6 | External event attendance → reflection | Stored, not surfaced back | P2 | 3h |
| 7 | Custom category usage → learned taxonomy | Fragments, never consolidates | P2 | 6h |
| 8 | Retention data → product iteration | Manual psql queries | P0 | 2h |
| 9 | OpenClaw Telegram → user delivery | Operator-only | **BLOCKED** | multi-week |
| 10 | Multi-timezone → multi-region | Single-TZ lock | **BLOCKED** | 3-5 days + bugs |

Plus one cross-cutting:

| # | Loop | Current state | Priority | Effort |
|---|---|---|---|---|
| 11 | Scope-estimate-at-plan → deadline outcome | **MISSING INSTRUMENT** | P0 | 4h (schema + UI + analysis) |

---

## Loop 1 — Calibration nudge → behavior change

**Signal captured:** nudge fires (bias_factor lookup); user accepts
(clicks "Use X min") or dismisses (clicks "Keep Y min"). The
`nudgeDecisionMade` flag (shipped 2026-04-22) is session-scoped and
non-persistent.

**What's missing:** a persistent per-firing log — did the nudge fire,
what did it suggest, did the user accept, and *what was the actual
duration_delta on that task*? Without the third piece, the question
"does the nudge improve calibration?" is unanswerable.

**Closure spec:**

1. New table `calibration_nudge_event`:
   ```sql
   id SERIAL PRIMARY KEY,
   user_id INT NOT NULL INDEX,
   task_id VARCHAR(36) NOT NULL,            -- task being planned
   suggested_duration_minutes INT NOT NULL,
   user_planned_duration_minutes INT NOT NULL,  -- what user had typed
   bias_factor FLOAT NOT NULL,              -- the raw multiplier
   sample_size INT NOT NULL,                -- how many similar past tasks
   user_decision VARCHAR(16) NOT NULL,      -- 'accepted' | 'dismissed'
   decided_at DATETIME NOT NULL,
   -- Filled by reconciliation job after task completes:
   executed_duration_minutes INT,           -- null until task executes
   resolved_at DATETIME
   ```
2. Write on decide (both branches of the modal already exist — add hook).
3. Reconciliation job (extend existing APScheduler): when a task
   transitions EXECUTING → EXECUTED, if it has a matching nudge_event
   row, stamp `executed_duration_minutes` + `resolved_at`.
4. New insight: `GET /v1/insights/calibration-effect` returns
   per-user accept-vs-dismiss delta means over rolling 30 days.
5. Surface: Insights page section, operator-only in v1.

**Why P0:** the entire "measurement-backed adaptive" thesis rests on
whether the calibration feedback actually changes planning behavior.
Currently there is zero data to answer yes or no. This loop is the
highest-leverage instrument to close.

---

## Loop 2 — Pre-task readiness → next-task prediction

**Signal captured:** readiness 1-5 stamped before start; reflection
1-5 after stop.

**What's missing:** no downstream consumer. Readiness never feeds
into bias_factor or any surface. `signed_discrepancy` is computed
but never shown.

**Closure spec:**

1. Add readiness-conditioned bias_factor: extend
   `calibration_service.bias_factor(category, time_of_day)` to
   `bias_factor(category, time_of_day, readiness_bucket)` with
   readiness bucketed into {low: 1-2, mid: 3, high: 4-5}.
2. When readiness is known, use the refined bias_factor for the
   calibration nudge.
3. Surface on the micro_mirror: "Tasks you started at readiness≤2
   took 1.8× their planned duration on average."
4. Regression test: nudge suggestion differs when readiness changes
   with ≥5 historical samples per bucket.

**Why P1:** leading indicator for the core thesis. Nice to have
before the deadline-shape mirror ships but not blocking.

**Risk:** at current per-user data density, readiness-conditioned
buckets are likely under-populated. Gate the refined estimate on
≥3 samples per (cat, tod, readiness) cell; fall back to unconditioned
bias_factor otherwise.

---

## Loop 3 — Archetype priors → cold-start predictions

**Signal captured:** Archetype table has `prior_bias_factor` + `prior_sigma`.

**What's missing:** zero users have archetype assignments. Intake
battery (MEQ + BFI-C + BSCS + GP) is deferred.

**Closure spec:**

1. Defer indefinitely until one of:
   - ≥20 users signed up (enough to make intake-to-prior mapping
     meaningful)
   - Research paper submission requires it
2. Until then, Archetype + ArchetypeAssignment are schema debt but
   not behavioral debt — keep the tables, don't instrument further.
3. DO NOT delete the schema — the thesis-refinement explicitly
   re-elevates deadline-temperament as a future research arm.

**Why P2:** infrastructure for a future research phase. Activating
it now at n<20 would produce no usable priors.

---

## Loop 4 — VT-17 pause-prediction acceptance rate

**Signal captured:** pause_prediction_log captures fire + outcome,
reconciliation job closes the 5-min acceptance window.

**What's missing:** no dashboard showing per-user acceptance rate.
Kill criterion (<0.20 kills) requires operator to manually query.

**Closure spec:**

1. Extend `GET /v1/analytics/pause-prediction` (if exists) or create
   it with per-user acceptance rate over rolling 7 / 30 days.
2. `/insights` page gets a "Pause prediction effectiveness" section:
   acceptance rate, sample size, progress bar toward n=20 threshold.
3. Operator dashboard section: kill-criterion indicator (green if
   ≥0.40, amber 0.20-0.40, red <0.20, grey <7 days per-user history).

**Why P1:** VT-17 is a live instrument. Without visibility, kill
decisions are made too slowly.

---

## Loop 5 — Reflection surfaces (VT-21) → behavior change

**Signal captured:** reflection_view_log records fire + viewed +
dismissed + dwell_seconds.

**What's missing:** VT-21 stratified analysis isn't written. Data
accumulates unread.

**Closure spec:**

1. `GET /v1/analytics/reflection-exposure` — per-user split of
   "exposed to surface X" vs "not exposed" across their last N tasks,
   with subsequent duration_delta variance as the stratification
   outcome.
2. Kill criterion per VT-21: stamp it into the doc if not already —
   something like "if exposure has no effect on subsequent delta
   variance at n=30 exposures per user, the mirror is decorative
   not corrective."
3. Insights surface: per-user "your exposure history" section with
   exposure-to-calibration correlation.

**Why P1:** supports the core thesis indirectly. Can wait until P0
loops are closed.

---

## Loop 6 — External attendance self-report → reflection

**Signal captured:** external_event_outcome (attended | skipped)
per user per GCal event.

**What's missing:** the signal goes into a table and stays there.
No product surface does anything with it.

**Closure spec:**

1. Weekly reflection surface: at Sunday night (or first session
   after 7 days of data), show "Last week you skipped 3 of 5
   meetings in category X. Does that pattern feel right to you?"
2. The surface itself generates a reflection_view_log row so VT-21
   can measure whether exposure changes subsequent attendance or
   scheduling behavior.
3. Kill criterion bump: at n≥10 users with ≥5 marked outcomes each,
   if the weekly reflection is dismissed >90% of the time, the
   signal is uninteresting to users.

**Why P2:** tangential to the core deadline-failure thesis. Nice
ambient signal, not load-bearing.

---

## Loop 7 — Custom category usage → learned taxonomy

**Signal captured:** user-typed categories persist per-task. CategoryMapping
seeded with keyword→category lookups.

**What's missing:** no clustering, aliasing, or suggestion. "lec"
and "lecture" and "Lectures" are three separate buckets. Per-category
bias_factor requires ≥N tasks per category → fragmentation delays
every insight.

**Closure spec:**

1. Phase 1 (P2): add a canonical-category-suggestion endpoint that
   runs edit-distance or embedding similarity against existing
   user categories + built-ins on modal focus. "You typed 'lec' —
   did you mean 'lecture' (14 prior tasks)?"
2. Phase 2 (P3, future): LLM-side similarity clustering for
   per-user alias merge suggestions, operator-approved.
3. DO NOT auto-merge without user consent — category-space mutation
   is Hard Rule territory; requires Structural Investigation.

**Why P2:** valuable when per-user task volume grows, not urgent
at 10-30 tasks per user.

---

## Loop 8 — Retention data → product iteration

**Signal captured:** every relevant metric lives in the DB
(signups, onboarded, first-task, first-execution, D2/D7 returns,
funnel shape).

**What's missing:** a dashboard. Operator runs ad-hoc psycopg2
scripts. Product decisions are made against last-week's mental model
of users.

**Closure spec:**

1. New endpoint `GET /v1/analytics/operator-dashboard` — gated on
   `is_operator=true`, returns cohort JSON:
   ```json
   {
     "total_users": 7,
     "non_operator_users": 4,
     "returning_today": 2,
     "returning_7d": 3,
     "funnel": {
       "signed_up": 7, "onboarded": 5, "first_task": 4,
       "first_execution": 3, "returned_d2": 2
     },
     "vt_progress": {
       "vt_17": {"users_at_7d_history": 1, "threshold": 20},
       "vt_22": {"macro_tasks_with_deadline": 0, "threshold": 20},
       "imp_3": {"gcal_connected": 0, "threshold": 20}
     },
     "last_calculated_at": "..."
   }
   ```
2. New operator-only page `/admin/dashboard` that renders the JSON
   above. Simple table + progress bars, no charts library.
3. Fire on app load for operator, cache 5 min.

**Why P0:** closes the operator's decision loop. Every product fix
today is based on manual inspection; this automates the inspection.

---

## Loop 9 — OpenClaw Telegram delivery → user intervention

**Signal captured:** pause prediction fires, notification enqueued
in Redis.

**What's missing:** only operator has OpenClaw integration → only
operator receives the notification → VT-17 intervention arm is n=1.

**Closure spec (BLOCKED):**

1. OpenClaw integration is operator-only per pre-registered memory
2. Alternative delivery paths:
   - Web push notifications (browser native)
   - Email digest (batched)
   - In-app banner (already partially exists — PausePredictionBanner)
3. The in-app banner IS a delivery arm for web-session users —
   treat VT-17 as measuring in-app intervention, not Telegram. Update
   the pre-registration to reflect the actual delivery channel.

**Why BLOCKED:** requires resolving OpenClaw operator-only constraint
OR formally reframing VT-17 as an in-app-only intervention.

---

## Loop 10 — Multi-timezone → multi-region expansion

Well-documented architectural debt. Deferred per
`dogfood_findings_living.md` P3.

---

## Loop 11 (NEW) — Scope-estimate-at-plan → deadline outcome

**Signal captured:** currently NONE. The description brain-dump is
free text; its scope content is never parsed.

**What's missing:** the whole instrument. Without this, VT-22 scope
inflation can't be tested.

**Closure spec:**

1. New columns on Task:
   - `deadline_utc` (nullable DateTime)
   - `scope_bullet_count_at_plan` (nullable Int) — computed from
     description bullet-regex at create time
   - `scope_bullet_count_at_execute` (nullable Int) — recomputed if
     user edits description before executing
2. Alembic migration (029).
3. `TaskParser` or create endpoint: parse description for bullet
   markers (`^\s*[-*•·]` with unicode) and count.
4. New reconciliation: on EXECUTED, if task had a deadline and a
   parent, compute `deadline_met` bool (= executed_end ≤ deadline)
   and stash in a new `deadline_outcome` view or column.
5. New analytics endpoint: `GET /v1/analytics/deadline-shape` —
   per-user deadline-miss distribution stratified by scope bullet
   count at plan.

**Why P0:** this is the instrument for the refined thesis. Without
it, every other P0/P1 loop is ancillary.

---

## Prioritized execution plan (arising from this document)

**P0 — Build these first, in this order:**

1. **Loop 8** — Operator dashboard (2h). Gets retention visibility
   running so every subsequent ship can be measured against it.
2. **Loop 1** — Calibration nudge outcome log (2h). Cheap schema,
   closes the core calibration loop, pays back immediately for any
   user (including operator) on their next 5+ tasks.
3. **Loop 11** — Deadline + scope-bullet instruments (4h). The
   thesis-blocker. Not necessarily shipped to users yet — shipping
   the SCHEMA + parser first, then the UI + mirror as Phase 5.

**P1 — After P0 and before Phase 5:**

4. **Loop 4** — VT-17 acceptance visibility (2h).
5. **Loop 2** — Readiness-conditioned bias_factor (4h).
6. **Loop 5** — VT-21 stratified analysis endpoint (4h).

**P2 — When user volume justifies:**

7. **Loop 6** — Attendance weekly reflection (3h).
8. **Loop 7** — Canonical category suggestion (6h).
9. **Loop 3** — Archetype intake battery (12h+).

**Blocked / deferred:**

- Loop 9 (OpenClaw gating) — reframe VT-17 as in-app-only OR resolve
  operator-only constraint.
- Loop 10 (multi-timezone) — well-scoped, not urgent at single-region
  cohort.

**Total P0 effort: ~8 hours. Loop 1 + Loop 8 alone = 4 hours and
unblock two major research feedback paths.**
