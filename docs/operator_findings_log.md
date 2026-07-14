# Operator Findings Log

**Owner:** Operator (Ali)
**Paired tools:** `notebooks/operator_analytics.ipynb`, `docs/operator_interrogation_checklist.md`
**Status:** Append-only log. One entry per interrogation pass.

Each entry records what was expected, what was observed, what was
surprising, and which actions (if any) it triggers. Actions are one of:

- **(a) New dogfood item** — added to `docs/dogfood_findings_living.md`
  with a Pn priority.
- **(b) New validity threat (VT)** — added to `MANIFESTO.md §The
  Validity Register` with distinguishing analyses.
- **(c) Noted, not actionable now** — logged but not escalated.

A finding without an action is still a valid entry. "No signal yet"
answers belong here too — leaving a question unanswered silently is
what this log is designed to prevent.

---

## Entry template

Copy the block below for each pass. Fill in every field; use "n/a" or
"no signal yet" where appropriate. Do not delete unused sub-sections —
the structure is load-bearing.

```markdown
## Day {10|30|60|90} — {YYYY-MM-DD} — cohort: {operator|trusted|all}

**Notebook run:** `operator_analytics.local.ipynb` commit/sha: {sha or "working copy"}
**Window:** {start_iso} → {end_iso}
**n (tasks):** {count}
**n (users):** {count}

### Expected patterns

- {what I expected to see, before running the notebook}
- {...}

### Observed patterns

#### Delta
- {median / mean / skew / category breakdown summary}

#### Discrepancy
- {unstratified ρ, stratified ρ, sign-flip yes/no}
- VT-12a: {rho, p, interpretation}
- VT-12b: {readiness=5 variance finding}
- VT-12c: {readiness × category std cells of note}

#### Initiation delay
- {distribution summary, time-of-day/category findings}

#### Unplanned rate
- {overall %, trend direction}

#### Cascade
- {session_index_in_day correlation, chain counts}

#### Data quality
- {null rates of note, any 100%-default flags, stale PAUSED count}

### Surprises

- {findings I did not expect — this is the section future-me will read first}
- {...}

### Actions

- **(a)** {new dogfood item title + priority + one-line description}
  → added to `docs/dogfood_findings_living.md` §{section} as {LYR-xxx | new bullet}
- **(b)** {new VT identifier + hypothesis}
  → added to `MANIFESTO.md §The Validity Register` as VT-{n}
- **(c)** {noted-not-actionable observation}
  → reason for deferral: {one line}

### Questions for next milestone

- {questions the findings raised that the current checklist did not cover}
- {...}

---
```

---

## Day 18 — 2026-04-23 — cohort: all users

**Notebook run:** direct DB introspection (psql via docker-compose exec); no notebook, working SQL session
**Window:** all-time (first task 2026-04-09 → last 2026-04-23)
**n (tasks):** 86 total, 43 passing Rule 13 filters (u=1 operator only)
**n (users):** 9 total, 5 with ≥1 executed task, 4 with multi-task activity

### Expected patterns

- Shrinkage blend produces sensible predictions per cell for operator's 43-session history
- diffuse_average prior (1.30) within reasonable distance of operator's global ratio
- H1 readiness→delta signal directionally consistent with classic planning-fallacy
- Pause prediction calibration roughly tracks confidence bucket → observed hit rate
- VT-21 nudge engagement: users actually reading and acting on calibration_nudge / micro_mirror
- No integrity violations on executed_duration_minutes, planned_duration_minutes, timestamps

### Observed patterns

#### Delta
- Operator global sum-ratio = **1.220** (overrun 22%, n=43)
- Per-category ratios diverge strongly from RESEARCH_PRIORS:
  - `development` 1.43 vs prior 1.50 ← **close match** (Buehler 1994 validated here)
  - `work` 2.12 vs prior 1.45 ← **+0.67 drift** (tasks take 2× planned)
  - `study` 0.47 vs prior 1.40 ← **-0.93 drift** (finishes at half-plan)
  - `academic` 0.88 vs prior 1.40 ← **-0.52 drift**
  - `planning` 2.12 vs prior 1.20 ← **+0.92 drift**
- Hour-of-day (Cairo): overrun peaks 13–18h at 1.6–1.9×, best calibration 7h (0.57) and 19–21h (0.50–0.65). Classical afternoon-slump shape.

#### Discrepancy
- **VT-22 ρ(pre_task_readiness, signed_delta) = -0.288 (n=43)** ← directionally supports scope-inflation hypothesis: high readiness → MORE overrun, opposite of naive planning-fallacy. Not quite significant at α=0.05 (critical ~0.30) but pre-registered Rule 10.
- VT-12a ρ(readiness, planned_duration) = +0.059 ← instrument-entanglement weak. But mean planned_duration climbs monotonically with readiness (83→117→150 min from readiness 3→4→5), so ambition-scaling exists as a central-tendency pattern not captured by rank correlation.
- VT-12b: readiness=5 cell has n=8 with mean_bf=0.841 — drops below 1.0 (UNDER plan), different shape from readiness=3/4 (overrun).
- VT-12c: not computed this pass (skipped — category × readiness cell counts too sparse for u=1's n).

#### Initiation delay
- u=1 has zero tasks with `initiation_status='live'` AND `initiation_delay_minutes IS NOT NULL` — the 'live' bucket is effectively empty for delay analysis. Most operator tasks have null initiation_status (pre-LYR-097 legacy).
- Task-creation-vs-planned-start lag by category reveals retroactive-logging pattern: `development` -0.7h (logged AFTER start), `health` -3.3h (hours after start), `academic` +3.2h (planned ahead). Operator logs dev/health retroactively, plans academic/study proactively.

#### Unplanned rate
- Skip rate by category (u=1): `study` **56%** (5/9), `academic` 27%, `health` 25%, `development` 17%, `work` 9%, `planning` 0%.
- **Study commitment failure** — over half of study tasks skipped, and the ones that execute finish at 47% of planned. The category is structurally under-committed.

#### Cascade
- Not computed this pass — session_index_in_day distribution not pulled. TODO next pass.

#### Data quality
- Planned/executed timestamp pairs clean: 0 inverted intervals, 0 missing executed_* on EXECUTED/non-voided.
- **5 stuck-open pause_events (u=1)** where session closed but resumed_at_utc still NULL. 4 from single evening 2026-04-15 (all external_interruption), 1 recent 2026-04-22 (distraction, 121-min gap). Class-of-bug: stopwatch close path doesn't close open pause_event.
- **1 negative-duration pause event (u=5, -12.02 min)** — resumed_at_utc 23:10 < paused_at_utc 23:22. Single row but exposes a gap: no write-time invariant check for `resumed ≥ paused`.
- **calibration_nudge dwell_seconds outlier: 12,072s (3.35 hours)** — dwell timer counts AFK/tab-hidden time. Mean-engagement metric contaminated.
- **Rule 13 filter drift:** endpoint uses `planned_duration_minutes > 0` instead of pre-registered `>= 5`. **Zero tasks affected today** (no 1–4-min planned tasks exist), but pre-registration divergence is real and waiting to trigger.
- **bias_factor_service.blend() crashes on unfiltered caller input** — `_bias_cell` does `sum(e for _, e in rows)` which raises TypeError if any row has None executed_duration_minutes. Endpoint filters upstream so it hasn't triggered in prod, but the service contract is brittle.
- 78 voided tasks: 60+ are explicit test/QA cleanups (`test_contamination` ×34, `dogfood test session` ×9, etc.) — intentional use of voiding, healthy.

#### Pause-prediction accuracy (operator, n=5)
- **Calibration by bucket:** 50–59% → 0/1 hits (observed 0%); 60–69% → 3/4 hits (observed 75%).
- Directionally consistent with confidence-calibration working: low-conf bucket underperforms, high-conf bucket matches or slightly over-performs prediction.
- n too small for conclusions. The 58% miss had sample_size=5 (smallest n among the 5 firings), consistent with "lower n → lower confidence → lower hit rate."
- Zero `self_reported_retroactively=TRUE` pause_event rows across ALL users — LYR-102 retroactive chip flow is code-complete but untested in the wild (operator did click Yes on two chips today, which should have stamped the flag — worth verifying whether the write path sets it).

#### Reflection-surface engagement (VT-21 input)
- **micro_mirror: 95% dismissal rate of viewed firings (20/21), avg_dwell 6.6s** — glance-and-dismiss. Across u=1/u=4/u=5/u=6 the dismissal pattern is uniform: every user who viewed one dismissed it.
- calibration_nudge: 54% dismissal of viewed, avg_dwell 1939.9s (heavily skewed by the 12,072s outlier; median dwell is closer to 70–100s which IS meaningful engagement).
- **Implication:** micro_mirror is not delivering value at current design. Either redesign or kill.

#### Archetype
- 1/9 users have taken the survey (u=1, self-classified as `diffuse_average` via skip-path default — actually completed=TRUE with intermediate chronotype + z=+0.28). u=4/5/6 have no ArchetypeAssignment row and presumably default to `diffuse_average` in `blend()` via the "no archetype_id" fallback.
- No duplicate assignments. User.archetype_id agrees with latest completed assignment (1 row checked).

### Surprises

- **VT-22 scope inflation landed its first empirical signal.** ρ=-0.29, directionally wrong-sign for naive H1, pre-registered under Rule 10 post April 17. At n=43 this is not significant but it's the right direction and the effect size is substantial. If the pattern holds to n=100 it becomes the dominant signal.
- **Study category is a structural outlier.** Not just overruns — *under*runs AND half-skip-rate. The operator's study blocks are both over-scheduled in count and under-executed in time. This is an emergent signal the insight layer should surface.
- **Afternoon-slump shape is clean.** 13–18h overrun 1.6–1.9×; early morning and late evening 0.5–0.65. The operator is a `diffuse_average` per the survey but the HOUR×BF pattern looks more like a disciplined-owl-with-afternoon-dip — suggests the chronotype scoring from MEQ may not fully capture time-of-day calibration.
- **RESEARCH_PRIORS drift is large per-category.** `work` +0.67, `study` -0.93, `planning` +0.92 vs pre-registered priors. For a n=4–7 sample size these drifts could be noise, but they all exceed the archetype prior's own σ (0.30 for diffuse). Exposes a real question: are the operator's category labels semantically aligned with the published studies' category definitions?
- **Shrinkage can mislead at small n with off-prior behavior.** Operator's `study` observed is 0.47 but blended prediction for 60-min study/morning is 1.277 — **2.7× higher than their actual pattern**. The pre-registered shrinkage formula is behaving exactly as designed (pw=0.13 at n=4), but the UX cost for this user in this category is real until n reaches ~20–30.

### Actions

- **(a)** Stuck-open pause_event on session-stop — close any open pause_event with `resumed_at_utc = session.end_time_utc`, compute `duration_minutes`
  → added to `docs/dogfood_findings_living.md` §P1 (see new LYR-105)
- **(a)** Negative-duration pause integrity guard — reject writes where `resumed_at_utc ≤ paused_at_utc`, log with prior session context
  → added to `docs/dogfood_findings_living.md` §P1 (LYR-106)
- **(a)** Rule 13 filter drift — change endpoint `planned_duration_minutes > 0` → `>= 5` to match pre-registration; no MANIFESTO amendment needed
  → added to `docs/dogfood_findings_living.md` §P0 Tier 2 (LYR-107)
- **(a)** `bias_factor_service.blend()` defensive filter — pre-filter task list inside the service; document caller contract; add assert/test
  → added to `docs/dogfood_findings_living.md` §P2 (LYR-108)
- **(a)** `calibration_nudge` dwell contamination — gate dwell timer via Page Visibility API (pause on tab hidden). VT-21 metric integrity depends on this
  → added to `docs/dogfood_findings_living.md` §P1 (LYR-109)
- **(a)** `micro_mirror` 95% dismissal — redesign or deprecate. Not delivering engagement signal at current shape. Candidate for killswitch + post-mortem
  → added to `docs/dogfood_findings_living.md` §P1 (LYR-110)
- **(b)** VT-26 category-semantics drift — pre-register that RESEARCH_PRIORS assumes user-defined category labels map cleanly to published-study category semantics. For users whose labels don't match, shrinkage toward research prior is actively wrong at small n. Distinguishing analyses: compare `personal_weight`-weighted prediction MAE across users with n≥30 per category vs n<10 per category; if small-n shows systematic MAE inflation in specific categories, label-semantic drift confirmed.
  → added to `MANIFESTO.md §The Validity Register` as VT-26
- **(b)** VT-27 pause-predictor calibration — pre-register threshold analysis: confidence-bucket hit rate must track predicted probability within ±10pp at n≥30 firings per bucket. Kill-criterion: if 50–59% bucket observes <30% hit rate and 70–79% bucket observes >80% at n≥30, the confidence function miscalibrates.
  → added to `MANIFESTO.md §The Validity Register` as VT-27
- **(c)** Afternoon-slump hour-of-day pattern — noted but needs more data before insight-card candidate; operator's intermediate chronotype + hour×BF pattern is suggestive not conclusive
  → reason for deferral: n=1 user; signal needs cross-user validation
- **(c)** RESEARCH_PRIORS drift per category — noted but small n per cell; shrinkage will handle as n grows
  → reason for deferral: pre-registration locks priors; shrinkage is the designed response
- **(c)** Survey adoption rate (1/9 users) — noted; retrofit banner is the adoption channel for existing users, new users hit the gate
  → reason for deferral: expected — survey shipped 24h ago, adoption tracked over trusted-user week

### Questions for next milestone

- At what n does `personal_weight` dominate enough to correct the `study`-category prediction for u=1? (Rule 13 specifies `n_sessions_in_cell / 30`; at current 3 tasks/week in study, that's ~10 weeks to pw=1.0.)
- Does the afternoon-slump shape replicate for u=2/u=4/u=5/u=6 once they accumulate comparable data?
- Does the VT-22 ρ(readiness, signed_delta) hold its sign as n grows past 100?
- Does micro_mirror redesign or removal affect calibration_nudge engagement (spillover effect)?
- Do the 5 stuck pause_events inflate VT-17 acceptance-window analysis? (Need reconciliation job audit for self-reported-retroactively path.)

---

## Standing rules

1. **Entries are append-only.** If a past finding is wrong, add a new
   entry that corrects it. Do not edit prior entries in place.
2. **Every checklist question has an answer in the corresponding
   "Observed patterns" sub-section.** Missing sub-sections mean the
   question was silently skipped — which is the failure mode this log
   exists to prevent.
3. **Actions reference their destination.** An (a) action that does not
   name the file + section it was added to is incomplete.
4. **n counts are mandatory.** Every pass records both task count and
   user count. Kill-criterion decisions depend on n.
5. **New questions go to the checklist, not the log.** If a pass raises
   a question worth asking again, add it to the next milestone section
   of `docs/operator_interrogation_checklist.md` — not retroactively to
   the current one.

## References

- `docs/operator_interrogation_checklist.md` — the question list
- `notebooks/operator_analytics.ipynb` — the tooling
- `docs/dogfood_findings_living.md` — where (a) actions land
- `MANIFESTO.md §The Validity Register` — where (b) actions land
- `docs/archive/legacy/planning/building_phases.md` §Phase 5 / 5.5 — milestone gates

---

## Day 12 — 2026-04-29 — cohort: trusted (n=7)

### Expected

Pre-launch sprint check on the trusted cohort to validate that the
re-onboarding gate (commit `67fa1fd`) applies correctly and that the
Apr 28 brain-dump rewrite hasn't lost any active users.

### Observed

Retention pull on the 7 trusted users:

| uid | email | signup | days | onb | tasks | exec sessions | days active | last seen |
|---|---|---|---|---|---|---|---|---|
| 3 | mariamnasser415 | 4/16 | 12 | ❌ | 0 | 0 | 0 | never |
| 4 | ghadatawfik85 | 4/16 | 12 | ✅ | 3 | 3 | 2 | 6d ago |
| 5 | t90seegg2006 | 4/17 | 11 | ✅ | 3 | 4 | 3 | today |
| 6 | medo.tamer1610 | 4/17 | 11 | ✅ | 11 | 11 | 4 | 3d ago |
| 7 | meroo0jj | 4/18 | 10 | ✅ | 3 | 1 | 1 | 2d ago |
| 12 | omar4reading | 4/22 | 6 | ✅ | 1 (SKIPPED meta-task) | 0 | 0 | never |
| 14 | pbassem04 | 4/23 | 5 | ✅ | 1 (SKIPPED meta-task) | 0 | 0 | never |

Aggregates (n=7):
- Onboarded: 6/7 (86%)
- D1 return stamp: **0/7 (0%)** — measurement bug, not behavior signal
- Multi-active (≥2 distinct executed days): 3/7 (43%) — ghada, t90seegg, medo
- Active in last 7d: 4/7 (57%) — same 4 + meroo

### Surprising

1. **D1 return stamp = 0 across the board.** The `d1_return_at` stamp
   logic in `endpoints/users.py` should fire on the first /me call
   ≥24h after signup. Multi-active and last-seen data confirm real
   returners exist (ghada, t90seegg, medo, meroo) so the stamp is
   broken, not the behavior. Action (a) — added to dogfood_findings_living.
2. **Two onboarded-never-executed users** (omar Day 6, pbassem Day 5)
   match the "onboarded but never logged a real task" failure mode
   the operator named. Their only "task" is the SKIPPED legacy "Plan
   your week" meta-task from the pre-rewrite onboarding.
3. **medo.tamer is the power user** (11 sessions, 4 active days, last
   3d ago). His engagement profile is what we'd want to be modal for
   the cohort.

### Actions taken in this pass

- Hard-deleted user_id 3, 12, 14 via the existing `retain_for_research=
  False` sequence (no useful behavioral data to retain). Operator will
  reach out to invite them to sign up fresh under the rewritten brain-
  dump onboarding.
- Shipped the **re-onboarding gate** (commit `67fa1fd`): /me returns
  `has_active_task_history` (count of non-voided non-SKIPPED non-
  DELETED tasks > 0); `(app)/layout.tsx` re-shows the brain-dump
  whenever this flag is false. Future pbassem/omar-style cases get
  the brain-dump again automatically; no manual deletion needed.

### Bugs encountered + documented this pass

- **LYR-113** — Google OAuth login broken on every cold-restart.
  Recurring P0; this was the third occurrence of the same symptom.
  Fixed at the Node-flag layer (`--no-network-family-autoselection`
  Node 20.4+). Documented in LYRA_BUGS.md with full incident timeline
  and drop-when conditions.
- **D1 stamp logic** — confirmed broken across all 7 trusted users
  despite real returners. Root cause TBD; likely a tz-naive vs tz-
  aware datetime comparison issue (parallel to LYR-103/H0 hotfix
  family). Action (a) — opening as a dogfood item.

### Out of scope, but worth noting

- Operator landed on the conclusion that **bug rate is too high this
  session**: "DOCUMENT THE BUGS, they should not happen this often."
  Three P0s within 24h (LYR-113 OAuth, the Apr 28 tz hotfix family,
  and the brain-dump default-time-in-past edge case). Pattern: each
  was caused by an environment assumption (IPv6 reachable, datetime
  naive matches DB, server clock matches user clock) that had only
  been verified once. Going forward: every environment assumption
  documented in agent bootstrap doc or memory must have a verification command
  the operator can run before declaring "fixed."
