# Documentation

This folder holds **system design assets** for [Lyra Secretary](https://github.com/Holmesberg/lyra-secretary).

## Diagrams (`diagrams/`)

| File | Description |
|------|-------------|
| [`architecture.png`](diagrams/architecture.png) | End-to-end components, layers, and data flow (Telegram, OpenClaw, FastAPI, TaskManager, SQLite, Redis, APScheduler, Notion). |
| [`state-machine.png`](diagrams/state-machine.png) | Task states and valid transitions (`StateMachine` / `TaskManager`). |
| [`data-flow.png`](diagrams/data-flow.png) | Sequence: create task → stopwatch start → stop → Notion sync. |

PNGs are generated for a dark theme at ~2× resolution. To regenerate after changing layout or colors:

```bash
pip install matplotlib
python docs/diagrams/generate_diagrams.py
```

Source: [`diagrams/generate_diagrams.py`](diagrams/generate_diagrams.py) (comments cite the backend modules used for verification).

## Elsewhere in the repo

- **[`../README.md`](../README.md)** — setup, API overview, OpenClaw integration.
- **[`../DOCKER.md`](../DOCKER.md)** — Docker networking and compose notes.
- **[`../openclaw/skills/lyra-secretary/SKILL.md`](../openclaw/skills/lyra-secretary/SKILL.md)** — agent-facing endpoint reference.
