# Calibration Contract

*Doctrine for every reflection surface in Lyra. Gates Phases 1-6 of the 2026-05-02 system transition (`/home/alina/.claude/plans/alright-listen-up-claude-delegated-garden.md`). Read before adding any user-facing surface that displays inferred behavior.*

---

## R1 — Comparative context before input

Every modal that captures user input renders **one calibrated comparative line above the input control**. Examples:

- Reflection modal: "Your average focus for `study` is 3.2/5 across 12 sessions"
- Pause modal: "You've paused 3× this session — your average for this category is 1.5×"
- New-task modal: "Based on 18 `dev` sessions; you typically run +14% over plan"
- First-time category: "First time we're seeing `cooking`."

Input without context is data extraction. Per `project_bootstrap_paradox`, every explicit ask must offer comparative return on the same surface.

## R2 — Confidence tier required on every numeric reflection

Every numeric reflection includes (a) sample size, (b) confidence tier ∈ {`cold_start`, `tentative`, `confirmed`}, (c) what's needed to reach the next tier.

Tier thresholds (per-user, per-signal, *not* aggregate):

| Tier | N | Behavior |
|------|---|----------|
| `cold_start` | < 5 | Show "Still learning your patterns." Never the operator-derived prior. |
| `tentative` | 5-29 | Show value with explicit caveat ("provisional, n=12"). |
| `confirmed` | ≥ 30 | Show value with sample size footnote ("from 47 sessions"). |

Generalize the existing `analytics.py:466-499` `_insight_discrepancy_signal` pattern.

## R3 — 60-day unread retirement trigger

Every signal surfaced has a documented retirement trigger inline: "If unread / undisplayed / never-fired for 60 consecutive days, retire the writer per `feedback_inference_quality_over_instrumentation_quantity`." Per-signal counter lives in the inference_engine output, audited at Phase 5.

## R4 — Banned vocabulary + warm tone register

**Banned in user-facing strings** (per `feedback_warm_tone_copy`): `calibration`, `prior`, `predictions`, `battery`, `instrument`, `model`, `inference`, `signal`, `feature`, `metric`.

**Allowed phrasing**: "you usually", "you typically", "we've seen N times", "across N sessions".

**Tone**: warm, descriptive, never clinical. Never identity claims ("you fear structure" / "you're avoiding study"). State observable tendencies with confidence intervals.

## R5 — Retreat under low confidence

Per `feedback_trust_copy_register`: when intelligence surface has insufficient data to fire, render one quiet grey line ("Still learning your patterns.") instead of silence or AI-padding ("analyzing your productivity waveform"). Drop numeric framing at `tentative`. Show "we've noticed" not "we predict" at all tiers.

## R6 — Every reflection writes to ReflectionViewLog

Per `feedback_progressive_revelation_canon`-adjacent: every fired reflection surface (impression OR telemetry) writes a ReflectionViewLog row. View-id stamped at impression; dwell-seconds computed on dismiss. This preserves VT-21 stratified analysis substrate.

## R7 — ReflectionViewLog namespace discipline

Per `feedback_reflection_view_log_namespace`:

- **Telemetry** `reflection_type` values prefix with `telemetry_*` (e.g. `telemetry_pause_hesitation`, `telemetry_modal_dwell`, `telemetry_survey_per_item`).
- **Impressions** unprefixed (`micro_mirror`, `calibration_nudge`, `creation_nudge`, `archetype_proximity`).
- Every payload includes top-level `event_class` (`"telemetry"` or `"impression"`) and `schema_version: 1`.
- Per-`reflection_type` payload schema documented in `docs/reflection_view_log_schemas.md` (lands with Phase 6). **No write without schema doc.**
- Existing VT-21 / stratified-analysis queries add `WHERE reflection_type NOT LIKE 'telemetry_%'`.

## R8 — Operator-overfit guard

Per `feedback_overfit_to_operator_guard` and `feedback_primitives_over_diagnostic_frames`:

- The risk is universalizing operator's specific cognitive topology (high introspection, systems-thinking, instrumentation tolerance, exploratory drive) onto median users who don't share it. NOT a clinical-condition framing.
- `confirmed` tier requires `n ≥ 30` for **the requesting user's own data**, not aggregated across the cohort. Operator's 200+ sessions don't grant non-operator users `confirmed` status on the same signal.
- Phase 2 hypotheses promoted from JARVIS get tagged `operator-only` or `potentially-general` in `docs/jarvis_hypothesis_log.md`. The tag-decision question: "Is this a behavioral primitive (transition friction, recovery latency, momentum collapse, action/declaration divergence, abandonment topology) — generalizable? OR a topology-specific trait (introspection appetite, archetype fascination, instrumentation tolerance) — operator-only?"
- Only `potentially-general` ships as user-facing reflection.
- Phase 3 → Phase 4 gate: signatures from operator + 2 non-operator trusted users must show *discrimination*, not similarity. Signatures that look identical across the 3 are suspect for operator-overfit; debug before shipping.
- User-facing reflection copy describes *behavior*, not identity. "After distraction pauses you usually resume in 2m" — not "Procrastinators recover slower." Diagnostic categories never reach user surfaces.

## R9 — Disagreement logging

When implicit-action signal and explicit-declaration signal disagree on a state estimate, the disagreement is a `disagreement_event` in the BehavioralSignature output. Patterns of disagreement that diverge sharply from the operator's pattern of disagreement = early operator-overfit signal. Surfaces only via JARVIS or `?include_disagreements=true`.

Per Phase 3 Principle 5: when implicit and explicit disagree, **implicit wins**. The disagreement itself is data, not error.

## R10 — Saturation cap

Per `feedback_saturated_posterior_display_cap`: any percentage display caps at 99%. 100% reads as identity assertion, not pattern observation.

---

## Enforcement

This doctrine is the gate for every PR that touches a reflection surface. Before merging:

- [ ] Surface follows R1-R10
- [ ] If new `reflection_type`, schema documented in `docs/reflection_view_log_schemas.md`
- [ ] If telemetry, `telemetry_*` prefix used
- [ ] Cold-start case (`n < 5`) handled per R5
- [ ] Sample size + confidence tier visible per R2
- [ ] No banned vocabulary per R4
- [ ] 60-day retirement trigger documented inline per R3

Violations of this doctrine are higher-severity than feature bugs because they erode the trust substrate that the entire inference layer depends on.

---

*Owner: Ali. Adopted 2026-05-02 with the system transition plan. Amendments require explicit operator approval and update to this file's git history (no in-place rewrites of past rules).*
