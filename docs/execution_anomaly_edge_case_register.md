---
authority: active-contract
may_authorize_code: false
runtime_owner: none
supersedes:
superseded_by:
---

# Execution Anomaly And Edge-Case Register

**Status:** Active anomaly register for planning, LyraSim, and reviewer
readiness.
**Created:** 2026-05-23.

This document tracks execution, provider, calibration, and presentation-relevant
edge cases that must stay visible as Lyra moves toward Baseet-oriented pilot
work. It does not authorize product features, runtime mutations, provider
integration, AI synthesis, or adaptive scheduling by itself.

The purpose is to prevent edge cases from being lost in presentation notes,
operator memory, or one-off dogfood findings.

## Core Rule

```text
An anomaly is not a product truth.
```

Anomalies may justify:

- a documented scenario;
- a LyraSim case;
- a reduced claim;
- a scorer/test;
- a user-confirmed recovery prompt;
- or a parked observation.

They do not automatically justify:

- new inference authority;
- clean calibration admission;
- automatic task mutation;
- adaptive scheduling;
- provider-derived execution truth;
- or identity/cognition labels.

## Product Boundary

Lyra should treat anomaly handling as recovery support, not hidden judgment.

Winning behavior:

```text
ambiguous or anomalous trace
-> name the uncertainty
-> offer a low-authority next action if useful
-> preserve provenance
-> avoid contaminating clean baselines
```

Failure modes:

- overclaiming from noisy traces;
- becoming silent under ambiguity;
- prompting on every tiny ambiguity;
- allowing one outlier to dominate future estimates;
- admitting repaired/provider-only rows as clean execution;
- confusing academic structure with academic work.

## Current Watchlist

### Extreme Duration Outliers

Examples:

- a task takes far above its baseline;
- a task finishes far below baseline;
- one planning task or stale session inflates an average beyond useful range;
- AFK/tab-hidden dwell time contaminates engagement metrics.

Rules:

- outliers are candidates for robust handling, not immediate new truths;
- averages should not silently drift from one extreme case;
- report medians/ranges or mark outlier-sensitive summaries when possible;
- repaired, stale, or AFK-contaminated rows must not enter clean calibration
  without explicit eligibility.

Candidate LyraSim / test pressure:

- a single extreme overrun must not rewrite a user's category estimate alone;
- a single extreme underrun must not produce overconfidence;
- outlier-sensitive copy should be bounded and reversible.

LyraSim status:

- promoted to `execution_outlier_single_trace_does_not_generalize`;
- validates the real `analytics.insights` seam with a corrected execution
  outlier beside clean baseline sessions;
- the repaired outlier must not enter `planning_calibration` or produce stable
  user-pattern copy.

### Stale Or Abandoned Sessions

Examples:

- user starts a session and walks away;
- local timer runs overnight;
- stale session recovery closes a session;
- user finishes elsewhere while a desktop session remains open.

Rules:

- stale recovery evidence is repaired evidence;
- repaired evidence should support recovery prompts, not clean execution truth;
- task state changes should be user-confirmed unless the existing stopwatch
  recovery path explicitly owns the transition;
- stale sessions should preserve provenance and avoid clean baseline pollution.

Candidate safe actions:

- adjust session duration;
- mark partial;
- split remaining work;
- discard or keep open;
- mark open and unconfirmed.

### Provider Progress Candidates

Examples:

- Baseet-like video reaches high progress while muted/backgrounded/idle;
- provider progress moves backward from submitted/complete to draft/open;
- mobile upload occurs while a desktop timer is stale;
- resource open or slide count looks like progress but may be unattended.

Rules:

- provider progress must be represented as `provider_progress_candidate`;
- provider progress must not become `execution_progress`;
- provider progress may support a recovery or confirmation prompt;
- provider progress must not auto-transition a task to executed;
- provider progress must not enter clean `measured_execution` or
  `planning_calibration`.

Candidate safe actions:

- confirm done, partial, or discard;
- confirm coverage;
- adjust session duration;
- mark open and unconfirmed.

### Duplicate, Stale, Or Changed Provider Deadlines

Examples:

- duplicate Baseet deadlines;
- stale due dates;
- changed assignment titles;
- vague provider rows such as "Assignment 1";
- section or professor mismatch.

Rules:

- provider rows are `external_obligation` or weak context until normalized;
- duplicate/stale provider rows must not double-inflate pressure unchecked;
- provider-specific IDs, URLs, or raw private data must remain redacted from
  user-facing summaries where required;
- pressure should use ranges and assumptions, not fake precision.

Candidate safe actions:

- ask for coverage confirmation;
- show uncertainty/trust state;
- keep provider row descriptive until confirmed.

### Task Supersession And Deadline Binding

Examples:

- a planning task exists only to organize the week;
- a task supersedes or binds to a deadline incorrectly;
- a deadline-specific study task is confused with the deadline itself;
- brain dump creates duplicate work after provider import.

Rules:

- supersession should prevent duplicate load when a task genuinely replaces or
  binds to a deadline;
- planning tasks should not become workload evidence merely because they mention
  deadlines;
- brain dump remains useful as fallback input, but Baseet/module flows should
  reduce redundant manual entry when provider structure is available;
- ambiguous binding should ask or remain unbound rather than silently merging.

Candidate safe actions:

- confirm whether task covers the deadline;
- mark a task as planning-only;
- bind or unbind explicitly;
- keep both items visible with uncertainty if unresolved.

### Calibration And Baseline Drift

Examples:

- one abnormal session shifts category averages;
- low-readiness sessions finish closer to plan than high-readiness sessions;
- study and work behave like different execution systems;
- time-of-day effects appear in dogfood data but remain underpowered.

Rules:

- baseline changes should require repeated eligible evidence;
- anomalous sessions should remain visible without becoming identity labels;
- readiness, category, and time-window signals are hypotheses until validated;
- confirmed patterns may improve estimates, but should not become stable
  personality claims.

Candidate safe actions:

- show bounded estimate ranges;
- ask for confirmation after surprising outcomes;
- tag findings as hypothesis or emerging pattern;
- require minimum sample thresholds before stronger copy.

### Safe-Action Spam

Examples:

- every tiny ambiguity produces a recovery prompt;
- already-resolved ambiguity prompts again;
- irrelevant low-severity ambiguity interrupts the user.

Rules:

- the opposite of paralysis is spam;
- safe-action availability must be balanced by safe-action spam checks;
- prompts should be reserved for ambiguity that is useful, action-relevant, or
  likely to affect recovery/calibration.

Candidate LyraSim pressure:

- low-severity ambiguity with no useful action should not raise a prompt;
- repeated prompts should cool down when ignored or resolved.

## Presentation Boundary

These edge cases should not dominate the main university reviewer pitch.

Main deck:

- show the value;
- show first value moment;
- show pressure map;
- show recovery;
- show aggregate pilot learning.

Backup/Q&A:

- explain anomalies;
- explain LyraSim;
- explain clean-data boundaries;
- explain why provider progress is a candidate, not execution truth;
- explain how dogfooding and user feedback surface edge cases before scale.

## Promotion Rule

An edge case should move from this register into implementation only when it
produces at least one of:

- failing test;
- LyraSim scenario;
- documented real-user/provider failure;
- reduced claim;
- concrete boundary update;
- or operational containment requirement.

Otherwise:

```text
document -> monitor -> rerun after real pressure
```

## Related Sources

- `docs/lyrasim_pressure_ambiguity_roadmap.md`
- `docs/lyrasim_stress_harness.md`
- `docs/stale_session_recovery_policy.md`
- `docs/provider_adapter_contract.md`
- `docs/academic_pressure_map_contract.md`
- `docs/brain_dump_onboarding_design.md`
- `docs/dogfood_findings_living.md`
- `docs/operator_findings_log.md`
- `docs/presentations/lyraos_university_reviewer_deck_strategy_notes.md`
