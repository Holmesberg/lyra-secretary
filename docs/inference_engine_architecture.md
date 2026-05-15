# Inference engine architecture (DRAFT)

**Status:** DRAFT — Phase 3 transition doc. Amend via git history; keep aligned with `backend/app/services/inference_engine.py` and `docs/calibration_contract.md`.

---

## 1. Purpose

The **inference engine** is the shared layer between:

- **Operator discovery** (JARVIS tools, scripts, dashboards), and  
- **Future user-facing calibration** (prefetched payloads on `/v1/users/me` and `/v1/tasks/query` per R11 — **not** implemented in this draft’s scope).

It centralizes **classification math** (valence, disagreement, confidence tiers) so JARVIS aggregations, analytics HTTP surfaces, and later UI carriers do not diverge.

---

## 2. Code layout (current)

| Module | Responsibility |
|--------|----------------|
| `backend/app/services/inference_engine.py` | `classify_task_valence`, `classify_disagreement`, `confidence_tier_from_n`, `SIGNAL_THRESHOLDS`, `behavioral_signature_for_operator` |
| `backend/app/services/jarvis_tools.py` | JARVIS executors; imports inference primitives for valence inside `analyze_behavioral_signature` |
| `backend/app/api/v1/endpoints/analytics.py` | `GET /v1/analytics/behavioral_signature` — **403** unless `User.is_operator` |

**Rule:** Any new classification that affects user trust must live in `inference_engine.py` (or call it), not only inside JARVIS.

---

## 3. HTTP: behavioral signature (operator-only)

- **Route:** `GET /v1/analytics/behavioral_signature?window_days=14`  
- **Auth:** Same as other analytics — scoped user + **`is_operator=True`** or **403**.  
- **Payload:** Identical aggregate dict to JARVIS `analyze_behavioral_signature` (`_exec_analyze_behavioral_signature`). Includes pause distributions, valence counts, reflection engagement summaries, disagreement events, etc.  
- **R11:** This endpoint is **forbidden** on user-facing first-paint paths. Operators may poll it for dashboards; the Web UI Today/Insights pages must **not** add blocking calls here.

---

## 4. Signal registry (aggregate keys)

The behavioral signature dict is the **Phase 2 discovery substrate**; keys evolve with `jarvis_tools._exec_analyze_behavioral_signature`. Canonical list is enforced by **`backend/tests/test_jarvis_phase2_discovery_tools.py`** (cold start + populated fixtures). At minimum, expect:

- `window_days`, `n_sessions`, `n_pause_events`  
- `pause_distribution`, `valence_distribution`, `valence_preconditions`  
- `disagreement_events`, `reflection_engagement`  
- Coverage / confidence helper fields as tested

Per-signal **R2** tiers for surfaced copy will be documented here when Phase 4 carriers ship; until then, tiers apply to **wording** in insights generators, not this raw aggregate.

---

## 5. Phase gates (rigorous)

| Gate | Requirement |
|------|-------------|
| Phase 2 → 3 | `docs/jarvis_hypothesis_log.md` — ≥3 PROMOTED + ≥2 REJECTED (`agent bootstrap doc`) |
| Phase 3 expansion | This doc updated in the **same PR** as new inference outputs or new aggregate fields |
| Phase 3 → 4 (R8) | Operator + 2 trusted users show **discrimination** before cohort-facing copy from promoted hypotheses |
| Phase 4+ | `docs/calibration_contract.md` Enforcement checklist on every reflection PR |

---

## 6. Non-goals (this phase)

- No new Postgres tables for the core loop without operator expansion of scope.  
- No Bayesian deep-learning stack.  
- No non-operator exposure of JARVIS or raw signature JSON in the Web UI without R8 + R11 design review.

---

*Owner: Ali. Created 2026-03-29 as Phase C / Phase 3 documentation anchor.*
