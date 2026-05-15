# MANIFESTO Alignment Audit — Magic-for-Alpha Plan
**Date:** 2026-04-28
**Scope:** Cross-checked the 3-commit magic-for-alpha plan (W1-frontend + Tier chip + P0 fixes + funnel + onboarding revive; W2 resume prediction; W3 task-end prediction + Rule 18) against MANIFESTO v1.15 (1282 lines, Rules 1–17, VTs 1–27, H3 signatures S1–S5).

**Operator instruction (Apr 28 03:50 ish):** "if any misalignments flag them without stopping I'll read them and report back if anything is serious."

This document captures the integrity items so the implementation commits can fold them in cleanly.

---

## P0 — Substantive amendments needed in commit messages

### 1. Rule 13 amendment required in W3 commit (Rule 18 ⊥ Rule 13)
**Issue:** Rule 13's "Protocol violations (require new pre-registration before change)" list explicitly includes:
> *"Changing the filter criteria that define `n_sessions_in_cell`"*

W3's Rule 18 contamination filter adds `Task.stopped_within_5min_of_task_end_ping = FALSE` to the bias_factor cascade query. This **is** a change to `n_sessions_in_cell` filter criteria.

**Resolution:** Rule 18 must explicitly state it amends Rule 13's `n_sessions_in_cell` definition. The amendment is permitted because (a) it's documented + dated, (b) tied to a new pre-registered rule (Rule 18) with its own kill criterion at ≥30%, (c) it protects measurement integrity from a NEW contamination source — the structural-invariant pattern from `docs/design_patterns/rules_vs_agency.md`. Bump v1.15 → v1.16.

**Where:** MANIFESTO.md Rule 18 body, plus a one-line note in Rule 13's "Freedoms preserved" section pointing forward to Rule 18.

---

### 2. Rule 14 stratification extension (already shipped in bed7010 — needs retroactive doc)
**Issue:** Rule 14 stratification enumerates `task.deadline_match_source ∈ {'user_explicit', 'parser_auto', 'user_corrected'}`. Commit `bed7010` introduced a new value `'llm_auto_confirmed'` without documenting the Rule 14 extension.

**Severity:** Not a protocol violation — Rule 14's frozen items are the kill threshold (p ≥ 0.05) and the H2 ρ formula, not the strata enumeration. Adding a stratum reflects a new mechanism type, which is permissible. But it should be on record.

**Resolution:** Document in C1 commit message: "Rule 14 stratification now includes `'llm_auto_confirmed'` as a new value, retroactively documenting bed7010's introduction. The kill threshold (p ≥ 0.05) and H2 ρ formula are unchanged." Add a one-line amendment to MANIFESTO Rule 14.

**Where:** MANIFESTO.md Rule 14, dated note. C1 commit message body.

---

### 3. Rule 11 stratification: include `reflection_type='llm_enrichment_chip'`
**Issue:** Rule 11 says *"all post-nudge-deployment H1 analysis is stratified by nudge-exposure status at the session level (surface-fired vs surface-suppressed), using the `reflection_view_log` shipped in LYR-098 Commit 2b as the authoritative exposure flag."*

The new chip is an intelligence surface that could plausibly influence subsequent `planned_duration_minutes`. The plan correctly writes a `reflection_view_log` row per chip impression — but the H1 stratification logic in operator notebook needs to know that `reflection_type='llm_enrichment_chip'` should be added to the exposure flag set alongside `micro_mirror`, `calibration_nudge`, `archetype_proximity`, etc.

**Resolution:** No code change needed — `reflection_view_log` already has the row. Document the addition in MANIFESTO Rule 11 amendment + C1 commit message: "Rule 11 stratification extended: chip impressions (`reflection_type='llm_enrichment_chip'`) join existing exposure types. Notebook aggregations updated to include this type."

**Where:** MANIFESTO Rule 11 dated amendment. Operator-side notebook update.

---

## P1 — Bake into commit message + code comment

### 4. VT-17 sibling for resume prediction (W2)
**Issue:** Resume prediction is structurally a sibling of pause prediction. VT-17's instrument-intervention threats (anchor drift, induced behavior) apply symmetrically — a "you usually resume by now" banner could induce premature resumption.

**Severity:** Not a current violation — sample sizes haven't crossed VT-17a/b/c thresholds for any user. But if I ship resume_predictor without naming the threat, the analyst layer might silently treat the data as clean.

**Resolution:** Add to `resume_predictor.py` docstring + C2 commit message: *"Resume prediction is a sibling of pause prediction (VT-17); same instrument-intervention threats apply (anchor drift, induced behavior). When `resume_prediction_log` accumulates n ≥ 30 firings per user, run VT-17a/b parallel analysis with pause→resume substitution. No new MANIFESTO rule yet (sample-size threshold not crossed). Document the contamination concern explicitly so it cannot be silently accepted later."*

**Where:** `resume_predictor.py` module docstring. C2 commit body.

---

### 5. Commit 4 identity-reinforcement layer constraint
**Issue:** Per VT-25 / Rule 17 §25a, archetype-derived identity copy is a contamination vector. The operator's plan for the C4 identity layer mentions "2 focused sessions today" (visible behavioral signal — fine) but if anyone later draws from `archetype_assignment` or `RESEARCH_PRIORS` to generate copy, that's a §25a contamination.

**Severity:** Forward-looking guard. Not a current violation.

**Resolution:** Code-level comment in C4 (when it ships) at the copy-generation site: *"Identity-reinforcement copy MUST use only directly observable behavioral signals (executed_at, executed_duration_minutes, time-of-day, session count). Drawing from archetype_assignment, bias_factor, or RESEARCH_PRIORS contaminates Rule 17 §25a. Adding archetype-derived copy requires a new pre-registered amendment to Rule 17."*

**Where:** Future C4 implementation. Note added to plan file now.

---

## P2 — Code comment only

### 6. `scope_estimate_minutes` future-proofing (W1 already shipped)
**Issue:** The LLM extracts `scope_estimate_minutes` per Pydantic schema. If anyone later adds a chip that surfaces this field as a planned-duration suggestion ("LLM thinks ~95min"), it's a direct `calibration_nudge` analog and Rule 11 + VT-21 apply.

**Severity:** Not currently surfaced anywhere. Forward-looking guard.

**Resolution:** Add a comment near the LlmParseResult Pydantic model in `llm_parser.py`: *"DO NOT surface `scope_estimate_minutes` as a user-visible chip or suggestion without first amending Rule 11 stratification + Rule 12 mediation test. The field is audit-only at present."*

**Where:** `llm_parser.py` near schema definition.

---

### 7. Funnel endpoint VT-15/VT-16 caveat
**Issue:** The new `/v1/analytics/alpha_funnel` endpoint reports retention metrics. Per VT-15 (anonymized retention trust-correlated bias) and VT-16 (cross-population methodology error), retention findings must be tagged as Population 2 (product research) data, not Population 1 (H1 hypothesis research).

**Severity:** Documentation only.

**Resolution:** Endpoint module docstring notes: *"This endpoint reports retention/funnel metrics. Per VT-15, opt-out rate must be reported alongside any aggregate finding. Per VT-16, this is Population 2 (product research) data, NOT Population 1 (H1 hypothesis research). Cross-population contamination is forbidden — do not feed funnel statistics into H1 correlation analyses."*

**Where:** `analytics.py` endpoint module docstring near alpha_funnel function.

---

## Summary by commit

| Commit | Items to fold in |
|---|---|
| C1 (W1-frontend + funnel + chip + P0) | #2 (Rule 14 retro-doc), #3 (Rule 11 amendment), #6 (scope_estimate comment), #7 (funnel docstring) |
| C2 (W2 Resume) | #4 (VT-17 sibling note in service docstring + commit body) |
| C3 (W3 Task-end + Rule 18) | #1 (Rule 13 amendment via Rule 18 cross-reference, v1.16 bump) |
| C4 (Identity layer, deferred) | #5 (copy-generation guard comment) |

## What this audit confirms is FINE

- LLM separates `llm_*` columns from canonical `deadline_id` / `priority` — correct per Rule 13/14 spirit (audit trail preserved, canonical fields user-controlled)
- `Task.scope_bullet_count_at_plan` continues to be regex output, `llm_sub_items` is separate — Rule 12 amendment (v1.12) compliant
- Tier 3 quiet "Still learning" copy is observational, not directive — Rule 11 stratification handles it via `reflection_view_log`
- Onboarding revive does NOT add synchronous Ollama calls to critical path — `enrichment-not-critical-path` invariant preserved
- Brain-dump LLM extraction in onboarding does NOT auto-bind deadlines — chip flow handles binding via user accept
- External Data Exclusion Rule untouched (LLM doesn't create from external sources, only enriches Lyra-native tasks)
- Rule 16 deadline soft-warning RCT remains INACTIVE — chip is binding UX, not misalignment warning

## Items NOT requiring amendment

- H3 signatures S1–S5 are all PROVISIONAL with thresholds far from current data; no ship-time impact
- VT-22 scope inflation mediation test continues on `scope_bullet_count_at_plan` (regex), not `llm_sub_items` (separate audit column)
- VT-17d retroactive confirmation: pause-only mechanism, doesn't apply to chip flow

---

**Audit author:** assistant runtime (Opus 4.7) at 2026-04-28 04:00 ish.
**Operator review:** "if any misalignments flag them without stopping I'll read them and report back if anything is serious." Items 1–7 are flagged in this doc for async review. Items will be folded into commit messages as I work; if any need pulling back, operator will say so.
