# Lyra Dogfood Findings — Living Doc

**Owner:** Operator (Ali)
**Started:** April 9, 2026
**Last updated:** April 11, 2026 (mid-morning)
**Status:** Active dogfood, pre-alpha

This document is edited continuously as new findings emerge. Sections of this doc are referenced directly in fix-batch prompts to Claude Code. Items move from OPEN to FIXED with commit hash when shipped. FIXED items get pruned every ~2 weeks.

---

## P0 — must fix before alpha launch

### OPEN

- **Voided task still shows paused timer banner.** After voiding CO block via OpenClaw, frontend banner kept showing "PAUSED · CO block 65:09:22". Possible causes: (a) frontend doesn't refetch /v1/stopwatch/status after void, (b) get_status doesn't filter voided_at IS NOT NULL sessions, (c) Redis active-stopwatch key still references the voided task. Investigate all three. *Found Apr 11.*

- **OpenClaw void endpoint hardcodes or skips voided_reason.** Operator voided CO block via OpenClaw with `void CO block ghost task paused for 65:17:59`. Lyra confirmed without asking for reason. Either SKILL.md hardcodes a reason or backend isn't enforcing the enum on the OpenClaw code path. Audit both. Backend Pydantic should reject any void without a valid voided_reason on every endpoint, not just web UI. *Found Apr 11.*

- **Stale session recovery job missing.** CO block was paused for ~65 hours before manual void. stale_session_recovery.py was designed in audit but never built. Required: PAUSED >12h auto-abandon, EXECUTING >planned×5 auto-abandon, notify operator on auto-action. *Found Apr 11.*

- **Edit click vs multi-select checkbox conflict on PLANNED rows.** Phase 4 added click-row-to-edit and checkbox-for-multi-select-void on the same row. Operator hasn't browser-verified that clicking the checkbox doesn't also trigger the edit modal, or vice versa. Needs verification. *Found Apr 11, untested.*

### FIXED (recent — prune in 2 weeks)

- PLANNED edit affordance via prefilled modal (commit 8eb4ac7)
- PLANNED delete affordance with confirmation (commit afcf868)
- EXECUTING/PAUSED skip affordance (commit 1d85b84)
- Multi-select void replacing row trash icon (commit b54e130)
- LYR-095 get_status falls through to Redis recovery (commit 9b7756f)
- LYR-096 task_completion_percentage passthrough (commit b3f8f2e)
- Friendly 400 on InvalidStateTransitionError (commit 7881ba2)
- Interruption flow handles mixed paused + blocking conflicts (commit 705b9d0)
- LYR-100 CORS middleware ordering (commit 625bf87)
- LYR-091 Notion archived-page detection (commit 951160e)
- AppLayout 401 auto-signOut + always-rendered Sign Out button (commit 7c9f33e)
- Cross-tenant write leak structural fix (Phase 3.2)
- Cross-tenant read leak per-user Redis keys (Phase 3.3 P0-A)
- Pause/resume 500 from int/float type mismatch (Phase 3.3 P0-B)
- completion_pct accepted 500% validation (Phase 3.3 P0-C)

---

## P1 — fix during Phase 4.5, before alpha

### OPEN

- **Sort PLANNED tasks ascending (next-up first).** Currently descending. Operator confirmed asc. Trivial flip. *Apr 10.*

- **useCurrentTime hook missing.** New task modal default start time stale after page idle. "Today" date doesn't refresh past midnight without manual reload (mostly works via 10s polling but edge case exists). Bundles LYR-099 (defaultStart stale on modal reopen). *Apr 10 + Apr 11 audit.*

- **Frontend backend-unreachable graceful retry UI.** "Failed to fetch" raw error shown on transient backend issues (host sleep, WSL port forward stabilization). Should be friendly retry banner with auto-retry every 5s. *Apr 11.*

- **Tooltips on `4 → 2 +29min` row arrow.** Only operator knows what readiness/focus/delta arrow means. Add hover tooltip or inline label for new users. *Apr 10.*

- **LYR-097 is_future_task warning ignored.** Backend returns warning when starting timer for task >5min in future, frontend silently discards. *Apr 11 audit.*

- **LYR-098 micro_mirror and calibration_nudge ignored on stop.** Backend computes both, frontend never displays. Research signal lost. *Apr 11 audit.*

- **Pause reason picker missing on web UI.** Backend accepts pause_reason enum, frontend hardcodes undefined. *Apr 11 audit.*

- **Density and typography polish on Today view.** Half-page empty, text could be denser. Reference: Linear, Vercel, Cron, Raycast. *Apr 9.*

- **No swap-tasks affordance.** Existed in OpenClaw, missing in web UI. *Apr 9.*

- **Active timer banner display when paused very long.** Currently shows large hour count past 12h. May want different presentation. *Apr 11.*

---

## P2 — defer to v2 backlog or post-alpha

### OPEN

- **category_type field (estimable vs time_anchored).** Designed in audit, deferred to Phase 4. Required before H1 analysis runs. Prayer/sleep/meals contaminate bias_factor. *Apr 10.*

- **self_reflection → planning rename.** Cosmetic only, deferred. *Apr 10.*

- **planned_end_utc schema refactor.** Phase 4 prereq before calendar view. Schedule-X may not need it. *Apr 10.*

- **Aladhan prayer API integration.** Auto-schedule 5 PRAYER tasks daily, suggest pause on prayer time. v2 backlog. *Apr 10.*

- **VT-5 parent_session_id for split sessions.** Decision deferred to Paper 1 analysis phase. *Audit.*

- **Smart inactivity reminders.** Escalating notifications before stale session recovery fires. v2 backlog. *Apr 10.*

- **Mid-funnel retention loop.** Daily/weekly digest for sessions 5-30. v2 backlog. *Apr 10.*

- **LLM-powered task creation via OpenClaw bridge.** Reframed from "v2 defer indefinitely" to Phase 6 candidate after dogfood data. Operator overruled "scope creep" framing — it's the differentiator, low cost since OpenClaw infrastructure exists. *Apr 10.*

- **PWA support.** iOS/Android home-screen install, offline mode, basic push notifications. ~4 hours of work for 80% of "feels like a real app." Phase 7. *Apr 11.*

---

## Process / environment findings

- **WSL + Next.js dev server stale cache.** `rm -rf .next` doesn't help if a zombie `next dev` process is still running — the old process recreates the cache from in-memory state. Must `pkill -f "next dev"` first. Operator added `lyra-dev` shell alias that does kill + clean + restart in one command. Goes away on Vercel deploy. *Recurring Apr 9-11.*

- **Zombie port 3000 after dev server crashes.** Same fix as above — the `lyra-dev` alias handles it. *Recurring.*

- **Host sleep breaks WSL port forwarding intermittently.** Symptoms: "Failed to fetch" or net::ERR_FAILED on localhost:8000 from browser, while WSL curl to same endpoint succeeds. Workaround: docker restart backend, or wsl --shutdown + Docker Desktop restart in worst case. *Apr 11.*

- **Middleware ordering rule documented in CONTRIBUTING.md** (LYR-100 lesson): response-modifying middleware must be added LAST to end up outermost. Short-circuiting middleware (auth, rate limit) goes inner. *Apr 11.*

---

## How operator uses this doc

1. New finding emerges → operator drops a one-line entry under the appropriate priority section.
2. When ready to ship a fix batch, operator references the relevant section by name in a Claude Code prompt: "read OPEN P0 section of dogfood_findings_living.md and ship items 1-3."
3. Claude Code reports back with commit hashes per item.
4. Operator (or Claude in chat) moves items from OPEN to FIXED with hash + date.
5. FIXED items stay for ~2 weeks then get pruned to keep the doc readable.

P0 = blocks alpha launch
P1 = ships before alpha but doesn't block
P2 = post-alpha, v2, or research-phase work
