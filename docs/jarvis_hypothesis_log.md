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

*No hypotheses proposed yet — soak window starts when operator initiates first JARVIS discovery chat.*

---

## Promoted

*Phase 3 inference_engine candidates. Empty until first promotion.*

---

## Rejected

*Hallucinated patterns + operator-overfit patterns. Each entry has a one-line reason. Empty until first rejection.*

---

*Owner: Ali. Append-only log. Promotion + rejection decisions made via separate JARVIS chat or direct-edit (must include date and reason).*
