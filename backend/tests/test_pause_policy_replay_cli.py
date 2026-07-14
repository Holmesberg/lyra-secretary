from __future__ import annotations

import json
import subprocess
import sys


def test_founder_replay_cli_reads_stdin_and_emits_aggregate_only():
    completed = subprocess.run(
        [sys.executable, "scripts/run_founder_pause_replay.py"],
        input=json.dumps({"tasks": [], "stopwatch_sessions": [], "pause_events": []}),
        text=True,
        capture_output=True,
        check=True,
    )

    result = json.loads(completed.stdout)
    assert result["status"] == "inconclusive"
    assert result["holdout_evaluated"] is False
    assert "tasks" not in result
    assert "stopwatch_sessions" not in result
