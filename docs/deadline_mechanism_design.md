# Deadline Mechanism — Design Note

**Status:** APPROVED for Option B build (2026-04-25, post-midterms start). Locked
by operator decision. See "Operator decision (Apr 25)" section below for the
justification chain. This doc is the implementation reference; do not depart from
the schema, parser, or pre-registration plan without an explicit re-review.

**Created:** 2026-04-25, midterm halt window.
**Approved:** 2026-04-25 by operator. Build starts post-midterms (≥ Apr 27).
**Owner:** Operator (Ali).
**Choice locked:** Option B (build before Jun 18-25 retention check) — see "Why this
conflicts with H1 measurement" section below for the surfaced trade.

---

## Operator decision (Apr 25)

**Choice:** Option B — build deadline mechanism mid-alpha, before the Jun 18-25
retention checkpoint and before H1 reaches an explicit decision.

**Justification (operator-stated):**
1. Per the operator's priority hierarchy (operator's time > users' time > research
   publications, see `~/.claude/projects/.../memory/user_priority_hierarchy.md`),
   research-integrity caveats yield to features the operator needs.
2. The operator wants to use this feature himself for midterms + BCI hackathon
   work — self-dogfooding is the fastest validation loop available.
3. The H1 retention signal is weak (1/9 actively retaining external users as of
   Apr 25). The dataset is too sparse to be at meaningful risk from
   mid-experiment additions, so the parked H2 caveat about "would invalidate the
   pre-registered analysis rules" is largely moot.
4. The deadline mechanism is hypothesized to *reduce* logging friction (see
   `project_logging_friction.md`), which would *increase* H1 dataset density. Net
   effect on H1 measurement quality may be positive even with the mid-experiment
   contamination.

**What this means for research-integrity mitigation (still required):**
- Pre-register the deadline split-cohort RCT in MANIFESTO before the soft-warning
  UX ships (data collection on the schema can begin earlier).
- Run analyses both with and without deadline-stratification when computing H1
  rho, so the H1 finding (or null) doesn't entangle with deadline introduction.
- Document the operator-decision-driven cohort change in the eventual H1 writeup
  if a writeup happens. Be explicit about the pivot from the parked H2 plan.

---

## Why this exists

Two threads converge into one design:

**Thread 1 (Apr 16 / Apr 17):** H2 deadline-proximity hypothesis is already parked in
`docs/parked_ideas.md` — proposes `deadline_utc` as a nullable column on `task` with
schema additions for `deadline_distance` and a kill criterion at n≥60 deadline-tagged
tasks. Status: parked, do not build mid-experiment.

**Thread 2 (Apr 25, this doc):** Operator proposes a structurally richer mechanism —
**deadlines as first-class entities** that bind multiple tasks together. Not "a column
on a task" but "a constellation around which tasks orbit." A deadline like "BCI Spring
School Hackathon" is one row; "build the speller backend", "test on subjects", "write
the postmortem" are multiple task rows that all bind to it. The parser infers binding
from semantic overlap.

This expands H2 from a single-column hypothesis into a **measurement infrastructure**
that enables a new class of insights and interventions.

---

## The structural shift

| Aspect | H2 (Apr 16, parked) | Deadline mechanism (Apr 25, this doc) |
|---|---|---|
| Schema | `task.deadline_utc` nullable | New `deadline` table + `task.deadline_id` FK |
| Granularity | Per-task deadline | Many-to-one: many tasks → one deadline |
| Inference | None — user explicitly tags | Title-parser infers binding via semantic similarity |
| Hypothesis | Distance × delta correlation | Plus: per-deadline scope/time integrity, priority misalignment, planning anchoring |
| Intervention | "Deadline in X hrs, +Y% est" | Plus: priority misalignment soft-warning, deadline-progress UI, deadline-anchored planning prompts |

The H2 schema is a strict subset of the deadline mechanism's schema. Building this
mechanism *automatically* gives us H2's data, plus three more lenses (constellation,
inference, priority-misalignment).

---

## What it unlocks

### Magic moments produced (in order of leverage)

1. **Priority misalignment soft-warning at task creation.**
   When the user creates a task and an active deadline is < N days away with < X
   tasks already bound to it, surface: *"Heads up — you're creating a task unrelated
   to [BCI Hackathon], which is in 3 days. You have 2 unstarted tasks for it. Want
   to pivot, or proceed?"* Same receipts-based design as A2 Pre-Mortem Whisper —
   shows the actual unstarted task list, not aggregate stats.

2. **Deadline-anchored planning prompt.**
   When the user opens the app to plan, surface: *"3 deadlines coming up. What's
   the first thing for [most-urgent]?"* Drops planning friction by giving the user a
   focal point. This addresses Apr 25's logging-friction analysis: deadlines are
   the planning anchor that gets users to plan more, which generates more logged
   data, which feeds every downstream mechanism.

3. **Per-deadline bias_factor stratification.**
   The Vocabulary Mirror (A1 in `docs/insight_mechanisms_post_retention.md`) gets a
   second lens: not just "your 'quickly' tasks overrun 3.8×" but "tasks bound to
   [BCI] deadlines run 2.1× planned time; tasks bound to [school] deadlines run 1.0×."
   Operator-style users with multiple project streams see calibration *per project*.

4. **Deadline-progress dashboard.**
   For each active deadline: total estimated hours vs completed, days remaining,
   implied per-day pace, today's actual contribution. *"BCI hackathon: 12h estimated,
   4h done, 8 days left → 1 hr/day required. Today's plan: 0 BCI tasks. Add one?"*

5. **VT-22 stratification — the research-integrity payoff.**
   Scope inflation hypothesis (MANIFESTO §VT-22) currently lacks a clean grouping
   variable. Deadline-binding gives one: compare scope_density × delta mediation
   for deadline-bound vs unbound tasks. If scope inflation is real, deadline-bound
   tasks should show *more* inflation (commitment + time pressure → over-promise).
   This is a pre-registerable additional analysis.

### Failure modes solved

| Alpha-cohort failure mode | How deadlines help |
|---|---|
| 90sseg (procrastination, Instagram) | Deadlines make the cost of skipping visible *at the moment* via misalignment warning |
| mariam, mero, pbassem (single-task-stop, "didn't plan their week") | Deadline-anchored planning prompt drops planning cost by giving a focal point |
| Operator (forgets to log even after 3 weeks) | Deadline binding makes each task feel like progress against a goal, not isolated overhead |
| omar (privacy-allergic) | Pure on-device computation; no new sensitive data class |

---

## Data model

```sql
-- New table
CREATE TABLE deadline (
    deadline_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         integer NOT NULL REFERENCES "user"(user_id),
    title           varchar NOT NULL,
    description     text,                       -- optional, used by parser
    due_at_utc      timestamp NOT NULL,
    category_hint   varchar,                    -- optional pre-bound category
    state           varchar NOT NULL DEFAULT 'active',  -- active|completed|missed|voided
    completed_at    timestamp,
    voided_at       timestamp,                  -- per voided_at memory pattern
    created_at      timestamp NOT NULL DEFAULT now()
);

-- New nullable FK on task
ALTER TABLE task ADD COLUMN deadline_id uuid REFERENCES deadline(deadline_id);
ALTER TABLE task ADD COLUMN deadline_match_confidence float;  -- 0.0-1.0 from parser
ALTER TABLE task ADD COLUMN deadline_match_source varchar;    -- "parser_auto"|"user_explicit"|"user_corrected"
```

Alembic migration label: `alembic 034 — deadline first-class entity` (current head is
~033 per the strategic_decisions_april_24 doc; verify before naming).

**Voided_at discipline (per memory):** every deadline query/mutation MUST filter
`WHERE voided_at IS NULL`. State-only filters leak. The orphan_task_recovery /
stale_session_recovery jobs need analogous logic for deadlines (e.g. a deadline
whose due_at_utc has passed without state transition → background job marks
`state='missed'`).

---

## Inference mechanism — title parser extension

The existing `services/parser.py` already does NLP date-parsing via dateparser. Extend
to also do deadline-binding inference:

1. **Pass 1 (explicit):** if the task creation payload includes `deadline_id`, bind directly.
   `deadline_match_source='user_explicit'`, `confidence=1.0`.

2. **Pass 2 (keyword):** for each active deadline for this user, compute keyword
   overlap between the task title and the deadline title. If overlap ratio ≥ 0.5
   AND at least one non-stoplist token shared → bind. `deadline_match_source='parser_auto'`,
   `confidence=ratio`.

3. **Pass 3 (semantic, v2):** sentence-similarity (TF-IDF cosine for v1, embeddings
   for v2) between task title and deadline title+description. If similarity ≥ 0.65 →
   bind. `confidence=similarity`.

4. **No match:** `deadline_id=NULL`. Task is unbound.

User correction always wins — when the user manually picks a deadline (or removes one)
post-creation, `deadline_match_source='user_corrected'`. This data is what we mine in
v2 to retrain the inference threshold.

**Why structurally interesting:** the parser builds a labeled training set from user
corrections automatically. Every "you got this wrong, the right deadline is X" is a
free training signal. After ~6 weeks of cohort use, the parser has cohort-specific
calibration data without any explicit ML tooling.

---

## Soft-warning UX (the killer feature)

Fires during task creation when:
1. There exists ≥1 active deadline for this user with `due_at_utc - now < N days`
   (tunable; default N=3)
2. That deadline has ≥X tasks bound with state IN (PLANNED, EXECUTING, PAUSED) — i.e.
   uncompleted work remaining (default X=1)
3. The task being created does NOT bind to that deadline (parser pass 1-3 yields no
   match for that specific deadline)
4. The user has not dismissed this specific warning combination in the last 24 hours
   (anti-nag throttle)

Wording (operator to refine):
> Heads up — you're creating a task unrelated to **BCI Spring School Hackathon**, which
> is in **2 days**.
>
> You still have **3 unstarted tasks** for it:
> - "build speller backend" (planned 2hr)
> - "test cases bench" (planned 1hr)
> - "write postmortem" (planned 30min)
>
> Pivot to one of those, or continue?
>
> [Pivot] [Continue anyway] [Don't ask again for 24h]

Tone matches A2 Pre-Mortem Whisper: receipts-based, soft, gives the user agency. The
"don't ask again for 24h" is essential for omar-archetype users — without it, the
system reads as nagging.

Critical research-integrity caveat (per Structural Investigation Rule): **this is a
closed feedback loop on H1 + H2 measurement**. Pre-register a split-cohort RCT before
shipping. Half see the warning, half don't, compare deadline-bound completion rates +
time-to-deadline-completion + delta distributions over 6 weeks. Without
pre-registration, the warning intervention contaminates the very hypothesis it's
testing.

---

## Pre-registration requirements

Per MANIFESTO §VT-22 Rule 12 + the Structural Investigation Rule, the following must be
frozen *before* user data is collected with the deadline mechanism live:

1. **H2 kill criterion (already parked):** at n≥60 deadline-tagged tasks across the
   cohort, `deadline_distance × delta` Spearman ρ p ≥ 0.05 → H2 falsified.
2. **Per-deadline bias_factor analysis:** within users with ≥30 sessions across ≥2
   deadlines, compute per-deadline bias_factor. Report distribution. Pre-register
   threshold for "deadlines DO modulate bias_factor": within-user σ across deadlines
   > 0.30 in ≥3 of 5 first cohort users.
3. **Soft-warning RCT:** half-cohort sees warning, half doesn't. After 4 weeks,
   compare:
   - Mean tasks bound per deadline (does the warning increase deadline-binding?)
   - Mean delta on deadline-bound vs unbound tasks
   - User-reported satisfaction (does the warning feel useful or naggy?)
4. **VT-22 stratification:** rerun Rule 12's mediation test stratified by
   `deadline_id IS NULL` vs `IS NOT NULL`. If scope inflation is deadline-driven, the
   `IS NOT NULL` arm should show stronger mediation.

Do NOT build until pre-registrations are committed to MANIFESTO.

---

## Why this conflicts with H1 measurement

This mechanism adds a new behavioral input to the system DURING the H1 measurement
window. Per parked_ideas H2 §"Do not": *"Build mid-experiment (would add a new input
variable to the H1 dataset and invalidate the pre-registered analysis rules in
MANIFESTO §801)."*

The honest framing of the strategic call: shipping deadlines mid-alpha violates the
parked H2 guidance. The justification (worth making explicit if shipped):
1. H1 retention signal is weak (1 actively-retaining external user out of 9 as of Apr
   25) — the H1 dataset is too sparse to be at risk anyway.
2. The deadline mechanism is hypothesized to *reduce* logging friction, which would
   *increase* H1 dataset density downstream. Net effect on H1 measurement quality may
   be positive even with the mid-experiment caveat.
3. If H1 retention fails at Jun 18-25, the parked H2 caveats become moot — there's no
   experiment left to contaminate. Shipping deadlines becomes a Lyra-Light pivot tool.
4. If H1 retention succeeds, the deadline mechanism is the *first* upgrade post-Phase-5.

**Decision required from operator before any code is written:**
- (A) Build deadline mechanism only after H1 decision (preserve experiment integrity,
  delay the retention-leverage benefit).
- (B) Build before Jun 18-25 retention check (sacrifice H1 measurement integrity, gain
  retention leverage immediately).
- (C) Build the schema + parser (silent — collect deadline data but don't surface
  warnings or progress UI to users) so the data accumulates pre-registered, then
  light up surfaces post-H1.

**Operator's instinct (per Apr 25 chat):** lean toward (B) given retention weakness.
This doc captures (C) as the structurally-cleanest middle path — pre-registers the
data without contaminating intervention measurement.

**Resolved (2026-04-25):** Option B locked by operator. See "Operator decision" at
top of this doc for the full justification chain. Option C's silent-collect path is
preserved internally as a fallback — if mid-build the operator decides the
soft-warning RCT is contaminating something important, the surfaces can be feature-
flagged off while data accrual continues.

---

## Implementation cost

| Phase | What | Cost |
|---|---|---|
| Schema + migration | `deadline` table + `task.deadline_id` FK + Alembic 034 | ~1-2 days |
| Parser extension | Pass 2 keyword overlap; Pass 3 deferred to v2 | ~3 days |
| Backend API | POST/GET/PUT/DELETE deadlines; bind/unbind on task | ~3 days |
| Frontend — deadline list | New page or sidebar section, deadline CRUD UI | ~3-4 days |
| Frontend — task creation UI | Deadline picker in NewTaskModal, parser preview ("Lyra thinks this binds to: BCI Hackathon") | ~2-3 days |
| Frontend — soft-warning | The misalignment warning UI + 24h throttle | ~2 days |
| Background jobs | Deadline state transitions (active → missed) every hour | ~1 day |
| Tests + analytics endpoints | Per-deadline bias_factor query | ~2-3 days |
| **Total** | | **~3-4 weeks** |

This is a substantial build — approximately the same scale as the entire Tier A
post-retention queue from `insight_mechanisms_post_retention.md`. Don't underestimate.

---

## Sequencing

If the operator chooses (B) or (C):

| Order | What | When |
|---|---|---|
| 1 | Pre-registration commits to MANIFESTO + Alembic migration drafted | Before any user-facing code |
| 2 | Schema + backend CRUD + parser pass 1+2 | Week 1 |
| 3 | Frontend deadline list + task-creation deadline picker | Week 2 |
| 4 | Per-deadline bias_factor analytics | Week 3 |
| 5 | Soft-warning UX (RCT split-cohort enabled at this point) | Week 4 |
| 6 | Deadline-progress dashboard + planning prompt | Week 5+ |

If choosing (A): wait until Jun 18-25 + H1 decision. This entire doc sits idle until
then.

---

## Connection map

```
Deadline mechanism (this doc)
         │
         ├── extends → H2 (parked_ideas.md §"H2: Deadline-proximity")
         │
         ├── stratifies → VT-22 (MANIFESTO §VT-22, Rule 12)
         │
         ├── enables → A1 Vocabulary Mirror (insight_mechanisms_post_retention.md)
         │            via per-deadline bias_factor lens
         │
         ├── reduces → logging friction (project_logging_friction.md memory)
         │            via deadline-anchored planning prompts
         │
         └── solves → 90sseg / mariam / mero / pbassem failure modes
                      (project_user_archetypes_qualitative.md memory)
```

---

## Kill criteria

| Threshold | Action |
|---|---|
| At n≥60 deadline-tagged tasks, `deadline_distance × delta` ρ p≥0.05 | H2 falsified; deadline mechanism remains as product feature but research claim drops |
| At week 4 of soft-warning RCT, treatment arm shows no improvement in deadline-bound completion rate AND user satisfaction declines vs control | Soft-warning surface removed; backend deadline data continues to accrue |
| Within-user σ across deadlines ≤ 0.10 in ≥3 of first 5 cohort users (per-deadline bias_factor doesn't vary) | Per-deadline lens dropped from analytics; deadlines remain as planning surface only |
| At Jun 18-25 retention check, GREEN cohort shows no statistically meaningful uplift attributable to deadline mechanism | Mechanism stays shipped (sunk cost) but de-prioritized in subsequent feature ranking |

If RED at Jun 18-25: this entire doc is moot. Lyra-Light pivot doesn't carry deadlines
unless they were the retention-rescuing feature, which by definition they would not
have been.
