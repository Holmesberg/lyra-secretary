# Heuristic Registry — Lyra Phase 1 magic-for-alpha
**Started:** 2026-04-28
**Operator-locked rule:** every heuristic in this registry must list trigger / intended outcome / metric / owner / sunset condition. New heuristics that don't appear here are protocol violations — they create "invisible superstition software" per operator's warning.

This is a living doc. Each heuristic gets one entry. Status values: `ACTIVE` (shipped + measured), `PROVISIONAL` (drafted, not yet activated), `RETIRED` (sunset triggered, removed).

---

## H1 — Deterministic deadline-binding heuristic (Tier 0)

**Status:** ACTIVE — shipped 2026-04-28 in commit TBD.

**Trigger:** POST /v1/create when no explicit `deadline_id` is supplied AND the user has bindable deadlines (`state ∈ planned|active`, `voided_at IS NULL`).

**Intended outcome:** When the task title clearly references a deadline name (exact phrase match or unambiguous startswith), bind `task.deadline_id` synchronously without waiting for LLM. Reduces perceived latency from 2-4s (LLM warm) to <10ms.

**Mechanism:** `services/deadline_heuristic.py:score_deadlines()`. Returns ranked candidates with score components:
  - `+1.0` exact normalized title match (full title in haystack)
  - `+0.8` haystack startswith deadline title OR single-token title in haystack as word
  - `+0.6` deadline title is substring of haystack (multi-word phrase only)
  - `+0.4` token overlap (post-stopword strip)

**Auto-bind guardrail (4 rules, ALL must pass):**
  1. `top.score >= 0.6`
  2. `top.score - second.score >= 0.2` (uniqueness margin)
  3. `count(c for c in candidates if c.score >= 0.5) <= 1`
  4. NOT brittle: if removing generic tokens (paper, project, task, work, …) drops overlap to ≤2, the match is too generic to auto-bind

**`deadline_match_source` values introduced:**
  - `heuristic_exact_title` — score >= 1.0
  - `heuristic_startswith` — 0.8 <= score < 1.0
  - `heuristic_substring` — 0.6 <= score < 0.8
  - `heuristic_alias` — RESERVED (future user-defined alias table; not populated yet)
  - `heuristic_confirmed` — user accepted a deterministic suggestion; the
    candidate payload retains the scorer-specific source

**Override priority list (operator-locked):**
```
manual_user > heuristic_exact_title > heuristic_confirmed >
user_corrected > heuristic_startswith > heuristic_substring >
parser_auto > null
```

**Metric:** Two SQL queries operator runs weekly:
```sql
-- Auto-bind rate by source
SELECT deadline_match_source, COUNT(*) AS n
FROM task
WHERE deadline_id IS NOT NULL AND voided_at IS NULL
  AND deadline_match_source LIKE 'heuristic_%'
GROUP BY deadline_match_source;

-- Heuristic disagreement rate (LLM proposed an alternative after heuristic bind)
SELECT COUNT(*) AS heuristic_then_llm_alt
FROM task
WHERE deadline_match_source LIKE 'heuristic_%'
  AND llm_alternative_suggestion IS NOT NULL
  AND voided_at IS NULL;
```

**Owner:** operator + this assistant runtime. Threshold tuning (the four constants in `deadline_heuristic.py`) requires operator approval before code change — they are protocol-frozen alongside the source enum extension.

**Sunset condition:**
- If explicit correction/dismissal exceeds 25% of suggested bindings within a rolling 50-task window per user, tighten the brittle floor or minimum score after review.
- If suggestion acceptance is <5% of task creations after a representative alpha window, retire the heuristic rather than replace it with an unvalidated model path.

**Pre-registration footnote:** Rule 14 stratification (MANIFESTO §13) lists
`deadline_match_source ∈ {'user_explicit', 'parser_auto', 'user_corrected'}`.
The deterministic `heuristic_*` values extend that enumeration. Historical
`llm_auto_confirmed` rows remain lineage only. This additive provenance value
does not alter a scoring threshold.

---

## H2 — Retired trust-not-rewrite model enrichment

**Status:** RETIRED 2026-07-11. Historical rows remain lineage only.

**Former trigger:** `llm_enrichment` completed on a task that already had a canonical binding.

**Carried invariant:** Never silently overwrite `task.deadline_id`. Current deterministic suggestions require explicit user confirmation.

**Former mechanism:** Removed direct NIM/Ollama parser and scheduler. Historical `llm_alternative_suggestion` values are retained for export/delete compatibility and do not authorize current UI.

**Metric:**
```sql
-- Switch acceptance rate when LLM proposes alternative
SELECT
  COUNT(*) FILTER (WHERE deadline_match_source = 'user_corrected') AS switched,
  COUNT(*) FILTER (WHERE llm_binding_rejected_at IS NOT NULL) AS kept_current,
  COUNT(*) FILTER (WHERE llm_alternative_suggestion IS NOT NULL) AS still_pending
FROM task
WHERE voided_at IS NULL;
```

**Owner:** operator + assistant runtime. The 0.85 confidence floor for surfacing alternatives is tunable; lower → more chip noise.

**Sunset condition:**
- If alternative-suggestion surface fires on >40% of heuristic-bound tasks for 2 weeks running, the heuristic is mismatching and trust-not-rewrite is becoming chip spam. Either tighten H1 guardrails or raise the alt-suggestion confidence floor to 0.92.
- If switch rate is <10% of fired alternatives, alternatives are noise the user ignores. Either retire the alt-suggestion path entirely or surface only when delta confidence > 0.30.

---

## H3 — Grandfathered onboarding lazy-stamp

**Status:** ACTIVE (hotfix) — shipped 2026-04-28 in commit TBD.

**Trigger:** GET /v1/users/me when `user.onboarding_completed_at IS NULL` AND the user has at least one non-voided task.

**Intended outcome:** Auto-stamp `onboarding_completed_at` to the user's earliest task `created_at` so they bypass the OnboardingFlow gate. Resolves the "WHERE DID THE OLD TASKS GO?" report (2026-04-28 morning) caused by re-enabling the OnboardingFlow gate against existing users whose pre-existing accounts were never stamped.

**Mechanism:** `endpoints/users.py:get_me()`. Lazy backfill: best-effort, errors non-blocking.

**Metric:**
```sql
-- Should approach zero post-deploy
SELECT COUNT(*) AS grandfathered_pending
FROM "user" u
WHERE u.onboarding_completed_at IS NULL
  AND EXISTS (
    SELECT 1 FROM task t
    WHERE t.user_id = u.user_id AND t.voided_at IS NULL
  );
```

**Owner:** operator. Long-term fix is to add a migration that backfills the column in one shot; this lazy-stamp covers the alpha window where users may not all hit /users/me on the same day.

**Sunset condition:** Once `grandfathered_pending` count is 0 and stays 0 for 1 week, the lazy-stamp branch can be removed. Defensive code, low blast radius — sunset is optional, not required.

---

## Reserved slots

| ID | Heuristic | Status |
|---|---|---|
| H4 | Silence heuristics — chip suppression when user rejected ≥2 chips in last hour, active focus streak >25min, >5 surfaces fired today | PROVISIONAL (Phase 1 follow-up) |
| H5 | Ops fallback — queue depth + Ollama latency-driven fallback to regex-only | RETIRED with direct provider runtime 2026-07-11 |
| H6 | Behavioral predictor heuristics — cascade detection, morning-anchor protection | PROVISIONAL (Phase 2) |
| H7 | Trust-recovery cooldown — after wrong prediction, raise confidence threshold for similar surfaces for N hours | PROVISIONAL (Phase 2) |
| H8 | Momentum reinforcement — "2 focused sessions today" / "you recover quickly" copy | PROVISIONAL (Phase 3, gated on funnel data) |

---

## Strategic warning (operator's framing, recorded here)

> "If you add many heuristics without registry + telemetry, you'll create invisible superstition software. Every rule should have: trigger, intended outcome, metric, owner, sunset condition."
>
> "A system with 20 smart heuristics and clean orchestration often outperforms a system with one expensive model and poor timing. For alpha, heuristics may be your real moat."

The bar to add an entry to this registry: the heuristic must be measurable, ownable, and sunset-able. If it can't be retired, it shouldn't be added.
