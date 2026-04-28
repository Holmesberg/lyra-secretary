> **ARCHIVED 2026-04-29.** Apr 17 sprint queue — items shipped or rolled forward into the post-Apr-28 alpha-launch plan. Successor planning lives in `docs/feedback_loops_closure_plan.md` + the operator's current sprint plan. Kept for the order-of-execution rationale; do not edit.

# Apr 17 Tier 1 execution queue

**Prepared:** April 16, 2026 evening (autonomous session while operator offline).
**Status:** Ready for tomorrow's rapid-execution window. Each item below is
investigation-complete — tomorrow's work is implementation + browser verify.

## Recommended execution order (high leverage first, easiest-to-verify last)

1. **Calibration nudge at creation (D3)** — 45–75 min
2. **Pause response banner (Web UI)** — 45–60 min
3. **/insights tab v1 fill-in** — 60–90 min

Retroactive modal queued separately (operator listed it in the overall queue
but wasn't in tonight's batch). Ordering rationale: creation nudge has the
highest per-session leverage for retention (user course-corrects *before*
committing time to a wrong estimate); pause response banner is VT-17
experimental mechanism; /insights is the lowest-frequency surface.

---

## Item 1 — Calibration nudge at task creation (D3)

### Backend readiness: ✅ endpoint exists

`GET /v1/analytics/bias_factor` (`backend/app/api/v1/endpoints/analytics.py`)
returns per (category × time_of_day) cells. Each cell has:

```
{
  "category": "dev",
  "time_of_day": "afternoon",
  "bias_factor": 1.42,        // sum(executed)/sum(planned), PRIMARY
  "bias_factor_mean": 1.38,   // sanity check (per-session avg)
  "sessions": 12,
  "confidence": "medium",
  "interpretation": "underestimates"
}
```

Plus fallbacks: `category_only`, `time_of_day_only`, `global`. The `min_sessions`
query param (default 3, up to 50) gates which cells appear.

### Fire condition (dogfood spec)

- `bias_factor >= 1.25` (user consistently underestimates)
- AND `sessions >= 10` in the (category, time_of_day) cell

### Tomorrow's implementation steps

1. **Add a lightweight lookup endpoint** (recommended but optional) —
   `GET /v1/analytics/bias_factor/lookup?category=X&tod=Y` returning a single
   cell. Frontend could filter the full response instead; the lookup endpoint
   is cleaner and avoids shipping all cells to every modal open. ~20 LOC
   backend. Same `_bias_cell` helper.

2. **Modify `new-task-modal.tsx`** —
   - On `category` + `start` change, debounce + fetch
     `/v1/analytics/bias_factor/lookup?category=X&tod=Y`.
   - Compute time_of_day from `start` using the same buckets as backend
     (`_time_of_day` in analytics.py: morning/afternoon/evening/night by
     hour of `planned_start_utc` in user TZ).
   - If cell exists AND `bias_factor >= 1.25` AND `sessions >= 10`:
     - Render inline nudge box (yellow, like the soft-conflict warning):
       `"Your {category} tasks at {time_of_day} run {X}% over plan on
       average. Adjust estimate to {Y} min?"`
     - Y = `planned_duration_minutes * bias_factor` (rounded to 5).
     - Three affordances: `[Keep N min]` / `[Use Y min]` / `[Dismiss]`
       (decisional modal contract per notification_patterns.md §Modal).
   - Dismissal logs an `override_action` entry — needs a new table OR a new
     column on `reflection_view_log` (the existing table fits; add
     `reflection_type="calibration_nudge_creation"`).
   - Track: did the user accept / adjust / keep / dismiss.

### Research-relevant fields — no silent defaults

- If user accepts `Use Y min`, set `planned_duration_minutes = Y` — this is
  the user's new estimate, not a default. User explicitly chose.
- If user dismisses, original estimate stands.
- No field gets a hidden `source="calibration_nudge_adjusted"` flag unless
  operator wants one for VT-21 stratification (recommend yes — adds column
  to task model).

### Acceptance-rate tracking (VT-21 candidate)

Each nudge fire writes a row to `reflection_view_log` with reflection_type
= `calibration_nudge_creation`, payload = the rendered text, + a new
`action_taken` field (keep / adjust / dismiss). Rate analysis at Day 10
interrogation.

### Estimated time for tomorrow: 45–75 min

- 15 min: add `/v1/analytics/bias_factor/lookup` endpoint + tests
- 20 min: frontend fetch + debounce + nudge rendering
- 10 min: action logging to reflection_view_log
- 10 min: browser verify + push

---

## Item 2 — Web UI pause response banner (VT-17 experimental mechanism)

### Backend readiness: ✅ contract shipped

Backend wiring is already complete:

1. **Prediction job:** `workers/jobs/pause_prediction.py` runs per-user every
   minute via APScheduler. When a prediction passes all gates, it:
   - Writes a row to `pause_prediction_log` (research artifact, VT-17).
   - Enqueues a notification payload on the per-user Redis queue at key
     `notifications:pending:{user_id}`.

2. **Notification queue drain:** `GET /v1/notifications/pending` drains and
   returns the queued items. Currently agent-facing (OpenClaw polls it every
   30s per SKILL.md). **Verify** this endpoint can also be hit by the web UI
   with the same scoping — scoping hook handles it; no backend change needed.

3. **Response endpoint:** `POST /v1/pause_predictions/{firing_id}/respond`
   (`endpoints/pause_predictions.py`) accepts body
   `{user_response: "pause_now" | "dismiss" | "snooze"}`. Returns 404 if
   firing_id not yours (scoping filters), 409 if already reconciled.

### Payload shape (from `pause_prediction.py`)

The enqueued notification is a structured dict (exact shape in code) with at
minimum: `firing_id`, `mechanism` (`clock_anchor` | `work_rhythm`),
`predicted_at`, `lead_minutes`, `confidence`, `sample_size`, optional
`active_task_id`.

### Tomorrow's implementation steps

1. **Frontend polling** — add a `/v1/notifications/pending` poll to `/today`
   page (or lift to AppShell if other routes need notifications too). Every
   30 s, same cadence as OpenClaw, via react-query `refetchInterval`.

2. **Filter by notification type** — payloads have a `type` field. Frontend
   handles `type === "pause_prediction"`. Other types (ex: `timer_overflow`)
   deferred to their own surfaces.

3. **Render banner** — new component `PausePredictionBanner.tsx` in
   `frontend/components/`:
   - Dismissible yellow banner at top of /today (above ActiveTimerBanner).
   - Copy: `"Pause predicted in ~{lead_minutes} min ({mechanism}). You
     usually break now."`
   - Three buttons: `[Pause now]` / `[Snooze]` / `[Dismiss]`.

4. **`[Pause now]` action** — **critical per do_not_add.md §Predictive
   notifications that default research-relevant fields**:
   - Opens the existing pause-reason picker (no silent default!).
   - User picks a reason → calls `POST /v1/stopwatch/pause` with picked
     reason + `pause_initiator="self"`.
   - THEN calls `POST /v1/pause_predictions/{firing_id}/respond` with
     `user_response="pause_now"`.
   - If user closes picker without choosing: neither call fires (banner
     stays). No silent pause.

5. **`[Snooze]` / `[Dismiss]` actions** — just call the respond endpoint;
   banner disappears.

6. **Rate limiting (already backend-enforced)** — the
   `FIRING_COOLDOWN_MINUTES = 10` in the prediction job ensures max one
   firing per user per 10 min. Frontend doesn't need additional rate
   limiting.

### Estimated time for tomorrow: 45–60 min

- 10 min: verify `/v1/notifications/pending` works from web UI (scoping)
- 20 min: `PausePredictionBanner.tsx` + /today wiring
- 10 min: route `[Pause now]` through existing picker
- 15 min: browser verify + push

---

## Item 3 — /insights tab v1

### Backend readiness: ✅ endpoint exists with 11 generators

`GET /v1/analytics/insights` (`analytics.py:577`) runs 11 generators and
returns the non-None outputs:

| Generator | What it surfaces |
|---|---|
| `_insight_time_of_day` | When you perform best (by delta) |
| `_insight_readiness` | Readiness rating pattern |
| `_insight_abandonment` | Tasks you tend to skip |
| `_insight_estimation_trend` | Are estimates getting better over time |
| `_insight_best_category` | Highest-performing category |
| `_insight_worst_category` | Worst-performing category |
| `_insight_discrepancy_signal` | Does readiness predict delta |
| `_insight_pause_pattern` | `pause_reason` enum counts |
| `_insight_morning_anchor` | Cascade starting from morning anchor |
| `_insight_retroactive_rate` | How often you log retroactively |
| `_insight_initiation_delay` | Pattern of late starts |

Each returns `Optional[dict]` — None if data insufficient (MIN_SESSIONS gate,
typically 3–6).

### @tremor/react: ✅ installed

`package.json`: `"@tremor/react": "^3.18.7"` — already in bundle. Charts
available for the VT-12 companion charts + cascade trend + bias_factor strip.

### Route scaffold: ✅ shipped tonight

`frontend/app/(app)/insights/page.tsx` renders a placeholder "Insights
unlock..." message. Route responds at `https://lyraos.org/insights` with
200 (no 404). Navigation link NOT added — needs tomorrow's browser verify
to land visibly.

### Tomorrow's implementation steps

1. **Replace placeholder with real fetch** —
   - `useQuery(["insights"], () => api<InsightsResponse>("/v1/analytics/insights"))`
   - Loading state
   - Error state (API unreachable)

2. **Render insight cards** — simple card list first (before charts):
   - Each insight: observation text + evidence stats.
   - Skeleton loader during fetch.

3. **Progress framing** — if returned insights list has < N entries OR
   user's EXECUTED task count < 30 in the target category, show
   `"Insights unlock in N more sessions"` per
   `docs/do_not_add.md §Gamification PERMITTED: progressive revelation`.
   Not a streak. Honest statement of data depth.

4. **Add three Tremor charts**:
   - VT-12 companion chart 1: discrepancy × delta scatter
   - VT-12 companion chart 2: readiness × focus bar
   - cascade_score trend line
   - bias_factor-by-category horizontal bar
   - pause pattern card (pause_reason weekly counts)

5. **Add navigation link** — modify `components/app-shell.tsx` to add
   `/insights` to the nav. This is where browser verify becomes
   critical — link visible on every page.

### Open design question

No confrontation dialect at Tier 1 per notification_patterns.md §Surface
Ordering — metric dialect only. "Your initiation delay averages 7 min"
(metric), NOT "You're chronically late to your own tasks" (confrontation).
All 11 insight generators already return metric-dialect observation
strings — tomorrow's render should not add a confrontation overlay.

### Estimated time for tomorrow: 60–90 min

- 20 min: fetch + loading + error states + basic card list
- 25 min: 3 Tremor charts (bias_factor bar, cascade trend, pause pattern)
- 10 min: progress framing "Insights unlock in N more sessions"
- 10 min: nav link + app-shell edit
- 20 min: browser verify + push

---

## Total estimated window for tomorrow

**150–225 minutes of code + verify work**, plus operator-driven browser
verification between each item. Realistic with ~30 min buffer each for
unexpected debugging: **3.5–4.5 hours total**.

All three items unblock with no backend dependency. Shipping all three
ahead of the April 18 trusted-user launch is feasible if operator starts
early morning.

## What NOT to ship tomorrow (defer past April 18)

- Confrontation-dialect insights (metric only at Tier 1)
- Calendar page mobile fix (P2 per Apr 16 dogfood entry)
- Pause/resume residual delay frontend optimization
- /insights post-30-session reclassification prompt (Phase 5)
- EXECUTED task immutability UX (P2)

## References

- `docs/building_phases.md §Phase 4.5 Tier 1` — shipping gate for alpha
- `docs/design_patterns/notification_patterns.md` — Toast vs Modal vs Banner
- `docs/design_patterns/rules_vs_agency.md` — structural invariant test
- `docs/do_not_add.md §Hardcoded default values` — no silent defaults
- `MANIFESTO.md §VT-17` — pause prediction pre-registration
- `MANIFESTO.md §VT-21 candidate` — narrative-layer influence stratification
