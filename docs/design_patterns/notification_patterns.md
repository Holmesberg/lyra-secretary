# Notification Patterns

**Owner:** Operator
**Created:** April 14, 2026 (feedback/output loop architecture lock)
**Status:** Canonical. Any new Lyra notification surface must conform.

This document is referenced by `docs/building_phases.md §Phase 4.5 Tier 1`, `docs/phase_6_architecture_backlog.md §Gradual Exposure → Notification Timing Mapping (D6)`, and the Phase 4.5 PR reviews. If you are about to add a new notification, banner, toast, or modal — read this first.

---

## Principles (Windows-style, not mobile-app-style)

Lyra's notification philosophy mirrors desktop OS conventions, not mobile-app engagement patterns. The product is a measurement instrument with custodian trust properties (see `docs/phase_6_architecture_backlog.md` §Custodianship trust frame), not an engagement-driven app. Four principles, load-bearing:

1. **Non-blocking.** Notifications do not interrupt the user's primary action. Timer still runs. Modal dialogs are used ONLY when a user decision is the next required step; informational output ships as toast or banner.
2. **Dismissible.** Every surface has a visible dismiss affordance. Auto-dismiss is permitted for informational surfaces (toast). Modal and banner surfaces require explicit user action. Inline warnings persist until the underlying state changes.
3. **Saved to history.** Every fired notification writes to `reflection_view_log` (or the Phase 6 equivalent) and appears in `/insights` history. A user who dismissed a micro_mirror can find it later. Nothing Lyra says to the user is lost on dismissal.
4. **No guilt.** Notifications never scold ("You haven't logged in 3 days"), never threaten loss ("Your streak is at risk"), never nag ("Ready to plan your day?"). Notifications are informational or decisional. If the surface would read as guilt in the user's voice, it is rejected — see `docs/do_not_add.md` §Aggressive notification schemes.

Violating any of these four principles is grounds to reject a notification design. They are not subject to taste or exception.

---

## The Four Surface Types

Lyra has exactly four notification surface types. New notification categories must fit one of these — if they do not fit, the surface is wrong for the product.

### 1. Toast — transient informational

- **Used for:** `micro_mirror` (one-line behavioral observation surfaced on stop), session milestone notices ("session 10 in dev logged"), successful action confirmations where the change is not visually obvious.
- **Lifespan:** 8 seconds auto-dismiss. User can pin to stay visible.
- **Position:** Bottom-right of the viewport. Stacks vertically if multiple fire in quick succession (max 3 visible, older ones collapse into a "+2 more" indicator that opens `/insights` history).
- **Affordances:** Dismiss button (×), optional "see more" link that opens the full observation in `/insights`.
- **State:** Saved to `reflection_view_log` with `reflection_type = 'micro_mirror'`, `viewed_at`, `dismissed_at`, `dwell_seconds`.
- **Phase 6 routing:** See `docs/phase_6_architecture_backlog.md` §D6 — extend lifespan for Type 2 users, suppress after consecutive dismissals for Type 3.

### 2. Modal — decisional

- **Used for:** `calibration_nudge` at task creation (keep/adjust/dismiss), `calibration_nudge` at stop with adjustable completion percentage, early-stop confirmation gate (existing).
- **Lifespan:** Until user action. No auto-dismiss.
- **Position:** Center, with dimmed backdrop.
- **Affordances:** At least two choices (never just "OK"). Choice labels describe consequences, not system state ("Keep 40 min plan" not "Confirm"; "Adjust to 72 min" not "Accept"). Always has a visible dismiss / cancel button.
- **State:** Saved to `reflection_view_log` with the chosen outcome.
- **Constraint:** Modal surfaces are reserved for moments where the next step is the user's choice. Informational content must not be shipped as a modal — that is friction, not information.

### 3. Inline warning — state-transition correctness

- **Used for:** `is_future_task` warning on start-timer (LYR-097), state-transition rejection (e.g., "Cannot start while another task is paused"), schedule conflict detection during task creation.
- **Lifespan:** Persists until the underlying state condition changes. Cannot be dismissed without resolving the warning.
- **Position:** Inline within the affected form or action. NOT a banner at the top, NOT a toast at the corner — the warning appears where the action was attempted.
- **Affordances:** Describes the condition, names the blocking state, offers the resolution path ("Resume the paused task first" with a one-click button if the resolution is one action away).
- **State:** Not saved to history by default. These are correctness-critical surfaces, not research signals. If V3 engagement tracking is desired on a specific inline warning (e.g., how often users proceed past an is_future_task warning after reading it), add logging explicitly.
- **Constraint:** Inline warnings are NOT routed by the Phase 6 exposure layer. Correctness is unconditional.

### 4. Banner — persistent milestone or insight

- **Used for:** Insight-fired announcements ("Your dev tasks at this time of day run 1.8× planned — see /insights"), 30-session milestone unlocks ("Bias factor published for dev. View in /insights"), "Insights unlock in N more sessions" progress framing on `/today` empty state.
- **Lifespan:** Until user dismisses. Dismissal moves to `/insights` history.
- **Position:** Top of `/today`, below the active timer banner if one is running. Only one banner visible at a time; queued banners surface on dismiss.
- **Affordances:** Dismiss button. Optional "open in /insights" link. Never has a "don't show again" affordance — that is the V5 silence preference's job, not per-banner suppression.
- **State:** Saved to `reflection_view_log` with `reflection_type = 'banner'`, plus the specific insight/milestone ID.
- **Phase 6 routing:** Calibrators unlock philosophical-dialect insight banners earlier; Type 3 Illusion Preservers unlock the same tier later with softer framing (see D6 mapping table in backlog).

---

## Gradual Exposure Mapping (Summary)

The full Phase 6 mapping of notification timing to user confrontation-readiness state is in `docs/phase_6_architecture_backlog.md` §"Gradual Exposure → Notification Timing Mapping (D6)". Pre-alpha summary for shipping reference:

| Surface | Phase 4.5 (v1 uniform) | Phase 6 (routed) |
|---|---|---|
| Toast — `micro_mirror` | Fires every stop. 8s dismiss. Dwell logged. | Extend to 12s for Type 2; suppress-on-repeated-dismiss for Type 3. |
| Modal — `calibration_nudge` (creation) | Fires at bias_factor ≥ 1.25 with ≥10 sessions in category. | Escalate dialect for Calibrators post-30-sessions; suppress for Type 3. |
| Modal — `calibration_nudge` (stop) | Fires at signed_discrepancy threshold. | Type 2 receives "you've seen this N times" variant. |
| Inline warning — `is_future_task`, state errors | Always on. Never suppressed. | No routing. Correctness-critical. |
| Banner — insight / milestone | Fires once per insight, once per milestone. | Calibrators unlock earlier; Type 3 unlocks with softer framing. |

Phase 4.5 ships uniformly because per-user routing requires ≥30 sessions per category, which no alpha user will cross before mid-May. V1/V3/V5 signal logging begins at Phase 4.5 so the Phase 6 router has training data.

---

## Guidelines for Future Notifications

Before adding a new notification surface, the designer must answer:

1. **Which of the four surface types?** If the answer is "a new one," the design is wrong for this product. Rework until it fits.
2. **Does it violate any of the four principles?** If it is blocking, non-dismissible, lost-on-dismiss, or guilty, it is rejected. Not "revise until it passes" — if the concept requires violating a principle to work, the concept itself is off.
3. **What fires it?** A specific backend signal, a timer, a state transition, or a user action. No notification is permitted whose trigger is "once per day" or "to re-engage the user" — those are engagement patterns, not information patterns.
4. **What does it log?** Even inline warnings can log if V3 engagement tracking is wanted. The default is "log to `reflection_view_log` if the user will see it rendered more than once, don't log otherwise."
5. **Does the Phase 6 router need to touch it?** If the notification is correctness-critical, no — inline warnings are unconditional. If the notification is exposure-layer, yes — the backlog D6 mapping must include it before Phase 6 ships.

If any answer is unclear, the surface is not ready to be designed. Write the feedback/output loop audit question ("what does this *mean* to the user right now, and what change of behavior does it invite?") until the answer clarifies the trigger, lifespan, and dismissal model.

---

## References

- `docs/building_phases.md` §Phase 4.5 Tier 1 — shipping gate for retention architecture
- `docs/phase_6_architecture_backlog.md` §D6 "Gradual Exposure → Notification Timing Mapping" — full routed timing table
- `docs/phase_6_architecture_backlog.md` §D2 "Measurement-state progress is not gamification" — permitted vs rejected surfaces
- `docs/do_not_add.md` §Aggressive notification schemes — rejected patterns
- `docs/do_not_add.md` §Gamification — rejected reward loops + PERMITTED progress framing
- `MANIFESTO.md` §Shipping Philosophy — Retention Mechanism First — why notification surfaces are Tier 1
- `SKILL.md` §Notifications — agent-side polling contract

---

## Authority

Designed by operator (Ali Nasser) in conversation with Claude (Anthropic), April 14, 2026. Post-feedback/output-loop audit decisions D5 (Windows-style pattern) and D6 (gradual exposure mapping). Not optional. Any notification designed outside this pattern is rejected on design review.
