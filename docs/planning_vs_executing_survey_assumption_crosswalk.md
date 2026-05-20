# Planning vs Executing Survey Assumption Crosswalk

**Status:** Evidence crosswalk, not validation.
**Created:** 2026-05-19.
**Source workbook:** `archive/Planning VS Executing.xlsx`.
**Source export:** `archive/data_exports/Planning VS Executing - Google Sheets.pdf`.
**Survey window:** 2026-04-09 20:18 to 2026-04-13 18:23.
**Responses:** 23.

This document cross-checks the assumptions in
`docs/product_research_assumption_register.md` against the Planning vs
Executing survey. It does not upgrade any assumption to validated. It records
which assumptions have survey support, mixed support, or no direct survey
coverage.

The survey is useful because it captures self-reported planning behavior before
the current asset-velocity and evidence-fusion doctrine existed. It is not a
behavioral trace dataset.

## 1. Survey Questions

The workbook contains one sheet, `Form Responses 1`, with these columns:

1. Timestamp.
2. How do you currently track how long tasks take you?
3. When you plan a task, how accurate is your estimate usually?
4. When you're wrong, which direction?
5. Before you start a task, do you notice how "ready" you feel?
6. Have you ever tried to improve your time estimates by tracking them?
7. When one task runs over and messes up your day, what usually happens?
8. If a tool told you "you always underestimate coding tasks by 40% in the
   afternoon" - would that be useful, or intrusive?
9. What do you currently use to manage your day?

## 2. Response Summary

### 2.1 Current Tracking Behavior

| Response | Count | Share |
| --- | ---: | ---: |
| I don't | 12 | 52% |
| Manually in a notebook or spreadsheet | 8 | 35% |
| Calendar / time-blocking app | 2 | 9% |
| Just looking at the clock before and after | 1 | 4% |

Interpretation:

- 13/23 either do not track or only glance at the clock.
- 8/23 use manual notebook/spreadsheet tracking.
- Only 2/23 report calendar/time-blocking apps.

This supports the assumption that heavy explicit instrumentation will not scale
cleanly for many students.

### 2.2 Estimate Accuracy

| Response | Count | Share |
| --- | ---: | ---: |
| Mostly accurate within 25% | 12 | 52% |
| I don't estimate, I just start | 6 | 26% |
| Usually wrong by 25-50% | 3 | 13% |
| Usually wrong by more than 50% | 2 | 9% |

Interpretation:

- 11/23 either do not estimate or report being wrong by at least 25%.
- 12/23 self-report being mostly accurate.
- This is mixed survey support for planning-execution divergence.
- The "mostly accurate" group still contains several underestimation reports,
  which supports the doctrine that self-report is evidence, not truth.

### 2.3 Error Direction

| Response | Count | Share |
| --- | ---: | ---: |
| I almost always underestimate | 10 | 43% |
| It depends heavily on task type | 6 | 26% |
| It's genuinely random | 4 | 17% |
| I almost always overestimate | 3 | 13% |

Interpretation:

- 16/23 report either underestimation or task-type dependence.
- Only 4/23 frame estimation error as genuinely random.
- This supports structured-error and domain-specific interpretation
  assumptions.

### 2.4 Readiness Awareness

| Response | Count | Share |
| --- | ---: | ---: |
| Yes, constantly | 10 | 43% |
| Sometimes, when I feel really off | 9 | 39% |
| Rarely | 3 | 13% |
| Never thought about it | 1 | 4% |

Interpretation:

- 19/23 notice readiness at least sometimes.
- This supports collecting readiness as a meaningful subjective channel.
- It does not prove readiness predicts execution.

### 2.5 Prior Tracking Attempts

| Response | Count | Share |
| --- | ---: | ---: |
| Yes, but I stopped | 8 | 35% |
| No, never crossed my mind | 8 | 35% |
| No, but I've thought about it | 5 | 22% |
| Yes, and it worked | 2 | 9% |

Interpretation:

- Only 2/23 say tracking worked.
- 8/23 tried and stopped.
- This strongly supports the cumulative-friction assumption and the need for
  low-friction or hybrid instrumentation.

### 2.6 Reaction To Personalized Estimation Feedback

The free-response question asked whether a tool saying "you always
underestimate coding tasks by 40% in the afternoon" would be useful or
intrusive.

Rough qualitative coding:

| Reaction | Count |
| --- | ---: |
| Positive/useful | 9 |
| Negative/intrusive/useless/overwhelming | 6 |
| Mixed/ambiguous | 4 |
| Blank | 4 |

Interpretation:

- Many users want calibrated feedback.
- A meaningful minority perceive it as useless, intrusive, strange, or
  potentially overwhelming.
- This supports low-authority copy, agency-preserving design, uncertainty
  language, and psychological safety gates.

### 2.7 Cascade / Runover Effects

Free responses show several recurring reactions when one task runs over:

- continue the task until it is finished,
- move the rest of the day to tomorrow,
- procrastinate or take the rest of the day off,
- sleep,
- feel frustrated or carry the pressure mentally,
- switch to the next task if priority demands it,
- use a hard stop and return later.

Interpretation:

- The survey supports cascade and recovery-path heterogeneity.
- It does not prove the statistical cascade hypothesis.
- It does support treating runover response as structured rather than purely
  random.

## 3. Assumption Crosswalk

| Assumption | Survey support | Evidence from survey | Notes |
| --- | --- | --- | --- |
| A1 - planned intention and execution diverge | Mixed support | 11/23 do not estimate or report 25%+ error; 12/23 self-report mostly accurate. | Survey supports the problem space but does not prove systematic behavioral divergence. |
| A2 - execution failure is structured | Supported | 16/23 report underestimation or task-type dependence; only 4/23 report randomness. | Strong survey support for structured interpretation. |
| A3 - longitudinal traces contain signal | Not directly tested | Survey is cross-sectional self-report. | Requires app traces over time. |
| A4 - humans can recalibrate | Weak/mixed support | 2/23 say tracking worked; 8/23 tried and stopped. | Supports possible recalibration but highlights friction risk. |
| A5 - execution is not a moral category | Indirectly supported | Several runover responses mention frustration, pressure, sleep, or giving up. | Supports non-judgmental framing but needs interviews. |
| M1 - execution can be instrumented | Mixed support | Users can describe estimation, readiness, and runover patterns; many do not track. | Instrumentation must be low-friction. |
| M2 - accepted intention matters | Indirect support | 6/23 do not estimate and just start. | Accepted intention is not always present; architecture must distinguish planned vs unplanned execution. |
| M3 - passive activity is weak evidence unless confirmed | Not directly tested | No passive activity questions. | Still doctrine-locked; survey does not validate or refute. |
| M4 - exposure contaminates behavior | Indirect support | Personalized feedback question generated positive, negative, and overwhelming reactions. | Suggests feedback may alter behavior or self-concept. |
| M5 - missingness can be signal but not truth | Indirect support | Non-tracking and stopped-tracking responses indicate missing data may reflect friction. | Missingness should not be treated as no execution. |
| M6 - preserve ability to discover wrongness | Indirect support | Mixed responses and self-report contradictions argue against hard certainty. | Supports ranges, corrections, and trust states. |
| M7 - self-report is evidence, not truth authority | Supported | Some users claim mostly accurate while also reporting underestimation. | Supports contradiction-aware interpretation. |
| M8 - system-suggested durations require provenance | Indirect support | Personalized feedback is useful to some and intrusive to others. | System estimates need low-authority provenance. |
| M9 - avoid surveillance hallucination | Indirect support | Negative/intrusive reactions show risk when the system makes strong claims about behavior. | Survey supports caution, not passive telemetry math. |
| P1 - users want execution clarity | Supported but not universal | 9 positive reactions to personalized estimation feedback. | Some users do want clarity. |
| P2 - transparency builds trust | Indirect support | Mixed reactions suggest exact/authoritative claims may be risky. | Needs copy testing. |
| P3 - agency-preserving adaptation | Supported | Several respondents prefer adjusting planning themselves; some reject or ignore tool claims. | Feedback should be optional and editable. |
| P4 - low-friction instrumentation required | Strongly supported | 13/23 do not track or only glance at clock; 8/23 tried tracking and stopped. | One of the strongest survey-backed product assumptions. |
| P6 - self-modeling must remain supportive | Supported as risk | One response says the knowledge could be overwhelming and create a fixed mindset. | Strong reason for low-authority, non-identity copy. |
| P7 - clarity must not become anxiety amplification | Supported as risk | Negative/intrusive/overwhelming feedback reactions. | Needs small-cohort qualitative testing. |
| P8 - instrumentation burden has cumulative threshold | Strongly supported | 8/23 tried tracking and stopped. | Supports passive/contextual assistance and sparse prompts. |
| P9 - probabilistic duration estimates must feel like estimates | Indirect support | Personalized estimate feedback is polarizing. | Exact claims like "always underestimate" are risky. |
| H1 - metacognitive discrepancy predicts execution failure | Not directly tested | Survey asks readiness awareness but not paired outcomes. | Requires app trace analysis. |
| H2 - cascades exist | Supported as qualitative precursor | Runover responses include downstream disruption, procrastination, sleep, postponement. | Survey motivates H2 but does not statistically validate it. |
| H3 - behavioral typologies exist | Weak precursor | Responses vary: hard stop, continue until done, postpone, sleep, carry pressure. | Suggests possible strategy profiles; needs clustering. |
| H4 - scope inflation matters | Weak precursor | Some users continue until finishing properly or use "while you're at it" style. | Suggestive only. |
| H5 - unplanned execution rate matters | Supported | 6/23 do not estimate and just start; many use no formal planning tool. | Strong conceptual support for measuring planning participation. |
| H6 - longitudinal traces matter | Not directly tested | Survey is one-time. | Requires repeated traces. |
| H7 - calibration should reduce dependence | Indirect support | Users want improvement but many reject heavy tracking or tool authority. | Supports calibration-and-release philosophy. |
| S7 - academic asset velocity | Not tested | Survey does not ask about lectures, slides, recordings, or resource counts. | New future-gated assumption remains unvalidated by this survey. |

## 4. Cross-Cutting Findings

### 4.1 The strongest survey-backed assumptions

- P4: low-friction instrumentation is required.
- P8: instrumentation burden has a cumulative threshold.
- A2: execution failure appears structured rather than purely random.
- M7: self-report is useful but contradictory.
- H5: unplanned execution rate matters.
- H2: cascades are plausible enough to test.

### 4.2 Assumptions with mixed survey support

- A1: divergence exists for many users, but half report mostly accurate
  estimates.
- A4: recalibration is possible, but friction kills tracking.
- P1/P2/P3: clarity and feedback are valuable for some users, but can feel
  intrusive or overwhelming for others.

### 4.3 Assumptions not covered by the survey

- A3 and H6: longitudinal trace value.
- H1: metacognitive discrepancy predicting execution failure.
- S7: academic asset velocity.
- M3/M9 passive telemetry math.
- BCI/neuroadaptive assumptions.
- Provider-adapter assumptions.
- Security/privacy governance assumptions beyond user discomfort with strong
  behavioral claims.

## 5. Register Impact

This survey should be treated as:

- **survey support** for low-friction instrumentation,
- **survey support** for structured estimation error,
- **survey support** for readiness as a subjective channel,
- **survey support** for caution around behavioral feedback,
- **qualitative precursor evidence** for cascades and typologies,
- and **no validation** for longitudinal, passive telemetry, asset-velocity, or
  neuroadaptive claims.

Recommended register language:

```text
partially-supported by early Planning vs Executing survey signal, not
cohort-validated.
```

Do not use this survey to claim:

- Lyra predicts execution failure,
- passive tracking is acceptable,
- cohort asset velocity works,
- users want surveillance-like telemetry,
- or feedback improves behavior longitudinally.

## 6. Follow-Up Survey Improvements

If rerun, add questions that directly test current assumptions:

- Would you accept opt-in passive academic activity signals if raw URLs and
  keystroke content never left your device?
- Would you prefer manual timers, passive suggestions, or both?
- Should Lyra ask you to confirm when signals disagree?
- Would duration ranges feel better than exact claims?
- Would cohort-based estimates for lecture/slides feel helpful or judgmental?
- Do you want Lyra to help you depend on it less over time?
- What kind of feedback feels supportive vs pressuring?
