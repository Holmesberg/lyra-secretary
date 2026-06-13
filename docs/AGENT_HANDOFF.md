# Agent handoff — Lyra Secretary

**Purpose:** Onboarding for any autonomous or agentic AI (editor agent, Copilot, agent runtime, etc.). Read this **before** editing code or docs. Cross-check claims against the repo; docs sometimes lag.

**Last updated:** 2026-05-03 — gates mirrored in **`agent bootstrap doc` → System transition — rigorous gates** (replace date when you materially change reality).

---

## 1. What this project is (non-negotiable framing)

- **Not** a generic todo/productivity app.
- **Behavioral inference engine** with scheduling/timer UX as the interaction surface.
- **Thesis:** measured behavior (especially **implicit** action — pauses, dwell, abandonment paths, timing) must eventually outweigh **declarative** self-report when they conflict, after **calibration** and **confidence** discipline — see `docs/calibration_contract.md` and Principle 5 in the May 2026 transition narrative (`agent bootstrap doc`).
- **Research as QC for the product** (`MANIFESTO.md`): pre-registration, validity, kill criteria — papers are a side effect; trust in surfaced reflections is the goal.
- **Operator-only LLM discovery vs rule-based user-facing inference:** JARVIS (operator) proposes hypotheses; promoted patterns ship as **deterministic math** for everyone else. Integrity stance: **403** for non-operator JARVIS — see `backend/app/api/v1/endpoints/jarvis.py`.

---

## 2. Two planning tracks (reconcile, don’t collapse)

| Track | Canonical files | Role |
|--------|-----------------|------|
| **Product / alpha roadmap** | `docs/building_phases.md` | Tiered shipping (retention surfaces first), Phase 4.5 → alpha → retention checkpoints. **Last updated date in file may predate May 2026.** |
| **May 2026 system transition (“cortex depth”)** | `agent bootstrap doc`, `docs/calibration_contract.md`, `archive/docs_history/data_utilization_inventory_2026_05_02.md`, `docs/jarvis_hypothesis_log.md` | Phases 0–6: calibration → inventory → **JARVIS soak** → inference engine → reflection surfaces → dark-column retirement → top-7 telemetry |

**Both are real.** Product work (Tier 1 surfaces, bugs) can proceed in parallel with transition phases. **Do not** assume “Phase 4.5” and “Phase 2 JARVIS” are the same numbering system.

**Action for you:** If you change phase semantics, update **`docs/building_phases.md` header** or add a short **`docs/current_transition_state.md`** linking both — eliminate dual-authority confusion.

---

## 3. Where the transition stands (verify in repo)

Check these **facts** on checkout:

| Transition phase | Intended gate | Verify |
|------------------|---------------|--------|
| **0 — Calibration doctrine** | `docs/calibration_contract.md` exists, used as gate for UI | Read R1–R11 |
| **1 — Data utilization inventory** | Operator sign-off in inventory doc §7 | `archive/docs_history/data_utilization_inventory_2026_05_02.md` |
| **2 — JARVIS discovery soak** | ≥3 **PROMOTED** + ≥2 **REJECTED** hypotheses with real discrimination | `docs/jarvis_hypothesis_log.md` |
| **3 — Inference engine** | Valence + tiers in code; full user-facing writers TBD | **`backend/app/services/inference_engine.py`** — valence, disagreement, R2 tiers; expand only with `docs/inference_engine_architecture.md` |
| **4+** | Surfaces, retirement, telemetry | Per transition doc; follow **`agent bootstrap doc` → System transition — rigorous gates** before merging reflection work |

**Inference engine:** `inference_engine.py` exists (shared classification math). **Rigorous gates** for every phase live in **`agent bootstrap doc` (System transition — rigorous gates)** — do not skip.

**JARVIS tools (backend):** `backend/app/services/jarvis_tools.py` — includes `analyze_behavioral_signature`, `query_dark_columns`, `propose_pattern_hypothesis` among read tools; write tools are separate. Tests: `backend/tests/test_jarvis_phase2_discovery_tools.py`, `test_jarvis_endpoints.py`.

**Frontend:** There is **no** ubiquitous `behavioral_signature` string — user-facing reflection likely rides **enriched existing responses** (`/me`, stop/create payloads) per calibration contract **latency / no speculative round-trip** discipline. Confirm in `docs/calibration_contract.md` (e.g. R11) before adding N new API calls.

---

## 4. Doc/code drift to watch

- **`docs/building_phases.md`** may still say “Phase 4.5 active” from April 2026 while May transition docs describe JARVIS/inference — **update explicitly** when you touch either.
- **`archive/docs_history/complexity_stress_test_2026_05_01.md`** — early sections push kill/substrate reduction; **read the 2026-05-02 postscript** for the reframe (utilization > raw complexity; JARVIS discovery kept).
- **`agent bootstrap doc` table count vs audits** — assistant runtime may list a subset; migrations evolve — trust `alembic/versions/` + `models.py` for truth.
- **Missing / partial docs:** `docs/inference_engine_architecture.md` (**DRAFT** — Phase C landed); still missing: `docs/dark_column_retirement_log.md`, `docs/reflection_view_log_schemas.md` — create or trim references when touched.

---

## 5. What to do next (ordered)

### A. Documentation hygiene (high leverage, low risk)

1. Add **`docs/current_transition_state.md`** (one page): date, active transition phase, product phase pointer, **next hard gate**.
2. Stub **`docs/inference_engine_architecture.md`** as **DRAFT** placeholder **or** implement Phase 3 and write the real doc in the same PR.
3. Grep for stale links to old handoff filenames and point them at **`docs/AGENT_HANDOFF.md`**.

### B. Phase 2 completion (blocks Phase 3)

1. Use JARVIS against **operator** data only; record outcomes in **`docs/jarvis_hypothesis_log.md`**.
2. Meet gate: **≥3 promoted**, **≥2 rejected** hypotheses (rejections must be substantive — proves the loop can say “no”).
3. Keep **`pytest`** green for JARVIS tests; Python **3.11** venv recommended (`backend/requirements.txt`); `PYTHONPATH` = backend root when running tests from `backend/tests/`.

### C. Phase 3 (only after B)

1. **`inference_engine.py` exists** — extend with new writers / **`GET`** analytics only per **`docs/inference_engine_architecture.md`** (land or update in the same PR).
2. **No** Bayesian DL stacks, **no** new tables for core loop if transition anti-step-10 fence still applies — reuse existing tables + `ReflectionViewLog` patterns unless operator expands scope.

### D. Phase 4 surfaces

1. Every surface obeys **`docs/calibration_contract.md`** (comparative line, tier, banned vocabulary, ReflectionViewLog).
2. Prefer **payload enrichment** over many new blocking client calls unless R11 explicitly allows.

---

## 6. Verification commands (local)

```bash
# Backend tests (from repo root, adjust venv)
cd backend
set PYTHONPATH=.   # Windows: $env:PYTHONPATH="."
pytest tests/test_jarvis_phase2_discovery_tools.py tests/test_jarvis_endpoints.py -q

# Diagrams (optional)
pip install matplotlib
python docs/diagrams/generate_diagrams.py
```

Docker and frontend workflows: **`agent bootstrap doc`** Commands section.

---

## 7. Hard limits (check before shipping)

- **`docs/do_not_add.md`** — gamification bans, auto-duration traps, etc.
- **`docs/design_patterns/structural_investigation_rule.md`** — features touching measurement.
- **Multi-tenant isolation** — JARVIS and analytics must stay operator-scoped where required; see existing tests and `ContextVar` patterns in backend.
- **Commit discipline:** meaningful chunks, verify gates operator uses (`CONTRIBUTING.md`, CI).
- **Git mutation confirmation:** before any `commit`, `push`, `pull`,
  `merge`, `rebase`, `stash`, or branch switch, state the current branch,
  name the exact change bucket, list the exact command, and wait for operator
  confirmation.
- **Pre-final git hygiene:** before the final response, run
  `.\scripts\git_hygiene_summary.ps1` and report dirty worktree status,
  intentionally changed files, unrelated dirty files, verification, and
  whether anything was committed/pushed.

---

## 8. Quick file map

| Area | Paths |
|------|--------|
| API entry | `backend/app/main.py`, `backend/app/api/v1/router.py` |
| Task truth | `backend/app/services/task_manager.py`, `state_machine.py` |
| JARVIS | `jarvis_tools.py`, `jarvis_agent.py`, `endpoints/jarvis.py` |
| Reflection logging | `reflection_view_log` model, endpoints that stamp view/dismiss |
| Frontend | `frontend/` — Next.js; production serve notes in `agent bootstrap doc` |
| Doctrine | `MANIFESTO.md`, `docs/calibration_contract.md` |

---

## 9. Handoff checklist for the next agent

- [ ] Read `agent bootstrap doc` (**including System transition — rigorous gates**) + `docs/calibration_contract.md` end-to-end.
- [ ] Read `docs/jarvis_hypothesis_log.md` — confirm Phase 2 gate (PROMOTED/REJECTED counts).
- [ ] Confirm `backend/app/services/inference_engine.py` and follow **agent bootstrap doc** gates before expanding inference.
- [ ] Run JARVIS-related pytest slice.
- [ ] Run `.\scripts\git_hygiene_summary.ps1` before final handoff and separate your changes from pre-existing dirty state.
- [ ] Only then implement Phase 3 expansion or Phase 4 surfaces.

When you finish a major milestone, **update the “Last updated” line at top** and **§3 table** so the next agent inherits truth.
