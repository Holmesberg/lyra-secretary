# Lyra — Parked Ideas

*Ideas captured but not executed. Each has a revisit condition. Do not build
before conditions are met.*

*Format: short description, why parked, what triggers revisiting, date captured.*

---

## Bayesian causal network — per-user personalization endgame
*Captured: 2026-04-22 evening. Operator recalled from memory while
debugging a user report ("understands some of my gaps but doesn't
REALLY get me"). Verified absent from the docs corpus before writing
this entry — only related-but-different references are Bayesian
weighting for BCI+self-report signal fusion (`archive/FEATURES.md:583`,
`README.md:19`) and Bayesian shrinkage for bias_factor
(`docs/methodology.md:62-69`, `README.md:190`). Neither is structure
learning. Operator remembered the shrinkage formula as living in a
`clustering_spec.md` file — that file does not exist; the formula is
in methodology.md.*

**Idea.** Phase 6+ personalization layer beyond cluster priors +
shrinkage. Given the variables Lyra already collects (readiness,
planned_duration, category, time_of_day, delta, scope_density, pause
patterns, cascade signatures, initiation delay, etc.), discover the
**per-user causal graph** that explains HOW those variables produce
failure. Output: directed acyclic graph showing which variables cause
which outcomes for THIS user.

**Why this addresses the "doesn't REALLY get me" feedback.** Prior
layers produce "people like you" personalization:
- Layer 1 (published priors from Buehler/Kahneman): generic by design
- Layer 2 (archetype cluster priors): cohort-level
- Layer 3 (shrinkage blend toward personal data — methodology.md:62-69):
  still a lookup table per (category, time_of_day) cell

These produce *correlations*. A Bayesian causal network produces
*mechanism*. The difference: Layer 1-3 answer "what typically happens
to people like you"; the causal network answers "given YOUR readiness
pattern + YOUR category + YOUR time-of-day, the causal path to
overrun goes through scope inflation, not time estimation — here's
the intervention point."

**Method.**
- Library: `pgmpy` (Python, MIT-licensed). Structure-learning
  algorithms: PC (constraint-based) or GES (score-based).
- Every variable already in the schema becomes a node. The network
  discovers the edges — causal structure + conditional-probability
  tables.
- Queryable per user: "given readiness=4 + category=dev + time=11am,
  what's the most probable mechanism of failure?" Returns path
  through the graph, not just endpoint prediction.

**Data volume.**
- Structure-learning stability gates: **n ≥ 50 users × n ≥ 20
  sessions each ≈ 1,000+ data points minimum.** Population-level
  causal structure first; per-user individual graphs later
  (50+ sessions per user for stable per-user DAG).
- At current scale (5 users × ~10 sessions ≈ 50 data points),
  attempting structure learning produces noise. Phase 6+ for a
  reason.

**Connection to VT-22 (scope inflation) — this is the key structural
insight.** VT-22 manually hypothesizes what the Bayesian network
would discover automatically. MANIFESTO Rule 12 pre-registers the
mediation test: `readiness → scope_density → delta` (not `readiness
→ delta` directly). If true, scope inflation is the causal mechanism
for high-readiness overruns.
- A Bayesian network learned from multi-user data would either
  confirm that edge (validating VT-22 *structurally*, not just
  inferentially) OR reveal a different causal path — e.g., `readiness
  → task_difficulty_selection → delta`, matching VT-22 competing
  hypothesis (b).
- When the network matures, VT-22-style manual mediation tests
  become a constrained special case — "does the discovered DAG
  include the edge `scope_density → delta` with non-zero conditional
  probability, after controlling for ancestors?"

**Integration with existing layers (replacement, not bolt-on).**
This completes the 4-layer stack, each adding specificity as data
accumulates:

| Layer | When active | What it produces | Status |
|-------|------------|------------------|--------|
| 1. Published priors | Session 0 | "Research says people underestimate by 40-60%" | Shipped |
| 2. Archetype cluster priors | Sessions 1-30 per cell | "People in your cohort underestimate by 1.4×" | Designed (Phase 5) |
| 3. Shrinkage blend | Sessions 1-30 per cell, weighted | `personal_weight × personal_mean + (1 - personal_weight) × archetype_prior` (methodology.md:62-69) | Designed (Phase 5.5+) |
| 4. Personal bias_factor (full) | Sessions 30+ per cell | Pure per-(user, category, time_of_day) estimate | Shipped (commit bac6fc2) |
| 5. Bayesian causal network (this entry) | n ≥ 50 users × 20 sessions | Population-level causal structure + per-user mechanism trace | Parked — Phase 6+ |
| 6. Individual per-user DAG (endgame) | 50+ sessions per user | Fully individual causal graph | Parked — Phase 7+ |

**Revisit conditions** — all must be met before building:
- n ≥ 50 users with ≥ 20 sessions each (data-volume gate)
- H1 / VT-22 status is resolved (Paper 1 analysis closed so the
  network isn't used to steer a still-live pre-registered test)
- Phase 6 shrinkage blend (Layer 3) is already shipped and stable
  (natural predecessor — the network adds mechanism on top of a
  working magnitude-estimation stack)

**Do not:**
- Attempt at n < 20 users — discovered structure will be noise and
  misinform subsequent design
- Use for individual per-user graphs before that user has 50+
  sessions — individual-level structure learning is much hungrier
  for data than population-level
- Bolt on without Layers 1-4 below it — the network is for
  *mechanism discovery*, not a replacement for the main
  personalization surface

**Connection to the immediate need.** The clustering survey (Layer 2
in the Phase 5 build plan) is the pre-Spring-School fix for "doesn't
REALLY get me." The Bayesian network is the post-Spring-School,
post-H1-resolution endgame. Not a substitute; the endpoint.

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

> **STATUS: ELEVATED to active design — 2026-04-25.** Per operator
> decision (Option B locked), the deadline mechanism is being built
> mid-alpha rather than waiting for Phase 6+. The "Do not build
> mid-experiment" caveat below is overridden by the priority hierarchy
> (operator's time > users' time > research). Current design lives in
> `docs/deadline_mechanism_design.md` with pre-registration plan for
> the soft-warning RCT to mitigate the H1 contamination concern. The
> historical parked-idea text is preserved below as the original
> hypothesis statement; treat the design doc as canonical.

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

---

## Autonomous planning — the relief-instrument endgame
*Captured: 2026-04-29 evening (operator-proposed during the LMS-wedge ship —
"later on we can manage people's plans autonomously using their patterns,
deadlines and given tasks. Plan for them basically.")*

**Idea.** A fourth intelligence mode beyond Full / Light / Manual (see
`feedback_graduated_intelligence_controls.md`): **Auto**. Lyra observes
the user's tasks, deadlines, bias_factor cells, pause patterns, cascade
signatures, archetype priors, and externally-imported data (Moodle
deadlines via alembic 041, future Google Cal context, etc.) and
proposes — then, with consent, executes — a daily/weekly plan on the
user's behalf. The user wakes up to "here's what I'd plan for tomorrow,
confirm or edit." Eventually: silent overnight commit with morning
summary.

**Why this is the natural endpoint, not a separate product.** Per
`project_relief_instrument_reframe.md` the user-facing mechanism is
chaos→structure. Today the user provides the chaos (brain-dump,
deadlines, manual scheduling) and Lyra applies the structure
heuristically. Autonomous planning collapses the user side too — Lyra
provides BOTH the chaos translation AND the structure. It is the
furthest extension of "make planning disappear" that the LMS sync
already started.

**Preconditions before this ships:**
1. **Dense per-user data.** Per `project_logging_friction.md` even the
   operator forgets to log after 3 weeks; an autoplanner trained on
   sparse data is just generic heuristics with someone's name on it.
   Floor: ≥30 EXECUTED tasks per user across ≥3 categories with
   pre/post readiness on ≥60% of them. The Moodle import (alembic 041)
   is exactly the right pre-cursor because it pulls dense deadline
   data without asking the user to type it.
2. **Trust runway from smaller wins first.** Sequencing matters more
   than capability:
   - Step 1 (DONE): LMS sync — pulls deadlines correctly, no agency.
   - Step 2: Calibration nudge accuracy at user-visible level (see
     `services/bias_factor_service.py` Rule 13 blend) — proves Lyra's
     suggestions are calibrated before it's allowed to act on its own.
   - Step 3: One-task-at-a-time autonomous reschedule with explicit
     confirmation ("Lyra moved your debugging block from 11am to 2pm
     because you usually under-perform mornings on dev work — undo?").
   - Step 4: End-of-day "tomorrow's plan" preview surface, requires
     one-tap confirm.
   - Step 5: Silent overnight autoplan, morning summary, undo per
     block.
   Skipping to Step 5 without 1–4 risks the creepy-smart fear before
   the user has seen the system get smaller things right.
3. **Pre-registered VT for autonomous-action contamination.** Once
   Lyra is moving tasks on its own, every signal (planned_duration,
   readiness, delta) is partly a function of Lyra's own decisions —
   the Hawthorne / instrument-intervention threats compound. Need a
   sibling to VT-21 (narrative internalization) and VT-25 (label
   reinforcement): VT-XX "autonomous-decision contamination of H1."
   Distinguishing test: Lyra-planned blocks vs user-planned blocks,
   stratified bias_factor; if they diverge >0.20 effect size,
   autoplanning is intervening on the very variable it's trying to
   measure.
4. **Reversibility per action.** Every autonomous action must produce
   an undo signal — not just an undo button, but an undo that itself
   becomes training data ("Lyra moved this; user undid; never do this
   pattern again"). Fits the existing undo-cache pattern
   (`utils/redis_client.py` 30s TTL) extended to 24h for autoplan
   actions.

**Architectural slot.** Add to `feedback_graduated_intelligence_controls.md`
3-mode ladder as a fourth mode: Full / Light / Manual / **Auto**. Auto
is opt-in only, never default for new users. Probably gated on
`user.first_task_at + 60 days` AND `≥30 EXECUTED tasks` AND user
explicit toggle. New service: `services/auto_planner.py` consuming
the same bias_factor cells + cascade_score + scope_density that
calibration nudge already reads — no new measurement instruments,
just a different consumer of the existing ones.

**Method (sketch — do not build before preconditions).**
- Daily cron at user's local 22:00 (per `user.timezone`): query active
  deadlines + brain-dump backlog + bias_factor cells + pause patterns.
- Solve the schedule as constrained optimization: minimize expected
  delay_minutes (per Rule 14 H2 prediction) + minimize cascade
  fragmentation, subject to deadline constraints.
- Write proposal to a new `plan_proposal` table (NOT `task` — proposals
  aren't tasks until accepted). Frontend renders "Tomorrow's plan" card
  on `/today`.
- One-tap accept → tasks created via existing `TaskManager.create_task`
  with `task_source='auto_planned'` flag (new TaskSource enum value).
  One-tap reject → row deleted, training signal logged.

**Trigger to revisit.**
- After Phase 6+ (post-Jun-18-25 retention checkpoint) AND ≥30 users
  AND median ≥30 EXECUTED tasks per active user AND H1 has resolved
  one way or the other (so we know if delta is the right metric to
  optimize).
- Also conditional on: Step 2 (visible calibration accuracy) shipped
  and validated against user qualitative read first ("did Lyra's
  nudges help you or annoy you?").

**Do not:**
- Build before n ≥ 30 users with dense data — autoplanner trained on
  sparse data IS the failure mode.
- Skip Steps 2–4 of the trust runway — silent overnight autoplan as
  v1 of autonomy is exactly the creepy-smart fear from
  `feedback_check_cognitive_load_layer.md` realized in production.
- Default to Auto for new users at any phase. Always opt-in, with the
  warm-tone framing per `feedback_warm_tone_copy.md`.

**Connection to current work.** The Moodle LMS sync (alembic 041,
2026-04-29) is structurally the first step toward this — it pulls
dense external data without user friction. Every Moodle-imported
deadline becomes a constraint the autoplanner will eventually optimize
against. The fact that we already flagged `external_source` and
pre-registered VT-29 (External-Deadline Contamination) means the
autoplanner inherits the right research-integrity scaffolding from
day one.

---

## LMS submission timestamps via Moodle Web Services (Path B)
*Captured: 2026-04-29 evening (operator: "a nice to have addition would
be to add ALL LMS deadlines (even submitted ones) for data, especially
seeing when the user submitted their tasks, is that possible?"). Yes —
feasible, parked because the iCal-only path A shipped an hour ago and
needs validation before adding more LMS surface.*

**Idea.** Pull not just future + recent due dates (current iCal feed)
but every assignment's full lifecycle metadata: submission timestamp,
grade, attempt count, late flag. Per-user submission timestamps are the
single highest-signal procrastination data point we don't have today —
"deadline was 23:59, user submitted 23:54" tells us things `delay_minutes`
alone cannot.

**Why iCal can't do this.** The `/calendar/export_execute.php` feed only
exposes calendar events (assignment due dates as future VEVENTs). Once
an assignment passes its due date the row stays in the feed but never
acquires submission status — that data lives in Moodle's gradebook
tables (`mdl_assign_submission`, `mdl_grade_grades`), not the calendar.
No combination of `preset_what` / `preset_time` will surface it.

**Path B architecture (when ready to build).**
- **Auth surface.** User generates a personal Moodle Web Services token
  in Moodle → Preferences → User account → Security keys. (Some schools
  disable this and require admin issuance — handle that error path.)
  Backend stores per-user `moodle_ws_token` (Text, plaintext v1, same
  trust class as `moodle_ics_url` and `google_refresh_token`).
- **API endpoints.** Moodle's standard REST surface (works on the same
  ASU Engineering Moodle 3.7 we tested):
    - `core_enrol_get_users_courses(userid)` — user's enrolled courses
    - `mod_assign_get_assignments(courseids[])` — assignments per course
    - `mod_assign_get_submissions(assignmentids[])` — submission rows
      (status, timecreated, timemodified, gradingstatus)
    - `gradereport_user_get_grade_items(courseid, userid)` — grades
- **Schema additions** (alembic 042 candidate):
    - New `lms_submission` table:
      `(id, user_id, external_source='moodle_ws', external_assignment_id,
       external_submission_id, deadline_id (FK nullable), submitted_at_utc,
       grade, late, attempt_count, voided_at, fetched_at)`
    - Backlink to `deadline` so the existing OVERDUE banner can grey out
      submitted-on-time imports (they're no longer pending action).
    - `WHERE external_source IS NULL` filters extend to the new table —
      same VT-29 contamination pattern.
- **Sync job.** New APScheduler job every 6h per user with non-NULL
  `moodle_ws_token`. Pulls course list → assignments → submissions for
  each user. Per-cycle cap (200 assignments) so a heavy semester load
  doesn't pile up.
- **UX surface.** Two visible payoffs:
    - `/today` OVERDUE banner: count drops the moment a submission lands
      — instant gratification, "Lyra noticed I just submitted."
    - `/insights` new card: "Submission lead time" — distribution of
      `(submitted_at - due_at)` in minutes, stratified by course code.
      Negative values cluster near zero = procrastination signal; large
      negative = preparedness signal. Per-user histogram is the
      academic-procrastination instrument the operator is asking for.

**Research value.** This is genuinely new measurement we can't get any
other way:
- `submission_lead_time = submitted_at - due_at` (signed minutes;
  negative = on time, positive = late)
- Cross with `bias_factor_observed` per category from H1 work — does
  high planning-overrun correlate with last-minute submission?
- Cross with VT-22 scope inflation: do users who under-scope ALSO
  submit closer to deadline?
- All without any user logging burden — Moodle does the recording.

**Why parked, not built now.**
- Path A (iCal sync) shipped 6h ago. Validate the wedge with real
  alpha-cohort users first — if Q12 of the post-week-1-2 survey
  (Appendix B of strategic plan) shows <50% interest in LMS sync,
  Path B is wasted effort.
- Path B is per-school-fragile: some Moodle admins disable user-level
  WS tokens. Need to know how many of the trusted alpha cohort can
  actually generate one before building the auth surface.
- Adds a second credential per user (token, not just URL). Doubles the
  key-rotation / disconnect / re-consent surface area.
- Submission lead time is rich research signal but not retention-critical
  in the way the iCal wedge is. Phase 6+ work, not pre-alpha polish.

**Trigger to revisit.** When ALL of:
- Path A iCal sync has 5+ active alpha users for ≥2 weeks
- Q12 of post-week-1-2 survey returns ≥4/7 enthusiastic
- One alpha student has confirmed they can self-issue a Moodle WS token
  on their school's install
- Operator has 3+ free days for a Phase 2 LMS push (post-alpha-launch
  stabilization)

**Implementation estimate at trigger time.** ~3-4 days for Path B MVP:
schema + WS client + sync job + frontend token-paste flow + insights
card. Reuses the credential storage, sync-job, and external-source
patterns already shipped for Path A.

**Cite when revisiting.** `docs/moodle_lms_integration.md` (Path A
architecture this extends), MANIFESTO.md §VT-29 (contamination test
that already covers Path B's writes by virtue of the external_source
filter), and `services/moodle_ics_sync.py` (the sync-service shape to
mirror for the WS variant).

---

## VT-19 quantification — auxiliary diagnostic for H1 contamination
*Captured 2026-04-30 morning, from ChatGPT manifesto-review pass on
2026-04-29 evening: VT-19 (post-task anchoring contamination of
signed_discrepancy) is acknowledged in the manifesto but never
quantified. Without quantification, we can't tell whether a positive
H1 ρ is "people mispredict → they overrun" (cognition error model)
or "people who overrun reconstruct themselves as having been less
ready" (post-hoc anchoring artifact).*

**Idea.** Add a single auxiliary diagnostic computation to the H1
analysis path:

```
ρ_aux = spearman(post_task_reflection, duration_delta_minutes)
```

Run alongside the primary H1 ρ at every H1 analysis cycle. No design
disruption — just one more correlation against existing fields.

**Interpretation:**
- `ρ_aux` low (< 0.20) → VT-19 is a small-magnitude effect; H1's
  signed-discrepancy construction is meaningful as a forward-looking
  cognition signal.
- `ρ_aux` high (≥ 0.40) → VT-19 dominates; signed_discrepancy is
  partly observational artifact (overrun → anchored low reflection
  → inflated discrepancy → flips ρ direction). H1 conclusions must
  be reframed: "rank-order alignment between two outcome-anchored
  distortions" rather than "overconfidence predicts overrun."
- `ρ_aux` middle (0.20–0.40) → publish both ρ and ρ_aux, let readers
  judge.

**Minimal implementation effort.** ~15 LOC in the H1 analysis
notebook / `analytics/discrepancy.py`. Touches no schema, no API.
Single Python function added to whatever computes Spearman ρ for H1.

**Why parked, not built now.**
- The H1 analysis itself is gated on n≥60 paired sessions per the
  manifesto kill criterion. Currently ~55-60 (operator-heavy). The
  H1 analysis hasn't fired yet; the auxiliary diagnostic ships as
  part of the same analysis cycle.
- Adding it now without H1 firing means the diagnostic sits dormant
  with no use case. Bundle it with the H1 analysis sprint.

**Trigger to revisit.** When n≥60 H1-eligible paired sessions land
and the operator runs the pre-registered H1 analysis. Do this fix
in the SAME session — both ρ and ρ_aux land in the H1 publication
together.

**Source.** ChatGPT manifesto-review 2026-04-29: "VT-19 is good, but
incomplete. You are not explicitly testing post_task_reflection ~
duration_delta. Without this, you cannot quantify VT-19's actual
magnitude."

---

## H1 learning-rule statistical fix — Δρ ≥ 0.10 → Fisher-z bootstrap CI
*Captured 2026-04-30 morning, from ChatGPT manifesto-review pass.
The pre-registered H1 learning rule ("if ρ improves by ≥ 0.10 across
session halves, declare improvement") is statistically fragile at
n≈30 per half because Spearman ρ instability at that N is high. A
0.10 difference is within expected sampling variance and could fire
spuriously.*

**Idea.** Replace the simple Δρ threshold with a proper bootstrap
confidence-interval test on the Fisher-z transformed ρ values:

```python
def split_half_learning_test(pairs_first_half, pairs_second_half,
                              n_bootstrap=2000, ci=0.95):
    rho_a = spearmanr(pairs_first_half).correlation
    rho_b = spearmanr(pairs_second_half).correlation
    z_a = arctanh(rho_a)
    z_b = arctanh(rho_b)

    # Bootstrap the difference
    deltas = []
    for _ in range(n_bootstrap):
        sample_a = resample(pairs_first_half)
        sample_b = resample(pairs_second_half)
        z_a_boot = arctanh(spearmanr(sample_a).correlation)
        z_b_boot = arctanh(spearmanr(sample_b).correlation)
        deltas.append(z_b_boot - z_a_boot)

    lower = percentile(deltas, (1-ci)/2 * 100)
    upper = percentile(deltas, (1+ci)/2 * 100)

    # "Learning" requires the CI to be entirely above 0
    learning_detected = lower > 0
    return learning_detected, (lower, upper), (rho_a, rho_b)
```

This catches:
- False positives: if the CI overlaps zero, no learning claim
  regardless of point-estimate Δρ
- False negatives: if true difference is < 0.10 but CI is well above
  zero (true small effect), still detected

**Why parked, not built now.** Same as VT-19 quantification — gated
on H1 firing at n≥60. Add to the same analysis cycle.

**Trigger to revisit.** Same as VT-19: H1 analysis sprint at n≥60.

**Source.** ChatGPT manifesto-review 2026-04-29: "The Δρ ≥ 0.10 rule
is within expected sampling variance at n≈30 per half. Better:
Fisher-z difference with bootstrap CI overlap."

---

## H3 priority — keep S3 + S4, defer S1 + S2 instrumentation
*Captured 2026-04-30 morning, from ChatGPT manifesto-review pass on
H3 (multi-faction control model with five signatures S1-S5). ChatGPT's
read: S3 (post-overrun trajectory classification) and S4 (cross-
category variance decomposition) are the genuinely interesting parts
that may survive contact with real data; S1 (latency = avoidance) and
S2 (switching = escape policy) are confound-sensitive enough that
they'll likely collapse into "context effects" under multi-user data.*

**Idea (no code change, just prioritization).** When H3 instrumentation
ships in Phase 6+, build S3 + S4 first; defer S1 + S2 until S3/S4
results are in.

**Why S3 is high-value.**
> "Tests policy update behavior, not static prediction. Distinguishes
> correction / inertia / avoidance. Close to a real control-system
> property: 'Does error propagate into future parameter adjustment
> or behavioral suppression?'"

**Why S4 is high-value.**
> "Tests separability by task manifold. Low separability → single
> global controller. High separability → context-conditioned
> policies. A real question in behavioral modeling."

**Why S1 + S2 are likely to collapse.**
> S1 (latency = avoidance): "Latency ≠ avoidance unless you control
> for scheduled vs unscheduled initiation, external interruption
> risk, cognitive load of category. Underidentified with current
> observables."
>
> S2 (switching = escape policy): "Switching is context-driven, not
> escape policy" likely interpretation under multi-user data.

**Risk to acknowledge if shipping S3 + S4 first.** ChatGPT also
flagged the over-attribution risk: "factions" vs "conditional
policy structure" are observationally similar but ontologically
different. To distinguish, eventually need intervention experiments
(forced-delay perturbations, randomized constraint manipulations).
Pure correlation mining of S3/S4 is "high-resolution behavioral
decomposition," not "validated internal-architecture model."

**Why parked, not actioned now.** H3 instrumentation isn't shipped
yet — no schema, no analysis path, no kill criteria gates fired.
This is a Phase 6+ priority note for when that work begins.

**Trigger to revisit.** When the operator queues H3 instrumentation
work — likely after the Jun 18-25 retention checkpoint validates
that the alpha is producing dense enough data to power any factional
analysis at all.

**Source.** ChatGPT manifesto-review 2026-04-29 (third pass on H3):
"S3 and S4 are the only parts likely to survive contact with real
data. S1 and S2 are highly confound-sensitive and will likely
collapse or become 'context effects.'"

---

## Proactive Lyra — chat-thread interventions, instrumented

*Captured: 2026-04-30 evening. Operator-prompted by ChatGPT critique
of the JARVIS/Lyra ship: "deep behavior analysis is only valuable if
it changes behavior — otherwise you've built a sophisticated mirror."
Reframed mid-conversation by operator: the boundary isn't
"proactive = contamination" but "uncontrolled intervention =
contamination, instrumented + pre-registered intervention = data."
The existing manifesto already proves this with VT-17, VT-21, Rule 11.
Captured here, not built — Lyra-the-assistant stays reactive (chat-
on-demand) for now while we accumulate enough operator dogfood data
to estimate baselines for each proposed intervention's acceptance
threshold.*

**Why now (concept), but not now (build).**

Reactive Lyra (what shipped 2026-04-30) is a high-resolution
introspection engine: ask a question, get a multi-cut read of your
data, decide what to do. Useful for the operator's stated rationale
("analyze my behavior DEEPLY") but vulnerable to ChatGPT's critique
— insight without leverage = mirror. The natural next axis is
proactive intervention: Lyra speaks first when patterns cross a
pre-registered threshold, the user accepts/dismisses, the system
measures whether intervention shifted behavior, kill criterion fires
if acceptance rate fails or if the intervention contaminates the
H1/H2/H3 measurement set.

**The shape of three pre-registrable interventions** (each a
candidate VT-30 / VT-31 / VT-32 — sequence is illustrative, not
locked):

### Pause cluster intervention (VT-30 candidate, extends VT-17)

**Trigger.** ≥3 EXECUTING sessions in a 24-hour window where the
user stopped at <50% planned duration (the existing early-stop gate
in `services/stopwatch_manager.py`).

**Lyra fire.** Single chat-thread message: "I noticed three early
stops today. Cut next session to 15 min?" — opens an action chip
that pre-fills the next planned task at 15 min planned duration.
Operator can accept / dismiss / mute-this-pattern.

**Pre-registered acceptance formula** (frozen at intervention launch
under VT-17's existing precedent):
```
acceptance_count(user, window=14d) := count of chat-thread fires
  WHERE acceptance_chip clicked within 1 hour of fire
total_fires(user, window=14d) := count of chat-thread fires
  WHERE parent_firing_id IS NULL
acceptance_rate := acceptance_count / total_fires
```
Per-user thresholds: ≥ 0.40 = ship; < 0.20 = kill the intervention
type (chat fires of this kind suppressed for that user — pattern
still shows in /insights but Lyra doesn't volunteer it).

**Distinguishing analyses** (frozen at launch):
- VT-30a — Sessions following an accepted intervention should show
  ≥10% reduction in early-stop rate vs the user's own baseline.
  Detected: feedback loop is closed. Not detected: intervention
  produces compliance without behavior change (theatrical click).
- VT-30b — Sessions following ANY fire (accepted OR dismissed)
  should not show systematic shift in `planned_duration_minutes`
  beyond the chip-driven adjustment. If they do, intervention is
  internalizing as a planning anchor (VT-21 narrative-internalization
  mechanism, applied to interventions instead of nudges).

### Readiness inversion forecast (VT-31 candidate, wires bias_factor → preemptive plan suggestion)

**Trigger.** User about to plan a session in a (category, time-of-
day) cell where the existing `bias_factor_service.blend()` produces
a personal_weight ≥ 0.5 estimate of bias_factor ≥ 1.5 — i.e., the
operator has enough personal data in the cell AND historical pattern
shows systematic ≥50% overrun.

**Lyra fire.** Inline chat suggestion at task-creation time (not the
existing calibration_nudge modal — Lyra speaks alongside it): "Your
last 4 development tasks at this time of day overran by 40+ min on
average. Plan for 60 instead of 40?" Operator accepts (replaces
duration) / dismisses (keeps original) / explains-why (free text
captured for VT-22 scope-inflation analysis).

**Why parallel to calibration_nudge, not replacement.** The
calibration_nudge is a system-driven suggestion ("we suggest 83 min
based on your bias_factor 1.8"). Lyra's version is a conversational
framing of the same underlying signal — testing whether identical
data delivered conversationally vs. modally produces different
acceptance rates. This is the missing A/B in the manifesto's existing
calibration_nudge vs creation-suggestion distinction.

**Pre-registered analysis.** Within-user split: half of qualifying
sessions get the calibration_nudge modal only (control), half get
both modal + Lyra chat fire (treatment). At n ≥ 30 paired sessions
per user, compare: (a) acceptance rate of the duration adjustment,
(b) post-session delta. If chat-fire arm shows higher acceptance AND
better delta, ship Lyra-as-replacement for the modal. If chat-fire
arm shows higher acceptance but no delta improvement, the chat
surface is a compliance theater and should not replace the modal.

### Cascade morning-skip intervention (VT-32 candidate, operationalizes the cascade hypothesis)

**Trigger.** First planned task of the user's day (lowest
`planned_start_utc` for that local-date) transitions to SKIPPED.

**Lyra fire.** Chat-thread message within 30 min of the skip:
"Mornings where the first task skips, you tend to skip 2.3× more
through the rest of the day. Want me to clear your next 2 hours so
you can reset?" — accepts triggers a /v1/today/clear-window endpoint
(does not exist yet, would be a small ship) that voids all PLANNED
tasks in the next 2 hours. Operator accepts / dismisses / asks Lyra
to elaborate.

**Pre-registered analysis (combines intervention + Paper 2 cascade
falsification).** This is the FIRST intervention test of the cascade
hypothesis (manifesto Paper 2). If accepting the clear-window
intervention produces ≥30% reduction in skip rate over the
subsequent 6 hours vs the user's own historical post-morning-skip
baseline, the cascade is intervention-responsive (i.e., real and
correctable). If acceptance produces no reduction, cascade is either
not real OR not correctable via window-clearing — both are
findings, the second more interesting because it suggests morning
skips trigger something deeper than schedule disruption.

**Why parked, not built now.**

Three structural reasons:
1. **Insufficient baseline data per intervention type.** Each
   intervention's acceptance threshold needs a pre-registration that
   can only be set defensibly after observing baseline rates. VT-17
   was set with reference to existing pause-prediction behavior;
   VT-30/31/32 need similar precedent. Operator has 43 EXECUTED
   sessions as of 2026-04-30 — enough for reactive Lyra to be
   useful, not enough to estimate intervention acceptance rates with
   confidence.
2. **Reactive Lyra needs dogfood time.** Operator stated the
   primary purpose is dogfooding for usability before shipping as a
   premium feature. Reactive Lyra hasn't accumulated enough operator
   conversation history to know which questions the operator
   actually asks vs which the operator avoids. That answer determines
   what proactive interventions matter.
3. **Premium framing depends on this distinction.** ChatGPT's
   "we manage your execution for you" framing was rejected as
   commodity-positioning that erases Lyra's research-credibility
   differentiation. The right premium framing — "your data, your
   pattern, surfaced when it matters" — requires the proactive layer
   to exist AND be measurably effective. Building the layer first
   and discovering the framing doesn't sell would burn the operator's
   most limited resource (time).

**Trigger to revisit.**

Whichever fires first:
- Operator dogfood passes 200 EXECUTED sessions (enough to set
  baseline acceptance thresholds for VT-30/31/32).
- Reactive Lyra usage shows operator asking the SAME pattern question
  ≥3 times in a week (signal that proactive surfacing of that
  pattern would have value) — measurable from the
  `jarvis_invocation` audit table by tool_name + tool_args.
- Retention checkpoint (Jun 18-25) validates that any non-operator
  user ever crosses the activity threshold where these interventions
  would fire.

**Operationalization checklist when revisited.**

For each VT (30/31/32) before ship:
- Pre-register the acceptance formula in MANIFESTO.md alongside the
  existing VT-17 / VT-17d formulas
- Pre-register at least two distinguishing analyses (one for
  intervention efficacy, one for VT-21-class internalization risk)
- Wire the chat fire to write a `reflection_view_log` row with
  `reflection_type='proactive_lyra_<vt_id>'`
- Add a per-user opt-out toggle in /settings under the existing
  graduated intelligence controls (Full / Light / Manual)
- Add a kill-switch flag in the relevant service so the intervention
  can be retracted without code revert if a per-user analysis trips

**Source.** ChatGPT critique 2026-04-30 evening + operator
reframing in same conversation: "uncontrolled intervention =
contamination, instrumented + pre-registered intervention = data.
The goal isn't to avoid proactivity — it's to contain it inside the
experiment design." Captured to preserve the insight without
disrupting reactive Lyra dogfood.

---

## Lyra-as-OpenClaw — copy the agent-OS architecture into Lyra core

*Captured: 2026-04-30 evening. Operator observation while validating
the GLM-5.1 swap in OpenClaw: "the real endgame is copying part of
openclaw's architecture and integrating it into our system. something
like the skill.md, etc."*

**The core insight.** OpenClaw isn't just a chat bot — it's a small
agent OS. Each capability the agent has is declared in a `SKILL.md`
file (the same file Lyra exposes to OpenClaw at
`openclaw/skills/lyra-secretary/SKILL.md`). The skill file declares:
verification preamble, hard rules, endpoints, expected behaviors,
required fields. The agent reads the skill, the runtime enforces it,
and the LLM operates within those constraints. Same shape:
declarative rules + runtime enforcement + LLM acting inside the
sandbox.

The Lyra-side parallel: a Lyra agent (the chat surface we just shipped
2026-04-30) has tools defined in `backend/app/services/jarvis_tools.py`
as Python schemas. That's one notation; OpenClaw's SKILL.md is
another, friendlier-to-write notation. The two architectures could
converge — Lyra gains the declarative `.md`-based skill format,
OpenClaw can read native Lyra skills.

**Why this matters strategically.**

1. **Skill ecosystem.** If Lyra ships skills as `SKILL.md` files,
   third-party integrators (and eventually users) can write skills
   without touching Python. OpenClaw already proves the model works
   for non-trivial tooling — the operator's `lyra-secretary` skill
   is a working example that drives 12+ endpoints declaratively.
2. **Cross-runtime portability.** A skill written for Lyra could run
   under OpenClaw's runtime (already does) AND under Lyra's own
   agent runtime (the Lyra-the-assistant chat surface). Operator
   wouldn't have to maintain two sets of tool definitions.
3. **User-facing skill catalog.** Phase 6+ thinking: users could
   browse a skill catalog (Moodle skill, Notion skill, GCal skill,
   each their own SKILL.md) and toggle them on/off, similar to how
   OpenClaw manages its plugin allow-list. The operator could ship
   first-party skills + open the door to community skills later.
4. **Reduces Lyra's surface to a kernel.** If skills live as
   `.md`-declared bundles, the core Lyra codebase shrinks — most of
   what's currently in `backend/app/services/*` becomes a skill, not
   a hardcoded service. Mom/sister/students can install only the
   skills they need (no Moodle skill if they don't have an LMS).

**What this is NOT.** Not "copy OpenClaw's whole architecture into
Lyra." OpenClaw has a lot of agent-OS surface area (sandboxes, exec
approvals, multi-agent coordination, browser automation, etc.) that
Lyra doesn't need at v1. The candidate to copy first is JUST the
skill declaration format + the runtime that loads them. Everything
else stays in OpenClaw's stack.

**Concrete first-ship sketch (when revisited).**

1. Define a Lyra `SKILL.md` schema (verification preamble + hard
   rules + tool list + endpoints + invariants — mirroring the
   format already at `openclaw/skills/lyra-secretary/SKILL.md`)
2. Write a Python loader that reads `SKILL.md` files from a
   `skills/` directory + emits OpenAI-style tool schemas
3. Migrate ONE existing service (probably brain dump or pattern
   summary) from `jarvis_tools.py` Python definitions to a
   `skills/brain_dump/SKILL.md` file
4. Verify Lyra's chat surface picks up the migrated skill as a
   first-class tool with no behavior change
5. Document the migration path so additional services can follow
6. Long-term: ship a `/settings/skills` UI for users to enable/disable
   skills (post-retention checkpoint)

**Why parked, not built now.**

1. **Brain dump P0s come first.** LYR-114 (silent partial-commit) and
   LYR-115 (durations ignored) are pre-alpha blockers per the
   2026-04-30 stress test. Skill-architecture refactor is a code
   reorganization, not a user-facing fix. Land the bugs first.
2. **Need the JARVIS-renamed-Lyra-chat surface to dogfood first.**
   The chat surface shipped 2026-04-30 with 6 read tools + 4 write
   tools. Need 2-4 weeks of operator usage to know which tool
   shapes worked + which need refactor. Migrating to skill.md before
   we know the right tool shapes would lock in the wrong abstraction.
3. **Skill catalog UI is a Phase 6+ concern.** Multi-skill
   management is meaningful only when there are ≥5 skills + multiple
   users. Today there are ~6 internal tool-shaped surfaces and 1
   user (operator). Build the abstraction when the inventory
   justifies it.

**Trigger to revisit.**

Whichever fires first:
- ≥5 distinct tool-shaped capabilities exist in `jarvis_tools.py`
  AND maintaining them in Python becomes the friction point (e.g.,
  "we need to add a 7th tool, and it would benefit from being
  declarative")
- An external integrator (or operator's mom!) asks to write a Lyra
  skill without touching Python — the .md format becomes the
  ergonomic answer
- Phase 6+ work begins on user-facing skill catalog
- OpenClaw publishes a stable, externally-maintained skill-runtime
  package that Lyra could import directly instead of re-implementing

**Source.** Operator 2026-04-30 evening, immediately after validating
GLM-5.1 swap in OpenClaw. Original phrasing: "the real endgame is
copying part of openclaw's architecture and integrating it into our
system. something like the skill.md, etc." Captured to preserve the
direction without disrupting current pre-alpha sprint priorities.
