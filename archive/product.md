# Product Design

*Consolidated from: `category_taxonomy.md`, `competitive_landscape.md`, `v2_backlog.md`.*
*Last updated: April 10, 2026.*

---

## 1. Category Taxonomy (Frozen — Apr 8 2026)

The category vocabulary is **frozen** for the duration of the April 4-15 measurement window. New keywords may be added; new *categories* may not, until post-experiment analysis.

### Rationale

Adding categories mid-experiment redistributes sessions across buckets and breaks the per-(category, time_of_day) bias-factor model. Bucket counts must remain monotonic over the window.

### Frozen list

| Category | Notes |
|---|---|
| fitness | Exercise / movement |
| academic | Lectures, classes, course-bound work |
| study | Self-directed learning, problem sets, reading |
| development | Coding, debugging, building (Lyra and other) |
| meeting | Synchronous calls, standups, interviews-as-meeting |
| prayer | Salah and related |
| self_reflection | Journaling, planning, calibration, refinement, brainstorming, reflection |
| network | Outreach, LinkedIn, networking interviews |
| health | Sleep, medical, recovery |
| work | Generic work fallback (quick / unplanned tasks) |
| personal | Meals and personal time |

### Apr 8 merge: `planning` -> `self_reflection`

`planning`, `calibration`, `plan`, `friction` were originally seeded into a separate `planning` category. This was a bookkeeping mistake — they belong with `self_reflection`. The two categories were semantically identical (both are meta-work *about* the system rather than execution). Two cells split a tiny bucket and would have produced false-negative bias estimates.

**Action taken (Apr 8):** all `planning`-categorized rows repointed to `self_reflection`. Pre-registered as MANIFESTO Rule #2.

### Category type field (design — Phase 4)

> **Status: design only, implementation deferred to Phase 4.** The `category_type` column does not exist in the database as of v1.5. The design below is approved; the migration has not been written.

Each category will carry a `category_type` enum with two values:

| Type | Meaning | Examples | Analytics treatment |
|---|---|---|---|
| `estimable` | Duration under user's control. Delta is meaningful. | development, study, academic, fitness, work | Included in bias-factor estimation, H1 correlation, scheduling predictions |
| `time_anchored` | Duration externally fixed. Delta is noise. | prayer, meeting, health | Excluded from bias-factor cells. Shown in timeline but not in calibration analytics. |

**Why this matters:** The bias-factor model is only meaningful for categories where the user controls duration. Including time-anchored categories dilutes the signal and produces false "accurate" bias factors.

**Implementation (Phase 4):** Add `category_type` column to `category_mapping` (default `estimable`), seed two `time_anchored` categories (prayer, meeting), filter on `category_type = 'estimable'` in bias-factor and H1 queries.

### Planned rename: `self_reflection` -> `planning` (Phase 4, post-experiment)

Users type "planning session" and expect a category called `planning`. The keyword mapping handles this, but the mismatch is a friction point.

Rename plan:
1. Alembic migration: UPDATE category_mapping and task tables
2. Update seed.py with `planning` as canonical name
3. Keep `self_reflection` as keyword alias
4. Update taxonomy doc and analytics queries

Blocked until Apr 4-15 experiment window closes.

### Adding keywords (allowed)

New keywords mapping into existing categories may be added at any time via `seed.py`.

### Adding categories (not allowed until Apr 16)

After the experiment closes, post-hoc analysis may justify splitting or merging categories. Do that against the frozen dataset, not live data.

---

## 2. Competitive Landscape

Quick scan of tools adjacent to Lyra Secretary.

| Product | Category | What it does | What it misses |
|---|---|---|---|
| Twin'Am | Adaptive scheduler | Learns work patterns, suggests blocks | No research layer; black-box suggestions; no planned-vs-executed exposure |
| Habitica | Gamified habit tracker | RPG-style streaks and rewards | Habits, not time; no duration data; no calibration loop |
| Toggl Track | Time tracker | Manual/auto timers, reports | Tracks but doesn't plan; no delta between intent and execution |
| RescueTime | Passive time tracker | Auto-categorizes app/site usage | Descriptive, not prescriptive; no user-facing readiness/reflection |
| Clockify | Time tracker | Timesheets, billing | Logs only, no planning layer |
| Notion | General workspace | Databases, docs, task boards | Storage, not scheduling; no timer, no adaptive loop |
| Todoist | Task manager | Lists, due dates, natural language | No duration, no execution data, no research layer |
| ClickUp | Project mgmt | Tasks, docs, time tracking, everything | Feature sprawl; no adaptive scheduling or calibration feedback |
| Forest | Focus timer | Pomodoro with tree gamification | Fixed intervals; no planning; no delta data |
| Focus Keeper | Focus timer | Pomodoro variants | No planning context, no post-hoc calibration |

### What's missing in the market

No tool closes the **metacognitive loop** between planning and execution:

1. **Planned vs executed duration as first-class data.** Everyone tracks one side or the other. Nothing surfaces the delta to the user as a learning signal.
2. **Pre-task readiness and post-task reflection as structured input.** Treated as journaling (if at all), never as a quantitative instrument paired with duration delta.
3. **Calibration feedback as a UX primitive.** "You planned 30, it took 45, your focus was 3/5 — here's what reference-class forecasting suggests for next time." No one ships this.
4. **Research layer visible in the daily view.** Users see the numbers that drive the adaptive model, not just the model's output.

---

## 3. v2 Backlog

Deferred deliberately. Not blocking alpha or the research-layer goal of v0.1.

- **LLM-powered task creation** — Phase 6 candidate, not deferred indefinitely. Cost is much lower than originally estimated because OpenClaw infrastructure already exists and just needs to be exposed as a web client. Implementation sketch: text input field on web UI → POSTs to OpenClaw gateway → existing SKILL.md workflow → backend calls.
- **Email notifications** — reminders, daily summaries. Requires SMTP/SES infra + user preferences.
- **Browser push notifications** — Web Push + VAPID. Polling at 10s is good enough for Phase 3/4.
- **Per-user category visibility flags** — hide categories per user without removing from frozen taxonomy. Needed once non-Cairo users arrive.
- **Mobile app** — native or PWA wrapper. Static export already works on mobile web.
- **Team / multi-user collaboration** — shared tasks, visibility scopes. Out of scope for single-user adaptive scheduler.
- **Prayer time API integration** — auto-block prayer windows using aladhan.com or similar. Reduces scheduling friction for users who observe fixed daily prayers.
- **Smart reminders (bias-aware)** — adjust lead time based on historical initiation_delay for that (category, time_of_day) cell. Requires n >= 10 sessions per cell.
- **Mid-funnel retention nudges** — detect users with <3 executed sessions in first 7 days, trigger lightweight check-in. Requires retention-check worker and nudge template system.
