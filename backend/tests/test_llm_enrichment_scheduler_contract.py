import ast
from pathlib import Path

from app.workers.jobs import llm_enrichment


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_llm_enrichment_is_auxiliary_bounded_work():
    assert llm_enrichment._MAX_TASKS_PER_CYCLE == 1


def test_scheduler_runs_llm_enrichment_on_slow_auxiliary_cadence():
    scheduler_path = REPO_ROOT / "backend" / "app" / "workers" / "scheduler.py"
    tree = ast.parse(scheduler_path.read_text(encoding="utf-8"))

    for call in [node for node in ast.walk(tree) if isinstance(node, ast.Call)]:
        if not (
            isinstance(call.func, ast.Attribute)
            and call.func.attr == "add_job"
            and any(
                keyword.arg == "id"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value == "llm_enrichment"
                for keyword in call.keywords
            )
        ):
            continue

        trigger_keyword = next(
            keyword for keyword in call.keywords if keyword.arg == "trigger"
        )
        trigger_call = trigger_keyword.value
        assert isinstance(trigger_call, ast.Call)
        assert any(
            keyword.arg == "seconds"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value >= 60
            for keyword in trigger_call.keywords
        )
        assert any(
            keyword.arg == "max_instances"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value == 1
            for keyword in call.keywords
        )
        return

    raise AssertionError("llm_enrichment scheduler job was not registered")
