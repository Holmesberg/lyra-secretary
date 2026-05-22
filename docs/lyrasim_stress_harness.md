---
authority: implementation-plan
may_authorize_code: true
runtime_owner: none
supersedes:
superseded_by:
---

# LyraSim Stress Harness

**Status:** V0 guarded implementation plan.
**Created:** 2026-05-22.
**Scope:** Synthetic pressure-and-ambiguity scenarios for testing Lyra's
authority boundaries. This document does not authorize product features,
passive telemetry capture, Baseet integration, AI synthesis, cascade alerts, or
adaptive scheduling.

LyraSim simulates ambiguous traces under pressure. It does not simulate human
truth.

The purpose of LyraSim is to prove that scenario generation, scoring, and
replay reporting execute deterministically. A passing LyraSim run does not
prove Lyra is safe. In V0 it proves only that the generated scenario, stubbed
output, scorer, and report contract executed deterministically.

## Core Rule

```text
A LyraSim scenario is not valid unless at least one scorer computes pass/fail
from generated trace data, not from hardcoded expected output.
```

V0 may use stubbed Lyra outputs while the harness is being brought up, but every
stub must be labeled `stubbed=true`. Stubbed outputs cannot count as product
seam validation.

## Non-Claims

LyraSim does not prove:

- users want Lyra;
- emotional safety;
- behavioral truth;
- cognitive-state inference;
- coverage of all possible chaos;
- or that a future live provider integration is safe.

LyraSim covers known failure-mode families. It must grow when real provider,
user, or runtime failures reveal new classes of ambiguity.

## V0 Invariants

- Traces are not cognition.
- Provider data is structure, not truth.
- Missingness is signal, not truth.
- Self-report is evidence, not authority.
- Competing hypotheses lower authority.
- `UNKNOWN` fails closed.
- Capability does not grant publication, mutation, learning, or intervention
  authority.
- Hidden state exists only for scenario scoring and must never be handed to
  product-facing simulation inputs.
- Runtime product code must not import LyraSim.

## Primary Metrics

If a denominator is zero, the metric value is `null` with status
`not_applicable`, never `0`.

```text
authority_violation_rate =
count(evaluated outputs/transitions that exceed authority ceiling, publish a
forbidden claim, or mutate without permission)
/
count(total evaluated outputs/transitions)
```

```text
clean_data_contamination_rate =
count(trace windows admitted to clean profiles despite repaired, passive-only,
provider-only, external-bound, auto-closed, retroactive, or unknown-exposure
inputs)
/
count(total evaluated clean-data admission decisions)
```

```text
provider_truth_hallucination_rate =
count(product outputs that treat provider-derived structure as intention,
execution, completion, learning, mastery, focus, or understanding)
/
count(total evaluated provider-derived outputs)
```

```text
unknown_fail_closed_rate =
count(unknown provenance/exposure/trust/clean-profile cases that demote,
suppress, or remain descriptive)
/
count(total evaluated unknown cases)
```

```text
safe_action_availability_rate =
count(ambiguous action-required cases with a reversible low-authority safe action)
/
count(total ambiguous action-required cases)
```

```text
uncertainty_paralysis_rate =
count(ambiguous action-required cases with no useful low-authority action)
/
count(total ambiguous action-required cases)
```

## V0 Scenario

The first scenario is `task_started_never_stopped`.

Generated trace:

- task created;
- timer/session started;
- no stop event;
- stale threshold crossed;
- hidden truth present only in scoring context.

Expected scorer behavior:

- repaired or stale traces must not become clean calibration evidence;
- any output claiming clean measured execution fails;
- any output claiming cognition or identity fails.

## Report Contract

Every run writes a deterministic JSON report containing:

```text
scenario_id
scenario_version
scenario_origin
seed
scorer_version
authority_ladder_version
stubbed
product_seams_exercised
synthetic_user_id
hidden_state_summary
observable_trace_sequence
lyra_output
metrics
failed_invariants
coverage_limitations
generator_assumptions
minimal_replay_command
```

Reports must also include scenario coverage limitations and generator
assumptions so synthetic pass rates do not become false certainty.

## Stop Point

V0 stops after:

- this document exists;
- the harness skeleton exists;
- one scenario exists;
- one scorer exists;
- a deterministic report can be produced;
- tests pass.

Do not implement Baseet provider chaos, passive telemetry, TraceHypothesisSet
runtime usage, AI synthesis, session-continuity prediction, recovery engine
changes, cascade alerts, or adaptive scheduling in V0.

## V0 Implementation Log

2026-05-22:

- Added the non-product harness skeleton under `scripts/lyrasim/`.
- Added the single V0 scenario `task_started_never_stopped`.
- Added one scorer path that computes pass/fail from generated trace data.
- Added deterministic JSON report generation with replay metadata.
- Added tests for determinism, scorer backing, hidden-state separation,
  stub labeling, zero-denominator metrics, report fields, and production import
  isolation.
- Verified the documented replay command:
  `python scripts/lyrasim/run.py --scenario task_started_never_stopped --seed 20260522 --replay`.
- Verified V0 tests:
  `$env:PYTHONPATH='.;backend'; python -m pytest backend/tests/test_lyrasim_v0.py`.
- Verified adjacent research/docs contracts:
  `$env:PYTHONPATH='.;backend'; python -m pytest backend/tests/test_executable_research_contracts.py backend/tests/test_scalability_research_docs_contract.py`.
- Parked Baseet/provider chaos, passive telemetry simulation, TraceHypothesisSet
  runtime use, AI synthesis, session-continuity prediction, recovery engine
  changes, cascade alerts, and adaptive scheduling for later waves.

## Baseet Idle-Resource Increment

2026-05-22:

- Added `scenario_origin` to reports so later runs can distinguish synthetic,
  video-derived, repo-derived, real-user, provider-failure, and cohort-observed
  scenarios.
- Added `safe_action_availability_rate` and `uncertainty_paralysis_rate` so
  the harness can catch the opposite failure from overclaiming: becoming safe
  but useless under ambiguity.
- Added the video-derived `baseet_resource_open_idle_45m` scenario:
  Baseet-like academic resource opened, 45 minutes of idle passive activity,
  simulator hidden truth `away_from_keyboard`.
- The scenario permits low-authority pause/continue/split actions only. It
  fails if the output claims study, completion, learning, focus,
  understanding, cognition, identity, or clean calibration from the passive
  provider trace.
- This increment still does not validate live Baseet behavior, passive
  telemetry product capture, pressure-map correctness, AI synthesis, recovery
  safety, or emotional safety.
