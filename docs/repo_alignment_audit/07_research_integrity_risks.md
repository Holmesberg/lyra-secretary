# 07 Research Integrity Risks

**Purpose:** Identify risks to falsifiability, identifiability, and data validity.

## Risk Register

| Risk | Mechanism | Severity | Mitigation state | Missing instrumentation |
| --- | --- | --- | --- | --- |
| self-reference loop | insights/nudges change the behavior they measure | critical | partial `ReflectionViewLog`, nudge/prediction logs | full exposure ledger |
| intervention contamination | calibration nudges affect planned durations | critical | `CalibrationNudgeEvent` logs some decisions | unified intervention profile |
| exposure contamination | user sees pattern, adapts future self-report/behavior | critical | reflection impressions partially logged | acknowledgement/engagement/acted-upon states |
| non-identifiability | same observable has multiple hidden causes | critical | Cortex topology marked hypothesis | stronger scope/interruption evidence |
| missing ground truth | no external truth for focus/flow/calibration | high | Cortex forbids latent truth | explicit validation studies |
| survivorship bias | retained users may be instrumentation-tolerant | high | funnel instrumentation exists | cohort stratification by exposure and dropout reason |
| onboarding distortion | first tasks reflect novelty/learning, not stable behavior | high | alpha funnel columns separated from H1 in docs | novelty-phase flags in clean profiles |
| operator contamination | operator's high agency/topology drives hypotheses | high | calibration contract R8, operator-only JARVIS | two trusted-user discrimination reports |
| semantic drift | readiness/reflection/pause reasons change meaning over time | high | open debt documented | scale anchoring and drift checks |
| category drift | user category labels may not match research priors | high | categories explicit | category-semantics validation |
| unstable priors | literature priors may not match individual/topology | medium/high | archetype blend and personal data | posterior variance/stationarity, not count-only |
| retroactive contamination | reconstructed sessions look clean but are narrative | high | Cortex excludes retroactive from learning | profile enforcement across all analytics |
| external-source contamination | imported deadlines constrain user planning | medium/high | Cortex planning profile excludes external deadline-bound tasks | enforce in all H1 queries |
| timer artifacts | forgotten timers, stale sessions, auto-close | medium/high | recovery jobs and flags | artifact flags in all learning profiles |
| LLM suggestion contamination | LLM changes task/deadline interpretation | medium | trust-not-rewrite fields | exposure ledger for chips |

## Most Dangerous Current Failure Mode

The system can become unable to distinguish:

- user behavior
- behavior after Lyra's predictions
- behavior after identity-like labels
- behavior reconstructed after the fact

This is identifiability collapse. Cortex v0 prevents some metric drift but does
not solve exposure contamination.

## Data Validity Strengths

- `voided_at` discipline exists and is repeatedly documented.
- `PauseEvent.self_reported_retroactively` separates retroactive pause
  confirmations.
- `StopwatchSession.data_quality_flag` isolates known contaminated pause
  metadata.
- `TaskDeadlineOutcome` snapshots deadline and execution timestamps at compute
  time.
- JARVIS tool prompt includes covered/not-covered anti-hallucination rules.
- Cortex clean-data profiles now centralize measured-execution exclusions.

## Data Validity Weaknesses

- Many analytics paths predate Cortex and may not use Cortex profiles.
- User-facing insights still use legacy `duration_delta_minutes`.
- Exposure state is not detailed enough for causal separation.
- `personal_weight` is count-based, not variance/stationarity based.
- Pause predictor confidence uses absolute minute dispersion.
- Scope bullet growth is an ambiguous proxy.

## Falsifiability Preservation Rules

1. Every promoted hypothesis must name a falsifier.
2. Every user-facing inference must log exposure.
3. Every learning query must declare a clean-data profile.
4. Every latent construct must remain a hypothesis until independently
   validated.
5. Cohort-level claims must separate operator, trusted users, alpha users, and
   imported/external-source contexts.
