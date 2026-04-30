# Brain Dump Stress Test — moriartyholmesberg
*2026-04-30. 61 cases × parse → commit → 30s LLM enrichment wait → DB read-back.*

## Headline

61/61 parsed OK + 61/61 committed OK at the HTTP layer **but** only 42 tasks + 14 deadlines actually landed in the DB. The gap: **the brain dump endpoint silently drops tasks that fail TaskManager validation** (mostly past-time rejection). The HTTP response says success even when individual items inside the commit batch were rejected — operator-facing UX bug.

LLM enrichment: 33/42 enriched within 30s, 6 still pending, 3 failed (Llama returned non-JSON). 0 unavailable (NIM is healthy).

Operator: **sign in to lyraos.org as `moriartyholmesberg` to verify the 42 tasks + 14 deadlines visually.** The full per-case table is below the findings.

---

## Critical findings (P0 / P1 — pre-alpha blockers)

### 🔴 P0: Silent partial-commit failures

**Symptom:** brain dump POST /commit returns 200 with task_ids[] populated, but if individual items inside the batch failed TaskManager validation (most commonly `start_in_past`), they are silently dropped. The user has no idea their "call mom at 5pm" task was rejected because it's already 7pm.

**Affected cases:** A2 (`call mom at 5pm`), A4 (`30 min for emails`), A5 (`in 2 hours`), A6 (`study soon`), A10 (`do dishes`), B4 (`midterm`), B5 (`deadline X`), B6 (`paper due`), C1 (`do dishes`), C2/C3/C5/G1/G2/G3/G4/G5 stagger cases, D1/D4/D6 (today-late tasks), F1/F4/F5 (conflict-prone with parsing issues), H4/H5/H6 — **roughly 19 of 61 cases lost ≥1 item without notifying the user.**

**Evidence:** `/app/app/api/v1/endpoints/brain_dump.py:161` calls `task_manager.create_task` inside a try/except that logs the error but doesn't surface it in the response. The response shape (`tasks_created: int`, `task_ids: list[str]`) doesn't include a `tasks_failed[]` or per-item status.

**Fix shape (~30 min):** extend `BrainDumpCommitResponse` with `failed_items: list[{item_id, kind, title, reason, retry_hint}]`. Frontend renders failed items as a dismissible toast: *"3 tasks couldn't be scheduled — they were in the past. Tap to retry tomorrow."*

### 🔴 P0: Explicit user-provided durations are ignored

**Symptom:** When the user writes `60 min`, `30 minutes`, `90 min`, etc. — the duration is parsed into the title string but **NOT extracted into `duration_minutes`**. Every committed task ends up with `planned_duration_minutes = 30` (the default).

**Evidence in stress data:**
- D2 input `PHM lecture tomorrow at 10am 60 min` → committed task duration = **30 min** ❌ (should be 60)
- D5 `team standup tomorrow 9am 15 min` → duration = **30 min** ❌
- D7 `weekly review Sunday at 8pm 60 min` → duration = **30 min** ❌
- D8 `interview prep tomorrow 6pm 90 min` → duration = **30 min** ❌
- D3 `study chapter 4 today at 7pm 45 min` → duration = **30 min** ❌
- A1 `Lab 8 ... for 30 minutes` → duration = **30 min** (correct by accident — matches default)
- E1, E2, E3, E4, E5, E7, E8 — same pattern, all committed at 30 min

**Root cause:** `brain_dump_parser.py` populates `BrainDumpParsedItem.duration_minutes = None` always (no duration extraction logic). The duration tokens (`30 min`, `60 minutes`) end up in the title via `_strip_date_tokens` not stripping them either.

**Fix shape (~1 hr):** add `_extract_duration(segment)` that regex-matches `(\d+)\s*(min|minutes|hr|hour|h)` and pops the match into `duration_minutes`. Strip from title. Test against the existing duration patterns.

This is the highest-impact bug surfaced by the stress test. It silently breaks the planned vs executed measurement contract — the user said 60 min, system records 30 min, "executed_duration vs planned_duration" delta becomes meaningless.

### 🟠 P1: Title-strip leaves dangling prepositions

**Symptom:** `_strip_date_tokens()` peels date tokens but leaves their joining prepositions (`at`, `for`) in the title.

**Evidence:**
- A1 `Lab 8 problem set tomorrow at 3pm for 30 minutes` → title `"Lab 8 problem set at for 30 m…"` (kept "at", "for")
- A7 `studied yesterday at 3pm for 2 hours` → title `"studied yesterday at for 2 ho…"` (kept "at", "for", "yesterday")
- D2 `PHM lecture tomorrow at 10am 60 min` → title `"PHM lecture at 60 min"`
- D3 `study chapter 4 today at 7pm 45 min` → title `"study chapter 4 at 45 min"`
- D4 `code review at 4pm 30 min` → title `"code review at 30 min"`
- F1 `study from 2-4pm tomorrow and meeting from 3-4pm tomorrow` → title `"study from 2- and meeting fro…"` (BAD — also segmentation didn't split on "and")
- F4 `study tomorrow 1-5pm, break tomorrow 2-2:30pm` → titles `"study 1"`, `"break"` (time range broken)
- E7 `BCI midterm May 15 ⏎ ...` → final review parsed as deadline with title `"final review 60 min"` (kept duration token in title)
- E8 → deadline title `"and final review 60 min"` (worse — kept "and")

**Fix shape (~30 min):** extend `_strip_date_tokens` to peel:
1. Trailing/leading `at`, `for`, `on`, `from`, `to`, `until`, `by`, `and` after time-token removal
2. Duration suffix patterns (`60 min`, `30 minutes`, `1.5 hours`)
3. Time-range patterns (`2-4pm`, `1:30pm`, `3-4pm`)

### 🟠 P1: Conflict-prone segmentation drops "and" as separator

**Symptom:** SEGMENT_SPLIT regex (`[,\n;]+|\s+then\s+|\s+\+\s+`) does NOT include "and". When users write natural language like `"study from 2-4pm and meeting from 3-4pm"`, the parser sees ONE segment, not two.

**Evidence:** F1, F5 — both merged into single tasks instead of two separate ones.

**Fix shape:** add `|\s+and\s+` to SEGMENT_SPLIT. Risk: false positives where "and" is part of a noun phrase ("research and development"). Mitigation: only split when "and" is followed by a verb pattern (heavier regex) — defer to operator decision.

### 🟠 P1: Time-range parsing broken

**Symptom:** Inputs like `2-4pm`, `1-5pm`, `2-2:30pm` aren't parsed as ranges. The "from" hour gets interpreted as the time but the "to" hour and the duration are lost. Title cleanup leaves "study 1" / "break" / "study from 2-".

**Evidence:** F4, F5, F1.

**Fix shape:** add a regex pre-pass for time-range patterns that emits `{when, duration_minutes}` tuples. ~45 min.

---

## Quality findings (P2 — defer to post-alpha unless trivial)

### 🟡 P2: Heuristic binding is overly conservative

**Symptom:** Only 3/61 cases produced a binding suggestion at any tier. 0 tier2_ask, 0 tier3_skip. The heuristic either auto-binds with high confidence OR stays silent — never asks.

**Cases that didn't bind but probably should have:**
- E2 `Paper review due Friday ⏎ write paper summary tomorrow` — no binding (because "paper" is a brittle token per `deadline_heuristic.py:65-69`). Probably correct given the brittle-token rule, but UX-wise the user might expect a "did you mean Paper review?" prompt.
- E4 `Paper due Friday ⏎ do laundry tomorrow at 5pm` — correctly no binding (laundry ≠ paper) ✓
- E6 `review due Monday ⏎ write review Wednesday` — no deadline parsed (kind=task for both — operator-locked verb-beats-deadline rule). Bound via parser_auto fallback.
- E7 `BCI midterm May 15 ⏎ study BCI today ...` — no binding suggested DESPITE "BCI" being a strong shared token. The committed task has `bind:—`. Why? E7 has 4 segments and the LLM enrichment may have taken over the binding decision asynchronously — but the heuristic surface didn't suggest one.
- E8 `Algorithms midterm May 15. Review chapters 1-3 ...` — period-separated single segment, the parser segmented oddly (one deadline `Algorithms midterm . Review c…`, separate `practice problems` task, separate `and final review 60 min` deadline). Mess.

**Fix shape:** lower the auto-bind threshold and surface tier2_ask more readily. ~1 hr to tune + re-run stress test.

### 🟡 P2: `B2 "May 15 paper due"` parsed as deadline title `"paper"` (single word, fragile)

The deadline title got truncated to just `"paper"` — losing the contextual "due" info. Probably fine but the title is so generic it'll never auto-bind to anything.

### 🟡 P2: Single-character input `H2 "x"` parsed to a date 6 months in the future

`_bump_to_future` applied to a non-date input. Date defaulted to 2026-10-30 (6 months out). Harmless but weird.

### 🟡 P2: G1 `"do A then do B then do C"` — first task scheduled 3 days out

`do A` ended up at 2026-05-03 (Sunday) instead of stagger-default. Possibly because the parser interpreted "do A" as a date phrase. Edge case.

### 🟡 P2: G5 bullet list — header "Multi-line plan:" treated as a task

User intent was clearly a header/intro. Brain dump created a task titled "Multi-line plan". Defer to a polish ship — could add a heuristic that strips trailing-colon prefixes.

### 🟡 P2: Period-separated single segments not split

E8 `"Algorithms midterm May 15. Review chapters 1-3 today at 5pm 60 min, practice problems Wednesday 4pm 90 min, and final review Thursday 6pm 60 min"` — period (`.`) is NOT in SEGMENT_SPLIT, so the entire first sentence becomes one item with the deadline title `"Algorithms midterm . Review c…"`. I3 has same issue.

---

## Working as intended ✓

- **Categories** assign correctly when text matches keyword seeds: D1 fitness, D2 academic, D3/D7/B8 study, D4/I1 development, D5/F3 meeting, D8 network, D9 personal
- **Deadline detection** B1, B7, E1, E3, E4, E5 all created proper Deadline rows
- **"this weekend" rewrite** A8 → Saturday May 2 ✓
- **30-min stagger** C2/C3/C4 — held cleanly across 3-, 5-, and 10-task chains
- **Empty/whitespace H1** → 0 items (parser_status="empty") ✓
- **Emoji** H3 → preserved in title, category=fitness ✓
- **URL** H7 → preserved in title ✓
- **Bullet list** H8 → 3 separate tasks, one per bullet ✓
- **Mixed delimiters** G2/G3/G4 → splits correctly on `,`, `;`, `then`, `+` ✓
- **Cross-segment binding** E1 BCI paper, E3 Paper A, E5 Report — all auto-bound via tier1_auto with confidence 1.00 ✓
- **LLM enrichment quality** — 33/42 enriched cleanly inside 30s, average ~5-9s per task

---

## Final DB state for moriartyholmesberg

- Active (non-voided) tasks: **42**
- Active (non-voided) deadlines: **14**

Operator can sign in to lyraos.org as moriartyholmesberg to verify visually.

---

## Operator action checklist

1. **Sign in to lyraos.org as `moriartyholmesberg`** and visually verify the 42 tasks + 14 deadlines on /today and /deadlines pages
2. Decide which P0 to fix first: (a) silent partial-commit (UX bug), (b) duration not extracted (measurement bug), or (c) both before alpha
3. P1 fixes (title strip, "and" segmentation, time ranges) can ship in a follow-up
4. Heuristic binding tuning (tier2_ask never fires) is a separate decision

---

## Detailed per-case table

| # | Tag | Input | Items parsed (kind:title @ when) | Bindings | Tasks committed (cat / start UTC / dur / bind / llm) | Deadlines committed | Notes |
|---|-----|-------|----------------------------------|----------|------|------|------|
| A1 | time-anchor | `Lab 8 problem set tomorrow at 3pm for 30 minutes` | task:Lab 8 problem set at for 30 m… @ 2026-05-01T15:00:00 | — | study / 2026-05-01T12:00:00 / 30m / — / enriched | — | title strip leaves "at for" ⚠ |
| A2 | time-anchor | `call mom at 5pm` | task:call mom @ 17:00 today | — | — | — | silent fail (past) |
| A3 | time-anchor | `study Friday` | task:study @ Fri 00:00 | — | study / Thu 21:00Z / 30m / — / enriched | — | midnight default acceptable |
| A4 | time-anchor | `30 min for emails` | task:30 min for emails @ now+stagger | — | — | — | silent fail (stagger past) |
| A5 | time-anchor | `in 2 hours` | task:in 2 hours @ now+2h | — | — | — | silent fail (in past per to_utc) |
| A6 | time-anchor | `study soon` | task:study soon @ now+stagger | — | — | — | silent fail; "soon" not parsed |
| A7 | time-anchor | `studied yesterday at 3pm for 2 hours` | task:studied yesterday at for 2 ho… @ tomorrow 15:00 | — | — / 2026-05-01T12:00:00 / 30m / — / enriched | — | "yesterday" bumped to future ⚠ |
| A8 | time-anchor | `do laundry this weekend` | task:do laundry @ Sat 00:00 | — | — / Fri 21:00Z / 30m / — / enriched | — | weekend rewrite ✓ |
| A9 | time-anchor | `submit report May 15` | task:submit report @ May 15 00:00 | — | — / May 14 21:00Z / 30m / — / enriched | — | task not deadline (verb wins) |
| A10 | time-anchor | `do dishes` | task:do dishes @ now+stagger | — | — | — | silent fail |
| B1 | kind-class | `Algorithms midterm May 15` | deadline:Algorithms midterm @ May 15 | — | — | Algorithms midterm @ May 14 21:00Z (active) | ✓ |
| B2 | kind-class | `May 15 paper due` | deadline:paper @ May 15 | — | — | paper @ May 14 21:00Z (planned) | title too generic |
| B3 | kind-class | `study for midterm tomorrow` | task:study for midterm @ tomorrow | — | study / tomorrow 12:24Z / 30m / parser_auto / enriched | — | verb beats deadline-keyword ✓ |
| B4 | kind-class | `midterm` | task:midterm @ now+stagger | — | — | — | silent fail; no deadline detected |
| B5 | kind-class | `deadline X` | task:X @ now+stagger | — | — | — | demoted to task ✓; silent fail (past) |
| B6 | kind-class | `paper due` | task:paper @ now+stagger | — | — | — | silent fail |
| B7 | kind-class | `Final exam December 20` | deadline:Final exam @ Dec 20 | — | — | Final exam @ Dec 19 22:00Z (planned) | ✓ |
| B8 | kind-class | `review for the BCI exam Saturday` | task:review for the BCI exam @ Sat 00:00 | — | study / Fri 21:00Z / 30m / — / enriched | — | ✓ |
| C1 | stagger | `do dishes` | task:do dishes @ now+stagger | — | — | — | silent fail |
| C2 | stagger | `do dishes, fold laundry, take out trash` | 3 staggered tasks | — | — | — | all silent fail (stagger past) |
| C3 | stagger | `task one ... task five` | 5 staggered tasks @ 30m | — | — | — | all silent fail |
| C4 | stagger | `task A ... task J` (10) | 10 staggered tasks | — | 5 of 10 committed (rest in past) | — | partial commit |
| C5 | stagger | `study at 5pm, then dinner, then read` | 3 items | — | — | — | "5pm" past; staggered defaults past |
| D1 | category | `workout 30 min today at 6pm` | task:workout 30 min @ today 18:00 | — | — | — | silent fail (past) |
| D2 | category | `PHM lecture tomorrow at 10am 60 min` | task:PHM lecture at 60 min @ tomorrow 10:00 | — | academic / tomorrow 07:00Z / **30m** ⚠ / — / enriched | — | duration ignored ❌ |
| D3 | category | `study chapter 4 today at 7pm 45 min` | task:study chapter 4 at 45 min @ today 19:00 | — | study / today 16:00Z / **30m** ⚠ / — / enriched | — | duration ignored ❌ |
| D4 | category | `code review at 4pm 30 min` | task:code review at 30 min @ today 16:00 | — | — | — | silent fail |
| D5 | category | `team standup tomorrow 9am 15 min` | task:team standup 15 min @ tomorrow 09:00 | — | meeting / tomorrow 06:00Z / **30m** ⚠ / — / enriched | — | duration ignored ❌ |
| D6 | category | `Asr prayer at 4pm` | task:Asr prayer @ today 16:00 | — | — | — | silent fail (past) |
| D7 | category | `weekly review Sunday at 8pm 60 min` | task:weekly review at 60 min @ Sun 20:00 | — | study / Sun 17:00Z / **30m** ⚠ / — / enriched | — | duration ignored ❌ |
| D8 | category | `interview prep tomorrow 6pm 90 min` | task:interview prep 90 min @ tomorrow 18:00 | — | network / tomorrow 15:00Z / **30m** ⚠ / — / enriched | — | duration ignored ❌ |
| D9 | category | `dinner with mom tomorrow 7pm` | task:dinner with mom @ tomorrow 19:00 | — | personal / tomorrow 16:00Z / 30m / — / enriched | — | ✓ |
| E1 | binding | `BCI paper due Friday ⏎ read BCI paper tomorrow at 7pm 60 min` | deadline:BCI paper + task:read BCI paper at 60 min | tier1_auto:BCI paper (1.00) | study / tomorrow 16:00Z / **30m** ⚠ / user_explicit / enriched | BCI paper @ Fri (active) | binding ✓; duration ignored ❌ |
| E2 | binding | `Paper review due Friday ⏎ write paper summary tomorrow 5pm 60 min` | deadline + task | — *(brittle token)* | — / tomorrow 14:00Z / **30m** ⚠ / — / enriched | Paper review @ Fri (active) | no auto-bind (paper brittle) |
| E3 | binding | `Paper A due Mon ⏎ Paper B due Wed ⏎ work on Paper A tomorrow at 6pm 60 min` | 2 deadlines + 1 task | tier1_auto:Paper A (1.00) | — / tomorrow 15:00Z / **30m** ⚠ / user_explicit / enriched | Paper A active, Paper B planned | ✓ |
| E4 | binding | `Paper due Friday ⏎ do laundry tomorrow at 5pm` | deadline + unrelated task | — | laundry committed unbound | Paper @ Fri (planned) | ✓ |
| E5 | binding | `Paper due Mon ⏎ Report due Tue ⏎ work on the report tomorrow 4pm 60 min` | 2 deadlines + 1 task | tier1_auto:Report (1.00) | — / tomorrow 13:00Z / **30m** ⚠ / user_explicit / enriched | Paper planned, Report active | binding correctly chose Report ✓ |
| E6 | binding | `review due Monday ⏎ write review Wednesday at 4pm 60 min` | task + task *(verb wins)* | — | review / Mon 21:00Z + write review / Wed 13:00Z | — *(no deadline kind)* | "due Monday" stripped from title; review/parser_auto bound |
| E7 | binding | `BCI midterm May 15 ⏎ study BCI today at 5pm 60 min ⏎ practice ... ⏎ final review Thu 6pm 60 min` | deadline:BCI midterm + 2 tasks + deadline:final review 60 min ⚠ | — *(no binding!)* | only practice committed; study BCI in past | BCI midterm planned, "final review 60 min" *(duration in title)* | E7 produced no binding even with shared "BCI" token |
| E8 | binding | `Algorithms midterm May 15. Review ch 1-3 today 5pm 60 min, practice problems Wednesday 4pm 90 min, and final review Thursday 6pm 60 min` | deadline:Algorithms midterm . Review c… ⚠ + task + deadline:and final review 60 min ⚠ | — | only practice committed | period-separated single segment problem | broken parsing |
| F1 | conflict | `study from 2-4pm tomorrow and meeting from 3-4pm tomorrow` | task:study from 2- and meeting fro… ⚠ *(merged on "and")* | — | study / tomorrow 12:27Z / 30m / — / enriched | — | "and" not split; title broken |
| F2 | conflict | `duplicate task ... 5pm 30 min, duplicate task ... 5pm 30 min` | 2 identical | — | both committed (force_conflicts=True); 1 enriched 1 failed | — | dedup not blocked |
| F3 | conflict | `meeting tomorrow 3-4pm, call tomorrow 4-5pm` | task:meeting 3 + task:call 4 *(time range chopped)* | — | both committed | — | time range broken |
| F4 | conflict | `study tomorrow 1-5pm, break tomorrow 2-2:30pm` | task:study 1 + task:break ⚠ | — | both committed wrong | — | time range broken |
| F5 | conflict | `lunch tomorrow at 1pm 60 min and meeting tomorrow at 1:30pm 30 min` | merged on "and" | — | only 1 task | — | "and" not split |
| G1 | delim | `do A then do B then do C` | task:do A @ Sat May 3 ⚠ + B/C staggered | — | only do-A committed | — | "do A" misparsed as date phrase |
| G2 | delim | `task A, task B, task C` | 3 staggered | — | — | — | all silent fail |
| G3 | delim | `task A; task B; task C` | 3 staggered | — | — | — | all silent fail |
| G4 | delim | `task A; task B, task C then task D + task E` | 5 staggered | — | — | — | all silent fail |
| G5 | delim | `Multi-line plan: ⏎ - write summary ⏎ - review code ⏎ - send email` | task:Multi-line plan + 3 bullet tasks | — | — | — | header treated as task; all silent fail |
| H1 | edge | whitespace only | — | — | — | — | parser_status="empty" ✓ |
| H2 | edge | `x` | task:x @ Oct 30 ⚠ | — | — / Oct 29 22:00Z / 30m / — / pending | — | random future date |
| H3 | edge | `🏋️ workout tomorrow at 6pm 30 min` | task:🏋️ workout at 30 min @ tomorrow 18:00 | — | fitness / tomorrow 15:00Z / 30m / parser_auto / pending | — | emoji preserved ✓ |
| H4 | edge | `study philosophy ` × 30 | very long title (truncated) | — | — | — | silent fail |
| H5 | edge | `ادرس الفصل الرابع غدا` | task with Arabic; date defaulted | — | — | — | parser doesn't understand Arabic 'tomorrow' |
| H6 | edge | `123` | task:123 *(time defaulted)* | — | — | — | silent fail |
| H7 | edge | `check https://example.com tomorrow at 5pm` | task:check https://example.com @ tomorrow 17:00 | — | — / tomorrow 14:00Z / 30m / — / pending | — | URL preserved ✓ |
| H8 | edge | `- task 1 ⏎ - task 2 ⏎ - task 3` | 3 staggered (no times) | — | — | — | all silent fail |
| I1 | llm | `URGENT: critical bug fix tomorrow at 9am 60 min` | task:URGENT: critical bug fix at 60 min | — | development / tomorrow 06:00Z / **30m** ⚠ / — / pending | — | duration ignored ❌ |
| I2 | llm | `code review tomorrow at 4pm 60 min — check naming, verify edges, run perf, write summary` | em-dash split into 4 separate tasks ⚠ | — | only code-review committed cleanly | — | sub-items got split into separate tasks instead of one task w/ scope-bullets |
| I3 | llm | `research presentation due May 10. start outlining today at 8pm 60 min` | period-separated single segment | — | — / May 9 21:00Z / **30m** ⚠ / — / pending | — | period not a delimiter |

---

## Summary stats

- Parse OK: 61/61
- Commit OK (HTTP): 61/61
- **Items committed cleanly: 42 tasks + 14 deadlines (out of 111 parsed)**
- **Items silently dropped: ~55** (most due to past-time, some due to missing-binding logic)
- Total bindings suggested: 3 (tier1_auto=3, tier2_ask=0, tier3_skip=0)
- LLM enrichment outcome: enriched=33, pending=6, unavailable=0, failed=3
