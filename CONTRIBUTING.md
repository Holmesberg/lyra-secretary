# Contributing

Thanks for your interest in [Lyra Secretary](https://github.com/Holmesberg/lyra-secretary).

## Development setup

1. Copy [`.env.example`](.env.example) to `.env` and fill in keys for local runs.
2. From the `backend/` directory, install dependencies and run tests:

   ```bash
   pip install -r requirements.txt
   pip install pytest
   set PYTHONPATH=.    # Windows PowerShell: $env:PYTHONPATH="."
   pytest tests/
   ```

   CI uses **Python 3.11** (see [`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

3. For Docker-based development, see the commands in [`CLAUDE.md`](CLAUDE.md) and networking details in [`docs/architecture.md §3`](docs/architecture.md).

## Pull requests

- Keep changes focused; match existing naming and structure in touched files.
- Update user-facing docs ([`README.md`](README.md) or [`openclaw/skills/lyra-secretary/SKILL.md`](openclaw/skills/lyra-secretary/SKILL.md)) when behavior or endpoints change.

## Middleware ordering rule

**Response-modifying middleware (CORS, security headers, compression, request ID
injection, logging) MUST be added LAST in `backend/app/main.py` so it ends up as
the outermost wrapper.**

Starlette applies middleware in REVERSE of `add_middleware` order — the
last-added middleware becomes the outermost. This matters because middleware
that short-circuits without calling `call_next` (auth rejection, rate limit,
error handling) returns responses directly that bypass any INNER middleware.

Example of the bug class (**LYR-100**, fixed 2026-04-11):

- `CORSMiddleware` was added before `UserScopeMiddleware`.
- `UserScope` ended up OUTER, `CORS` ended up INNER.
- When `UserScope` rejected an expired JWT with `JSONResponse(401)`, the
  response never entered the CORS layer.
- Browser saw a bare 401 with no `Access-Control-Allow-Origin` header, blocked
  the response, and reported it as a CORS error.
- Latent for 48 hours — only triggered once a real expired token forced the
  short-circuit path. Any short-circuiting middleware that ever ships with
  response-modifying middleware inner of it will eventually hit this.

Correct order (outer to inner, which means **LAST-added** to **FIRST-added** in
code):

1. `CORSMiddleware` (last add → outermost) — wraps every response, including
   short-circuited error responses.
2. `SecurityHeadersMiddleware` (if added later).
3. `RequestIDMiddleware` (if added later).
4. `UserScopeMiddleware` (first add → innermost) — may short-circuit on auth
   failure; that's fine, the response still flows through the outer wrappers.

PR review checklist for any new middleware:

- **Does it short-circuit** (return `JSONResponse`/`Response` directly without
  `call_next`)? If yes, it MUST be added before any response-modifying
  middleware.
- **Does it modify responses** (add headers, transform body)? If yes, it MUST
  be added after any short-circuiting middleware.
- When in doubt, response-modifying goes LAST.

## Multi-user isolation testing

Any PR that touches a **write path** (task creation, state transitions, stopwatch
start/stop/pause/resume, void, reschedule, soft-delete) **must** include or
update a test in `tests/test_multiuser_isolation_adversarial.py` that proves the
write is scoped to the calling user.

The test pattern:
1. Create a resource as user A (high ID like 98 or 99 — never 1, to catch
   default-value leaks).
2. Attempt the write as user B with a different `X-User-Id` header.
3. Assert that user B gets 403 or 404 (never 200).
4. Assert that user A's resource is unchanged (use `_fresh_query_task()` to
   bypass SQLAlchemy's identity map cache).

PRs that modify only read paths, documentation, or frontend-only code are exempt.

## Frontend dev restart rule (WSL)

**Every Next.js dev-server restart in WSL MUST kill zombie `next-server` and
`next dev` processes BEFORE cleaning `.next`. Never run `rm -rf .next` on its
own.**

The correct sequence:

```bash
pkill -9 -f "next-server" 2>/dev/null
pkill -9 -f "next dev"    2>/dev/null
sleep 2                                 # let WSL release file locks
rm -rf frontend/.next
cd frontend && npm run dev
```

Example of the bug class (**recurring Apr 9-11 2026**):

- Operator hit a dev-server issue (HMR runtime error, stale bundle, port 3000
  zombie). Ran `rm -rf .next` to clean the cache.
- `rm -rf` failed with `Directory not empty` because a zombie `next-server`
  worker still held open file descriptors on `.next/cache/webpack/*.pack`.
- Operator ran `rm -rf .next` a second time — this time it partially succeeded,
  leaving a corrupted half-deleted cache.
- `npm run dev` on top of the corrupted cache produced a "works on my laptop
  but the old bug still appears in the browser" state that wasted ~30 min
  before we realised the bundle was stale.
- Root cause: WSL's 9P filesystem bridge is slower than native Linux at
  releasing file locks, so zombie node processes can hold `.next/*` open for
  seconds after the parent shell closes. Native Linux rarely hits this; macOS
  never hits it.

The `sleep 2` in the sequence above is load-bearing — without it, `rm -rf`
races the OS and fails intermittently. 2 seconds is empirically enough for
WSL2 + Node 20.

**Operator has the sequence wired as the `lyra-dev` shell alias.** Anyone else
working in WSL should either alias it the same way or paste the block above.
CI doesn't hit this because CI runs on native Linux, not WSL, so this rule is
**developer-workflow only** — do not add it to any CI step.

Diagnostic smell: if `rm -rf .next` ever prints `Directory not empty`, or if
Fast Refresh shows "had to perform a full reload due to a runtime error" more
than once per session, stop typing and run the full kill+clean+restart
sequence.

## Diagrams

Regenerate PNGs after editing [`docs/diagrams/generate_diagrams.py`](docs/diagrams/generate_diagrams.py):

```bash
pip install matplotlib
python docs/diagrams/generate_diagrams.py
```
