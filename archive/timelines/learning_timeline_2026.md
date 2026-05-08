# Personal Learning Timeline — Apr 26 → Jul 24, 2026

Companion to `archive/python_practice3.html`. Honest pacing for three concurrent commitments racing the same clock.

---

## Velocity calibration (read this first)

What I actually know about your throughput from the last 3 months:

- **Practice problems**: 25 solved in ~3 weeks of intermittent work. Steady-state ≈ 1 problem/day; routinely 0/day on Lyra-incident days.
- **Lyra ops baseline**: ~1–2 hr/day (dogfood, bug triage, doc updates, retention reads). This is the floor — even on "no Lyra work" days it eats this much.
- **Documentation gap**: 50% covered (your own estimate). Reading time on each new file ≈ 2× longer than for a developer with full doc context.
- **Application code velocity**: high in PM/spec mode, slow in implementation. The slow-down sprint flips this on purpose.
- **Stamina pattern**: deep 4–6 hr sessions, then 1–2 days of low output. Plan for the recovery days, don't pretend they're not there.

**Working assumption**: 5 productive learning hours per day on average over a 7-day week. That's 35 hr/week before any Lyra ops cost.

---

## The three deadlines you're racing

| Date | Event | Stakes |
|------|-------|--------|
| **May 17, 2026** (Day 21) | End of slow-down sprint | First solo Lyra bug fix (#829). The "competence proof" milestone. |
| **Jun 18–25, 2026** (Day 53–60) | Retention checkpoint (per `docs/strategic_decisions_april_24.md`) | The week-6-to-8 signal that decides whether to scale. Cannot be moved. |
| **Jul 6–24, 2026** (Day 71–89) | Neuromatch CompNeuro live course | Full-time intensive: 4.5 hr/day curriculum + 3 hr/day pod project. Assumes acceptance (announcement expected ~mid-May). |

Aibdaya has no fixed deadline — it's a 120-hour course (60 theory + 60 practice). Treated as parallel infrastructure, not a sprint.

---

## Phase 1 — Slow-down sprint (Apr 26 → May 17, 21 days)

**Single goal: fix one OPEN Lyra bug solo by May 17, ≤ 90 min, no Claude writing code.**

That's problem #829 in the practice file. Everything else this phase serves it.

### Week 1 (Apr 26 → May 2): consolidate Python core
**Practice**: #26 → #40. Functions, scope, modules, banking program, slot machine, encryption, hangman.
**Pace**: 2 problems/day weekdays, 1/day weekend = 14 problems in 7 days.
**Lyra**: keep dogfood + reactive bug triage only. No new features.

### Week 2 (May 3 → May 9): OOP and exceptions
**Practice**: #41 → #58. Modules, the rest of practical fundamentals, full OOP block (inheritance, super, polymorphism, duck typing, exceptions).
**Pace**: 2/day = 14 problems.
**Why this matters**: OOP unlocks SQLAlchemy ORM, Pydantic models, and most of the Lyra service layer. Without this you can't read `task_manager.py`.

### Week 3 (May 10 → May 17): Lyra Prereqs + capstone
**Practice**: #800 → #811 (Lyra Prereqs — type hints, Pydantic, decorators, pytest, SQLAlchemy ORM + joins, async, logging, pdb, git). 12 problems in 7 days = 1.7/day.
**May 17 (graduation day)**: #829 — pick LYR-068 or LYR-099 from `LYRA_BUGS.md`, fix without Claude writing any code, time it.

### Slip plan
If you're behind by May 10, drop the OOP advanced problems (#49 multiple inheritance, #50 super) and push them to Phase 2. Do NOT skip the Lyra Prereqs — they're the load-bearing block.

If May 17 graduation fails (>90 min or needed Claude code), repeat the attempt May 18–24 with a different bug. Two failures in a row is the signal to talk about whether the slow-down dose was wrong.

---

## Phase 2 — Maintain & broaden (May 18 → Jun 17, 31 days)

Lyra gradually returns to normal velocity. You write, Claude reviews. Aibdaya runs in the background.

### Practice schedule
- **#59 → #77** (rest of course: exceptions, file handling, JSON, APIs, weather app). 19 problems over ~25 days = 0.75/day. Slow on purpose; this stuff overlaps less with Lyra.
- **Aibdaya Stages 1–3** (ML foundations, ML pipeline, statistics). ~30 hours of content. 1 hr/day = ~30 days. Finishes around Jun 17.

### Lyra targets
- **Solo bug count**: 1 fixed solo per week minimum. By Jun 1, target ≥ 4 fixed without Claude touching the code.
- **Doc coverage**: write missing docs for the files you touch. Aim 50% → 60% by Jun 17.
- **Velocity check on Jun 1**: if solo bug count < 3, the slow-down worked partially — extend Phase 1 patterns into Phase 2 instead of resuming Claude-led implementation.

### NMA acceptance window
- Applications closed Mar 22. CompNeuro announcements typically land 4–6 weeks before the course → expect email between **May 11 – Jun 8**.
- If accepted: Phase 4 fires as scheduled.
- If rejected: shift Jul 6–24 to a self-directed project (your choice — Lyra v1.1 partial build, or solo Aibdaya cram, or rest).

---

## Phase 3 — Retention checkpoint week (Jun 18 → Jun 25, 8 days)

**Pause all learning.** This week is operator-mode only.

- Read u1–u10 retention numbers in qualitative context (per memory `feedback_retention_needs_qualitative.md`).
- Make the scale / hold / kill call per `docs/strategic_decisions_april_24.md`.
- Document the decision and the reasoning in a new dated doc under `docs/`.
- If the call is "scale" → Phase 5 plans change drastically; revisit this timeline.

No practice problems. No Aibdaya videos. The checkpoint is the deliverable.

---

## Phase 4 — Neuromatch pre-course cram (Jun 26 → Jul 5, 10 days)

**Target: #812 → #824** (Tri-Track Bridge + Neuromatch Prep — 13 problems).

Pace: 1.3/day. Heavier than Phase 2 because it's pre-course pressure and the math compounds — falling behind on linear algebra in Week 1 of NMA is much more expensive than being slow now.

Coverage:
- #812–819 Tri-Track: NumPy, broadcasting, vectorization, statistics, Bayesian, t-test, matplotlib (hist + heatmap)
- #820–824 Neuromatch Prep: linear algebra, numerical derivatives, ODE (LIF neuron), spike trains, PCA from scratch

**Parallel**: read `compneuro.neuromatch.io/prereqs` end-to-end. Watch the W0D1–W0D5 prep videos NMA publishes.

**Lyra during this phase**: maintenance only. Dogfood + critical bugs. No new features, no doc work.

---

## Phase 5 — Neuromatch live course (Jul 6 → Jul 24, 19 days)

NMA is full-time. 4.5 hr/day curriculum + 3 hr/day pod project = 7.5 hr/day, 6 days/week.

**Lyra**: emergency-only. Operator delegates dogfood reads to memory snapshots (Claude can summarise weekly).

**Practice file**: paused.

**Aibdaya**: paused.

**Risk**: NMA pace + your Phase 1–4 pattern = high burnout probability. One mandatory rest day per week (Sat or Sun, your choice). Non-negotiable.

---

## Phase 6 — Reset & next-quarter planning (Jul 25 onwards)

Decisions are dependent on outcomes:

- **If retention checkpoint was green + NMA went well**: ramp Lyra v1.1 build (#401), aim Sep ship.
- **If retention was yellow/red**: pause Lyra dev, run a Phase 1–style 3-week sprint on whatever the retention diagnosis surfaces.
- **Aibdaya**: resume at 1 hr/day, finishes ~Sep–Oct.
- **AI Prereq additions** (#825–828: gradient descent, perceptron, MLP, PyTorch): start once you have base ML foundation from Aibdaya Stage 4+.

---

## Total problems shipped on this plan

By Jul 24:
- Course problems: #26 → #77 = **52 problems** (current #25 → #77)
- Lyra Prereqs (new): #800–811 = **12 problems**
- Tri-Track Bridge: #812–819 = **8 problems**
- Neuromatch Prep: #820–824 = **5 problems**
- Lyra capstone (solo bug fix): #829 = **1 problem**
- **Total: 78 problems / 90 days**

Ratio = 0.87 problems/day average. That's slightly below your steady-state, with built-in slip room for the retention checkpoint week and NMA intensive.

Skipped/deferred to post-Jul 24 (≥ 80 problems):
- Mini Projects #101–131 (most are not load-bearing)
- Deep Dive #201–205
- The PyQt5-heavy course problems (#75–77 if time-pressed)
- Existing AI Prereqs #301–343 except where they overlap Tri-Track
- New AI Prereqs #825–828
- Lyra v1.1 capstone #401
- Final Plan #501–510
- Advanced Engineering #601–607

---

## What to track weekly (the actual feedback loop)

Open a `docs/learning_log.md` (this file documents the plan; the log captures what really happened). Every Sunday, 10 min:

1. Problems solved this week (vs. plan).
2. Hours on Lyra ops (vs. budget of 1–2/day).
3. Solo bugs fixed (cumulative count).
4. One concept that confused you mid-week → flag it for re-reading.
5. One thing that worked better than expected → keep doing it.
6. Sleep average (cheap leading indicator of burnout).

If 3 weeks in a row miss the plan by more than 30%, the plan is wrong — revisit, don't grind.

---

## Failure modes worth naming up front

- **"I'll catch up on the weekend"**: weekends are recovery, not catch-up. Catch-up days don't exist in this plan.
- **"Just one more bug fix"**: Lyra incidents are infinite. Cap them or they eat the curriculum.
- **"I'll skip the easy problems"**: easy problems are where you internalise reflexes (e.g., type-hint fluency). Skipping them leaves cracks that surface during the NMA tutorials.
- **"I don't need to retake Aibdaya from start"**: you do — the math foundation in Stage 1 is exactly what NMA assumes.
- **"NMA might still accept me late"**: build the plan as if accepted; pivot if not. Don't wait for the email to start preparing.
- **Comparing yourself to course instructors / NMA pod-mates**: they've been doing this 5+ years. The metric is your delta from yourself on Apr 26.

---

## One-line summary

By Jul 24, you should be able to read any Lyra service file unaided, fix any small bug solo in under an hour, and follow a Neuromatch tutorial on Bayesian inference in real time. That's the bar. Everything in this plan serves it.
