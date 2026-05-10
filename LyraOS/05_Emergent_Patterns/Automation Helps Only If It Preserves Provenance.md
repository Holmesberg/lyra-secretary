---
type: pattern
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/cortex_product_research_contract_v0.md
  - docs/openclaw_orchestration_contract_v0.md
related:
  - "[[Tension - Automation vs Provenance]]"
  - "[[Integrations]]"
  - "[[OpenClaw Runtime]]"
data_class: internal_architecture
---

# Automation Helps Only If It Preserves Provenance

## Pattern

Automation reduces burden and increases coverage only when it keeps origin, confidence, and uncertainty visible.

## Evidence

- Import sources and repair provenance are distinct.
- OpenClaw outputs require provenance labels.

## Counter-Evidence

Some automation can be deterministic and low-risk, but it still needs source labeling.

## Related Tensions

- [[Tension - Automation vs Provenance]]

## Related Domains

- [[Integrations]]
- [[OpenClaw Runtime]]
- [[Vault Continuous Update System]]

## Interpretation

The system should automate candidate capture, not silently promote truth.

## Risk

AI or imported state gets treated as user-observed behavior.

## Next Watch Signal

Generated notes or rows without source refs.
