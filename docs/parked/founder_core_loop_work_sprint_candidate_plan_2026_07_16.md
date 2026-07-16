# Parked Founder Core Loop WorkSprint Candidate Plan

---
authority: parked-product-plan
may_authorize_code: false
runtime_owner: none
status: documentation-only candidate pending founder activation
product_name: LyraOS
schema_authority: none
route_authority: none
experiment_authority: none
required_final_reviewer: founder
plan_date: 2026-07-16
---

## 1. Objective

Test whether one bounded founder workflow makes the existing product loop
voluntarily useful:

```text
capture/import
-> Pressure Map orientation
-> explicit bounded intent
-> timer-observed execution
-> lightweight reconciliation
-> visible next-cycle feedback
```

The candidate is a modular-monolith vertical slice. It is not a universal
DecisionEpisode implementation, plan graph, experiment platform, or cohort
policy.

## 2. Existing Authorities To Reuse

| Fact or behavior | Existing owner | WorkSprint treatment |
| --- | --- | --- |
| Current task state and duration | `TaskManager` | reference only |
| Deadline and provider structure | deadline/provider services | reference and immutable snapshot |
| Pressure projection | `academic_pressure` | reference fingerprint and accepted snapshot |
| Session, pause, switch, stop | `StopwatchManager` | reference sessions; derive time |
| Render and interaction truth | Exposure Ledger | reference exposure/outcome IDs |
| Export and deletion | user-data registry | register new rows before activation |
| Cache impact | query-key contract | add Sprint mutation effects explicitly |

## 3. Founder V1 Product Contract

### Selection

- Select one to three visible obligations.
- Exactly one selected obligation is primary.
- The primary must resolve to an existing canonical Task before activation.
- Missing task resolution is explicit and user-visible; no hidden Sprint task
  is created.
- Supporting obligations may remain reference-only and cannot be stopwatch
  targets until explicitly resolved to Tasks.
- Target types are `advance` and `finish`. `Clarify` remains a Pressure Map
  correction/navigation action in v1.

### Intent kernel

The immutable identity is:

- selected obligation membership;
- primary obligation;
- bounded minimum movement.

Changing any kernel field creates a successor Sprint. Estimate disagreement,
pause/resume, working method, execution order, and recovery within the same
purpose do not.

### Lifecycle

```text
execution_phase: active | ended
end_reason: completed | superseded | abandoned | invalidated
reconciliation_status: not_due | due | resolved | waived
```

- At most one Sprint per user may have `execution_phase=active`.
- Reconciliation due does not block a later Sprint.
- There is no automatic expiry in v1.
- A successor has one `supersedes_sprint_id`; each predecessor has at most one
  successor. This is bounded lineage, not a generic PlanLineage subsystem.

### Activation

One idempotent product command must:

1. authorize the founder capability and reject the operator;
2. validate projection freshness and obligation ownership;
3. resolve the primary Task without hidden creation;
4. reject or confirm an existing active timer conflict through current
   stopwatch semantics;
5. create Sprint/member evidence and link the new stopwatch session in the
   canonical database commit;
6. return the mounted active state;
7. converge on retry when the response is lost after commit.

Redis publication remains best-effort after canonical database truth and uses
the existing rehydration path. Validation failure produces no Sprint row.

### Closure

**End Sprint** records one outcome per member:

```text
complete | advanced | untouched | replaced | irrelevant | unknown
```

Closure evidence never completes a Task or Deadline by itself. Any proposed
canonical consequence is previewed and separately confirmed through the
existing owner. WorkSprint retains mutation references, not duplicated state.

The first version does not own or apply low/high remaining-effort ranges.
Pressure Map may show accepted forecast, observed execution, and confirmed
closure together. A user-confirmed point-duration edit may use the current Task
edit authority. Range recalibration requires a later estimate-authority plan.

## 4. Local Data Delta

| Candidate information | Operation | Canonical owner or reason |
| --- | --- | --- |
| Sprint ID and user | `CREATE` | domain identity and ownership |
| Execution phase/end reason | `CREATE` | Sprint boundary, not Task lifecycle |
| Reconciliation status | `CREATE` | product burden and closure completeness |
| Idempotency key | `CREATE` | exactly-once activation |
| Selected membership and primary | `CREATE` | accepted bounded intent |
| Minimum movement | `CREATE` | user-confirmed purpose |
| Task/deadline/session/exposure IDs | `REFERENCE` | existing authorities |
| Title, due time, accepted estimate, provenance | `SNAPSHOT` | decision-time reconstruction |
| Projection fingerprint/version | `SNAPSHOT` | stale-decision detection |
| Active duration and pauses | `DERIVE` | StopwatchManager/session truth |
| Current pressure and coverage | `DERIVE` | academic pressure projection |
| Current Task/Deadline state | `FORBID_COPY` | canonical managers |
| Browser render state | `FORBID_COPY` | Exposure Ledger |
| Current remaining range | `FORBID_COPY` | no approved canonical owner yet |

No candidate field enters a migration merely because it appears in this table.
The implementation seam must name its immediate consumer and irrecoverability.

## 5. Candidate Product Surface

- Add a dedicated Pressure Map route only after separate activation approval.
- Pulse remains a compact orientation summary linking to the route.
- Reuse the current Pressure Map query; do not clone its arithmetic.
- First viewport shows demand range, primary pressure source, selected count,
  and one obvious **Start Sprint** command.
- Keep the current plan draft as secondary **Schedule blocks** functionality.
  Sprint activation never invokes that multi-create path.
- On activation, navigate to Today with visible Sprint context.
- On failed pre-commit activation, remain on the map with the original
  selection intact. On an ambiguous lost response, query current Sprint before
  offering retry.
- Reconciliation should normally take under 30 seconds and may be deferred
  without blocking new execution.

## 6. Feedback Contract

The first feedback contract is deliberately descriptive:

```text
accepted range and intent
+ linked session evidence
+ confirmed member outcome
-> next-map evidence panel
```

It may say what changed, what did not, and what remains unresolved. It may not
claim personal learning, automatically alter another obligation, or promote a
Sprint-only range into canonical estimate truth.

Only after this descriptive feedback changes or materially clarifies a real
founder decision should a separate seam consider one explicit estimate
correction primitive.

## 7. Sequence If Later Activated

1. Commit and prove the documentation checkpoint.
2. Correct caller-controlled create state and Pulse label integrity in separate
   seams.
3. Ship the dedicated route as a read-only reuse of current Pressure Map truth.
4. Characterize activation transaction, idempotency, active-timer conflicts,
   Redis loss, and retry behavior.
5. Approve the minimal migration from fields with proven consumers.
6. Implement one activation command and mounted active context.
7. Add closure evidence without canonical mutation.
8. Add separately confirmed canonical Task effects where current authority is
   sufficient.
9. Add descriptive next-map feedback.
10. Add recovery and supersession only after voluntary use exposes the need.
11. Add at most one decision-changing question only after the base loop works.

## 8. Adversarial Proof

Required cases include:

- stale projection fingerprint with zero writes;
- double click and two-tab activation;
- lost response after database commit;
- Redis publication failure and DB rehydration;
- existing running or paused timer;
- cross-user Task, Deadline, Sprint, and exposure IDs;
- operator mutation rejection;
- missing or voided primary Task;
- provider obligation disappearance after snapshot;
- supporting obligation without a Task;
- task switch outside Sprint membership;
- closure deferred followed by a new Sprint;
- closure and abandon called twice;
- supersession with no fork and preserved prior sessions;
- no automatic Task/Deadline completion;
- no duplicate task from a linked obligation;
- export, account deletion, retention, and Redis cleanup;
- browser render only after authenticated acknowledgement.

## 9. Founder Product Gates

- **Start:** three real attempts, at least two voluntary starts, no repair.
- **Closure:** three closures, usually under 30 seconds, no fabricated
  attribution.
- **Feedback:** two later maps visibly clarify a decision using prior Sprint
  evidence.
- **Recovery:** only after the above, two real disruptions and one voluntarily
  useful recovery.
- **Promising:** five voluntary cycles on three days, one changed decision,
  one useful reconciliation/recovery, and no QA-only dependence.
- **Stable:** ten voluntary cycles on five days without manual database repair
  or recurring annoyance.

Twenty to thirty episodes may later support descriptive recurrence analysis.
That larger sample is not required before deciding whether the product loop is
useful enough to continue.

## 10. Failure Routing

- No voluntary start: return to orientation and selection UX.
- Hidden or duplicate Tasks: stop activation and repair task resolution.
- Closure feels ceremonial: reduce to primary-outcome confirmation.
- Feedback does not change or clarify the next decision: stop adding episode
  structure and reconsider the product mechanism.
- Multiple unresolved closures become annoying: infer less, ask less, and keep
  them non-blocking.
- A second workflow needs different opening, membership, or closure semantics:
  keep it domain-specific rather than forcing shared infrastructure.

## 11. Hard Stop

This plan authorizes no route, code, schema, migration, runtime AI, automatic
mutation, experiment, cohort use, deployment, or public claim. Activation
requires a clean decision packet and explicit founder approval after the
documentation checkpoint is committed and proven.
