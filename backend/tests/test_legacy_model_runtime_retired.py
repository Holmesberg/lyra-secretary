"""Fail closed if the retired direct-model runtime is reintroduced."""
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_direct_model_provider_runtime_files_are_absent():
    removed_paths = (
        "backend/app/services/llm_parser.py",
        "backend/app/services/nvidia_nim_client.py",
        "backend/app/services/jarvis_tools.py",
        "backend/app/workers/jobs/llm_enrichment.py",
        "backend/tests/test_jarvis_phase2_discovery_tools.py",
        "scripts/llm_latency_bench.py",
    )
    assert not [path for path in removed_paths if (REPO_ROOT / path).exists()]


def test_runtime_configuration_has_no_retired_provider_wiring():
    checked_paths = (
        "backend/app/core/config.py",
        "backend/app/workers/scheduler.py",
        "docker-compose.yml",
        ".env.example",
    )
    forbidden = (
        "NVIDIA_NIM",
        "OLLAMA_",
        "OPENAI_API_KEY",
        "NOTION_API_KEY",
        "NOTION_DATABASE_ID",
        "llm_enrichment",
    )
    findings = []
    for relative_path in checked_paths:
        text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        for token in forbidden:
            if token in text:
                findings.append(f"{relative_path}: {token}")
    assert findings == []


def test_retired_provider_does_not_leave_false_model_activity_copy():
    chip = (
        REPO_ROOT / "frontend/components/llm-enrichment-chip.tsx"
    ).read_text(encoding="utf-8")
    assert "LyraOS is reading this" not in chip
    assert "Still learning from your patterns" not in chip
    assert 'task.llm_parse_status === "retired"' in chip


def test_historical_model_candidates_are_not_actionable():
    endpoint = (
        REPO_ROOT / "backend/app/api/v1/endpoints/tasks.py"
    ).read_text(encoding="utf-8")
    assert endpoint.count('task.llm_parse_status != "retired"') >= 2
    assert endpoint.count(
        "Historical model suggestions are retained for audit only"
    ) >= 2
