# Notification Patterns

**Owner:** Operator
**Created:** April 14, 2026 (feedback/output loop architecture lock)
**Status:** Canonical. Any new Lyra notification surface must conform.

This document is referenced by `docs/archive/legacy/planning/building_phases.md §Phase 4.5 Tier 1`, `docs/archive/legacy/planning/phase_6_architecture_backlog.md §Gradual Exposure → Notification Timing Mapping (D6)`, and the Phase 4.5 PR reviews. If you are about to add a new notification, banner, toast, or modal — read this first.

---

## Principles (Windows-style, not mobile-app-style)

Lyra's notification philosophy mirrors desktop OS conventions, not mobile-app engagement patterns. The product is a measurement instrument with custodian trust properties (see `docs/archive/legacy/planning/phase_6_architecture_backlog.md` §Custodianship trust frame), not an engagement-driven app. Four principles, load-bearing:

1. **Non-blocking.** Notifications do not interrupt the user's primary action. Timer still runs. Modal dialogs are used ONLY when a user decision is the next required step; informational output ships as toast or banner.
2. **Dismissible.** Every surface has a visible dismiss affordance. Auto-dismiss is permitted for informational surfaces (toast). Modal and banner surfaces require explicit user action. Inline warnings persist until the underlying state changes.
3. **Saved to history.** Every fired notification writes to `reflection_view_log` (or the Phase 6 equivalent) and appears in `/insights` history. A user who dismissed a micro_mirror can find it later. Nothing Lyra says to the user is lost on dismissal.
4. **No guilt.** Notifications never scold ("You haven't logged in 3 days"), never threaten loss ("Your streak is at risk"), never nag ("Ready to plan your day?"). Notifications are informational or decisional. If the surface would read as guilt in the user's voice, it is rejected — see `docs/do_not_add.md` §Aggressive notification schemes.

Violating any of these four principles is grounds to reject a notification design. They are not subject to taste or exception.

---

## The Four Surface Types

Lyra has exactly four notification surface types. New notification categories must fit one of these — if they do not fit, the surface is wrong for the product.

### 1. Toast — transient informational

- **Used for:** `micro_mirror` (one-line behavioral observation surfaced on stop), `calibration_nudge` at stop (reference-class summary — post-hoc informational, not decisional), session milestone notices ("session 10 in dev logged"), successful action confirmations where the change is not visually obvious.
- **Lifespan:** 8 seconds auto-dismiss by default. User can pin to stay visible. Exception: `calibration_nudge` at stop renders as pinned-by-default (until-dismiss) since the reference-class summary is multi-sentence and a brief auto-dismiss would not give the user time to read it.
- **Position:** Bottom-right of the viewport. Stacks vertically if multiple fire in quick succession (max 3 visible, older ones collapse into a "+2 more" indicator that opens `/insights` history).
- **Affordances:** Dismiss button (×), optional "see more" link that opens the full observation in `/insights`.
- **State:** Saved to `reflection_view_log` with `reflection_type = 'micro_mirror'`, `viewed_at`, `dismissed_at`, `dwell_seconds`.
- **Phase 6 routing:** See `docs/archive/legacy/planning/phase_6_architecture_backlog.md` §D6 — extend lifespan for Type 2 users, suppress after consecutive dismissals for Type 3.

### 2. Modal — decisional

- **Used for:** `calibration_nudge` at task creation (keep/adjust/dismiss — decisional, surfaces the predicted overrun before commit), early-stop confirmation gate (existing). Stop-time `calibration_nudge` was previously listed here; moved to §Toast (2026-04-15) because its content is post-hoc informational, not decisional — surfacing it as a modal would violate the "reserved for user-choice moments" rule.
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

The full Phase 6 mapping of notification timing to user confrontation-readiness state is in `docs/archive/legacy/planning/phase_6_architecture_backlog.md` §"Gradual Exposure → Notification Timing Mapping (D6)". Pre-alpha summary for shipping reference:

| Surface | Phase 4.5 (v1 uniform) | Phase 6 (routed) |
|---|---|---|
| Toast — `micro_mirror` | Fires every stop. 8s dismiss. Dwell logged. | Extend to 12s for Type 2; suppress-on-repeated-dismiss for Type 3. |
| Modal — `calibration_nudge` (creation) | Fires at bias_factor ≥ 1.25 with ≥10 sessions in category. | Escalate dialect for Calibrators post-30-sessions; suppress for Type 3. |
| Toast — `calibration_nudge` (stop) | Fires at n ≥ 3 same-category EXECUTED history (Phase 4.5 pre-registered threshold, see `backend/app/services/stopwatch_manager.py::_compute_calibration_nudge`). Until-dismiss (pinned by default). Dwell logged to `reflection_view_log`. | Type 2 receives "you've seen this N times" variant. |
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

## Predictive Notifications — Measurement Instrument Implications

Predictive notifications are a special case that appeared after the four canonical surface types were defined. They are notifications fired *before* a predicted behavior, inviting the user to take an action the instrument believes they are about to take anyway. The Phase 4.5 Tier 1.5 pause-prediction feature is the first example.

Predictive notifications must conform to all four principles (non-blocking, dismissible, saved-to-history, no guilt) — but they also introduce a measurement risk that the canonical four surfaces do not: the instrument's own output can change the behavior it is measuring (VT-17 in `MANIFESTO.md`).

Rules for predictive notifications:

1. **Surface type.** Use toast if the notification is informational ("you usually pause now"). Use modal-equivalent (Telegram message with explicit action-choice text) if the notification is decisional. Never use banner or inline-warning for predictions — banners are for insights (past-tense), inline warnings are for correctness-critical state errors.
2. **Research-relevant fields MUST NOT be defaulted by the notification's action path.** If the user taps "accept," the resulting state change must still route through whatever flow normally captures research-relevant fields. For pause prediction: accepting the prediction must still result in the canonical pause flow asking `pause_initiator` and `pause_reason` — the notification does NOT supply defaults for those fields. See `docs/do_not_add.md §Predictive notifications must not default research-relevant fields`.
3. **Pre-register a Validity Threat.** Every predictive notification is a VT candidate by construction (it intervenes in the measurement). The VT entry must define distinguishing analyses that answer "did the notification change the behavior?" — not just "did users accept the notification?"
4. **Pre-register the kill criterion at launch.** Acceptance-rate formula, threshold, window start, per-user vs aggregate — written down before any data lands. Changing the formula after data lands is indistinguishable from p-hacking.
5. **Self-activation gate.** Predictions must not fire until the user has a minimum history depth (for pause prediction: ≥ 7 days of `pause_event` rows). Firing predictions on under-powered history produces noise that the user perceives as annoyance, tripping the kill threshold on a non-representative window.
6. **Rate-limit across mechanisms.** One notification per user per 30 minutes across all prediction mechanisms. Two predictors firing in the same minute is a worse user experience than one predictor firing confidently.
7. **Suppress during the predicted state.** Don't fire a "you usually pause now" while the user is already paused. Don't fire a "task will finish soon" while the task is already stopped.
8. **Post-hoc acceptance inference is acceptable.** Explicit user callback buttons are not required if the raw event (the pause) can be detected in a defined window. This trades infrastructure for inference noise; the Phase 4.5 Tier 1.5 design chose inference to preserve pause_reason data capture via the existing agent flow.

Predictive notifications live in the same `reflection_view_log` (or equivalent) as other surfaces, PLUS a dedicated `pause_prediction_log` that captures what the instrument predicted and what it observed. The prediction log is a research artifact; the notification render is a user interaction.

---

## Progressive Revelation Pattern

Progressive revelation is the notification pattern for **measurement-state milestones**. Unlike event notifications (pause prediction, timer overflow) which fire on external triggers, progressive revelation fires when the instrument has accumulated enough data to produce a trustworthy claim *about the user*. The reward is information transfer, not behavior reinforcement — which is why it is permitted under `docs/do_not_add.md §Gamification` where streaks/badges/XP are rejected.

Characteristics:

- **Threshold-triggered** — session count, confidence score, or similar data-depth metric crosses a pre-defined threshold.
- **One-time or rare** — fires once per milestone, not recurringly. Re-fires only when a meaningfully new claim becomes available (e.g. reclassification at session 15–20 if behavior diverges from the session-5–7 archetype).
- **Information transfer as reward** — the user learns something about themselves ("your archetype is X with medium confidence") rather than earning something for behavior.
- **Optional dismissal without data loss** — user can acknowledge, dismiss, or engage. Never required to act. Dismissed reveals are saved to `reflection_view_log` and remain retrievable in `/insights` history.

Examples in the current / planned system:

- "Insights unlock in N more sessions" progress framing at cold-start (Tier 1, `/today` empty state).
- Archetype reveal at session 5–7 (Phase 5 pre-alpha — see `docs/archive/legacy/planning/building_phases.md §Pre-alpha ship list`).
- Reclassification prompt at session 15–20 if behavior diverges from the initial archetype (Phase 5 pre-alpha).
- Confidence-tier transitions on `bias_factor` ("low confidence: 8/30 sessions" → "medium: 18/30" → "published: 30+").
- Pattern-specific reveals (cascade-risk detection, optimal time-of-day detected) — Phase 6 candidates.

Guidelines for designing a progressive-revelation surface:

- **Honest framing about data depth.** "Medium confidence" or "based on N sessions" — never "you are an X-type." The reveal describes the measurement state, not a fixed user identity.
- **Three affordances, never required action.** Acknowledge / dismiss / engage (e.g. open `/insights` for the underlying data). No modal lock-in.
- **Show progression toward next milestone.** "Next pattern unlocks at session X" — extends the progressive-revelation chain and prevents dead-end framing.
- **Surface-type fit.** Banner is the default surface for milestone reveals (persistent, dismissible, saved-to-history — see §Banner above). Toast is acceptable for minor confidence-tier upticks. Modal is reserved for reveals that require a next-action choice (e.g. reclassification needs explicit accept/reject), never for informational ones.

This pattern is compatible with the four-principle contract (non-blocking, dismissible, saved-to-history, no guilt) and with the measurement-instrument constraint that no research-relevant field gets defaulted by the notification's action path. Because the reveal *describes* what the instrument already measured rather than *causing* a new measurement, the VT pre-registration requirements that apply to predictive notifications do not apply here — the reveal is downstream of measurement, not upstream.

---

## References

- `docs/archive/legacy/planning/building_phases.md` §Phase 4.5 Tier 1 — shipping gate for retention architecture
- `docs/archive/legacy/planning/phase_6_architecture_backlog.md` §D6 "Gradual Exposure → Notification Timing Mapping" — full routed timing table
- `docs/archive/legacy/planning/phase_6_architecture_backlog.md` §D2 "Measurement-state progress is not gamification" — permitted vs rejected surfaces
- `docs/do_not_add.md` §Aggressive notification schemes — rejected patterns
- `docs/do_not_add.md` §Gamification — rejected reward loops + PERMITTED progress framing
- `MANIFESTO.md` §Shipping Philosophy — Retention Mechanism First — why notification surfaces are Tier 1
- `SKILL.md` §Notifications — agent-side polling contract

---

## Authority

Designed by operator (Ali Nasser) in conversation with assistant runtime (hosted model provider), April 14, 2026. Post-feedback/output-loop audit decisions D5 (Windows-style pattern) and D6 (gradual exposure mapping). Not optional. Any notification designed outside this pattern is rejected on design review.
