# Brain-dump Onboarding — Design + Edge-Case Findings

**Date:** 2026-04-29
**Shipped:** commit `f816986` (parser, endpoint, UI, tests) + commit `67fa1fd` (re-onboarding gate)
**Replaces:** the single-meta-task onboarding ("Plan your week — brain dump and triage") that landed users on /today with one SKIPPED row and zero engagement signal.

---

## Operator-locked design (2026-04-28 evening)

Direct quotes from the conversation that pinned the shape of this surface:

- *"i honestly think the brain dump feature catches the user from the get go."*
- *"it shouldn't create a planning task afterwards I just planned my week in the first modal."*
- *"it should parse the user's deadlines, link tasks with each other if using confidence scores and confirming with the user as a block with one tap questions."*
- *"less magic but more deterministic."*
- *"NO KEEP THE SURVEY AND CONSENT CHECKBOXES — only the tutorial at the end."*
- *"remove the time completely from the brain dump, multiple timings should be parsed."*

Locked invariants:
1. Heuristic-only on the synchronous critical path. **No model dependency.** Deterministic deadline suggestions may appear after task creation and require explicit user confirmation.
2. **No meta-task** created. The brain-dump items themselves are the user's first plan.
3. Form has **only the textarea**. No title field, no start/end pickers, no category dropdown — all of it parsed from the text.
4. Two-step flow: dump → confirmation block (kind/title/when cards + one-tap binding pills) → commit.

---

## Architecture

```
frontend/components/onboarding-flow.tsx (rewritten)
  ↓ Step 1 — textarea + "Parse my plan" button
  POST /v1/brain-dump/parse  ── pure function, no DB writes
  ↓ Step 2 — preview cards + binding pills + "Lock in"
  POST /v1/brain-dump/commit ── intentional partial-success orchestration:
    1. deadlines first through DeadlineManager.create_deadline
    2. tasks next through TaskManager.create_task, force_conflicts=True,
       passing deadline_id when binding was confirmed
    3. report created, reused, rejected, and failed items explicitly
    4. stamp onboarding_completed_at through the idempotent fallback for
       deadline-only or empty-commit cases

The managers currently commit canonical items independently. The endpoint must
never claim all-or-nothing atomicity until transaction ownership is explicitly
refactored and failure-injected. Partial success is user-visible behavior and
requires direct retry/navigation rather than hidden repair.

backend/app/services/brain_dump_parser.py    ── pure heuristic
backend/app/api/v1/endpoints/brain_dump.py   ── /parse + /commit
backend/app/schemas/brain_dump.py            ── Pydantic models
frontend/lib/brain-dump.ts                   ── typed client
```

### Parser pipeline (pure function, no I/O)

```
raw_text
  ↓ SEGMENT_SPLIT regex: comma | newline | semicolon | " then " | " + "
segments[]
  ↓ for each segment:
    1. _classify_kind(seg)        → ("task" | "deadline", confidence)
    2. _extract_when(seg, now)    → naive local datetime | None
    3. _strip_date_tokens(seg)    → cleaned title
    4. blend confidence (kind + has-date)
    5. demote deadline → task if no when_local (better to schedule
       than reject)
    6. apply default when_local for undated tasks (now + 30min,
       staggered 30min between consecutive defaults)
items[]
  ↓ for each parsed task vs each parsed deadline:
    deadline_heuristic.score_deadlines(...) — same Tier 0 engine
    used by /v1/create's auto-bind path
bindings[]  (tier1_auto, tier2_ask, or filtered out at tier3_skip)
  ↓
BrainDumpParseResponse {items, bindings, parser_status}
```

### Classification — action-verb-wins (operator-tuned 2026-04-29)

The Apr 28 edge-case battery surfaced a bug: "study for midterm tomorrow" was classified as a **deadline** because "midterm" hits `DEADLINE_KEYWORDS`. The user's intent was clearly to *study* (a task referring to a deadline). Fix: **leading action verb wins, even when a deadline keyword appears elsewhere in the segment.**

```
1. Leading verb in TASK_LEADING_VERBS + has_date  → task   (0.88)
2. Leading verb in TASK_LEADING_VERBS             → task   (0.70)
3. Whole-word deadline kw + has_date              → deadline (0.92)
4. Whole-word deadline kw                          → deadline (0.78, demoted to task if no date)
5. Bare date                                       → task   (0.55)
6. Bare segment                                    → task   (0.42)
```

Whole-word matching for deadline keywords (via `_has_deadline_kw`) prevents the "submit" inside "submitting" false-positive that the original substring check produced.

### Title cleanup

`_strip_date_tokens` runs:
1. Strip leading bullet markers (`-`, `*`, `•`, `1.`, `1)`, `(1)`)
2. Replace every DATE_HINTS span with a space
3. Strip leading deadline-framing (`deadline:`, `due `, `by `)
4. Iteratively peel trailing prepositions (`at`, `on`, `by`, `before`, `after`, `until`, `from`, `to`, `in`, `the`, `for`, `of`, `during`, `around`, `about`, `deadline`, `due`) — up to 4 passes so chains like "for the" peel cleanly
5. Collapse whitespace + trim trailing punctuation

This fixes the title-leak failure mode observed on Apr 28 ("call advisor at 3pm" → "call advisor", not "call advisor at"; "EXAM ON FRIDAY 10AM" → "EXAM", not "EXAM ON"; "BCI paper deadline friday" → "BCI paper", not "BCI paper deadline").

### Date extraction

Three-phase strategy in `_extract_when`:
1. **Pre-translation** for forms dateparser fails on natively. Rewrite map (operator-discovered):
   ```
   this weekend       → saturday
   next weekend       → saturday
   this evening       → today 18:00
   this afternoon     → today 14:00
   this morning       → today 09:00
   tomorrow night     → tomorrow 20:00
   tomorrow morning   → tomorrow 09:00
   tonight            → today 20:00
   next <weekday>     → <weekday>     (PREFER_DATES_FROM=future bumps it forward)
   this <weekday>     → <weekday>
   ```
   Without this, dateparser returns `None` for "this weekend", "next saturday", etc., even though it parses bare "saturday" cleanly.

2. **Whole-segment parse** — try `dateparser.parse(rewritten, PREFER_DATES_FROM='future', RELATIVE_BASE=now_local)`. Catches bare date strings like "Friday 10am".

3. **Span-extraction fallback** — when whole-segment fails (e.g. "midterm exam Friday at 10am"), find every `DATE_HINTS` regex span, try the joined-span substring first ("Friday at 10am"), then individual spans by length descending. This recovers from segments where date tokens are surrounded by domain words.

4. **`_bump_to_future` post-pass** — if the result is more than 12h in the past, advance one month. Catches dateparser's habit of returning bare "the 15th" as the same-month occurrence even when that day has passed.

### Binding heuristic

Reuses `app.services.deadline_heuristic.score_deadlines` — the same Tier 0 engine that powers /v1/create's auto-bind path. This is intentional: the binding chip on /today should match what the brain-dump confirmation block shows. Same scoring rules, same brittle-token guard, same tier mapping:

```
score >= 0.85 → tier1_auto    (UI pre-checks the binding pill)
0.45-0.84    → tier2_ask     (UI shows pill unanswered)
< 0.45       → tier3_skip    (UI doesn't surface — too noisy)
```

`BRITTLE_TOKENS` (`paper`, `project`, `task`, `work`, `report`, `doc`, etc.) prevents matches that depend solely on generic words. Verified on the Apr 28 battery: "paper due Friday" + "finish other work tonight" correctly produced no binding because "paper" is brittle.

---

## Edge-case battery findings (2026-04-29 second pass)

15 cases run live against `moriartyholmesberg@gmail.com` (uid=15, assistant runtime test arena per `memory/project_test_arenas.md`). All hard bugs surfaced in the Apr 28 first pass were fixed.

| Verification | Result |
|---|---|
| Title leaks (`at`/`on`/`deadline`/`due` trailing) | ✅ all 15 cases clean |
| Action-verb-wins classification | ✅ "study for midterm tomorrow" → task → tier1_auto bind to midterm (1.00 confidence) |
| Leading bullet/number stripping | ✅ "- read" and "1. read" titles cleaned |
| `+` separator splitting | ✅ |
| `this weekend` / `next saturday` parsing | ✅ resolves to next Saturday |
| `the 15th` parsing | ✅ bumps to next-month if current-month 15th has passed |
| `May 16` month-name parsing | ✅ |
| `3:30pm tomorrow` decimal time | ✅ resolves to 15:30 tomorrow |
| Whole-word `_has_deadline_kw` (no false-positive on "submitting") | ✅ |
| backend pytest | 549/549 passing, 31 brain_dump tests included |
| frontend tsc / build | clean |

3 of 15 cases produced auto-bindings end-to-end:
- `"midterm Wednesday\nstudy for midterm tomorrow"` → tier1_auto 1.00
- `"BCI paper due Friday\nread BCI paper tomorrow"` → tier1_auto 1.00 (after title-strip dropped "due")
- The 5-item operator screenshot dump → 0 bindings when no distinctive token is shared. The UI must make manual binding easy; no model fallback is assumed.

### Known limitations (accepted for alpha)

- **Foreign-language input**: DATE_HINTS regex is English-only. Arabic dumps fall through to default-when; the limitation must be explicit until a researched parser path is approved.
- **Semantic similarity**: heuristic is token-overlap based. "prepare slides" does not bind to "presentation" when they share zero meaningful tokens. Manual deadline selection is the recovery path.
- **`_default_when_for_task` tz drift**: when `current_local_iso` isn't sent by the client, parser falls back to `datetime.now()` which is UTC inside the container. TaskManager then re-interprets as `USER_TIMEZONE` (Cairo) and `to_utc()` shifts it backwards, sometimes landing in the past → `start_in_past` rejection. Frontend always sends `current_local_iso` so the bug doesn't surface for real users; it only affects the test runner.

---

## Re-onboarding gate (commit `67fa1fd`)

Previously, completing the brain-dump (or skipping it via `/users/me/skip-onboarding`) stamped `onboarding_completed_at` and that was final — even if the user committed nothing or only SKIPPED their items. The Apr 29 retention pull found 3 such users (mariam=0 tasks/0 sessions; omar/pbassem each = 1 SKIPPED legacy meta-task) sitting onboarded-but-never-engaged.

Operator decision: any user who completed onboarding but has zero non-voided, non-SKIPPED, non-DELETED tasks should re-see the brain-dump on next visit.

Implementation:
- `/v1/users/me` returns new `has_active_task_history: bool`
- `(app)/layout.tsx` gate is now: `!needsConsent && (!onboarding_completed_at || !has_active_task_history)`

The 3 disengaged users were hard-deleted via the existing `delete_my_account` retain_for_research=False sequence so they sign up fresh next time. See `docs/operator_findings_log.md` Apr 29 entry.
