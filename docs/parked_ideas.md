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
