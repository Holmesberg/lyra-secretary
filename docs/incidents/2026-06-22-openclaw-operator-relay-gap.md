# OpenClaw Operator Relay Gap - 2026-06-22

Status: repaired and verified.
Runtime owner: operator infrastructure.
May authorize code: false.

## Symptom

LyraOS public runtime was unreachable through `lyraos.org`, and operator
warnings were no longer reaching the OpenClaw Telegram account.

## Findings

- Public runtime was restored by restarting backend, frontend, and Cloudflare
  tunnel paths.
- Lyra was still queueing operator alerts in Redis:
  `notifications:pending:1`.
- The OpenClaw Telegram bot itself was reachable.
- The missing link was the queue relay: alerts accumulated in Redis but no live
  OpenClaw process drained them into Telegram.
- The OpenClaw skill contract also still referenced the legacy
  `/v1/notifications/pending` path instead of
  `/v1/notifications/openclaw/pending`.

## Repair

- Added `scripts/openclaw_operator_relay.mjs`.
- Added `scripts/start_openclaw_operator_relay.ps1`.
- Wired the relay into:
  - `scripts/start_public_after_reboot.ps1`;
  - `scripts/watch_public_runtime.ps1`.
- Updated `openclaw/skills/lyra-secretary/SKILL.md` to use the explicit
  OpenClaw notification endpoint.
- Updated `docs/notification_coverage.md` with the current endpoint and relay
  contract.

## Verification

- `node scripts/verify_runtime_topology.mjs --topology public --skip-browser`
  returned `ok: true`.
- `scripts/watch_public_runtime.ps1 -NoRepair` passed:
  - local frontend;
  - local API;
  - public frontend;
  - public API;
  - public static asset graph;
  - OpenClaw operator relay restart.
- Redis backlog drained from `23` to `0`.
- A synthetic alert from `app.services.operator_notifier.notify_operator`
  queued successfully and was relayed by OpenClaw:
  `source=codex.openclaw-relay.verify`.

## Follow-Up Check - 2026-06-22 Evening

After another public runtime outage:

- `scripts/start_public_after_reboot.ps1` rebuilt public frontend build
  `add822d`, restarted backend/Redis, restarted the Cloudflare tunnel, and
  verified public topology.
- `scripts/start_openclaw_operator_relay.ps1 -StatusOnly` showed the relay
  alive inside `openclaw-openclaw-gateway-1`:
  `node /tmp/lyra_openclaw_operator_relay.mjs`.
- `notifications:pending:1` had length `0`.
- Relay log showed successful sends after restart, including
  `source=calendar.sync` at `2026-06-22T16:08:59Z`.

Interpretation:

```text
At this checkpoint, Lyra queue -> OpenClaw relay was working. If Telegram did
not visibly show the alert, next triage should inspect Telegram delivery/chat
visibility rather than treating Lyra notification production as failed.
```

## Boundary

The relay is observation-only. It must not mutate tasks, sessions, provider
state, notification lifecycle, exposure state, user activity, or user metrics.
