# Documentation Alignment Audit - 2026-06-04

Status: audit report only.  
Authority: does not authorize runtime, schema, frontend, backend, migration, test, deployment, or provider work.  
Scope: documentation and repo-organization alignment.

## Method

This audit used six read-only review passes plus local repository searches and
a targeted literature scan. No runtime code was edited.

Agent perspectives:

- Authority and doctrine.
- Product loop.
- Provider and middleware boundaries.
- Research and measurement integrity.
- User trust and anti-surveillance.
- Complexity and repo organization.

The audit question was not "what more can Lyra build?" It was:

```text
Which documents currently make Lyra harder to reason about?
```

## Executive Summary

The strongest active invariant across the repo is clear:

```text
Lyra records explicit, user-confirmed execution state.
Provider data and passive/contextual evidence can structure attention, but they
do not become task, execution, completion, focus, motivation, or identity truth.
```

The current documentation mostly knows this. The main problem is not absence of
doctrine. The problem is authority sprawl: older, public, provider-specific,
pitch, parked, and ignored-vault documents still sound active enough that a
future agent could accidentally implement from them.

The highest-risk document classes are:

- historical Manifesto sections that still contain user-facing avoidance,
  escape, and archetype product implications;
- public AI-readable files that frame Lyra as "behavioral analytics" or an
  "AI-native productivity system";
- provider docs where Moodle/provider state can mutate canonical deadline
  completion;
- academic substrate docs that imply hidden measurement or passive observation;
- parked/root parked docs that contain "elevated" or active-sounding entries;
- stale roadmap files that still call themselves the forward-looking source of
  truth.

The docs should be simplified around one current product loop:

```text
brain dump -> bind to existing obligations -> pressure/occupancy map
-> confirmed task/recovery creation -> session tracking -> recovery/insights
```

Everything else should be classified as active contract, external orientation,
parked memory, or historical context.

## Current Active Invariants

| Invariant | Classification | Evidence | Notes |
|---|---|---|---|
| User remains author of truth. | active doctrine | `MANIFESTO.md`, `docs/AUTHORITY.md`, provider/exposure contracts | Strong and repeated. |
| Capability is not authority. | active doctrine | `docs/AUTHORITY.md`, `MANIFESTO.md` | Needs stronger enforcement in provider docs. |
| Unknown stays unknown. | active doctrine | Cortex and product-research contracts | Strong. |
| Mirrors, nudges, pressure maps, reminders, and insights are interventions. | active doctrine | `MANIFESTO.md`, exposure docs, tightened docs | Strong, but public docs understate this. |
| Every user-facing surface can contaminate later behavior. | active doctrine | `docs/tightened_docs/12_intervention_exposure_risks.md` | Needs per-card exposure coverage before adaptive claims. |
| Execution Time, Session Span, Pause Overhead, and Occupancy Time are distinct. | active doctrine / partially implemented | Cortex product-research contract, interruption metric work | UI wording still sometimes says "focus minutes." |
| Provider data is structure until confirmed. | active doctrine | Provider contract and core loop plan | Violated by Moodle completion wording. |
| No identity, focus, motivation, avoidance, worth, productivity, fragmentation, switching, or student-risk scores. | active doctrine | H8/context-switching docs and tightened semantic docs | Older H3/archetype/public docs still conflict. |
| PARKED docs are memory, not implementation authority. | active doctrine | `docs/parked/future_implementation_index.md`, `docs/AUTHORITY.md` | Root parked docs leak active intent. |
| Brain dump is capture/orientation, not silent canonical mutation. | already implemented / active doctrine | core loop plan, Pulse behavior | Public docs should say this more clearly. |
| Pressure map is diagnostic planning support, not execution truth. | already implemented / active doctrine | pressure-map contracts and wave plan | Still too academic in several docs. |
| Open threads/re-entry load should be recovery-first, not insight-first. | parked hypothesis / active copy boundary | H8 docs, parked open-thread plan | Keep parked unless promoted. |

## Current Implementation Authority

Use this order until the repo explicitly updates its authority index:

1. `MANIFESTO.md` latest current governance amendments, with historical sections
   treated as non-authorizing when superseded.
2. `docs/AUTHORITY.md` as the implementation-governance map.
3. `docs/current_transition_state.md` for active branch scope, but split its
   authorizing documents from context documents.
4. `docs/architecture_freeze_priority_hold_2026_05_20.md` and tightened freeze
   docs for freeze constraints.
5. Active contracts:
   - `docs/cortex_contract_v0.md`
   - `docs/cortex_product_research_contract_v0.md`
   - provider, exposure, output-surface, security, calibration, and pressure
     contracts.
6. Active doctrine/registers:
   - `docs/behavioral_instrumentation_doctrine.md`
   - `docs/product_research_assumption_register.md`
   - H8/context-switching docs.
7. Product-maintenance guidance:
   - `docs/core_product_loop_wave_plan.md`
   - only where consistent with items 1-6.
8. External/reviewer docs:
   - context only, unless explicitly listed by authority docs.
9. Historical/roadmap/design docs:
   - non-authorizing unless re-promoted.
10. `docs/parked/*`, `docs/parked_ideas.md`, `docs/parked_governance_specs.md`,
    `archive/*`, and the ignored `LyraOS/` vault:
    - no implementation authority.

## Main Contradictions And Tensions

### 1. Authority Chain Drift

`MANIFESTO.md` says it is the highest-priority governance document, while
`docs/AUTHORITY.md` is the current implementation-governance map. That can work,
but the Manifesto governance index does not clearly delegate live implementation
authority to `docs/AUTHORITY.md`.

Action:

- Update the Manifesto governance index or explicitly delegate the live
  implementation map to `docs/AUTHORITY.md`.
- Mark historical Manifesto sections as non-authorizing when later amendments
  supersede them.

### 2. Accidental Promotion Through `current_transition_state`

`docs/current_transition_state.md` includes explanatory/research docs in an
authority chain even when those docs say they are not canonical governance.

Action:

- Split into:
  - authorizing docs;
  - context docs;
  - historical references.

### 3. Public Product Docs Overstate AI/Behavioral Analytics

`frontend/public/lyraos.md` and `frontend/public/llms.txt` describe Lyra as
"AI-native productivity" and "behavioral analytics." This conflicts with
README positioning that Lyra is not an AI productivity wrapper.

Action:

- Rewrite public files around:
  - execution-state middleware;
  - explicit planning/timing history;
  - confirmation-gated structure;
  - recovery support.
- Avoid "behavioral model" unless the text also states evidence limits.

### 4. Provider Truth Violation In Moodle Docs

`docs/moodle_lms_integration.md` says Moodle submission or grade can transition
a deadline to completed. That violates the provider boundary.

Action:

- Rename provider completion evidence to `external_submission_trace` or
  `completion_candidate`.
- Canonical completion should require user confirmation or a separately
  authorized outcome policy.

### 5. Passive/Hidden Measurement Language

`docs/academic_execution_substrate.md` says Lyra can become the "hidden
measurement layer" and includes tab/activity examples. This conflicts with the
current no-surveillance constraint.

Action:

- Replace hidden/passive phrasing with visible, opt-in, user-controlled evidence.
- Move passive capture/browser extension plans under parked gates only.

### 6. Academic Primitive Leakage

Provider contracts use `academic_asset` as a core primitive. That makes the
global middleware layer look academic-only.

Action:

- Rename core primitive to `structured_asset` or `resource_asset`.
- Keep `domain=academic` as a subtype.

### 7. Historical Avoidance/Archetype Language Still Looks Shippable

Older H3 and archetype sections include "avoidance latency," "escape ratio,"
"Profile: Procrastinator," and "Research shows people like you" language.
Newer H8 doctrine forbids this as user-facing explanation.

Action:

- Add supersession banners to the older sections.
- Keep them as historical/falsification records, not product copy.

### 8. Roadmap Staleness

`docs/building_phases.md` still calls itself the forward-looking phase source
while later docs call it stale April planning.

Action:

- Add frontmatter:
  - `authority: historical`
  - `superseded_by: docs/current_transition_state.md`
  - or refresh it as a non-authorizing roadmap.

### 9. Root Parked Docs Leak Active Intent

`docs/parked_ideas.md` contains entries with "STATUS: ELEVATED to active
design" while the parked folder index says parked is not backlog.

Action:

- Make `docs/parked/future_implementation_index.md` the sole parked index.
- Move root parked docs into `docs/parked/` or mark them historical.
- Replace "elevated" entries with pointers to active docs.

### 10. Execution Metrics Still Use "Focus" In Places

The product-research contract distinguishes active execution from focus, but UI
and public docs still use "focus minutes" for executed duration.

Action:

- Prefer "active minutes" for timer-derived execution.
- Reserve "focus" for self-report only.

## Core-Loop Coverage Matrix

| Loop Step | Internal Coverage | Public/Product Coverage | Gap |
|---|---|---|---|
| Brain dump | Strong but split between old onboarding and current wave docs | Partial | Needs current Pulse quick-capture doc. |
| Bind to obligations | Strong in wave/provider docs | Weak | Public docs barely explain confirmation-gated binding. |
| Pressure/occupancy map | Strong but academic-heavy | Weak | Needs provider-neutral product doc. |
| Confirmed task/recovery creation | Strong in wave/authority docs | Weak | Public docs do not center "preview then confirm." |
| Session tracking | Strong | Strong, but timer-first | Risk: product reads as just timer/task manager. |
| Pause/resume/interruption | Strong in newer code/docs | Partial | Needs one current recovery lifecycle doc. |
| Resume banner/open threads | Partially implemented/parked | Weak | Re-entry should be recovery-first, not insight-first. |
| Insights | Strong doctrine and many parked ideas | Stronger than recovery | Risk: insight-only drop-off if recovery docs lag. |
| Export/delete/trust | Present | Present but scattered | Needs trust surface map. |

## Provider Primitive Alignment

Aligned:

- `provenance`
- `trust_state`
- `authority_level`
- `redaction_status`
- `external_obligation`
- `activity_event`
- `execution_event`
- `exposure`
- `idempotency_key`

Partially aligned:

- `provider_connection`
- `outcome_trace`
- `academic_asset`
- `provider_item_type`

Missing or not active enough:

- `scheduled_block`
- `recurring_commitment`
- `availability_constraint`
- `task_candidate`
- `completion_candidate`
- `provider_progress_candidate`
- `confirmation`
- `recurrence_instance_key`
- `series_id`
- `exception_of_series_id`
- `source_window`
- `last_seen_at`

Recommendation:

Create a provider terminology boundary table before any new import work:

| Term | Provider Meaning | Lyra Meaning | Truth Boundary |
|---|---|---|---|
| deadline | due constraint | due constraint, not work proof | provider can propose, user/system contract confirms |
| obligation | external commitment | imported/captured commitment | structure only |
| event | time-bounded occurrence | schedule context | not task execution |
| resource | file/page/asset | work object/context | not completion |
| status | provider-local status | evidence/candidate | not canonical by default |
| confirmation | user action or authorized outcome policy | truth promotion event | must be scoped |

## Research And Measurement Integrity

The newest governance layer is strong. The leakage comes from old pitch,
archetype, and methodology language.

High-risk claims to soften:

- "We can predict when you'll fail before you start."
- "validated psychometric instruments" when referring to Lyra's combined
  battery and product archetype mapping.
- "clinical-grade personality phenotyping."
- "Research shows people like you."
- "abandonment risk" without controlled evidence.
- "focus quality" when only explicit timer/self-report data exists.

Required evidence rules:

- Every analytics/report claim should state:
  - clean-data profile;
  - exclusions;
  - sign convention;
  - exposure state;
  - denominator;
  - unknown count.
- Every adaptive inference should wait for per-card exposure and acted-state
  linkage.
- Context switching/open threads should remain correlation and recovery support,
  not a causal claim about failure, avoidance, motivation, or focus.

## User Trust And Anti-Surveillance Findings

Rewrite or park language that suggests:

- hidden measurement;
- passive observation as default;
- focus/motivation/avoidance inference;
- institutional/admin monitoring;
- productivity or fragmentation scoring;
- Lyra as source of self-recognition.

Recommended user-facing terms:

- open threads;
- parked work;
- re-entry load;
- planning footprint;
- resume load;
- active minutes;
- session span;
- pause overhead.

Avoid:

- fragmentation score;
- switching score;
- productivity score;
- avoidance index;
- failure prediction;
- focus quality unless self-reported.

## Literature Mapping

This scan should support framing only. It does not validate Lyra as an
instrument.

| Lyra Observable | Closest Literature Family | Confidence | Likely Keyword | Implementation Relevance |
|---|---|---:|---|---|
| Brain dump/capture | personal informatics preparation/collection | high | personal informatics stage model | Supports capture -> integration -> reflection -> action framing. |
| Provider import/binding | personal informatics integration; learning/work analytics | medium | data integration, workload visualization | Supports provider data as context, not truth. |
| Pressure map/workload distribution | personal informatics reflection/action; workload dashboards | medium | workload visualization, personal informatics | Supports planning reflection; avoid exact predictive claims. |
| Planning estimate vs executed duration | planning fallacy/time prediction | high | planning fallacy, time prediction | Supports estimate calibration, not "Lyra knows." |
| Pause/re-entry latency | interruption/resumption lag; memory for goals | high | resumption lag, memory for goals | Supports "pick it back up" recovery prompts. |
| Task switches/open threads | task switching/interruption science/work fragmentation | medium | interrupted work, work fragmentation | Parked hypothesis; correlation only. |
| Missed/skipped planned blocks | intention-action gap; implementation intentions | medium-high | implementation intentions, goal disengagement | Supports recovery options, not avoidance claims. |
| Nudges/reminders | JITAI/MRT; digital intervention exposure | medium | just-in-time adaptive intervention, micro-randomized trial | Supports exposure accounting before adaptive claims. |
| Self-report readiness/reflection | metacognition/self-report reliability | medium | self-report, metacognition | Weak evidence only; label as perceived state. |
| Email/notification engagement | digital intervention adherence and re-entry | low-medium | re-engagement, notification fatigue | Supports product iteration, not psychological inference. |

Representative sources:

- Li, Dey, and Forlizzi's personal informatics stage model describes
  preparation, collection, integration, reflection, and action stages, with a
  balance of automation and user control
  (`https://www.cs.cmu.edu/~jhm/Readings/2010-ianli-chi-stage-based-model.pdf`).
- Altmann and Trafton's memory-for-goals work models suspended goal retrieval
  and interruption/resumption (`https://www.sciencedirect.com/science/article/pii/S0364021301000581`).
- Interruption-lag research treats resumption lag as a metric for returning to
  interrupted tasks (`https://interruptions.net/literature/Altmann-CogSci04.pdf`).
- Mark, Gudith, and Klocke's interrupted-work study connects interruptions
  with speed/stress tradeoffs, not simple productivity judgment
  (`https://ics.uci.edu/~gmark/chi08-mark.pdf`).
- Micro-randomized trial/JITAI literature is relevant for future notification
  optimization, but only after exposure and outcome definitions are mature
  (`https://pmc.ncbi.nlm.nih.gov/articles/PMC8887814/`).

## What Should Remain Parked

These should not move into active implementation through this audit:

- browser extension/passive capture;
- full recurring schedule/import system;
- Google Meet/Teams/Sheets/Excel parsing;
- archetype reveal or identity labels;
- context-switching causal model;
- fragmentation/switching score;
- adaptive notification optimization;
- AI cold-start estimates as calibration evidence;
- observer-sovereignty doctrine beyond the current lightweight boundary;
- formal research/instrument validation plans.

## Where Governance Overhead Is Excessive

The repo has too many active-sounding surfaces for the same ideas:

- multiple reading orders;
- multiple public product narratives;
- root parked files plus `docs/parked/`;
- ignored Obsidian vault with active-sounding docs;
- stale phase planning plus current wave plans;
- pitch/manifesto/professor/public docs repeating claims at different evidence
  levels.

Simplification target:

```text
One authority ladder.
One current product loop source.
One parked index.
One external product-facts source.
One provider primitive registry.
```

## Top 10 Documentation Actions

1. Update the Manifesto governance index or explicitly delegate live
   implementation authority to `docs/AUTHORITY.md`.
2. Split `docs/current_transition_state.md` into authorizing docs and context
   docs.
3. Add `docs/README.md` as the canonical docs map with active, external,
   parked, and historical lanes.
4. Mark `docs/building_phases.md` historical or refresh it as non-authorizing.
5. Rewrite public AI-readable docs around execution-state middleware, not
   behavioral analytics.
6. Fix provider truth wording in Moodle/import docs.
7. Generalize `academic_asset` to `structured_asset` or `resource_asset`.
8. Add supersession banners to H3 avoidance/escape/archetype sections.
9. Consolidate parked material under `docs/parked/` with one promotion template.
10. Replace timer-derived "focus minutes" language with "active minutes" where
    not explicitly self-reported.

## Recommended Browser Verification After Doc Cleanup

These are verification candidates only, not implementation authorization:

- Pulse quick capture still anchors to top/bottom intended capture surface.
- Brain dump preview still requires confirmation before canonical task/deadline
  mutation.
- Deadline/provider binding still shows source and confirmation state.
- Pressure map copy uses provider-neutral "pressure map" language.
- Timer pause/resume/stop labels distinguish active time, span, and pause.
- Resume banner uses recovery copy, not failure/focus/motivation copy.
- Insights do not surface avoidance, focus, motivation, or identity labels.
- Export/delete/account scoping remain easy to find.

## Final Diagnosis

Lyra's documentation does not need a bigger ontology. It needs a smaller
authority surface.

The deepest invariant is already present:

```text
Lyra may organize evidence around the user, but it must not replace the user as
the authority that decides what happened, what it meant, or what should happen
next.
```

