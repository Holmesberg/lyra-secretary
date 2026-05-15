# 16 Open Questions

**Purpose:** Preserve uncertainty instead of prematurely resolving it.

## Measurement Questions

1. What exactly does a user's `pre_task_readiness` rating mean after they have
   seen Lyra's explanations for weeks?
2. Does `post_task_reflection` measure perceived focus, satisfaction, relief,
   completion pride, or something else?
3. Can bullet-count growth distinguish real scope expansion from decomposition?
4. What is the minimum evidence required to call a task topology `bounded`?
5. Should biological tasks be excluded from all cognitive calibration or only
   from specific profiles?

## Statistical Questions

1. When should `personal_weight=min(1,n/30)` be retired or reframed?
2. What variance or stationarity metric should replace count-only confidence?
3. Should execution multipliers be modeled in log space everywhere after Cortex?
4. How should long exploratory development sessions be separated from normal
   bounded execution?
5. How should repeated tasks and correlated project phases affect effective
   sample size?

## Causal Questions

1. How can the system distinguish model accuracy from behavior changed by the
   model?
2. What is the right exposure ledger granularity?
3. Can predictions be randomized or withheld ethically to preserve causal tests?
4. Do nudges improve calibration or anchor planned durations?
5. Does reflection copy change self-report scale semantics?

## Product/Research Boundary Questions

1. Which surfaces are measurement instruments and which are interventions?
2. Should user-facing archetype labels survive?
3. Should `flow/friction` remain operator-only?
4. What claims are allowed before trusted-user discrimination is documented?
5. How much UX simplification is acceptable before it destroys signal?

## Repo Governance Questions

1. Should `analytics.py` be split by layer?
2. Should `jarvis_tools.py` be capped and decomposed?
3. Should historical docs get an explicit active/superseded/archive marker?
4. Should notebooks and local `.venv` artifacts remain in repo?
5. Should there be a CI check that every Cortex code change modifies docs?

## Do Not Resolve By Guessing

These questions should remain open until code evidence, data evidence, or
operator decision resolves them.
