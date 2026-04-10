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

3. For Docker-based development, see [`DOCKER.md`](DOCKER.md).

## Pull requests

- Keep changes focused; match existing naming and structure in touched files.
- Update user-facing docs ([`README.md`](README.md), [`docs/README.md`](docs/README.md), or [`openclaw/skills/lyra-secretary/SKILL.md`](openclaw/skills/lyra-secretary/SKILL.md)) when behavior or endpoints change.

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

## Diagrams

Regenerate PNGs after editing [`docs/diagrams/generate_diagrams.py`](docs/diagrams/generate_diagrams.py):

```bash
pip install matplotlib
python docs/diagrams/generate_diagrams.py
```
