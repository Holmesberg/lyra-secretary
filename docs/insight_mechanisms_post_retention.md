# Insight Mechanisms — Post-Retention Queue

**Status:** PARKED. Do not implement before the Jun 18–25 week-6-8 retention checkpoint
(see `docs/strategic_decisions_april_24.md`). Adding novelty surfaces pre-retention
contaminates the retention signal — you cannot tell if users stayed for the product
or for the new toy.

**Created:** 2026-04-25, midterm halt window.
**Owner:** Operator (Ali).
**Trigger to revisit:** Stage 2 GREEN at the post-novelty checkpoint.

---

## Why this document exists

User feedback (Omar, Apr 23): the system should not just *understand* the user better,
it should *give back* — the data the user supplies should produce visible, surprising
output, not just better passive modeling. This document captures the highest-leverage
ways Lyra can do that, sequenced for after retention is validated.

The user's two target reactions:
1. **"WHAT, how did it know?"** — surprise from accuracy/specificity.
2. **"I didn't know this about myself but it makes sense"** — self-discovery from a
   pattern invisible to introspection.

These are different. The first is *prediction quality*. The second is *insight
generation*. The mechanisms below are sorted by which reaction they produce.

---

## The unifying frame: memory asymmetry

The reason these mechanisms can produce magic at all is that **Lyra remembers every
minute of every task across months; the user remembers last week imperfectly and last
quarter as a vague feeling**. Every "WHAT, how did it know?" reduces to the same root
mechanic: *Lyra is showing the user the contents of their own forgotten memory, with
receipts*.

This frames every output decision below. The pattern that produces the magic is
**specificity + provenance**, not volume + insight-ish-ness. Three mediocre reflections
do less than one reflection that says "your last 4 attempts at this exact thing — here
they are, with the actual times".

---

## Tier A — the killer three (1-2 weeks each, uses existing data only)

### A1. The Vocabulary Mirror

**Magic moment:** *"I literally typed that word. I didn't notice."*

**Mechanism:** Tokenize task titles. For each token that appears ≥5 times in the user's
history, compute its mean planned/executed delta and skip rate. Surface words that
systematically predict overrun, skip, or pause-heavy outcomes. Show them with statistics
*and example titles the user wrote*.

**Output sketch:**
> Words that betray you:
> - **"quickly"** — last 14 tasks containing this word ran 3.8× planned time. Mean
>   overrun: 47 minutes.
> - **"just"** — 22 tasks, 31% skip rate (your overall skip rate is 9%).
> - **"review"** — 18 tasks, 67% never started.
>
> Try writing the task without these words. Estimate again.

**Data path:** `task.title` tokenized → join with `task.duration_delta_minutes` and
`task.state` → group by token → filter for tokens with N≥5 and significant delta. Pure
SQL + Python. No ML.

**Implementation cost:** ~3 days.
- 1 endpoint: `GET /v1/insights/vocabulary-patterns`
- 1 InsightsCard component
- Stoplist of common English words ("the", "a", "is", category nouns)
- Min frequency threshold N≥5
- Bonferroni-adjusted p-value to avoid noise

**Research integrity:** Pure read-only. No measurement contamination. Safest mechanism
to ship first. Filter: `WHERE voided_at IS NULL`.

**Why nobody else can ship this:** Toggl/Clockify don't separate planned from executed.
Things/Todoist don't measure execution time. Lyra's per-task plan-execute pair is what
makes this query possible.

**Risk:** Low. Worst case: the patterns aren't strong enough to be interesting.
Mitigation: don't surface the card unless there are ≥3 statistically significant tokens.

---

### A2. The Pre-Mortem Whisper

**Magic moment:** *"How did it know my last 4 attempts?"*

**Mechanism:** At task creation time, surface a prediction grounded in the user's last N
executions of structurally similar tasks (same category × hour bucket × weekday).
Critically — show the **actual receipts**, not just an aggregate multiplier.

**Output sketch (slides up from create-task modal, 800ms after estimate is entered):**
> Heads up — you're estimating **30 min** for a coding task on a Tuesday after 11pm.
>
> Your last 4 of those:
> - Apr 12, "fix auth bug" — planned 30, actual **74 min**
> - Apr 8, "quick API tweak" — planned 20, actual **52 min**
> - Apr 3, "small refactor" — planned 30, actual **88 min**
> - Mar 29, "add validation" — planned 45, actual **120 min**
>
> Average overrun in this window: **2.3×**. Plan for 70 min instead?

**Data path:** New endpoint `/v1/tasks/predict-overrun`. Inputs: `(category, hour_bucket,
weekday, planned_duration)`. Returns the matching last-4 tasks with computed mean ratio.
Reuses existing `bias_factor` math but exposes the *raw evidence*, not the multiplier.

**Implementation cost:** ~5 days.
- 1 endpoint
- Frontend integration into NewTaskModal (debounce on duration change, 800ms)
- Opt-in setting (default on)
- Rate-limit: only fire when matching window has N≥4 samples AND overrun ≥1.5×
- Once-per-creation-flow throttle

**Research integrity — CRITICAL:** This is a closed feedback loop on the H1 measurement.
Pre-register before shipping or H1's planned-vs-executed delta data gets contaminated by
the intervention itself. The right design: split-cohort RCT.
- Control arm: half of users see no whisper
- Treatment arm: half see the whisper
- Compare delta distributions across arms over 4 weeks
- Pre-register: "intervention reduces |delta| by ≥20%" or kill

This is also a VT-22 (scope inflation hypothesis) opportunity: if the whisper changes
delta but does NOT change task title length / scope, that's evidence delta is time
estimation error. If users keep planning the same and just write smaller tasks, that's
evidence for scope inflation. Co-pre-register the scope hypothesis.

**Risk:** Medium. The UX challenge is showing this without making the user feel
attacked or constantly nagged. Solve with: opt-in, gating thresholds (N≥4, overrun
≥1.5×), and once-per-flow throttle. Soft language: "Heads up", not "You will overrun".

---

### A3. The Skip Phantom

**Magic moment:** *"Oh god, you're right, this isn't really on my list."*

**Mechanism:** Detect task titles the user re-creates repeatedly without completing —
semantic similarity clustering across the user's full SKIPPED + PLANNED history. Surface
clusters as "ideas you keep planning but never doing."

**Output sketch (weekly insights):**
> 3 ideas you keep proposing to yourself but never start:
>
> 1. **"reorganize notes / clean up Obsidian / sort the vault"** — planned 11 times
>    across 84 days. Started: 0. Skipped: 7. Auto-deleted: 4.
> 2. **"write the BCI postmortem"** — planned 6 times across 32 days. Started: 0.
> 3. **"call mom"** — planned 4 times. Skipped 3, completed 1.
>
> These aren't on your list. They're aspirations. Want to commit one to a slot, or
> remove them honestly?

**Data path:** Sentence similarity (TF-IDF cosine for v1, embeddings for v2) over
`task.title` filtered by `state IN (SKIPPED, DELETED, PLANNED)` for the same user.
Cluster by similarity ≥0.75. Filter clusters with ≥3 instances and ≤1 EXECUTED count.

**Implementation cost:** ~7-10 days.
- v1: scikit-learn TF-IDF (3-5 days)
- v2: sentence-transformers embeddings (extra 2-5 days)
- Backend: clustering job + cache table (skip_phantom_cluster)
- Frontend: weekly digest card

**Research integrity:** Read-only. No measurement contamination. Filter:
`WHERE voided_at IS NULL`. Pre-registration optional.

**Risk:** Medium-high — this one stings. The "not on your list — aspirations" framing
is essential. Without it, the user feels judged. With it, the user feels seen. Pilot
with the operator first; tune the wording before any external user sees it.

---

## Tier B — sleeper hits (3-4 weeks, light new instrumentation)

### B1. The Sunday Letter

A 2-3 paragraph generated narrative every Sunday evening, written in second-person past
tense, that synthesizes the week's patterns. Not a chart. Not a stat block. A *letter*
from Lyra to the user.

**Output sketch:**
> This week, you started Mondays planning 28% more than you finished. By Thursday you
> were running 94% on plan — your most accurate day. Friday you skipped 3 tasks tagged
> "writing" and the only writing task you completed had "draft" in the title (you
> complete drafts; you skip "finals"). You took 7 pauses for "low focus" — all between
> 2pm and 4pm. None in the morning.
>
> Compared to the last 4 weeks, this week you committed 18% less and finished 91% of
> it. That's your highest completion rate since March 19. The thing that changed: you
> didn't add new tasks after 9pm.
>
> Tomorrow: you usually start Mondays with email. Last 5 weeks, on weeks where you
> started with deep work instead, you finished 22% more.

**Why narrative:** Charts inform. Sentences move. Three time-perspectives (this week,
4-week comparison, tomorrow) in one artifact. This is the share-with-a-friend artifact —
the closest Lyra gets to a Spotify Wrapped moment.

**Data path:** Templated LLM call (Claude Haiku 4.5) over a structured weekly summary
built in SQL. Slot-filled templates for v1, full LLM generation for v2.

**Cost:** ~2-3 weeks. Privacy: weekly summary goes to Anthropic API, document in privacy
policy.

---

### B2. The First-Hour Predictor

Real-time forecast at ~10am on the day's first task choice.

**Output sketch:**
> You started today with **email triage** at 9:48am.
>
> On days you start with admin/email (n=23 over 90 days), you complete **58%** of your
> planned tasks. On days you start with deep work (n=18), you complete **84%**.
>
> Today's predicted plan completion: **60-65%**. Most-likely-to-survive: tasks 1-4.
> Most-likely-to-skip: tasks 6-7.
>
> Drop the tail now to protect the head?

**Data path:** Logistic regression on `(first_task_category, hour, weekday) →
plan_completion_rate`. Pure SQL + bucket counts works for v1.

**Cost:** ~1-2 weeks.

**Research integrity:** Same H1 contamination concern as A2. Pre-register or split-cohort.

---

### B3. The Pause-Reason Predictor

VT-17 already predicts WHEN. Extend to predict WHY.

**Output sketch (banner):**
> Coming up at 11:23 (in 8 min): you typically pause here.
>
> Most likely reason today: **distraction** (your usual at this hour). Phone in another
> room?

**Data path:** Predict `pause_event.reason` as f(hour, weekday, category, pauses_today).
Naive frequency-based predictor for v1.

**Cost:** ~1 week. Existing `pause_event.reason` data already collected.

**Research integrity:** Subset of VT-17. Already pre-registered architecture; just an
extra column on the prediction.

---

## Tier C — bigger bets (post-alpha-success only)

### C1. The Constellation View
Visualize the temporal shape of the user's "good days" (≥80% plan completion + ≥1 deep
work block). User sees their own optimal rhythm emerge as a constellation pattern.

### C2. The Inverse Archetype
"You're 73% Owl-Disciplined. Here are 3 places where you defy your archetype's
prediction. These are your unique fingerprints." Reframes archetype as baseline-to-deviate-from
rather than box-to-fit-in.

### C3. The Doppelganger
Cohort-aggregated comparison: "Someone with your archetype + completion-rate profile,
doing what you're about to do, ran 1.8× over their estimate." Privacy-friendly because
archetype-cohort-aggregated, but **requires N≥30 in the cohort** — not safe to ship
until alpha hits scale.

---

## Sequencing (post-Jun-18-25 GREEN only)

| Order | What | When |
|---|---|---|
| 1 | A1 Vocabulary Mirror | First. Read-only, no measurement risk, lowest implementation cost. |
| 2 | A2 Pre-Mortem Whisper (split-cohort RCT) | After A1 lands and user feedback validates the receipt-based pattern. Pre-register. |
| 3 | A3 Skip Phantom | If A2 reception is strong. Calibrate wording on operator first. |
| 4 | B1 Sunday Letter | The marketing artifact. Build once 8+ weeks of dense data per user exists. |
| 5 | B2 First-Hour Predictor + B3 Pause-Reason | Same sprint, both extend existing predictors. |
| 6 | Tier C | Only if N≥30 cohort and Tier A/B are landed. |

---

## Critical contract: retroactive entries must mark `initiation_status='retroactive'`

The Apr 25 logging-friction analysis (operator-confessed: even after 3 weeks of dogfooding, tasks happen but don't get logged) makes a Daily Catch-up Sweep one of the highest-leverage moves before any of the mechanisms above. **Any sweep, calendar-auto-prompt, or other retroactive-logging surface that lands data into the `task` table MUST tag those entries with `initiation_status='retroactive'`** — otherwise they contaminate the planning-discrepancy signal that `bias_factor` is built on.

Why: MANIFESTO Rule 13 already excludes retroactive tasks from `bias_factor` calculation precisely because they have no real planned-vs-executed delta (the user is back-filling history, not making a forecast). Retroactive sweeps fix the *volume* of logged data and the *timeline*, but the planning self never made a forecast for those entries — so the delta is meaningless and pulls bias_factor toward zero if mixed in.

This is also a prerequisite for the deadline mechanism (`docs/deadline_mechanism_design.md`): deadline-bound tasks where the user retroactively logged execution should still bind to the deadline (for completion tracking) but be excluded from per-deadline bias_factor (for measurement integrity).

Operator decision: any new retroactive-capture surface must pass through `services/task_manager.py` with `initiation_status='retroactive'` enforced at the entry point, never as a downstream filter.

## The pushback to Omar's framing

Omar said: "I want it to give back, not just understand better." The naive read is
"more outputs". The deeper read is **fewer, sharper outputs that have receipts**.

Adding 7 more reflection types creates noise. Adding one Vocabulary Mirror that surfaces
the user's actual word choices with their actual outcomes creates a story they tell
other people about the app.

The current calibration_nudge / micro_mirror / archetype card all share a structural
weakness: they tell the user *what* without showing the *evidence*. The Tier A
mechanisms above all share one structural choice: **they include the receipts**. That
is the pattern. Specificity + provenance > volume + insight-ish-ness.

---

## Kill criteria for this whole document

If at the Jun 18-25 retention checkpoint:
- Stage 2 RED → Lyra Light pivot, none of these mechanisms ship.
- Stage 2 YELLOW (week 3 green, week 6 declining) → hedonic adaptation; **A1 alone**
  ships as the lightest-weight test of whether content output prevents adaptation.
- Stage 2 GREEN → execute the sequence above.

This document is valid only as a queue for Stage 2 GREEN. If RED or YELLOW it should be
archived under `archive/` with a one-line note about why.
