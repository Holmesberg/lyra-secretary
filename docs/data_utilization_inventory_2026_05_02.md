# Data Utilization Inventory — 2026-05-02

*Source of truth for the 2026-05-02 system transition. Every signal Lyra collects (or could derive) classified into 5 categories with 4 actionable dispositions. Phase 1 of the transition plan (`/home/alina/.assistant runtime/plans/alright-listen-up-assistant runtime-delegated-garden.md`). Phase 2 (JARVIS soak) does not start until operator signs off on this disposition table.*

---

## Methodology + Counts

Five sequential Explore passes (2026-05-02) inventoried collected vs reflected data:

| Pass | Layer | Found |
|------|-------|-------|
| 1 | DB columns across 17 tables | 24 DARK + 5 derivable-dark = 29 |
| 2 | Backend API reflection layer (10 derived endpoints) | 7 unconsumed by frontend |
| 3 | Frontend UI reflection (16 surfaces) | 11 high-value signals never displayed |
| 4 | Cross-table joins + Redis state + jarvis_invocation tool_args + scheduler state | +36 (43 DARK + 22 derivable-dark) |
| 5 | Journey-side implicit signals at 21 stages | +131 |
| 6 | Transition-topology pass (post-ChatGPT reframe) | +12 named patterns |
| **Total** | **≥ 208 dark/implicit/derivable signals** |

**The count is a floor, not a ceiling.** Column-counting is finite; transition-topology is combinatorial. The discipline is *inventory accounting*, not *inventory completeness* — once we ask "what implicit choice does the user make at each transition," the inventory grows structurally.

## Classification Categories

| Category | Definition |
|----------|------------|
| **REFLECTED** | Already surfaces back to the user via UI (micro_mirror, /insights, calibration_nudge, archetype card) with confidence framing |
| **OPERATOR-ONLY** | Analytics or research consumption only — intentionally not user-facing per VT-15/VT-16 cross-population separation |
| **DARK** | Written, never read by any analytics or UI |
| **DERIVABLE-DARK** | Computable from existing data, no derivation code exists |
| **NOT-INSTRUMENTED** | Implicit signal exists in the moment (typing duration, modal dwell, reason-pick latency) but no capture exists |

## Dispositions

| Disposition | Phase | Action |
|-------------|-------|--------|
| **SURFACE** | Phase 4 | Reflect to non-operator users via UI with calibrated confidence per `docs/calibration_contract.md` |
| **PROMOTE-TO-JARVIS** | Phase 2 | Expose via `query_dark_columns` tool for operator-side hypothesis exploration; not yet ready for user-facing reflection |
| **RETIRE** | Phase 5 | Remove the writer (column kept for history); not promoted, not surfaced |
| **INSTRUMENT** | Phase 6 | Add lightweight capture via ReflectionViewLog `telemetry_*` namespace (top 5 only) |
| **NO-ACTION** | — | Already correctly REFLECTED or correctly OPERATOR-ONLY; no transition work needed |

---

## §1 — DB Column Triage (per table)

### Task table

| Column | Class | Disposition | Rationale |
|--------|-------|-------------|-----------|
| `planned_duration_minutes` | REFLECTED | NO-ACTION | Surfaced via micro_mirror, /insights |
| `executed_duration_minutes` | REFLECTED | NO-ACTION | Same |
| `duration_delta_minutes` (derived) | REFLECTED | NO-ACTION | Surfaced |
| `initiation_delay_minutes` | REFLECTED | NO-ACTION | Surfaced via /insights initiation_delay generator |
| `initiation_status` | REFLECTED | NO-ACTION | Surfaced |
| `pause_count` | REFLECTED | NO-ACTION | Surfaced via micro_mirror, /table |
| `pre_task_readiness` | REFLECTED | NO-ACTION | Surfaced |
| `post_task_reflection` | REFLECTED | NO-ACTION | Surfaced |
| `discrepancy_score` (derived) | REFLECTED | NO-ACTION | Surfaced via /insights discrepancy generator |
| `signed_discrepancy` (derived) | OPERATOR-ONLY | NO-ACTION | Research H1 substrate |
| `category` | REFLECTED | NO-ACTION | Surfaced |
| `state` | REFLECTED | NO-ACTION | Surfaced |
| `parent_task_id` | OPERATOR-ONLY | PROMOTE-TO-JARVIS | Interruption-tree topology — generalizable primitive (context-switch cost) |
| `replaces_task_id` / `replaced_by_task_id` | OPERATOR-ONLY | PROMOTE-TO-JARVIS | Substitution chains — generalizable primitive (abandonment-path) |
| `reschedule_count` | DARK | SURFACE | Schedule volatility primitive — display "you've shifted this 3× this week" at confidence ≥ tentative |
| `scope_bullet_count_at_plan` | OPERATOR-ONLY | PROMOTE-TO-JARVIS | Scope inflation hypothesis (Rule 12) — keep for VT-22 mediation |
| `scope_bullet_count_at_execute` | DARK | PROMOTE-TO-JARVIS | Scope drift signal; expose to JARVIS for operator-side validation |
| `llm_parse_status` | OPERATOR-ONLY | NO-ACTION | Internal pipeline state |
| `llm_priority` | DARK | RETIRE | Dead code path — column receives writes but `task.priority` doesn't exist (commented at `tasks.py:553`); retire writer until priority col ships |
| `llm_inferred_deadline_id` / `llm_deadline_candidates` | OPERATOR-ONLY | NO-ACTION | Surfaced as binding chip |
| `deadline_match_source` / `deadline_match_confidence` | OPERATOR-ONLY | PROMOTE-TO-JARVIS | Auto-bind volatility hypothesis (per Pass 2 §5) |
| `voided_at` / `voided_reason` | OPERATOR-ONLY | NO-ACTION | Filter discipline per `feedback_voided_at_guard` |
| `post_deletion_retained_at` / `original_user_id_hash` | OPERATOR-ONLY | NO-ACTION | Anonymization substrate |
| `session_index_in_day` | OPERATOR-ONLY | PROMOTE-TO-JARVIS | Day-position effects — generalizable (cascade primitive) |
| `notion_page_id` | OPERATOR-ONLY | NO-ACTION | Sync mechanism only |
| `unplanned_reason` / `interruption_type` / `source` | OPERATOR-ONLY | PROMOTE-TO-JARVIS | Source-channel hypothesis (does brain dump vs modal vs OpenClaw produce different outcomes?) |
| `last_modified_at` | DARK | DERIVABLE-DARK → PROMOTE-TO-JARVIS | Edit cadence primitive |

### StopwatchSession table

| Column | Class | Disposition | Rationale |
|--------|-------|-------------|-----------|
| `total_paused_minutes` | REFLECTED | NO-ACTION | Surfaced |
| `pause_reason` (denormalized) | OPERATOR-ONLY | SURFACE | **High-value primitive.** Per pause_event canonical; surface aggregate distribution per (category, time_of_day) |
| `pause_initiator` (denormalized) | OPERATOR-ONLY | SURFACE | Self-vs-external attribution — actionable primitive |
| `paused_at_utc` | OPERATOR-ONLY | DERIVABLE-DARK → SURFACE | Recovery-latency computation source |
| `original_pre_task_readiness` | DARK | PROMOTE-TO-JARVIS | Readiness drift signal — operator-side first |
| `task_completion_percentage` | DARK | PROMOTE-TO-JARVIS | Mid-task vs final completion variance — primitive but needs operator-side validation |
| `auto_closed` | DARK | PROMOTE-TO-JARVIS | Recovery-job differential — does it predict re-engagement? |
| `end_time_utc` / `start_time_utc` | OPERATOR-ONLY | DERIVABLE-DARK → SURFACE | wall_clock_minutes property exists but unused — pause overhead per category |
| `data_quality_flag` | OPERATOR-ONLY | NO-ACTION | Analytics filter |
| `wall_clock_minutes` (derived property) | DARK | SURFACE | Pause overhead = (wall_clock − executed) / wall_clock — generalizable primitive |

### PauseEvent table

| Column | Class | Disposition | Rationale |
|--------|-------|-------------|-----------|
| `pause_reason` | OPERATOR-ONLY | SURFACE | **Top-priority surface.** Pause-reason distribution per category × time-of-day = highest-value Phase 4 win |
| `pause_initiator` (self vs external) | OPERATOR-ONLY | SURFACE | Self-vs-external attribution primitive |
| `paused_at_utc` / `resumed_at_utc` / `duration_minutes` | OPERATOR-ONLY | DERIVABLE-DARK → SURFACE | Recovery latency by pause_reason — primitive |
| `active_elapsed_at_pause_seconds` | DARK | PROMOTE-TO-JARVIS | When-in-task pause timing (early vs late) — operator-side first |
| `self_reported_retroactively` | OPERATOR-ONLY | NO-ACTION | VT-17d analysis |

### PausePredictionLog table

| Column | Class | Disposition | Rationale |
|--------|-------|-------------|-----------|
| `user_response` / `response_at` | OPERATOR-ONLY | NO-ACTION | VT-17 acceptance-rate substrate |
| `mechanism` (clock_anchor vs work_rhythm) | DARK | PROMOTE-TO-JARVIS | Mechanism differential — does one type predict better? Operator-side first |
| `confidence` | DARK | PROMOTE-TO-JARVIS | Confidence calibration check — operator-side hypothesis |
| `lead_minutes` / `sample_size` | OPERATOR-ONLY | NO-ACTION | VT-17 substrate |
| `active_task_id` | DARK | PROMOTE-TO-JARVIS | Context-anchor — was the prediction firing on a known-pause-prone task? |
| `parent_firing_id` (snooze chain) | DARK | PROMOTE-TO-JARVIS | **Snooze-chain analysis** — multi-rejection then accept = engagement primitive |

### ResumePredictionLog table

| Column | Class | Disposition | Rationale |
|--------|-------|-------------|-----------|
| All response/mechanism/confidence/sample_size | DARK | PROMOTE-TO-JARVIS | Sibling of VT-17; sample size below floor for surfacing. Operator-side validation first |

### CalibrationNudgeEvent table

| Column | Class | Disposition | Rationale |
|--------|-------|-------------|-----------|
| `suggested_duration_minutes` / `user_planned_duration_minutes` / `user_decision` / `bias_factor` / `sample_size` | OPERATOR-ONLY | NO-ACTION | Loop 1 research substrate |
| `executed_duration_minutes` / `resolved_at` | OPERATOR-ONLY | NO-ACTION | Outcome reconciliation |
| `voided_at` | OPERATOR-ONLY | NO-ACTION | Filter discipline |

### ReflectionViewLog table

| Column | Class | Disposition | Rationale |
|--------|-------|-------------|-----------|
| `reflection_type` / `payload` / `fired_at` | OPERATOR-ONLY | NO-ACTION | VT-21 stratification + history substrate |
| `viewed_at` / `dismissed_at` | OPERATOR-ONLY | NO-ACTION | Engagement audit |
| `dwell_seconds` | DARK | PROMOTE-TO-JARVIS | Distribution per reflection_type — operator-side validation; potential SURFACE post-validation |
| `outcome` (kept/adjusted/dismissed) | DARK | SURFACE | Per-category nudge acceptance — calibration_nudge basis line on new-task-modal |

### Deadline table

| Column | Class | Disposition | Rationale |
|--------|-------|-------------|-----------|
| `title` / `due_at_utc` / `state` / `completed_at` | OPERATOR-ONLY | NO-ACTION | Loop 11 research substrate |
| `external_source` / `external_id` / `imported_at` | OPERATOR-ONLY | NO-ACTION | VT-29 filter |
| `voided_at` | OPERATOR-ONLY | NO-ACTION | Filter discipline |

### TaskDeadlineOutcome table

| Column | Class | Disposition | Rationale |
|--------|-------|-------------|-----------|
| `deadline_met` / `delay_minutes` / `computed_at` | OPERATOR-ONLY | NO-ACTION | Phase H/I deferred research |

### Archetype + ArchetypeAssignment tables

| Column | Class | Disposition | Rationale |
|--------|-------|-------------|-----------|
| `archetype_id` (assignment) | REFLECTED | NO-ACTION | Surfaced via archetype card |
| Survey scores (`meq`, `bfi_c`, `bscs`, `gp`) | OPERATOR-ONLY | NO-ACTION | Research substrate |
| `completed` / `skipped_at` / `raw_responses` | OPERATOR-ONLY | NO-ACTION | Re-fitting substrate |

### User table

| Column | Class | Disposition | Rationale |
|--------|-------|-------------|-----------|
| `timezone` / `terms_accepted_at` / `research_consent_at` / `onboarding_completed_at` | OPERATOR-ONLY | NO-ACTION | Population filtering |
| `archetype_id` | REFLECTED | NO-ACTION | Surfaced |
| `first_task_at` / `first_timer_started_at` | OPERATOR-ONLY | NO-ACTION | North Star |
| `d1_return_at` | OPERATOR-ONLY | NO-ACTION | North Star (currently broken per operator log Day 12) |
| OAuth tokens (`google_refresh_token`, `moodle_*`) | OPERATOR-ONLY | NO-ACTION | Credentials |
| `moodle_last_synced_at` / `moodle_disconnect_reason` | OPERATOR-ONLY | DERIVABLE-DARK → PROMOTE-TO-JARVIS | Sync-latency-drift signal — operator-side first |
| Integration `connected_at` (MISSING column) | NOT-INSTRUMENTED | INSTRUMENT (deferred) | Integration order is a high-value onboarding fingerprint; needs explicit timestamp column. Defer until cohort scaling. |

### ExternalEventOutcome table

| Column | Class | Disposition | Rationale |
|--------|-------|-------------|-----------|
| `outcome` (attended/skipped) | DARK | SURFACE | "You attended 12/15 calendar events this week" — primitive (intention/attendance gap) |
| External metadata fields | OPERATOR-ONLY | NO-ACTION | VT-23 substrate |

### Feedback + JarvisInvocation tables

| Column | Class | Disposition | Rationale |
|--------|-------|-------------|-----------|
| Feedback fields | OPERATOR-ONLY | NO-ACTION | Triage queue |
| `jarvis_invocation.tool_args` | DARK | PROMOTE-TO-JARVIS | **Operator's questions ARE behavioral signal.** JARVIS can analyze its own invocation history during soak. |
| `jarvis_invocation.tool_result_summary` | OPERATOR-ONLY | NO-ACTION | Capped audit trail |
| `confirmed_at - invoked_at` (derived) | DARK | PROMOTE-TO-JARVIS | Operator's reasoning-time on JARVIS write tools — meta-signal about operator's cognitive load |

---

## §2 — Cross-Table Derivations (8 signals)

| Derivation | Class | Disposition | Rationale |
|------------|-------|-------------|-----------|
| `task.created_at` vs `task.planned_start_utc` (scheduling latency / hesitation) | DERIVABLE-DARK | SURFACE | **Top-7 candidate** — hesitation primitive |
| `task.executed_end_utc` vs `task.planned_end_utc` (overrun signature) | DERIVABLE-DARK | SURFACE | Overrun primitive |
| `pause_event.paused_at` vs next session `start_time_utc` (context-switch latency) | DERIVABLE-DARK | SURFACE | Context-switch cost primitive |
| `task.parent_task_id` linkage (interruption tree graph) | DERIVABLE-DARK | PROMOTE-TO-JARVIS | Switch-direction analysis — operator-side first |
| `task.replaces_task_id` / `replaced_by_task_id` (substitution chains) | DERIVABLE-DARK | PROMOTE-TO-JARVIS | Abandonment-path primitive — surface after JARVIS validation |
| `reflection_view_log.fired_at` → `viewed_at` → `dismissed_at` (engagement latency by reflection_type) | DERIVABLE-DARK | PROMOTE-TO-JARVIS | Engagement primitive — surface after validation |
| Per-day cascade chains (consecutive SKIPPED tasks) | DERIVABLE-DARK | SURFACE | **Cascade primitive** — survives audit's kill list as inference math |
| Per-week consistency variance | DERIVABLE-DARK | PROMOTE-TO-JARVIS | Stability primitive — operator-side first |

---

## §3 — Redis State (9 key families)

| Key family | Class | Disposition | Rationale |
|------------|-------|-------------|-----------|
| `stopwatch:active:{user_id}` | DARK | NO-ACTION | Cache only; queue-depth not behavioral |
| `stopwatch:paused:{user_id}` | DARK | NO-ACTION | Cache only |
| `undo:{user_id}:{entity_id}` | DARK | NO-ACTION | Transient |
| `idempotency:{key}` | DARK | NO-ACTION | Transient |
| `notion:sync_queue:{user_id}` (depth) | DARK | PROMOTE-TO-JARVIS | Queue depth = real-time behavioral pressure (user has X pending writes) — operator-side validation |
| `gcal:access_token` / `gcal:events:*` | OPERATOR-ONLY | NO-ACTION | Sync mechanism |
| `last_operated_task:{user_id}` | OPERATOR-ONLY | NO-ACTION | Context for follow-up corrections |
| `notifications:pending:{uid}` (depth + dwell) | DARK | PROMOTE-TO-JARVIS | Queue dwell = engagement-gap signal — operator-side first |

---

## §4 — Journey-Stage Implicit Signals (21 stages, ~131 named)

Compressed to highest-value per stage. Full enumeration in the Pass-5 Explore agent report.

| Stage | Top implicit signal | Class | Disposition |
|-------|---------------------|-------|-------------|
| 1. Pre-signup landing | UTM / referrer / device / dwell | NOT-INSTRUMENTED | NO-ACTION (defer; cohort too small to learn from acquisition channels) |
| 2. OAuth signup | OAuth completion latency, scope hesitation | NOT-INSTRUMENTED | NO-ACTION |
| 3. First load / onboarding routing | Auth-to-render → first-interact latency | NOT-INSTRUMENTED | INSTRUMENT (deferred) |
| 4. Brain dump onboarding | Parse-to-commit latency + binding acceptance + edit count | NOT-INSTRUMENTED | **INSTRUMENT (top-7 #1)** |
| 5. 29-item archetype survey | Per-item dwell + variance | NOT-INSTRUMENTED | **INSTRUMENT (top-7 #3)** |
| 6. Tutorial complete/skip | Step-level engagement | NOT-INSTRUMENTED | NO-ACTION (tutorial is being phased out per onboarding rewrite) |
| 7. Settings → Integrations | Integration order, time-to-first-connect, retry frequency | NOT-INSTRUMENTED | INSTRUMENT (deferred — needs `connected_at` column) |
| 8. First task creation | Modal-open-to-submit latency, field-fill order | NOT-INSTRUMENTED | **INSTRUMENT (top-7 #5)** |
| 9. Calendar view | View-preference, drag-vs-modal-reschedule path | NOT-INSTRUMENTED | NO-ACTION (defer) |
| 10. Today view | Page-open frequency, scroll depth, force-refresh count | NOT-INSTRUMENTED | NO-ACTION (defer) |
| 11. Stopwatch start (readiness modal) | Click-to-modal latency, readiness-edit-before-submit | NOT-INSTRUMENTED | NO-ACTION (defer) |
| 12. During execution | Completion-percentage update trajectory | NOT-INSTRUMENTED | **INSTRUMENT (top-7 #2)** |
| 13. Pause flow | Reason-pick latency + consistency over time | NOT-INSTRUMENTED | **INSTRUMENT (top-7 #4)** |
| 14. Resume flow | Resume trigger source (manual vs prediction-accept vs reminder) | DARK | DERIVABLE-DARK → PROMOTE-TO-JARVIS |
| 15. Task switching mid-session | Switch-chain depth + return probability | DERIVABLE-DARK | PROMOTE-TO-JARVIS |
| 16. Stop flow | Reflection-rating hesitation + edit | NOT-INSTRUMENTED | NO-ACTION (defer; reflection modal already gets context line per Phase 4) |
| 17. Post-stop reflection surfaces | Dwell distribution per reflection_type | DARK | DERIVABLE-DARK → PROMOTE-TO-JARVIS |
| 18. End-of-session navigation | Post-reflection next-page choice | NOT-INSTRUMENTED | NO-ACTION (defer) |
| 19. Day-end / cross-day return | Return-after-cascade latency | DERIVABLE-DARK | **SURFACE** (computable from existing Task.created_at + state — no instrumentation needed) |
| 20. Voiding / abandoning / rescheduling / skipping | Per-user abandonment-path preference | DERIVABLE-DARK | **SURFACE** (computable from existing data) |
| 21. Account deletion | Modal dwell, retention checkbox rate | NOT-INSTRUMENTED | NO-ACTION (low frequency, low value pre-cohort) |

**The transition-topology framing:** the intelligence is in the *transitions between stages*, not in the columns. Most stages above carry implicit signal that primitive-anchors to one of: transition friction, recovery latency, momentum collapse, action/declaration divergence, abandonment topology, contextual instability, cognitive overload under transitions.

---

## §5 — Top 7 Implicit-Not-Captured (ranked by user-understanding potential, per Pass 5)

These are the signals worth Phase 6 instrumentation. Ranked by primitive-value, not by ease of capture.

| Rank | Signal | Stage | Primitive | Disposition |
|------|--------|-------|-----------|-------------|
| 1 | Brain dump parse-to-commit latency + binding acceptance | 4 | Transition friction at onboarding | **INSTRUMENT** (Phase 6 — telemetry_brain_dump_dynamics) |
| 2 | Completion-percentage update trajectory | 12 | Action/declaration divergence (mid-task scope reality-check) | **INSTRUMENT** (Phase 6 — telemetry_completion_trajectory) |
| 3 | Per-item dwell + variance in 29-item survey | 5 | Authentic-response vs speed-running primitive | **INSTRUMENT** (Phase 6 — telemetry_survey_per_item) |
| 4 | Reason-pick latency + consistency in pause flow | 13 | Pause discipline vs reflex noise | **INSTRUMENT** (Phase 6 — telemetry_pause_hesitation) |
| 5 | Modal-open-to-submit latency in first task creation | 8 | Task-entry friction primitive | **INSTRUMENT** (Phase 6 — telemetry_modal_dwell) |
| 6 | Return-after-cascade latency | 19 | Recovery latency primitive | **DERIVABLE — SURFACE in Phase 4** (no instrumentation needed) |
| 7 | Per-user abandonment-path preference stability | 20 | Abandonment topology primitive | **DERIVABLE — SURFACE in Phase 4** (no instrumentation needed) |

**Phase 6 net new instrumentation: 5 telemetry types** (not 7). Items 6 and 7 are derivable from existing data and ship in Phase 4 reflection surfaces.

All 5 telemetry types follow `feedback_reflection_view_log_namespace`: `telemetry_*` prefix, `event_class: "telemetry"` payload field, `schema_version: 1`, schema documented in `docs/reflection_view_log_schemas.md` (lands with Phase 6).

---

## §6 — Disposition Rollup (the actionable output)

| Disposition | Count | Phase |
|-------------|-------|-------|
| **NO-ACTION** (already correctly handled) | ~95 | — |
| **SURFACE** (Phase 4 UI reflection) | ~12 high-value primitives | Phase 4 |
| **PROMOTE-TO-JARVIS** (Phase 2 operator-side discovery) | ~24 | Phase 2 |
| **RETIRE** (Phase 5 writer removal) | 1-3 (`task.llm_priority` confirmed; others TBD post-JARVIS soak) | Phase 5 |
| **INSTRUMENT** (Phase 6 net-new capture) | 5 (top-7 #1, #2, #3, #4, #5) | Phase 6 |
| **DEFER** (low-priority, revisit post-cohort-scale) | ~70 | — |

The remaining ~70 deferred signals stay in this doc as the backlog. They are not closed; they are sequenced. Post-Jun-18-25 retention checkpoint, this list gets re-triaged with cohort-scale signal density informing what to surface next.

---

## §7 — Operator Sign-Off

This disposition table is the gate for Phase 2. Before JARVIS gets the new tools, operator confirms:

- [x] The ~12 SURFACE items are the right Phase 4 candidates
- [x] The ~24 PROMOTE-TO-JARVIS items are the right discovery substrate
- [x] The Phase 6 INSTRUMENT list of 5 is correct (not 7 — items 6/7 are derivable)
- [x] `task.llm_priority` is OK to RETIRE (writer removal; column kept)
- [x] The ~70 DEFER items are acceptable as backlog (operator can flag any to promote earlier)

**Sign-off note from operator:** Confirmed override to proceed with JARVIS soak (2026-05-02).

Once signed, Phase 2 (JARVIS soak window 2026-05-02 → 2026-05-16 minimum) starts. The hypothesis log accumulates in `docs/jarvis_hypothesis_log.md`. Promotion to Phase 3 inference engine requires ≥3 promoted + ≥2 rejected hypotheses with the failure case demonstrating discrimination.

---

## Revision 2 — 2026-03-29

### §R2.1 — Task-level primitive: incomplete description before deadline

Dogfood **May 2** (`docs/dogfood_findings_living.md`): if the user assigns a **deadline** but fails to finish composing the task **description / scope** before the deadline instant, that indicates **declared urgency without planning depth** — a priority-measurement primitive for Phase 6 inference.

| Signal id | Class | Disposition | Capture notes |
|-----------|-------|-------------|----------------|
| `description_incomplete_at_deadline` | **NOT-INSTRUMENTED** → **INSTRUMENT** (Phase 6 candidate; inference_engine substrate) | Same tier as other behavioral primitives in §5 | **High fidelity:** boundary snapshot at or before `Deadline.due_at_utc` (telemetry or server-side). **Proxies for JARVIS:** `deadline_id`, `Deadline.due_at_utc`, `Task.description`, `scope_bullet_count_at_plan`, `Task.last_modified_at`. |

This revision **adds one named row** to the triage set. It does **not** re-total the §Methodology passes (the **≥208** figure remains the documented floor; overlap across passes is unchanged).

### Cross-reference

Narrative journey spine + definitions: `docs/journey_signal_counts.md`.

---

*Owner: Ali. Lands 2026-05-02 alongside Phase 0 doctrine. Source of truth — no behavioral signal disposition decisions land outside this doc. Amendments require git history (no in-place rewrites; append a "Revision N" section).*
