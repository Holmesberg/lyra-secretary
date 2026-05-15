# 11 Data Lineage Map

**Purpose:** Trace raw event -> metric -> inference -> exposure -> feedback.

## Core Task Execution Lineage

1. User creates task in frontend or API.
2. `TaskManager.create_task()` writes planned timestamps, duration, category,
   deadline binding, scope bullet count, session index, and optional nudge event.
3. Stopwatch starts via `StopwatchManager.start()`.
4. Task transitions `PLANNED -> EXECUTING`.
5. `StopwatchSession` row opens; Redis stores active state.
6. Pauses create `PauseEvent` rows and update session paused state.
7. Resume closes pause event and accumulates paused time.
8. Stop computes active execution duration and calls `TaskManager.complete_task()`.
9. Task transitions `EXECUTING -> EXECUTED`.
10. Micro-mirror and calibration nudge can be generated.
11. Reflection exposure can be logged in `ReflectionViewLog`.
12. Future behavior can be changed by what the user saw.

## Metric Lineage

| Raw source | Derived metric | Inference consumer | Exposure consumer |
| --- | --- | --- | --- |
| planned/executed duration | execution multiplier, deltas | bias factor, insights, archetype proximity, Cortex | new-task nudges, insights |
| readiness/reflection | discrepancy/signed shift | disagreement classifier, insight readiness signal | task row, insights |
| pause events | pause counts, pause timing, recovery latency | pause/resume predictor, JARVIS signature | prediction banners |
| deadline binding/outcome | met/missed/delay | deadline-shape analytics | deadline UI |
| reflection impressions | dwell/outcome | VT-21, JARVIS signature | history/insights |
| calibration nudge event | accepted/dismissed/outcome | nudge effectiveness | future planning copy |

## Where Uncertainty Is Lost

1. `deadline_match_confidence` can be read as probability, but it is a score.
2. `discrepancy_score` loses direction unless `signed_discrepancy` is used.
3. `duration_delta_minutes` sign is easy to invert.
4. `scope_bullet_count` becomes "scope creep" in inference despite ambiguous
   proxy semantics.
5. `post_task_reflection` can become "focus" in UI language.
6. User exposure is not fully attached to later task outcomes.

## Retroactive Contamination Path

Retroactive task creation writes execution-like fields after the fact. These
rows are useful descriptive history but invalid for learning metrics unless a
profile explicitly allows them.

Cortex excludes `initiation_status='retroactive'` from `measured_execution`.

## External Import Contamination Path

Moodle and Google Calendar introduce externally constrained events/deadlines.
These are product-useful but not pure user planning estimates.

Cortex `planning_calibration` excludes externally imported deadline-bound tasks.

## JARVIS Lineage

1. JARVIS read tools query scoped data.
2. Tool results are summarized and written to `JarvisInvocation`.
3. LLM synthesizes operator-facing interpretation.
4. Hypothesis proposal tool can create structured speculative proposals.
5. Human operator may later promote patterns.

**Risk:** if promotion discipline fails, an LLM interpretation becomes doctrine.

## Required Future Lineage Addition

Phase 1 exposure ledger must connect:

`insight/nudge/prediction shown -> user acknowledged/ignored/acted -> future task/outcome`.

Without that link, adaptive inference cannot distinguish natural behavior from
Lyra-shaped behavior.
