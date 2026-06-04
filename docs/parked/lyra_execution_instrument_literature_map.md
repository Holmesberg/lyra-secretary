---
authority: parked
may_authorize_code: false
runtime_owner: none
promotion_condition: >
  Use when Lyra needs external research positioning or instrument-validation
  framing. Does not authorize new metrics, claims, user prompts, passive
  tracking, or implementation steps.
---

# Authority-Aware Literature Map: Lyra As Execution-State Instrument

Status: parked research map. This document maps what Lyra already tracks or
documents to nearby literature families. It does not validate Lyra as a
psychological instrument and does not authorize implementation.

Lyra's current instrument shape:

```text
intention -> planned window -> active execution -> pause/interruption ->
resolution -> recalibration/exposure
```

Closest overall family:

```text
time-use diary
+ ecological momentary assessment / experience sampling
+ personal informatics
+ interruption/resumption instrumentation
+ planning-fallacy / implementation-intention tracking
+ future JITAI/MRT substrate
```

## Observable-To-Literature Map

| Lyra observable | Current authority | Closest literature family | Confidence | Likely keyword | Implementation relevance |
| --- | --- | --- | --- | --- | --- |
| task creation with planned start/end/duration | already implemented | time-use diary; planning fallacy; implementation intentions | high | time-use diary; prospective planning; implementation intention | Supports planning/execution trace; no new runtime authority. |
| accepted user intention before task creation | active doctrine + implemented surfaces | implementation intentions; intention-action gap | high | goal intention; implementation intention; intention-behavior gap | Confirms why user confirmation remains core. |
| planned vs executed active duration | already implemented | planning fallacy; task-duration estimation | high | planning fallacy; time prediction error; optimism bias | Supports estimate calibration only when provenance is clean. |
| execution time vs session span vs pause overhead | already implemented / active doctrine | time-use diary; interruption studies | high | active time; elapsed time; interruption duration | Supports separate execution/occupancy metrics; never merge into one truth. |
| pause events and pause duration | already implemented | interruption/resumption; time-use/activity logs | high | task interruption; pause duration; resumption lag | Supports recovery mechanics and pause analysis. |
| pause/re-entry latency | partially implemented / parked expansion | interruption/resumption lag; memory for goals | high | resumption lag; memory for goals; suspended goals | Supports recovery prompts and open-thread surfaces. |
| task switch / parent-child interruption chain | already implemented topology; parked hypothesis for interpretation | task switching; interrupted work; attention residue | medium | task switching; attention residue; interruption recovery | Supports open-thread recovery; not causal focus/motivation claims. |
| context-switching footprint | parked hypothesis | task switching; interruption science; work fragmentation | medium | task switching; interrupted work; fragmentation | Parked; internal term only; user copy should say open threads/parked work. |
| open threads / parked work | parked hypothesis / future surface | interrupted work; prospective memory; memory for goals | medium-high | open goals; suspended goals; resumption cues | Supports re-entry recovery surfaces if promoted. |
| reentry resolution outcome | future implementation idea | interruption recovery; prospective memory; behavior change outcome tracking | high | resolution outcome; proximal outcome; task resumption | Required before claiming whether switching mattered. |
| missed/skipped planned blocks | already implemented / active doctrine | intention-action gap; procrastination/delay; time-use noncompletion | medium-high | goal disengagement; implemental delay; initiation failure | Supports recovery options, not avoidance claims. |
| initiation delay | already implemented / active doctrine | procrastination; intention-action gap | medium | initiation delay; implemental delay; procrastination | Weak evidence; do not infer avoidance without controls. |
| deadline bindings / obligation links | already implemented | planning; temporal constraints; educational/work analytics | medium | deadline pressure; temporal landmarks; workload | Supports pressure map context; not execution truth. |
| pressure map / workload distribution | already implemented / active doctrine | workload visualization; planning support; personal informatics | medium | workload visualization; personal informatics reflection | Supports planning reflection; exact-hour precision must stay bounded. |
| self-report readiness | already implemented | EMA/ESM; metacognition; self-report reliability | medium | ecological momentary assessment; readiness; self-report reliability | Weak ordinal evidence only; not capacity/focus truth. |
| post-task reflection | already implemented | personal informatics; EMA; metacognition | medium | reflection; self-monitoring; metacognitive monitoring | Useful self-report, but user-facing mirror is an intervention. |
| signed pre/post discrepancy | active hypothesis | metacognitive discrepancy; confidence calibration; self-monitoring | medium | metacognitive monitoring; calibration; self-assessment | Supports H1-style hypothesis only after controls. |
| exposure render/ack logs | already implemented / active doctrine | intervention exposure; JITAI; MRT; measurement reactivity | high | exposure; proximal outcome; measurement reactivity | Required to separate baseline from post-surface behavior. |
| micro-mirrors / nudges / resume banners | already implemented surfaces | personal informatics; behavior change; JITAI | medium | just-in-time adaptive intervention; self-tracking feedback | Product surfaces; must log exposure and avoid overclaiming. |
| email reactivation clicks/opens | already implemented operational telemetry | digital intervention engagement; campaign analytics | high for click, low for open | click-through; email open tracking; engagement | Operational re-entry visibility; not behavioral/cognitive evidence. |
| provider imports / LMS/calendar events | partially implemented; active doctrine constraints | learning analytics; calendar/time-use context | medium | learning analytics; calendar data; digital trace validity | Structure/context only until confirmed; not completion or effort truth. |
| passive browser/activity traces | unsupported / speculative | digital phenotyping; passive sensing; contextual integrity | low-medium | digital phenotyping; passive sensing; contextual integrity | Parked; no runtime authority; confirmation-gated if ever promoted. |
| archetype/cluster priors | implemented/active but constrained | individual differences; shrinkage priors; personalization | low-medium | archetype; Bayesian shrinkage; personalization | Planning support only; avoid identity labels. |
| AI cold-start estimates | future implementation idea | reference-class forecasting; planning fallacy debiasing | medium | outside view; reference class forecasting; time estimation | Parked until estimate provenance is explicit. |
| adaptive interventions / randomized prompts | unsupported / speculative | JITAI; micro-randomized trials | medium as literature fit, low current authority | just-in-time adaptive intervention; micro-randomized trial | Future research substrate only; not current runtime authority. |

## Classification Summary

### Already Implemented

- Task creation and confirmed state transitions.
- Planned/executed duration traces.
- Explicit stopwatch sessions.
- Pause/resume/stop lifecycle.
- Some interruption topology through task switching/parent-child links.
- Pressure map and recovery surfaces.
- Exposure/event logs for several output surfaces.
- Email engagement telemetry for future reactivation emails.

### Active Doctrine

- User remains author of truth.
- Execution time, session span, and pause overhead stay separate.
- Provider/passive data is context until confirmed.
- Mirrors/nudges are interventions.
- Unknown stays unknown.
- No identity/focus/motivation/avoidance claims.

### Parked Hypotheses

- Context-switching footprint as recovery intelligence.
- Open threads as the user-facing recovery surface.
- Metacognitive discrepancy as modifier of recovery friction.
- Pressure-map usefulness as a planning/recovery aid rather than insight-only
  surface.

### Future Implementation Ideas

- Estimate provenance fields and cold-start AI ranges.
- Re-entry resolution outcomes.
- Provider-blind recurring obligation middleware.
- ICS/Sheets/Outlook/Teams/Meet adapters.
- Formal research design and instrument validation.

### Unsupported / Speculative

- Passive browser extension as execution evidence.
- Autonomous planning or proactive task mutation.
- Fragmentation/switching scores.
- Validated psychological claims from current trusted-user data.
- Lyra as a JITAI/MRT platform in current runtime.

## Literature Anchors

These sources informed the map and should be revisited before any external
research positioning:

- Personal informatics stage model:
  https://www.cs.cmu.edu/~jhm/Readings/2010-ianli-chi-stage-based-model.pdf
- Lived informatics:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC12435389/
- Personal informatics critical review:
  https://www.tandfonline.com/doi/abs/10.1080/07370024.2016.1276456
- Time-use diary methodology:
  https://bmcpublichealth.biomedcentral.com/articles/10.1186/s12889-019-6760-y
- Data quality decay in online time-use surveys:
  https://journals.sagepub.com/doi/10.1177/00811750221126499
- Task interruption and resumption lag:
  https://www.sciencedirect.com/science/article/abs/pii/S1071581903000235
- Interruptions as prospective-memory tasks:
  https://www.researchgate.net/publication/227643114_Interruptions_Create_Prospective_Memory_Tasks
- Systematic review of interruption interventions:
  https://www.sciencedirect.com/science/article/pii/S0003687021001538
- Attention residue:
  https://ideas.repec.org/a/eee/jobhdp/v109y2009i2p168-181.html
- Interrupted work and stress:
  https://www.ics.uci.edu/~gmark/chi08-mark.pdf
- Planning fallacy:
  https://homepages.se.edu/cvonbergen/files/2013/01/Exploring-the-Planning-Fallacy_Why-People-Underestimate-Their-Task-Completion-Times.pdf
- Implementation intentions:
  https://prospectivepsych.org/sites/default/files/pictures/Gollwitzer_Implementation-intentions-1999.pdf
- Goal-directed delay / procrastination via ESM:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC8356899/
- Digital phenotyping ethics:
  https://www.nature.com/articles/s41746-018-0075-8
- Micro-randomized trials for JITAIs:
  https://pubmed.ncbi.nlm.nih.gov/26651463/
- MRT design overview:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC8887814/

## Non-Authority Clause

This map can support framing, literature review, and future validation
planning. It cannot authorize:

- new runtime metrics;
- new user prompts;
- passive tracking;
- autonomous scheduling;
- stronger product claims;
- publication of psychological interpretation.
