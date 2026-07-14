# Pressure Map Product And Measurement Contract

**Status:** Active product and measurement contract.
**Implementation status:** Partial. The current Pulse panel is shipped; the
dedicated tab and the corrected projection described here are sequenced work.
**Created:** 2026-05-17.
**Revised:** 2026-07-12.
**Scope:** Pressure semantics, workload accounting, estimate authority,
whole-tab interaction design, scenario previews, and Day-0 gates.
**Runtime AI authority:** None.
**Schema authority:** None.

This file keeps its historical academic filename for compatibility. The
target product surface is provider-neutral, but it must never imply that it
contains non-academic workload until those obligations are actually admitted
to the projection.

## 1. Product Definition

The Pressure Map is a time-based model of obligations competing for limited
capacity. It shows where coverage breaks and lets the user preview the
smallest explicit action that could restore feasibility.

Within roughly ten seconds, it should answer:

1. What is creating visible pressure?
2. When is that pressure likely to peak?
3. Why does LyraOS currently believe that?
4. What is missing or uncertain?
5. What can the user change now through a real command?

Pressure means an operational mismatch:

```text
remaining obligation demand
versus
realistically represented capacity before the obligation is due
```

Pressure does **not** mean emotion, anxiety, motivation, discipline, focus,
avoidance, intelligence, productivity, clinical risk, or moral worth.

The intended interaction is:

```text
see the collision
-> understand its cause
-> inspect uncertainty
-> preview one change
-> confirm a canonical action
-> watch the projection redistribute
```

The map succeeds when it makes a real planning decision easier. A decorative
visualization, generic score, or list of non-executable suggestions does not
satisfy this contract.

## 2. Approved Design Target, Runtime Expansion Still Gated

Founder approval on 2026-07-12 permits the product contract to design the
shipped Pressure Map as a future dedicated tab. It does **not** lift the active
runtime freeze or authorize implementation of a new route, user input,
scenario engine, persistence model, or mutation command.

During freeze closure, active Pressure Map work is limited to:

- characterizing and correcting shipped arithmetic and authority defects;
- demoting or removing controls whose labels exceed their behavior;
- preserving browser-owned exposure truth;
- making the existing Pulse summary disclose scope, freshness, unknowns, and
  hidden counts honestly;
- and collecting real evidence about whether the truthful summary changes a
  decision.

The dedicated tab becomes eligible for a separate founder activation
checkpoint only after capture, onboarding, count-once accounting, action
parity, render-based measurement, and real Pulse orientation evidence pass.
If activated later, each implementation seam must preserve this boundary:

- the existing registered Pressure Map remains the surface owner;
- deterministic projection remains available without AI;
- no new behavioral or psychological construct is introduced;
- no automatic scheduling or mutation is introduced;
- no schema, provider, passive sensing, dependency graph, or claim class is
  introduced without a separately approved seam;
- every new action uses an existing canonical command or remains visibly
  unavailable;
- every scenario remains side-effect-free until explicit confirmation;
- every estimate remains a range with source and correction affordance;
- the expansion is reversible independently from the underlying task,
  deadline, calendar, and exposure authorities.

The dedicated tab is the approved product target, not current implementation
authority and not general permission to expand the product freeze.

## 3. Product Promise

The intended response is:

```text
This finally explains the shape of my week.
```

The map should reveal:

- obligations and deadlines;
- remaining effort ranges;
- work already represented by future blocks;
- due-date clusters;
- available-capacity ranges when an authority exists, otherwise the missing
  capacity evidence needed to compute them;
- estimate, source, and calendar uncertainty;
- obligations missing estimates, links, or coverage;
- operational scope-expansion signals;
- and the smallest currently executable repair.

Day-0 value is bounded legibility, not omniscience. An early map may use
confirmed calendar structure, user-entered work, provider obligations,
research priors, deterministic task semantics, and clearly labeled unknowns.
It becomes more personal only after clean linked execution, corrections, and
accepted plans exist.

Approximate data is useful only when the approximation is visible and
correctable.

The product should be willing to make a bounded prediction. `UNKNOWN` is
reserved for a genuinely missing authority or input; it is not the default
voice of the map. When a compatible prior exists, LyraOS shows a provisional
range prominently, names its broad basis, and offers a low-friction way to
correct it through real work.

## 4. Non-Goals

The Pressure Map must not:

- produce a dominant universal pressure score;
- infer emotion, cognitive load, energy, stress, motivation, or perfectionism;
- treat provider activity as execution or completion truth;
- treat scheduled intention as completed work;
- infer hidden obligations and present them as facts;
- invent dependencies or blockers;
- silently narrow uncertainty;
- claim exact productive capacity;
- mutate tasks, deadlines, calendar events, or scope automatically;
- optimize a schedule behind the user's back;
- use AI wording or estimates as canonical truth;
- imply that a calm visual design makes an uncertain result reliable.

A secondary structural index may eventually support sorting or diagnostics,
but it cannot replace the mechanism-revealing timeline or become a behavioral
claim.

## 5. Existing Authority And Compatibility

The registered Pressure Map remains a `diagnostic_planning_surface`.

It may compute and display:

- pressure clusters and time windows;
- visible demand, linked planning coverage, and represented capacity when
  authority exists;
- uncertainty-aware ranges;
- source and trust states;
- coverage questions and gaps;
- side-effect-free scenario drafts;
- and bounded next actions.

It does not own automatic task creation, calendar mutation, provider truth,
student-risk scoring, learning/mastery inference, clean calibration admission,
or execution truth.

The current API fields remain compatibility surface until a separately tested
response-version seam replaces them:

- `pressure_summary`;
- `compression_points`;
- `recovery_options`;
- `coverage_questions`;
- `capacity_context`;
- `items`, estimate ranges, methodology, warnings, source summary, authority
  metadata, exposure ID, and redacted render snapshot.

Existing clients may continue reading those fields while the implementation
introduces a projection model behind them. The redesign must not silently
remove a shipped field or change its meaning.

## 6. Surface Architecture

### 6.1 Pulse summary

Pulse keeps a compact summary that answers only:

- one dominant sentence in the form
  `[window]: [state], mainly [cause]; [largest caveat]`;
- at most three supporting numeric facts;
- exactly one primary action selected by the ranking rule in Section 12;
- and `Open Pressure Map`.

The summary must disclose hidden content with `+N more` or equivalent. It must
never silently render the first four items as though they were the full map.
It always states horizon, current academic/study scope, provider/calendar
freshness, and unresolved count. Unknown capacity suppresses alarm styling
rather than merely adding a caveat beneath a deficit.

### 6.2 Dedicated Pressure Map tab

The proposed canonical route is `/pressure-map`. It is a design target until
the runtime activation checkpoint passes. Horizon, view, and selected
obligation use restorable URL state; an unsaved scenario remains local and
requires confirmation before navigation discards it.

The dedicated tab is the canonical future orientation and scenario surface.
Its first viewport contains:

1. **Dominant interpretation sentence** - state, main cause, and largest caveat.
2. **At most three numeric facts** - selected from peak window, known demand,
   represented coverage, unknown count, and unscheduled range.
3. **One primary safe action** - blocking correction before planning.
4. **Time landscape and semantic list/table** - equal-primary views of the
   same projection.

The default desktop layout is a full-width time landscape with a right-side
inspector that starts closed. The inspector becomes a full-screen drill-down
on mobile for dense or mutable content. The primary visualization must not be
placed inside nested decorative cards.

The chart is never the only representation. A semantic ordered list or table
exposes one focusable control per obligation with an accessible name containing
timing, range, collision state, and trust. Selection moves focus to the
inspector heading; Escape/Back closes scenario, then inspector, then leaves the
route; closing returns focus and scroll origin. Horizon and scenario
recalculation use concise live-region announcements.

### 6.3 Views

The tab has three views over one projection model:

- **Time**: where demand and capacity may collide over 1, 7, or 14 days;
- **Sources**: which obligations or domains contribute demand, with unresolved
  work kept separate;
- **Coverage**: what is fully represented, partially represented, unscheduled,
  uncertain, blocked by confirmed facts, or missing an estimate.

These are internal views, not additional product tabs. They change
presentation, not truth ownership or calculations.

On mobile there is one page scroll axis. Relevant/peak windows are grouped
before the complete chronology, the sticky summary collapses after scrolling,
touch targets are at least 44px, and dense editing uses a full-screen flow
rather than a nested scrolling sheet.

## 7. Core Accounting Model

### 7.1 Required concepts

The implementation may use internal names that fit the repository, but the
projection must preserve these concepts:

- `Obligation`: user-confirmed or provider-derived structure with a due or
  relevant window;
- `EstimateEnvelope`: low/high remaining-effort range plus source set;
- `ScheduledCoverage`: future user-accepted blocks linked to an obligation;
- `CompletedEvidence`: clean, linked execution plus explicit scope-completion
  evidence; elapsed minutes alone do not reduce remaining scope;
- `AppliedCoverage`: the portion of future linked planning coverage that can
  cover remaining effort;
- `Overcoverage`: future linked planning coverage beyond remaining effort;
- `CapacityEnvelope`: low/high represented availability after deduplicated hard
  commitments;
- `ProviderCoverageStatus`: `complete`, `partial`, `stale`, `unavailable`, or
  `not_connected`, with window, fetch time, pagination status, and exclusions;
- `CoverageGap`: known missing estimate, schedule, source, or import coverage;
- `PressureProjection`: a deterministic versioned projection over time;
- `ScenarioDraft`: a side-effect-free proposed change and complete recomputed
  projection;
- `ProjectionDiff`: before/after changes with no claim that the scenario will
  cause the predicted outcome.

These are conceptual contracts. This revision authorizes no new database
tables. Wave 5A may add validated, versioned response DTO fields behind a
compatibility adapter; API response evolution is not persistence-schema
authority. Every numeric envelope rejects `low < 0` and `high < low`.

### 7.2 Count-once invariant

Every unit of work must be counted exactly once in each accounting role. The
projection keeps active-effort minutes and calendar-footprint minutes as
distinct estimands even when both use minutes as a unit.

```text
for each admissible joint scenario s:

remaining_s = max(0, total_estimate_s - completed_scope_credit_s)
feasible_coverage_s = clipped, deduplicated future linked footprint
applied_coverage_s = min(remaining_s, feasible_coverage_s)
unscheduled_s = max(0, remaining_s - feasible_coverage_s)
overcoverage_s = max(0, feasible_coverage_s - remaining_s)

remaining_s = applied_coverage_s + unscheduled_s
feasible_coverage_s = applied_coverage_s + overcoverage_s
```

Ranges are envelopes over admissible joint scenarios. The implementation may
not add or subtract independent interval endpoints and then claim the original
identity still holds.

Subject to uncertainty ranges and explicit unknowns:

- a linked deadline and its task are one obligation, not two loads;
- a scheduled study block is coverage of demand when it is linked, not new
  demand added on top of the same deadline estimate;
- an unlinked planned block is a capacity commitment, not assumed obligation
  coverage;
- a calendar event occupies one deduplicated busy interval, even when mirrored
  by a LyraOS task; it reduces capacity only after an availability authority
  exists;
- overlapping calendar events consume the union of occupied intervals, not
  the sum of duplicate minutes;
- future scheduled coverage does not count as completed work;
- elapsed execution reduces remaining scope only through an explicit,
  admissible scope-credit rule. A 60-minute session with 0% completion is not
  60 minutes of completed scope;
- completed scope credit beyond the estimate high bound marks the estimate
  inconsistent and requests correction; it is not silently floored;
- remaining effort and unscheduled demand are floored at zero;
- future coverage beyond remaining effort is `overcoverage`, not negative
  demand;
- an unknown relation remains unknown rather than being deduplicated by title
  similarity alone.

The permanent regression target is segment- and entity-level attribution, not
merely a matching aggregate total. Every displayed minute is traceable to one
normalized time segment, one-or-more contributing entity IDs, and one
accounting role.

### 7.3 Demand envelope

An `EstimateEnvelope` has state `known_range`, `provisional_range`, or
`unknown`. Unknown bounds are nullable and aggregates expose
`known_subtotal_range`, `unknown_obligation_count`, and `coverage_status`.

A provisional range is a first-class product answer, not a warning buried
beneath missingness copy. The map leads with the best admissible range and
then states what would make it more personal. It uses `unknown` only when no
compatible range can be justified.

Completed scope credit requires compatible estimand, unit, canonical linkage,
clean profile, observation window, and conversion rule. When those conditions
are absent, execution remains contextual evidence and the estimate stays
provisional or unknown.

If total estimate, scope credit, or linkage is unknown, the result carries that
unknown explicitly. The implementation may not substitute zero or a generic
prior without labeling it provisional.

### 7.4 Capacity envelope

Capacity is at least as uncertain as demand. It must not be drawn as a solid
fact while task estimates receive uncertainty treatment.

The repository currently has no authoritative availability denominator. A
calendar token, busy-minute sum, or task list cannot establish one. Therefore,
until explicit availability authority is separately approved, persisted, and
verified, capacity and collision state remain `UNKNOWN`. Wave 5A may still
correct demand, coverage, busy-interval union, and source completeness.

A future capacity envelope may use only:

- user-declared availability;
- confirmed calendar commitments;
- accepted LyraOS task blocks;
- explicit quiet hours or planning exclusions;
- source freshness and coverage status.

It must not infer sleep, energy, focus, productive hours, or hidden personal
constraints. Historical execution may inform a future descriptive personal
range only after a separate admission and validity review.

For half-open window `W = [as_of, end)`:

```text
H_confirmed = union(clip(confirmed_commitment_i, W))
H_possible = union(clip(possible_commitment_i, W))
C_low = measure(A_confirmed \\ H_possible)
C_high = measure(A_possible \\ H_confirmed)
```

Credential presence is not provider coverage. Fetch failure, stale data,
pagination truncation, unsupported all-day structure, or excluded intervals
produce `partial`, `stale`, or `unavailable`, never zero busy time. When
availability is absent or provider coverage is incomplete, capacity remains
`UNKNOWN` or visibly partial.

### 7.5 Collision states

Collision is evaluated for every due-time prefix using **unscheduled demand
versus residual capacity after all commitments**, including linked coverage.
Coverage and commitments are clipped to `[as_of, due_at)` so capacity after a
deadline cannot rescue work due before it.

Where an authoritative capacity envelope exists, the map uses interval
comparisons rather than a crisp invented threshold:

- `certain_visible_collision`: demand low bound exceeds capacity high bound;
- `possible_collision`: demand high bound exceeds capacity low bound, but the
  intervals overlap;
- `no_visible_collision`: demand high bound is within represented capacity low
  bound;
- `unknown`: demand, capacity, linkage, ordering, or coverage is insufficient.

`No visible collision` is not a promise that the week is safe. It means no
collision is supported by the currently represented evidence.

### 7.6 Pressure onset

An obligation appears where its remaining work starts competing for feasible
capacity, not only as a dot at its deadline. A deterministic projection may
show an earliest pressure-onset range or latest feasible start range, but it
must expose the formula version and source assumptions. It may not present a
single precise start time when demand or capacity is ranged.

Projection windows are frozen half-open intervals `[as_of, end)`. Every task,
calendar interval, coverage block, and due-time prefix is clipped consistently.
An obligation is included when its pressure-onset envelope intersects the
window even if its deadline falls just outside it. For one fixed `as_of`, the
1/7/14-day projections must nest consistently except for explicitly documented
resolution changes.

Lower estimate bounds round outward down and upper bounds round outward up.
Values below two hours remain in minutes or outward-rounded decimal hours; the
UI may not turn a nonzero range into `0-0h`.

The shipped `pressure_level` field is legacy due-date proximity, not the new
pressure construct. Treat it as `due_proximity_level` in compatibility code and
prohibit it from driving collision state or `compressed` copy.

## 8. Estimate Authority And Provenance

### 8.1 Source families

Every estimate shows one or more broad source families:

1. user-entered or user-corrected range;
2. clean personal evidence from linked comparable work;
3. research or population prior with registry reference;
4. deterministic task-type or semantic heuristic;
5. provider structure without duration authority;
6. future AI-proposed scope/difficulty candidate;
7. unresolved or missing.

The visible label may be concise, but the inspector must reveal which source
contributed, the sample count where applicable, and why the range remains
uncertain.

### 8.2 Selection and combination rules

- The deterministic floor is:
  `current user correction -> clean comparable personal range -> one
  registered fallback prior -> semantic family selection or widening ->
  UNKNOWN`.
- A current user correction owns the active planning range but retains its
  origin and does not become independent behavioral evidence merely because
  the user accepted it.
- Clean personal evidence may calibrate a future range only when canonical
  linkage, clean profile, estimand, unit, window, sample rule, and uncertainty
  are compatible.
- Browser code may display admitted envelopes but may not title-match,
  select, aggregate, or calibrate behavioral evidence. The backend issues the
  versioned envelope through one registered projection owner.
- Research and survey priors are competing alternatives, not multiplicative
  independent evidence. Contributions sharing a construct or source may not
  stack.
- Every registered prior declares estimand, unit, population, task context,
  extraction method, distribution, uncertainty, transportability, validation
  status, and version.
- Deterministic task semantics may choose one prior family or widen
  uncertainty; they do not apply a second directional multiplier or establish
  difficulty truth.
- Provider metadata establishes structure and due dates within its authority;
  it does not establish effort, learning, or completion.
- Survey priors remain provisional cold-start influence, visibly separable
  from personal evidence and never identity truth.
- A future AI candidate may propose components, estimate ranges, missing-scope
  questions, or disagreement. It is excluded from selected estimates, totals,
  collisions, and actions until the user explicitly converts it into a
  correction.
- The deterministic projection is computed first and identified by a baseline
  hash. For unconfirmed AI output, timeout, invalid response, quota exhaustion,
  revocation, or unavailability:
  `projection_without_ai == projection_with_ai`. Entitlement changes metadata,
  not deterministic truth.

The system retains competing source contributions long enough to explain the
selected range. It must not collapse disagreement into false precision.

### 8.3 Coverage authority

Coverage authority remains ordered:

1. instructor, moderator, or authoritative source metadata for the structure
   it actually establishes;
2. provider/LMS structure within provider authority;
3. cohort confirmations only under an approved aggregation, privacy, and
   transportability contract;
4. individual user correction for that user's map;
5. deterministic or future AI candidate awaiting confirmation.

The earlier `3-5 student confirmations` rule is retained as a provisional
historical design hypothesis, not a validated universal threshold and not
runtime authority. It may not be promoted without an approved cohort method,
minimum-N/privacy review, disagreement handling, and rollback.

An individual correction personalizes that user's map immediately. It does
not establish cohort truth.

### 8.4 Calibration rule

Personal planning calibration requires accepted intention plus admissible
observed execution. Provider activity, calendar presence, or a scheduled block
alone cannot calibrate execution.

Allowed:

```text
Your linked Quiz 2 preparation took longer than the prior range.
The next range is wider while LyraOS gathers comparable evidence.
```

Forbidden:

```text
You are slow.
You wasted time.
Opening this resource proves you studied it.
```

### 8.5 Scope-expansion risk

Scope states are explicit and non-interchangeable:

- `confirmed_scope_change`;
- `self_reported_scope_change`;
- `initial_scope_ambiguity`;
- `candidate_missing_component`.

Only a supported temporal change is called expansion. An initial ambiguous
title, upward correction, or AI-proposed component is not itself evidence that
scope expanded.

Operational evidence may include:

- the user added components after the initial estimate;
- the provider changed deliverables or coverage;
- linked attempts repeatedly revealed additional explicit work;
- the user corrected the estimate upward;
- the title or description contains unresolved deliverables;
- a future AI parser proposes missing components that the user has not yet
  confirmed.

The map may widen a provisional range or ask a clarification. Candidate
components are not counted as obligations or demand until confirmed. It may
not say the user is a
perfectionist, avoidant, undisciplined, or likely to expand scope without an
operational evidence basis and claim authority.

### 8.6 Unaccounted obligations

The map distinguishes missing representation from invented work with explicit
states:

- `known_unestimated`;
- `known_unscheduled`;
- `unlinked_commitment`;
- `ingestion_gap`;
- `out_of_scope_domain`;
- `candidate_missing_component`.

Supported evidence includes:

- unresolved Brain Dump items;
- parser partial failures or excluded rows;
- stale or incomplete provider sync;
- deadlines without estimates;
- scheduled blocks without linked obligations;
- obligations without future coverage;
- user-declared missing workload;
- imported structure awaiting confirmation.

LyraOS may say `work may be missing from this map`. A known unscheduled
obligation is not unaccounted, and an unlinked block is a capacity commitment,
not hidden demand. LyraOS may not invent a hidden task and present it as
observed truth.

## 9. Category And Scope Boundary

The current projection contains `academic` and `study` rows:

- `academic`: institution-provided or prescheduled structure such as
  deadlines, lectures, tutorials, labs, and classes;
- `study`: user-owned revision, reading, problem solving, assignment work, and
  exam preparation blocks.

They share a pressure surface because both consume study capacity, but their
sources remain distinct. Provider structure is not self-study behavior, and
self-study intention is not provider coverage truth.

Until non-academic obligations are admitted through an active contract, the
UI must say `study workload`, `academic and study pressure`, or another
truthful bounded label. Removing `academic` from copy must not make a partial
projection look like a whole-life workload model.

## 10. Time Landscape

The primary visual is a horizontal time landscape on desktop:

```text
now -> today -> 3 days -> 7 days -> 14 days

obligation demand          [------????------]
future linked coverage       [====]
unscheduled demand                 [####]
busy intervals            [==]       [===]
capacity, if authorized   [====================]
```

When availability authority is absent, the capacity row reads `not measured`
and the demand, coverage, unscheduled work, and busy intervals remain useful.
The landscape does not disappear merely because one denominator is missing.

Visual encoding should communicate:

- horizontal position: relevant time and deadline window;
- width: feasible or pressure-onset window;
- thickness: remaining effort range, not emotional severity;
- one texture dimension only: estimate uncertainty;
- inline labels/icons: provenance, freshness/trust, and missing coverage as
  separate non-exclusive states;
- stacking: obligations competing in the same time window; capacity comparison
  appears only when authorized;
- link: only confirmed obligation/coverage/dependency relations.

The exact encoding requires usability testing. Color is never the sole carrier
of urgency, uncertainty, trust, or selection. High pressure uses concentrated
contrast rather than flashing, pulsing alarm decoration.

Every ranged statement includes an interpretation rather than requiring mental
interval arithmetic. When capacity authority exists, an example is: `Possible
collision; demand exceeds represented capacity by 0 to 2 hours because the
ranges overlap.` Accessible text uses `4 to 8 hours`, not an ambiguous hyphen.
Decision-critical trust, timing, provenance, and errors use persistent text at
least 4.5:1 contrast; decorative microtype is forbidden for these semantics.

On mobile, the same projection becomes stable day/window rows with a sticky
summary and explicit expand controls. It must not shrink a fourteen-day chart
until labels, targets, and ranges become unreadable.

## 11. Selection Inspector

Selecting an obligation opens an inspector answering:

1. **Why is this creating pressure?**
2. **What does LyraOS know?**
3. **What is uncertain or missing?**
4. **What remains unscheduled if nothing changes?**
5. **What real actions are available?**

Example evidence:

```text
Due in four days.
Estimated remaining work: 4-7h.
Future linked coverage: 90m.
Estimate source: research prior plus your correction.
Calendar coverage: partial.
Unscheduled work: approximately 2.5-5.5h.
```

The inspector never includes a field that the system lacks the capability to
evaluate. `Dependency unknown` is shown only when a dependency candidate or
confirmed dependency contract exists; otherwise the field is omitted.

## 12. Canonical Actions

Every rendered action has one of three honest states:

- executable through a named canonical command;
- navigation to a named correction surface;
- unavailable with a short reason and no button styling.

Allowed action families, when canonical authority exists:

- confirm or correct an estimate;
- confirm or correct coverage;
- schedule a linked block;
- split remaining effort into explicitly smaller chunks;
- move or reschedule movable work;
- shrink user-controlled scope;
- mark irrelevant or drop where deletion/retention authority permits;
- review missing calendar or provider coverage;
- clarify a confirmed blocker.

`Review calendar` may be a deep link. It must not look like a mutation.
`Confirm coverage` and `mark irrelevant` must not render as commands until a
canonical write and rollback exist.

`Split into blocks` is truthful only when the preview divides one obligation's
remaining effort into smaller explicit chunks whose ranges reconcile with the
original estimate. Sequencing whole-sized rows from the next half-hour is not
splitting and must be renamed or removed until corrected.

Primary action ranking is deterministic:

1. blocking estimate, coverage, freshness, or scope correction;
2. one scoped reversible canonical action;
3. navigation to obtain missing context;
4. no action when none is safe.

Exactly one first-viewport call to action is allowed. A blocked planning action
may remain inspectable as unavailable, but not clickable. Ranking is returned
with the projection as action state and rationale; JSX ordering does not own
policy.

## 13. Scenario Preview

Scenario mode is side-effect-free. It supports a bounded set of proposals:

- correct estimate;
- add a linked work block;
- move a movable block;
- split remaining effort;
- shrink user-controlled scope;
- remove an irrelevant obligation from the active plan.

Each preview:

1. clones the admitted projection inputs;
2. applies one explicit proposed change;
3. recomputes the entire horizon and every affected obligation;
4. shows before/after demand, linked coverage, and unscheduled work, adding
   capacity and collision changes only when availability authority exists;
5. states which assumptions did not change;
6. performs no product mutation;
7. exposes one `Apply` command only when the proposal maps to canonical
   mutation authority.

A preview may not locally move one bar while leaving competing obligations
stale. `Pressure improved` is descriptive of the deterministic projection,
not a causal promise about user behavior.

Scenario v1 compares one frozen baseline with one frozen draft. Both use the
same scale and row order. A textual diff leads with unscheduled-range change,
new or worsened collisions when computable, and assumptions that did not
change. `Apply` stays disabled until full recomputation completes.

The current editable block form is a `Plan draft`, not a scenario preview. It
collapses ranges, may enrich rows asynchronously, and can apply several task
creates with partial success. Until a durable proposal identity and mutation
receipt exist, it must not claim scenario recomputation or atomic plan apply.
A partial apply requires an explicit receipt naming created, failed, and
unchanged rows plus the available rollback/correction path; closing the dialog
cannot imply rollback.

Scenario persistence, multi-mutation lineage, and atomic whole-plan rollback
are not authorized under the current no-schema boundary. If a first scenario
is later activated, it is one no-write server recomputation plus at most one
existing idempotent canonical mutation.

## 14. Trust-State Copy

| Trust state | User-facing meaning |
| --- | --- |
| `verified_exact` | An authoritative source supports this structure. It still does not prove execution, learning, or completion. |
| `verified_reachable` | LyraOS reached or imported the item. Coverage and correctness may still need confirmation. |
| `ambiguous` | More than one plausible interpretation remains. |
| `requires_user_confirmation` | A usable candidate exists, but confirmation is required before stronger planning. |
| `stale` | The source may be outdated. Re-check before planning. |
| `dead_link` | The source could not be reached. Do not use it as coverage truth. |
| `access_denied` | LyraOS cannot inspect the source. Ask the user or provider for a safer path. |

Trust meaning must remain consistent across the map, inspector, scenario
preview, correction flow, export, and provider-native surfaces.

## 15. Copy And Emotional Design

Pressure is described as a structural condition, not a personal failure.

Allowed:

```text
Three obligations compete for the same two evenings.
This estimate is still wide because the task scope is unconfirmed.
Correct the estimate or add a linked block to preview the difference.
LyraOS estimates 4-7 hours for these tasks. Start the next timer and make the next estimate more yours.
Think that range is off? Start the task and prove the estimate wrong.
```

When an availability authority exists, this additional comparison is allowed:

```text
Between Tuesday and Thursday, visible demand is 9-13h and represented capacity is 5-7h.
```

Forbidden:

```text
You are overloaded.
You are behind because you procrastinated.
Your pressure score is 82.
LyraOS knows you need six focused hours.
Your perfectionism is expanding this task.
```

The emotional target is `the system located the constraint`, not `the system
judged me`. Calm styling follows reliable arithmetic and action parity; it
must never camouflage broken accounting.

The challenge is aimed at the estimate, never at the user's competence or
discipline. Timer language must also stay measurement-honest: starting a timer
creates execution evidence, not completed-scope truth. A later estimate may
learn only from canonically linked, clean, finalized sessions and explicit
correction rules.

When capacity, scope, or provider coverage is unknown, uncertainty receives at
least equal visual salience to any capacity or collision claim and alarm
styling is suppressed. The map still leads with the demand and coverage ranges
it can defend instead of repeating `unknown` across the surface. A bounded
example is: `Visible work is 6-9h; 3h is already represented in your plan.
Free capacity is not measured yet.` The surface provides a neutral `Review
later` or leave path and never exposes raw archetype IDs or identity-like
estimate provenance.

## 16. Exposure And Outcome Truth

The map is behavior-shaping output. These events remain distinct:

```text
projection computed
-> candidate delivered
-> browser rendered
-> item inspected
-> scenario previewed
-> action selected
-> mutation confirmed
-> later execution or recovery outcome
```

- Browser render truth requires authenticated acknowledgement.
- The server binds each decision to one surface variant, owns the authoritative
  rendered timestamp and canonical stimulus hash, and rejects client-supplied
  surface mismatches or backdating.
- Direct API reads do not create render truth.
- Scenario generation is not mutation.
- Preview selection is not action success.
- Applied scheduling is not execution.
- Recovery selection is not recovery outcome.
- Every applied scenario links to the resulting canonical mutation IDs.
- Exposure contamination remains visible to downstream analysis.

Pulse summary, dedicated Time view, obligation inspector, and scenario preview
require distinct registered surface variants or facets before the tab ships.
`Opened` means authenticated browser render, never server decision creation.
View, preview, action, mutation, rollback, and outcome remain separate
denominators.

## 17. Day-0 And Orientation Gates

### Day-0 gate

A new account can:

1. complete or skip onboarding without identity-style claims;
2. Brain Dump or import real workload;
3. see which items were accepted, rejected, reused, or remain unresolved;
4. open the map from the capture result and from Pulse;
5. identify demand, scheduled coverage, and whether capacity is represented or
   still unmeasured;
6. inspect and correct at least one estimate or coverage assumption through a
   real command;
7. preview one bounded change without mutation;
8. apply one canonical action explicitly;
9. encounter no personal-history or whole-life claim before evidence exists.

### Orientation gate

Code-level completion requires a real-cookie browser proof that the full path
is understandable and reversible. Product-level completion requires at least
one real non-synthetic use where the user:

- identifies a specific collision or important uncertainty;
- changes or materially confirms a planning decision;
- previews the redistribution;
- applies or deliberately rejects the proposed action;
- and can explain why the map changed.

This evidence establishes usability of the mechanism, not general efficacy.
Synthetic fixtures can prove invariants but cannot satisfy founder product-loop
fit.

## 18. Current Implementation Audit

### Preserve

- 1/7/14-day horizons;
- deterministic ranges and assumptions;
- source and trust distinctions;
- read-only safe mode;
- browser-owned render acknowledgement;
- explicit preview and lock-in;
- canonical task creation and conflict handling;
- dismiss-without-write;
- provider provenance and export/delete coverage.

### Correct before trusting totals

- current `estimated_*`, `known_load`, and `pressure_level` fields are legacy,
  non-reconciled values. They are prohibited as v2 collision inputs and the
  Wave 5A accounting gate is unsatisfied;
- planned academic/study tasks currently enter item estimates and can be added
  again as planned load;
- linked deadlines and tasks are not yet reconciled as one obligation;
- calendar and task occupancy are summed without a complete interval-union and
  mirror-dedup contract;
- provider failure can collapse to zero events while the surface still reports
  Calendar connected;
- all external deadlines become `verified_reachable` without a freshness
  decision;
- capacity is represented more confidently than the evidence supports and no
  availability denominator exists;
- the current schema cannot express unknown estimates, overcoverage,
  attribution roles, freshness, or collision state and does not validate
  `0 <= low <= high`.

### Correct before trusting estimate authority

- the browser title-matches tasks and aggregates planned, executed,
  completion-scaled, and pause evidence outside a canonical clean profile;
- the Pressure Map consumes `task.creation_nudge` bias lookup output without
  honoring that surface's suppression/exposure contract;
- accepted system-generated duration can later re-enter calibration as though
  it were independent user estimation evidence;
- type, semantic, survey, archetype, and research contributions can stack
  without declared independence or estimand compatibility;
- visible provenance can expose raw archetype identifiers;
- runtime copy still promotes `3-5 student confirmations` even though the
  contract classifies that threshold as an unvalidated historical hypothesis.

Pressure Map estimate selection and clean-data admission must move to one
server-side projection owner before personal calibration is trusted.

### Correct before calling actions complete

- coverage questions lack a canonical correction command;
- several recovery options are labels only;
- `split_into_blocks` does not yet prove genuine smaller chunks;
- draft placement sequences blocks from the next half-hour rather than
  recomputing feasible capacity;
- plan preview can remain available while blocking coverage is unresolved.

The first correction is demotion or removal of unsupported actions, not the
creation of several new commands in one seam.

### Correct before calling Day-0 orientation complete

- the compact panel silently caps items and reasons;
- estimate provenance is compressed and direct range correction is missing;
- the provider-neutral copy can overstate the current academic/study scope;
- normal hosted recovery emission remains safety-gated;
- the current panel sits too low and too narrowly to serve as the complete
  time landscape;
- decision-critical microtype currently fails legibility/contrast expectations
  and creation/error state changes lack complete live announcements;
- operator `pressure_map_opened` currently derives from decision rows rather
  than authenticated render truth and does not separate Pulse from future tab
  exposure.

## 19. Delivery Sequence

### Stage A: accounting truth

- add characterization fixtures for linked deadline/task, unlinked blocks,
  overlapping calendar events, partial coverage, missing estimates, and stale
  sources;
- establish entity-level count-once attribution;
- separate demand, linked coverage, unrelated busy time, and unknowns;
- report provider coverage and interval-unioned busy time without inventing an
  availability denominator;
- keep capacity and collision `UNKNOWN` until a separate availability authority
  is approved, while still presenting admissible provisional demand ranges;
- change no estimate prior while correcting accounting.

### Stage B: action truth

- remove or demote non-executable options;
- add canonical correction only where ownership and rollback are clear;
- make split semantics real or rename them;
- disclose hidden items and reasons;
- keep explicit preview and confirmation.

### Stage C: truthful Pulse orientation

- lead with one bounded demand/coverage interpretation and one safe action;
- expose scope, freshness, unknown count, and hidden-item count without turning
  the surface into a missingness report;
- prove the compact surface changes or materially clarifies one real decision;
- measure Pulse render truth independently from decision creation;
- stop at `activation_approval_pending` before adding a route or tab shell.

### Stage D: activated dedicated Time view

This stage requires the explicit runtime activation checkpoint in the core-loop
plan. If activated:

- add the full-tab shell and Pulse entry point;
- ship Time first; keep Coverage and Sources parked;
- add desktop inspector and accessible mobile drill-down;
- prove keyboard, focus, target size, zoom, texture, and non-color semantics;
- preserve the compact Pulse summary as a truthful subset.

### Stage E: scenario engine

- wait until the required canonical recovery command exists and Wave 6 has
  proved its authority;
- implement a pure full-horizon recomputation;
- support one proposal family per seam;
- prove before/after accounting and no-write preview;
- link `Apply` to existing canonical commands;
- browser-prove rollback and cleanup.

### Stage F: personal calibration

- admit clean linked execution only after unit, source, and sample gates;
- keep user corrections and personal evidence distinguishable;
- report calibration error and disagreement;
- do not call the range validated without baseline and uncertainty evidence.

### Stage G: future AI augmentation

Only a later approved plan may let the `ReasoningRuntimeContract` propose:

- task components;
- scope-ambiguity questions;
- difficulty/range candidates;
- competing explanations for estimate disagreement;
- smoother wording for already-authorized actions.

AI remains candidate authority. It cannot own the projection, capacity,
dependency truth, mutation, exposure, or claim promotion.

## 20. Literature Translation Boundary

The design uses external literature as structural guidance, not product-effect
proof:

- The personal-informatics stage model distinguishes collection, integration,
  reflection, and action. It supports connecting capture to an executable
  decision surface; it does not prove that this Pressure Map improves outcomes.
  See [Li, Dey, and Forlizzi, CHI 2010](https://doi.org/10.1145/1753326.1753409).
- Research on gaps in reflection support motivates moving beyond `look at your
  data` toward inspectable action paths; it does not authorize behavioral
  attribution. See [Cho et al., CHI 2022](https://doi.org/10.1145/3491102.3501991).
- Uncertainty-visualization research supports making overlapping ranges and
  ambiguity visible, while also showing that presentation effects are
  task-dependent. The visual encoding must therefore be usability-tested in
  LyraOS rather than treated as universally effective. See
  [Dong and Hayes, 2012](https://doi.org/10.1177/1555343411432338) and
  [Bisantz et al., 2011](https://doi.org/10.1177/1555343411415793).
- Planning-fallacy research supports retaining empirical and corrected ranges
  instead of trusting one inside-view estimate. It does not justify a fixed
  universal multiplier. See
  [Buehler, Griffin, and Ross, 1994](https://doi.org/10.1037/0022-3514.67.3.366).
- Resource-constrained scheduling provides a useful demand-versus-capacity
  formalism, but human availability is not a machine resource and must retain
  uncertainty, consent, and user control. See
  [Trojet, H'Mida, and Lopez, 2011](https://doi.org/10.1016/j.cie.2010.08.014).

No effect size, threshold, prior, or scheduling policy transfers directly from
these sources into runtime.

## 21. Hard Stop

This contract does not authorize:

- runtime AI or ReasoningRuntime wiring;
- automatic scheduling or recovery;
- new provider adapters;
- passive availability or energy inference;
- dependency or task-graph persistence;
- schema migration;
- validated difficulty, productivity, stress, or risk claims;
- cohort defaults from founder behavior;
- public efficacy claims.

Implementation proceeds only through the ordered refactor plan, one accounting
or action boundary at a time, with characterization, browser proof, cleanup,
and rollback.
