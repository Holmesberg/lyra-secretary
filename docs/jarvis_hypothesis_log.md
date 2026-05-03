# JARVIS Hypothesis Log

*Phase 2 of the 2026-05-02 system transition (`/home/alina/.claude/plans/alright-listen-up-claude-delegated-garden.md`).*

JARVIS-on-operator-data discovery layer. Operator chats with JARVIS; JARVIS uses `analyze_behavioral_signature` + `query_dark_columns` + `propose_pattern_hypothesis` tools to surface candidate patterns from operator's behavioral history. Each proposed hypothesis lands in this log with status `PROPOSED`. Operator validates against lived experience and either promotes (→ Phase 3 inference engine) or rejects (with one-line reason).

**Soak window:** 2026-05-02 → 2026-05-16 minimum.

**Promotion criteria (Phase 2 → Phase 3):**
1. Operator validation that the pattern matches lived experience
2. Pattern can be re-derived by rule-based math from existing tables (no new schema)
3. `generality_tag = potentially-general` (operator-only patterns stay in JARVIS sandbox)

**Phase 3 gate:** at least 3 PROMOTED + at least 2 REJECTED hypotheses, with the failure case demonstrating the system has discrimination.

---

## Format

Each hypothesis lands as a section. Append-only; never edit prior hypothesis content (re-state with a new entry if a finding changes).

```markdown
## H-N — short title

- **Proposed:** YYYY-MM-DD via JARVIS chat
- **Observation:** [JARVIS-generated, citing tool output numbers]
- **Signals used:** [list]
- **Predicted outcome:** [JARVIS]
- **Falsifier:** [JARVIS]
- **Generality tag:** operator-only | potentially-general
- **Valence class:** friction | flow | scope_creep | under_plan | neutral
- **Sample size at proposal:** n=X, confidence='tentative' | 'confirmed'
- **Status:** PROPOSED → PROMOTED (date, encoding plan) | REJECTED (date, reason)
```

---

## Starter prompts (seed the soak window)

These are operator-prompts to seed JARVIS chat sessions. Each surfaces a category of pattern from a different angle.

1. **Onboarding fingerprint:** "Looking at my onboarding — integration-connect order, skipped steps, archetype-survey response patterns — what does that predict about my execution style? Falsifiable how?"

2. **Action vs declaration alignment:** "Where do my explicit ratings (readiness, focus) most disagree with my implicit behavior (pause frequency, abandonment, completion %)? When they disagree, which one tracks outcomes better?"

3. **Transition causality:** "Map the pause-resume-next-task graph. After distraction pauses, what category do I switch to? Does the switch-to category correlate with same-day cascade probability?"

4. **Behavioral exhaust:** "Beyond the canonical metrics — what implicit choices in my data (integration retry patterns, modal abandonment, schedule volatility, reschedule chains) carry signal that the rule-based math doesn't currently use?"

5. **Rebound dynamics:** "After a high-discrepancy task (signed_discrepancy ≥ 2), what's my next-task behavior? Recovery, cascade, or unchanged?"

6. **Identity-internalization risk:** "Is there evidence in my data that I'm self-fulfilling the Procrastinator archetype reveal vs evidence I'm exhibiting it independently of the reveal?"

7. **task_switch differential (post-2026-05-02 surface):** "Now that task_switch is exposed in the pause picker, does my behavior on operator-attributed task_switch pauses look different from system-attributed ones (from /v1/stopwatch/switch)?"

---

## Proposed (active)

## H-1 — Optimism Collapse in Academic Tasks

- **Proposed:** 2026-05-02 via JARVIS chat
- **Observation:** When your explicit ratings show "optimism collapse" (felt sharp before, executed poorly), 50% of these events (2 out of 4) occur in the "academic" category.
- **Signals used:** [disagreement_events]
- **Predicted outcome:** High readiness ratings before an academic task paradoxically predict a higher risk of poor execution (friction) than in other categories.
- **Falsifier:** Over the next 14 days, optimism_collapse events distribute evenly across categories rather than clustering in "academic".
- **Generality tag:** operator-only
- **Valence class:** friction
- **Sample size at proposal:** n=4, confidence='tentative'
- **Status:** PROPOSED

## H-2 — Intentional Breaks as Development Bridges

- **Proposed:** 2026-05-02 via JARVIS chat
- **Observation:** After an `intentional_break`, you overwhelmingly switch to "development" tasks (n=23) compared to "academic" (n=10) or "study" (n=5).
- **Signals used:** [post_pause_transitions]
- **Predicted outcome:** Intentional breaks serve specifically as cognitive resets before development work, rather than general rest periods.
- **Falsifier:** In the next 14 days, post-break transitions distribute proportionally to your baseline category execution frequency.
- **Generality tag:** operator-only
- **Valence class:** neutral
- **Sample size at proposal:** n=23, confidence='confirmed'
- **Status:** PROPOSED

## H-3 — Front-Loaded Planning Friction

- **Proposed:** 2026-05-02 via JARVIS chat
- **Observation:** You exhibit massive hesitation between task creation and planned start (p75 = 194.98 mins), but almost zero execution friction once the plan is set (planned-to-executed p75 = 1.89 mins).
- **Signals used:** [hesitation_chain]
- **Predicted outcome:** Behavioral interventions targeting "getting started on a planned task" will yield no improvement; the friction is entirely contained in the planning-commitment phase.
- **Falsifier:** Over the next 14 days, `planned_to_executed_start_minutes` p50 rises above 5 minutes.
- **Generality tag:** potentially-general
- **Valence class:** neutral
- **Sample size at proposal:** n=77, confidence='confirmed'
- **Status:** PROPOSED

## H-4 — Incomplete planning before deadline (May 2 dogfood primitive)

- **Proposed:** 2026-03-29 (doc + inventory sync; operator to validate with `query_dark_columns` + lived experience)
- **Observation:** Tasks with a bound deadline sometimes reach the due instant with a thin or empty composed description / scope — **declared urgency without planning depth** (priority mismeasurement).
- **Signals used:** `deadline_id`, `Deadline.due_at_utc`, `Task.description`, `scope_bullet_count_at_plan`, `Task.last_modified_at` (proxy); future boundary telemetry at `due_at_utc` per `docs/data_utilization_inventory_2026_05_02.md` Revision 2.
- **Predicted outcome:** Stricter description-incomplete cases correlate with different skip / friction / reschedule outcomes than fully planned-before-deadline tasks.
- **Falsifier:** No outcome or valence split once n is sufficient and proxy or telemetry definition is frozen.
- **Generality tag:** potentially-general
- **Valence class:** neutral
- **Sample size at proposal:** n=TBD (run column stats after proxy definition)
- **Status:** PROPOSED

---

## Phase 2 → 3 gate machine (automated doc snapshot)

| Requirement | Count |
|-------------|-------|
| PROMOTED (operator-validated, encoding-ready) | **0** |
| REJECTED (discrimination demonstrated) | **0** |
| PROPOSED (active) | **4** (H-1 … H-4) |

The Phase 3 gate (**≥3 PROMOTED + ≥2 REJECTED**) requires **operator decisions** in chat or dated edits — not inference from this file alone.

---

## Promoted

*Phase 3 inference_engine candidates. Empty until first promotion.*

---

## Rejected

*Hallucinated patterns + operator-overfit patterns. Each entry has a one-line reason. Empty until first rejection.*

---

*Owner: Ali. Append-only log. Promotion + rejection decisions made via separate JARVIS chat or direct-edit (must include date and reason).*
