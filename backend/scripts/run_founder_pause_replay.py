"""Evaluate the frozen founder pause replay from an export supplied on stdin."""
from __future__ import annotations

import json
import sys

from app.services.pause_policy_replay_baselines import evaluate_founder_holdout


MAX_INPUT_BYTES = 100_000_000


def main() -> int:
    payload = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(payload) > MAX_INPUT_BYTES:
        raise ValueError("export exceeds the 100 MB replay envelope")
    exported = json.loads(payload)
    if not isinstance(exported, dict):
        raise ValueError("export payload must be an object")
    result = evaluate_founder_holdout(exported)
    sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
