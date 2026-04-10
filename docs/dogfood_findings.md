# Dogfood findings — Phase 3.5

Operator self-dogfood log. Populated during the 48h pause before Phase 4.

## Session log

| # | date | task | readiness | focus | planned | executed | delta | notes |
|---|------|------|-----------|-------|---------|----------|-------|-------|
| 1 | 2026-04-08 | Phase 3.2 implementation | 4 | 3 | 120 | 185 | -65 | Cross-tenant leak discovery extended scope significantly |
| 2 | 2026-04-08 | Adversarial test suite | 3 | 4 | 60 | 90 | -30 | Cross-test contamination debugging took longer than expected |
| 3 | 2026-04-09 | Phase 3.3 P0 bug fixes | 4 | 4 | 90 | 110 | -20 | Redis key isolation was clean once identified |
| 4 | 2026-04-09 | Browser verification pass | 3 | 3 | 30 | 55 | -25 | Stale .next cache caused unrelated 500s during verification |
| 5 | 2026-04-09 | completion_pct hardening | 4 | 5 | 15 | 25 | -10 | HTML number input bypass required second iteration (text+inputMode) |

## P0 — blockers (must fix before Phase 4)

- **[FIXED] P0-A: Stopwatch Redis key leak** — all StopwatchManager methods used static `"user_primary"` key. User 2's timer was visible to user 1. Fix: `_user_key()` resolves from ContextVar.
- **[FIXED] P0-B: Pydantic int/float mismatch on pause/resume** — schema declared `int` for `paused_minutes` and `total_paused_minutes` but DB stores `float` after column widening. 500 on every resume.
- **[FIXED] P0-C: completion_pct accepts out-of-range values** — HTML `type="number"` min/max only constrains spinner arrows, not typed/pasted input. First fix (onChange clamp) was correct but masked by stale browser cache. Second fix switched to `type="text" inputMode="numeric"` with regex strip.

## P1 — friction (should fix in Phase 4)

- **Error messages were raw HTTP status codes** — `api.ts` threw `${res.status}: ${text}` without parsing the JSON body. Users saw "422: {\"detail\":{...}}" instead of a human message. Fixed: parse `detail.message` from JSON error bodies.
- **Sort order was ascending (oldest first)** — Today view showed the earliest task at top. Reversed to descending so the most recent/active task is always visible without scrolling.
- **Voided tasks still visible in Today view** — No client-side filter on `voided_at`. Added `.filter((t) => !t.voided_at)` in the sort pipeline.
- **No void affordance on terminal tasks** — Trash icon added to EXECUTED/SKIPPED rows for data-quality cleanup.
- **Stale `.next` webpack cache** — After rebuilding, dev server returned 500 on `/api/auth/session` with "Cannot find module './520.js'". Required `rm -rf .next` to fix. Consider adding `.next` cleanup to the dev startup script.

## P2 — nice-to-have (v2 backlog candidates)

- **Pause reason prompt** — currently only `pause_initiator` is captured. A quick reason selector ("interruption", "break", "context switch") would enrich the cascade analysis data.
- **Bulk void** — voiding test/duplicate tasks one by one is tedious. A multi-select + batch void would help during data cleanup.
- **Session timeline visualization** — a horizontal bar showing planned vs executed spans per session would make the delta visible at a glance, replacing the numeric-only display.

## Notes / observations

- The motivated underestimation pattern (H4) was clearly visible in sessions 1–2: scope expanded mid-session because "I'm already here, might as well." The planned duration was honest at planning time but the task definition drifted.
- Cross-test contamination in the adversarial suite was the hardest debugging problem. SQLAlchemy's identity map caches objects across queries within a session, so a test that reads a task through the fixture session may see stale state from a prior test. The fix (fresh `TestingSession()` for every verification query) is correct but non-obvious — this should be documented as a testing pattern.
- The Redis key namespace pattern (`stopwatch:active:{user_id}`) is the right isolation boundary but was never enforced by convention — it was just how one method happened to work, and other methods used a flat key. A `_user_key()` accessor that fails-loud on missing context is the durable fix.
- Browser cache was a real confounder during verification. Changes that were deployed and correct appeared broken because the browser served stale JS. Hard-refresh (`Ctrl+Shift+R`) should be part of the verification protocol.
