# LyraOS Research Claim Map

> **Status:** explanatory research map for professor/external review.
> **Last updated:** 2026-05-16
> **Authority note:** this document is not canonical governance. `MANIFESTO.md`
> remains the highest-authority doctrine for research/product boundaries.

This map separates what LyraOS can honestly claim today from what remains
speculative. The current system is strongest as an implemented behavioral
measurement substrate. It has not yet validated cross-user behavioral
prediction, adaptive scheduling, or archetype effectiveness.

---

## 1. Already Supported By Implementation

These claims are supported by code, tests, or shipped architecture. They are
not yet the same as validated behavioral science claims.

| Claim | Current support | Repo references |
| --- | --- | --- |
| Lyra separates product traces, derived metrics, exposure state, and output surfaces. | The repository has Cortex contracts, exposure ledger models/services, output surface registry behavior, and regression tests. | `docs/cortex_product_research_contract_v0.md`, `backend/app/services/exposure_ledger.py`, `backend/app/services/output_surfaces.py`, `backend/tests/test_exposure_ledger_v0.py` |
| Exposure state fails closed when unknown. | Exposure helpers represent `NONE`, `EXPOSED`, `INTERVENTION`, and `UNKNOWN`; only clean state may certify baseline use. | `backend/app/services/exposure_ledger.py`, `backend/tests/test_exposure_ledger_v0.py` |
| Bias-factor priors and personal-history blending are implemented. | The backend computes a prior-personal blend and exposes provenance fields, but the numeric prior values are engineering priors. | `backend/app/services/bias_factor_service.py`, `backend/tests/test_bias_factor_blend.py` |
| Archetype proximity exists as a probabilistic surface. | The backend computes proximity from qualifying task evidence and dampens evidence rather than treating the profile as identity truth. | `backend/app/services/archetype_proximity_service.py`, `backend/tests/test_analytics_archetype_proximity.py` |
| Pause and resume prediction are implemented as bounded predictors. | Services, scheduler jobs, log rows, cooldowns, and tests exist. This supports implementation maturity, not clinical validity. | `backend/app/services/pause_predictor.py`, `backend/app/services/resume_predictor.py`, `backend/tests/test_resume_predictor.py` |
| User-facing behavioral outputs are treated as exposure candidates. | Output-surface registration and exposure acknowledgement paths exist. | `backend/app/core/output_surface_registry.json`, `backend/app/services/output_surfaces.py`, `backend/app/api/v1/endpoints/exposures.py` |

Conservative phrasing:

```text
LyraOS has implemented the infrastructure needed to study planning and
execution behavior under explicit provenance, exposure, and uncertainty
constraints.
```

Avoid:

```text
LyraOS has proven that it can predict user failure.
```

---

## 2. Supported By Literature

These ideas are directionally supported by the cited literature and are safe as
background framing when stated conservatively.

| Literature-backed claim | What the literature supports | Key sources |
| --- | --- | --- |
| People often underestimate personal task completion time. | Planning fallacy and optimistic scenario focus are well-established for task prediction. | Buehler, Griffin & Ross 1994; Newby-Clark et al. 2000; Roy, Christenfeld & McKenzie 2005 |
| Outside-view records can improve future estimates. | Prior-duration records and explicit use of past cases can improve prediction. | Buehler et al. 1994; Roy et al. 2005 |
| Pre-task estimates can be contaminated by suggestions. | Anchoring and adjustment make pre-task system suggestions a measurement threat. | Tversky & Kahneman 1974 |
| Post-task reflection is noisy and outcome-contaminated. | Hindsight bias, cue-dependent metacognition, and common-method bias are real validity threats. | Fischhoff 1975; Koriat 1997; Podsakoff et al. 2003 |
| Personal informatics systems are fragile around friction, lapses, and inaccurate data. | Self-tracking users face collection/reflection/action barriers; frustration and lapses are common. | Li, Dey & Forlizzi 2010; Epstein et al. 2015 |
| Short self-report instruments can seed hypotheses. | MEQ, BFI-10, BSCS, and procrastination scales have psychometric roots. | Horne & Ostberg 1976; Adan & Almirall 1991; Rammstedt & John 2007; Tangney, Baumeister & Boone 2004; Lay 1986; Steel 2007/2010 |

Important correction: the literature supports the **directional rationale** for
duration estimation, self-report caution, and cold-start hypotheses. It does not
directly validate LyraOS's current category-specific numeric priors or adaptive
scheduling behavior.

---

## 3. Speculative Claims

These are active hypotheses or product-research directions. They should be
presented as hypotheses until multi-user, exposure-aware, held-out evidence
exists.

| Claim | Why it is speculative | What would strengthen it |
| --- | --- | --- |
| Repeated planning/execution traces contain stable, useful behavioral structure. | This is the core substrate hypothesis. The system can collect the traces, but cross-user predictive validity is not yet established. | Longitudinal multi-user analysis with train/test separation and clean-data profiles. |
| Readiness or discrepancy predicts planning drift. | Operator dogfood has suggestive anomalies, but single-user evidence cannot establish the construct. | Within-user and across-user models comparing readiness-only, history-only, and combined predictors. |
| Adaptive scheduling can eventually be earned from evidence. | Current adaptive scheduling is a future-gated direction, not a validated shipped system. | Explicit experiment protocol, exposure logging, acceptance/rejection outcomes, and outcome comparisons. |
| Archetype priors improve cold-start calibration. | The survey and priors are implemented as hypothesis scaffolding, not validated clusters. | Reliability checks, cluster separability, and proof that priors beat flat/history-only baselines. |
| Missingness is meaningful signal. | Missingness can be informative, but random inconsistency and usability friction must be separated. | Missingness taxonomy, user/session context, and tests against random-dropout baselines. |

Conservative phrasing:

```text
LyraOS is designed to test whether these traces become predictive under
clean-data and exposure constraints.
```

---

## 4. Novel Combination

The novelty is not that each component is new. The stronger claim is that LyraOS
combines several mature ideas into a product-shaped behavioral instrument.

Potentially novel combination:

- low-friction planning and timer product as the data collection interface
- read-time metric canonicalization through Cortex
- output-surface registration before behavioral feedback is rendered
- exposure ledger to distinguish baseline from post-feedback behavior
- cold-start priors that must decay or be overridden by personal traces
- explicit uncertainty and fail-closed research doctrine
- user attention treated as scarce measurement capital

Professor-safe framing:

```text
The project is less novel as a planning-fallacy claim and more novel as an
integrated product/research architecture for collecting and protecting
longitudinal planning-execution traces.
```

---

## 5. Rediscoveries And Borrowed Foundations

These ideas should not be presented as LyraOS discoveries. LyraOS can use them,
operationalize them, or combine them, but the underlying ideas are already known.

| Idea | Status |
| --- | --- |
| Planning fallacy and optimistic task prediction | Established literature. |
| Anchoring as a threat to independent estimates | Established judgment-and-decision-making literature. |
| Self-tracking friction and lapses | Established personal informatics/HCI literature. |
| Self-report unreliability and hindsight bias | Established measurement-validity literature. |
| Trait scales for chronotype, conscientiousness, self-control, and procrastination | Established psychometric instruments. |
| Bayesian-ish prior updating / shrinkage intuition | Established statistical framing; Lyra's current implementation is a heuristic prior-personal blend, not a full Bayesian posterior model. |

---

## 6. Needs Operationalization Or Stronger Statistics

These are the main places where LyraOS should be tightened before stronger
research claims.

### Operationalization Gaps

| Gap | Needed next step |
| --- | --- |
| Duration delta sign and naming | Keep `P`, `E`, `m = E/P`, and delta sign conventions explicit in every analysis/report. |
| Time-estimation error vs scope inflation | Add or derive scope-change markers before claiming overruns are pure estimation error. |
| Adaptive scheduling | Define experiments, exposure windows, user acceptance/rejection, rollback, and outcome measures before shipping stronger suggestions. |
| Missingness as signal | Distinguish ignored prompts, abandoned tasks, technical failures, and random lapses. |
| Repaired/retroactive traces | Keep repaired data out of measured-execution baselines unless a successor clean-data profile admits it. |

### Statistical Grounding Gaps

| Gap | Needed next step |
| --- | --- |
| Hardcoded `RESEARCH_PRIORS` | Treat as engineering priors initialized from literature, not published population means. Refit once enough Lyra traces exist. |
| `1.35` default prior | Do not attribute numerically to Kahneman & Tversky. Use them only as conceptual lineage. |
| Steel/procrastination multiplier | Mark any GP-high duration multiplier as unvalidated until directly supported or estimated from Lyra data. |
| Archetype validity | Check reliability, separability, prior-beats-flat performance, and decay/override behavior. |
| Readiness/discrepancy predictive value | Run held-out within-user and cross-user tests against history-only baselines. |
| Operator dogfood findings | Keep as formative evidence, not final validation. |

---

## 7. Compact Bibliography

| Source | Used for |
| --- | --- |
| Tversky, A., & Kahneman, D. (1974). *Judgment under Uncertainty: Heuristics and Biases.* | Anchoring and heuristic judgment threats. |
| Kahneman, D., & Tversky, A. (1979). *Intuitive Prediction: Biases and Corrective Procedures.* | Conceptual lineage for intuitive prediction; not a numeric prior source. |
| Buehler, R., Griffin, D., & Ross, M. (1994). *Exploring the planning fallacy: Why people underestimate their task completion times.* | Planning fallacy and future-scenario focus. |
| Newby-Clark, I. R., Ross, M., Buehler, R., Koehler, D. J., & Griffin, D. (2000). *People focus on optimistic scenarios and disregard pessimistic scenarios while predicting task completion times.* | Optimistic scenario bias. |
| Roy, M. M., Christenfeld, N. J. S., & McKenzie, C. R. M. (2005). *Underestimating the duration of future events: Memory incorrectly used or memory bias?* | Duration-estimation review and outside-view motivation. |
| Li, I., Dey, A., & Forlizzi, J. (2010). *A stage-based model of personal informatics systems.* | Self-tracking stages and barriers. |
| Epstein, D. A., Ping, A., Fogarty, J., & Munson, S. A. (2015). *A lived informatics model of personal informatics.* | Lapses, switching, and lived self-tracking friction. |
| Fischhoff, B. (1975). *Hindsight is not equal to foresight.* | Post-outcome judgment contamination. |
| Koriat, A. (1997). *Monitoring one's own knowledge during study: A cue-utilization approach to judgments of learning.* | Metacognitive self-rating caution. |
| Podsakoff, P. M., MacKenzie, S. B., Lee, J.-Y., & Podsakoff, N. P. (2003). *Common method biases in behavioral research.* | Shared-method measurement validity threats. |
| Horne, J. A., & Ostberg, O. (1976). *A self-assessment questionnaire to determine morningness-eveningness in human circadian rhythms.* | Chronotype instrument lineage. |
| Adan, A., & Almirall, H. (1991). *Horne & Ostberg morningness-eveningness questionnaire: A reduced scale.* | Short chronotype instrument lineage. |
| Rammstedt, B., & John, O. P. (2007). *Measuring personality in one minute or less: A 10-item short version of the Big Five Inventory.* | BFI-10 lineage. |
| Tangney, J. P., Baumeister, R. F., & Boone, A. L. (2004). *High self-control predicts good adjustment, less pathology, better grades, and interpersonal success.* | Brief Self-Control Scale lineage. |
| Lay, C. H. (1986). *At last, my research article on procrastination.* | General Procrastination Scale lineage. |
| Steel, P. (2007). *The nature of procrastination: A meta-analytic and theoretical review of quintessential self-regulatory failure.* | Procrastination/self-regulation background. |
| Steel, P. (2010). *Arousal, avoidant and decisional procrastinators: Do they exist?* | Procrastination subtype/measurement caution. |

---

## 8. One-Paragraph External Summary

LyraOS currently has an implemented behavioral instrumentation architecture:
task plans, execution traces, pauses, reflections, exposure events, and
clean-data profiles are captured and separated from user-facing feedback. The
literature supports the general rationale that humans often misestimate task
duration, self-report is noisy, and self-tracking systems are sensitive to
friction and data quality. What remains unvalidated is the stronger claim that
LyraOS can predict failure or adapt scheduling across users. The most honest
current claim is that LyraOS is a serious substrate for testing those questions,
not that it has already answered them.
