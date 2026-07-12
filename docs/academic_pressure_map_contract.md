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

## 2. Bounded Existing-Surface Expansion

Founder approval on 2026-07-12 permits the shipped Pressure Map to expand from
a compact Pulse panel into a dedicated tab, provided each implementation seam
preserves this boundary:

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

The dedicated tab is an expansion of a shipped decision surface, not general
permission to expand the product freeze.

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
- available-capacity ranges and coverage gaps;
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
- visible demand, linked planning coverage, and represented capacity;
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

- next peak window;
- visible demand range versus represented capacity range;
- uncovered-work range;
- main pressure source;
- one primary action;
- and `Open Pressure Map`.

The summary must disclose hidden content with `+N more` or equivalent. It must
never silently render the first four items as though they were the full map.

### 6.2 Dedicated Pressure Map tab

The dedicated tab is the canonical orientation and scenario surface. Its first
viewport contains:

1. **Peak pressure window** - a time range, not a severity identity.
2. **Demand versus capacity** - both expressed as ranges.
3. **Uncovered work** - obligation count and effort range.
4. **Main source** - the obligations or missing coverage creating the largest
   visible mismatch.
5. **Time landscape** - the primary visual, immediately below the summary.

The default desktop layout is a full-width time landscape with a right-side
inspector for the selected obligation. The inspector becomes a bottom sheet
or full-screen drill-down on mobile. The primary visualization must not be
placed inside nested decorative cards.

### 6.3 Views

The tab has three views over one projection model:

- **Time**: where demand and capacity may collide over 1, 7, or 14 days;
- **Sources**: which obligations or domains contribute demand, with unresolved
  work kept separate;
- **Coverage**: what is fully represented, partially represented, unscheduled,
  uncertain, blocked by confirmed facts, or missing an estimate.

Tabs change presentation, not truth ownership or calculations.

## 7. Core Accounting Model

### 7.1 Required concepts

The implementation may use internal names that fit the repository, but the
projection must preserve these concepts:

- `Obligation`: user-confirmed or provider-derived structure with a due or
  relevant window;
- `EstimateEnvelope`: low/high remaining-effort range plus source set;
- `ScheduledCoverage`: future user-accepted blocks linked to an obligation;
- `CompletedEvidence`: clean, linked execution that can reduce remaining work;
- `CapacityEnvelope`: low/high represented availability after deduplicated hard
  commitments;
- `CoverageGap`: known missing estimate, schedule, source, or import coverage;
- `PressureProjection`: a deterministic versioned projection over time;
- `ScenarioDraft`: a side-effect-free proposed change and complete recomputed
  projection;
- `ProjectionDiff`: before/after changes with no claim that the scenario will
  cause the predicted outcome.

These are conceptual contracts. This revision authorizes no new database
tables.

### 7.2 Count-once invariant

Every unit of work must be counted exactly once in each accounting role.

```text
total estimate range
= admissible completed linked effort
 + remaining effort range

remaining effort range
= future linked planning coverage
 + remaining unscheduled demand range
```

Subject to uncertainty ranges and explicit unknowns:

- a linked deadline and its task are one obligation, not two loads;
- a scheduled study block is coverage of demand when it is linked, not new
  demand added on top of the same deadline estimate;
- an unlinked planned block is a capacity commitment, not assumed obligation
  coverage;
- a calendar event reduces represented capacity once, even when mirrored by a
  LyraOS task;
- overlapping calendar events consume the union of occupied intervals, not
  the sum of duplicate minutes;
- future scheduled coverage does not count as completed work;
- completed work reduces remaining effort only through admissible linked
  evidence;
- remaining effort and unscheduled demand are floored at zero;
- future coverage beyond remaining effort is reported as possible overcoverage,
  not negative demand;
- an unknown relation remains unknown rather than being deduplicated by title
  similarity alone.

The permanent regression target is entity-level attribution, not merely a
matching aggregate total. Every displayed minute must be traceable to one
obligation, coverage block, or capacity commitment and one accounting role.

### 7.3 Demand envelope

For an obligation with sufficient authority:

```text
remaining_effort_range
= total_estimate_range
 - admissible_completed_effort_range

unscheduled_demand_range
= remaining_effort_range
 - confirmed_future_linked_coverage
```

If total estimate, completed effort, or linkage is unknown, the result must
carry that unknown explicitly. The implementation may not substitute zero.

### 7.4 Capacity envelope

Capacity is at least as uncertain as demand. It must not be drawn as a solid
fact while task estimates receive uncertainty treatment.

The initial capacity envelope may use only:

- user-declared availability;
- confirmed calendar commitments;
- accepted LyraOS task blocks;
- explicit quiet hours or planning exclusions;
- source freshness and coverage status.

It must not infer sleep, energy, focus, productive hours, or hidden personal
constraints. Historical execution may inform a future descriptive personal
range only after a separate admission and validity review.

The projection subtracts the union of non-overlapping hard commitments from
declared availability. When availability is absent or calendar coverage is
incomplete, capacity remains `UNKNOWN` or visibly partial.

### 7.5 Collision states

The map uses interval comparisons rather than a crisp invented threshold:

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

- A current user correction owns the active planning range.
- Clean personal evidence may calibrate a future range only when task linkage,
  sample admission, and units are compatible.
- Research priors remain fallback evidence and retain population and
  transportability limits.
- Deterministic task semantics may choose a prior family or widen uncertainty;
  they do not establish difficulty truth.
- Provider metadata establishes structure and due dates within its authority;
  it does not establish effort, learning, or completion.
- Survey priors remain provisional cold-start influence, visibly separable
  from personal evidence and never identity truth.
- A future AI candidate may propose components, estimate ranges, missing-scope
  questions, or disagreement. It cannot silently override, narrow, or mutate
  any estimate.
- AI unavailability must leave the deterministic map complete and usable.

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

`Scope expansion` is an operational uncertainty flag, not a personality label.
It may be supported by evidence such as:

- the user added components after the initial estimate;
- the provider changed deliverables or coverage;
- linked attempts repeatedly revealed additional explicit work;
- the user corrected the estimate upward;
- the title or description contains unresolved deliverables;
- a future AI parser proposes missing components that the user has not yet
  confirmed.

The map may widen a range or ask a clarification. It may not say the user is a
perfectionist, avoidant, undisciplined, or likely to expand scope without an
operational evidence basis and claim authority.

### 8.6 Unaccounted obligations

The map distinguishes missing representation from invented work. Supported
coverage gaps include:

- unresolved Brain Dump items;
- parser partial failures or excluded rows;
- stale or incomplete provider sync;
- deadlines without estimates;
- scheduled blocks without linked obligations;
- obligations without future coverage;
- user-declared missing workload;
- imported structure awaiting confirmation.

LyraOS may say `work may be missing from this map`. It may not invent a hidden
task and present it as observed truth.

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

capacity envelope       [====================]
obligation demand          [------????------]
uncovered range                    [####]
```

Visual encoding should communicate:

- horizontal position: relevant time and deadline window;
- width: feasible or pressure-onset window;
- thickness: remaining effort range, not emotional severity;
- solid/striped boundary: evidence certainty;
- dotted extension: unresolved possible scope;
- outline/icon: confirmed, imported, inferred, stale, or missing coverage;
- stacking: obligations competing for the same capacity;
- link: only confirmed obligation/coverage/dependency relations.

The exact encoding requires usability testing. Color is never the sole carrier
of urgency, uncertainty, trust, or selection. High pressure uses concentrated
contrast rather than flashing, pulsing alarm decoration.

On mobile, the same projection becomes stable day/window rows with a sticky
summary and explicit expand controls. It must not shrink a fourteen-day chart
until labels, targets, and ranges become unreadable.

## 11. Selection Inspector

Selecting an obligation opens an inspector answering:

1. **Why is this creating pressure?**
2. **What does LyraOS know?**
3. **What is uncertain or missing?**
4. **What remains uncovered if nothing changes?**
5. **What real actions are available?**

Example evidence:

```text
Due in four days.
Estimated remaining work: 4-7h.
Future linked coverage: 90m.
Estimate source: research prior plus your correction.
Calendar coverage: partial.
Uncovered work: approximately 2.5-5.5h.
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
4. shows before/after demand, capacity, uncovered work, and newly created
   collisions;
5. states which assumptions did not change;
6. performs no product mutation;
7. exposes one `Apply` command only when the proposal maps to canonical
   mutation authority.

A preview may not locally move one bar while leaving competing obligations
stale. `Pressure improved` is descriptive of the deterministic projection,
not a causal promise about user behavior.

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
Between Tuesday and Thursday, visible demand is 9-13h and represented capacity is 5-7h.
This estimate is still wide because the task scope is unconfirmed.
Correct the estimate or add a linked block to preview the difference.
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
- Direct API reads do not create render truth.
- Scenario generation is not mutation.
- Preview selection is not action success.
- Applied scheduling is not execution.
- Recovery selection is not recovery outcome.
- Every applied scenario links to the resulting canonical mutation IDs.
- Exposure contamination remains visible to downstream analysis.

## 17. Day-0 And Orientation Gates

### Day-0 gate

A new account can:

1. complete or skip onboarding without identity-style claims;
2. Brain Dump or import real workload;
3. see which items were accepted, rejected, reused, or remain unresolved;
4. open the map from the capture result and from Pulse;
5. identify demand, scheduled coverage, capacity coverage, and unknowns;
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

- planned academic/study tasks currently enter item estimates and can be added
  again as planned load;
- linked deadlines and tasks are not yet reconciled as one obligation;
- calendar and task occupancy are summed without a complete interval-union and
  mirror-dedup contract;
- capacity is represented more confidently than the evidence supports.

### Correct before calling actions complete

- coverage questions lack a canonical correction command;
- several recovery options are labels only;
- `split_into_blocks` does not yet prove genuine smaller chunks;
- draft placement sequences blocks from the next half-hour rather than
  recomputing feasible capacity;
- plan preview can remain available while blocking coverage is unresolved.

### Correct before calling Day-0 orientation complete

- the compact panel silently caps items and reasons;
- estimate provenance is compressed and direct range correction is missing;
- the provider-neutral copy can overstate the current academic/study scope;
- normal hosted recovery emission remains safety-gated;
- the current panel sits too low and too narrowly to serve as the complete
  time landscape.

## 19. Delivery Sequence

### Stage A: accounting truth

- add characterization fixtures for linked deadline/task, unlinked blocks,
  overlapping calendar events, partial coverage, missing estimates, and stale
  sources;
- establish entity-level count-once attribution;
- separate demand, linked coverage, unrelated busy time, and unknowns;
- expose capacity as a range or partial/unknown state;
- change no estimate prior while correcting accounting.

### Stage B: action truth

- remove or demote non-executable options;
- add canonical correction only where ownership and rollback are clear;
- make split semantics real or rename them;
- disclose hidden items and reasons;
- keep explicit preview and confirmation.

### Stage C: dedicated tab

- add the full-tab shell and Pulse entry point;
- ship Time, then Coverage, then Sources views over the same projection;
- add desktop inspector and accessible mobile drill-down;
- prove keyboard, focus, target size, zoom, texture, and non-color semantics;
- preserve the compact Pulse summary as a truthful subset.

### Stage D: scenario engine

- implement a pure full-horizon recomputation;
- support one proposal family per seam;
- prove before/after accounting and no-write preview;
- link `Apply` to existing canonical commands;
- browser-prove rollback and cleanup.

### Stage E: personal calibration

- admit clean linked execution only after unit, source, and sample gates;
- keep user corrections and personal evidence distinguishable;
- report calibration error and disagreement;
- do not call the range validated without baseline and uncertainty evidence.

### Stage F: future AI augmentation

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
