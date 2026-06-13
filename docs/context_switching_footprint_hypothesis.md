# Context-Switching Footprint Hypothesis

**Status:** Product-research hypothesis, low authority.
**Created:** 2026-06-03.
**Authority:** Documentation and future read-only derived metrics only. This
does not authorize passive browser tracking, automatic rescheduling,
autonomous task mutation, new notifications, or causal product claims.

## Core Framing

Lyra already records the machinery needed to observe context switching as an
execution topology:

```text
intention -> execution -> drift -> interruption -> consequence -> recalibration
```

The current hypothesis is observational:

```text
Explicit task switches and interruption chains may correlate with later
recovery friction, planning-window overhead, and execution drift.
```

The current hypothesis is not causal:

```text
High switching does not yet prove why fragmentation happened.
```

Hard tasks, unclear tasks, emotional avoidance, genuine emergencies, deadline
overload, excessive commitments, provider noise, and forgotten timers can all
produce similar switch signatures. The first duty of this hypothesis is to
preserve that ambiguity.

## Product Rule

This hypothesis should primarily strengthen re-entry, not insight.

Near-term product value:

```text
open threads -> recovery options
```

Not:

```text
switches -> fragmentation score
```

The safest first surface is a neutral recovery card:

```text
Parked after a task switch.
Paused for 42m.
Pick it back up, reschedule, or drop?
```

Avoid exposing `context_switching_footprint` as user-facing terminology. It is
acceptable as an internal metric family, but externally it can sound
surveillance-adjacent. Prefer:

- parked work
- re-entry load
- planning footprint
- open threads
- resume load

Preferred near-term copy:

```text
You have 3 open threads from earlier today.
```

Do not say:

```text
high switching causes recovery friction
```

Say:

```text
high switching correlates with recovery friction
```

until clean evidence, controls, and exposure accounting support stronger
claims.

## Terms

| Term | Meaning | User-facing wording |
| --- | --- | --- |
| `task_switch` | Explicit active-timer handoff between open sessions. | "Switch active timer" / "switching to another task." |
| `interruption_chain` | Parent-child execution topology created when work is parked while another task starts. | "Paused work" / "parked work." |
| `parked_work` | A paused task with an open session waiting for resume, switch, drop, or repair. | "Pick it back up?" |
| `open_thread` | Parked or interrupted work that still has an unresolved next action. | "Open thread." |
| `reentry_latency` | Time from pause/switch/miss to the next confirmed continuation or resolution. | "parked for 42m." |
| `reentry_resolution_type` | What happened after parked/interrupted work: resumed, completed, rescheduled, dropped, marked irrelevant, stale/open at day end, or auto-closed. | "Resolved by rescheduling" / "still open." |
| `recovery_friction` | Derived planning/recovery burden after work is interrupted or delayed. | "re-entry load" / "recovery friction." |
| `context_switching_footprint` | Derived footprint of switches, parked work, pause overhead, and downstream drift. | "planning footprint" / "re-entry load." |
| `metacognitive_discrepancy_modifier` | Estimate-vs-execution mismatch around the switched or parked work. | "this kind of work has run over plan before." |

Avoid "failure," "degradation," "focus loss," "motivation," "avoidance,"
"discipline," and identity labels in user-facing copy.

## Observable Inputs

Use only explicit, user-scoped, provenance-aware state:

- `Task.parent_task_id`
- `Task.interruption_type`
- `Task.planned_duration_minutes`
- `Task.executed_duration_minutes`
- `Task.task_completion_percentage`
- `Task.initiation_delay_minutes`
- `Task.state`
- `Task.voided_at`
- `StopwatchSession.total_paused_minutes`
- `StopwatchSession.auto_closed`
- `StopwatchSession.data_quality_flag`
- `PauseEvent.pause_reason`
- `PauseEvent.pause_initiator`
- `PauseEvent.duration_minutes`
- `PauseEvent.self_reported_retroactively`
- missed/skipped planned blocks
- deadline or obligation links
- output-surface and exposure state

Do not use passive browser activity, raw provider activity, calendar attendance,
LMS completion, security audit rows, or unconfirmed imported status as
execution truth.

## Candidate Derived Metrics

V1 should be read-time derived. Do not persist new canonical truth on `Task`.

| Metric | Meaning | Profile |
| --- | --- | --- |
| `task_switch_count` | Count of explicit `task_switch` pause/switch events in a window. | Exclude dirty, voided, retroactive-only, auto-closed, and stale sessions. |
| `interruption_chain_count` | Count of parent-child interruption chains. | Use confirmed task/session topology only. |
| `parked_task_count` | Paused open-session tasks waiting for resolution. | Current user only; no provider/passive rows. |
| `reentry_latency_minutes` | Pause/switch/miss to resume, switch, drop, or mark-done resolution. | Treat open unresolved work as censored, not failed. |
| `reentry_resolution_type` | Resolution outcome for parked/interrupted work: resumed, completed later, rescheduled, dropped, marked irrelevant, stale/open at day end, auto-closed. | Required before evaluating whether switching mattered. |
| `time_to_resolution_minutes` | Time from switch/pause/miss to explicit resolution. | Use active user-confirmed resolutions; treat unresolved work as censored. |
| `open_thread_end_of_day_count` | Count of unresolved parked/open threads remaining at local day end. | Recovery load indicator, not a failure score. |
| `switch_load_level` | Low/medium/high descriptive tier from current and recent switch topology. | Confidence tier, not calibrated probability. |
| `post_switch_active_delta_minutes` | Active execution drift after a switch compared with planned active duration. | Use active minutes; do not include pause overhead. |
| `planning_window_footprint_minutes` | Execution time plus bounded clean pause overhead. | Planning guidance only, not execution truth. |

Switch topology alone is insufficient. Without resolution outcomes, Lyra only
knows that a switch happened, not whether it mattered. Any future derived
metric must include what happened after the switch before supporting product
copy or research claims.

Do not create a `fragmentation_score`, `switching_score`, or similar
user-facing scalar. Scoring turns recovery state into judgment and should be
treated as a kill-path warning.

## Metacognitive Discrepancy Link

Metacognitive discrepancy can strengthen the interpretation but must not
replace topology.

Use it as a modifier when clean samples exist:

```text
switch topology + repeated estimate drift -> higher recovery-risk evidence
```

Do not infer:

```text
the user switched because they were avoiding the task
```

Allowed interpretation:

```text
This switched/parked work resembles prior work that ran over plan and took
longer to re-enter.
```

## Validity Threats

- **Reverse causality:** the user may switch because the task was already hard,
  unclear, or badly scoped.
- **Confounding:** emergencies, overload, deadline pressure, task ambiguity,
  provider changes, sleep, meetings, and excessive commitments can all produce
  the same topology.
- **Tautology:** `execution_efficiency = active / span` mechanically falls
  when pauses inflate span. Use it as footprint, not proof of degradation.
- **Exposure contamination:** a visible switch insight can change future pause,
  switch, and planning behavior.
- **Measurement artifact:** forgotten timers, stale-session repair, clock drift,
  and auto-close can mimic recovery friction.
- **Low-n/operator bias:** trusted-user and operator traces can generate
  hypotheses, not broad claims.

## Falsification

The hypothesis is falsified or demoted if, after clean-data and exposure
controls:

- switch/interruption sessions do not predict higher reentry latency than
  matched non-switch pauses;
- switch topology adds no predictive lift over category, deadline pressure,
  time of day, planned duration, user baseline, and exposure state;
- metacognitive discrepancy explains the outcome and switch topology adds no
  incremental signal;
- effects are unstable across users, windows, or comparable contexts;
- users repeatedly report that the system misread genuine emergencies,
  planned switches, or external commitments;
- the insight changes behavior enough that naturalistic evaluation is no
  longer separable.

## Kill Criteria

Kill or park the product surface if any of these happen:

- usefulness requires passive browser/activity tracking;
- the UI starts implying Lyra knows why the user switched;
- the surface creates shame, pressure, or identity interpretation;
- false positives dominate trusted-user feedback;
- users dismiss or churn after seeing the switch-footprint surface;
- exposure logging cannot distinguish clean behavior from post-insight
  behavior;
- the surface performs no better than simpler "paused work" and "missed plan"
  recovery affordances.

## Implementation Waves

### Phase 1: Documentation Only

- Add this hypothesis note.
- Register the hypothesis in the assumption register.
- Align terminology in inference, metrics, semantic conflict, integrity, and
  exposure docs.
- No runtime behavior changes.

### Phase 2: Read-Only Derived Metrics

- Add a backend derived-metrics service around existing `Task`,
  `StopwatchSession`, and `PauseEvent` rows.
- Add no schema migration unless attribution cannot be reconstructed.
- Keep `executed_duration_minutes` as active work.
- Exclude stale, retroactive, auto-repaired, dirty, voided, and forgotten-timer
  anomalies from averages.
- Derive resolution outcomes before interpreting switches:
  `reentry_resolution_type`, `time_to_resolution_minutes`, and
  `open_thread_end_of_day_count`.

### Phase 3: Pulse Re-entry Integration

- Add compact neutral reasons to existing re-entry candidates. This is the
  primary near-term surface.
- Suggested copy:
  - "Parked after a task switch."
  - "Paused for 42m."
  - "You have 3 open threads from earlier today."
  - "Later plan also slipped."
- Actions stay explicit: pick it back up, reschedule, drop, mark done, or keep
  parked.

### Phase 4: Insights Gated By Sample Support

- Add a weekly summary only after enough clean samples exist and only if the
  re-entry surface is already useful.
- Use "correlates with" language.
- Include confidence/sample status.
- Log exposure before using later behavior for adaptive inference.
- Never publish a weekly "you switch a lot" style insight.

### Phase 5: Evaluate Or Kill

- Compare against matched non-switch sessions.
- Check whether metacognitive discrepancy explains more than switch topology.
- Promote, revise, or kill the surface based on the criteria above.
