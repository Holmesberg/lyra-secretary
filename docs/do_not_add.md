# Do Not Add

This file lists architectural directions explicitly considered and rejected. New ideas matching these patterns should be checked against this file before being added to dogfood findings.

---

## GPS/WiFi fingerprinting
**Rejected.** Crosses the surveillance vs measurement instrument boundary. Lyra measures self-reported behavioral patterns, not location. Adding location tracking changes the product's trust category from "personal journal" to "tracking app." The custodianship trust frame (see phase_6_architecture_backlog.md) depends on the user perceiving Lyra as a personal-history tool, not a monitoring tool. Location data also introduces GDPR Art. 9 special-category complications that are disproportionate to any analytical value.

## BCI-first architecture
**Deferred to Path B (October hackathon).** Not rejected permanently, but rejected as a current-phase priority. Research narrative requires retention validation before adding a second signal stream. BCI integration decision scheduled for June, with October hackathon as the preferred implementation window. Adding BCI before proving the behavioral-data-only hypothesis muddies the research story — if the combined system works, you can't attribute the effect. Prove the base case first.

## Gamification: streaks, badges, leaderboards, XP, points
**Rejected.** QS (Quantified Self) literature post-2017 consistently shows gamification elements produce novelty-driven engagement that masks retention failure. Streaks create anxiety-driven logging (data quality degrades as users log to preserve streaks, not to measure). Badges reward frequency, not depth. Leaderboards are structurally incompatible with a single-user research instrument. XP/points reward volume, which corrupts the planning signal because users log to accumulate rather than to measure. Lyra's retention mechanism must come from insight value, not extrinsic reward loops.

**PERMITTED: measurement-state progress framing.** This is structurally different from gamification and is a required Phase 4.5 Tier 1 shipping item (see `docs/archive/legacy/planning/building_phases.md`). Permitted surfaces:

- "Insights unlock in N more sessions" — honest statement about when the instrument has enough data to say something.
- "Archetype unlocks at 30 sessions in ≥2 categories" — describes the measurement gate, not a user achievement.
- Per-category confidence tier on bias_factor ("low confidence: 8/30 sessions" → "medium: 18/30" → "published: 30+") — describes the data, not the user.

The test that distinguishes permitted from rejected: *does this surface make a true statement about what the instrument can do right now?* If yes, it is progress framing (permitted). If instead it tells the user something about themselves ("You've logged 7 days in a row!", "You earned 120 XP this week!"), it is gamification (rejected). Progress framing is not optional polish — it is the mechanism by which Lyra tells users *why* they can't see insights yet, which is what prevents them from concluding the product is empty during the cold-start window. See `docs/archive/legacy/planning/phase_6_architecture_backlog.md` §"Measurement-state progress is not gamification (D2)" for the full distinction and application rule.

**PERMITTED: progressive revelation as measurement-state milestone.** When the instrument accumulates enough data to produce a trustworthy claim, revealing that claim to the user IS the reward. Example: archetype assignment unlocked at session 5-7 with medium confidence, reclassification shown at session 15-20 if behavior diverges. The user is rewarded with increasing precision about themselves, not with artificial milestones.

Distinguishing test: does the reward require the user to do something (behavior-reinforcement gamification, rejected) or does the reward deliver information about the user's own behavior (progressive revelation, permitted)?

See `docs/design_patterns/notification_patterns.md §Progressive Revelation Pattern` for the notification-surface characteristics (threshold-triggered, one-time/rare, honestly-framed confidence tier, optional dismissal without data loss).

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

## Auto-suggested task durations without provenance
**Rejected.** A system-suggested duration that is accepted unchanged and then
treated as the user's independent estimate corrupts the planning signal. If
the system suggests "45 min based on your history," the user's subsequent
estimate is anchored (Tversky & Kahneman 1974) and no longer measures their
independent planning ability.

**Permitted only with provenance and clean-data exclusion.** Low-authority
duration priors may appear as editable product scaffolding when the row records
the suggestion source, user decision, exposure state, and whether the user
accepted or edited it. Unedited accepted suggestions must be excluded from
pure user-estimate calibration unless a successor clean-data profile explicitly
admits them as a separate source class.

Distinction:

- **Independent user estimate:** eligible for planning-calibration baselines
  if all other clean-data rules pass.
- **System-suggested accepted duration:** product-useful but contaminated for
  independent-estimate claims.
- **System-suggested edited duration:** may become a distinct negotiation
  signal, not a pure user estimate.

Bias-factor feedback remains safest after the task. Any pre-task duration
suggestion is an exposure surface.

## Mobile native apps before PWA proves form factor
**Rejected as current priority.** PWA support (Phase 7, ~4 hours) proves 80% of the mobile form factor hypothesis. Native apps require ongoing maintenance burden (App Store review, platform-specific bugs, CI pipeline per platform) that is disproportionate to a pre-retention research instrument. If PWA retention data shows mobile is critical, native apps enter the backlog. Not before.

## Hardcoded default values for any research-relevant field
**Rejected.** Defaults bias measurement. If `pre_task_readiness` defaults to 3, users who skip the prompt produce data indistinguishable from users who genuinely feel neutral. Every research-relevant field must be explicitly provided or explicitly null — never silently filled. This applies to: readiness, reflection, completion percentage, pause reason, pause initiator, unplanned reason, void reason. Backend enforces via required fields or nullable columns; frontend enforces via mandatory prompts before progression (Hard Rules 3, 4, 5, 9 in SKILL.md).

These are **structural invariants** — per `docs/design_patterns/rules_vs_agency.md`, they protect measurement integrity and are non-negotiable regardless of user preference. Distinct from behavioral constraints (overridable with `force=true` or explicit user confirmation), invariants have no override path.

## Predictive notifications that default research-relevant fields
**Rejected.** A predictive notification ("you usually pause now") whose accept action triggers a state change MUST NOT supply defaults for any research-relevant field as part of the accept path. For pause prediction specifically: the Telegram "pause" flow routes through the existing OpenClaw agent, which asks `pause_initiator` and `pause_reason` before calling the pause API. A hypothetical design where tapping an inline-keyboard button called `/v1/stopwatch/pause` with `pause_reason='prediction_accepted'` would be REJECTED — it defaults a research field AND conflates instrument-suggested with user-reported. This is structurally a Hard Rule violation (Hard Rules 3/4/5 in SKILL.md) and a `do_not_add.md §Hardcoded default values` violation at once. See `docs/design_patterns/notification_patterns.md §Predictive Notifications` for the full rule.
