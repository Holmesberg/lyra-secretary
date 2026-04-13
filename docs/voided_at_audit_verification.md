# voided_at Audit Verification Checklist

**Date:** 2026-04-13
**Commits:** 5 (listed at bottom)
**Total bugs fixed:** 15 (14 original audit + 1 found by audit script)

---

## Contamination audit (run first, before any fixes feel complete)

Connect to the production SQLite database and run these queries. The goal is to measure how much damage the voided_at leaks caused in the operator's 9-day dataset (Apr 5 — Apr 13).

### Query 1: Voided tasks auto-SKIPPED by overdue job

```sql
SELECT count(*), task_id, title, state, voided_at, voided_reason
FROM task
WHERE voided_at IS NOT NULL
  AND state = 'SKIPPED'
ORDER BY voided_at DESC;
```

**What it detects:** The overdue_tasks job transitioned voided PLANNED tasks to SKIPPED. These rows have contaminated state — the task should have remained PLANNED (voided, frozen in time).

**Expected:** 0-3 rows. The overdue job runs every 30 min. If voided tasks typically had their window already passed, this could fire on each.

### Query 2: Voided tasks synced to Notion

```sql
SELECT count(*), task_id, title, notion_page_id, voided_at
FROM task
WHERE voided_at IS NOT NULL
  AND notion_page_id IS NOT NULL
ORDER BY voided_at DESC;
```

**What it detects:** notion_sync retried and succeeded on voided tasks, pushing contaminated data to Notion. These Notion pages may show stale/incorrect status.

**Expected:** Potentially all voided tasks if they had Notion pages before voiding. Not a data integrity issue in SQLite — just Notion pages that may need manual cleanup.

### Query 3: Stopwatch sessions on voided tasks

```sql
SELECT s.session_id, s.task_id, s.start_time_utc, s.end_time_utc, s.auto_closed,
       t.title, t.voided_at
FROM stopwatch_session s
JOIN task t ON s.task_id = t.task_id
WHERE t.voided_at IS NOT NULL
ORDER BY s.start_time_utc DESC;
```

**What it detects:** Sessions that were started, stopped, or auto-closed on voided tasks. The stale_session_recovery job may have auto-closed sessions that should have been left alone.

**Expected:** Small number. Most sessions would have been closed before the task was voided.

### Query 4: Voided tasks that received reminders (check Redis)

```bash
redis-cli keys "reminder_sent:*" | head -20
```

**Note:** Reminder keys have 2h TTL — they may have already expired. This is a best-effort check.

---

## Regression verification steps (run after all 5 commits are deployed)

### Background jobs (5 tests)

1. **Reminders:** Void a PLANNED task scheduled for 10 minutes from now. Wait 15 minutes. Verify no reminder notification fired via OpenClaw.

2. **Timer overflow:** Start a timer, let it overflow past planned end, void the task mid-session. Wait for next timer_overflow job tick (2 min). Verify no overflow notification fired.

3. **Overdue tasks:** Void a PLANNED task scheduled in the past. Wait for next overdue_tasks job tick (30 min). Verify the task state remains PLANNED (not coerced to SKIPPED).

4. **Stale session recovery:** Void a task while its session is PAUSED. Verify stale_session_recovery doesn't auto-close the voided session (check after 12h or by lowering STALE_THRESHOLD_HOURS temporarily).

5. **Notion sync:** Void a task that has a pending Notion sync (trigger a Notion failure first, then void). Verify notion_sync skips it on retry.

### Mutation endpoints (7 tests)

6. **mark-abandoned:** Attempt to mark-abandon a voided task via OpenClaw. Verify 400 error, no state change.

7. **swap:** Attempt to swap two tasks where one is voided. Verify 400 error.

8. **reschedule:** Attempt to reschedule a voided task via drag in /calendar. Verify 400 error, no time change.

9. **complete_task:** Attempt to complete a voided task via API. Verify 400 error.

10. **stopwatch start:** Attempt to start a timer on a voided task. Verify 400 error.

11. **stopwatch stop (mid-void):** Start a timer, void the task mid-session, attempt to stop. Expected behavior: self-heal fires in `_get_active`, orphan session is auto-closed, Redis cleared, 400 "No active stopwatch" returned. This is correct — the self-heal path handles this case.

12. **update-completion:** Attempt to update-completion on a voided task via the overrun check-in path. Verify 400 error.

### Query + Redis (2 tests)

13. **/tasks/last:** Void a task, then call GET /v1/tasks/last via OpenClaw. Verify the voided task is not returned (404).

14. **/table view:** Open /table with 'Show voided' off. Verify voided tasks are hidden. Toggle on. Verify they appear.

### Undo Redis scoping (1 test)

15. **Cross-user undo:** With two test users, user A creates a task. User B calls POST /v1/undo. Verify B gets "Nothing to undo" (400), not A's undo action.

### Audit script

16. **Run the automated check:**
    ```bash
    cd backend && bash scripts/check_voided_at.sh
    ```
    Should output: `PASS: All files querying Task.state also reference voided_at.`

---

## Day navigation bug status

Re-check the forward navigation from yesterday after the voided_at commits land. The prior three edits may have been masked by HMR cache.

**Diagnosis protocol:**
```bash
# Cold restart (HARD GATE)
cd frontend
pkill -f "next dev" || true
rm -rf .next
npm run dev &

# Wait for compilation, then test:
# 1. Navigate to yesterday via left arrow
# 2. Click right arrow — should navigate to today
# 3. Navigate to 2 days ago — right arrow should go to yesterday
# 4. On today view, right arrow should be disabled UNLESS tomorrow has PLANNED tasks
```

If still broken, check:
- `nextDayBlocked` logic: should only be true when `isToday && !tomorrowHasTasks`
- React Query key: must use `["next-day-check", nextDateStr]` not `["tasks", nextDateStr]`
- `navigateTo()` function: verify it pushes `?date=YYYY-MM-DD` correctly

---

## Contamination decision

Operator to review contamination counts from audit queries above, then decide:

- **Option A:** Backfill state to PLANNED for voided-then-auto-SKIPPED rows
  ```sql
  UPDATE task SET state = 'PLANNED'
  WHERE voided_at IS NOT NULL AND state = 'SKIPPED'
    AND initiation_status = 'abandoned';
  ```

- **Option B:** Flag rows via new `state_contaminated_by_bug` column, exclude from analytics

- **Option C:** Accept contamination in operator data, flag only `cohort_start` date in MANIFESTO

Claude should not make this decision. Operator makes it after seeing actual counts.

---

## Commits to review

| # | Hash | Description |
|---|------|-------------|
| 1 | `2af80f0` | fix: background jobs skip voided tasks (voided_at audit 1/4) |
| 2 | `2afd063` | fix: mutation endpoints reject voided tasks (voided_at audit 2/4) |
| 3 | `7823424` | fix: /tasks/last filters voided + undo cache per-user scoped (voided_at audit 3/4) |
| 4 | `05d3e0a` | fix: add voided_at audit script + fix skill_check leak (voided_at audit 4/4) |
| 5 | `b7ed224` | fix: conflict detector excludes voided tasks (ghost conflict bug) |

**Test coverage added:** 15 new regression tests across 3 test files:
- `tests/test_jobs_skip_voided_tasks.py` (5 tests)
- `tests/test_mutations_reject_voided.py` (7 tests)
- `tests/test_last_task_and_undo_scoping.py` (3 tests)

**Total test suite:** 94 tests, all passing.
