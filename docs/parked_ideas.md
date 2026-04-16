# Lyra — Parked Ideas

*Ideas captured but not executed. Each has a revisit condition. Do not build
before conditions are met.*

*Format: short description, why parked, what triggers revisiting, date captured.*

---

## LLM-powered subscription tier
*Captured: April 14, 2026*

**Idea:** Base Lyra (web UI + mobile app) remains free or low-cost. Paid tier
adds OpenClaw via Telegram (natural language commands, conversational
interactions) + other LLM-powered features. Monthly subscription covers
Anthropic API consumption + margin.

**Rationale:** The operator's April 14 OpenClaw credit exhaustion revealed
that the conversational interface has real per-user cost. Pricing that tier
separately aligns cost with value. Users who want conversational power pay
for it; base users don't subsidize them.

**Reference models:** Notion AI, Linear AI, Cursor Pro — standard pricing
pattern for LLM-enhanced consumer products in 2025+.

**Revisit conditions (all must be met):**
- Retention validated post-May 21 with base product
- Base product has earned paying users or proven willingness-to-pay
  independent of AI tier
- Trusted-user feedback confirms OpenClaw is valued enough to justify paid
  access
- Operator has capacity to ship billing infrastructure without disrupting
  research timeline

**Do not:**
- Build pricing infrastructure before validating base value proposition
- Architect tier separation (feature gates, entitlements, subscription
  state) before retention data confirms which features users actually value
- Let monetization framing drift research design — all Phase 4.5 and
  Phase 5 decisions remain research-driven, not monetization-driven

**If idea still looks good in June+:** open a Phase 7 architecture spike.
Begin with competitive analysis of Notion/Linear/Cursor pricing models, then
decide Lyra-specific pricing model.

---

## Strategic decision log pointer
*Captured: April 14, 2026*

See `docs/strategic_decisions_april_14.md` for the four locked decisions from
the evening session: behavioral correction primary framing, gamification
refinement via progressive revelation, conflict detection forced override,
cold-start as legitimate experiment. These are referenced across
`MANIFESTO.md`, `docs/building_phases.md`, `docs/do_not_add.md`, and
`docs/design_patterns/notification_patterns.md`.

---

## Moat architecture discussion
*Captured: April 14, 2026*

**Parked until post-April 29** (after Spring School).

**Prerequisite:** operator has clarity on which scenario (research-impact,
commercial scale, learning vehicle) Lyra primarily serves. Moat thinking
without that clarity risks corrupting the behavioral-correction thesis by
drifting toward platform-product defensiveness.

**Revisit conditions:**
- Spring School completed (April 29)
- Retention data from trusted-user cold-start analyzed (see
  `docs/dogfood_findings_living.md §Cold-start engagement decay analysis`)
- Operator has explicitly chosen which primary scenario to optimize for

**Do not:**
- Begin moat-shaped architecture work (platform lock-in, data moat
  accumulation, switching-cost design) before the primary scenario is named
- Let moat framing enter Phase 4.5 / Phase 5 / Phase 5.5 design decisions —
  those remain research-driven

---

## Multi-task logging with cognitive bandwidth allocation
*Captured: April 15, 2026 (recurrent idea, third+ mention)*

**Pain:** Knowledge workers operate in concurrent modes. Operator examples:
vibecoding while studying, conversation while attending lecture, coding
while in async meeting. Current sequential-task execution model
misrepresents these patterns. Sessions get logged as one task or another,
never the actual blended attention state.

**Proposed mechanism:** Concurrent task groups where multiple tasks can be
EXECUTING simultaneously, each with declared cognitive bandwidth
allocation (e.g., 70% lecture, 30% conversation). delta computed against
bandwidth-weighted planned duration.

**Key open questions:**
- State machine: how do EXECUTING states stack? How does pause work for
  one task in a group?
- Measurement semantics: is "actual" duration wall-clock or bandwidth-
  weighted?
- Self-report validity: bandwidth allocation as Likert-style rating has
  same scale-saturation risk as readiness (VT-12 class).
- Interaction effects: does measuring multi-task state make users do more
  multi-tasking (instrument-intervention class, VT-17/VT-21 adjacent)?
- New validity threats around concurrent execution measurement.
- UI complexity: how do you show 2-3 active timers without cognitive
  overhead?
- Aggregation: how do bias_factor and other per-task metrics combine
  across concurrent groups?

**Revisit conditions:**
- Post-alpha (post-May 21)
- Post-H1-validation (because if signed_discrepancy doesn't predict delta
  in single-task mode, it certainly won't in multi-task mode)
- When Phase 6 calibration architecture is in active build
- After observing alpha users for evidence of whether multi-task patterns
  are common enough to warrant the model expansion

**Do not:**
- Build mid-experiment (would invalidate single-task baseline data)
- Build before validating it's a common pattern, not just
  operator-specific
- Build before designing the validity threat framework for concurrent
  measurement

**Related:**
- Offline mode (different problem, also recurrent)
- VT-12, VT-17, VT-21 (similar measurement-intervention concerns)
- Phase 6 calibration architecture

---

## Deadline-proximity risk assessment (H2 candidate)
*Captured: April 16, 2026 (from ChatGPT conversation)*

**Hypothesis:** Users systematically underestimate task duration as deadline
approaches, producing increasing `duration_delta_minutes` near deadlines.
Mechanism: temporal discounting × planning-fallacy interaction — imminent
deadlines compress the mental representation of required work.

**Status:** H2 candidate. Not in H1's kill-criterion chain and does not bear
on the Apr 15 H1 decision. Documented here so it isn't lost; do not build.

**Prerequisites (all required before any work begins):**
- H1 validated or falsified first (see `MANIFESTO.md §Kill Criterion — H1`)
- `deadline_utc` field added to task schema (currently absent — Lyra has no
  deadline concept; tasks are scheduled, not deadlined)
- Calendar integration (Google/Outlook) providing deadline data at task
  creation time, or an in-app deadline-setting UX
- Minimum 30 days of multi-user data with deadline-tagged tasks so
  within-user deadline-proximity × delta correlation can be estimated
  with enough paired observations per category

**Phase:** 6+ (post-calibration-architecture). Deadline data is a new
measurement axis, not a refinement of the existing discrepancy model.

**Do not:**
- Build mid-experiment (would add a new input variable to the H1 dataset
  and invalidate the pre-registered analysis rules in MANIFESTO §801)
- Ship deadline UI before H1 decision (would contaminate the single-
  hypothesis window by introducing a competing behavioral signal users
  will orient to)
- Treat deadline_utc as equivalent to planned_start_utc / planned_end_utc
  — they represent distinct constructs (scheduling vs. hard obligation)

**Revisit conditions:**
- H1 decision complete (validated, falsified, or explicit pivot)
- Phase 6 calibration architecture is in active build
- Operator has made an explicit scope call that H2 is the next hypothesis
  to test (competing candidates exist — cascade hypothesis per MANIFESTO
  §Paper 2, interruption-recovery cost, others)

**Related:**
- MANIFESTO §Kill Criterion (H1 pre-registration; H2 is downstream of H1)
- MANIFESTO §Paper 2 cascade hypothesis (alternative post-H1 direction)
- VT-7 (anchor-scheduling evidence base) — adjacent concern about the
  calendar field's behavioral meaning
