---
authority: parked
may_authorize_code: false
runtime_owner: none
promotion_condition: >
  Estimate suggestions become useful enough to shape planning, but current
  provenance is insufficient to preserve calibration validity.
---

# Estimate Provenance And Cold-Start Plan

Status: parked future implementation.

## Problem

Lyra needs better cold-start estimates, but estimate suggestions can destroy
calibration if user estimates, research priors, AI guesses, and accepted
system suggestions collapse into one field.

Core rule:

```text
planning assistance must not become fake user calibration evidence
```

## Estimate Sources To Separate

- `user_entered_estimate`
- `accepted_system_estimate`
- `edited_system_estimate`
- `research_prior_estimate`
- `archetype_cluster_prior`
- `personal_history_estimate`
- `deadline_linked_history_estimate`
- `AI_cold_start_estimate`
- `provider_block_length_estimate`

## Minimum Future Fields

Only add schema if read-time reconstruction is insufficient:

- `duration_estimate_source`
- `duration_estimate_confidence`
- `duration_estimate_range_low`
- `duration_estimate_range_high`
- `duration_estimate_accepted_from_system`
- `duration_estimate_user_modified`
- `duration_estimate_model_version`
- `duration_estimate_reference_class`

## Heuristic Inputs

Use in descending authority:

1. Same user's clean sessions linked to the same deadline/obligation.
2. Same user's clean sessions with similar title/category/source.
3. Same user's planned-vs-executed active duration history.
4. Same user's occupancy/re-entry history after anomaly filtering.
5. Archetype/cluster priors.
6. Research priors.
7. AI cold-start range.

Anomalies:

- exclude stale/dirty/auto-repaired/voided sessions;
- exclude forgotten timers and >8-10h pause anomalies from pause-overhead
  averages unless explicitly confirmed as real;
- treat overnight spans separately.

## Product Copy

Allowed:

```text
Initial range from prior similar sessions.
Execution estimate: 70-95m.
Planning window: about 2h with typical pause overhead.
```

Forbidden:

```text
You will take 94 minutes.
Lyra knows this task takes you 2h.
```

## Tests If Promoted

- accepted AI estimates do not enter clean user-estimate calibration as if the
  user independently planned them;
- same-deadline history beats generic category priors;
- occupancy excludes anomaly pauses;
- task window uses end-time + duration coherently;
- estimate source renders visibly in create/edit surfaces.
