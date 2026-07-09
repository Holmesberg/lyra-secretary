---
authority: parked
may_authorize_code: false
runtime_owner: none
created: 2026-06-29
---

# Uncertainty Reduction Computation Council - 2026-06-29

Status: documentation-only synthesis. This document does not authorize runtime
feature work, AI synthesis, new user-facing insights, behavior-transition
equations, schema changes, or adaptive authority.

## Core Question

LyraOS should ask:

```text
What can we validly observe about accepted intention meeting execution under
constraints?
```

It should not ask:

```text
Why is this person like this?
```

The repo already contains useful instrumentation substrate: Cortex clean
profiles, Exposure Ledger v0, ClaimCompiler, output-surface registry,
stale/repair flags, `TaskExecutionCorrection`, `DeadlineCompletionEvent`,
`PauseEvent`, calibration nudge rows, and operator diagnostics. The missing
layer is not "more data." The missing layer is uncertainty-reducing computation
with clean denominators, exposure discipline, and bounded claim authority.

## Council Method

The synthesis was run as a multi-pass council:

1. Statistician / uncertainty-reduction pass.
2. Behavioral science and HCI pass.
3. Product-retention pass.
4. Sequential modeling / state-transition pass.
5. Measurement-integrity adversary pass.
6. Systems architecture / ClaimCompiler integration pass.
7. Cross-agent critique and final veto pass.

The output below is the consolidated council result, not an implementation
plan.

## Top Computation Families

| Rank | Computation family | Main uncertainty reduced | Current status |
|---:|---|---|---|
| 1 | Admission & Coverage Gate | Which rows are admissible at all. | Operator diagnostic / infrastructure candidate after freeze. |
| 2 | Execution Drift Decomposition | Whether drift came from late start, active overrun, pause overhead, or dirty repair. | Post-freeze candidate. |
| 3 | Re-entry Resolution Survival | Whether paused/stale work resumes, resolves, drops, reschedules, or auto-closes. | Post-freeze candidate. |
| 4 | Pressure-to-Execution Funnel | Whether pressure visibility leads to binding, preview, timer start, clean stop, and return. | Operator diagnostic only. |
| 5 | Exposure-Response Cost Curve | Whether Lyra's own prompts change behavior or create noise. | Operator diagnostic / research guardrail. |
| 6 | Planned-Block Collapse Topology | How planned work becomes started, missed, skipped, stale, retroactive, repaired, or recovered. | Descriptive only. |
| 7 | Native Deadline Delay Distribution | Native deadline timing behavior without provider contamination. | Post-freeze candidate. |
| 8 | Evidence Concordance Guard | Contradictions between plan, timer, provider fact, self-report, and repair. | Parked; surveillance risk. |
| 9 | Transition Kernel / Motifs | Reusable state-transition primitives from execution traces. | Parked research. |
| 10 | Constraint Pressure Geometry | Structural load and visible-time pressure. | Operator/pressure-map only until cockpit stability. |

## If Only Three Post-Freeze

If LyraOS can add only three computation families after cockpit stability, the
council recommends:

1. **Admission & Coverage Gate**  
   Before any claim, decide whether evidence is clean, dirty, repaired,
   provider-only, synthetic, voided, retroactive, exposed, unknown, or
   otherwise excluded.

2. **Execution Drift Decomposition**  
   Split planned-to-executed drift into late start, active overrun, pause
   overhead, clean log(E/P), and dirty/repaired exclusion.

3. **Re-entry Resolution Survival**  
   Treat paused, switched, stale, and interrupted work as recovery paths:
   resumed, resolved, dropped, rescheduled, stale, or auto-closed.

If Admission/Coverage is treated as cockpit infrastructure rather than a new
computation, the next candidate is **Pressure-to-Execution Funnel**, strictly
operator-only.

## Computations To Reject Or Park

Reject or park these until stronger evidence and explicit authority exist:

- productivity scores;
- focus scores;
- motivation, discipline, avoidance, agency, or competence classifiers;
- archetype identity drift;
- generic behavior-change score;
- causal pressure-return claims;
- cascade interventions;
- AI synthesis over raw traces;
- decorative Markov paths that do not alter falsifiability or product action;
- behavior-transition equations in runtime.

## Operator Cockpit Implications

Before any new user-facing insight exists, `/operator` should make these visible
as diagnostics:

- admission/coverage counts by reason;
- clean eligible explicit stopwatch session denominator;
- dirty reason distribution;
- exposure-without-render and render-without-exposure counts;
- pressure-to-execution funnel dropoff;
- re-entry/stale-resolution path counts;
- provider-only and imported rows split from native rows;
- "not instrumented" buckets instead of fake zeroes.

These diagnostics should not mutate last activity, notification state, exposure
state, user metrics, task/session/provider state, or provider sync state.

## ClaimCompiler Packet Implications

AI or deterministic synthesis may only reason over packets whose inputs are
already admitted. The required distinction is:

```text
Admission/Coverage Gate = decides whether rows are eligible.
EvidencePacket = packages eligible evidence for a bounded claim.
ClaimCompiler = decides whether the claim may emit.
```

Minimum future packet families:

- `admission_coverage_packet`;
- `execution_drift_decomposition_packet`;
- `reentry_resolution_survival_packet`;
- `pressure_execution_funnel_packet`;
- `exposure_response_packet`;
- `deadline_delay_distribution_packet`.

Every packet must declare:

- clean profile;
- denominator;
- exclusions;
- dirty reasons;
- exposure policy;
- time window;
- slice-invariance checks;
- uncertainty basis;
- allowed claim authority;
- forbidden interpretations;
- kill criteria.

## Task-Creation Duration Nudge Exposure

The task creation time-estimate suggestion is exposure. If Lyra shows `Use 85
min` and the user changes their planned duration to match, the system has shaped
the planning estimate.

Repo-grounded current path:

- `backend/app/core/output_surface_registry.json` registers
  `task.creation_nudge` as an in-app modal scheduling suggestion.
- `frontend/components/new-task-modal.tsx` acknowledges render with
  `ackExposureRender()` when the nudge is visibly mounted.
- The same modal sends `nudge_decision=accepted|dismissed` plus suggested
  duration, bias factor, sample size, and viewed timestamp in the task-create
  payload.
- `backend/app/services/task_manager.py` writes `CalibrationNudgeEvent` and a
  legacy reflection view outcome on task creation.

Interpretation:

```text
render exposure exists;
duration-decision outcome exists;
the original render -> interaction outcome link should remain first-class.
```

Future cleanup should model this as one exposure render plus a linked
interaction outcome (`accepted`, `dismissed`, `ignored`) rather than relying on
ambiguous duplicate render/legacy rows.

## Freeze Boundary

No runtime feature work is authorized by this council output.

No AI synthesis is authorized.

No new user-facing insights are authorized.

No behavior-transition equation is authorized for runtime.

This output may only inform documentation, operator diagnostics, and
post-freeze planning.
