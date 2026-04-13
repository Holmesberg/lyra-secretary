# Do Not Add

This file lists architectural directions explicitly considered and rejected. New ideas matching these patterns should be checked against this file before being added to dogfood findings.

---

## GPS/WiFi fingerprinting
**Rejected.** Crosses the surveillance vs measurement instrument boundary. Lyra measures self-reported behavioral patterns, not location. Adding location tracking changes the product's trust category from "personal journal" to "tracking app." The custodianship trust frame (see phase_6_architecture_backlog.md) depends on the user perceiving Lyra as a personal-history tool, not a monitoring tool. Location data also introduces GDPR Art. 9 special-category complications that are disproportionate to any analytical value.

## BCI-first architecture
**Deferred to Path B (October hackathon).** Not rejected permanently, but rejected as a current-phase priority. Research narrative requires retention validation before adding a second signal stream. BCI integration decision scheduled for June, with October hackathon as the preferred implementation window. Adding BCI before proving the behavioral-data-only hypothesis muddies the research story — if the combined system works, you can't attribute the effect. Prove the base case first.

## Gamification: streaks, badges, leaderboards
**Rejected.** QS (Quantified Self) literature post-2017 consistently shows gamification elements produce novelty-driven engagement that masks retention failure. Streaks create anxiety-driven logging (data quality degrades as users log to preserve streaks, not to measure). Badges reward frequency, not depth. Leaderboards are structurally incompatible with a single-user research instrument. Lyra's retention mechanism must come from insight value, not extrinsic reward loops.

## Social feeds, sharing
**Rejected.** Lyra is a single-user research instrument. Social features change the incentive structure from honest self-measurement to performance for an audience. The discrepancy hypothesis (H1) requires that self-reports reflect genuine self-assessment, not socially desirable reporting. Even optional sharing changes how users fill in readiness/reflection scores (Hawthorne effect, already documented as VT-1 in MANIFESTO).

## LLM-parsed task creation as primary input
**Rejected as primary path.** LLMs parsing natural language into task fields hide data quality issues — the user doesn't see what was parsed, doesn't correct subtle errors, and the system trains on potentially wrong structured data. The explicit-field creation path forces the user to confront their own planning assumptions (duration, start time), which is itself a measurement moment. LLM-assisted creation is a Phase 6 candidate via OpenClaw bridge, but always as a secondary path that shows the user the parsed result for confirmation, never as a transparent pass-through.

## Multi-user collaboration / teams
**Rejected pre-retention.** Collaboration features are irrelevant until single-user retention is validated. Adding team dynamics before proving individual value creates a confound — users may retain because of social obligation, not because the instrument is useful. Revisit post-retention validation (after May 21 projected answer date).

## Hybrid planning-execution UI collapsing PLANNED and EXECUTING states
**Rejected.** State machine clarity is load-bearing. The PLANNED -> EXECUTING -> EXECUTED progression is not a UX convenience — it is the measurement instrument. Collapsing states hides the initiation moment (when the user actually starts vs when they planned to start), which is the source of `initiation_delay_minutes`, one of the core behavioral signals. The state machine boundary is where discrepancy data is generated. Making it invisible makes the data invisible.

## Aggressive notification schemes
**Rejected.** Lyra's notification philosophy is minimal and informational: timer overflow alerts (2 min cycle), reminders (1 min cycle, single fire), overdue detection (30 min cycle). No engagement-driving notifications, no "you haven't logged today" guilt prompts, no streak-preservation nudges. Notifications that serve the system's retention goals rather than the user's information needs violate the custodianship trust frame.

## Auto-suggested task durations
**Rejected.** Would corrupt the user's own planning signal. The `planned_duration_minutes` field must reflect the user's genuine estimate, not a system suggestion. If the system suggests "45 min based on your history," the user's subsequent estimate is anchored (Tversky & Kahneman 1974) and no longer measures their independent planning ability. The calibration architecture (Phase 6) depends on observing uncontaminated planning inputs. Bias-factor feedback is surfaced AFTER the task, never before.

## Mobile native apps before PWA proves form factor
**Rejected as current priority.** PWA support (Phase 7, ~4 hours) proves 80% of the mobile form factor hypothesis. Native apps require ongoing maintenance burden (App Store review, platform-specific bugs, CI pipeline per platform) that is disproportionate to a pre-retention research instrument. If PWA retention data shows mobile is critical, native apps enter the backlog. Not before.

## Hardcoded default values for any research-relevant field
**Rejected.** Defaults bias measurement. If `pre_task_readiness` defaults to 3, users who skip the prompt produce data indistinguishable from users who genuinely feel neutral. Every research-relevant field must be explicitly provided or explicitly null — never silently filled. This applies to: readiness, reflection, completion percentage, pause reason, pause initiator, unplanned reason, void reason. Backend enforces via required fields or nullable columns; frontend enforces via mandatory prompts before progression (Hard Rules 3, 4, 5, 9 in SKILL.md).
