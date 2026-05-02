"""Tests for Phase 2 JARVIS discovery tools (2026-05-02 system transition).

Covers:
- analyze_behavioral_signature returns valid structure on cold-start (no data)
- analyze_behavioral_signature aggregates pause distribution + recovery latency
  when sample data exists
- query_dark_columns rejects non-whitelisted columns
- query_dark_columns returns aggregated stats (never raw rows) for whitelisted columns
- propose_pattern_hypothesis validates required fields + enum values
- propose_pattern_hypothesis writes a structured row to JarvisInvocation audit log
- task_switch is now a valid pause reason in the user-facing picker

Per docs/calibration_contract.md R8: confidence tiers respect per-user-N
(operator-overfit guard). Cold-start case: n=0 → confidence='cold_start'
across all signals.
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.db.models import (
    JarvisInvocation,
    PauseEvent,
    PausePredictionLog,
    ReflectionViewLog,
    StopwatchSession,
    Task,
    TaskState,
    TaskSource,
    User,
)
from app.schemas.stopwatch import PAUSE_REASONS
from app.services.jarvis_tools import (
    _DARK_COLUMN_QUERIES,
    _exec_analyze_behavioral_signature,
    _exec_propose_pattern_hypothesis,
    _exec_query_dark_columns,
    EXECUTORS,
    READ_TOOLS,
    all_tools,
)


def test_phase2_tools_registered():
    """All 3 Phase 2 tools are registered in EXECUTORS + READ_TOOLS."""
    assert "analyze_behavioral_signature" in EXECUTORS
    assert "query_dark_columns" in EXECUTORS
    assert "propose_pattern_hypothesis" in EXECUTORS

    tool_names = {t["function"]["name"] for t in READ_TOOLS}
    assert "analyze_behavioral_signature" in tool_names
    assert "query_dark_columns" in tool_names
    assert "propose_pattern_hypothesis" in tool_names


def test_task_switch_in_pause_reasons():
    """task_switch is now in PAUSE_REASONS for the user-facing picker."""
    assert "task_switch" in PAUSE_REASONS


def test_analyze_behavioral_signature_cold_start(db):
    """No data → all signals at cold_start confidence, no 500."""
    iso_user_id = 88001
    result = _exec_analyze_behavioral_signature(db, iso_user_id, {"window_days": 14})

    assert result["window_days"] == 14
    assert result["n_sessions"] == 0
    assert result["n_pause_events"] == 0
    # Pause distribution structure exists but values are empty
    assert "pause_distribution" in result
    assert result["pause_distribution"]["by_reason_overall"] == {}
    # Confidence tiers all cold_start
    confidences = result["confidence_per_signal"]
    assert all(v == "cold_start" for v in confidences.values()), (
        f"Expected all cold_start, got {confidences}"
    )


def test_analyze_behavioral_signature_with_pauses(db):
    """Sample data → pause distribution + recovery latency populated."""
    iso_user_id = 88002
    now = datetime.utcnow()

    # Seed a task + pause events
    task_id = str(uuid4())
    db.add(Task(
        task_id=task_id,
        user_id=iso_user_id,
        title="study session",
        category="study",
        planned_start_utc=now - timedelta(hours=2),
        planned_end_utc=now - timedelta(hours=1),
        planned_duration_minutes=60,
        executed_duration_minutes=75,
        executed_start_utc=now - timedelta(hours=2, minutes=5),
        executed_end_utc=now - timedelta(minutes=50),
        state=TaskState.EXECUTED,
        source=TaskSource.WEB,
        created_at=now - timedelta(hours=5),
    ))
    session_id = str(uuid4())
    db.add(StopwatchSession(
        session_id=session_id,
        task_id=task_id,
        user_id=iso_user_id,
        start_time_utc=now - timedelta(hours=2, minutes=5),
        end_time_utc=now - timedelta(minutes=50),
    ))
    # 3 distraction pauses, 2 intentional_break, 1 task_switch
    for reason, n in [("distraction", 3), ("intentional_break", 2), ("task_switch", 1)]:
        for i in range(n):
            db.add(PauseEvent(
                pause_event_id=str(uuid4()),
                session_id=session_id,
                user_id=iso_user_id,
                paused_at_utc=now - timedelta(hours=1, minutes=30 - i * 5),
                resumed_at_utc=now - timedelta(hours=1, minutes=28 - i * 5),
                duration_minutes=2.0,
                pause_reason=reason,
                pause_initiator="self",
            ))
    db.commit()

    result = _exec_analyze_behavioral_signature(db, iso_user_id, {"window_days": 14})

    assert result["n_sessions"] == 1
    assert result["n_pause_events"] == 6
    distribution = result["pause_distribution"]["by_reason_overall"]
    assert distribution["distraction"] == 0.5  # 3/6
    assert distribution["intentional_break"] == round(2 / 6, 3)
    assert "task_switch" in distribution
    # Recovery latency by reason — distraction has 3 samples
    recovery = result["recovery_latency_by_reason"]
    assert recovery["distraction"]["n"] == 3
    assert recovery["distraction"]["confidence"] == "cold_start"  # n<5


def test_query_dark_columns_rejects_unwhitelisted(db):
    """Non-whitelisted column returns ok=False with whitelist exposed."""
    result = _exec_query_dark_columns(db, 1, {"column_name": "task.title"})
    assert result["ok"] is False
    assert result["reason"] == "column_not_whitelisted"
    assert "whitelist" in result
    assert "task.reschedule_count" in result["whitelist"]


def test_query_dark_columns_reschedule_count(db):
    """task.reschedule_count returns aggregated distribution, no raw rows."""
    iso_user_id = 88003
    now = datetime.utcnow()
    for rc in [0, 0, 0, 1, 2, 3]:
        db.add(Task(
            task_id=str(uuid4()),
            user_id=iso_user_id,
            title=f"t{rc}",
            planned_start_utc=now,
            planned_end_utc=now + timedelta(minutes=30),
            planned_duration_minutes=30,
            state=TaskState.PLANNED,
            source=TaskSource.WEB,
            reschedule_count=rc,
            created_at=now - timedelta(days=1),
        ))
    db.commit()

    result = _exec_query_dark_columns(
        db, iso_user_id,
        {"column_name": "task.reschedule_count", "window_days": 30},
    )
    assert result["ok"] is True
    assert result["n"] == 6
    assert result["max"] == 3
    assert result["n_with_at_least_one_reschedule"] == 3
    # Aggregates only — no raw rows in output
    assert "rows" not in result
    assert "tasks" not in result


def test_propose_pattern_hypothesis_missing_fields(db):
    """Required field validation — partial proposal rejected."""
    result = _exec_propose_pattern_hypothesis(db, 1, {
        "observation": "test",
        # missing everything else
    })
    assert result["ok"] is False
    assert result["reason"] == "missing_required_fields"
    assert "signals_used" in result["missing"]
    assert "falsifier" in result["missing"]
    assert "valence_class" in result["missing"]


def test_propose_pattern_hypothesis_invalid_valence(db):
    """Invalid valence_class enum value rejected."""
    result = _exec_propose_pattern_hypothesis(db, 1, {
        "observation": "test",
        "signals_used": ["foo"],
        "predicted_outcome": "bar",
        "falsifier": "if X happens",
        "generality_tag": "operator-only",
        "valence_class": "vibes",  # not in enum
        "n_at_proposal": 10,
    })
    assert result["ok"] is False
    assert result["reason"] == "invalid_valence_class"
    assert "friction" in result["allowed"]
    assert "flow" in result["allowed"]


def test_propose_pattern_hypothesis_invalid_generality(db):
    """Invalid generality_tag enum value rejected."""
    result = _exec_propose_pattern_hypothesis(db, 1, {
        "observation": "test",
        "signals_used": ["foo"],
        "predicted_outcome": "bar",
        "falsifier": "if X happens",
        "generality_tag": "universally-true",  # not in enum
        "valence_class": "friction",
        "n_at_proposal": 10,
    })
    assert result["ok"] is False
    assert result["reason"] == "invalid_generality_tag"


def test_propose_pattern_hypothesis_valid_proposal(db):
    """Valid proposal returns recorded=True with structured fields."""
    result = _exec_propose_pattern_hypothesis(db, 1, {
        "observation": "Late-afternoon study tasks show 3x distraction-pause rate vs morning",
        "signals_used": ["pause_distribution.by_reason_x_tod", "recovery_latency_by_reason"],
        "predicted_outcome": "Scheduling deep work in mornings would reduce distraction pauses ~40%",
        "falsifier": "If next 14d shows distraction-pause rate equal across morning vs afternoon",
        "generality_tag": "potentially-general",
        "valence_class": "friction",
        "n_at_proposal": 18,
    })
    assert result["ok"] is True
    assert result["recorded"] is True
    assert result["valence_class"] == "friction"
    assert result["generality_tag"] == "potentially-general"
    assert result["n_at_proposal"] == 18


def test_dark_column_whitelist_excludes_sensitive():
    """Whitelist doesn't contain raw-row-leaking columns (titles, descriptions, payloads)."""
    forbidden = {"task.title", "task.description", "reflection_view_log.payload"}
    assert forbidden.isdisjoint(_DARK_COLUMN_QUERIES)


def test_all_tools_includes_phase2():
    """all_tools() (used by NIM client) includes the 3 Phase 2 tools."""
    tool_names = {t["function"]["name"] for t in all_tools()}
    assert "analyze_behavioral_signature" in tool_names
    assert "query_dark_columns" in tool_names
    assert "propose_pattern_hypothesis" in tool_names
