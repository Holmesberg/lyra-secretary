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

## Product Seam Boundary

This V0 document records harness bring-up. The active post-V0 bridge from
stubbed scenarios to real product behavior lives in
`docs/lyrasim_pressure_ambiguity_roadmap.md` under Product Seam Connection
Plan.

Rules:

- `stubbed=true` remains harness validation only.
- `product_seam_validated=true` requires generated scenario data to enter at
  least one real product service or endpoint.
- The report must name the exercised seam.
- Hidden state must never enter product-facing inputs.
- Product seam validation must stay deterministic, replayable, redacted, and
  user-scoped.

The recommended first seam is a Baseet-like duplicate/stale deadline pressure
scenario against the real academic pressure-map path, while keeping the stubbed
scenario as a control.

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
- Competing hypotheses eventually collapse only to the unique highest-scoring
  hypothesis.
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

```text
self_report_prompt_availability_rate =
count(simulated self-report opportunities with a low-authority hypothesis-check prompt)
/
count(total simulated self-report opportunities)
```

```text
safe_action_spam_rate =
count(low-severity ambiguous cases where Lyra offers a recovery or confirmation action)
/
count(total low-severity ambiguous cases)
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
simulated_self_report_summary
observable_trace_sequence
lyra_output
metrics
findings_summary
failed_invariants
coverage_limitations
generator_assumptions
minimal_replay_command
```

Reports must also include scenario coverage limitations and generator
assumptions so synthetic pass rates do not become false certainty.

`findings_summary` includes:

```text
overall_status
finding_count
failed_invariants
stubbed
product_seam_validated
summary_lines
resolution_rung
safe_action_type
```

Resolution rungs:

```text
suppress | clarify | repair | recommend | adapt
```

Safe action types:

```text
confirm_done_partial_discard
confirm_coverage
adjust_session_duration
mark_open_unconfirmed
ask_pause_continue_split
none
```

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
- Added `self_report_prompt_availability_rate` so the harness can verify that
  ambiguity can be clarified by a low-authority question instead of collapsing
  into either surveillance claims or silence.
- Added the video-derived `baseet_resource_open_idle_45m` scenario:
  Baseet-like academic resource opened, 45 minutes of idle passive activity,
  simulator hidden truth `away_from_keyboard`.
- The scenario permits low-authority pause/continue/split actions only. It
  fails if the output claims study, completion, learning, focus,
  understanding, cognition, identity, or clean calibration from the passive
  provider trace.
- The scenario now includes a simulator-only self-report response that confirms
  the low-authority pause/inactive-resource hypothesis. The confirmation may
  calibrate future hypothesis confidence, but it is still `self_reported`
  evidence and must not become clean execution truth.
- Added findings summaries to JSON reports and CLI output so every simulation
  run reports pass/fail status, failed metrics/invariants, resolution rung,
  safe action type, and replay command.
- Added the `safe_action_spam_rate` diagnostic so LyraSim catches the opposite
  failure from paralysis: recovery prompts for every tiny ambiguity.
- This increment still does not validate live Baseet behavior, passive
  telemetry product capture, pressure-map correctness, AI synthesis, recovery
  safety, or emotional safety.

## Abandoned Provider-Progress Increment

Provider progress is explicitly represented as:

```text
provider_progress_candidate
```

not:

```text
execution_progress
```

Implemented harness-only scenarios:

- `baseet_stale_task_progress_candidate`
- `baseet_background_video_fakeout`
- `baseet_multidevice_upload_collision`
- `baseet_reverse_progress_signal`

These scenarios require `clarify` or `repair` resolution. They fail if provider
progress creates automatic task mutation, clean calibration, execution truth,
completion truth, learning/focus/understanding claims, or safe-action
paralysis.

## Hypothesis Collapse

LyraSim may model competing explanations for ambiguous traces, but those
explanations must not become endless contradiction absorption.

The simulator-only collapse condition is:

```text
unique highest score -> collapsed operational hypothesis
tie or insufficient scenario threshold -> unresolved
```

Collapse resolves the simulator's operational explanation, not human truth. It
does not authorize identity claims, clean calibration, mutation, adaptation, or
public certainty.
