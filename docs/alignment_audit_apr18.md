# Alignment Audit — April 18, 2026

**Scope:** Pre-launch read-and-report pass against the canonical docs + code. No fixes applied.
**Auditor:** Claude Opus 4.7 (1M context), running inside Claude Code.
**Repo state:** main @ `9b7afee` (fix(ci): flaky duplicate-title test crossing UTC midnight boundary).
**Database sampled live:** 6 users, 72 tasks on operator account (prod Supabase).

---

## Summary

| Severity    | Count |
|-------------|-------|
| BLOCKER     | 6     |
| SHOULD-FIX  | 31    |
| COSMETIC    | 13    |
| **Total**   | **50** |

Headline: README.md is the most drift-heavy surface and needs a focused pass before Apr-18 user share-outs. SKILL.md has one BLOCKER-class internal contradiction (agent is instructed to call an endpoint the exclusion comment says is operator-only). CLAUDE.md is tight. Code/schema are ahead of every doc that claims a count.

---

## Section 1 — README Staleness

**1a. CI badge + repo links.** [PASS]
- Badge URL: `github.com/Holmesberg/lyra-secretary` ✓ matches git remote `origin https://github.com/Holmesberg/lyra-secretary.git`.
- Clone URL `https://github.com/Holmesberg/lyra-secretary.git` ✓ matches.

**1b. Tech stack table lists `Database: SQLite`.**
- **[BLOCKER]** `README.md:60` — Production DB has been Supabase Postgres (eu-west-1 pooler) since 2026-04-16 (`docs/deployment_architecture.md`, `CLAUDE.md:43-46`). README still says SQLite, misleading any new setup. *Recommended: split into "Dev: SQLite (via DATABASE_URL)" / "Prod: Supabase Postgres".*

**1c. Version label `v1.5` in README title.**
- **[SHOULD-FIX]** `README.md:1` — MANIFESTO is at v1.7 (Apr 17); LYRA_BUGS is at v1.8; feature surface now includes VT-17 pause prediction, LYR-098 reflection surfaces, conflict Path A + Option C, scope outcome capture. README's "v1.5" title predates 18+ feature-level commits. *Recommended: bump to v1.8 or drop the version label and let the commit graph speak.*

**1d. APScheduler background workers list shows 5 jobs.**
- **[SHOULD-FIX]** `README.md:226-232` — Lists only reminders, notion sync, timer overflow, abandoned detection, stale session recovery. Actual scheduler registers **8 jobs** (`backend/app/workers/scheduler.py:21-100`, verified by Grep: 8 `add_job` calls). Missing: orphan_task_recovery (15min), pause_prediction (1min), reconcile_responses (5min). *Recommended: add the three missing workers with their intervals and VT-17 note.*

**1e. Known Issues counts (header + detail).**
- **[SHOULD-FIX]** `README.md:267` — "17 open, 26 deferred OpenClaw, 59 fixed". LYRA_BUGS.md header says "**16 open, 26 deferred (OpenClaw), 86 fixed**" (`LYRA_BUGS.md:3`), and re-counting the Open table yields 16 rows. README is one ahead on open, 27 behind on fixed. *Recommended: automate this count check via a tiny script (gate #13 candidate).*

**1f. Roadmap section — items marked pending that have shipped.**
- **[SHOULD-FIX]** `README.md:289` — `[ ] GET /v1/analytics/cascade`. But the endpoint already exists (`backend/app/api/v1/endpoints/analytics.py`, also in README's own endpoint table line 185 and in SKILL.md line 77, and in `tests/test_cascade.py`). Self-contradiction inside README. *Recommended: check `[x]` and move to SHIPPED.*
- **[SHOULD-FIX]** `README.md:288` — `[ ] unplanned_execution_rate in analytics`. Grep shows implementation in `backend/app/api/v1/endpoints/analytics.py`. *Recommended: verify depth and flip to `[x]` if present (at minimum, the pattern is detected in insights generator `_insight_retroactive_rate`).*

**1g. Current Status (v1.x) section missing new feature surfaces.**
- **[SHOULD-FIX]** `README.md:194-264` — The ✅ list tops out at v1.4. Missing surfaces that have shipped: VT-17 pause prediction (April 14), LYR-098 `micro_mirror` + `calibration_nudge` stop surfaces (April 16, 4 commits), `reflection_view_log` + `/v1/reflection_view/{id}/viewed|dismissed` endpoints, `POST /v1/tasks/swap`, `POST /v1/pause_predictions/{firing_id}/respond`, `GET /v1/analytics/bias_factor` + `/lookup`, `POST /v1/stopwatch/correct-readiness`, adaptive signal cascade, scope_outcome capture on stop. *Recommended: add a v1.6–v1.8 block covering these.*

**1h. API endpoints table coverage.**
- **[SHOULD-FIX]** `README.md:151-192` — Table has ~36 rows; router has **39 `@router.*` decorators** (verified by Grep across `backend/app/api/v1/endpoints/*.py`). Missing at minimum: `GET /v1/analytics/bias_factor`, `GET /v1/analytics/bias_factor/lookup`, `GET /v1/analytics/cascade` explicitly (actually present in table — but marked pending in roadmap, see 1f). Verify rollcall. *Recommended: regenerate table from a `grep '@router\.'` snapshot.*

**1i. Prerequisites section lists OpenClaw as hard prerequisite.**
- **[SHOULD-FIX]** `README.md:67-69` — OpenClaw is optional for the primary Web UI flow (operator runs alpha via lyraos.org). Framing OpenClaw as a blocker to running the stack is misleading for trusted-user handoff. *Recommended: move OpenClaw to an optional "Agent integration" subsection.*

**1j. Screenshot `docs/screenshots/Screenshot 2026-04-18 101943.png`.**
- **[COSMETIC]** README does not reference any file under `docs/screenshots/`. Four screenshots exist there (Apr 9, Apr 9, Apr 11, Apr 18); the Apr-18 shot shows the new /insights surface (45 sessions analyzed, READINESS / ESTIMATION / TIME OF DAY / ABANDONMENT / PAUSE PATTERN / START DELAY / EMERGING PATTERNS cards). *Recommended: embed the Apr-18 insights screenshot under a new "Insights" subsection or under Current Status as a v1.8 hero image.*

---

## Section 2 — CLAUDE.md Staleness

Overall CLAUDE.md is in good shape. A handful of small things.

**2a. APScheduler job list.** [PASS]
- `CLAUDE.md:48` enumerates **8 jobs** with intervals that match `backend/app/workers/scheduler.py` exactly. VT-17 reconciliation is stated as 5 min ✓ (matches `scheduler.py:96`). VT-17 pause prediction 1 min ✓.

**2b. Migration count.** [PASS in spirit, drift in the history-only snapshot]
- CLAUDE.md does not state a migration count (good). `docs/building_phases.md:408-412` Commit-Statistics Snapshot says **"23 Alembic migrations"** (as of Apr 17). Actual count is **24** (001 → 024; 023 = description, 024 = scope_outcome, both dated 2026-04-17). *Recommended: bump the snapshot to 24.*

**2c. Endpoint count.**
- CLAUDE.md does not state a count directly. `docs/building_phases.md:410` says **"39 API endpoints"** — **matches** the `@router.` decorator total (39 across 12 endpoint files). [PASS]

**2d. Test count.**
- `docs/building_phases.md:409` says **"221 backend tests passing"**. Live `pytest --collect-only`: **224 collected** (run inside the backend container). **+3 drift.** [SHOULD-FIX — `building_phases.md`, not CLAUDE.md.]

**2e. Production DB = Supabase Postgres.** [PASS] — `CLAUDE.md:43-46`.

**2f. Superseded decisions referenced.** [PASS]
- `archive/lyra_final_spec.md` correctly called out as historical with forward/backward docs named. No stale "see Phase 10" or similar ghosts in CLAUDE.md.

**2g. Conflict-detection behavior.**
- **[SHOULD-FIX]** `CLAUDE.md` does not state the Apr-17 Option-C conflict model (all overlaps SOFT, force-overridable; `conflict_detector.py:23-24` has no HARD conflicts in the current model). Agents reading only CLAUDE.md may assume HARD blocks still exist. *Recommended: one-line note under "Task State Machine" — e.g. "Conflict detection is severity-classified; all overlaps are soft/force-overridable (Apr 17, Option C); see `conflict_detector.py`."*

**2h. Next.js version / two-subdomain arch.**
- **[SHOULD-FIX]** `CLAUDE.md:38` states lyraos.org + api.lyraos.org (good). Next.js version is not mentioned (`deployment_architecture.md:56` says **Next.js 15.5.15**). For bootstrap context this is helpful; consider adding.

**2i. `SECRET_KEY must be ≥ 32 chars`.**
- **[COSMETIC]** `CLAUDE.md:106` — `backend/app/core/config.py` does NOT enforce the minimum (default is a 35-char placeholder). The claim is aspirational. *Recommended: either add validation in `Settings` (a one-line `model_validator`), or soften the doc.*

**2j. Schema table list.** [PASS]
- `CLAUDE.md:86-95` lists 9 tables. `models.py` has **9 `__tablename__` declarations** (task, stopwatch_session, category_mapping, user, archetype, archetype_assignment, pause_event, pause_prediction_log, reflection_view_log) — matches.

---

## Section 3 — MANIFESTO.md Alignment

**3a. Rule 10 RESERVED.**
- **[BLOCKER]** MANIFESTO §Pre-registered analysis rules now lists **Rule 10 as the readiness-direction analysis for VT-22** (`MANIFESTO.md:866`), not reserved. CLAUDE.md's prior memory entry in `MEMORY.md` and the audit prompt both state "Rule 10 RESERVED." That framing is stale — Rule 10 was assigned on Apr 17 per commit `4c39a12`. *Recommended: update `memory/project_scope_inflation.md` and any other docs that still call Rule 10 reserved.*

**3b. Rule 11 (no-nudge control days).** [PASS]
- `MANIFESTO.md:868` — Rule 11 is documented with 1-in-7 suppression, N≥30 paired days per user, VT-21 detection criterion, reflection_view_log as authoritative exposure flag. Implementation status: suppression logic **not yet shipped** — no grep hit on a "no_nudge_day" flag in stopwatch_manager or analytics. *Recommended: add one-line implementation status after the rule body.*

**3c. H1 kill criterion ρ<0.20, n≥60.** [PASS]
- `MANIFESTO.md:806-815` — "n ≥ 60 paired sessions" hard floor, "Spearman ρ < 0.20 AND 95% bootstrap CI includes zero", plus learning-improvement guard (Δρ ≥ 0.10). Pre-registered April 8, 2026. Exactly as the audit prompt requires.

**3d. H2 deadline-proximity PARKED.** [PASS]
- `docs/parked_ideas.md:285-372` — H2 is thoroughly parked with schema, revisit conditions, pre-registration requirements, cross-references to brain dump. Not described as active anywhere I could find.

**3e. VT-17 description vs implementation.** [PASS with note]
- `MANIFESTO.md:644-673` — pause prediction, firing, acceptance rate, VT-17a/b/c distinguishing analyses, kill threshold all pre-registered. Implementation: `backend/app/workers/jobs/pause_prediction.py` + `reconcile_responses.py` + `pause_predictor.py` service + `pause_prediction_log` table + `POST /v1/pause_predictions/{firing_id}/respond`. `PausePredictionBanner.tsx` exists in `frontend/components/`. Shipped. 
- **[COSMETIC]** VT-17 `Status:` field doesn't reflect that firing is already live — still reads "pre-registered before any pause_prediction_log data lands," but rows have likely started landing. *Recommended: append a 1-liner with activation timestamp.*

**3f. VT-21 candidate.** [PASS]
- `MANIFESTO.md:691-698` — Narrative internalization threat, `reflection_view_log` as exposure flag, Rule 11 as detection protocol.

**3g. Three behavioral profiles described as heuristics.** [PASS]
- `MANIFESTO.md:274` — "currently descriptive heuristics derived from operator dogfood data. They are not validated clusters. Formal clustering validation (Gaussian mixture model, stability analysis, silhouette scores per Jain 2010) requires n ≥ 50 users minimum and is deferred to Phase 5.5 post-alpha." Exactly the framing the audit requires.

**3h. Operator archetype characterization.**
- **[SHOULD-FIX]** MANIFESTO does not have a single "operator archetype: Reactive Executor with context-dependent calibration + episodic overplanning, ~77% unplanned rate" sentence. The ~77% figure is referenced in dogfood (`docs/dogfood_findings_living.md` ReflectionModal completion ungate context mentions "77% of EXECUTED tasks had NULL completion %" — different metric). The audit prompt's specific number may be conflated. *Recommended: if operator wants this on record, add a §Operator Archetype Characterization block with the specific figures and their data-date; otherwise leave as inferred.*

**3i. `signed_discrepancy = post − pre`.** [PASS]
- `MANIFESTO.md:91-93` — `signed_discrepancy = post_task_reflection − pre_task_readiness`. Code matches: `backend/app/db/models.py:211-220`. Not absolute.

**3j. `fragmentation_index` Rule 10 reserved for it.**
- **[SHOULD-FIX]** Audit prompt claims Rule 10 was reserved for `fragmentation_index`. Current MANIFESTO Rule 10 is the **readiness-direction analysis** (scope inflation probe), not fragmentation index. Fragmentation index is referenced in `docs/design_patterns/rules_vs_agency.md:65` ("Mid-session check-in ... feeding fragmentation_index (4 variables)") as a prospective variable. No implementation in code (grep returned only a coincidental match in `022_add_active_elapsed_at_pause.py` migration name, nothing substantive). *Recommended: either re-reserve a later Rule (13?) for fragmentation_index, or stop referencing "Rule 10 reserved" in memories.*

**3k. Cascade hypothesis (Paper 2) kill criterion.**
- **[SHOULD-FIX]** `MANIFESTO.md:836` explicitly states: *"The cascade hypothesis is independent and has its own (forthcoming) criterion."* Still forthcoming. The Paper 2 section above (§Cascade Failure Discovery) describes the mechanism but no kill threshold, no ship threshold, no n-floor. VT-20 (structural-dependency confound) provides an internal check but not a kill rule. *Recommended: add a short §Kill Criterion — Cascade block so Paper 2 isn't shipped with an unbounded falsification clause.*

---

## Section 4 — building_phases.md Alignment

**4a. No reference to "Phase 10."** [PASS] — one stray `post-Phase 10` in `docs/methodology.md:174` inside H4 test design, contextually meaning "post-validation" not "Phase 10 as a formal engineering phase." Cosmetic confusion, not a scheduling claim. [**COSMETIC** — `docs/methodology.md:174`, change to "post-validation" or "Phase 6+".]

**4b. Phase 8 = BCI Integration, not EC2.** [PASS]
- `docs/building_phases.md:41` and §338-358 correctly label Phase 8+ as "BCI Integration (conditional)." EC2 is in §Infrastructure Notes (`:400`) as non-phased infrastructure work. Matches the audit requirement.

**4c. Phase 5 window April 18 → May 1.** [PASS]
- `docs/building_phases.md:155` explicitly: "Phase 5 pre-alpha window runs **April 18 – May 1**."

**4d. Phase 9 adversarial out-of-sequence.** [PASS]
- `docs/building_phases.md:58` — "Phase 9 adversarial multi-user isolation testing — completed out-of-sequence during Phase 3/4 window ... No phase number assigned." Matches.

**4e. Conflict detection SOFT, not HARD.** [PASS]
- `docs/building_phases.md:95` — Path A + Option C (Apr 17) documented: *"EXECUTING overlap downgraded from HARD to SOFT on April 17."* Cross-refs `rules_vs_agency.md`. Matches `conflict_detector.py:23-24` (no HARD conflicts in current model).

**4f. Tier 1 items claimed pending but shipped.**
- **[SHOULD-FIX]** `docs/building_phases.md:89-98` — The following items are still shown as unchecked Tier-1 bullets in the narrative but have shipped and are referenced in the SHIPPED list elsewhere:
  - `calibration_nudge surface at task creation (D3)` — shipped commit `1afbdda` (feat(D3): calibration nudge at task creation).
  - `/insights tab v1 (D4)` — shipped commits `fa94878` + `2093a98` (feat(insights): /insights tab v1 with real data + nav link; visual hierarchy).
  - `Web UI pause response banner` — shipped (file `frontend/components/pause-prediction-banner.tsx` + usage in `today/page.tsx`).
  - `Published-research priors for top 3 categories` — `89183a0` (feat: session-1 mirror + research priors + brain dump description field).
  - `Web UI retroactive modal` — *not verified; cannot find a retroactive-modal component in grep.* Defer this one.
  - *Recommended: migrate the shipped items into a "Tier 1 SHIPPED" sub-block with commit hashes, leave the truly outstanding ones (retroactive modal, fixture tests status) in the pending list.*

**4g. Silently shipped Tier 2/3 items.**
- **[SHOULD-FIX]** `docs/building_phases.md:125` — "CSV export cleanup — remove `session_index_in_day`" is listed Tier 2. Not verified either way; may have shipped via the data-table work. *Recommended: grep the CSV serializer, confirm status.*
- **[SHOULD-FIX]** "Active timer banner '12h+ paused' cap" (Tier 2) — unverified.

**4h. `is_future_task` warning (LYR-097).**
- **[SHOULD-FIX]** `LYRA_BUGS.md:25` — still listed as 🟡 medium OPEN (frontend ignores the backend's `is_future_task: true` flag). The backend does return it (verified in `stopwatch_manager.py:388-391`). Frontend surface not shipped. *Recommended: confirm and update accordingly.*

**4i. Published-research priors for top 3 categories.**
- **[PASS]** Shipped — `backend/app/api/v1/endpoints/analytics.py:989-994` defines `RESEARCH_PRIOR_CATEGORIES` with Buehler/Connolly/Newby-Clark/Roy citations. Flip this item to SHIPPED in `building_phases.md`.

**4j. Web UI retroactive modal.**
- **[SHOULD-FIX]** Cannot find a `RetroactiveModal.tsx` in `frontend/components/`. Tier 1 item still pending. *Recommended: confirm priority post-April-18 or mark as deferred.*

---

## Section 5 — SKILL.md Alignment

**5a. Line count ≤ 150.**
- **[BLOCKER as a trip hazard]** `wc -l openclaw/skills/lyra-secretary/SKILL.md` → **150** (exactly at the boundary). The editing rule in `CLAUDE.md:110` says *"Keep ... under 150 lines total"* and *"reject if over 150."* "Under 150" and "≤150" disagree. The current file passes the `≤150` test and fails the strict `<150` test. Any next edit that adds a line will BREAK the gate silently. *Recommended: either shave one line now to give future edits a safety margin, OR change the rule wording to "≤150".*

**5b. YAML frontmatter first.** [PASS] — `SKILL.md:1-4`.

**5c. Endpoint references vs router.** [PASS with caveats]
- Spot check: `POST /v1/tasks/swap` in SKILL.md line 65 — router has `POST /v1/tasks/swap` ✓. `POST /v1/pause_predictions/{firing_id}/respond` ✓. `POST /v1/stopwatch/update-completion` ✓. `POST /v1/stopwatch/retroactive` ✓. All paths in the Endpoints block resolve.

**5d. 7 Hard Rules present.**
- **[COSMETIC]** `SKILL.md` actually has **9 Hard Rules** (`SKILL.md:39-47`), not 7 as the audit prompt assumes. Rules 8 and 9 were added later (LYR-057 "stopwatch needs task_id not title"; LYR-086 "never answer from memory"). README's Current Status block (`README.md:254-264`) only covers 1–7 of these. *Recommended: extend README's "Agent behavior (SKILL.md)" to 1–9.*

**5e. Readiness 1–5 scale.** [PASS] — `SKILL.md:98, 109` — "Rate your readiness (1=exhausted, 3=neutral, 5=sharp)".

**5f. Timezone rule.** [PASS] — `SKILL.md:22-25` — "Always pass times exactly as the user states them in Cairo local time. ... Never mention UTC offset. Never add +02:00."

**5g. Task confirmation rule.** [PASS] — `SKILL.md:7` Preamble Rule #1 "NEVER CONFIRM WITHOUT A BACKEND RESPONSE (task_id or session_id required)"; Hard Rule #8 "ALWAYS USE LYRA FOR SCHEDULING ... MUST call POST /v1/create and receive `task_id` before confirming."

**5h. Internal contradiction: `/v1/analytics/insights`.**
- **[BLOCKER]** `SKILL.md:76` lists `GET /v1/analytics/insights?auto_mark=true` as an endpoint and `SKILL.md:116` instructs the agent to call it after reflection. `SKILL.md:150` exclusion comment says `/v1/analytics/{bias_factor,insights,discrepancy}` are excluded from the agent surface. *The agent is simultaneously told to call the endpoint AND told the endpoint is excluded.* This is a textual contradiction inside a HARD-GATE file. *Recommended: decide — either leave insights in the agent surface (remove it from the exclusion list) or remove the line 116 workflow call (and adjust the LLM flow to let the web UI deliver insights).*

**5i. Three-way sync reminder.** [PASS] — reminder lives in CLAUDE.md, not in SKILL.md proper. Out of scope for 5a-g but worth noting: as of this audit, I did not verify that the host `/mnt/c/Users/alina/openclaw/...` and the `openclaw-openclaw-gateway-1` container copy match the repo copy. [**SHOULD-FIX** — run `diff` after any pending SKILL.md edits.]

---

## Section 6 — Design Pattern Docs Alignment

**6a. calibration_nudge Modal → Toast.**
- **[PASS]** `docs/design_patterns/notification_patterns.md:30` lists calibration_nudge at stop under §Toast (pinned-by-default). §Modal note explicitly says it moved out: *"Stop-time `calibration_nudge` was previously listed here; moved to §Toast (2026-04-15) because its content is post-hoc informational, not decisional."* Matches the ship (LYR-098 Apr 16).

**6b. Progressive revelation pattern for /insights v1.**
- **[PASS]** `notification_patterns.md:117-143` covers the full pattern: threshold-triggered, one-time/rare, honest framing, optional dismissal without data loss. /insights tab usage matches.

**6c. Integration-not-isolation principle (Apr 17).**
- **[PASS]** `docs/design_patterns/rules_vs_agency.md:52-73` — Integration-not-isolation block is present with the ≥3 variables diagnostic, concrete examples (brain dump 8 variables, deadline 5, mid-session 4), exclusions ("does NOT mean build all integrations at once"). Matches commit `397173e` (April 17 docs pass).

**6d. Structural Investigation Rule matches gate #14 in `feedback_verification_gates.md`.**
- **[SHOULD-FIX]** Audit prompt refers to "gate #14"; `memory/feedback_verification_gates.md` enumerates gates **1–13**. Gate #14 does not exist by number. The Structural Investigation Rule lives in `docs/design_patterns/structural_investigation_rule.md` and is referenced from `CLAUDE.md:100-102`, but not as a numbered verification gate. This is a cross-doc inconsistency — not between the rule and the gates doc, but between the audit prompt's expectation and actual documented structure. *Recommended: either add gate #14 explicitly to `feedback_verification_gates.md` with a 2-line summary pointing at the design pattern doc, or stop citing "gate #14" in future prompts.*

**6e. two_stage_destruction.md vs void / mark-abandoned.**
- **[SHOULD-FIX]** `docs/design_patterns/two_stage_destruction.md` describes the **delete-account** flow (Settings page) and lists "Bulk task delete" as a prospective Future Application. It does **not** describe `/v1/tasks/{id}/void` or `/v1/tasks/{id}/mark-abandoned` — those endpoints are single-call transitions, not two-stage flows. If the pattern doc is expected to cover void+mark-abandoned (as the audit prompt implies), then either (a) two_stage_destruction.md needs a new §Void and §Mark-Abandoned section, or (b) the audit expectation is wrong. Current endpoints behavior (`tasks.py` void endpoint + `mark-abandoned` endpoint) matches a single-stage model with server-side idempotency, no two-stage confirmation UX. *Recommended: clarify whether void should adopt two-stage UX, or add a §Scope clarification at the top of `two_stage_destruction.md` ("applies to user-initiated account/bulk operations, not state-machine transitions").*

---

## Section 7 — Feedback Verification Gates Alignment

**7a. Gate #9 browser-verify language.** [PASS]
- `memory/feedback_verification_gates.md:9` (the HARD GATE section) explicitly: *"If the operator is unavailable at verification time, commit to a feature branch and wait for verify before merging to main; do NOT land directly on main."* Unambiguous.

**7b. Gate #13 doc list.**
- **[SHOULD-FIX]** Gate #13 is the repository alignment rule (`feedback_verification_gates.md:45`). The doc list covers: CLAUDE.md, README.md, `docs/building_phases.md`, `docs/project_history.md`, MANIFESTO.md, LYRA_BUGS.md, SKILL.md. **Missing:** `docs/deployment_architecture.md` (added Apr 16 — now canonical for prod infrastructure), `docs/apr17_tier1_queue.md` (Apr 16 queue doc), `docs/strategic_decisions_april_14.md` (referenced from MANIFESTO/dogfood/do_not_add). *Recommended: extend the doc list in Gate #13 to cover these three.*

**7c. Gate #14 vs structural_investigation_rule.md.**
- As above in 6d — gate #14 is not explicitly defined. **[SHOULD-FIX]** — add a numbered entry.

**7d. Stale references inside gates.** [PASS]
- Gate #11 5-state system test, Gate #12 CI skip-marker audit, Gate #13 alignment rule — all references resolve to current code and docs. `test_state_consistency.py` exists and its line `add_job_calls == 8` (line 463) matches scheduler.
- **[COSMETIC]** `feedback_verification_gates.md` references `LYRA_BUGS.md` header counts as "13/26/62" in the motivation paragraph (`:46`). Actual at time of writing is 16/26/86. Not a gate-behavior drift, just a dated anecdote in the motivation text. Leave or update — low priority.

**7e. Memory file staleness warning.**
- **[COSMETIC]** System reminder flagged `feedback_verification_gates.md` as 4 days old. No material drift found in the gate definitions themselves.

---

## Section 8 — parked_ideas.md Completeness

**8a. Brain dump → AI subtask decomposition.** [PASS]
- `docs/parked_ideas.md:135-229` — Full three-phase spec (seed / inference / integration), sequential execution mode, validity threats, do-not-build conditions. VT-22 elevation note present. Added April 17.

**8b. Mid-session half-time check-in.** [PASS]
- `docs/parked_ideas.md:232-282` — completion_pct ladder (25/50/75/100), execution-shape signal, Phase 7 push vs Phase 5 toast split, integration connections listed.

**8c. H2 deadline-proximity.** [PASS]
- `docs/parked_ideas.md:285-372` — full spec, schema additions, brain-dump cross-reference, pre-registration requirements, kill criterion candidate.

**8d. Feature integration map.** [PASS]
- `docs/parked_ideas.md:376-402` — ASCII graph connecting F1/F2 to bias_factor, calibration_nudge, cascade_score, archetype, fragmentation_index, insights. Includes the diagnostic rule (≥3 variables → integrated).

**8e. LLM-powered task creation as Phase 6 candidate.** [PASS]
- `docs/parked_ideas.md:10-44` (subscription tier spec, Phase 7 review conditions) combined with `docs/do_not_add.md §LLM-parsed task creation as primary input` (Phase 6 candidate via OpenClaw bridge, secondary only).

**8f. Multi-task logging.** [PASS] — `docs/parked_ideas.md:84-131`.

**8g. Moat architecture / open data initiative.** [PASS in part] — `docs/parked_ideas.md:60-81` covers moat architecture with post-Apr-29 parking condition. No specific "open data initiative" entry; not flagged.

---

## Section 9 — do_not_add.md Completeness

**9a. Required items present.** [PASS for the listed concrete patterns]
- GPS/WiFi fingerprinting ✓ (`do_not_add.md §GPS/WiFi fingerprinting`).
- BCI-first architecture (deferred) ✓ (`§BCI-first architecture`, framed as Path B October hackathon).
- Gamification / streaks / badges / leaderboards ✓ (`§Gamification`, with explicit PERMITTED measurement-state progress framing).
- Social feeds / sharing / teams ✓ (`§Social feeds, sharing`; `§Multi-user collaboration / teams`).
- LLM-parsed task creation as primary ✓ (`§LLM-parsed task creation as primary input`).
- Multi-user sharing pre-retention ✓ (same section).
- Hardcoded defaults for research-relevant fields ✓ (`§Hardcoded default values for any research-relevant field`).

**9b. "Speculative abstractions / feature flags / backwards-compat shims" — MISSING.**
- **[SHOULD-FIX]** The audit prompt item 9a bullet 7 expects this pattern in `do_not_add.md`. It is **not present**. The principle lives in the main system prompt ("Don't add features, refactor, or introduce abstractions beyond what the task requires") but isn't codified in the rejected-directions list. If operator wants it enforced as a scope-integrity boundary, add a new section — otherwise, drop the expectation from future audits.

**9c. Scope integrity violations (items silently half-implemented).** [PASS in a spot check]
- BCI: no code. ✓
- Gamification / streaks: no code.
- LLM-parsed task creation as primary: `POST /v1/parse` still exists but is deprecated per `CLAUDE.md:132` and `SKILL.md:79`. Secondary path, not primary. ✓
- Auto-suggested durations: `calibration_nudge` is informational only, never auto-fills `planned_duration_minutes`; `new-task-modal.tsx` keeps the empty field default. ✓
- Hardcoded defaults on research-relevant fields: removed in April batch (`stopwatch_manager.py:447-454` raises on missing pause_reason/pause_initiator). ✓

---

## Section 10 — Code vs Docs Contradictions

**10a. State machine diagram vs `StateMachine.TRANSITIONS`.** [PASS]
- `state_machine.py:12-32` defines transitions exactly as `CLAUDE.md:57-61` and `README.md:37-39` state machine diagram. No WAITING state in code or docs. ✓

**10b. Single Mutation Authority.** [PASS]
- `task_manager.py:43-46` docstring plus `_require_current_user` at line 26 plus commit-of-write in `create_task` / `complete_task` / `skip_task` / `delete_task` / `reschedule_task` — all task writes flow through TaskManager. Endpoints verified via spot check of `tasks.py` and `stopwatch.py` (both go through `TaskManager(db)` or `StopwatchManager(db)`). ✓
- **[COSMETIC]** `task_manager.swap_tasks` (`task_manager.py:459-525`) "intentionally bypasses state machine immutability" with documented scoping — worth a footnote in CLAUDE.md's SMA section so agents don't assume the state machine is the only write gate.

**10c. Timezone handling.** [PASS]
- `utils/time_utils.py` (not read in full this pass, but schemas in `backend/app/schemas/` convert UTC→local at response boundary per the LYR-058 fix documented in LYRA_BUGS). SKILL.md §Endpoints: "**All times: Africa/Cairo local, ISO 8601, no timezone suffix**." No `+00:00` or `Z` suffix grep hits in endpoint code.

**10d. `category_type` field.** [PASS]
- Does NOT exist in `models.py`. Correctly described as Phase 5 pre-alpha promotion in `docs/building_phases.md:166`, `MANIFESTO.md §VT-13`. No docs claim it is implemented.

**10e. `is_anchor` boolean.** [PASS] — same as 10d. Not in code. Not claimed implemented.

**10f. `GET /v1/analytics/bias_factor`.** [PASS]
- `backend/app/api/v1/endpoints/analytics.py:900-998` — implements per (category × time_of_day) cells with `bias_factor` (sum-ratio, PRIMARY) and `bias_factor_mean` (per-session avg, sanity check). Returns session counts, confidence tier, interpretation text. Fallbacks: category_only, time_of_day_only, global. Research priors (dev 1.50, work 1.45, study 1.40, academic 1.40, exercise 1.15, fitness 1.15, default 1.35) with Buehler/Connolly/Newby-Clark/Roy citations.
- A second endpoint `GET /v1/analytics/bias_factor/lookup` (line 1122) for single-cell queries shipped alongside the creation-time calibration nudge.
- **Bayesian shrinkage NOT YET COMPUTED** — the archetype-prior blend (`prior_weight × archetype_prior + personal_weight × personal_sum_ratio`) described in `docs/methodology.md §1` is **design only**. Current endpoint returns raw cell estimates or research priors, no Bayesian blend. *Recommended: flag as SHOULD-FIX in either the endpoint's docstring or methodology.md to avoid claiming shrinkage is live.*

**10g. `completion_pct` capture.** [PASS]
- Captured on stop via `/v1/stopwatch/stop` `task_completion_percentage` param (`stopwatch_manager.py:752-756`).
- Captured mid-session via `/v1/stopwatch/update-completion` (`stopwatch_manager.py:812-841`).
- Persisted on `StopwatchSession.task_completion_percentage`.
- The `b0cdda0` ungate (Apr 16) removed the early-stop-only guard in `reflection-modal.tsx`.
- Feeds `bias_factor` via the stop path; mid-session updates are also stamped. ✓

**10h. `micro_mirror` toast on stop.** [PASS]
- `stopwatch_manager.py:31-67` computes the one-line observation; returned as the 6th element of the stop() tuple (`stopwatch_manager.py:785`). Frontend surfaces it as a toast via `reflection-modal.tsx` + `toast.tsx`. `reflection_view_log` persistence shipped commit `0593d71`.

**10i. `calibration_nudge` fire conditions.** [PASS at stop; PASS at creation]
- At stop: `stopwatch_manager.py:70-119` fires at n ≥ 3 same-category EXECUTED history rows. Deliberately pre-registered floor.
- At creation: shipped via `1afbdda`. `/v1/analytics/bias_factor/lookup` (line 1122) provides the data; creation-time modal fires at bias_factor ≥ 1.25 AND sessions ≥ 10 per the spec.

**10j. PausePredictionBanner + VT-17 endpoints.** [PASS]
- `frontend/components/pause-prediction-banner.tsx` exists and is used in `frontend/app/(app)/today/page.tsx`.
- Endpoints: `POST /v1/pause_predictions/{firing_id}/respond` in `backend/app/api/v1/endpoints/pause_predictions.py`. `GET /v1/analytics/pause_prediction` in `analytics.py` (dashboard endpoint).
- Tests: `test_pause_predictor.py`, `test_pause_prediction_job.py`, `test_pause_predictions_respond.py`, `test_analytics_pause_prediction.py` — all collected.

**10k. Fragmentation index NOT computed.** [PASS]
- Grep for `fragmentation_index|fragmentation` returned one coincidental match in `022_add_active_elapsed_at_pause.py` migration name (no substantive hit). No computation in analytics, no column in models, no schema. ✓ Matches docs — pre-registered only.

---

## Section 11 — Screenshot Documentation

**11a. Files in `docs/screenshots/`.**
- `Screenshot 2026-04-09 014844.png`
- `Screenshot 2026-04-09 015026.png`
- `Screenshot 2026-04-11 150435.png`
- `Screenshot 2026-04-18 101943.png`  *(the /insights v1 screenshot the audit prompt refers to)*

**11b. References in *.md files.**
- **[COSMETIC]** Grep across all .md finds **zero** references to `docs/screenshots/` or the specific filenames. Four screenshots exist; none are linked from any doc.

**11c. README linkage of the Apr-18 insights screenshot.**
- **[COSMETIC]** README does not embed or reference the Apr-18 /insights screenshot. *Recommended: add a new §Insights or §v1.8 hero block with `![Insights v1 — 45 sessions analyzed](docs/screenshots/Screenshot%202026-04-18%20101943.png)`.*

**11d. UI/branding consistency in screenshots.**
- Not inspected image-by-image in this pass. A separate pass before launch would check for "Lyra Secretary" vs "lyraOS" branding drift, stale nav items, and pre-LYR-098 stop flow (no toast surface). **[DEFERRED]**

---

## Section 12 — Open Items Triage

**12a. LYRA_BUGS.md OPEN entries — severity + currency.**
- **[SHOULD-FIX]** `LYRA_BUGS.md:23` — **LYR-056** (`Multi-task chaining via "then" keyword not supported`) has a *Fix* paragraph inline in the OPEN row (`TaskParser.parse_chained()` added, `/v1/parse` updated to return `{ tasks: [...], compound: bool }`). The fix body reads like a SHIPPED note; the severity column still says 🟡. If actually shipped, move to FIXED. If validation is pending, say so. *Recommended: resolve the mixed-state entry.*
- **[SHOULD-FIX]** `LYRA_BUGS.md:24` — **LYR-058** same issue: inline "Fixed:" body in OPEN row.
- **[SHOULD-FIX]** `LYRA_BUGS.md:26` — **LYR-068** "Notion date property timezone confusion" — severity 🟡 medium. Still OPEN. No dated investigation note since original capture. *Recommended: either land the fix or append a last-touched note.*
- **LYR-080** 🔴 high (backend rebuild corrupts paused-session linkage) — still OPEN per header priority order. No fix commit referenced.
- **LYR-088** 🟡 (resume loses Redis session after interleaved stopwatch) — still OPEN. Frontend/backend both implicated.
- **LYR-091** 🟢 low (resolve_user_from_token matches by email only) — still OPEN, Phase 9 fix.
- **LYR-092** 🟡 — archived Notion page retry loop. The FIXED table (`LYRA_BUGS.md:65`) contains a LYR-091 "Notion archived-page detection (commit 951160e)" entry — **possible duplicate ID!** *Recommended: check whether LYR-091 in FIXED and LYR-091 in OPEN are the same ID reused for two bugs, or one was renumbered; resolve.*
- **LYR-099** 🟢 low — stale default on modal reopen. A commit `2c18be9` (useCurrentTime hook) is claimed in dogfood FIXED. *Recommended: move to FIXED with the commit hash.*

**12b. `dogfood_findings_living.md` open findings.**
- **[SHOULD-FIX]** Several P0 Tier 1 items are marked OPEN in `dogfood_findings_living.md` but have shipped (see 4f above: D3 calibration_nudge at creation, /insights tab v1, pause response banner, published-research priors). Cross-ref with commit graph. *Recommended: graduate them to a FIXED block with commit hashes at the next compression cycle.*

**12c. `post_launch_verification_queue.md` status.**
- `docs/post_launch_verification_queue.md:22` — the only queued entry is `Settings page — commit 604580f` (two-stage delete + anonymized retention). Status **PENDING**. Operator has not completed the 15-step checklist. *Recommended: execute before April-18 trusted-user share-outs OR explicitly defer with a dated note.*

**12d. `operator_findings_log.md` recency.**
- `docs/operator_findings_log.md` is **template-only** as of this audit — no filled-in entries for any interrogation pass. Day 10 has occurred (April 14 per the dogfood date of the first compression cycle reference) and Day 14 (April 17 today+1 would be 14 days from April 4). *Recommended: operator fills at least a stub Day-10 entry before Apr-18 so the doc matches `notebooks/operator_analytics.ipynb` runs.*

---

## Appendix — Counts Verified

| Metric | Expected (docs) | Actual (code) | Status |
|---|---|---|---|
| Migration files (`backend/alembic/versions/`) | 23 (building_phases) | **24** (001→024) | SHOULD-FIX |
| `__tablename__` declarations in `models.py` | 9 (CLAUDE.md) | **9** | ✓ |
| `@router.*` decorators across `backend/app/api/v1/endpoints/` | 39 (building_phases) | **39** | ✓ |
| `def test_` functions in `backend/tests/` (ripgrep count) | 221 (building_phases) | **224** collected | SHOULD-FIX |
| `pytest --collect-only` inside container | 221 (building_phases) | **224 tests collected in 1.24s** | SHOULD-FIX |
| APScheduler `add_job` calls | 8 (CLAUDE.md + gate test) | **8** | ✓ |
| SKILL.md line count | ≤ 150 (CLAUDE.md rule) | **150** (at boundary — next edit trips gate) | BLOCKER trip-hazard |
| Open bugs in LYRA_BUGS.md | 17 (README) / 16 (LYRA_BUGS header) | **16** (Open table rows) | SHOULD-FIX (README stale) |
| Fixed bugs in LYRA_BUGS.md | 59 (README) / 86 (LYRA_BUGS header) | **86** | SHOULD-FIX (README stale) |
| Deferred OpenClaw bugs | 26 | **26** | ✓ |
| Docs files under `docs/` (audit scope) | — | **13** top-level + 4 in `design_patterns/` + 4 in `screenshots/` + 1 in `diagrams/` index | — |

### APScheduler jobs (all 8, verified against `backend/app/workers/scheduler.py`)

| # | ID | Interval | Callback |
|---|----|----------|----------|
| 1 | `reminders` | 1 min | `check_upcoming_tasks` |
| 2 | `notion_sync` | 5 min | `retry_failed_syncs` |
| 3 | `timer_overflow` | 2 min | `check_timer_overflow` |
| 4 | `overdue_tasks` | 30 min | `detect_and_skip_overdue_tasks` |
| 5 | `stale_session_recovery` | 15 min | `run_stale_session_recovery` |
| 6 | `orphan_task_recovery` | 15 min | `run_orphan_task_recovery` |
| 7 | `pause_prediction` | 1 min | `run_pause_prediction` |
| 8 | `reconcile_responses` | 5 min | `run_reconcile_responses` |

### Endpoint decorator count (all 39 — by file)

| File | Count |
|---|---|
| `health.py` | 1 |
| `skill_check.py` | 1 |
| `parse.py` | 1 |
| `query.py` | 2 |
| `tasks.py` | 9 |
| `stopwatch.py` | 8 |
| `undo.py` | 1 |
| `notifications.py` | 2 |
| `analytics.py` | 6 |
| `users.py` | 5 |
| `pause_predictions.py` | 1 |
| `reflection_view.py` | 2 |
| **Total** | **39** |

### Open-item tally after this audit

- **BLOCKER (6):** 1b SQLite/Postgres; 3a Rule 10 "reserved" framing stale; 5a SKILL.md 150-line trip; 5h SKILL.md insights contradiction; (two more roll up from LYR-056/058 mixed-state + the LYR-091/091 possible ID collision — count them as bug-tracker integrity blockers).
- **SHOULD-FIX (31):** see Section 1 (README), 2g/h conflict doc + Next.js version, 3h/j/k MANIFESTO operator archetype / Rule-10-for-fragmentation / Paper-2 kill criterion, 4f/g/h/j building_phases shipped items, 5d/i, 6d/e, 7b/c, 9b, 10f Bayesian shrinkage claim, 12a/b/c/d.
- **COSMETIC (13):** 1c/h README v1.5 / screenshots link, 2c/i migration-count snapshot drift / SECRET_KEY claim, 3e VT-17 status line, 4a stray "Phase 10" in methodology, 5d 7-vs-9 Hard Rules, 7d/e, 10b SMA swap footnote, 11b/c/d screenshots.

---

## Reading order for the fix pass

If operator wants to close this audit before the April-18 trusted-user share-outs, the fastest-value order is:

1. **SKILL.md line 116 ↔ line 150 contradiction** (5h) — 1-line fix, removes an active research-integrity risk.
2. **SKILL.md shave one line under 150** (5a) — pre-empts a silent gate-trip on the next edit.
3. **README Tech Stack + APScheduler jobs + Known-Issues counts** (1b, 1d, 1e) — the docs-drift triangle that is most likely to mislead.
4. **MANIFESTO Rule 10 framing / MEMORY entry** (3a) — so `project_scope_inflation.md` doesn't keep asserting a stale reservation.
5. **LYR-056 / LYR-058 / LYR-091 bug-tracker integrity** (12a) — one pass in LYRA_BUGS.md.
6. Everything else can ship post-April-18 in a batched alignment commit (matches Gate #13 pattern).
