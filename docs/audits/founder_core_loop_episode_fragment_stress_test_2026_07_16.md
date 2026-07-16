# Founder Core Loop Episode-Fragment Stress Test

---
authority: audit-evidence
may_authorize_code: false
runtime_owner: none
status: documentation-only adversarial review
product_name: LyraOS
schema_authority: none
model_authority: none
experiment_authority: none
required_final_reviewer: founder
audit_date: 2026-07-16
---

## 1. Scope

This audit stress-tests the proposed `WorkSprint` and DecisionEpisode-fragment
approach against the current repository. It does not authorize a route, model,
migration, runtime behavior, deployment, or cohort use.

Evidence inspected:

- Pressure Map projection, plan-draft UI, exposure acknowledgement, and tests;
- Task creation, update, deadline binding, and lifecycle ownership;
- stopwatch start, pause, switch, stop, Redis recovery, and corrections;
- mutation, output-surface, user-data, and preservation registries;
- the plan-execution ontology, computation catalogue, repository archaeology,
  and parked research sequence.

## 2. Executive Verdict

The bounded founder Sprint remains the strongest next product experiment. The
proposed anti-duplication method is useful, but the pasted proposal goes too far
when it turns that method into three new universal governance artifacts.

Accept now:

- one domain-named `WorkSprint` candidate;
- a local Data Delta in every approved implementation plan;
- explicit existing authority owners;
- one idempotent activation command;
- bounded supersession;
- separate closure evidence and canonical mutation;
- founder usefulness and reconstruction gates.

Reject now:

- a universal semantic-field registry;
- a universal fragment registry;
- one L0-L6 promotion ladder;
- mapping every command, projection, correction, and exposure into an episode;
- a generic `DecisionEpisode`, `PlanLineage`, or recovery platform;
- fields with no current product consumer or executable policy.

The governing rule is:

> Specify the information delta of the next real product slice. Promote a
> shared abstraction only after a second independent slice needs the same
> semantics and sharing removes demonstrated duplication.

## 3. Findings

### F1. A supersession link is lineage

The statement "no PlanLineage" must mean "no generic PlanLineage subsystem,"
not "no lineage." A `supersedes_sprint_id` relation is a narrow lineage edge.

Founder v1 should permit one predecessor and at most one direct successor. The
service may walk that short chain for audit history. Current active work is
found by execution state, not by traversing a lineage graph. Do not add a root
ID, materialized path, revision table, or generic graph until real use needs
branching or frequent historical queries.

### F2. The proposed status list mixes phase and reason

`closed`, `superseded`, `abandoned`, and `expired` do not occupy one semantic
dimension. A minimal candidate uses:

```text
execution_phase: active | ended
end_reason: completed | superseded | abandoned | invalidated
reconciliation_status: not_due | due | resolved | waived
```

There is no `expired` state in founder v1 because no expiry policy exists.
There is no ordinary `awaiting_execution` state because activation is one
product command. Failed validation creates no Sprint. A committed database
start remains canonical even when best-effort Redis publication fails.

### F3. Pending reconciliation must not deadlock new work

The one-active-Sprint invariant applies only to `execution_phase=active`.
Ending a Sprint can leave reconciliation due without blocking a later Sprint.
The UI may surface pending reconciliation, but it cannot make historical
cleanup a prerequisite for starting new work.

### F4. `Clarify` does not share progress closure semantics

The current candidate outcomes fit execution, not ambiguity resolution.
Founder Sprint v1 should use `advance` or `finish`. Clarification remains a
Pressure Map correction or navigation action unless a later real workflow
proves that a timed clarification episode needs distinct outcomes.

Recommended member outcomes are:

```text
complete | advanced | untouched | replaced | irrelevant | unknown
```

### F5. Activation should be one command, not two product transactions

The current `StopwatchManager.start()` commits task/session truth and then
publishes Redis state best-effort. Therefore the honest contract is one
idempotent activation command with database truth and convergent Redis
recovery, not impossible database-plus-Redis atomicity.

Validation, ownership, idempotency, Sprint membership, task resolution, and
timer-start preparation must occur before the canonical commit. A lost HTTP
response after commit must converge on retry to the already-active Sprint.

### F6. The immutable intent kernel was oversized

The proposal included protected constraints and a priority rule before either
has a shipped Sprint consumer. Founder v1 needs only:

- selected obligation membership;
- one primary obligation;
- one bounded minimum-movement statement;
- accepted estimate and projection snapshots as evidence, not identity.

Changing membership, primary obligation, or minimum movement supersedes the
Sprint. Pauses, task order, working method, estimate disagreement, and ordinary
recovery do not.

### F7. Remaining-range feedback currently lacks a canonical owner

The Task model stores a planned-duration point. Pressure Map derives low/high
ranges. The repository has no canonical user-owned remaining-range command.
Writing a remaining range only to `work_sprint_member` and then letting
Pressure Map consume it would create a second estimate authority.

Founder v1 may:

- preserve accepted range and closure response as historical evidence;
- show forecast, observed session evidence, and closure together;
- apply an explicit existing Task duration edit when the user chooses a point;
- leave range recalibration parked until an estimate-correction authority is
  separately designed and approved.

It may not silently feed a Sprint-only range into Pressure Map computation.

### F8. Hidden task creation would duplicate obligations

Pressure Map already has a plan draft that creates canonical Tasks one row at a
time. Sprint activation must not call that path or create a generic Sprint
task.

The primary obligation must resolve to a user-visible canonical Task before
activation. If no task exists, the UI offers an explicit idempotent **Create
execution task** action through `TaskManager`. Supporting obligations may be
reference-only, but cannot become timer targets until explicitly resolved to a
Task.

### F9. A universal field registry would duplicate the control plane

The repository already has:

- mutation-impact ownership and query invalidation;
- output-surface and exposure policy;
- user-data export/delete ownership;
- clean-data and feature-preservation registries.

A new registry for every candidate semantic field would overlap these sources,
grow before runtime use, and require its own drift scanner. Use a local Data
Delta table in the approved plan. Add a shared registry only after two
independent implemented fragments demonstrate semantic drift that cannot be
controlled by the existing registries.

### F10. L0-L6 collapses independent questions

Product usefulness, evidence authority, cohort transportability, and
abstraction reuse are not one monotonic ladder. A field can be founder-useful
but scientifically weak, or shared by two services without cohort validity.

Track three separate decisions instead:

```text
product gate: unused | useful | rejected
truth gate: unreconstructible | reconstructible | corrected
reuse gate: local | repeated | shared
```

Do not produce one promotion score or universal authority level.

### F11. Not every loop stage is an episode fragment

Brain Dump commit is a canonical command. Pressure Map is a projection and
behavior-shaping surface. Stopwatch sessions are execution evidence. A task
correction is an append-only repair. They may participate in reconstructing a
Sprint without becoming persisted DecisionEpisode fragments themselves.

The future loop may be documented as a coverage map, but only an approved
domain workflow receives a full fragment contract.

## 4. Lean Data Delta Contract

Every future implementation plan should include one local table:

| Operation | Meaning | WorkSprint example |
| --- | --- | --- |
| `CREATE` | Irreducible new fact | accepted minimum movement |
| `REFERENCE` | Link to canonical fact | task, session, exposure IDs |
| `SNAPSHOT` | Historical context that may change | title, due time, accepted range, projection fingerprint |
| `DERIVE` | Recompute from canonical owners | active time, pause time, current pressure |
| `FORBID_COPY` | Must remain elsewhere | task state, deadline completion, render truth, canonical estimate |

Each row also names its consumer, privacy class, export/delete treatment,
missingness, and why persistence is necessary. Empty future placeholders fail
review.

## 5. WorkSprint Candidate Boundary

```text
Pressure Map projection
-> explicit task resolution
-> one idempotent activate command
-> existing stopwatch execution
-> explicit End Sprint
-> coarse reconciliation evidence
-> optional separately confirmed canonical task mutation
-> next Pressure Map recomputation from canonical state
```

WorkSprint owns purpose and boundary. It does not own current task state,
deadline truth, execution time, exposure truth, or current Pressure Map
estimates.

## 6. Best Next Moves

1. Commit the current docs/audit checkpoint separately from later product work.
2. Correct active documentation that still implies a universal episode or
   automatic plan-learning path.
3. Characterize caller-selected task state and the Pulse `Wins` sign defect;
   do not mix their eventual fixes with Sprint implementation.
4. Prototype and browser-test the dedicated Pressure Map route as a read-only
   product surface before adding Sprint persistence.
5. Write focused transaction tests around stopwatch start, Redis publication,
   idempotent retry, and task resolution before choosing migration fields.
6. Approve one minimal WorkSprint migration only after those tests confirm the
   transaction boundary.
7. Implement activation, then closure evidence, then explicit canonical
   updates, then next-map feedback. Do not build recovery or a decision
   question until the earlier path is voluntarily reused.
8. Revisit shared episode infrastructure only after a second independent
   domain workflow produces the same field semantics and lifecycle.

## 7. Hard Stop

This audit authorizes no code, migration, route, schema, feature flag, runtime
AI, automatic recovery, experiment, cohort promotion, deployment, or public
claim.
