# Lyra — Parked Ideas

*Ideas captured but not executed. Each has a revisit condition. Do not build
before conditions are met.*

*Format: short description, why parked, what triggers revisiting, date captured.*

---

## Guided product tour (onboarding steps)
*Captured: 2026-04-22 (operator-proposed; triggered by mom-guided-demo
observation + pending mentor share with Omar today)*

**Idea:** 7–8 skippable tutorial overlay steps that introduce Lyra's
core surfaces to a fresh user on first sign-in. Standard pattern from
complex SaaS apps (Notion, Linear, Figma). Persist per-user completion
/ skip state so they don't re-fire.

**Why:** mom (u4) couldn't return after her guided demo because she
couldn't reconstruct the flow independently. Omar (mentor) gets the
app today — biggest single-test-case of "is this learnable without a
human in the loop." Current app throws the user onto /today with a
seeded starter task and no orientation; not enough scaffolding for a
non-operator mental model.

**Proposed step sequence:**
1. *Welcome + one-sentence thesis.* "Lyra measures how long your tasks
   actually take vs how long you thought they would — over time, you
   see the shape of your own planning."
2. *Starter task highlight.* Arrow to the seeded "Plan your week"
   row. "This is your first task. Click Start to fire a timer; we'll
   ask how ready you feel before you begin."
3. *Readiness prompt preview.* Screenshot / mock. "A 1–5 slider before
   every task. Not scored, not shown to anyone — it's calibration
   input."
4. *Stop + reflection preview.* "When you stop, we ask how you felt
   about the run. The gap between readiness and reflection is a
   signal."
5. *Calendar tour.* Briefly: "Drag to reschedule PLANNED tasks; past
   ones are locked."
6. *Insights tour.* "Your delta pattern shows up here after 10+
   tasks."
7. *Integrations tour.* Briefly: "Connect Google Calendar if you want
   external events alongside your plans. Optional."
8. *Closing.* "We stay out of your way. No streaks, no guilt, no push
   notifications until you earn them. Questions → settings."

**Implementation sketch:**
- New Alembic migration adds `user.tutorial_completed_at` +
  `user.tutorial_skipped_at` (nullable DateTime).
- New frontend overlay component (`<TutorialOverlay />`) rendered in
  `(app)/layout.tsx` when both fields are null and
  `onboarding_completed_at IS NOT NULL`.
- Steps implemented as a simple carousel: no interactive DOM-targeting
  highlighting in v1 (brittle); just a modal with "Next / Skip" per
  step.
- "Skip all" button on step 1 stamps `tutorial_skipped_at = now()` +
  closes.
- "Finish" on step 8 stamps `tutorial_completed_at = now()`.
- Accessibility: dismissable via Escape key; focus trap inside modal.
- Research note: tour exposure logged to `reflection_view_log` as
  `reflection_type='tutorial'` so VT-21 can eventually ask "does
  tutorial exposure correlate with D7 return?"

**Priority:** P0 if Omar-test today is load-bearing. Otherwise ship
before the next external-user invite.

**Revisit conditions:** ship on first iteration. Can always skip for
Omar today (one mentor, high trust) and aim for the next invite, but
operator flagged it as "why don't we just add this" — net positive
even at n=1 mentor.

**Tour v2 — contextual/pointer-based walkthrough (parked 2026-04-22 evening)**

Operator feedback after v1 shipped: the centered-modal carousel tells
users about features in the abstract but doesn't show them *where* the
features live. "Basic" was the word used. The next iteration should
anchor each step to a real UI element with a tooltip + backdrop
highlight, similar to Intercom / Pendo / Userflow / React-Joyride
patterns.

**Proposed step sequence (v2 — tour should point at these):**
1. *Welcome.* Centered, same as v1.
2. *"Create a new task" button* — tooltip anchored to the `+` button
   on /today. "Click this to plan ahead. You can also type a time like
   'tomorrow 3pm' and Lyra parses it."
3. *Task row affordances* — anchored to the first row on the feed.
   Walk through: Start timer button, the three-dot menu (Edit / Skip /
   Delete / Void), the category badge, the duration + state chip.
4. *Readiness modal preview* — trigger the modal (or screenshot) when
   user hypothetically clicks Start. Explain the 1–5 slider and why
   it matters.
5. *Timer + Pause* — anchored to the active-timer banner. Explain
   Pause vs Stop, when to pause (prayer, break, interruption) vs when
   to stop (done).
6. *Stop + reflection* — second half of a timer's life. Reflection
   slider, task_completion_percentage, then the calibration nudge /
   micro_mirror surfaces that may fire post-stop.
7. *Void control* — anchored to the void option in the menu. Critical:
   "Delete = I regret creating this. Void = this isn't real data,
   don't use it for learning." The distinction matters for research
   integrity and the operator flagged it specifically.
8. *Calendar nav* — link to /calendar in sidebar. "Everything you plan
   and execute lives on this grid. Drag PLANNED tasks to reschedule."
9. *Insights nav* — after ~10 tasks.
10. *Settings → Integrations nav* — "Connect Google Calendar here
    when you're ready. Optional."
11. *Closing.* Centered finish, "Get started."

**Implementation sketch:**
- Add `data-tour-id="new-task-button"` etc. to anchor elements across
  the codebase. Keep the IDs in a central constants file
  (`frontend/lib/tour-anchors.ts`) so renames don't silently break
  the tour.
- Use `@floating-ui/react` (MIT, small, framework-native) for anchor
  positioning with auto-flip when the anchor is near a viewport edge.
- Backdrop: absolutely-positioned div with a `clip-path` cutout
  around the anchor's bounding rect. Re-compute on scroll + resize.
- Advance on: click Next button OR click the highlighted anchor
  itself (if the step is about an action the user should learn by
  doing).
- Re-entry: the tour can be re-opened from Settings → "Replay product
  tour" button. Stamp `tutorial_replayed_at` so re-runs don't affect
  the original completion analysis.
- Skip button stays available on every step. Esc still dismisses.
- Storage: re-use `user.tutorial_completed_at` + `tutorial_skipped_at`;
  add `user.tutorial_replayed_at` in a future migration.

**Tradeoffs vs v1:**
- Higher build cost (~6–8h). More moving parts; more visual-regression
  risk when UI changes.
- Higher learn-by-seeing value. Mom-proof test: if it points at the
  button you want her to click, she doesn't have to pattern-match
  from description.
- Anchor IDs become a minor maintenance burden — every time a
  component rename happens, the tour needs a bump.

**Revisit conditions:** ship when (a) Omar's session exposes specific
gaps the v1 tour didn't cover, OR (b) next external-user invite
cohort is ≥3 users (enough to justify the build cost), OR (c) the
mom-user-archetype retention proves otherwise unaddressable. Whichever
fires first.

**Do not:**
- Build the anchor system before operator feedback from Omar's run
  lands — v1 may prove sufficient for some users and the v2 build
  should be driven by observed failure modes, not speculation.
- Auto-replay the tour on every login after changes (feels patronizing;
  changes the measurement context for existing users).

---

**Do not (v1 constraints, retained):**
- Gate core app behind completion (Structural Investigation: tutorial
  is a *structural invariant measurement moment*, not a *behavioral
  gate*)
- Auto-advance or time-limit steps (user-paced)
- Add gamification (streaks / XP / achievement badges) — violates
  `do_not_add.md`

---

## LLM-powered subscription tier
*Captured: April 14, 2026*

**Idea:** Base Lyra (web UI + mobile app) remains free or low-cost. Paid tier
adds OpenClaw via Telegram (natural language commands, conversational
interactions) + other LLM-powered features. Monthly subscription covers
Anthropic API consumption + margin.

**Rationale:** The operator's April 14 OpenClaw credit exhaustion revealed
that the conversational interface has real per-user cost. Pricing that tier
separately aligns cost with value. Users who want conversational power pay
for it; base users don't subsidize them.

**Reference models:** Notion AI, Linear AI, Cursor Pro — standard pricing
pattern for LLM-enhanced consumer products in 2025+.

**Revisit conditions (all must be met):**
- Retention validated post-May 21 with base product
- Base product has earned paying users or proven willingness-to-pay
  independent of AI tier
- Trusted-user feedback confirms OpenClaw is valued enough to justify paid
  access
- Operator has capacity to ship billing infrastructure without disrupting
  research timeline

**Do not:**
- Build pricing infrastructure before validating base value proposition
- Architect tier separation (feature gates, entitlements, subscription
  state) before retention data confirms which features users actually value
- Let monetization framing drift research design — all Phase 4.5 and
  Phase 5 decisions remain research-driven, not monetization-driven

**If idea still looks good in June+:** open a Phase 7 architecture spike.
Begin with competitive analysis of Notion/Linear/Cursor pricing models, then
decide Lyra-specific pricing model.

---

## Strategic decision log pointer
*Captured: April 14, 2026*

See `docs/strategic_decisions_april_14.md` for the four locked decisions from
the evening session: behavioral correction primary framing, gamification
refinement via progressive revelation, conflict detection forced override,
cold-start as legitimate experiment. These are referenced across
`MANIFESTO.md`, `docs/building_phases.md`, `docs/do_not_add.md`, and
`docs/design_patterns/notification_patterns.md`.

---

## Moat architecture discussion
*Captured: April 14, 2026*

**Parked until post-April 29** (after Spring School).

**Prerequisite:** operator has clarity on which scenario (research-impact,
commercial scale, learning vehicle) Lyra primarily serves. Moat thinking
without that clarity risks corrupting the behavioral-correction thesis by
drifting toward platform-product defensiveness.

**Revisit conditions:**
- Spring School completed (April 29)
- Retention data from trusted-user cold-start analyzed (see
  `docs/dogfood_findings_living.md §Cold-start engagement decay analysis`)
- Operator has explicitly chosen which primary scenario to optimize for

**Do not:**
- Begin moat-shaped architecture work (platform lock-in, data moat
  accumulation, switching-cost design) before the primary scenario is named
- Let moat framing enter Phase 4.5 / Phase 5 / Phase 5.5 design decisions —
  those remain research-driven

---

## Multi-task logging with cognitive bandwidth allocation
*Captured: April 15, 2026 (recurrent idea, third+ mention)*

**Pain:** Knowledge workers operate in concurrent modes. Operator examples:
vibecoding while studying, conversation while attending lecture, coding
while in async meeting. Current sequential-task execution model
misrepresents these patterns. Sessions get logged as one task or another,
never the actual blended attention state.

**Proposed mechanism:** Concurrent task groups where multiple tasks can be
EXECUTING simultaneously, each with declared cognitive bandwidth
allocation (e.g., 70% lecture, 30% conversation). delta computed against
bandwidth-weighted planned duration.

**Key open questions:**
- State machine: how do EXECUTING states stack? How does pause work for
  one task in a group?
- Measurement semantics: is "actual" duration wall-clock or bandwidth-
  weighted?
- Self-report validity: bandwidth allocation as Likert-style rating has
  same scale-saturation risk as readiness (VT-12 class).
- Interaction effects: does measuring multi-task state make users do more
  multi-tasking (instrument-intervention class, VT-17/VT-21 adjacent)?
- New validity threats around concurrent execution measurement.
- UI complexity: how do you show 2-3 active timers without cognitive
  overhead?
- Aggregation: how do bias_factor and other per-task metrics combine
  across concurrent groups?

**Revisit conditions:**
- Post-alpha (post-May 21)
- Post-H1-validation (because if signed_discrepancy doesn't predict delta
  in single-task mode, it certainly won't in multi-task mode)
- When Phase 6 calibration architecture is in active build
- After observing alpha users for evidence of whether multi-task patterns
  are common enough to warrant the model expansion

**Do not:**
- Build mid-experiment (would invalidate single-task baseline data)
- Build before validating it's a common pattern, not just
  operator-specific
- Build before designing the validity threat framework for concurrent
  measurement

**Related:**
- Offline mode (different problem, also recurrent)
- VT-12, VT-17, VT-21 (similar measurement-intervention concerns)
- Phase 6 calibration architecture

---

## Brain dump → AI subtask decomposition
*Captured: April 17, 2026. Integration feature, not isolated addition.*
*Elevated: April 17, 2026. VT-22 (scope inflation hypothesis) identifies
brain dump as potential PRIMARY measurement surface, not secondary corpus.
See `MANIFESTO.md` §VT-22 and pre-registered Rule 12.*

**Problem:** Users create macro tasks ("build session", "study subject X",
"meetings") that hide internal complexity. Measurement at macro level misses
where time actually goes. Current system measures delta on the whole block
but cannot identify which subtask caused the overrun.

**Scope inflation connection (VT-22):** If delta measures scope inflation
rather than time estimation error, the brain dump captures *stated scope* —
the missing half of the measurement. `scope_density = description_item_count
/ planned_minutes` becomes the core metric. High scope density + high
readiness = detectable impossible plan at creation time. See MANIFESTO §VT-22
for the full hypothesis and §Rule 12 for the pre-registered mediation test.

**Three-phase implementation:**

Phase 4.5 — Seed (trusted-user week, unblocked):
- Add optional description textarea to task creation modal: "What does this
  involve? (optional)"
- Store as `task.description` (TEXT, nullable)
- New Alembic migration if column does not exist
- No AI, no inference, no subtasks at this phase
- Collapsible UI behind "Add details" toggle
- Purpose: corpus accumulation + archetype signal (detailed dump = planner
  signal, empty = reactive signal)
- Zero impact on existing measurement variables

Phase 5 — Inference (post-Spring-School, requires 50+ brain dumps):
- LLM inference at task creation: brain dump text → structured subtask list
- Flow: user creates macro task → estimates total duration → brain dumps
  specifics → AI infers subtasks (1. X, 2. Y, 3. Z) → user
  confirms/edits/dismisses → confirmed subtasks created as linked tasks
- Subtask durations inferred from `bias_factor` + historical patterns, NOT
  user-estimated
- Requires: LLM API call in creation flow (latency 2-5s), `parent_task_id`
  FK structure for subtask linking, accumulated corpus

Phase 5 — Sequential execution mode:
- After subtask inference and user confirmation, app auto-queues subtasks
- On subtask N stop: immediate single-tap prompt "Start subtask N+1:
  [name]? [Yes] [Skip]"
- Execution becomes guided walkthrough of AI-decomposed plan
- This is a new interaction paradigm — NOT just inference at creation.
  Design separately.

Phase 6 — Integration (post-alpha):
- `bias_factor`: per-subtask-type delta granularity — "You underestimate
  API work 40% but frontend is calibrated"
- `calibration_nudge`: fires per subtask at creation and stop
- `cascade_score`: intra-task cascade detection — did subtask 3 fail
  because subtask 2 ran over?
- `archetype_classification`: brain dump style as signal (detail level,
  organization, specificity)
- `category_auto_creation`: macro task name → new category when repeated
  >3 times
- `fragmentation_index`: extends to subtask transitions
- `micro_mirror`: subtask-specific observation text
- `insights`: cross-subtask pattern detection

**Connection map (existing variables touched):**
`bias_factor`, `calibration_nudge`, `cascade_score`, `archetype`,
`category_mapping`, `fragmentation_index`, `micro_mirror`, `insights` — all
8 touched.

**UX target state:** user brain dumps once, then manages execution via
single taps. Planning labor shifts from user to system.

**Key constraint (`rules_vs_agency.md`):** AI-suggested subtasks are
suggestions, never mandates. User can dismiss, edit, reorder, ignore.
System measures what actually happens regardless of whether user followed
the decomposition.

**Validity threats to pre-register before Phase 5:**
- VT candidate: AI decomposition changes user behavior by framing task
  differently before execution. Same class as VT-21. Mitigation: compare
  delta distributions tasks with/without AI decomposition.
- VT candidate: subtask count as proxy for complexity is noisy. 2-subtask
  hard problem ≠ 10-subtask easy checklist.
- VT candidate: LLM inference quality varies. Wrong decomposition → wrong
  subtask priors → confidently wrong calibration nudges. Guardrail:
  confidence flag on AI-generated decompositions, explicit "AI suggested"
  label.

**Do not build Phase 5+ until:**
- H1 validated or falsified
- 50+ brain dumps accumulated across users
- Not mid-experiment

**Related:** H2 deadline proximity, multi-task logging (existing), calendar
integration (Phase 7)

---

## Mid-session half-time check-in
*Captured: April 17, 2026.*

**Problem:** Current system knows where a session ended
(`task_completion_percentage` on stop). It does not know where the user was
at the midpoint. Execution shape is unmeasured — strong-start/weak-finish
vs slow-start/strong-finish produce identical final delta but different
behavioral signals.

**Mechanism:**
- At 50% of `planned_duration_minutes` elapsed, system surfaces check-in
- Prompt: "Halfway point — where are you?"
- `completion_pct` input: 25 / 50 / 75 / 100
- 100 = early finish path → surfaces "Stop now?" single-tap option
- <50 = likely overrun path → `calibration_nudge` fires with adjusted
  estimate
- Stored as `mid_session_completion_pct` (new field or separate event table)

**New signal unlocked:**
- Within-session trajectory (execution shape)
- Early-finish edge case handled proactively instead of reactively
- Additional `bias_factor` calibration data point
- "You typically hit 50% completion at the halfway mark on development
  tasks but only 25% on study tasks" → new insight tier

**Early-finish edge case:**
- At half-time ping, user reports 100% → single-tap "Stop session?" prompt
- Replaces current reactive early-stop detection
- `completion_pct` collected here feeds same `bias_factor` pipeline as
  existing stop flow

**Phase constraint:**
- Full push notification version: Phase 7 (requires PWA service worker)
- In-app toast fallback: Phase 5 (fires only if tab is open, `useEffect`
  timer or server-sent event)
- Do not block Phase 5 sequential execution mode on push notification
  capability

**Connection to existing variables:**
- `bias_factor` ← mid-session completion adds calibration signal
- `micro_mirror` ← trajectory-aware observation text possible
- `insights` ← execution shape patterns (strong-start vs slow-start per
  category)
- `fragmentation_index` ← mid-session state extends pause pattern analysis

**Do not build until:**
- Phase 5 sequential execution mode is designed (avoid conflicting
  mid-session prompts)
- Existing `task_completion_percentage` on stop has sufficient data to
  validate whether mid-session signal adds value

---

## H2: Deadline-proximity risk assessment
*Captured: April 16, 2026 (from ChatGPT conversation). Expanded April 17
with integration mapping.*

**Hypothesis:** Users systematically underestimate task duration due to
distorted risk assessment under deadline proximity, producing increasing
`duration_delta_minutes` as deadline approaches. Mechanism: temporal
discounting × planning-fallacy interaction — imminent deadlines compress
the mental representation of required work.

**Testable predictions:**
- Case A: delta increases near deadline → classic procrastination +
  temporal discounting
- Case B: delta inverts near deadline → anxiety compensation
  (overestimation)
- Case C: no correlation → H2 falsified
- All three outcomes are informative.

**Status:** H2 candidate. Not in H1's kill-criterion chain and does not
bear on the Apr 15 H1 decision. Documented here so it isn't lost; do not
build.

**Schema additions required:**
- `deadline_utc`: nullable column on Task (currently absent — Lyra has no
  deadline concept; tasks are scheduled, not deadlined)
- `deadline_distance`: computed at creation as
  `deadline_utc - planned_start_utc`
- Calendar integration (Phase 7) provides deadline data automatically from
  Google Calendar events with due dates

**Measurable cross-references:**
- `bias_factor` × `deadline_distance`
- `cascade_score` × `deadline_distance`
- `signed_discrepancy` × `deadline_distance`
- `initiation_delay` × `deadline_distance`
- `unplanned_execution_rate` × `deadline_distance`
- Brain dump complexity × `deadline_distance` (requires brain dump
  `description` field)

**Connection to brain dump (Feature 1):** Brain dump captures task scope.
Deadline captures time pressure. Intersection: does the gap between stated
scope (brain dump complexity) and stated duration widen as deadline
approaches? A user who brain-dumps 8 bullet points but plans 30 minutes
with a 2-hour deadline is producing a detectably impossible plan at
creation time.

**Product endgame:** Predict plan feasibility before user commits. "Given
your history, this task's scope, and time remaining: this plan has X%
chance of succeeding." Not a time tracker — a feasibility instrument.

**Intervention (measure first, build second):**
At task creation when deadline exists: "Deadline in X hours.
Research-adjusted estimate: +Y%. [Keep] [Adjust]." Track option picked +
actual outcome. Only build after pattern validated in multi-user data.

**Pre-registration required before data collection:**
- H2 registered in MANIFESTO before schema addition
- Kill criterion: `deadline_distance` × `delta` correlation not significant
  at n≥60 deadline-tagged tasks → H2 falsified
- Stratify by category

**Phase:** 6+ (post-calibration-architecture). Deadline data is a new
measurement axis, not a refinement of the existing discrepancy model.

**Do not:**
- Build mid-experiment (would add a new input variable to the H1 dataset
  and invalidate the pre-registered analysis rules in MANIFESTO §801)
- Ship deadline UI before H1 decision (would contaminate the single-
  hypothesis window by introducing a competing behavioral signal users
  will orient to)
- Treat `deadline_utc` as equivalent to `planned_start_utc` /
  `planned_end_utc` — they represent distinct constructs (scheduling vs.
  hard obligation)

**Revisit conditions:**
- H1 decision complete (validated, falsified, or explicit pivot)
- Phase 6 calibration architecture is in active build
- Operator has made an explicit scope call that H2 is the next hypothesis
  to test (competing candidates exist — cascade hypothesis per MANIFESTO
  §Paper 2, interruption-recovery cost, others)
- Brain dump field (Feature 1) providing scope signal

**Related:**
- MANIFESTO §Kill Criterion (H1 pre-registration; H2 is downstream of H1)
- MANIFESTO §Paper 2 cascade hypothesis (alternative post-H1 direction)
- VT-7 (anchor-scheduling evidence base) — adjacent concern about the
  calendar field's behavioral meaning
- Brain dump → AI subtask decomposition (this file)

---

## Feature integration map
*Maintained as features are parked. Last updated: April 17, 2026.*

Shows how parked features connect to each other and to the shipped
computation layer.

```
Brain dump (F1) ←→ H2 deadline proximity (F2)
       ↕                        ↕
  bias_factor    ←→    calibration_nudge
       ↕                        ↕
  cascade_score  ←→    archetype_classification
       ↕                        ↕
fragmentation_index ←→ category_auto_creation
       ↕
insights (11 generators, extensible)

Mid-session check-in → bias_factor + micro_mirror
                     + execution_shape (new)
Sequential execution → cascade_score (intra-task)
                     + fragmentation_index
```

**Diagnostic rule:** if a proposed feature touches fewer than 3 existing
variables, it is an isolated addition. Redesign to integrate or park until
integration path is clear. See `docs/design_patterns/rules_vs_agency.md`
§Integration-not-isolation principle.
