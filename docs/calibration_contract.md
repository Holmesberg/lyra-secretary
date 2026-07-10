# Calibration Contract

*Doctrine for every reflection surface in Lyra. Gates Phases 1-6 of the 2026-05-02 system transition (`/home/alina/.assistant runtime/plans/alright-listen-up-assistant runtime-delegated-garden.md`). Read before adding any user-facing surface that displays inferred behavior.*

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

**Default tier thresholds (per-user, per-signal, *not* aggregate):**

| Tier | N | Behavior |
|------|---|----------|
| `cold_start` | < 5 | Show "Still learning your patterns." Never the operator-derived prior. |
| `tentative` | 5-29 | Show value with explicit caveat ("provisional, n=12"). |
| `confirmed` | ≥ 30 | Show value with sample size footnote ("from 47 sessions"). |

**Per-signal threshold overrides (R2.1).** Default thresholds protect against operator-overfit at *common-signal* base rates (every pause, every task). High-severity / low-frequency primitives (cascade recovery latency, abandonment-path stability, account-deletion patterns) would never reach `confirmed` under the default — a typical user might experience 30 cascades over a year, trapping the signal in `tentative` indefinitely. Each signal in `inference_engine` MAY declare its own `(cold_start, tentative, confirmed)` thresholds when the default is base-rate-incompatible.

Each non-default threshold MUST include a `base_rate_justification` comment in the signal definition stating: (a) expected per-user-per-month occurrence rate, (b) why the lower threshold doesn't reintroduce operator-overfit risk (typically: severity makes the signal actionable at lower N; or the pattern is structurally robust to single-user variance). Example:

```python
SIGNAL_THRESHOLDS = {
    # default: (5, 30) — common signals
    "cascade_recovery_latency": (3, 10),
    # base_rate_justification: cascades occur ~2-4× per month per active user;
    # n=10 spans ~3 months which is a reasonable operator-overfit horizon. Severity
    # justifies surfacing at lower confidence — recovery latency is more
    # actionable than execution-discrepancy at small n.
    
    "abandonment_path_stability": (5, 15),
    # base_rate_justification: void/reschedule/skip events occur ~5-10× per month;
    # path-preference stability is robust to single-user variance because it's
    # a within-user comparison (does the same user prefer the same path?), not
    # cross-user generalization.
}
```

The threshold table itself lives in `inference_engine.py` and is reviewed during the Phase 3 → 4 gate. Adding a new override post-Phase-3 requires a new commit + operator approval (no in-place edits).

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
- **`event_class` is a top-level NOT NULL column on `reflection_view_log`** (`'telemetry'` | `'impression'`), backed by a btree index. Promoted from JSON payload to column to avoid `NOT LIKE 'telemetry_%'` sequential-scan performance hits as telemetry volume grows. Schema change lands as Phase 1.5 alembic migration before Phase 6 ships. (R7.1)
- Existing VT-21 / stratified-analysis queries change from `WHERE reflection_type NOT LIKE 'telemetry_%'` to `WHERE event_class = 'impression'` — equality on indexed column. One-liner update, documented in the Phase 1.5 migration log.
- Every payload still includes `schema_version: 1` for forward-compat.
- Per-`reflection_type` payload schema documented in `docs/reflection_view_log_schemas.md` (lands with Phase 6). **No write without schema doc.**

## R8 — Operator-overfit guard

Per `feedback_overfit_to_operator_guard` and `feedback_primitives_over_diagnostic_frames`:

- The risk is universalizing operator's specific cognitive topology (high introspection, systems-thinking, instrumentation tolerance, exploratory drive) onto median users who don't share it. NOT a clinical-condition framing.
- `confirmed` tier requires `n ≥ 30` for **the requesting user's own data**, not aggregated across the cohort. Operator's 200+ sessions don't grant non-operator users `confirmed` status on the same signal.
- Phase 2 hypotheses promoted from JARVIS get tagged `operator-only` or `potentially-general` in `docs/archive/legacy/ai/jarvis_hypothesis_log.md`. The tag-decision question: "Is this a behavioral primitive (transition friction, recovery latency, momentum collapse, action/declaration divergence, abandonment topology) — generalizable? OR a topology-specific trait (introspection appetite, archetype fascination, instrumentation tolerance) — operator-only?"
- Only `potentially-general` ships as user-facing reflection.
- Phase 3 → Phase 4 gate: signatures from operator + 2 non-operator trusted users must show *discrimination*, not similarity. Signatures that look identical across the 3 are suspect for operator-overfit; debug before shipping.
- User-facing reflection copy describes *behavior*, not identity. "After distraction pauses you usually resume in 2m" — not "Procrastinators recover slower." Diagnostic categories never reach user surfaces.

## R9 — Valence-aware disagreement resolution

The naive "implicit wins on disagreement" rule breaks at the **flow-state false positive**: overrun + high focus + few pauses is a hyper-focused success state, not a friction failure. The implicit signal (overrun) and the explicit signal (5/5 focus) aren't disagreeing — they're orthogonal. Implicit measures time-vs-plan; explicit measures productivity. Both can be true simultaneously.

**Each task gets a valence classification before any implicit-vs-explicit resolution applies:**

| Valence class | Pattern | Resolution rule |
|---------------|---------|-----------------|
| `friction` | Overrun + low focus (≤2/5) + ≥3 pauses + scope unchanged | **Implicit wins.** Surface as friction signal. Disagreement event logged. |
| `flow` | Overrun + high focus (≥4/5) + ≤1 pause + scope possibly grew | **Explicit wins.** Surface as success signal. The overrun is feature, not bug. No disagreement event. |
| `scope_creep` | Overrun + medium focus (3/5) + scope grew dramatically (≥50% bullet count delta) | **Neither wins.** Per VT-22: this is instrument-confusion territory. Surface as scope-inflation signal, route to scope-density analysis path. Mediation test pre-registered as Manifesto Rule 12. |
| `under_plan` | Underrun + high focus + low pauses | **Both confirm success.** Surface as calibration improvement opportunity ("you finished early"). |
| `neutral` | Within ±15% of plan, focus 3/5, pauses ≤2 | No reflection fires. Calibrated execution is the absence of signal. |

The valence classifier runs in `inference_engine.classify_task_valence()` before applying the action-weight discount (Principle 5). `disagreement_event` is logged ONLY for `friction` valence — not for `flow` or `under_plan` (where both signals agree on outcome) or `scope_creep` (where the disagreement is structural, not behavioral).

**Phase 2 hypothesis proposals carry a `valence_class` tag** so JARVIS-generated patterns are explicit about which class they describe. A "you usually overrun" pattern means very different things depending on whether it's framed as friction (intervention candidate) or flow (status acknowledgment) or scope-creep (planning recalibration target).

When a non-operator user's valence distribution diverges sharply from the operator's (operator runs 70% flow / 20% friction; user runs 70% friction / 5% flow), that's a strong operator-overfit signal — flag for review.

## R10 — Saturation cap

Per `feedback_saturated_posterior_display_cap`: any percentage display caps at 99%. 100% reads as identity assertion, not pattern observation.

## R11 — Latency neutrality (no new round-trips, no blocking writes)

Reflection surfaces are quiet observations the user can ignore. They MUST NOT add latency to the surfaces they decorate. Any reflection that costs the user a wait stops being quiet.

**Read-side rules:**

- Phase 4 reflection surfaces read from **prefetched/cached data**, never from new round-trips. Concrete pattern: extend the `/v1/users/me` response (called once per page load, cached aggressively per `frontend/lib/api.ts`) with the BehavioralSignature subset relevant to the rendering surface. /me is the read-side carrier.
- For per-task reflection lines on `/today`, extend the `/v1/tasks/query` response (already cached) with per-task derived signals computed in the same join. One round-trip carries both the task list and its reflections.
- For modal context lines (reflection-modal, new-task-modal calibration basis), the comparative context comes from the `/me` cache or a parent-component prefetch — **the modal opens immediately**, the context line is already present at first paint.
- The new `/v1/analytics/behavioral_signature` endpoint exists for JARVIS + operator analytics; it is NOT called from user-facing rendering paths.

**Write-side rules:**

- Phase 6 telemetry writes (`telemetry_modal_dwell`, `telemetry_pause_hesitation`, etc.) are **fire-and-forget**. Use `navigator.sendBeacon()` where supported, or `fetch()` with `keepalive: true` and `void` the promise. NEVER `await` a telemetry write before user-visible state transitions.
- Telemetry write failures are non-fatal — silently dropped, never surfaced to user, never block the UI thread.
- Server-side, telemetry endpoint returns `204 No Content` immediately and queues actual ReflectionViewLog write asynchronously (background task or Redis queue). Insertion failure logged for operator review; never bubbles to client.

**Caching:**

- The BehavioralSignature payload has a per-user 5-minute TTL in Redis. Most users won't see the signature change minute-to-minute; the cache absorbs the read load.
- Cache invalidation on: task EXECUTED, pause event, retroactive add, void. Not on every read.

**Verification gate:** any PR landing a Phase 4 surface or Phase 6 telemetry must include a manual smoke check confirming the surface adds <50ms to its host page's render time (measured via Chrome DevTools Performance panel against the pre-PR baseline). Documented in PR description.

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
