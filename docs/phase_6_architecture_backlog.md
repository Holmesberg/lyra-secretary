# Phase 6 Architecture Backlog

## Orienting Principles (read before designing any Phase 6 component)

### The branch-laying mechanism
Lyra's output layer is not "system that displays patterns to users." It is "environment that lays branches at appropriate confrontation levels and allows the walker's discernment to choose which to follow." Imperfect-but-honest branches activate the walker's reasoning. Perfect-precise statements produce passive receipt. The mechanism is timing + multiple-distinguishable-precision, not correctness. Designed across April 13 conversation. Calibration architecture implements the timing dimension; output dialect design implements the multiple-precision dimension.

### Custodianship trust frame
Lyra has crossed from utility to custodianship. Users form personal-history expectations (analogous to Apple Photos, Bear, Day One) rather than productivity-tool expectations (Notion, Linear). UX conventions must follow custodial product references, not productivity ones. This affects backup architecture, destructive UI patterns, error states, data-access surfaces, and trust signals throughout the product. First operationalized in the two-stage major-warning delete account pattern (April 14).

### Data sovereignty surface
The Settings page is not a junk drawer. It is the named architectural unit where users verify their data exists, extract it, leave the system, and see backup status. New items added to Settings must contribute to data sovereignty coherence. Items that don't fit data sovereignty go elsewhere.

### Architect-side constraints (load-bearing)
The calibration architecture and any environment-layer feature requires more careful building than other components because the same mechanism that enables guided arrival at honest reasoning could guide arrival at something else if architect-side constraints drift. External human accountability required. Not documented further here. Operator holds the deeper specification.

---

# Error-Rate Gradual Exposure Calibration (Phase 6+)

## Origin

Designed across April 12-13 in operator + Claude + ChatGPT conversation. Not implemented. Schema and analytics layer to be built post-retention validation. This document preserves the design so it doesn't have to be reconstructed.

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

## Open Questions for Phase 6 Implementation

- How is execution_efficiency measured for the gamed-calibration check? Proxy via completion_pct x actual_duration trends, or explicit output input required?
- Does the response-type classification use hard boundaries or soft probabilistic membership? Probabilistic likely cleaner.
- Does the system ever explain its confrontation readiness score to the user? Argument for: transparency. Argument against: makes the system gameable in a different way.
- How does the calibration architecture interact with cohort changes (operator's data, pre_alpha_trusted, alpha_v1)? Each cohort may need its own calibration baseline.

## Authority

Designed by operator (Aly Nasser) in conversation with Claude (Anthropic) and ChatGPT (OpenAI), April 12-13, 2026. Not implemented. Phase 6 work, post-retention validation. This document is the design specification, not a build plan.
