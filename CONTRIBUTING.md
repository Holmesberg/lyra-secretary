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

## Diagrams

Regenerate PNGs after editing [`docs/diagrams/generate_diagrams.py`](docs/diagrams/generate_diagrams.py):

```bash
pip install matplotlib
python docs/diagrams/generate_diagrams.py
```
