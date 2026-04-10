# Documentation Audit — April 11, 2026

*This is a working document. It will be deleted after reconciliation is complete.*

---

## A. Document State Inventory

The repo contains 19 markdown files (excluding node_modules, .next, venv). Several are superseded, several contradict each other, and several serve no purpose a reader couldn't get from the code.

| File | Last git mod | Lines | Status | Notes |
|------|-------------|-------|--------|-------|
| MANIFESTO.md | Apr 10 | 610 | Living, stale header | Says v1.2, revised Apr 5. Actually revised Apr 10 (kill criterion tightening). Header lies. |
| FEATURES.md | Apr 8 | 666 | Living, probably stale | Last touched Apr 8. Several features shipped since (interruption flow, completion_pct hardening). |
| LYRA_BUGS.md | Apr 9 | 166 | Living, stale counts | Header says "37 open, 53 fixed" but actual counts don't match. Many OpenClaw bugs are now irrelevant (system pivoted to web UI). |
| README.md | Apr 7 | 277 | Living, significantly stale | Says "v1.4". No mention of web UI, multi-user, Google OAuth, or any Phase 2-3 work. Still describes Telegram/OpenClaw as primary interface. |
| CLAUDE.md | Apr 7 | 122 | Living, moderately stale | Accurate on architecture. Missing: PAUSED state mentioned but Phase 3 frontend not described. Still references 3 APScheduler jobs (actual: 4). |
| CONTRIBUTING.md | Apr 10 | 50 | Living, current | Updated today with multi-user isolation testing rule. Clean. |
| DOCKER.md | Apr 4 | 104 | Historical | Only covers backend + Redis + OpenClaw networking. No frontend Docker setup. Still useful for backend-only dev. |
| docs/clustering_spec.md | Apr 10 | 261 | Design doc, current | Validation gates added today. Design-only, no implementation. Clean. |
| docs/category_taxonomy.md | Apr 10 | 67 | Living, current | Updated today with category_type design and planning rename. Clean. |
| docs/multiuser_migration_plan.md | Apr 8 | 208 | Historical | Describes the migration plan that was *executed* in Phases 1-2. Much of it is now implemented. Should be marked historical or merged into a living doc. |
| docs/dogfood_findings.md | Apr 10 | 40 | Living, current | Populated today. Session data is from memory, not verified against DB. |
| docs/v2_backlog.md | Apr 10 | 43 | Living, current | Updated today. Clean. |
| docs/competitive_landscape.md | Apr 9 | 41 | Historical | Quick scan, no updates needed unless market changes. |
| docs/hypotheses.md | Apr 10 | 63 | Living, current | H4 only. H2 and H3 not documented anywhere (cascade failure is in MANIFESTO, not here). |
| docs/phase_4_prerequisites.md | Apr 10 | 157 | Design doc, current | Written today. Clean. |
| docs/README.md | Apr 4 | 27 | Stale | References only 4 diagrams and points to README/DOCKER/SKILL.md. Doesn't mention any doc created after Apr 4. |
| lyra_final_spec.md | Apr 5 | 3379 | Superseded | The original product spec. 3,379 lines. Much of it has been implemented, refined, or contradicted by later decisions. The MANIFESTO, FEATURES.md, and CLAUDE.md together supersede it. It should be archived as a historical record, not used as a living reference. |
| openclaw/skills/lyra-secretary/SKILL.md | Apr 7 | 141 | Living, partially obsolete | Agent-facing endpoint reference. Still accurate for backend API, but the system has pivoted to web UI. OpenClaw is no longer the primary interface. Many Hard Rules are agent-specific and don't apply to the web UI. |
| backend/docs/GOOGLE_OAUTH_SETUP.md | Apr 9 | 182 | Living, current | Setup guide for Google OAuth. Accurate. |

**Document count: 19. Target: 10-12.** The biggest consolidation opportunities are: merge multiuser_migration_plan into a multi-user section of MANIFESTO or CONTRIBUTING; archive lyra_final_spec.md as historical; merge competitive_landscape into a customer-facing doc; update docs/README.md to reflect current structure.

---

## B. Undocumented Decisions

These were found by reading all conversation transcripts (9 sessions, 147 substantial user messages) and cross-referencing against current documentation.

### B1. Product-first strategic reframe (CRITICAL)

**Decision:** "Product -> retention -> multi-user -> research validity. Not the other way around."

**Source:** Transcript 51154017, approximately Apr 8. Operator explicitly said: "We slipping too much in the research direction, it's a product first then a research second." And: "A perfectly clean n=1 experiment with no product is a paper nobody reads and a system nobody uses."

**Current doc state:** MANIFESTO.md still opens with "Lyra Secretary is not a productivity app. It is a measurement instrument." This directly contradicts the strategic reframe. The manifesto was written Day 1 in research-first mode. The operator pivoted on Day 4. The manifesto never caught up.

**Severity:** Blocker. A new contributor reading the manifesto will optimize for research purity. The operator has explicitly said that's the wrong frame. The manifesto needs a framing update that says: the research layer exists to make the product better, not the other way around. The product must be worth using independent of the research.

### B2. Three behavioral profiles (Calibrated / Reactive / Overplanner)

**Decision:** Three empirical profiles observed from operator's own data, each requiring different interventions.

**Source:** Transcript b74b36e8, approximately Apr 5 (Day 2). Implemented in MANIFESTO.md.

**Current doc state:** Documented in MANIFESTO.md lines 186-210. Also mentioned in the clustering spec as distinct from the 5 operational archetypes — but the distinction between the two taxonomies (3 research profiles vs 5 product archetypes) is not explicitly stated anywhere. They serve different purposes: profiles describe *what you observe*, archetypes describe *what you do about it at signup*.

**Severity:** Should-fix. One sentence of clarification prevents confusion.

### B3. Parent_task_id interruption flow

**Decision:** When a user starts a new task while another is paused, the new task is automatically linked via parent_task_id. The paused task becomes the "parent" of the interruption. The stop response includes paused_parent info. This was designed in SKILL.md for the Telegram flow and ported to web UI on Apr 10.

**Source:** Transcript b74b36e8, Bug E in the massive fix batch. Also transcript 51154017 (Phase 3.x implementation).

**Current doc state:** Partially documented in SKILL.md's "PAUSED TASK CONFLICT" workflow section. NOT documented in MANIFESTO, FEATURES.md, or any architecture doc. The web UI implementation (d5c77d8) exists in code but the *design rationale* — why interruptions are linked, what the parent_task_id enables for analytics, how it feeds cascade analysis — is nowhere.

**Severity:** Should-fix. This is a load-bearing interaction pattern that two UIs now depend on.

### B4. Void reason enum design

**Decision:** Five valid void reasons: test_contamination, duplicate, system_error, data_quality, other (requires detail). Voided tasks excluded from all analytics.

**Source:** Implemented in Phase 3.2 (4cf2168), design discussed in transcript c9774de9.

**Current doc state:** Not documented in any .md file. The enum exists only in code (schemas/task.py:148-154) and in test assertions. FEATURES.md doesn't mention void reasons. MANIFESTO only mentions VT-11 mitigation via void endpoint. LYRA_BUGS.md mentions "Session voided via POST /v1/tasks/{id}/void" but doesn't list valid reasons.

**Severity:** Should-fix. Any new contributor trying to void a task will hit a 422 and have to read the code.

### B5. Redis per-user key namespacing

**Decision:** All Redis keys scoped by user_id via `_user_key()` static method. Prevents cross-tenant timer leaks. Fixed in Phase 3.3.

**Source:** Transcript 51154017, P0-A fix.

**Current doc state:** Not documented anywhere. CLAUDE.md mentions "Redis responsibilities" but doesn't mention per-user namespacing. The fix is only in the commit message (1373538) and in the code comment at stopwatch_manager.py:45-46.

**Severity:** Nice-to-have. The code is self-documenting here, but a CONTRIBUTING note about "all Redis keys must be user-scoped" would prevent regression.

### B6. Form A customer discovery (n=22)

**Decision:** Operator ran a customer discovery survey (Form A) with 22 respondents as of Apr 10. H4 (Motivated Underestimation) emerged from respondent #3. Cross-tabs planned: Q4 x Q7, Q5 x Q7.

**Source:** Transcript 51154017, user message containing H4 hypothesis text.

**Current doc state:** H4 is in docs/hypotheses.md. Form A itself is not referenced in any doc. No customer discovery doc exists. The competitive_landscape.md is a quick product scan, not a customer discovery record. The n=22 count, the cross-tab plan, and the ICP definition are all undocumented.

**Severity:** Should-fix. Customer discovery data is perishable context. The Form A reference should be in a doc that explains what was asked, what was learned, and what's planned.

### B7. BCI complementary signal reframe

**Decision:** Operator explicitly stated BCI should be reframed from replacement-or-parallel (current r > 0.6 / r < 0.4 gate) to complementary. "BCI and self-report are two noisy estimators of an underlying cognitive state. Combine them with Bayesian weighting."

**Source:** Current conversation (this audit task), operator's prompt.

**Current doc state:** MANIFESTO.md lines 370-380 still uses the old framing: "If r > 0.6: BCI enhances the model / If r < 0.4: BCI is a parallel signal, not a replacement." This is the exact framing the operator wants rewritten.

**Severity:** Blocker (for Phase 2 reconciliation). Five BCI references in MANIFESTO need rewriting.

### B8. Session splitting VT-5 honest state

**Decision:** parent_session_id was proposed as mitigation for VT-5 (session splitting artifact). It was never implemented. The 90-minute cap is protocol-level only — no code enforces it. Sessions of any length are allowed.

**Source:** MANIFESTO.md lines 465-470, code audit confirms no enforcement.

**Current doc state:** MANIFESTO says "parent_session_id not implemented. 90-minute cap is protocol-level, not system-enforced." This is accurate but incomplete — it should state explicitly whether this matters for the April 15 analysis and what the decision is.

**Severity:** Should-fix. The analysis is 4 days away. If long sessions exist in the data, the analyst needs to know whether to split them, flag them, or treat them as independent.

### B9. Sleep as leading indicator

**Decision:** Morning session data shows that sleep quality/duration may predict next-day execution. Not yet implemented as a field.

**Source:** Transcript b74b36e8, MANIFESTO update batch.

**Current doc state:** Documented in MANIFESTO.md lines 270-285 under "Sleep as a Leading Indicator." Status says "sleep_hours field not yet implemented. Add to v1.5 as optional morning check-in." This is accurate.

**Severity:** None. Properly documented.

### B10. Category_type (estimable vs time_anchored)

**Decision:** Categories gain a type field distinguishing user-controlled durations from externally-fixed ones. Prayer, meeting = time_anchored (excluded from bias factor). All others = estimable.

**Source:** Transcript 51154017, Phase 4 prerequisite documentation batch.

**Current doc state:** Documented in docs/category_taxonomy.md (added Apr 10). Design-only, not yet in code. CategoryMapping model has no category_type column (confirmed by code audit).

**Severity:** None. Properly documented as design-only.

---

## C. Code-Documentation Contradictions

### C1. APScheduler job count

**Code says:** 4 jobs registered in scheduler.py — reminders (1min), notion_sync (5min), timer_overflow (2min), overdue_tasks (30min).

**Docs say:** CLAUDE.md line 46: "reminders every 1 min, Notion sync retries every 5 min, timer overflow alerts every 2 min." Only 3 jobs listed.

**Which is correct:** Code. The overdue_tasks job was added in commit 219b681 but CLAUDE.md was never updated.

### C2. Conflict detector includes PAUSED

**Code says:** conflict_detector.py:38 filters `Task.state.in_([PLANNED, EXECUTING, PAUSED])`. PAUSED tasks are conflict candidates.

**Docs say:** CLAUDE.md doesn't specify which states trigger conflicts. README mentions conflict detection but not PAUSED inclusion. The interruption flow (just shipped) depends on PAUSED being a conflict trigger — without it, the web UI would never see the "paused parent" conflict that triggers the interruption offer.

**Which is correct:** Code is correct and the interruption flow depends on it. This should be documented.

### C3. State machine: PAUSED -> EXECUTED path

**Code says:** state_machine.py defines `PAUSED -> {EXECUTING, SKIPPED}`. There is no direct PAUSED -> EXECUTED transition. The stop-while-paused flow goes through auto-resume (PAUSED -> EXECUTING) then immediate stop (EXECUTING -> EXECUTED) inside stopwatch_manager.stop().

**Docs say:** CLAUDE.md line 57 states "PAUSED is non-terminal: it must resolve to EXECUTED (via auto-resume on stop) or SKIPPED." This is functionally accurate but could mislead someone reading state_machine.py — the direct transition doesn't exist, it's a two-step internally.

**Which is correct:** Both are correct at different levels of abstraction. Add a clarifying note.

### C4. README describes Telegram/OpenClaw as primary interface

**Code says:** The system now has a Next.js web UI (frontend/), Google OAuth, multi-user support. OpenClaw/Telegram is a secondary interface.

**Docs say:** README.md describes "Client (Telegram / OpenClaw agent)" as the top of the architecture stack. No mention of web UI anywhere in the README.

**Which is correct:** Code. README is significantly stale. The web UI pivot happened in Phase 3 (commit e9f5d76 and later).

### C5. MANIFESTO commit count

**Code says:** `git rev-list --count HEAD` = 117 commits.

**Docs say:** MANIFESTO.md line 529: "62 commits of solid engineering."

**Which is correct:** Code. The count was accurate when written (Apr 5) but has not been updated.

### C6. LYRA_BUGS.md contains irrelevant OpenClaw bugs

**Code says:** System has pivoted to web UI. OpenClaw is secondary.

**Docs say:** 20+ open bugs are OpenClaw-specific (LYR-007, LYR-035, LYR-043, LYR-048, LYR-049, LYR-051, LYR-052, LYR-053, LYR-057, LYR-059, LYR-062, LYR-063, LYR-064, LYR-065, LYR-066, LYR-067, LYR-069, LYR-071, LYR-078, LYR-081, LYR-082). Many reference Haiku, Qwen3.5:9b, or OpenClaw exec-approvals that are no longer the primary path.

**Which is correct:** These bugs are real but low-priority since the web UI is now primary. They should be moved to a "deferred / OpenClaw-specific" section rather than cluttering the priority list.

### C7. FEATURES.md not updated for Phase 3 web UI features

**Code says:** Web UI has: Today view, task CRUD, timer start/stop/pause, readiness/reflection modals, active timer banner, interruption flow, void affordance, new task modal.

**Docs say:** FEATURES.md doesn't mention any web UI features. It's organized by backend version (v1.1 through v1.7) and lists backend endpoints, not frontend capabilities.

**Which is correct:** Code has shipped features not tracked in FEATURES.md.

---

## D. Stale Versions and Dates

| Reference | Location | Claims | Actual | Fix |
|-----------|----------|--------|--------|-----|
| Manifesto version | MANIFESTO.md:1 | v1.2 | Should be v1.3+ (kill criterion tightened, pre-reg rules added Apr 10) | Update |
| Manifesto revision date | MANIFESTO.md:3 | "Revised: April 5, 2026" | Last git mod: Apr 10 | Update |
| "Day N" experiment refs | MANIFESTO.md:2,3,216,546,592 | Day 1, Day 2, Day 4 | Today is Day 8 (Apr 4 = Day 1, Apr 11 = Day 8) | Leave historical refs; add "current day" note |
| Commit count | MANIFESTO.md:529 | "62 commits" | 117 commits | Update |
| README version | README.md:1 | v1.4 | Code is well past v1.4 (multi-user, web UI, Phase 3.3 fixes) | Update |
| Bug tracker counts | LYRA_BUGS.md:3 | "37 open, 53 fixed" | Actual open: ~30 after strikethrough filtering, fixed: 49 in the fixed table | Recount |
| Bug tracker date | LYRA_BUGS.md:3 | "April 7, 2026" | Last git mod: Apr 9 | Update |
| CLAUDE.md APScheduler | CLAUDE.md:46 | 3 jobs | 4 jobs (overdue_tasks missing) | Add |
| lyra_final_spec.md | lyra_final_spec.md | Active spec | Superseded by MANIFESTO + FEATURES + CLAUDE.md | Mark historical |
| docs/README.md | docs/README.md | Lists 4 diagrams only | Doesn't reference any doc created after Apr 4 | Update or delete |

---

## E. VT-5: Session Splitting — Honest State

The 90-minute cap is a **protocol rule**, not a system enforcement. There is no code anywhere that prevents a session from running longer than 90 minutes. The `parent_session_id` field proposed in MANIFESTO.md line 468 does not exist in the database schema — confirmed by code audit.

What this means for the April 15 analysis:

1. If any sessions in the dataset exceed 90 minutes, they are **not split** — they are single observations.
2. The statistical independence assumption holds trivially for these sessions (they ARE independent — there's no splitting to create dependence).
3. The VT-5 threat as originally stated ("splitting forces artificial sub-tasks that aren't independent") cannot occur because splitting doesn't happen.
4. However, a different form of the threat exists: if the operator *chose* to manually split a long task into two consecutive tasks with the same title, those tasks would appear independent in the data but aren't. This is undetectable without `parent_session_id` or a naming convention.

**Recommendation:** Update VT-5 status to: "The system-enforced splitting threat is moot (no cap enforced). Manual splitting by the operator is possible but detectable by title + temporal adjacency. parent_session_id remains unimplemented. Decide before Paper 1 whether to implement it, run the analysis with the independence assumption, or add a manual check for adjacent same-title tasks."

---

## F. BCI Reframing Plan

Five BCI references found in MANIFESTO.md. Current framing uses a binary gate (r > 0.6 = enhancement, r < 0.4 = parallel signal). Operator wants complementary framing.

| Line | Current text | Rewrite direction |
|------|-------------|-------------------|
| 95 | "Phase 3 (BCI, conditional): validated EEG markers -> true state -> predicted delta" | Reframe: BCI as complementary estimator alongside self-report, weighted by signal-to-noise ratio |
| 362 | "BCI becomes optional enhancement, not core" | Reframe: BCI contributes to a weighted cognitive state estimate; neither source is disposable |
| 370-380 | Full Phase 3 section with r > 0.6 / r < 0.4 gate | Replace gate with: Bayesian combination. Low correlation = different constructs (interesting, not bad). High correlation = validation (less new info). Weighting proportional to per-source SNR. |
| 496 | "Medium-term: BCI provides the moment-to-moment data that self-report cannot" | Keep — this is accurate and complementary-framing-compatible |
| 527 | "the BCI, the startup are all downstream" | Keep — context unchanged |

Total rewrite scope: ~3 paragraphs. Phase 2 work.

---

## G. Documentation Structure Proposal

**Current: 19 files. Target: 12 files.**

### Keep as-is (7 files)
- `MANIFESTO.md` — living research + product philosophy (with updates from this audit)
- `FEATURES.md` — shipped + planned features
- `LYRA_BUGS.md` — live bug tracker (with cleanup)
- `README.md` — repo landing page (with major update)
- `CLAUDE.md` — Claude Code operational directives
- `CONTRIBUTING.md` — process rules
- `openclaw/skills/lyra-secretary/SKILL.md` — agent endpoint reference

### Consolidate (create 3, delete 7)
- `docs/methodology.md` — merge from: clustering_spec.md, hypotheses.md. Contains: research protocol, clustering model, validation gates, all hypotheses (H1 cross-ref to MANIFESTO, H4, future hypotheses).
- `docs/product.md` — merge from: category_taxonomy.md, competitive_landscape.md, v2_backlog.md. Contains: taxonomy with category_type, competitive landscape, v2 backlog, customer discovery stub.
- `docs/architecture.md` — merge from: multiuser_migration_plan.md, phase_4_prerequisites.md. Contains: multi-user migration (historical + current state), schema refactor plan, useCurrentTime hook, stale session recovery, interruption flow design.

### Keep standalone (2 files)
- `docs/dogfood_findings.md` — operator session log, active during Phase 3.5
- `backend/docs/GOOGLE_OAUTH_SETUP.md` — technical setup guide, standalone

### Archive (1 file)
- `lyra_final_spec.md` — add "HISTORICAL — superseded by MANIFESTO.md + FEATURES.md" header. Do not delete (research record).

### Delete (2 files)
- `docs/README.md` — outdated index; README.md and docs/ folder structure are self-explanatory
- `DOCKER.md` — merge the 3 useful lines (compose commands) into CLAUDE.md or README.md, delete the rest

**Net: 19 -> 12 files. 7 fewer docs to maintain.**

---

## H. Dogfood Findings State

`docs/dogfood_findings.md` was populated earlier today (commit 277097e). It contains:
- 5 sessions with readiness, focus, planned, executed, delta, and notes
- 3 P0 items (all marked FIXED: Redis key leak, Pydantic mismatch, completion_pct bypass)
- 5 P1 items (error messages, sort order, voided filter, void affordance, stale .next cache)
- 3 P2 items (pause reason prompt, bulk void, session timeline viz)
- 4 observational notes

The session data was reconstructed from conversation memory, not verified against the database. Actual duration/delta values may differ. The findings are directionally correct but the numbers should be treated as approximate.

No findings are listed as open that have already been fixed.

---

## I. Architectural Coherence Assessment

The operator asked: "Are the overlapping models coherent, or are they four parallel theories masquerading as one?"

The project has four taxonomic systems:

1. **Three behavioral profiles** (Calibrated / Reactive / Overplanner) — a research observation about how users relate to the planning layer. Derived from operator's own data on Day 2.
2. **Five operational archetypes** (Disciplined Lark, Disciplined Owl, Diffuse Average, Procrastinator, Lark Low-Discipline) — a product mechanism for cold-start personalization. Derived from psychometric literature.
3. **Eleven categories x two types** (estimable / time_anchored) — a data taxonomy for filtering which sessions contribute to the bias-factor model.
4. **Four primary variables** (delta, discrepancy, cascade, unplanned_rate) — the measurement framework.

These are **not** four parallel theories. They operate at different layers:

- The **profiles** answer "what kind of user is this?" based on behavioral data (what they actually do). They are *descriptive* and emerge *after* data exists.
- The **archetypes** answer "what kind of user is this?" based on psychometric data (what they report about themselves). They are *predictive* and apply *before* data exists (cold start).
- The **categories** answer "what kind of task is this?" They are orthogonal to user type.
- The **variables** answer "what are we measuring?" They are orthogonal to both user and task type.

The composition is: for a given (archetype OR profile) x (category, time_of_day) cell, the system predicts a bias_factor. The variables (delta, discrepancy) are the measurements that fill and validate those cells. The cascade model operates on the *sequence* of cells, not individual cells.

This is coherent. The one tension is: the profiles and archetypes are not explicitly linked. A "Reactive Executor" (profile) could be any archetype — reactivity is about planning behavior, not about chronotype or discipline. The clustering spec should note this: profiles describe behavior post-onboarding, archetypes describe predicted behavior pre-onboarding. They are not competing classifications; they measure different things at different times.

---

## J. The Load-Bearing Assumption Most Likely to Break

The operator asked for the weakest point. It is:

**The single-subject generalizability problem is not just a sample-size issue — it is a construct-validity issue.**

Ali Nasser is a CS undergraduate in Cairo with a morning-anchor routine, a BCI research interest, and the motivation to build and operate the measurement instrument he's being measured by. Every calibration constant in the system — the bias_factor priors, the cascade_score thresholds, the archetype assignment boundaries — is being derived from or validated against this one subject.

The 5-archetype clustering spec cites Western adult population norms for MEQ, BFI, BSCS, and GP instruments. These instruments have not been validated on Egyptian CS undergraduates. The MEQ chronotype cutoffs (<=11 evening, >=18 morning) were normed on Swedish and Spanish adult populations. The GP procrastination scale was normed on Canadian undergraduates in 1986. Whether these map meaningfully onto a 2026 Cairo engineering student is an empirical question that the clustering spec assumes away.

This doesn't invalidate the architecture. It means the priors in Section 4 of the clustering spec are *hypotheses*, not facts, and the first 5-10 non-operator users will tell you whether they generalize. The validation gates (especially Gate 3: "prior beats flat") are the correct defense. But if Gate 3 fails, the entire archetype model collapses to a single population prior — which is fine for the product but means the psychometric onboarding was wasted effort.

The most honest thing the docs can say is: "We are building a personalization engine calibrated on one subject and validated against literature that may not transfer. The architecture survives this uncertainty — the Bayesian shrinkage formula converges to personal data within 30 sessions regardless of prior quality. But the cold-start experience (first 2-3 weeks) for users unlike the operator may be worse than a flat prior. Gate 3 tests this."

This is not in any doc. It should be.

---

## K. The Single Most Important Thing the Docs Don't Say

The docs don't say what the product actually *is* for a new user.

The manifesto opens with research philosophy. The README opens with architecture. FEATURES.md opens with a version changelog. No document answers: "I'm a new user. What does this thing do for me? Why would I keep using it after Day 1?"

The answer is: Lyra Secretary shows you the gap between how you plan and how you execute, and over time, it gets better at predicting when you'll overrun. The research layer is what makes the predictions improve. The friction (readiness/reflection capture) is the data that powers the predictions.

This should be the first paragraph of README.md. Not "adaptive task scheduling backend for a personal cognitive operating system." A user doesn't care about cognitive operating systems. They care about: "I always think coding will take 30 minutes and it takes 90. Lyra learns that and tells me before I plan wrong again."

---

*End of Phase 1. Commit this file, then halt for operator review.*
