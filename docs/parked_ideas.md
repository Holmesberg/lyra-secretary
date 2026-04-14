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
