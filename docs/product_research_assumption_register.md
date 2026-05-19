# Product Research Assumption Register

**Status:** Product-research governance register.
**Created:** 2026-05-19.
**Purpose:** Name the assumptions behind LyraOS, translate them into
operational hypotheses, and define how each can be validated, falsified, or
demoted before stronger product, research, or investor claims are made.
**Audience:** Product, engineering, professor/research review, and investor
diligence.
**Governance:** Subordinate to `MANIFESTO.md`, especially "Manifesto
Governance Rule", "Substrate Kill Criterion", "Friction-Tested Instrument
Methodology", "Academic Execution Substrate Governance", and
"Trusted-Alpha Security Governance".

This document does not authorize new product claims, autonomous adaptation,
BCI claims, institutional deployment claims, or broader cohort scaling. It is a
truth-maintenance artifact.

The contract:

```text
assumption
  -> operational hypothesis
  -> observable variables
  -> validation path
  -> falsification signal
```

No assumption becomes a product claim until its validation path survives the
relevant data-quality, exposure, cohort, and security gates.

---

## 1. Why This Exists

LyraOS is built on many assumptions. The healthy move is not to hide them. The
healthy move is to make them explicit, testable, killable, and revisable.

For research reviewers, this register separates hypothesis from evidence.

For investor diligence, this register separates genuine moat candidates from
unvalidated risk. The moat is not "AI planning." The moat, if it survives
validation, is a longitudinal, exposure-aware execution instrument whose
assumptions are observable and falsifiable.

## 2. Current Confidence Legend

| Status | Meaning |
| --- | --- |
| `doctrine-locked` | Required boundary even before empirical validation. |
| `partially-supported` | Supported by operator data, alpha behavior, survey signal, or implemented tests, but not yet cohort-validated. |
| `speculative` | Plausible and architecturally important, but not validated. |
| `future-gated` | Not a current product claim; requires earlier gates to pass. |
| `killable` | Explicitly allowed to fail without killing the whole product. |

## 3. Human Execution Assumptions

| ID | Assumption | Operational hypothesis | Observable variables | Validation path | Falsification signal | Status |
| --- | --- | --- | --- | --- | --- | --- |
| A1 | Planned intention and real execution systematically diverge. | Planned-vs-actual execution deltas show non-zero, non-random structure across users and contexts. | `planned_active_minutes`, `executed_active_minutes`, `active_delta_minutes`, completion state, initiation delay. | Estimate per-user and cohort-level delta distributions; test repeatability by category, time window, workload density, and exposure state. | Deltas are indistinguishable from random noise after opportunity and exposure controls. | partially-supported / killable |
| A2 | Execution failure is structured, not random. | Skips, drift, overload, interruption, and recovery form stable patterns rather than independent accidents. | skip sequences, pause topology, recovery latency, deadline compression, time-of-day drift. | Test autocorrelation, cluster stability, within-user recurrence, and cross-user replication. | Failure patterns do not replicate within users or across comparable contexts. | partially-supported |
| A3 | Longitudinal traces contain meaningful behavioral signal. | Repeated execution traces reveal user-specific dynamics beyond session-level variance. | drift signatures, pause ratios, unplanned execution rate, recovery latency, estimation error, context windows. | Compare intra-user stability against inter-user variance over fixed windows; test whether personal history improves prediction over aggregate baselines. | Personal-history models fail to outperform simple cohort or time-of-day baselines. | partially-supported / killable |
| A4 | Humans can recalibrate. | Users can improve estimate accuracy, recovery behavior, or planning participation after bounded feedback. | estimate drift trend, execution multiplier trend, recovery latency trend, accepted corrections, plan edits. | Compare pre/post windows while conditioning on exposure history; run bounded neutral-control comparisons before adaptive claims. | Drift and recovery do not improve under transparent feedback, or improvement disappears after exposure controls. | speculative |
| A5 | Human execution is not a moral category. | Framing drift as probabilistic execution dynamics preserves correction and trust better than identity or blame framing. | correction acceptance, retention, feedback sentiment, support requests, abandonment after insight exposure. | Compare low-authority copy against identity/blame copy only in tightly governed review; prefer qualitative interviews before experiments. | Users interpret Lyra as judgmental, punitive, or identity-labeling despite low-authority copy. | doctrine-locked |

## 4. Measurement And Instrument Assumptions

| ID | Assumption | Operational hypothesis | Observable variables | Validation path | Falsification signal | Status |
| --- | --- | --- | --- | --- | --- | --- |
| M1 | Execution can be meaningfully instrumented through tasks, timers, pauses, readiness, outcomes, and corrections. | The instrumentation captures enough structure to explain or predict drift better than self-report alone. | task state, timer sessions, pause events, readiness, reflection, scope fields, execution corrections. | Compare instrumented traces against user interviews, manual audits, and prediction lift from each signal family. | Instrumented variables fail to explain drift or users consistently reject the trace as inaccurate. | partially-supported |
| M2 | Accepted intention matters. | Planning calibration quality is materially stronger when traces are linked to accepted or confirmed intention. | accepted plan/block, task source, passive activity class, execution outcome, calibration eligibility. | Compare accepted-plan traces against passive-only traces for calibration accuracy and predictive lift. | Passive telemetry performs equally well without intention and does not increase false inference. | doctrine-locked / testable |
| M3 | Passive activity is weak evidence unless intention is accepted or confirmed. | Passive academic/workplace activity helps reconstruct engagement but cannot safely enter `planning_calibration` alone. | resource open, active time, scroll/video activity, idle gaps, user confirmation, imported obligations. | Keep passive rows excluded from calibration; test whether confirmation changes predictive usefulness. | Passive-only rows outperform accepted-intention rows without increasing overclaim or user correction burden. | doctrine-locked |
| M4 | Exposure contaminates future behavior. | User-facing nudges, predictions, pressure maps, reminders, and reflections measurably alter later behavior. | exposure ledger state, surface id, truth class, signal targets, downstream windows, later task deltas. | Compare clean vs exposed windows; estimate exposure effects by surface class and horizon policy. | Exposed and clean windows remain indistinguishable across enough cohort data and intervention types. | doctrine-locked / partially-supported |
| M5 | Missingness can be signal, but it is not truth. | Missing starts, stops, reflections, or responses may indicate friction, but cannot be treated as completion or intent. | missing timer transitions, repair prompts, skipped fields, non-response, abandoned sessions. | Analyze missingness patterns separately from clean execution; prompt repair only under confidence/cooldown rules. | Missingness carries no useful explanatory value after context controls. | doctrine-locked / killable |
| M6 | The system must preserve the ability to discover it was wrong. | Ranges, trust states, editable assumptions, kill criteria, and versioned contracts reduce false certainty. | user corrections, trust-state displays, confidence tiers, profile eligibility, metric versions. | Track correction rates, trust failures, and claims demoted after new evidence. | Users or reviewers cannot tell what Lyra knows, guesses, or cannot infer. | doctrine-locked |

## 5. Product And UX Assumptions

| ID | Assumption | Operational hypothesis | Observable variables | Validation path | Falsification signal | Status |
| --- | --- | --- | --- | --- | --- | --- |
| P1 | Users want execution clarity more than abstract optimization. | Workload topology, drift, and recovery mirrors create immediate value before strong personalization exists. | pressure-map engagement, Pulse return rate, qualitative "this explains my week" feedback, plan acceptance. | Small-cohort interviews plus product usage; separate clarity value from adaptive recommendation value. | Users do not experience workload visualization as useful or understandable. | partially-supported |
| P2 | Transparency builds trust. | Low-authority copy, ranges, visible assumptions, and editable estimates reduce trust collapse. | correction acceptance, trust-state comprehension, feedback sentiment, churn after insight exposure. | Compare reactions to exact/authoritative vs ranged/uncertain copy in review or small cohort. | Users prefer opaque certainty or find transparent uncertainty confusing enough to reduce use. | partially-supported |
| P3 | Users prefer adaptive systems that preserve agency. | Suggestions framed as choices outperform commands or identity labels. | accept/reject rates, undo/reschedule behavior, feedback language, retention after interventions. | Track intervention response by authority level; run qualitative interviews after repeated exposure. | Users consistently prefer authoritative automation and do not report agency loss. | partially-supported |
| P4 | Low-friction instrumentation is required. | Reducing manual tracking burden increases trace continuity and retention. | session continuity, timer usage, passive candidate confirmation, provider-assisted onboarding, retention. | Compare manual-heavy flows against provider-assisted or embedded flows. | Lower friction does not improve trace density or retention. | partially-supported |
| P5 | Communication is exposure when it shapes behavior. | Transactional account messages are safe without exposure rows, but behavioral email/push nudges require exposure governance. | email category, copy class, exposure registration, later behavior windows. | Keep activation email transactional; require a separate notification/exposure contract for behavioral messaging. | Account messages start affecting behavior or include adaptive claims without exposure coverage. | doctrine-locked |

## 6. Scientific And Behavioral Hypotheses

| ID | Assumption | Operational hypothesis | Observable variables | Validation path | Falsification signal | Status |
| --- | --- | --- | --- | --- | --- | --- |
| H1 | Metacognitive discrepancy predicts execution failure. | Signed pre/post discrepancy correlates with active-duration delta or execution failure after validity-threat controls. | readiness, reflection, signed discrepancy, duration delta, completion state, exposure state. | Pre-registered Spearman/correlation and distinguishing analyses from the manifesto. | Correlation remains below threshold with CI including zero and no learning trend. | killable |
| H2 | Cascades exist. | Failure or abandonment of one planned block increases downstream failure probability in the same temporal window. | skip sequence, session index, category, time-of-day, workload density, sleep if available. | Compare `P(skip N+1 | skip N)` against baseline skip probability with structural controls. | Downstream failure probability does not meaningfully increase after controls. | partially-supported / killable |
| H3 | Behavioral typologies exist. | Execution patterns cluster into partially stable archetypes or strategy profiles. | unplanned rate, drift variance, recovery latency, cascade sensitivity, planning frequency, readiness mismatch. | Cluster across users, then test longitudinal stability and predictive usefulness. | Clusters are unstable, non-predictive, or mostly artifacts of UI/cohort exposure. | speculative |
| H4 | Scope inflation may explain failure better than time estimation error. | Underestimated scope density mediates readiness-to-drift more strongly than duration estimates alone. | scope bullet count at plan/execute, description growth, task edits, duration delta, readiness. | Mediation test: readiness -> scope density -> execution drift; compare against direct readiness -> drift. | Scope variables add little explanatory power or mainly reflect decomposition style. | speculative / killable |
| H5 | Unplanned execution rate is a fundamental planning-layer variable. | The proportion of execution without prior planning predicts instability better than estimation error alone. | unplanned tasks, retroactive sessions, planned tasks, drift, recovery, pressure compression. | Correlate unplanned execution rate with drift, completion, recovery, and retention; test against estimation-error-only models. | Planning participation adds little explanatory or predictive value. | partially-supported / publishable candidate |
| H6 | Longitudinal traces matter more than snapshots. | Multi-week personal histories outperform single-session observations for prediction and interpretation. | rolling drift, rolling recovery, exposure-adjusted windows, per-user baselines. | Compare snapshot models against rolling user-specific models. | Rolling history does not improve interpretation or prediction. | partially-supported |

## 7. Provider, Scalability, And Product Architecture Assumptions

| ID | Assumption | Operational hypothesis | Observable variables | Validation path | Falsification signal | Status |
| --- | --- | --- | --- | --- | --- | --- |
| S1 | Provider data is structure, not execution truth. | Moodle/Baseet/Calendar/Jira-like systems can provide obligations and context, but not learning, completion, or calibration truth by themselves. | imported obligations, provider outcomes, user confirmations, execution traces. | Keep provider-bound rows low-authority until confirmed; test correction rates and false-positive pressure. | Provider-sourced status consistently equals user-confirmed execution without added risk. | doctrine-locked |
| S2 | Provider-native UX can coexist with a provider-blind core. | Users understand local vocabulary while Cortex and clean-data reason over normalized primitives. | adapter DTOs, provider labels, clean-data eligibility, provider-leakage scans. | Add provider adapters only behind normalization; run static provider-name leakage tests. | Provider-specific branches become necessary in Cortex or clean-data to preserve product value. | partially-supported |
| S3 | External systems can bootstrap context without provider lock-in. | Academic/workplace integrations improve utility while Lyra remains a provider-agnostic execution substrate. | provider mix, import success, plan acceptance, user-scoped adapter records. | Test one provider at a time; verify normalized facts survive provider replacement. | Value depends on one provider's semantics or proprietary workflow. | speculative |
| S4 | Drift rollups can improve scalability without corrupting research truth. | Async/cached rollups can reduce latency if they remain versioned, user-scoped, profile-scoped derived values. | endpoint p95, slow-query traces, metric version, clean profile, source high-water mark. | Delay materialization until runtime trigger; compare rollup output to read-time canonical values. | Rollups drift from source truth, hide profile/exposure state, or become user-facing authority. | future-gated |
| S5 | Runtime reliability is part of measurement validity. | Scheduler, database, topology, and auth failures can damage data quality if not classified and degraded correctly. | JobResult state, alert taxonomy, retry behavior, mutation phrase, topology verifier, smoke tests. | Enforce scheduler degradation contracts and topology checks; incident notes for repeated platform failures. | Operational failures silently create missing or mis-scoped behavioral traces. | doctrine-locked |
| S6 | Redis state must be atomic where execution traces can race. | Rapid timer or telemetry mutations require atomic Redis operations to avoid dropped or contradictory execution state. | stopwatch state, pause/resume bursts, active task ids, recovery rows. | Transaction/pipeline tests under rapid state changes. | Naive read-modify-write loses trace state or misbinds active execution. | partially-supported |

## 8. Security, Privacy, And Governance Assumptions

| ID | Assumption | Operational hypothesis | Observable variables | Validation path | Falsification signal | Status |
| --- | --- | --- | --- | --- | --- | --- |
| G1 | Security audit is governance-only. | `SecurityAuditEvent` can support incident review without becoming behavioral telemetry. | audit event imports, consumers, redacted metadata, event taxonomy. | Static scans block Cortex, analytics inference, clean-data, adaptive scheduling, and behavioral services from importing audit rows. | Audit state is consumed as productivity, attention, execution, or behavior evidence. | doctrine-locked |
| G2 | Provider failure must degrade functionality, not auth or scoping. | Calendar/Moodle/Baseet failures reduce context but never weaken identity, scope, or trust. | auth path, provider error path, scoped queries, provider outage alerts. | Route and outage tests; browser/API two-user smoke. | Any provider failure permits fallback identity, cross-user reads, or trusted synthetic evidence. | doctrine-locked |
| G3 | Token and provider payload redaction is a measurement prerequisite. | Sensitive provider data can be integrated only if raw URLs, OAuth payloads, tokens, emails, and session content stay out of logs/audit rows. | redaction tests, audit metadata, logs, provider DTOs. | Static and unit redaction tests for each adapter and audit path. | Raw secrets or behavioral session content enter governance/operational stores. | doctrine-locked |
| G4 | Small cohort with constant feedback is safer than premature scale. | Early users reveal validity threats and product friction before optimization pressure distorts measurement. | user interviews, correction logs, issue notes, exposure coverage, retention. | Trusted-alpha review cadence and professor/external architecture review before larger cohorts. | Cohort growth produces untriaged validity threats, hidden interventions, or trust collapse. | doctrine-locked |

## 9. Epistemology And Method Assumptions

| ID | Assumption | Operational hypothesis | Observable variables | Validation path | Falsification signal | Status |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | Reality constraints reveal truth better than isolated theorizing. | Product friction reliably generates sharper validity threats and contracts than armchair design alone. | incidents, bug sweeps, user-flow failures, doctrine revisions, tests added after friction. | Maintain friction -> threat -> contract genealogy in docs and commits. | Architecture changes become story-driven rather than evidence- or friction-driven. | doctrine-locked |
| E2 | Product and research should oscillate symmetrically. | Product surfaces generate traces; research constraints prevent overclaim; each improves the other. | feature changes, contract tests, exposure coverage, user feedback, claims demoted. | Review every new feature for whether it fixes a boundary, tests an invariant, or reduces operational risk. | Product velocity outpaces measurement validity or research doctrine blocks actual usability. | doctrine-locked |
| E3 | The git history is part of the methodology. | Timestamped commits and doctrine changes preserve the sequence of assumptions, failures, and responses. | commit messages, migration history, incident notes, doc revisions, test additions. | Keep changes scoped and traceable; link incidents and contracts to code/tests. | Reviewers cannot reconstruct why a measurement boundary exists. | doctrine-locked |
| E4 | Null results remain scientifically useful if assumptions are explicit. | Failed hypotheses refine the instrument instead of forcing hidden story changes. | killed hypotheses, demoted claims, new validity threats, revised analysis rules. | Pre-register falsifiers and preserve dead-theory registry. | Null results are reframed as success without new falsifiable hypotheses. | doctrine-locked |

## 10. Future Neuroadaptive Assumptions

| ID | Assumption | Operational hypothesis | Observable variables | Validation path | Falsification signal | Status |
| --- | --- | --- | --- | --- | --- | --- |
| N1 | BCI signals become more useful when grounded in longitudinal behavioral traces. | EEG/BCI cognitive-state estimates improve adaptive usefulness when conditioned on LyraOS execution history. | EEG markers, behavioral drift, recovery latency, exposure state, false positives, intervention outcomes. | Compare BCI-only inference against BCI + longitudinal execution context after behavioral validity gates pass. | Behavioral context adds little predictive or intervention value over BCI-only or behavior-only baselines. | future-gated |
| N2 | BCI is complementary evidence, not truth authority. | Neural signals and self-report capture noisy, partially overlapping constructs; weighting should be per-user and evidence-based. | signal-to-noise estimates, self-report, EEG features, execution deltas. | Simultaneous sessions with Bayesian or equivalent weighting; report correlation and divergence honestly. | BCI is treated as ground truth or fails to add signal after validated behavioral controls. | future-gated |
| N3 | Closed-loop neuroadaptive execution requires exposure governance first. | Neuroadaptive interventions are scientifically interpretable only if exposure, contamination, and clean-data admission are already robust. | exposure ledger rows, intervention class, downstream windows, clean-profile exclusions. | Do not integrate neuroadaptive intervention until exposure coverage and clean-data contracts are externally reviewed. | Neural feedback changes behavior without observable exposure state. | future-gated |

## 11. Investor Diligence Reading

The investor-relevant thesis is not that every assumption is true today.

The investor-relevant thesis is:

```text
LyraOS is building an execution instrument whose assumptions are explicit,
observable, and falsifiable before claims are scaled.
```

Potential moat candidates if validated:

- longitudinal execution traces under real constraints,
- exposure-aware intervention history,
- provider-agnostic normalization into substrate primitives,
- user-specific calibration over time,
- unplanned execution rate and cascade metrics,
- and future behavioral grounding for noisy cognitive-state signals.

Primary risks:

- traces do not generalize beyond operator/early cohort,
- users do not tolerate instrumentation friction,
- exposure effects overwhelm clean baseline inference,
- provider adapters leak local semantics into the core,
- operational instability damages data quality,
- or adaptive feedback becomes manipulative instead of epistemically honest.

Current mitigation strategy:

- small cohort before scale,
- professor/researcher architecture review,
- executable contracts for security, exposure, provider leakage, and clean-data
  admission,
- browser/API multi-user smoke,
- incident notes for operational failures,
- and no new features unless they fix a boundary, test an invariant, or reduce
  operational risk.

## 12. Highest-Priority Assumptions To Test Next

1. Provider adapters normalize local dialects without Cortex/clean-data leakage.
2. Exposure Ledger coverage is complete enough for all behavior-shaping
   surfaces.
3. Accepted intention improves calibration quality over passive activity.
4. Unplanned execution rate explains instability beyond estimation error.
5. Read-time drift computation remains fast until a real rollup trigger fires.
6. Small-cohort qualitative feedback confirms that transparency increases
   trust rather than confusion.

Until these survive contact with users and runtime, LyraOS should stay in
trusted-alpha research-instrument mode.
