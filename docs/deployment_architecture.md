# Deployment Architecture — lyraos.org

**Owner:** Operator (Ali)
**Shipped:** April 16, 2026 (P0 sprint ahead of April 18 trusted-user launch)
**Status:** Live. First external-domain deployment.

Security companion: `docs/prodblueprint_security.md` is the trusted-alpha
security blueprint for access control, audit logs, data isolation, provider
failure handling, and public-beta upgrade gates.

## Current stack

**Current runtime note (May 15, 2026; updated July 8, 2026):** the frontend is expected to run as a
production build served by `next start` via `scripts/restart_frontend_wsl.ps1`.
The hosted-public build artifact directory is `frontend/.next-public`, kept
separate from local development/build artifact directory `frontend/.next`.
Older diagram labels or checklist text mentioning `npm run dev` are historical
April notes and should not be used as current production guidance.

```
[ Trusted user (phone / laptop) ]
            │
            │ https://lyraos.org  /  https://api.lyraos.org
            ▼
┌──────────────────────────┐
│ Cloudflare edge (proxy)  │  TLS termination (Full-strict), DDoS, CDN
│  — tunnel ingress        │
└──────────────────────────┘
            │  QUIC tunnel (outbound from laptop)
            ▼
┌──────────────────────────┐
│ cloudflared (laptop)     │  routes hostnames → local services:
│  tunnel = lyra-prod      │    lyraos.org     → http://localhost:3000
│  uuid =                  │    api.lyraos.org → http://localhost:8000
│    f996af66-6f7c-4788-   │
│    bc56-29a17dd65da2     │
└──────────────────────────┘
            │                       │
            ▼                       ▼
┌──────────────────────┐   ┌──────────────────────┐
│ Next.js (frontend)   │   │ FastAPI (backend)    │
│ port 3000            │   │ port 8000 in Docker  │
│ production build     │   │ lyrasecretaryv01-    │
│ served by            │   │ backend-1            │
│ `next start`         │   │ + Redis, + workers   │
│                      │   │                      │
└──────────────────────┘   └──────────┬───────────┘
                                      │ postgres + ssl
                                      ▼
                           ┌──────────────────────┐
                           │ Supabase Postgres    │
                           │ eu-west-1 pooler     │
                           │ project              │
                           │  xrrboaxptttdzednaxwk│
                           │ free tier 500 MB     │
                           └──────────────────────┘
```

**Total spend:** $6.48/year (Cloudflare Registrar). Everything else is free-tier.

## Component responsibilities

| Layer | Host | Purpose |
|---|---|---|
| DNS + Proxy + SSL | Cloudflare (free) | Registrar (lyraos.org), CNAMEs to tunnel UUID, automatic HTTPS |
| Tunnel | `cloudflared` on operator's laptop | Zero-config ingress without opening any inbound port at home |
| Frontend | Next.js 15.5.15 | App shell, auth UI, task surfaces, reflection modal, toast stack |
| Backend | FastAPI + APScheduler in Docker | State machine, scoping, Notion sync, pause prediction, retention signals |
| Cache / queue | Redis in Docker | Active-stopwatch state, undo cache, idempotency, Notion retry queue |
| Primary DB | Supabase Postgres 17.6 (eu-west-1, pooler on :6543, sslmode=require) | Canonical user + task data |

Redis + SQLite fallback both still work — SQLite is kept as `.env.backup-sqlite-2026-04-16` for fast revert if Supabase misbehaves.

## How trusted users access

1. Share `https://lyraos.org` in chat.
2. They click "Sign in with Google" — NextAuth handles OAuth entirely on the lyraos.org side (frontend process). Google callback: `https://lyraos.org/api/auth/callback/google` (added to the Google Cloud Console alongside the existing localhost entry).
3. Signed in → `/today` loads from the production build served by `next start`.
4. Frontend talks to `api.lyraos.org` via the typed API wrappers in `frontend/lib/*.ts`. CORS uses an explicit origin allow-list rather than a single `FRONTEND_URL` value, so operator dev and public runtime can coexist:
   - `http://localhost:3000`
   - `http://127.0.0.1:3000`
   - `https://lyraos.org`

## Runtime Topology Integrity

Runtime topology is part of epistemic integrity. Browser verification is not
trusted until the frontend, auth origin, API origin, and backend CORS contract
agree on the same topology.

Canonical contract:

- `runtime_topology.json`

Self-report endpoints:

- frontend: `/api/topology`
- backend: `/v1/health/topology`

Every topology packet includes:

- `topology_class`
- `frontend_origin` or `api_origin`
- `compiled_api_origin` for the frontend
- `nextauth_url` for the frontend
- `cors_allowed_origins` for the backend
- `build_id`
- `runtime_stamp`
- `verified_topology`

Verifier:

```powershell
node scripts/verify_runtime_topology.mjs --topology public
node scripts/verify_runtime_topology.mjs --topology local
```

Use `--topology public` when `https://lyraos.org` is intentionally serving the
public bundle:

```text
frontend_origin = https://lyraos.org
api_origin = https://api.lyraos.org
nextauth_url = https://lyraos.org
```

Use `--topology local` only when `localhost:3000` is intentionally serving a
local bundle:

```text
frontend_origin = http://localhost:3000
api_origin = http://localhost:8000
nextauth_url = http://localhost:3000
```

If `localhost:3000` is currently serving a public-env bundle for the tunnel, the
local verifier must fail with `topology_class=mixed`. That is expected and is
the guard doing its job. Do not fix this by changing ports or weakening CORS.

Browser verification rule:

```text
topology verifier passes -> alt-account browser stress can be trusted
topology verifier fails -> screenshots, latency logs, and bug reports are
epistemically ambiguous
```

Public frontend authority:

```text
Cloudflare reaches the WSL `lyra-frontend` tmux process, not any stray Windows
`next start` process.
```

For `lyraos.org`, use:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/restart_frontend_wsl.ps1
node scripts/verify_runtime_topology.mjs --topology public
```

`scripts/restart_public_frontend.ps1` is not a separate restart authority. It
is kept only as a compatibility wrapper that warns and delegates to
`scripts/restart_frontend_wsl.ps1`; use `-DryRun` to verify delegation without
restarting the frontend.

Do not use a Windows port-3000 frontend to prove public health while the tunnel
is served from WSL. If both Windows and WSL have frontend processes, stop and
verify which process Cloudflare is actually reaching.

Public operator browser stress requires the operator account cookie:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_operator_readonly_browser_stress.ps1 -Topology public
```

The runner reads `LYRA_COOKIE_ALINASSERSABRY` from the current user
environment, runs public topology verification first, then verifies the main
operator account through the normal browser/session path. The route walk is
read-only: it captures desktop/mobile screenshots, latency budgets,
console/network failures, operator-route checks, forbidden-copy checks, and
before/after export counts so task, deadline, and session creation cannot pass
unnoticed.

## Laptop sleep / wake behavior

- The public runtime is guarded by `scripts/watch_public_runtime.ps1`.
- Windows Task Scheduler runs `LyraOS Public Runtime Watchdog` every 12 hours.
- The current-user Startup folder also runs `LyraOS Public Runtime Watchdog.lnk`
  at Windows logon, installed by
  `scripts/install_public_runtime_startup_shortcut.ps1`.
- The watchdog checks local frontend/API health, public frontend/API health,
  public topology, the public static asset graph referenced by served HTML, and
  repairs Cloudflare/local runtime when needed.
- `scripts/restart_cloudflared_wsl.ps1` pins Cloudflare Tunnel DNS resolvers so
  WSL DNS failures do not strand the connector.

**Fallback today:** if a trusted user hits "site down" while the operator's
laptop is asleep, wake/login should run the startup watchdog. If not, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\watch_public_runtime.ps1
```

## Database separation rationale

Supabase holds the data *off* the laptop so:
- Laptop reboot / crash doesn't lose research data.
- Migration to EC2 (post-Spring-School) swaps *compute* without touching *data*. The API goes down; the data is safe.
- Multiple compute instances (laptop + EC2 in transition) can read the same canonical DB.

## Emergency recovery

| Failure mode | Symptom | Fix |
|---|---|---|
| Tunnel down (cloudflared killed) | `https://lyraos.org` -> 1033 / no response | `powershell -ExecutionPolicy Bypass -File scripts/restart_cloudflared_wsl.ps1` |
| WSL DNS blocks tunnel startup | Tunnel log contains `Couldn't resolve SRV record` against `10.255.255.254:53` | Use `scripts/restart_cloudflared_wsl.ps1`; it runs cloudflared with explicit `1.1.1.1` and `8.8.8.8` DNS resolvers |
| Backend container down | `https://api.lyraos.org/v1/health` → 502 | `docker compose up -d backend` |
| CORS split-brain | Browser shows `Failed to fetch` from `/v1/users/me`, while `curl localhost:8000/` returns 200 | Verify `CORS_ALLOWED_ORIGINS` includes the browser origin and rerun preflight; see `archive/docs_history/runtime_incident_cors_split_brain_2026_05_12.md` |
| Mixed runtime topology | `/api/topology` returns `verified_topology=false`, e.g. `.org` serving localhost auth/API or localhost serving public auth/API | Stop browser verification. Restart the intended frontend env and rerun `node scripts/verify_runtime_topology.mjs --topology public` or `--topology local`. For `.org`, use `scripts/restart_frontend_wsl.ps1`; see `docs/incidents/2026-05-17-public-frontend-mixed-topology.md`. |
| Frontend process killed or incomplete `.next-public` artifact | `https://lyraos.org` → 502 while `https://api.lyraos.org/v1/health` stays 200 | From Windows repo root: `powershell -ExecutionPolicy Bypass -File scripts/restart_frontend_wsl.ps1` |
| Supabase outage | API returns 5xx; connection errors in backend log | Flip `.env` back to SQLite backup + restart backend. Supabase data preserved, new writes go to SQLite until resolved. Manual reconciliation needed after. |
| Domain issue (registrar lock, DNS break) | `lyraos.org` DNS fails | Cloudflare dashboard → Registrar + DNS tab. `oslyra.com` is the name-swap candidate if lyraos.org becomes unusable (see dogfood P2 entry). |
| `cert.pem` lost / revoked | `cloudflared` operations fail auth | `cloudflared tunnel login` on laptop, re-authenticate 24p0248@eng.asu.edu.eg |

## Monitoring basics

- **Tunnel health:** `wsl -e bash -lc "~/.local/bin/cloudflared tunnel info lyra-prod"` lists active connectors. A healthy deployment shows 4 edge connections.
- **Backend health:** `curl https://api.lyraos.org/v1/health` → `{"status":"ok"}`.
- **Supabase connection:** `docker exec lyrasecretaryv01-backend-1 python -c "from app.core.config import settings; import psycopg2; psycopg2.connect(settings.DATABASE_URL).close(); print('ok')"`.
- **Laptop uptime during trusted-user week:** operator keeps laptop awake + on charger during peak hours.

## Domain renewal

- `lyraos.org` renews **April 16, 2027** via Cloudflare Registrar (auto-renew on, payment method = prepaid virtual card on file).
- `oslyra.com` expires **November 10, 2026** — monitor for potential upgrade from .org to .com. See `docs/dogfood_findings_living.md` P2 entry.

## Future EC2 migration path

Trigger: after Spring School (April 29+), once trusted-user signal confirms retention mechanism works.

1. Provision EC2 t3.small (free tier eligible for first year).
2. Clone repo, `docker compose up -d`.
3. Point DNS CNAMEs at the EC2 tunnel instead of laptop tunnel (same Cloudflare Tunnel can have multiple origins).
4. Drain laptop tunnel after EC2 stable.

Supabase data is unchanged across the swap — same `DATABASE_URL`. Zero data migration.

## Morning Recovery Checklist (laptop-sleep wake)

The watchdog should run every 12 hours and at Windows logon. If public health is
unclear, run this first:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\watch_public_runtime.ps1
```

Services that survive sleep vs require repair:

| Service | Survives sleep? | Recovery |
|---------|----------------|----------|
| Docker (backend + Redis) | Usually yes (containers stay up) | `docker compose ps` -> restart if "Exited" |
| Cloudflared tunnel | Often no (foreground process can die) | Watchdog, or `powershell -ExecutionPolicy Bypass -File scripts/restart_cloudflared_wsl.ps1` |
| Next.js (frontend) | Sometimes no (tmux process may die; `.next-public` can be left incomplete if a public build is interrupted) | Watchdog, or `powershell -ExecutionPolicy Bypass -File scripts/restart_frontend_wsl.ps1` |
| APScheduler | Yes (restarts with backend) | Automatic — fires missed jobs on wake |
| Supabase connection pool | Yes (pool_pre_ping reconnects stale conns) | Automatic |
| Redis data | Yes (persistent volume) | Automatic |

**Quick recovery script (copy-paste):**
```bash
# 1. Docker
docker compose ps
docker compose restart  # if anything shows Exited

# 2. Tunnel
powershell -ExecutionPolicy Bypass -File scripts/restart_cloudflared_wsl.ps1
sleep 2 && curl -sf https://api.lyraos.org/v1/health || echo "TUNNEL DOWN"

# 3. Frontend
# Stops stale next/npm processes, removes .next-public, rebuilds public topology,
# verifies BUILD_ID and public /api/topology, then starts `start:public`
# inside WSL tmux session `lyra-frontend`.
powershell -ExecutionPolicy Bypass -File scripts/restart_frontend_wsl.ps1

# 4. Orphan check
# Runtime HTTP auth requires a valid bearer/JWT. Do not use X-User-Id outside
# tests. Use an authenticated browser session, an operator diagnostic endpoint,
# or backend logs until an operator service-token path exists.

# 5. Recent errors
docker logs lyrasecretaryv01-backend-1 --since 1h 2>&1 | grep -i error | tail -10
```

## References

- `agent bootstrap doc §Architecture` — layer overview, now pointing at this doc.
- `README.md §Deployment` — endpoint table.
- `docs/operator_interrogation_checklist.md §Production monitoring` — the Day N questions to ask about trusted-user health.
- `docs/dogfood_findings_living.md` — operational findings (laptop sleep, tunnel recovery, domain watch).
- `~/.cloudflared/config.yml` (not in repo — operator machine): tunnel ingress rules.
- `.env.backup-sqlite-2026-04-16` (not in repo): SQLite revert config.
- `frontend/.env.local.backup-localhost-2026-04-16` (not in repo): local-dev frontend config.
