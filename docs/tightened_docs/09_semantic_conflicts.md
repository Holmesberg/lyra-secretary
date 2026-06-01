# 09 Semantic Conflicts

**Purpose:** Document conflicts without silently resolving them.

## Conflict Register

| Conflict | Locations | Nature | Severity | Recommendation |
| --- | --- | --- | --- | --- |
| `duration_delta_minutes` vs `active_delta_minutes` | `Task.duration_delta_minutes`, Cortex contract | opposite sign conventions | critical | keep legacy, use explicit conversion, future deprecation plan |
| `bias_factor` vs `execution_multiplier` | `bias_factor_service.py`, Cortex contract | same ratio, different semantic framing | high | Cortex name canonical; alias legacy |
| `discrepancy` duration vs self-report gap | models/docs/prose | one term means multiple concepts | high | ban bare `discrepancy` in new metrics |
| `confidence` as sample tier vs probability | analytics, predictors, LLM ranking | same word, different math | high | require confidence semantics field |
| `readiness` as input vs state | DB/UI/docs | self-report overloaded into capacity | high | use self-assessed wording |
| `reflection` as input vs focus/quality | DB/UI/docs | self-report overloaded into cognitive state | high | use self-reported reflection/focus only with caveat |
| `flow` as valence vs latent state | inference/docs/UI possible | deterministic class vs psychological construct | high | phrase as hypothesis |
| `scope_creep` vs `expanding` topology | inference_engine vs Cortex | related but not identical | medium/high | centralize topology vocabulary later |
| `cold_start/tentative/confirmed` vs `low/medium/high` | calibration contract vs analytics/frontend | competing confidence taxonomies | medium/high | freeze old terms; migrate by surface |
| external deadlines in planning calibration | deadline/integration docs vs older analytics | imported constraints contaminate native planning | high | use Cortex `planning_calibration` profile |
| archetype posterior vs survey archetype | archetype_service/proximity/frontend | static assignment and dynamic proximity coexist | medium/high | preserve distinction in UI/docs |
| LLM candidate confidence vs heuristic confidence | `llm_parser.py`, `deadline_heuristic.py` | different score origins | medium | do not compare as probability |
| overlap vs multitasking vs interruption | conflict detector, stopwatch switch, calendar UI, pressure map | one word currently covers schedule collision, active task switch, and visible load compression | high | use the terminology boundary below |

## Do Not Auto-Resolve

The following require design decisions, not mechanical rename:

- replacing `duration_delta_minutes` in public APIs
- renaming `bias_factor` in existing frontend/product copy
- changing confidence taxonomy in user-facing insights
- reclassifying `flow/friction` as topology instead of valence
- removing archetype labels

## Canonicalization Direction

Use the Cortex vocabulary for new measurement work:

- `execution_multiplier`
- `log_execution_multiplier`
- `active_delta_minutes`
- `self_assessed_readiness`
- `self_reported_reflection`
- `execution_topology`

Keep legacy aliases documented until all consumers migrate.

## Overlap Terminology Boundary

Do not use "multitasking" as the generic label for every overlapping or
parallel-looking event. These are different product states:

| Term | Meaning | Canonical owner | User-facing implication |
| --- | --- | --- | --- |
| `planned_overlap` | Two planned windows occupy the same clock time. | conflict detector / calendar | Usually a soft planning conflict; user may override or edit. |
| `active_overlap` | A new start collides with an already executing timer. | stopwatch / task create | Requires explicit handling because only one task can be actively executing. |
| `interruption` | A user starts a second task while another task is paused or suspended. | stopwatch `parent_task_id` / `interruption_type` | Preserve the parent-child link and offer resume/switch affordances. |
| `task_switch` | The user explicitly swaps the active timer from one open session to another. | stopwatch switch endpoint | This is continuity management, not a new task or a moralized interruption. |
| `parallel_scheduled_load` | Academic/calendar obligations sit near each other in the week/day. | pressure map | Explain compression; do not infer simultaneous execution. |
| `concurrent_visible_activity` | Future passive signals suggest more than one activity may have happened near the same time. | future passive evidence layer | Confirmation-gated weak evidence only; never clean execution truth by itself. |

Copy rule:

```text
Say "overlaps" for schedule windows.
Say "interruption" for parent-child execution chains.
Say "switch" for active timer handoff.
Say "compressed" for pressure-map load.
Avoid "multitasking" unless the user explicitly frames the behavior that way.
```

Why this matters: planned overlap is an editable calendar shape; active overlap
is a single-mutation-authority constraint; interruption is a recovery topology;
pressure compression is planning intelligence. Collapsing them into one word
makes the UI sound simpler while making the data model harder to trust.
