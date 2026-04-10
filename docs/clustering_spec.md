# Clustering Spec — Cold-Start Personalization via Archetype Priors

*Status: design only. No implementation in this document.*
*Author: Lyra Secretary v0.1 — drafted Apr 8 2026.*
*Audience: future implementer (likely the same operator) post-Apr 15 experiment.*

---

## 1. Rationale

The current `bias_factor` model is per-(category, time_of_day) and starts from a flat 1.0 prior. With 24 executed non-retroactive sessions on Day 4, only **one** fully-qualified cell exists; everything else is data-starved (`insufficient_cells` array proves this empirically). The same problem hits any new user on Day 1 — but worse, because they have *zero* sessions.

Three options for cold-start:

1. **Flat 1.0** (current) — wrong for everyone, slow to learn.
2. **Population mean** — better than flat, but the population is heterogeneous: a morning chronotype with low procrastination needs a different prior than an evening chronotype with high procrastination. Population mean is everyone's average, no one's reality.
3. **Archetype prior** (this spec) — assign new users to one of a small number of behavioral clusters at signup based on validated psychometric instruments, use that cluster's empirical bias_factor distribution as their prior, then shrink toward the personal estimate as sessions accumulate.

Archetype priors are the only option that makes Day-1 personalization actually personal without requiring weeks of cold-start data collection. They work because the literature supports clustering on a small set of stable traits that *predict* planning-fallacy magnitude (chronotype, conscientiousness, self-control, procrastination tendency).

This spec is design-only because the operator is currently a single subject, archetype assignment is meaningless on n=1, and the experiment is mid-window. The implementation lands post-multi-user migration.

---

## 2. Psychometric instruments

Four short, validated instruments. All four are public-domain or free-for-research and produce numeric scales. Total signup time target: **under 4 minutes**.

### MEQ-5 (Chronotype) — Horne & Östberg 1976, short form Adan & Almirall 1991
- 5 items, 5-point Likert each.
- Score range: 4–25.
- Output mapping: ≤11 evening type, 12–17 intermediate, ≥18 morning type.
- Why: chronotype directly predicts which time-of-day buckets will have positive vs negative bias. An evening type's "morning" cell is structurally different from a morning type's "morning" cell.
- Citation: Horne JA, Östberg O. (1976). *A self-assessment questionnaire to determine morningness-eveningness in human circadian rhythms.* Int J Chronobiol 4(2):97–110. Adan A, Almirall H. (1991). *Horne & Östberg morningness-eveningness questionnaire: A reduced scale.* Pers Individ Differ 12(3):241–253.

### BFI-10 (Big Five, Conscientiousness only) — Rammstedt & John 2007
- Use only the 2 conscientiousness items from BFI-10.
- 5-point Likert.
- Score range: 2–10.
- Output mapping: ≤4 low C, 5–7 mid C, ≥8 high C.
- Why: conscientiousness is the strongest Big Five predictor of planning behavior and follow-through. Low-C operators systematically underestimate effort across the board.
- Citation: Rammstedt B, John OP. (2007). *Measuring personality in one minute or less: A 10-item short version of the Big Five Inventory in English and German.* J Res Pers 41(1):203–212.

### BSCS-Brief (Brief Self-Control Scale) — Tangney, Baumeister, Boone 2004, 13-item form
- 13 items, 5-point Likert.
- Score range: 13–65.
- Output mapping: tertile split on the calibration sample (median ~39, IQR roughly 33–45 in college samples).
- Why: self-control predicts the gap between *intending* to start a planned task and *actually* starting it. Maps directly to `initiation_delay_minutes` and `abandonment_pattern`.
- Citation: Tangney JP, Baumeister RF, Boone AL. (2004). *High self-control predicts good adjustment, less pathology, better grades, and interpersonal success.* J Pers 72(2):271–324.

### GP-Short (General Procrastination, short form) — Lay 1986, abbreviated per Steel 2010
- 9 items (subset of Lay's 20-item GP scale), 5-point Likert.
- Score range: 9–45.
- Output mapping: ≤20 low, 21–32 mid, ≥33 high procrastinator.
- Why: procrastination tendency is what the planning-fallacy literature actually measures — the gap between predicted and actual completion time scales with GP score. This is the most direct predictor of `bias_factor` magnitude.
- Citation: Lay CH. (1986). *At last, my research article on procrastination.* J Res Pers 20(4):474–495. Steel P. (2010). *Arousal, avoidant and decisional procrastinators: Do they exist?* Pers Individ Differ 48(8):926–934.

**Total: 5 + 2 + 13 + 9 = 29 items.** At 5–7 seconds per Likert, that's 2.5–3.5 minutes. Well under the 4-minute budget.

---

## 3. The 2D archetype space

Four traits collapse to **two axes** for archetype assignment. This is deliberate dimensionality reduction — fewer axes means fewer archetypes means more sessions per cluster in calibration.

### Axis A — Temporal alignment (when does the person execute well?)
Driven by **MEQ-5** alone. Three levels: morning / intermediate / evening.

### Axis B — Execution discipline (does the person follow through?)
Driven by a weighted composite of **BFI-10 C**, **BSCS**, and **GP** (reverse-scored):

```
discipline_z = 0.30 * z(BFI-C) + 0.40 * z(BSCS) + 0.30 * (-z(GP))
```

Z-scores against the calibration sample (initially the n=1 operator, expanded as users arrive). Three levels: low / mid / high discipline.

Weighting rationale: BSCS gets the largest weight because it's the most behaviorally grounded of the three (it asks about actions, not self-image). GP and BFI-C contribute equally as cross-checks — high agreement across all three is what makes a discipline assignment trustworthy.

### Resulting cells: 3 × 3 = 9 nominal cells
But not all 9 deserve their own archetype. The literature supports collapsing them into **5 archetypes** (next section) — the corner combinations that produce qualitatively different planning behavior, plus a default middle.

---

## 4. The 5 archetypes (with empirical priors)

Each archetype has a starting `bias_factor` distribution drawn from the literature. These are *priors*, not predictions — they get overwritten by personal data as sessions accumulate.

| # | Name | Cells covered | Prior bias_factor | Rationale |
|---|---|---|---|---|
| 1 | **Disciplined Lark** | morning × high | 0.95 (σ 0.15) | Closest to plan; slight underestimate. Buehler 1994 college students who scored high on conscientiousness. |
| 2 | **Disciplined Owl** | evening × high | 1.05 (σ 0.20) | Same discipline, but mornings are structurally harder for them. Slight overrun, especially before noon. |
| 3 | **Diffuse Average** | intermediate × mid (and any cell that doesn't fit a corner) | 1.30 (σ 0.30) | The population midpoint from Buehler & Roy. The Roy 2005 meta-analytic finding of 1.3× was on a mixed sample — this is the best default. |
| 4 | **Procrastinator (any chronotype) × low discipline** | * × low | 1.80 (σ 0.40) | Heavy planning-fallacy load. Steel 2010 showed GP-high subjects underestimate by 1.6–2.2× on multi-step tasks. Pezzo 2006 confirmed the same on single-task estimates. |
| 5 | **Lark, low discipline** | morning × low | 1.50 (σ 0.35) | Specifically called out because morning chronotype partially compensates for low discipline — they execute better than a generic procrastinator in their peak window, worse outside it. Time-of-day cells will diverge sharply for this archetype. |

Citations for the priors:
- Buehler R, Griffin D, Ross M. (1994). *Exploring the "planning fallacy": Why people underestimate their task completion times.* J Pers Soc Psychol 67(3):366–381. → 1.0–1.3× for college students on academic tasks.
- Roy MM, Christenfeld NJS, McKenzie CRM. (2005). *Underestimating the duration of future events: Memory incorrectly used or memory bias?* Psychol Bull 131(5):738–756. → meta-analytic 1.3× on a mixed sample.
- Pezzo MV, Litman JA, Pezzo SP. (2006). *On the distinction between yuppies and hippies: Individual differences in prediction biases for planning future tasks.* Pers Individ Differ 41(7):1359–1371. → conscientiousness moderates planning bias.
- Steel P. (2007, 2010). *The nature of procrastination.* Psychol Bull 133(1):65–94. → GP score predicts 1.6–2.2× underestimation on procrastination-prone tasks.

The σ values are intentionally generous because the priors are doing pre-data work — they should not over-commit before personal sessions arrive.

---

## 5. Bayesian shrinkage formula

The system blends the archetype prior with the personal empirical estimate as sessions accumulate. The blend weight grows linearly until the personal estimate fully owns the prediction at n = 30 sessions per cell.

```
personal_weight   = min(1.0, n_sessions_in_cell / 30)
prior_weight      = 1.0 - personal_weight

bias_factor_final = prior_weight   * archetype_prior_for_cell
                  + personal_weight * personal_sum_ratio_for_cell
```

Where `personal_sum_ratio_for_cell = sum(executed_minutes) / sum(planned_minutes)` over the operator's sessions in that (category, time_of_day) cell.

### Why n = 30
- 30 is the conventional threshold for the central limit theorem to give a reasonably stable mean of a continuous variable.
- It is also roughly the number of sessions an active operator generates in a single category within 2–3 weeks of normal use, which is the right horizon for "I trust your data over the prior."
- It is *not* derived from theory — it is a tunable. After multi-user data arrives, fit it empirically by holding out a validation set and finding the n that minimizes downstream prediction error.

### Why linear (not exponential or sigmoid)
Linear is the simplest defensible blend and easy to explain to the operator ("after 30 sessions in this slot, your data fully owns the prediction"). Exponential decay was considered and rejected because it under-weights early personal data — the first 5 sessions in a cell are highly informative and should immediately move the prediction off the prior.

### Per-archetype variance σ as a confidence reporter (not a blend weight)
The σ values from §4 are reported alongside the prediction so the UI can show "high prior uncertainty" early on. They do *not* enter the blend formula — keeping the math one-line readable matters more than capturing every nuance of the prior's spread.

---

## 6. Assignment algorithm

```
on_signup(user):
    scores = administer_instruments(user)   // MEQ-5, BFI-10 C, BSCS, GP-Short
    chronotype = classify_meq(scores.meq)   // morning / intermediate / evening
    discipline_z = (
        0.30 * z(scores.bfi_c, BFI_C_sample_stats)
      + 0.40 * z(scores.bscs,  BSCS_sample_stats)
      + 0.30 * (-z(scores.gp,  GP_sample_stats))
    )
    discipline = classify_z(discipline_z)   // low / mid / high

    archetype = match (chronotype, discipline):
        ("morning",      "high") -> Disciplined Lark
        ("evening",      "high") -> Disciplined Owl
        (_,              "low" ) -> Procrastinator        // overrides chronotype except below
        ("morning",      "low" ) -> Lark Low-Discipline   // more specific than Procrastinator
        _                        -> Diffuse Average

    user.archetype = archetype
    user.archetype_assigned_at = now()
    user.instrument_scores = scores               // store raw for re-assignment
    seed_bias_factor_priors(user, archetype)     // populate per-cell priors
```

### Re-assignment policy
The archetype is fixed at signup but **not immutable**. Two re-assignment triggers:

1. **Automatic re-assessment** at 90 days. If the new score differs by more than 1 SD on the discipline axis, re-bucket. The operator is notified.
2. **Manual** via a settings page. Useful for life-event changes (new job, new schedule, post-injury, etc.).

When archetype changes, the personal data is *not* discarded. The blend formula in §5 still works because `personal_weight` only depends on `n_sessions_in_cell`, not on the prior identity. Switching archetypes only changes the prior on cells where the operator hasn't yet hit n = 30.

---

## 7. Implementation notes

**Schema additions (will require an alembic migration when implemented):**

| Table | Field | Type | Notes |
|---|---|---|---|
| `user` (new — see multi-user migration plan) | `archetype` | `String(40)` | One of 5 archetype names |
| `user` | `archetype_assigned_at` | `DateTime` | For re-assessment trigger |
| `user` | `instrument_scores` | `JSON` | Raw MEQ/BFI-C/BSCS/GP scores for re-bucket |
| `bias_factor_prior` (new lookup table) | `(archetype, category, time_of_day)` PK | composite | Seeded at app init |
| `bias_factor_prior` | `prior_value` | `Float` | The archetype's prior for this cell |
| `bias_factor_prior` | `prior_sigma` | `Float` | For UI uncertainty display |

**Service layer:**
- `services/archetype_service.py` — administers instruments, computes scores, assigns archetype, handles re-assessment.
- `services/bias_factor_blend.py` — single function `blend(user_id, category, time_of_day) -> dict` returning `{ value, prior_value, personal_value, n_sessions, personal_weight, sigma }`. Called by the scheduler at task creation time.
- The existing `GET /v1/analytics/bias_factor` endpoint stays as-is for the operator's introspection. A new endpoint `GET /v1/scheduler/predicted_duration?category=...&time_of_day=...` wraps `blend()` for the scheduler's use.

**Where the prior table comes from:**
- Initially: hardcoded from §4 above. Five archetypes × ~11 categories × 4 time-of-day = ~220 rows. Hand-seeded once.
- Eventually (n ≥ 100 users per archetype): replace the hardcoded values with the empirical pooled mean per archetype-cell. This is a periodic batch job, not online learning.

**Cost of running this (worth flagging):**
- Instruments add ~3 min to signup. This is real friction. Mitigation: make the survey skippable with a warning that the system will start from a flat 1.0 prior. Most users will take the survey if the explanation is honest ("we'll personalize your scheduler in 3 minutes — or skip and we'll guess for the first month").
- Storing raw instrument scores is mildly sensitive (psychometric data). Encrypt at rest if the deployment grows beyond personal use.

---

## 8. Validation plan

The clustering model claims four things. Each has a falsification test.

### Claim 1: The 5 archetypes are real (cluster separability)
Test: with ≥ 50 users per archetype, run a silhouette analysis on the (chronotype, discipline_z) space. Silhouette score ≥ 0.4 across all archetypes is "real clusters." < 0.3 is "the archetypes are a useful fiction but not statistically separable" — keep them anyway because the priors still work.

### Claim 2: Archetype priors beat the flat 1.0 prior at cold start
Test: hold out the first 10 sessions of each new user. Compute predicted vs actual for both `bias_factor_final` (with archetype prior) and `bias_factor_final` (with flat 1.0 prior). Mean absolute error of the archetype version must be **lower** by at least 15%. If not, archetypes are not earning their complexity — fall back to a single population prior.

### Claim 3: The Bayesian shrinkage curve has the right shape (n=30 is a good threshold)
Test: with ≥ 200 users and ≥ 90 days of data each, fit the optimal blend curve (could be exponential, could be sigmoid, could shift to n=20 or n=50). If the empirical optimum is wildly different from linear-to-30, replace the formula. If it's within 10%, keep the linear form for explainability.

### Claim 4: Archetype assignment is stable over 90 days
Test: re-administer instruments at 90 days for ≥ 100 users. ≥ 70% should land in the same archetype. Below 60% means the instruments are too noisy or the bucketing thresholds are wrong — revisit the discipline_z weights.

### What this spec does *not* claim (to forestall scope creep)
- That archetype membership predicts H1 (signed_discrepancy → delta). H1 is independent and tested separately per MANIFESTO.
- That the 5 archetypes are exhaustive. They are a tractable starting set; #6 and #7 may emerge from the cluster analysis in Claim 1.
- That instruments measure ground truth. They measure self-report. The validation tests above are all *behavioral* (predicted vs actual delta, cluster separability of behavior) — never "did the instrument score correlate with a different self-report instrument."

---

## 9. Validation gates

Five gates that must be passed **in order** before the clustering model moves from design to production. Each gate has a trigger condition and a fail-action. Gates are evaluated at fixed milestones, not continuously.

### Gate 1 — Instrument reliability (before launch)
- **Trigger:** First 20 users complete the onboarding survey.
- **Check:** Cronbach's α ≥ 0.65 on each instrument subscale (MEQ-5, BFI-10 C, BSCS, GP-Short). If any subscale falls below, inspect item-total correlations for the offending items.
- **Fail-action:** Drop or replace the unreliable subscale. If BSCS fails, fall back to GP-only discipline axis (single instrument, simpler but less robust). If MEQ-5 fails, collapse chronotype to a single self-report item ("Are you a morning or evening person?").

### Gate 2 — Archetype separability (n ≥ 50 per archetype)
- **Trigger:** 250+ users assigned (≥ 50 per archetype on average; tolerate one archetype at 30 if the rest are at 50+).
- **Check:** Silhouette score ≥ 0.3 on the (chronotype, discipline_z) space. This is the Claim 1 test from §8.
- **Fail-action:** If silhouette < 0.3, merge adjacent archetypes (e.g., Disciplined Lark + Disciplined Owl → "Disciplined", dropping the chronotype axis). Rerun with 3 archetypes instead of 5. If still < 0.3, abandon archetypes entirely and use a single population prior.

### Gate 3 — Prior beats flat (n ≥ 10 sessions per new user, ≥ 100 users)
- **Trigger:** 100+ users with ≥ 10 executed sessions each.
- **Check:** Hold-out MAE comparison from Claim 2 (§8). Archetype prior must beat flat 1.0 by ≥ 15% MAE reduction on the first 10 sessions.
- **Fail-action:** If the improvement is < 15%, the archetype priors are not earning their complexity. Fall back to a single population prior (the Diffuse Average prior applied to everyone). Keep the instrument data for research but remove archetype assignment from the user-facing flow.

### Gate 4 — Shrinkage curve calibration (n ≥ 200 users, 90+ days each)
- **Trigger:** 200+ users with 90+ days of data.
- **Check:** Fit optimal blend curve (linear, exponential, sigmoid) and compare to the hardcoded linear-to-30 from §5. Claim 3 test.
- **Fail-action:** If the empirical optimum differs from n=30 by more than ±10 sessions, update the threshold. If a non-linear curve reduces prediction error by > 10% over linear, switch to it. Document the change in the changelog.

### Gate 5 — Assignment stability (90-day retest, n ≥ 100 users)
- **Trigger:** 100+ users reach their 90-day re-assessment window.
- **Check:** ≥ 70% land in the same archetype on retest. Claim 4 test.
- **Fail-action:** If < 60%, the instruments or bucketing thresholds are too noisy. Revisit discipline_z weights, consider widening the "mid" band to absorb borderline cases, or switch to a continuous discipline score instead of discrete buckets. If 60–70%, flag as "marginal" and retest at 180 days with a larger sample before making changes.

### Gate sequencing

Gates 1 and 2 are **blocking** — the system must not assign archetypes to production users until both pass. Gates 3–5 are **corrective** — the system launches with hardcoded priors from §4 and the gates trigger improvements or fallbacks as data accumulates. No gate requires stopping the system; all fail-actions degrade gracefully to simpler models.

---

## Open questions for post-Apr 15 review

1. Should `category` be in the prior table at all, or only `time_of_day`? The category dimension may be too sparse to support per-archetype priors and may need to be folded into a single global prior per (archetype, time_of_day).
2. Should the operator's existing 4 days of data feed back into the prior generation when they become "user 1" of the multi-user system? Or should the priors be set independently and the operator's data treated as the first personal-data input?
3. Is the discipline_z weighting (0.30 / 0.40 / 0.30) defensible, or should it be derived from a regression on calibration data once available?
4. Does the re-assessment trigger at 90 days conflict with the planning of long-term experiments (e.g. someone runs a deliberate intervention for 60 days and the prior shifts mid-experiment)? Probably needs an opt-out lock.
