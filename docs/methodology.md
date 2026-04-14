# Research Methodology

*Canonical research-layer document. Consolidates earlier drafts of clustering and hypothesis notes (never committed as standalone files); those names are historical.*
*Last updated: April 14, 2026.*

This document covers the research layer: clustering model, validation gates, and working hypotheses beyond H1. The primary hypothesis (H1: signed_discrepancy -> delta) and its pre-registered kill criterion live in `MANIFESTO.md §Kill Criterion — H1` and are not duplicated here.

---

## 1. Cold-Start Personalization via Archetype Priors

*Status: design only. No implementation as of v1.5.*

### Rationale

The `bias_factor` model is per-(category, time_of_day) and starts from a flat 1.0 prior. With few sessions, most cells are data-starved. Three options for cold-start:

1. **Flat 1.0** (current) — wrong for everyone, slow to learn.
2. **Population mean** — better than flat, but the population is heterogeneous.
3. **Archetype prior** (this spec) — assign new users to a behavioral cluster at signup using validated psychometric instruments, use that cluster's empirical bias_factor distribution as their prior, then shrink toward the personal estimate as sessions accumulate.

Implementation lands post-multi-user migration.

### Psychometric instruments

Four short, validated instruments. Total signup time target: under 4 minutes (29 items at 5-7s each).

| Instrument | Items | Score range | Output | Why |
|---|---|---|---|---|
| **MEQ-5** (Chronotype) — Horne & Ostberg 1976, short form Adan & Almirall 1991 | 5 | 4-25 | <=11 evening, 12-17 intermediate, >=18 morning | Chronotype predicts which time-of-day buckets have positive vs negative bias |
| **BFI-10 C** (Conscientiousness) — Rammstedt & John 2007 | 2 | 2-10 | <=4 low, 5-7 mid, >=8 high | Strongest Big Five predictor of planning follow-through |
| **BSCS-Brief** (Self-Control) — Tangney, Baumeister, Boone 2004 | 13 | 13-65 | Tertile split (median ~39) | Predicts initiation_delay and abandonment_pattern |
| **GP-Short** (Procrastination) — Lay 1986, abbreviated per Steel 2010 | 9 | 9-45 | <=20 low, 21-32 mid, >=33 high | Most direct predictor of bias_factor magnitude |

### The 2D archetype space

Four traits collapse to two axes:

- **Axis A — Temporal alignment:** MEQ-5 alone. Three levels: morning / intermediate / evening.
- **Axis B — Execution discipline:** Weighted composite: `discipline_z = 0.30 * z(BFI-C) + 0.40 * z(BSCS) + 0.30 * (-z(GP))`. BSCS gets the largest weight because it asks about actions, not self-image. Three levels: low / mid / high.

3 x 3 = 9 nominal cells, collapsed to 5 archetypes.

### The 5 archetypes (with empirical priors)

| # | Name | Cells covered | Prior bias_factor | Rationale |
|---|---|---|---|---|
| 1 | **Disciplined Lark** | morning x high | 0.95 (sigma 0.15) | Closest to plan; slight underestimate. Buehler 1994. |
| 2 | **Disciplined Owl** | evening x high | 1.05 (sigma 0.20) | Same discipline, mornings structurally harder. |
| 3 | **Diffuse Average** | intermediate x mid (default) | 1.30 (sigma 0.30) | Population midpoint from Roy 2005 meta-analysis. |
| 4 | **Procrastinator** | * x low | 1.80 (sigma 0.40) | Steel 2010: GP-high subjects underestimate 1.6-2.2x. |
| 5 | **Lark, low discipline** | morning x low | 1.50 (sigma 0.35) | Morning chronotype partially compensates for low discipline in peak window. |

The sigma values are intentionally generous — priors should not over-commit before personal data arrives.

Key citations:
- Buehler R, Griffin D, Ross M. (1994). J Pers Soc Psychol 67(3):366-381.
- Roy MM, Christenfeld NJS, McKenzie CRM. (2005). Psychol Bull 131(5):738-756.
- Pezzo MV, Litman JA, Pezzo SP. (2006). Pers Individ Differ 41(7):1359-1371.
- Steel P. (2007, 2010). Psychol Bull 133(1):65-94.

### Bayesian shrinkage formula

```
personal_weight   = min(1.0, n_sessions_in_cell / 30)
prior_weight      = 1.0 - personal_weight

bias_factor_final = prior_weight   * archetype_prior_for_cell
                  + personal_weight * personal_sum_ratio_for_cell
```

Why n=30: conventional CLT threshold for stable mean estimation; roughly the sessions an active user generates per category in 2-3 weeks. Tunable — fit empirically once multi-user data arrives.

Why linear: simplest defensible blend. Exponential under-weights early personal data.

### Assignment algorithm

```
on_signup(user):
    scores = administer_instruments(user)
    chronotype = classify_meq(scores.meq)
    discipline_z = 0.30 * z(BFI-C) + 0.40 * z(BSCS) + 0.30 * (-z(GP))
    discipline = classify_z(discipline_z)

    archetype = match (chronotype, discipline):
        ("morning",  "high") -> Disciplined Lark
        ("evening",  "high") -> Disciplined Owl
        (_,          "low" ) -> Procrastinator
        ("morning",  "low" ) -> Lark Low-Discipline
        _                    -> Diffuse Average

    seed_bias_factor_priors(user, archetype)
```

Re-assignment: automatic at 90 days if score differs by >1 SD on discipline axis. Manual via settings page. Personal data is never discarded on re-assignment.

### Implementation notes

Schema additions (alembic migration, post-multi-user):
- `user.archetype` (String(40)), `user.archetype_assigned_at` (DateTime), `user.instrument_scores` (JSON)
- `bias_factor_prior` table: (archetype, category, time_of_day) PK, prior_value (Float), prior_sigma (Float)

Service layer: `archetype_service.py` (instruments, scoring, assignment), `bias_factor_blend.py` (single `blend()` function). New endpoint: `GET /v1/scheduler/predicted_duration?category=...&time_of_day=...`.

---

## 2. Validation Gates

Five gates in order before clustering moves from design to production.

### Gate 1 — Instrument reliability (before launch)
- **Trigger:** First 20 users complete onboarding survey.
- **Check:** Cronbach's alpha >= 0.65 on each subscale.
- **Fail-action:** Drop or replace the unreliable subscale. BSCS fails -> fall back to GP-only. MEQ-5 fails -> single self-report chronotype item.

### Gate 2 — Archetype separability (n >= 50 per archetype)
- **Trigger:** 250+ users assigned.
- **Check:** Silhouette score >= 0.3 on (chronotype, discipline_z) space.
- **Fail-action:** Merge adjacent archetypes (e.g., both Disciplined types -> "Disciplined"). If still <0.3, abandon archetypes, use single population prior.

### Gate 3 — Prior beats flat (n >= 10 sessions per user, >= 100 users)
- **Trigger:** 100+ users with >= 10 executed sessions.
- **Check:** Hold-out MAE comparison. Archetype prior must beat flat 1.0 by >= 15%.
- **Fail-action:** Fall back to Diffuse Average prior for everyone. Keep instrument data for research.

### Gate 4 — Shrinkage curve calibration (>= 200 users, 90+ days each)
- **Trigger:** 200+ users with 90+ days of data.
- **Check:** Fit optimal blend curve, compare to linear-to-30.
- **Fail-action:** Update threshold if optimal n differs by > +/-10 sessions. Switch to non-linear if >10% error reduction.

### Gate 5 — Assignment stability (90-day retest, >= 100 users)
- **Trigger:** 100+ users reach 90-day re-assessment.
- **Check:** >= 70% land in same archetype on retest.
- **Fail-action:** <60%: revisit weights/thresholds. 60-70%: flag as marginal, retest at 180 days.

Gates 1-2 are **blocking** (no production assignment until both pass). Gates 3-5 are **corrective** (system launches with hardcoded priors, gates trigger improvements).

### What this spec does NOT claim
- That archetype membership predicts H1. H1 is independent, tested separately per MANIFESTO.
- That the 5 archetypes are exhaustive. #6 and #7 may emerge from cluster analysis.
- That instruments measure ground truth. Validation tests are all behavioral (predicted vs actual delta).

### Open questions for post-Apr 15 review
1. Should `category` be in the prior table at all, or only `time_of_day`?
2. Should the operator's existing data feed back into prior generation as "user 1"?
3. Is the discipline_z weighting (0.30/0.40/0.30) defensible, or should it be regression-derived?
4. Does 90-day re-assessment conflict with long-term experiment designs?

---

## 3. Working Hypotheses

### H4 — Motivated Underestimation Hypothesis

**Origin:** Form A respondent #3, April 9 2026.

**Claim:** People underestimate task duration not (only) because of cognitive bias, but because the underestimate itself produces a small reward. The optimistic plan feels good in the moment of planning, and finishing "early" against an unrealistic estimate generates a dopamine hit that finishing on time against a realistic estimate does not.

**Implication for Lyra:** The calibration nudge may face emotional resistance even when users intellectually accept it. Removing the underestimation removes the reward source. "Accurate estimation" may be less desirable than "estimation that feels ambitious."

**Predictions if true:**
- Users high on optimism/reward-sensitivity (BFI Extraversion, BAS-Drive) will resist calibration nudges more
- Sessions where executed < planned will correlate with higher post_task_reflection, controlling for delta
- Users will silently inflate plans over time after seeing the calibration nudge

**Predictions if false:**
- No correlation between underrun and reflection score
- Users adopt calibrated estimates with unchanged or higher plan satisfaction

**Status:** UNVALIDATED — n=1 anecdotal. Do not act on this in product decisions until 5+ respondents independently surface the theme, OR 30+ paired sessions per user exist to test the prediction.

**Relationship to H1:** Independent. H1 is about metacognitive accuracy. H4 is about motivated cognition driving the inaccuracy. Both could be true, false, or split. Test separately.

**Test design (post-Phase 10):**
1. Per user with >= 30 paired sessions: Spearman correlation between underrun magnitude and post_task_reflection, controlling for category and time-of-day
2. Positive correlation = H4 supported
3. After calibration nudge ships: compare bias_factor trajectories — do users converge on accurate estimates, or inflate plans to preserve the underrun reward?
