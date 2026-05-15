# 12 Intervention Exposure Risks

**Purpose:** Map system actions that can change future observations.

## Current Exposure/Intervention Surfaces

| Surface | User sees | Tracking state | Risk |
| --- | --- | --- | --- |
| micro-mirror on stop | short behavioral observation | `ReflectionViewLog` impression/view/dismiss | changes future self-interpretation |
| calibration nudge on stop | reference-class forecast | `ReflectionViewLog`, sometimes task outcome | reinforces/anchors planning |
| creation nudge | suggested duration/context | `CalibrationNudgeEvent`, `ReflectionViewLog` | directly changes planned duration |
| pause prediction banner | predicted near-term pause | `PausePredictionLog`, response reconciliation | induces pause or resistance |
| resume prediction banner | usual resume timing | `ResumePredictionLog` | induces resume or guilt |
| insights page | behavioral patterns | frontend read, unclear per-card exposure | changes future behavior and self-report |
| archetype display | dynamic or survey-based label | partial view/exposure comments | identity attachment |
| tutorial/onboarding | explains measurement concepts | some reflection logging | primes reporting behavior |
| JARVIS | operator interpretation | `JarvisInvocation` | can reshape operator behavior and theory |
| LLM deadline chip | candidate binding | task `llm_*` state, accept/reject | alters task-deadline semantics |

## Exposure State Gaps

Cortex v0 has `none | exposed | intervention | unknown`, but that is too coarse
for causal analysis. Missing states:

- seen
- acknowledged
- clicked
- dismissed
- ignored
- accepted
- adjusted behavior
- repeated exposure
- suppressed/avoided

## Untracked Or Partially Tracked

| Exposure | State |
| --- | --- |
| insight card scroll/view | likely untracked or partially tracked; needs verification |
| modal dwell before readiness/reflection | mostly not instrumented except planned telemetry docs |
| user reads archetype copy | partially tracked via logs/comments; verify runtime path |
| user sees landing page claims | untracked; public copy can shape expectations |
| JARVIS answer influence on operator | invocation logged, but acted-upon effect not linked |

## Research Consequence

Once a user sees "you usually underestimate development tasks," future
development-task planning is no longer naturalistic. It is exposed behavior.

Learning metrics must condition on exposure or freeze the pre-exposure window.

## Phase 1 Minimum

The exposure ledger must capture:

- exposure id
- user id
- task id or context id
- surface
- claim type
- confidence shown
- delivery mode
- shown time
- acknowledged/dismissed/acted state
- linked future event window

No adaptive inference should proceed before this is implemented.
