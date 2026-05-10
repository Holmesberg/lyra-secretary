---
type: counterfactual
status: active
confidence: low
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - archive/appstore/summary_of_app.md
related:
  - "[[Pause Predictions Can Reduce Overrun Or Interrupt Flow]]"
  - "[[Feedback Surfaces]]"
  - "[[Tension - Helpfulness vs Contamination]]"
data_class: internal_architecture
---

# Counterfactual - Pause Prediction Removed

## Alternative World

LyraOS stops surfacing pause predictions.

## Expected Benefit

Less interruption and less predictive-alert contamination of pause behavior.

## Expected Harm

Loss of proactive recovery and reduced operator learning about pause topology.

## What Current Architecture Assumes

Pause predictions may be valuable if gated, throttled, and exposure-modeled.

## What Evidence Could Change The Assumption

Consistent evidence that pause predictions interrupt flow or produce low engagement.

## Related Tensions

- [[Tension - Helpfulness vs Contamination]]
- [[Tension - Frictionless UX vs Measurable Behavior]]
