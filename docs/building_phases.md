# Building Phases

Forward-looking canonical document. What remains to be built, organized by phase. Updated at phase boundaries.

**Last updated:** April 14, 2026 (Phase 4.5 active)

---

## Canonical Update Rule

This document is the single source of truth for forward-looking phase planning. Updated at every phase boundary (when a phase closes or opens). `dogfood_findings_living.md` is the fast-moving tactical doc; this document is the slow-moving strategic one. Items from dogfood graduate here when they solidify into phase-level commitments. Items here don't duplicate dogfood — they reference it.

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

### PRE_ALPHA (remaining — see dogfood P0/P1 for details)

P0 blockers (5 items):
- New task modal stale defaults (component state leak on reopen)
- Cannot start PLANNED task while another task is PAUSED (start path doesn't distinguish paused-parent from active-executing)
- Edit click vs multi-select checkbox conflict on PLANNED rows (unverified)
- Stale session recovery job not firing as designed (APScheduler verification needed)
- Ghost timer banner persists after OpenClaw mark-abandoned (Redis key cleanup on skip path)

P1 pre-alpha (selected — see dogfood P1 for full list):
- Backend-unreachable graceful retry UI
- micro_mirror and calibration_nudge display after stop
- ReflectionModal completion % ungate (remove earlyStop guard)
- Tooltips on readiness/focus/delta arrow
- is_future_task warning surfaced in UI
- Active timer banner "12h+ paused" cap

---

## Phase 5 — Onboarding (April 30 launch → May ~14)

**Goal:** Ship the alpha to 10-30 trusted users. Instrument collection, consent flow, first-run experience.

**Entry gate:** All P0 dogfood items FIXED. Operator browser-verified.

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

**If retention validates (users return after week 3):**
- Proceed to Phase 6 (calibration)
- Begin Paper 1 data collection (H1 requires 30-60 days, 60+ paired sessions)
- Paper 2 (cascade failure) may be publishable by June if signal holds

**If retention fails:**
- Diagnose: is it the measurement friction? The UX? The value proposition?
- Middle-phase retention mechanism candidates (see dogfood P2): insight tiering, lightweight social accountability, predictive intervention
- May pivot to Phase 1A (delta-only, productivity-first) if the metacognitive layer is the friction source

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

- category_type field (estimable vs time_anchored) — required before H1 analysis
- is_anchor boolean on prayer/sleep tasks
- Trigger field for implementation intentions (clock / after_task / contextual)
- LLM-powered task creation via OpenClaw bridge (secondary path, always showing parsed result for confirmation)
- Residue-based cascade model evaluation against probability-based (fit both, ship better one)
- Archetype re-fit cycle (periodic Bayesian update vs archetype(t) function)

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
| Native mobile apps | Post-PWA | PWA proves 80% of form factor at 10% cost |
| sleep_hours field | v1.5+ | Leading indicator for cascade, but adds daily friction |
| Multi-user collaboration | Post-retention | Social-obligation confound, irrelevant until single-user value proven |
| pre_task_readiness reactive measure note | Paper 1 methods | Framing change, not measurement change |
| self_reflection → planning rename | Phase 6 migration batch | Cosmetic, bundle with category_type |
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

## Commit Statistics Snapshot

As of April 14, 2026 (see `project_history.md` for full history):
- ~120 commits on main
- 19 Alembic migrations
- 94 backend tests passing
- 4 frontend routes (/today, /calendar, /table, /settings)
- 5 P0 dogfood items remaining before alpha
