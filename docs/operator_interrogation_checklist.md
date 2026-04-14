# Operator Interrogation Checklist

**Owner:** Operator (Ali)
**Paired tools:** `notebooks/operator_analytics.ipynb`, `docs/operator_findings_log.md`
**Status:** Canonical. Run at Day 10 / 30 / 60 / 90 of the Phase 5 trusted-user window.

This checklist exists because ad-hoc CSV review causes silent signal loss.
Every milestone below is a fixed list of questions to run through the
notebook helpers. Findings are written to the findings log, not carried
in memory. If a question stops being informative, delete it here — do not
silently skip it.

Each question names the notebook cell(s) that answer it. Lower-alpha labels
(e.g. VT-12a) cross-reference validity threats defined in `MANIFESTO.md §The
Validity Register`.

---

## Day 10 — smoke-test the instrument, not the hypothesis

Goal: confirm the pipeline captures what it claims to capture. Nothing about
H1 should be inferred from a 10-day window; these questions are instrument
integrity checks.

### Delta (planned − executed duration)

- [ ] What is the median, mean, and IQR of `duration_delta_minutes`?
      → Cell C on `duration_delta_minutes`.
- [ ] Does the delta skew systematically positive or negative across all tasks?
      → compare mean vs median; > |5 min| separation suggests a long tail.
- [ ] Does the delta differ by category?
      → Cell C stratified by `category`; also a groupby agg.
- [ ] Are there categories where > 80% of tasks are off-plan by > 10 min?
      That is a bias_factor candidate signal, not noise.

### Discrepancy (pre_task_readiness vs post_task_reflection)

- [ ] What is the Spearman ρ between `signed_discrepancy` and
      `duration_delta_minutes`, unstratified and stratified by category?
      → Cell D. **Do not** treat this as H1 evidence at n<60.
- [ ] **VT-12a:** Is `pre_task_readiness` correlated with
      `planned_duration_minutes`? (Motivated underestimation — users may plan
      shorter sessions on low-readiness days.) → starter cell under
      "Discrepancy" in the notebook.
- [ ] **VT-12b:** At `pre_task_readiness = 5`, has variance of
      `duration_delta_minutes` collapsed? (Ceiling saturation.)
- [ ] **VT-12c:** Does the readiness × category cross-tab show any cell with
      near-zero variance? → pivot_table + std on the notebook.

### Initiation delay

- [ ] What is the distribution of `initiation_delay_minutes`?
      → Cell C.
- [ ] Is there a time-of-day or category pattern? → Cell F heatmap.
- [ ] Are there delays > planned_duration_minutes (started later than the task
      would have ended if started on time)? Count and list.

### Unplanned rate

- [ ] What share of tasks have `source = 'unplanned'` or `unplanned_reason`
      populated?
- [ ] Is that share stable across the 10 days or drifting up?
      → Cell E on a boolean `is_unplanned` column.
- [ ] Is the unplanned rate correlated with day-level delta?
      (Do unplanned-heavy days also run over on other tasks?)

### Cascade

- [ ] Does `session_index_in_day` correlate with `duration_delta_minutes`?
      → Cell G + a groupby.
- [ ] Are there days with a clear "slippage staircase" — each later task
      further over plan than the one before?
- [ ] How many `parent_task_id` chains exist, and how deep? (Interruption
      visualization ships Phase 6 — this is an early count.)

### Data quality

- [ ] For every research-relevant field (`pre_task_readiness`,
      `post_task_reflection`, `initiation_delay_minutes`, `pause_count`,
      `ss_pause_reason`, `ss_pause_initiator`,
      `ss_task_completion_percentage`, `unplanned_reason`, `category`,
      `reschedule_count`): what is the null rate? → last cell in the
      Day 10 block.
- [ ] Is any field populated 100% with the same value? That flags a
      silent default (see `docs/do_not_add.md §Hardcoded default values`).
- [ ] Are there `state = 'EXECUTED'` tasks missing
      `executed_duration_minutes`? Those are auto-close or crash artefacts
      — count and investigate.
- [ ] Are any tasks in `PAUSED` state older than 12h? Stale-session sweeper
      should have closed them.

### Notification and override patterns

- [ ] Conflict detection override rate per gate (Gate 1 active overlap,
      Gate 2 non-voided overlap, Gate 3 duplicate-title soft warning).
      → per-user per-week `overrides / (overrides + cancels)`. Flag any
      gate exceeding 0.5.
- [ ] Distribution of override reasons logged — are reasons clustering
      (e.g. "intentional overlap for split focus") or heterogeneous?
- [ ] Pause-prediction response rate — `pause_now` / `snooze` / `dismiss`
      / no-response breakdown per user per mechanism (clock-anchor vs
      work-rhythm). VT-17 kill criterion runs at end-of-week-1 per user.
- [ ] Micro_mirror dismissal rate — fraction of stops where the toast
      fired and was dismissed vs allowed to auto-expire (proxy for
      attention).
- [ ] Calibration-nudge accept vs dismiss ratio (per gate: creation-time
      nudge vs stop-time nudge).
- [ ] Cold-start engagement curve — for each user, locate the first >24h
      gap in session logging. Record session count at gap and classify
      app-facing vs life-facing cause. Cross-refs
      `docs/dogfood_findings_living.md §Cold-start engagement decay
      analysis`.

**Exit criterion for Day 10:** every question above has been answered in
the findings log. Answers may be "no signal yet" — that is still a logged
answer, not a skipped question.

---

## Day 30 — does the instrument separate users from each other?

At n ≈ 30 sessions per user, cohort contrasts become meaningful. H1 is
still not the question. Archetype fit and readiness-scale behavior are.

- [ ] Compare delta, discrepancy, and initiation-delay distributions across
      users. Are there two clearly different populations, or is it one cloud?
- [ ] Which users' `pre_task_readiness` distribution is visibly narrower
      (potential scale-saturation or disengagement)?
- [ ] Does `post_task_reflection` show the same narrowness? If pre is narrow
      and post is wide, the user is measuring but not planning; if both are
      narrow, the scale is not usable for that user.
- [ ] Re-run every Day 10 question per-user. Surprises that were invisible
      in aggregate often live here.
- [ ] **VT-13 (category-type semantic drift):** split categories into
      estimable vs time_anchored (see `docs/do_not_add.md` + building_phases).
      Does bias_factor separate cleanly on that boundary?
- [ ] Has any user reached ≥10 sessions in a category with
      `|bias_factor - 1| ≥ 0.25`? That is the calibration_nudge trigger
      threshold — check whether the nudge fired and how the user responded.

### Progressive revelation engagement

- [ ] Archetype reveal timing — did users engage with the reveal when
      archetype surfaced at session 5–7 (Phase 5 pre-alpha)? Dwell time
      on the reveal banner, whether they opened `/insights` after.
- [ ] Reclassification frequency — how often does the session-15–20
      check result in a reclassification prompt firing? For users who
      saw the prompt: accept / reject / dismiss breakdown.
- [ ] Confidence-tier transition engagement — when bias_factor moves
      low → medium or medium → published, does the surfacing attract
      engagement (dwell, follow-through click to `/insights`)?

---

## Day 60 — H1 pre-registered primary analysis

This is the milestone at which H1 has sufficient n. Protocol is frozen to
prevent post-hoc choice.

- [ ] Compute Spearman ρ between `signed_discrepancy` and
      `duration_delta_minutes` with n ≥ 60 per user.
- [ ] Kill criterion: if n ≥ 60 and ρ < 0.20, H1 fails for that user.
- [ ] Report unstratified ρ and category-stratified ρ side by side.
      Report whichever is smaller as the headline — do not cherry-pick.
- [ ] Include VT-12a / VT-12b / VT-12c distinguishing analyses alongside
      the primary. Without them the ρ is not interpretable.
- [ ] Per-category `bias_factor` stability: is it drifting monotonically
      across the 60 days, or has it plateaued?
- [ ] Initiation-delay trend: is the user's own delay shrinking over time
      (learning effect), or stable (true baseline)?
- [ ] Cascade chain depth over time: are longer chains appearing, and do
      they correlate with low-readiness days?

---

## Day 90 — retention decision + Phase 6 input

At Day 90 the retention-architecture question is answerable. Phase 5.5
gates shipping Phase 6 on:

- (a) ≥50% week-3 session frequency
- (b) ≥40% readiness-populated planning engagement
- (c) qualitative mirror-engagement signal on ≥6/10 users

- [ ] Compute (a) and (b) directly from the dataframe. Flag any user who
      crossed the threshold at Day 30 but has since dropped below.
- [ ] For (c), pull every `reflection_view_log` event for each user
      (once the table ships) and classify dwell/dismiss patterns by the
      four user-response types (Calibrator / Acknowledger / Illusion
      Preserver / Overcorrector — see `docs/phase_6_architecture_backlog.md`).
- [ ] Which V1/V3/V5 composite signals are strong enough to drive the
      Phase 6 router? List signals by discrimination quality, not by the
      order they appear in the backlog.
- [ ] For churned users: what was the last session they logged, what was
      the delta, what was the reflection? Churn does not always follow a
      bad session — document what it does follow.
- [ ] Which questions from Day 10 have become redundant? Delete them from
      this checklist before the next cycle — do not keep dead questions.

---

## Standing rules

1. **Every question produces an answer in the findings log, even "no
   signal yet."** Unanswered questions become invisible; logged nulls do
   not.
2. **Sample size guards are not optional.** n < 60 means "no H1 inference,"
   full stop. Record counts in the log even for exploratory questions.
3. **Stratified analyses come paired with the unstratified baseline.** If
   the baseline and stratified ρ disagree in sign, that is the finding —
   write it up.
4. **New questions always go in the next-milestone section.** Do not
   retroactively add questions to Day 10 after Day 30 has been run; that
   is post-hoc selection masquerading as checklist design.
5. **A finding is a finding only when it is in the log.** In-notebook
   observations that never reach `docs/operator_findings_log.md` do not
   exist.

## References

- `MANIFESTO.md` §The Validity Register — VT-1 through VT-16
- `docs/building_phases.md` §Phase 5 / Phase 5.5 gate
- `docs/phase_6_architecture_backlog.md` §D2, D3, D6, readiness-drift,
  interruption-chain visualization
- `docs/do_not_add.md` §Hardcoded default values, §Gamification
- `notebooks/operator_analytics.ipynb` — the notebook that runs each question
- `docs/operator_findings_log.md` — where answers live
