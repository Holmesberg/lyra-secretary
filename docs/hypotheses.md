# Research Hypotheses

Index of working hypotheses driving Lyra's research layer. H1 (the
discrepancy → delta pre-registered kill criterion) lives in
`MANIFESTO.md §Kill Criterion — H1` and is not duplicated here.
Subsequent hypotheses — unvalidated theories surfaced from dogfood,
interviews, or literature — are recorded below with their predictions,
status, and test design so they can be revisited when data is
sufficient.

---

## H4 — Motivated Underestimation Hypothesis

**Origin:** Form A respondent #3, April 9 2026.

**Claim:** People underestimate task duration not (only) because of cognitive
bias, but because the underestimate itself produces a small reward. The
optimistic plan feels good in the moment of planning, and finishing a task
"early" against an unrealistic estimate generates a dopamine hit that
finishing on time against a realistic estimate does not.

**Implication for Lyra:** The calibration nudge ("you always underestimate
coding tasks by 40% in the afternoon") may face emotional resistance even
when users intellectually accept it. Removing the underestimation removes
the reward source. This is a feature-level risk, not just a UX risk:
"accurate estimation" may be less desirable than "estimation that feels
ambitious."

**Predictions if true:**
- Users who score high on optimism / reward-sensitivity (BFI Extraversion
  facet, or BAS-Drive subscale) will resist calibration nudges more than
  others
- Sessions where executed_duration < planned_duration will correlate with
  higher post_task_reflection scores than sessions where
  executed_duration ≈ planned_duration, even when controlling for delta
- Users will silently inflate their plans over time after seeing the
  calibration nudge — preserving the gap rather than closing it

**Predictions if false:**
- No correlation between underrun and reflection score
- Users adopt calibrated estimates and plan satisfaction is unchanged
  or higher

**Status:** UNVALIDATED — n=1 anecdotal, no data yet. Do not act on
this hypothesis in product decisions until at least 5 more respondents
independently surface the same theme, OR until 30+ paired sessions per
user exist to test the underrun-vs-reflection prediction.

**Relationship to H1:** Independent. H1 (signed_discrepancy → delta) is
about metacognitive accuracy. H4 is about motivated cognition driving
the inaccuracy in the first place. Both could be true, both could be
false, or one could be true and the other false. Test separately.

**Test design (post-Phase 10, when n is sufficient):**
1. For each user with ≥30 paired sessions, compute Spearman correlation
   between (planned_duration - executed_duration) — i.e. underrun
   magnitude — and post_task_reflection score, controlling for category
   and time-of-day
2. Positive correlation = H4 supported (underrun feels good)
3. After calibration nudge ships in production, compare bias_factor
   trajectories: do users converge on accurate estimates, or do they
   inflate their plans to preserve the underrun reward?
