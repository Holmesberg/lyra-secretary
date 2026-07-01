# Building Phases

> Historical phase map. This document preserves pre-freeze planning context, but
> it is not current implementation authority during the architecture freeze. Do
> not use it to authorize runtime features, roadmap scope, cohort expansion,
> AI synthesis, passive tracking, or new provider adapters. Current authority
> lives in `docs/AUTHORITY.md`, `docs/current_transition_state.md`, and
> `docs/architecture_freeze_priority_hold_2026_05_20.md`.

Historical phase map. This preserves April planning context and shipped/parked
intent, but it is not a forward-looking source of truth during the current
freeze-closure refactor.

**Last updated:** April 14, 2026 (Phase 4.5 active)

---

## Canonical Update Rule

Historical rule preserved for context only: this file used to act as the
slow-moving phase plan. During the architecture freeze, do not use this section
to authorize code or runtime behavior. Current authority lives in
`docs/AUTHORITY.md`, `docs/current_transition_state.md`,
`docs/operator_dashboard_contract.md`, and the refactor stabilization ledger.

When a phase ships, its section collapses to a summary line referencing `project_history.md` and any items that slipped forward move to the next phase.

---

## Status Taxonomy

| Status | Meaning |
|--------|---------|
| SHIPPED | Merged to main, browser-verified, in production |
| IN_PROGRESS | Active work, uncommitted or unverified |
| PRE_ALPHA | Must ship before April 30 alpha launch |
| PHASE_5 | Blocked on alpha launch + retention validation |
| PHASE_6 | Blocked on 30+ sessions per user + archetype data |
| PHASE_7 | Blocked on retention answer (May 21 ± 3 days) |
| DEFERRED | Explicitly deferred with reason |
| REJECTED | See `docs/do_not_add.md` |

---

## Phase Boundary Definitions

| Phase | Gate to enter | Gate to exit |
|-------|--------------|-------------|
| 4.5 (Pre-Alpha Polish) | Phase 4 calendar shipped | All P0 dogfood items FIXED, operator browser-verified |
| 5 (Onboarding) | Alpha launch April 30 | 10+ users onboarded, instrument data collected |
| 5.5 (Trusted-User Monitoring) | First alpha cohort active | Retention answer (May 21 ± 3 days) |
| 6 (Calibration + Feature Surfaces) | 30+ sessions per user, archetype data available | Calibration layer deployed, Phase 6 validation gates pass |
| 7 (Public Expansion) | Retention validated, Week 6-8 checkpoint green | PWA shipped, multi-timezone working |
| 8+ (BCI) | BCI decision (June), hackathon path confirmed | Bayesian signal fusion validated (20+ simultaneous sessions) |

---

## Phase 4.5 — Pre-Alpha Polish (April 13-18 target)

Active phase. Goal: harden everything shipped so far, close remaining P0/P1 items from dogfood, prepare for trusted-user handoff.

**Pause window:** April 19-29 (Spring School). Pre-pause hardening target: April 18.

### SHIPPED

- voided_at audit: 15 bugs found and fixed across background jobs, mutation endpoints, conflict detector, undo cache (5 commits, 15 regression tests)
- Notion-style data table at /table with CSV export
- SKIPPED ghost banner fix + mark_abandoned Redis cleanup
- POST /v1/stopwatch/update-completion + early-stop override
- 5-state system consistency gate tests
- Phase 9 adversarial multi-user isolation testing — completed out-of-sequence during Phase 3/4 window (not post-Phase 8 as originally planned). Scope leak found and fixed. Multi-user isolation test suite written and passing (`tests/test_multiuser_isolation_adversarial.py`). No phase number assigned.
- Multi-tenant Redis key namespacing (notifications, last_operated_task, notion sync queue)
- Mid-task completion estimate surfaced at stop time (mid_task_completion_pct in stop response)
- End-time primary input on new task modal
- Day navigation on Today view (prev/next arrows)
- PLANNED edit affordance via prefilled modal
- PLANNED delete affordance with confirmation dialog
- EXECUTING/PAUSED skip affordance
- Multi-select void replacing row-level trash icon
- Interruption flow handles mixed paused + blocking conflicts
- Friendly 400 on invalid state transitions
- ActiveTimerBanner hook order violation fix
- Pause reason picker (6-reason dropdown)
- Stale session recovery job (15-min APScheduler sweep)

### IN_PROGRESS

- Settings page: Export JSON + Delete account with two-stage major warning pattern + anonymized research retention (code complete, pending browser-verify + commit)
- GET /v1/users/me/data-summary endpoint
- Alembic 019: anonymized retention columns
- Canonical project documentation (this document + project_history.md)

### PRE_ALPHA — reordered by tier (retention architecture first, correctness last)

Ordering rationale: the pre-alpha ship order follows `MANIFESTO.md §Shipping Philosophy — Retention Mechanism First`. The retention mechanism (feedback/output loop that closes Error → Exposure → Adjustment) must ship before correctness polish, because a correct product with no feedback loop churns faster than a rough product that mirrors back. Tier 1 is the shipping gate for alpha. Tiers 2–4 may slip; Tier 1 may not.

#### Tier 1 — Retention architecture (SHIPPING GATE)

The feedback/output surfaces that make Lyra feel like a mirror rather than a logger. Every backend signal with a user-facing meaning must have a visible surface.

- ✅ **micro_mirror surface** — toast-pattern render on stop response per `docs/design_patterns/notification_patterns.md §1 Toast`. LYR-098 shipped Apr 16 across 4 commits (`553d7b0` fixture tests → `a8aeae0` text neutralization + filter fix → `0593d71` reflection_view_log persistence → `c8efff2` Toast UI).
- ✅ **calibration_nudge surface at stop** — **toast** (pinned-by-default), not modal, since the reference-class summary is post-hoc informational, not decisional (moved from §Modal → §Toast in `notification_patterns.md` on Apr 16, see `strategic_decisions_april_14.md §3` April 16 refinement note). LYR-098 shipped Apr 16 with the same 4-commit sequence as micro_mirror.
- **calibration_nudge surface at task creation (D3)** — when the user sets a `planned_duration_minutes` that the bias_factor model predicts will overrun, surface a pre-commit nudge with the predicted range. User chooses to accept, adjust, or dismiss. Dismissal logged for V3 engagement analytics. Never auto-corrects the value (see `docs/do_not_add.md` §Auto-suggested task durations without provenance — surfacing is informational, not replacing the user's estimate unless provenance/exposure rules explicitly record that source).
- **/insights tab v1 (D4)** — new top-level route. Renders: (a) "Insights unlock in N sessions" progress framing when the user has < 30 sessions in a category (see G4), (b) the three VT-12 companion charts for users who have crossed 30, (c) the operator's cascade_score trend, (d) a bias_factor-by-category strip, (e) **pause pattern card** — weekly breakdown of `pause_reason` enum counts (mental_fatigue / distraction / task_difficulty / external_interruption / intentional_break / prayer), with per-category split if data supports it. Surfaces the `pause_reason` write-only and `pause_pattern` analytics bundle that the audit flagged as invisible. No confrontation dialect at this tier — metric dialect only (see `docs/phase_6_architecture_backlog.md` §Surface Ordering). Confrontation dialects land post-retention. **Implementation:** use `@tremor/react` (already installed, currently unused) for the chart layer — this is exactly the library this tab was latent-for.
- **"Insights unlock in N sessions" framing (G4)** — measurement-state progress, legitimate per `docs/do_not_add.md` §Gamification PERMITTED section. Applies everywhere Lyra has sub-30-session data for a category: "2 more sessions in dev to unlock bias_factor" is a truthful statement about when the instrument can speak. NOT a streak, NOT a badge, NOT a point total.
- ✅ **completion_pct ungate** — shipped `b0cdda0` (Apr 16). Removed `earlyStop &&` guard in `reflection-modal.tsx`; completion % input now renders on every stop, optional. Apr 16 data audit had shown 77% of EXECUTED tasks (33/43) had NULL task_completion_percentage; this ungate closes that gap.
- **is_future_task warning surface** — LYR-097. Backend already returns the warning; frontend must render an inline warning banner (see notification_patterns.md §inline-warning) and require confirmation before the timer starts on a future-dated task.
- **Conflict detection with forced override affordance (April 16 relaxation — Path A, April 17 further relaxation — Option C).** Finding 1 implementation, walked back from yesterday's "hard block on any non-voided overlap" per Apr 15 dogfood finding. **Severity model (updated April 17):** All overlaps are **SOFT** (force-overridable). Only remaining **HARD** constraint: two tasks cannot be EXECUTING simultaneously (single-mutation-authority — structural invariant per `rules_vs_agency.md`). EXECUTING overlap downgraded from HARD to SOFT on April 17 — the HARD block was a behavioral constraint masquerading as an invariant; users legitimately create tasks during execution windows. Interruption flow offered only within 5-min window of planned start. Each conflict carries a `gate_id` (`executing_overlap` | `planned_overlap` | `duplicate_title`) so the dogfood Day-10 override-rate analytics can attribute overrides per gate. Frontend surfaces `[Cancel] / [Create anyway]` for all soft conflicts. The `override_token` 60-second one-shot from the original spec is **deferred** — current implementation uses the simpler `force=true` boolean already in the wire contract; replay-protection token is its own design pass. Allowing planned-task overlap is a precondition for the multi-task logging investigation in `parked_ideas.md`. Shipped commits `bb5d5d9` (initial), updated April 17.
- **Published-research priors for top 3 categories** — cold-start feedback acceleration. Operator provides a prior table for `coding` / `academic` / `exercise` categories with citations. Applied at task creation as progressive-revelation teaser: "Research on [category] shows tasks run [X]% over estimates. Your estimate: N min. Research-adjusted: N+adjustment min. [Keep] [Use adjusted]." Priors transition to personal patterns at session 7+ per the progressive-revelation pattern (see `docs/do_not_add.md §Gamification — PERMITTED: progressive revelation`).
- **Web UI retroactive modal** — covers the OpenClaw gap for trusted users per Finding 3 Option C hybrid. Frontend affordance to retroactively log a session with `pre_task_readiness` / `post_task_reflection` / `unplanned_reason` capture. Must include conflict detection (Gate B) from the override item above.
- **Web UI pause response banner** — for pause predictions that fire from the Tier 1.5 system. Dismissible banner on `/today` with `[Pause now]` / `[Snooze]` / `[Dismiss]` affordances calling `POST /v1/pause_predictions/{firing_id}/respond`. Routes acceptance through the existing pause flow so `pause_reason` + `pause_initiator` remain user-provided (no defaults — see `docs/do_not_add.md §Predictive notifications that default research-relevant fields`).
- **Fixture tests for retention signals (PRECONDITION for every UI surface above)** — backend tests that assert two things on fixture inputs:
  1. *Contract tests* — `/v1/stopwatch/stop`, `/v1/create`, and `/v1/analytics/insights` return the fields the frontend surfaces expect. Prevents future backend refactors from silently breaking the feedback loop.
  2. *Computation-correctness tests* — the actual values of `bias_factor`, `calibration_nudge`, `micro_mirror`, and any insight the UI surfaces are correct on known fixture data. Required by `MANIFESTO.md §Scope of the retention-before-polish principle` (added April 14, 2026): the retention-before-polish ordering does **not** apply to insight correctness, because wrong insights in a self-tracking context produce trust collapse (Li 2010, Epstein 2015) that bugs do not. These tests must land **before** any of the surfacing items above ships, not in parallel.

#### Tier 1.5 — Experimental retention mechanisms (ship during trusted-user window with kill criteria)

User-facing retention features that are NOT blockers for the April 18 trusted-user launch but SHIP before the May 1 alpha. Each item lands with a pre-registered kill criterion and a VT candidate. Per-user threshold, 7-day review window — if the kill threshold trips, the feature is pulled before alpha; if the ship threshold holds, it graduates. This tier is distinguished from Tier 1 by *falsifiability at launch* — Tier 1 items are architectural commitments; Tier 1.5 items are hypotheses about what helps retention.

- **Pause-prediction notifications** — Telegram-delivered predictions that fire 2–3 min before a user's expected pause time, derived from their historical pause patterns (clock-anchor mechanism) and current-task work rhythm (work-rhythm mechanism). Predictions self-activate per user at ≥ 7 days of `pause_event` history. Pause-now action routes through the existing OpenClaw agent flow — the notification instructs the user to reply `pause` to the agent; no callback-button infrastructure is built (text-reply path preserves full pause_reason + pause_initiator data capture via the canonical agent dialog, see SKILL.md §Pause). Acceptance/dismissal inferred post-hoc from pause_event timing.
  - **Kill criterion:** pre-registered in MANIFESTO VT-17 — acceptance_rate ≥ 0.40 ships per-user; < 0.20 kills. Formula frozen at feature launch.
  - **Validity threat:** VT-17 (Instrument-Intervention Threat) — three distinguishing analyses (17a/b/c) run at end of 7-day acceptance window; any one can independently trigger a kill.
  - **Motivating incident:** April 14, 2026 — operator forgot to pause during breakfast, contaminating Dev session duration. Feature aims to preempt missed-pause data contamination, not to drive engagement.
  - **Structural investigation outcome:** spec initially assumed pause-event history existed in schema; it did not (schema retained only the most-recent pause per session, cleared on resume). Feature ships with a new `pause_event` table + dual-write from pause()/resume() + elimination of silent defaults at stopwatch_manager.py:330-331 that were a latent `do_not_add.md` violation. See `docs/design_patterns/structural_investigation_rule.md` for the rule that surfaced this.

#### Tier 2 — Operator-verifiable correctness (ship after Tier 1)

Bugs the operator has hit during dogfood. Blocks daily use but not retention architecture.

- New task modal stale defaults (component state leak on reopen)
- Cannot start PLANNED task while another task is PAUSED (start path doesn't distinguish paused-parent from active-executing)
- Edit click vs multi-select checkbox conflict on PLANNED rows (unverified)
- Stale session recovery job not firing as designed (APScheduler verification needed)
- Ghost timer banner persists after OpenClaw mark-abandoned (Redis key cleanup on skip path)
- Backend-unreachable graceful retry UI
- Active timer banner "12h+ paused" cap
- Tooltips on readiness/focus/delta arrow — include `discrepancy_score` inline on the row arrow as well ("4→2 +29min | discrepancy: 2"). Low-effort surfacing of the partially-invisible signal the audit flagged.
- CSV export cleanup — remove `session_index_in_day` from the /table CSV columns. Field is deliberately analytics-only (used internally for cascade analysis), not a user-facing signal. Removing from export reduces column clutter without losing any surfacing (it was never displayed in the table view either).
- Delete account browser-verify (see `docs/post_launch_verification_queue.md`)
- Export JSON browser-verify (see `docs/post_launch_verification_queue.md`)

#### Tier 3 — Infrastructure (ship with Tier 2 or defer into Phase 5)

Not user-facing. Can slip a week without visible alpha impact.

- Backup infrastructure (nightly SQLite snapshot + 7-day retention)
- DBGuard (readiness-gate checks before destructive migrations)
- Race condition fix in `stopwatch_manager.stop()` (documented, low-frequency)
- Postgres migration — deferred, no alpha-user signal yet
- `cohort` field on user table (defaults to `alpha_v1`; retention analysis needs it labeled before data lands)
- **Operator analytics notebook** (`notebooks/operator_analytics.ipynb`) + systematic interrogation checklist (`docs/operator_interrogation_checklist.md`) + findings log template (`docs/operator_findings_log.md`). Private operator tooling, not a product feature. Seven helper cells (DB loader, distribution, stratified correlation, time series, category×time heatmap, cascade visualizer) plus Day 10 / 30 / 60 / 90 question cells. Ships before Spring School so operator can use it during the trusted-user monitoring window. Replaces ad-hoc CSV review, which causes silent signal loss.

#### Tier 4 — Onboarding ceremony (deferred past April 18)

The instrument-battery-before-product flow is retention-hostile. Direct entry to `/today` is the alpha entry path.

- Consent modal (research-consent, separate from TOS)
- `/privacy` and `/terms` placeholder pages (legal links exist, content fills in later)
- Direct entry to `/today` after signup (NOT instrument battery first)
- Full MEQ-5/BFI-10/BSCS/GP-Short instrument battery — ships in Phase 5 during the May 1+ soft-onboarding window, captured progressively over the first week rather than at signup

---

## Phase 5 — Pre-Alpha + Onboarding (April 18 → May ~14)

**Goal:** Ship clustering survey + archetype wiring between trusted-user launch (April 18) and alpha launch (May 1). Then ship the alpha to 10-30 trusted users with instrument collection, consent flow, first-run experience.

**Timeline clarification (April 17):** Phase 5 pre-alpha window runs **April 18 – May 1** (between trusted-user handoff and alpha launch). April 30 is the alpha launch target, not the Phase 5 start date. The pre-alpha ship list below ships during the trusted-user observation window; the onboarding ceremony ships at alpha launch (May 1+).

**Entry gate:** All Phase 4.5 Tier 1 items SHIPPED and browser-verified. Tier 2 correctness fixes shipped or explicitly deferred.

**Onboarding timing correction (April 14):** Full instrument battery + consent ceremony ships on or after **May 1**, NOT before April 18. The pre-alpha trusted-user path (if any alpha users onboard before May 1) enters `/today` directly with progressive instrument capture over the first week. Reason: the instrument-battery-before-product flow is retention-hostile for users who have not yet seen Lyra's feedback loop. Ceremony without context produces drop-off.

### Pre-alpha ship list (between April 18 trusted-user launch and May 1 alpha launch)

Archetype architecture — data from trusted-user cold-start informs these, shipping before alpha:

- **Onboarding clustering survey** — 8–12 question survey that places new users in one of 5 archetypes with an initial confidence score. Ships in the May 1+ onboarding window; trusted-user cold-start data (April 18–29) informs question wording and archetype boundary placement.
- **Archetype prior wiring** — `bias_factor` computation applies the archetype prior via Bayesian shrinkage. Weighted heavily early (archetype dominates when personal N < 5), personal data dominates by N=15. See `docs/methodology.md` archetype grid for the prior table.
- **Progressive archetype revelation** — display archetype at session 5–7 with medium-confidence framing; reclassification UI surfaces at session 15–20 if behavior diverges. Implements the progressive-revelation pattern from `docs/do_not_add.md §Gamification` and `docs/design_patterns/notification_patterns.md §Progressive Revelation Pattern`.
- **Archetype-based calibration-nudge text** — nudges reference the archetype ("users with your profile tend to...") in early sessions and transition to personal framing ("your pattern: ...") as N accumulates. Text-only change on the existing Tier 1 calibration-nudge surface.

### Onboarding Instrument Battery

Four validated instruments, <4 min total signup time (see `docs/methodology.md §1`):

1. **MEQ-5** (Chronotype) — 5 items, 4-25 range
2. **BFI-10 C** (Conscientiousness) — 2 items, 2-10 range
3. **BSCS-Brief** (Self-Control) — 13 items, 13-65 range
4. **GP-Short** (Procrastination) — 9 items, 9-45 range

Scores map to 2D archetype space (Chronotype × Discipline) → 5 archetypes with calibrated prior bias_factors. See `methodology.md` for the full archetype grid and Bayesian shrinkage model.

### Planning Friction Architecture

The core measurement requires users to plan tasks with estimated durations *before* executing them. This is deliberate friction — the planning act generates the data that makes everything downstream work.

**Two-population design principle:** Some users will be natural planners (planning is relief). Others will not (planning is friction). Lyra must serve both without corrupting the measurement instrument:

- **Planners:** Full task creation with start/end times, categories, notes. Calendar view as primary interface. These users generate the richest data and are the primary H1 population.
- **Non-planners:** Minimal viable input — title + estimated duration only. "Quick add" flow. No required category, no required time slot. System infers time slot from creation timestamp. These users generate sparser but still valid delta data. They may never use the calendar.

The system must not push non-planners toward planning (that's intervention, not measurement) or simplify away from planners (that loses signal). Both populations produce valid `duration_delta_minutes`. The difference is how much contextual metadata surrounds it.

**Implementation:** Quick-add endpoint (title + duration → auto-slot from now) + existing full-creation flow. Frontend: floating "+" button → quick add; navbar "New task" → full modal. Both flows converge on the same `POST /v1/create` with different field populations.

### Consent + Terms Flow

- Terms of service acceptance gate (POST /v1/users/me/consent)
- Research consent (separate, optional, clearly framed)
- Anonymized retention default explained during onboarding
- Settings page as the data sovereignty surface (export, delete, backup status)

### First-Run Experience

- Empty state guidance on /today (no tasks yet)
- Instrument battery on first login (before task creation unlocks)
- Archetype assignment + prior bias_factor set
- Brief explanation of what Lyra measures and why planning matters

### Alpha Recruitment

- 10-30 users, deliberately NOT like operator — different cognitive styles, planning habits, non-morning-dependent day structures (MANIFESTO commitment)
- Recruitment channels: TBD (university cohort, personal network, productivity communities)
- Per-user APScheduler jobs via for_each_user() pattern already implemented

---

## Phase 5.5 — Trusted-User Monitoring (May ~14 → May 21 ± 3 days)

**Goal:** Monitor first alpha cohort through the fragility window. Retention is the gate for everything after.

### Retention Measurement

- **Week 1:** Session frequency, drop-off points, first-task completion rate
- **Week 3:** Retention checkpoint (standard). But per QS literature post-2017, week 3 can be novelty-driven false positive
- **Week 6-8:** True retention checkpoint. If week 3 green but week 6 red → hedonic adaptation, not product-market fit

### Monitoring Deliverables

- Daily/weekly digest for sessions 5-30 (mid-funnel retention loop — see dogfood P2)
- Operator dashboard: per-user session counts, delta trends, drop-off signals
- Bug triage pipeline: alpha user reports → dogfood doc → fix batch cycle

### Kill/Pivot Decision (May 21 ± 3 days)

**Explicit decision-gate criteria.** The May 21 review evaluates three measurable conditions. At least two must hold for retention to count as validated.

**(a) Week-3 session frequency.** ≥ 50% of users from the alpha cohort recorded at least one `stopwatch_session` in the calendar week containing May 14–20 (week 3 of their signup cohort). Computed as `distinct(user_id) with ≥1 session in week_3 / total alpha_v1 users onboarded by May 7`. If < 50%, treat as red — drop-off during the fragility window.

**(b) Week-3 planning engagement.** Among users who are week-3 active per (a), ≥ 40% have a `pre_task_readiness` populated on ≥ 5 sessions across their tenure. Planning engagement is the measurement-instrument signal; users who log sessions but never rate readiness are effectively in Phase 1A mode and do not contribute to H1. If < 40%, the metacognitive layer is being skipped and the retention we're seeing is logger-retention, not instrument-retention.

**(c) Qualitative signal from operator weekly review.** Operator reads every alpha user's exposure distribution and flags users whose interaction pattern matches "engaged with mirror" vs "logged and dropped off before surfacing caught up." If ≥ 6 of the alpha cohort (from 10 minimum) show mirror-engaged behavior (reading micro_mirror / calibration_nudge, dwell time > 2s on notifications, at least one completion-percentage adjustment after mid-task check-in), this passes. If fewer, the feedback loop is not closing for most users.

**If retention validates (two of three criteria pass):**
- Proceed to Phase 6 (calibration)
- Begin Paper 1 data collection (H1 requires 30-60 days, 60+ paired sessions)
- Paper 2 (cascade failure) may be publishable by June if signal holds

**If retention fails (two of three criteria fail):**
- Diagnose: is it the measurement friction? The UX? The value proposition?
- Middle-phase retention mechanism candidates (see dogfood P2): insight tiering, lightweight social accountability, predictive intervention
- May pivot to Phase 1A (delta-only, productivity-first) if the metacognitive layer is the friction source

**If exactly one criterion passes:** extend the checkpoint by 14 days to capture the week-6 data point. Week-3 novelty false positives are a known QS-literature phenomenon (see `docs/dogfood_findings_living.md` §Post-novelty retention metric).

---

## Phase 6 — Calibration + Feature Surfaces (post-retention validation)

**Goal:** Deploy the error-rate gradual exposure calibration architecture. Full spec in `docs/phase_6_architecture_backlog.md` — this section is a summary, not a duplicate.

**Entry gate:** 30+ sessions per user in at least one category. Archetype data available.

### Core Mechanism

Three signals infer confrontation readiness without explicit user input:

- **V1 (Measurement-Trust Velocity):** Passive — tracks whether user's new plans drift toward bias-adjusted expectation. Zero friction.
- **V3 (Engagement with Surfaced Data):** Light instrumentation — view tracking on micro_mirror, calibration_nudge, time-to-dismiss. New schema: `reflection_view_log` table.
- **V5 (Silence Preference):** One setting, four levels — "just metrics" through "full depth." Movement toward depth = calibration development.

### User Response Typology

Four types classified from behavioral data (not self-report):

1. **Calibrators** — error decreasing, adjustments proportionate → ready for philosophical branches
2. **Acknowledge-but-don't-change** — high awareness, no shift → need existential weight
3. **Illusion Preservers** — repeat same planning despite errors → mirror only, no confrontation
4. **Overcorrectors** — wild swings post-exposure → stabilization anchoring

### Pre-registered Constraints

- No confrontation before 30 sessions per category (cold-start protection)
- No confrontation in first 14 days regardless of readiness
- Default exposure during cold start: "metrics + reflections" with no branches
- User can always opt out via V5 (silence preference)
- External human accountability required — operator weekly review of exposure distributions

### Schema Additions (Phase 6)

- `reflection_view_log` table
- `users.exposure_preference` + `users.exposure_preference_history`
- `gamed_calibration_flag` on task
- `intervention_log` table (prediction-first logging)
- Per-category bias_factor with Bayesian shrinkage (methodology.md model)

### Research Deliverables (Phase 6)

- Falsification engine: continuous H1 correlation computation, AT_RISK/PASS/FAIL status
- Metacognitive reliability score per user (Dunning-Kruger stratification, 30+ sessions)
- Confrontation readiness score (composite: consistency + calibration_rate − variance − avoidance_signals)
- Gamed calibration detection (delta improves AND execution_efficiency drops)

### Additional Feature Surfaces

- category_type field (estimable vs time_anchored) — **promoted to Phase 4.5 Tier 1** per VT-13 (`MANIFESTO.md`); retained here as summary reference
- is_anchor boolean on prayer/sleep tasks — same promotion
- Trigger field for implementation intentions (clock / after_task / contextual)
- LLM-powered task creation via OpenClaw bridge (secondary path, always showing parsed result for confirmation)
- Residue-based cascade model evaluation against probability-based (fit both, ship better one)
- Archetype re-fit cycle (periodic Bayesian update vs archetype(t) function)
- **Interruption chain visualization.** Backend already tracks `parent_task_id` and `interruption_type` on tasks started as interruptions (commit 2f4abed). Currently no UI. Phase 6 surface: on `/insights` or a dedicated detail view, render parent→child chains so the user can see "this week you interrupted dev work 4 times with admin tasks averaging 18 minutes." Requires real design — rough rendering for trusted alpha users is worse than no rendering. Deferred from Phase 4.5 per audit disposition.
- **Readiness-drift signal from `original_pre_task_readiness`.** Audit column currently written on `/v1/stopwatch/correct-readiness` calls and never read. Phase 6 use: feeds a "readiness drift" signal into the calibration layer — users who frequently correct their readiness post-hoc have a different metacognitive pattern than users who don't. Adds a V1 (measurement-trust velocity) component. See `docs/phase_6_architecture_backlog.md` for the full design.

See `docs/phase_6_architecture_backlog.md` for full schemas, acceptance criteria, implementation sequence, and orienting principles.

---

## Phase 7+ — Public Expansion (post-retention answer)

**Goal:** Scale beyond trusted alpha. Mobile form factor, multi-timezone, public access.

**Entry gate:** Retention validated (May 21 checkpoint). Week 6-8 retention checkpoint green.

### Deliverables

- **PWA support** — iOS/Android home-screen install, offline mode, basic push notifications. ~4 hours for 80% of "feels like a real app." Deferred from Phase 5 because retention must validate before investing in distribution.
- **Multi-timezone API refactor** — Backend switches from naked Cairo-local ISO strings to UTC with Z suffix. Frontend converts via `user.timezone` field. Estimated 3-5 days + 2-3 weeks bug hunt. Trigger: first non-Cairo user signup. See dogfood P3 for the `TIMEZONE CONTRACT` preservation rule.
- **Middle-phase retention mechanisms** (if needed) — insight tiering, lightweight social accountability, or predictive intervention. Three candidate paths documented in dogfood P2.
- **Schedule-X drag-and-drop shim removal** — Housekeeping, waiting for `@schedule-x/drag-and-drop@4.x` upstream release.
- **Calendar dense-cluster readability** — Custom event renderer with cluster fallback for 5+ overlapping events.

### Research Deliverables (Phase 7)

- **Paper 1:** "Metacognitive discrepancy as predictor of execution failure" — requires 30-60 days data, 60+ paired sessions. Publishable if H1 survives.
- **Paper 2:** "Sequential task abandonment in knowledge workers: evidence for a cascade failure model" — independent of H1, data already being collected. Faster publication path, potentially June if signal holds.

---

## Phase 8+ — BCI Integration (conditional)

**Goal:** Integrate EEG + self-report as two noisy estimators of cognitive state via Bayesian signal fusion.

**Entry gate:** BCI decision in June. Path B (October BR41N.IO hackathon) preferred for research clarity. Integration only if both signals show meaningful correlation with delta.

### Architecture (from MANIFESTO)

- EEG and self-report as complementary signals, not replacement
- Bayesian weighting proportional to SNR per source
- Requires 20+ simultaneous EEG + self-report sessions per subject for validation
- Signal combination enhances precision — not new capability
- BCI-first architecture explicitly rejected (see `docs/do_not_add.md`) — behavioral-only case must prove first

### Why Conditional

If H1 fails (metacognitive signal doesn't predict delta), adding a second metacognitive signal (EEG) doesn't help — the problem is the hypothesis, not the measurement precision. BCI only adds value if the behavioral self-report signal is valid but noisy.

### Research Deliverable

- **Paper 3:** Cognitive-behavioral loop modeling — after ML layer works, if BCI integration produces meaningful signal improvement.

---

## Deferred Items

Items with explicit deferral decisions and reasons. Not rejected — just not yet.

| Item | Deferred to | Reason |
|------|------------|--------|
| VT-5 parent_session_id | Paper 1 analysis | Acknowledge in limitations rather than fix now |
| Smart inactivity reminders | Phase 7 | Retention must validate first |
| Aladhan prayer API | Phase 7+ | Nice-to-have, not measurement-critical |
| Prayer-time pause prediction | Phase 7+ | Can inform pause anticipation, but prayer/body-process anchors must stay outside cognitive calibration |
| Recurring lecture/task schedules | Phase 7+ | Needs recurrence contract, expansion rules, and duplicate-protection before implementation |
| Brain-dump sequential allocation with estimates | Phase 6/7 | Requires provenance for LLM-estimated duration/time; deadlines remain unchanged |
| ~~Overdue PLANNED/SKIPPED task done affordance~~ | **Shipped 2026-05-08** | One-click retrospective `done` marks overdue tasks EXECUTED with `initiation_status='retroactive'`; excluded from Cortex measured-execution profiles. See `docs/cortex_product_research_contract_v0.md` §4.5. |
| Native mobile apps | Post-PWA | PWA proves 80% of form factor at 10% cost |
| sleep_hours field | v1.5+ | Leading indicator for cascade, but adds daily friction |
| Multi-user collaboration | Post-retention | Social-obligation confound, irrelevant until single-user value proven |
| pre_task_readiness reactive measure note | Paper 1 methods | Framing change, not measurement change |
| ~~self_reflection → planning rename~~ | **Shipped 2026-04-21** | Un-merged early as part of Path B (engineer planning habit). See `docs/strategic_decisions_april_21.md`. |
| ~~Phase 5 onboarding scaffold~~ | **Shipped then paused 2026-04-21** | Full-screen onboarding surface shipped in the morning, commented out same-day after dogfood showed the brain-dump had nowhere visible to go. Replaced by a backend-seeded starter task inside `resolve_user_from_token` — user lands on `/today` with one PLANNED "plan your week" task already there. Onboarding UI code preserved for post-Spring-School re-enable. See `docs/strategic_decisions_april_21.md` §5 + `docs/import_integrations_capability_map.md`. |
| Complexity field (VT-4) | Phase 6 | Optional enrichment, not blocking |

---

## Rejected

See `docs/do_not_add.md` for the full list of 11 rejected architectural directions with reasoning. Summary:

**Permanently rejected:** GPS/WiFi fingerprinting, gamification, social feeds, multi-user collaboration pre-retention, hybrid PLANNED/EXECUTING UI collapse, aggressive notifications, auto-suggested durations, hardcoded defaults for research fields.

**Rejected as primary path (secondary OK):** LLM-parsed task creation (Phase 6 candidate as secondary via OpenClaw bridge).

**Deferred with preferred path:** BCI-first architecture (Path B October hackathon), native mobile (PWA first).

---

## Phase Numbering Cross-Reference

This document uses **engineering phase numbering**. MANIFESTO.md uses **research phase numbering**. See `docs/project_history.md` for the mapping table.

---

## Infrastructure Notes

**EC2 migration** is post-Spring-School infrastructure work, not a numbered phase. See `docs/deployment_architecture.md` §"Future EC2 migration path." Current production: operator laptop + Cloudflare Tunnel + Supabase Postgres. EC2 swaps compute without touching data. Trigger: retention signal from trusted-user week.

---

## Commit Statistics Snapshot

As of April 26, 2026 (post Apr 17-26 shipping burst; see `project_history.md` for full history):
- ~314 commits on main (was 222 at Apr 17 baseline)
- 33 Alembic migrations (was 23)
- 322 backend tests passing (was 221)
- 55 API endpoints (was 39)
- 10 business tables (was 9 — added `external_event_outcome` Apr 21 alembic 027)
- 8 APScheduler background jobs (unchanged: reminders, notion-retry, timer-overflow, overdue-tasks, stale-session-recovery, orphan-task-recovery, pause-prediction, reconcile-responses)
- 6 frontend (app)/ routes (/today, /calendar, /table, /settings, /insights, /admin) + 3 root pages (/onboarding, /privacy, /terms)
