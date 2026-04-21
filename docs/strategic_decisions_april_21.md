# Strategic Decisions — April 21, 2026

Four structural clarifications that reshape Lyra's near-term product + research trajectory. Each grounded in data from the first two external-user activations (April 18-20) and a council-style multi-agent review of the current state.

---

## 1. Path B committed: engineer planning as a habit, reject accommodating reactive execution

**Previous implicit framing:** Lyra is a mirror for people who "plan well and still fail themselves." Users bring their planning; we measure the gap.

**Clarified framing:** Planning is a skill. Most users don't plan in any meaningful lead-time sense. The thesis "reduce the gap between planning and executing" is vacuous when there's no planning to begin with. Lyra's product surface must *develop the planning habit in users* — not accommodate reactive-executer patterns as if they were the target behavior.

**Data that forced the reframe (2026-04-21):**

| Cohort | Tasks | Planned >30 min ahead | Reactive (≤2 min lead) | Plan created AFTER exec started |
|--------|-------|------------------------|-------------------------|----------------------------------|
| External (user_ids 4, 5, 6) | 9 | **0 (0%)** | 4 (44%) | 1 (11%) |
| Operator (user_id 1) | 78 | 28 (36%) | 11 (14%) | 17 (22%) |

**Zero of nine external-user tasks had meaningful planning lead time.** Even the operator, who has absorbed the research goal, is only 36% "true planning" (>30 min lead). For external users the instrument is effectively measuring snap-estimation bias, not planning fallacy. Two different literatures (Tversky prospective duration estimation vs. Buehler/Kahneman planning fallacy), different predictions, different product shape.

**Implication — Path B over Path A:**
- **Path A** (rejected): lean into snap estimation, drop the "plan well" framing, optimize for one-tap start with inline duration guess. Lower friction, matches observed behavior, smaller thesis.
- **Path B** (committed): engineer a planning ritual. Onboarding auto-creates a "planning" category task (30 min, first session) so the user's first interaction IS planning. Daily morning-plan nudge (APScheduler). External-tool ingestion (Notion, Google Calendar) as import-and-re-plan rituals — not bypasses. The system teaches the behavior it measures.

**What this locks in:**
- The landing-page thesis ("plan well and still fail themselves") stays — but the product must *teach* planning, not assume it.
- `readiness` rating and `description` brain-dump remain research-critical.
- VT-22 (scope inflation) becomes a *diagnostic companion* to Path B: scope inflation is what happens when users plan but fail to specify scope. Both are mechanisms of the planning-execution gap; Path B addresses the first, VT-22 exposes the second.

**Precedents (from prior-art scan):**
- `docs/parked_ideas.md:135-230` — Phase 4.5 brain-dump design is already aligned with Path B: user states scope before executing, corpus accumulates, AI subtask decomposition unlocks at 50+ dumps. The `description` textarea is unblocked; Path B ratifies its priority.
- `docs/do_not_add.md` — gamification rejected; progress-framing permitted. A planning ritual may not use streaks or guilt, but *can* surface "planning habit forming" progressive revelations (archetype reveal, per-category insights).
- `docs/design_patterns/rules_vs_agency.md` — the planning ritual is a *structural invariant* (always a measurement moment), not a *behavioral constraint* (overridable gate). Users can skip the morning planning nudge; the first-session planning task is mandatory because it's the instrument calibration moment, not a feature gate.

**Kill criterion (pre-registered):** by 2026-05-21, among users who completed the first-session planning task, at least 30% must have a second planning task (logged or prompted-and-completed) before session 10. Below 30% and Path B is not habit-forming; it's onboarding theater. Roll back to Path A or pivot.

---

## 2. `self_reflection` → `planning` un-merged (taxonomy edit 2026-04-21)

**Previous state (April 8 merge, commit 281e230):** `planning` was collapsed into `self_reflection` because usage data showed operator-dominated meta-work logging. Two small buckets would have split the signal and produced false-negative bias estimates during the Apr 4-15 H1 window.

**Clarified state (today):** Path B requires the category surface to *invite* planning behavior. A dropdown listing "self_reflection" as the meta-work category signals "this is for people who journal" — which excludes the exact users Path B wants to convert. The category name is the copy. Rename was deferred in `docs/building_phases.md:375` as cosmetic; today's commitment promotes it to shipping.

**Mechanical details:**
- Frontend: `frontend/lib/categories.ts` — `self_reflection` → `planning`. Color kept (fuchsia ramp). Pure slot rename; bias_factor priors' (category, time_of_day) key space unchanged.
- Backend: `backend/app/db/seed.py` — keyword expansion from 3 keywords (planning/reflection/journal) to 16 covering plan, schedule, brain dump, brainstorm, outline, agenda, roadmap, priorities, weekly review, plus retained reflection/journal/calibration/friction/idea/refinement for back-compat.
- Data migration executed against prod (2026-04-21): `UPDATE task SET category='planning' WHERE category='self_reflection'` — 6 rows updated. `UPDATE category_mapping` — 9 rows updated. 7 new keywords seeded.
- Risk: any user-typed string "self_reflection" in descriptions/retroactive entries stays as text — not my problem (description is free text). Dedicated `self_reflection` as a separate category can return if n=50 data shows it's a real sub-behavior distinct from planning.

**What this does NOT do:** it does not add a new slot to the taxonomy. Adding categories mid-window breaks bias_factor monotonicity per Rule #2 (MANIFESTO.md:850). This is a rename at fixed cardinality.

---

## 3. Three-bug UI fix (new-task-modal.tsx)

Dogfood 2026-04-21: operator reported "can't create past task, no warning, duration doesn't update." Screenshot showed 11:45 AM → 01:45 AM on same day (AM/PM slip), duration 0h 0m, calibration nudge firing with "Use 5 min" for a task of 0 minutes, disabled Create button, small "End time must be after start" error visually overwhelmed by the loud research popup. Three root causes stacked:

1. **`handleEndChange` silently ignored negative ranges** (line 262-269): `if (mins > 0)` guard meant duration state never updated when end fell before start. UI displayed stale values.
2. **Calibration nudge fired on 0-duration** via `lookupBiasFactor(category, tod, planned || 30)` fallback — a 0-min estimate queried bias factor as if planned=30, producing nonsensical "adjust to 5 min" recommendations on invalid forms.
3. **No AM/PM inference** — the most common cause of "end before start on same day" is the native `<input type="datetime-local">` keeping AM when the user typed PM. Forcing the user to re-click the period without a one-tap recovery path.

**Fix (shipped):**
- Always recompute duration on `handleEndChange`, zero it for negative ranges with banner feedback.
- Gate calibration-nudge effect on `totalMinutes > 0 && rangeValid`.
- Add `suggestAmPmSwap` derived value: if end is 1-12h before start on same calendar day, offer one-tap "Did you mean 1:45 PM? — tap to fix" button inline in the error banner.

**Observational hypothesis for Path B roadmap:** if AM/PM slips are common, the native datetime-local picker is user-hostile for time-anchored planning. A custom picker (or a natural-language time field via OpenClaw parse) may be Phase 5 work.

---

## 4. Documentation habit: decisions land in docs/ by default

Operator feedback 2026-04-21: "always document decisions and ideas without me asking to."

This is now a durable working rule. Every non-trivial decision, idea, data finding, or hard rule gets written to `docs/` as part of the work, not as an explicit ask. Bundle docs commits with the code commits they describe, or trail a doc-only commit in the same push chain. Saved to Claude memory (`feedback_always_document.md`).

**Why:** the operator's project DNA is corpus-driven. Decisions without a durable record don't cohere into a thesis over months. A 3-month retrospective needs to re-find "why did we un-merge planning on April 21?" — the answer lives here.

---

## Roadmap sketch (what Path B needs)

*Not committed beyond Phase 4.5 + the first-session planning task; captured here so it's legible next session.*

| Item | Blocker | Est. | Priority |
|------|---------|------|----------|
| Onboarding flow scaffolding (`frontend/app/onboarding/` currently empty) | None | ~1 day | P0 for first-session planning task |
| First-session planning task auto-creation | Onboarding flow | ~2h | P0 (the Path B ritual) |
| Morning-plan APScheduler job + user settings surface | None | ~1 day | P1 (daily habit reinforcement) |
| Notion import flow (page URL → parsed tasks) | OpenClaw parse reusable? | ~3 days | P2 (post n=20 users) |
| Google Calendar import (events → PLANNED tasks) | OAuth + timezone refactor | ~1 week | P3 (post multi-timezone, Phase 7+) |
| Custom time picker with AM/PM safety | Dogfood only; see §3 | ~1 day | P2 (after n≥3 AM/PM incidents) |
| Planning-habit kill-criterion dashboard | Telemetry events for "first-session planning task completed" | ~half day | Pre-registered for 2026-05-21 checkpoint |

---

**Shipped today (2026-04-21):**
- 3-bug UI fix on `new-task-modal.tsx`
- `self_reflection` → `planning` taxonomy rename (frontend + backend + prod DB + keyword seeder)
- This decision doc
- Matching updates to `docs/building_phases.md` and `docs/dogfood_findings_living.md`
- Council-review verdict + dogfood data finding (captured inline in this doc's §1)

**Deferred:**
- Net-new Path B infrastructure (onboarding, morning nudge) — planned for next session cycle
- Custom time picker — dogfood-gated (need ≥3 AM/PM incident reports)
