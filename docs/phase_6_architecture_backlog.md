# Phase 6 Architecture Backlog

> Historical/parked backlog. This document preserves April Phase 6 design
> context, but it is not current implementation authority during the
> freeze-closure refactor. Do not use it to authorize runtime features, schema
> additions, new user-facing insights, confrontation/readiness routing,
> passive tracking, OpenClaw/GPT wiring, behavior-transition equations, or
> cohort expansion. Current authority lives in `docs/current_transition_state.md`,
> `docs/AUTHORITY.md`, and `docs/architecture_freeze_priority_hold_2026_05_20.md`.

> R5a extraction rule: all progress-framing, classifier, router,
> confrontation/readiness, behavior-equation, passive tracking, schema,
> insight-surface, and "ships" language below is parked design history. It is
> not current implementation permission and must not be used to add runtime
> behavior, user-facing claims, or schema during freeze closure.

## Orienting Principles (read before designing any Phase 6 component)

### The branch-laying mechanism
Lyra's output layer is not "system that displays patterns to users." It is "environment that lays branches at appropriate confrontation levels and allows the walker's discernment to choose which to follow." Imperfect-but-honest branches activate the walker's reasoning. Perfect-precise statements produce passive receipt. The mechanism is timing + multiple-distinguishable-precision, not correctness. Designed across April 13 conversation. Calibration architecture implements the timing dimension; output dialect design implements the multiple-precision dimension.

### Custodianship trust frame
Lyra has crossed from utility to custodianship. Users form personal-history expectations (analogous to Apple Photos, Bear, Day One) rather than productivity-tool expectations (Notion, Linear). UX conventions must follow custodial product references, not productivity ones. This affects backup architecture, destructive UI patterns, error states, data-access surfaces, and trust signals throughout the product. First operationalized in the two-stage major-warning delete account pattern (April 14).

### Data sovereignty surface
The Settings page is not a junk drawer. It is the named architectural unit where users verify their data exists, extract it, leave the system, and see backup status. New items added to Settings must contribute to data sovereignty coherence. Items that don't fit data sovereignty go elsewhere.

### Architect-side constraints (load-bearing)
The calibration architecture and any environment-layer feature requires more careful building than other components because the same mechanism that enables guided arrival at honest reasoning could guide arrival at something else if architect-side constraints drift. External human accountability required. Not documented further here. Operator holds the deeper specification.

### Measurement-state progress is not gamification (D2)
Surfacing "insights unlock in N sessions" or "archetype unlocks at 30 sessions in ≥2 categories" or a confidence-tier indicator on per-category bias_factor is **permitted** and **encouraged** as a retention mechanism. These are honest statements about when the instrument has enough data to say something. They are structurally different from streaks, badges, XP, points, and leaderboards (all rejected — see `docs/do_not_add.md` §Gamification). The distinction is load-bearing and should be checked against every new UI surface:

- **Progress framing (permitted):** describes a *property of the measurement state* — "this category has 22/30 sessions, bias_factor publishes at 30." Truth-preserving. Frames the wait in terms of what the user is waiting *for*, not how long they've been logging.
- **Gamification (rejected):** describes a *property of the user* that the system will reward — streaks reward frequency, badges reward milestones, points reward logging volume. Incentive-shaped. Corrupts data quality because users log to preserve the reward structure, not to measure.

When in doubt, apply the test: *does this surface make a true statement about what the instrument can do right now?* If yes, it is progress framing. If it instead tells the user something about themselves ("You've logged 7 days in a row!"), it is gamification. Progress framing ships in the retention-mechanism tier (`docs/building_phases.md` §Phase 4.5 Tier 1, gap fix G4). Gamification is not reopened as a design direction by this section.

---

# Error-Rate Gradual Exposure Calibration (Phase 6+)

## Origin

Designed across April 12-13 in operator + assistant runtime + ChatGPT conversation. Not implemented. Schema and analytics layer to be built post-retention validation. This document preserves the design so it doesn't have to be reconstructed.

## Core Principle

Lyra's deeper architecture is not "measurement instrument that displays patterns to users." It's "environment that creates conditions where users arrive at honest reasoning about their own patterns through their own discernment." The mechanism is layering branches at appropriate levels of confrontation based on the user's measured readiness to walk them.

Confrontation at the wrong moment causes churn. Confrontation at the right moment causes growth. The system must measure which moment a user is in before choosing what to surface.

## Calibration as Learning Velocity, Not Performance

Calibration is NOT "how often the user is wrong." It is "how quickly and consistently the user updates their future behavior after being shown they were wrong, within the same task category."

Triplet measured over time:
  Error -> Exposure -> Adjustment

- Error: user's self-prediction or planning was wrong (high delta, high discrepancy, large initiation_delay)
- Exposure: system surfaces this (micro_mirror, calibration_nudge, or future Phase 6 branch surfaces)
- Adjustment: in next-N sessions for the SAME category, does behavior shift toward the data?

## Measurement: V1 + V3 + V5 Composite

Three signals combined infer V4 (distance-walked-per-branch) without requiring explicit branch-walking input. Total new user-facing input: one settings preference (V5). Philosophical depth emerges from correlating three low-friction streams.

### V1 — Measurement-Trust Velocity
Passive, zero-friction. Already-collected data.

For each user, per task category:
  bias_factor_predicted = computed from historical delta
                          per category x time_of_day
  trust_lag = (planned_duration on next task in category)
              vs (bias_factor-adjusted expected duration)

A user whose new plans drift toward the bias-adjusted expectation is gaining trust in their own data. A user whose plans don't shift after exposures is at baseline trust.

Measurable from Day 1 of alpha. No new schema needed.

### V3 — Engagement with Surfaced Data
Requires light instrumentation, no user input.

For each surfaced reflection (micro_mirror, calibration_nudge):
  - Was it viewed (UI tracking)?
  - Time-to-dismiss
  - Did the user's next-task plan reflect the surfaced finding?
  - Did readiness rating shift in the predicted direction?

Phase 6 schema additions:
  - reflection_view_log table: user_id, reflection_type, viewed_at, dismissed_at, dwell_seconds
  - Correlation analytics: post-exposure behavior delta

### V5 — Silence Preference (Adaptive)
One settings preference, four levels:
  - "just metrics" (delta + discrepancy only)
  - "metrics + reflections" (current default)
  - "metrics + reflections + patterns"
  - "full depth"

Critical: track the change in preference over time. A user who moves from "just metrics" to "full depth" over 3 weeks is demonstrating calibration development. A user moving the other direction is signaling disengagement or overwhelm.

Phase 6 schema:
  - users.exposure_preference (enum, default "metrics + reflections")
  - users.exposure_preference_history (JSON or separate table tracking changes with timestamps)

## User Response Typology (from ChatGPT Apr 13)

Users classified by their behavioral response to error exposure, not by raw performance:

### Type 1: Calibrators
- Error decreasing over time within categories
- Adjustments consistent and proportionate
- Ready for branch-dialect prompts (philosophical confrontation)

### Type 2: Acknowledge-but-don't-change
- High discrepancy awareness (signed_discrepancy consistent across exposures)
- No behavioral shift (planned_duration doesn't move)
- THIS is where philosophical confrontation has highest traction — they already know, they need existential weight to close the gap between knowing and acting

### Type 3: Illusion Preservers
- Repeat the same planning despite errors
- Readiness ratings don't update across category exposures
- Defended; confrontation will trigger exit, not growth
- Need grounding/mirror prompts only, no confrontation

### Type 4: Overcorrectors
- Wild swings in planning post-exposure
- High variance in adjustments
- Need stabilization-anchoring prompts, NOT confrontation
- Adding this type breaks the linear "low capacity -> high capacity" model — Type 4 isn't lower capacity, it's a different response pattern

Classification computed per-user per-category over rolling 30-session window. Same user can be Type 1 in academic tasks and Type 3 in development tasks simultaneously.

## Confrontation Readiness Score

Composite gating variable:
  readiness =
    consistency_of_logging
  + calibration_rate
  - variance_in_adjustments
  - avoidance_signals (skips, voids after errors)

Negative terms penalize Type 4 (variance) and catch Type 3 avoidance behavior (skipping or voiding tasks after error events, not at baseline). Both signals latent in current data; need explicit per-category post-error computation in Phase 6 analytics.

Thresholds:
- Low -> metric dialect only ("you ran +35min")
- Medium -> soft branches ("Tuesday and Thursday show similar patterns. Worth sitting with?")
- High -> philosophical branches ("you're preserving a planning identity your data no longer supports")

## Gamed Calibration Detection

Failure mode: user inflates planned_duration estimates to beat the system, producing apparent calibration improvement (delta -> 0) while actual self-knowledge hasn't sharpened.

Cross-check:
  if delta improves AND execution_efficiency drops:
      flag as gamed_calibration

Where execution_efficiency = actual work output per unit of time. Hard to measure directly without explicit output tracking. Proxy: completion_pct x actual_duration trends — if completion_pct stable but actual_duration inflating, gaming is likely.

Phase 6 schema:
  - Per-user gamed_calibration_flag computed nightly
  - Excluded from primary calibration analysis when flagged

## Surface Ordering by Calibration State

Same data, different output dialect based on user state:

Low calibration:
  "You underestimated by 2.3x on dev tasks"

Medium calibration:
  "You consistently underestimate dev tasks. Try doubling planned time."

High calibration:
  "You're preserving a planning identity that your data no longer supports."

Type 2 specifically (Acknowledge-don't-change):
  "You've seen this pattern 7 times. What stops you from planning differently?"

The last variant only ships to users with evidence of non-adjustment over time. Otherwise it's noise or arrogance.

## Architectural Constraint

A system that calibrates exposure based on user readiness is, by construction, a system that could mis-calibrate in either direction:
- Over-expose (confrontation damage, churn)
- Under-expose (paternalism that prevents growth)

Both failure modes are invisible from inside the system. External human accountability required to catch drift. Operator commits to weekly review of exposure distributions across cohort post-alpha.

This is where the load-bearing moral weight on the architect lands. Calibration layer is built more carefully than any other Phase 6 component.

## Friction Cost Summary

V1: Zero. Already-collected data, passive computation.
V3: Minimal. UI instrumentation for view tracking. No user input.
V5: One settings preference. User can ignore.

Total new user-facing input across the calibration architecture: one settings toggle. Philosophical depth emerges from correlating low-friction streams, not from extracting high-friction reflection input.

## Implementation Sequence (Phase 6+)

1. Schema: reflection_view_log, users.exposure_preference, users.exposure_preference_history, gamed_calibration_flag
2. Analytics: per-category post-error behavior delta computation, response-type classification job, confrontation readiness score nightly
3. Settings UI: silence preference selector with the four levels
4. Output layer: surface dialect router that selects prompt variant based on user state vector (trust layer, meta layer, engagement layer)
5. Drift monitoring: weekly operator review of exposure distribution, alert on outlier patterns

## Pre-registered Constraints

Calibration layer never ships to a user before that user has 30 sessions of data per category (cold-start problem). Default exposure during cold start: "metrics + reflections" with no branches.

User can always opt out via V5 silence preference. Setting is preserved across sessions.

System never confronts a user in their first 14 days of usage regardless of measured readiness, to allow the novelty window to establish baseline trust.

## Calibration Nudge at Task Creation (D3)

Decision locked: April 14, 2026. Partially ships in Phase 4.5 Tier 1 as a pre-retention seed of the calibration architecture; the full per-category confidence model lands in Phase 6.

### What it is

At task creation time, when the user enters `planned_duration_minutes`, the system queries the current bias_factor for that (user × category × time_of_day) triplet and, if it predicts a ≥25% overrun (bias_factor ≥ 1.25), surfaces a pre-commit nudge:

> "Your dev tasks at this time of day have run ~1.8× planned over the last 30 sessions. This task would likely execute closer to 72 minutes than 40 minutes. Keep at 40, adjust to 72, or dismiss?"

The nudge offers three affordances:
- **Keep the plan** — no change. User's estimate is locked. Event logged (`nudge_dismissed`).
- **Adjust to prediction** — system replaces `planned_duration_minutes` with the bias-adjusted value. Event logged (`nudge_accepted`). Flag for gamed-calibration detection: if the user ALWAYS accepts the prediction, they're outsourcing planning to the model and their self-prediction signal is extinct.
- **Dismiss** — closes the modal, keeps the plan. Event logged (`nudge_dismissed_silent`).

### Why at creation, not at stop

Bias-factor feedback surfaced at stop (the current `calibration_nudge` path) tells the user "you overran." Feedback at creation tells the user "you are about to overrun." Both are useful, but the creation-time surface is the only one that intervenes *before* the planning act is contaminated by the anchoring effect of whatever duration the user first typed. Surfacing at creation is also the only timing that influences the session's behavior — surfacing at stop only influences the *next* session.

### Architectural constraints

- **Never auto-fill as an independent user estimate.** The field starts empty.
  The user types a number. Only after the user has committed a number does the
  nudge fire. This preserves the uncontaminated planning signal. Any future
  pre-task duration prior must be recorded as system-suggested, exposed, and
  excluded from pure user-estimate calibration unless a successor profile
  admits it (see `docs/do_not_add.md` §Auto-suggested task durations without
  provenance).
- **Cold-start protection.** Nudge suppressed for (user × category) combinations with < 10 sessions. Surface the "Insights unlock in N sessions" progress framing instead (gap fix G4). Maps to calibration pre-registered constraint §"30 sessions per category" but relaxed to 10 for the *nudge surface*, which is a lower-stakes metric-dialect surface — philosophical branches keep the 30-session gate.
- **No escalation on dismiss.** Dismissal is not nagged. The user saw the prediction, chose to proceed, that choice is itself V1 signal (measurement-trust velocity — a user who repeatedly overrides the model and overruns is an Illusion Preserver or Overcorrector, see §User Response Typology).
- **V3 engagement signal.** Every nudge render, dismissal, and acceptance logs to `reflection_view_log` with `reflection_type = 'creation_nudge'`, `viewed_at`, `dismissed_at`, `dwell_seconds`, `outcome` (kept/adjusted/dismissed). Feeds the Phase 6 response-type classifier.

### Phase 4.5 Tier 1 v1 shipping scope

For pre-alpha, the nudge is gated behind a simple rule (no Phase 6 analytics layer yet):

- bias_factor computed per (user × category) with no time_of_day split (session counts too low)
- Fire threshold: bias_factor ≥ 1.25 AND session count for that (user × category) ≥ 10
- Dismiss/accept logged to a minimal `reflection_view_log` table schema (creation_nudge event type only; other event types added in Phase 6)
- No auto-correction. Always user-driven.

The Phase 6 version layers on time_of_day splits, Bayesian shrinkage with archetype prior, confidence intervals around the predicted range, and surface-dialect routing via the response-type classifier.

## Gradual Exposure → Notification Timing Mapping (D6)

Decision locked: April 14, 2026. v1 ships in Phase 4.5 Tier 1 with *uniform* exposure for all users. The V1+V3+V5 composite signal is *logged* from day one so that Phase 6 has training data, but notification timing is **not** yet personalized. Per-user routing activates in Phase 6 after 30 sessions per category.

### The mapping (Phase 6 target state)

Each of the four notification types (see `docs/design_patterns/notification_patterns.md`) has a timing profile that the Phase 6 router can widen, narrow, delay, or suppress based on the user's confrontation readiness score (§Confrontation Readiness Score) and response type (§User Response Typology).

| Notification type | Baseline timing (v1 uniform) | Phase 6 routed adjustment |
|---|---|---|
| Toast (`micro_mirror`) | Fires on every stop. 8s auto-dismiss. | Calibrators: keep baseline. Type 2 (Acknowledge-don't-change): extend to 12s, allow user to pin. Type 3 (Illusion Preserver): suppress after 5 consecutive dismissals without planning change — mirror dialect only on request. Type 4 (Overcorrector): suppress during high-variance periods to avoid amplifying swings. |
| Modal (`calibration_nudge` at stop, `calibration_nudge` at creation) | Fires when bias_factor ≥ 1.25 (creation) or when signed_discrepancy exceeds threshold (stop). | Calibrators: escalate to philosophical-dialect variant after 30 sessions in category with decreasing error. Type 2: escalate to "You've seen this 7 times — what stops you?" variant (per §Surface Ordering). Type 3: suppress entirely, mirror dialect only. Type 4: suppress during high-variance windows. |
| Inline warning (`is_future_task`, state-transition error) | Fires on action that would cross a state-machine guard. Never suppressed — correctness-critical. | No user-level routing. This is not an exposure-layer surface; it is an operational correctness surface. |
| Banner (`insight fired`, `session milestone`, "insights unlock") | Fires once per insight, once per 30-session milestone. Dismissible, saved to /insights history. | Calibrators: unlocks philosophical-dialect insight tier earlier. Type 3: unlocks same tier later, with softer framing. Type 4: one-time stabilization banner after a detected overcorrection streak. |

### v1 logging scope (Phase 4.5 Tier 1)

Even under uniform exposure, v1 logs three signal streams so the Phase 6 router has data to train on when it activates:

- **V1 (Measurement-Trust Velocity):** already computable from existing `planned_duration_minutes` and bias_factor history. Nightly job writes per-user per-category trust_lag scalar. No new schema.
- **V3 (Engagement with Surfaced Data):** `reflection_view_log` table, minimal schema for Phase 4.5 (reflection_type, viewed_at, dismissed_at, dwell_seconds, outcome). Extended to include all surface types in Phase 6.
- **V5 (Silence Preference):** NOT shipped in Phase 4.5. Settings surface for the four-level preference lands in Phase 6 alongside the routing layer. Default for all v1 users is "metrics + reflections" (current uniform exposure).

### Why uniform in v1

Per-user routing requires 30 sessions per category (pre-registered cold-start constraint, §Pre-registered Constraints). No alpha user will cross that threshold before mid-May. Shipping the routing layer with empty training data produces either random assignment (bad science, bad UX) or operator-guessed heuristics (drift source — see §Architect-side constraints). The correct behavior is: uniform exposure, log signals, activate routing only when the data supports it.

### Interaction with architect-side constraint

D6 is the Phase 6 component that most directly enables mis-calibration in either direction (§Architectural Constraint). When the routing layer activates, it must ship with: (a) operator weekly review of exposure distributions, (b) per-user override via V5 silence preference, (c) no routing of inline-warning-class notifications regardless of user state, (d) suppress-on-ambiguity default — if the user's response type is not confidently classified, fall back to baseline uniform exposure rather than guessing.

## Readiness-Drift Signal (Phase 6)

Decision locked: April 14, 2026, as part of the feedback/output-loop audit disposition pass.

### What exists now (Phase 4.5)

The `original_pre_task_readiness` audit column is written on every call to `POST /v1/stopwatch/correct-readiness`. The original value is retained; the new value overwrites `pre_task_readiness` on the session. The column is currently never read — it is audit-only.

### What Phase 6 adds

A new analytics signal: **readiness drift rate** per user per category.

```
drift_rate(user, category) =
    count(sessions where original_pre_task_readiness IS NOT NULL)
  / count(sessions where pre_task_readiness IS NOT NULL)
```

Where non-null `original_pre_task_readiness` means the user corrected their readiness post-hoc (within-session or at reflection). High drift rate is itself a metacognitive signal: the user entered the task with one self-model and updated it during execution. This distinguishes two response patterns that look identical in `signed_discrepancy` alone:

- **Real-time updater:** rates readiness 4 at start, realizes mid-task they were actually 2, corrects. `signed_discrepancy` ends up reflecting the corrected rating.
- **Retrospective-only reporter:** rates readiness 4 at start, never corrects, reports focus 2 at reflection. `signed_discrepancy` looks the same.

These are different cognitive patterns. The retrospective-only reporter is a candidate Type 3 (Illusion Preserver — aware of the gap only at reflection). The real-time updater is more often a Calibrator.

### Phase 6 integration

- Drift rate feeds into the §Confrontation Readiness Score as a positive term (correction behavior is evidence of self-model updating).
- Surfaced in `/insights` as a percentage ("You corrected your initial readiness on 18% of dev sessions this month"). Metric dialect only.
- V1 (Measurement-Trust Velocity) gets a secondary input: users who trust their corrected rating over their initial rating are gaining measurement trust.

### Why not Phase 4.5

The signal is latent in current data and useful only once response-type classification ships. Surfacing the percentage alone with no interpretive frame is a number without context — premature. Ships when the §User Response Typology router lands.

## Interruption Chain Visualization (Phase 6)

Decision locked: April 14, 2026.

### What exists now

Commit 2f4abed wired up `parent_task_id` and `interruption_type` on the Task model. The interruption flow in SKILL.md links an interrupting task to its parent automatically. Backend stores the graph; frontend never renders it.

### Phase 6 surface

A view (likely a card on `/insights`, possibly a dedicated `/insights/interruptions` subroute) that renders interruption chains as:

- Per-week summary: "You interrupted dev work 4 times this week with admin tasks, averaging 18 minutes each."
- Per-category breakdown: which task categories interrupt which most often (parent category × child category heatmap).
- Weighted by total interrupting time, not raw count (one 90-minute interruption matters more than six 5-minute ones).

### Why rough rendering is worse than nothing for trusted users

An interruption chain is a relational structure. Rendering it as a flat list of `parent_task_id` links is technically accurate and unreadable. Rendering it as a tree requires design work (which layout? collapse deep chains? group by day or by category?). Shipping a flat-list v1 to trusted alpha users primes them to read the feature as "Lyra notices interruptions" but doesn't deliver enough to influence behavior — the worst of both: cost of the surface, none of the payoff.

Design + ship together in Phase 6, not in pieces.

### Phase 6 constraints

- No routing by user response type at first (unlike toast/modal/banner). Interruption data is factual, not exposure-layer.
- Must respect V5 silence preference: "just metrics" users see count + time only; "full depth" users see the full graph.
- Interruption counts are a V3 signal: does surfacing interruption patterns change the user's next-week interruption count? Prediction-first logging (see §Pre-registered Constraints in the Phase 6 base spec).

## Open Questions for Phase 6 Implementation

- How is execution_efficiency measured for the gamed-calibration check? Proxy via completion_pct x actual_duration trends, or explicit output input required?
- Does the response-type classification use hard boundaries or soft probabilistic membership? Probabilistic likely cleaner.
- Does the system ever explain its confrontation readiness score to the user? Argument for: transparency. Argument against: makes the system gameable in a different way.
- How does the calibration architecture interact with cohort changes (operator's data, pre_alpha_trusted, alpha_v1)? Each cohort may need its own calibration baseline.

## Authority

Designed by operator (Aly Nasser) in conversation with assistant runtime (hosted model provider) and ChatGPT (OpenAI), April 12-13, 2026. Not implemented. Phase 6 work, post-retention validation. This document is the design specification, not a build plan.
