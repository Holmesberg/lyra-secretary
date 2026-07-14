"""Provider-neutral characterization of the operator signature aggregate."""

from datetime import datetime, timedelta
from uuid import uuid4

from app.db.models import PauseEvent, StopwatchSession, Task, TaskSource, TaskState
from app.services.behavioral_signature_aggregate import (
    analyze_behavioral_signature_aggregate,
)


def _executed_task(
    user_id: int,
    *,
    title: str,
    category: str,
    started_at: datetime,
    ended_at: datetime,
) -> Task:
    return Task(
        task_id=str(uuid4()),
        user_id=user_id,
        title=title,
        category=category,
        planned_start_utc=started_at,
        planned_end_utc=ended_at,
        planned_duration_minutes=max(
            1, int((ended_at - started_at).total_seconds() / 60)
        ),
        executed_duration_minutes=max(
            1, int((ended_at - started_at).total_seconds() / 60)
        ),
        executed_start_utc=started_at,
        executed_end_utc=ended_at,
        state=TaskState.EXECUTED,
        source=TaskSource.WEB,
        created_at=started_at - timedelta(hours=1),
    )


def test_signature_aggregates_pause_distribution_and_recovery(db):
    user_id = 98102
    now = datetime.utcnow()
    task = _executed_task(
        user_id,
        title="study session",
        category="study",
        started_at=now - timedelta(hours=2),
        ended_at=now - timedelta(minutes=45),
    )
    db.add(task)
    session = StopwatchSession(
        session_id=str(uuid4()),
        task_id=task.task_id,
        user_id=user_id,
        start_time_utc=task.executed_start_utc,
        end_time_utc=task.executed_end_utc,
    )
    db.add(session)
    for reason, count in (
        ("distraction", 3),
        ("intentional_break", 2),
        ("task_switch", 1),
    ):
        for index in range(count):
            paused_at = now - timedelta(minutes=90 - index * 5)
            db.add(
                PauseEvent(
                    pause_event_id=str(uuid4()),
                    session_id=session.session_id,
                    user_id=user_id,
                    paused_at_utc=paused_at,
                    resumed_at_utc=paused_at + timedelta(minutes=2),
                    duration_minutes=2.0,
                    pause_reason=reason,
                    pause_initiator="self",
                )
            )
    db.commit()

    result = analyze_behavioral_signature_aggregate(
        db, user_id, {"window_days": 14}
    )

    assert result["n_sessions"] == 1
    assert result["n_pause_events"] == 6
    distribution = result["pause_distribution"]["by_reason_overall"]
    assert distribution["distraction"] == 0.5
    assert distribution["intentional_break"] == round(2 / 6, 3)
    assert "task_switch" in distribution
    recovery = result["recovery_latency_by_reason"]
    assert recovery["distraction"]["n"] == 3
    assert recovery["distraction"]["confidence"] == "cold_start"


def test_signature_declares_covered_and_uncovered_evidence(db):
    result = analyze_behavioral_signature_aggregate(
        db, 98111, {"window_days": 7}
    )

    coverage = result["coverage"]
    assert "covered_signal_categories" in coverage
    assert "NOT_covered_dont_speculate_about_these" in coverage
    assert "hallucination_rule" in coverage
    assert "answering_rule" in coverage
    assert "n_by_covered_signal" in coverage
    not_covered = " ".join(
        coverage["NOT_covered_dont_speculate_about_these"]
    ).lower()
    assert "onboarding" in not_covered
    assert "modal dwell" in not_covered or "modal_dwell" in not_covered
    covered = " ".join(coverage["covered_signal_categories"]).lower()
    assert "valence" in covered
    assert "disagreement" in covered
    assert "post-pause" in covered
    assert "valence preconditions" in covered


def test_signature_counts_post_pause_category_transition(db):
    user_id = 98110
    now = datetime.utcnow()
    first = _executed_task(
        user_id,
        title="first",
        category="development",
        started_at=now - timedelta(hours=2),
        ended_at=now - timedelta(hours=1, minutes=30),
    )
    second = _executed_task(
        user_id,
        title="second",
        category="study",
        started_at=now - timedelta(hours=1),
        ended_at=now - timedelta(minutes=15),
    )
    db.add_all([first, second])
    first_session = StopwatchSession(
        session_id=str(uuid4()),
        task_id=first.task_id,
        user_id=user_id,
        start_time_utc=first.executed_start_utc,
        end_time_utc=first.executed_end_utc,
    )
    second_session = StopwatchSession(
        session_id=str(uuid4()),
        task_id=second.task_id,
        user_id=user_id,
        start_time_utc=second.executed_start_utc,
        end_time_utc=second.executed_end_utc,
    )
    db.add_all([first_session, second_session])
    db.add(
        PauseEvent(
            pause_event_id=str(uuid4()),
            session_id=first_session.session_id,
            user_id=user_id,
            paused_at_utc=now - timedelta(hours=1, minutes=45),
            resumed_at_utc=now - timedelta(hours=1, minutes=40),
            duration_minutes=5.0,
            pause_reason="distraction",
            pause_initiator="self",
        )
    )
    db.commit()

    result = analyze_behavioral_signature_aggregate(
        db, user_id, {"window_days": 7}
    )

    transitions = [
        item
        for item in result["post_pause_transitions"]
        if item["pause_reason"] == "distraction"
        and item["next_category"] == "study"
    ]
    assert len(transitions) == 1
    assert transitions[0]["count"] == 1
    lift = [
        item
        for item in result["post_pause_transitions_lift_vs_baseline"]
        if item["pause_reason"] == "distraction"
        and item["next_category"] == "study"
    ]
    assert len(lift) == 1
    assert lift[0]["count"] == 1
    assert lift[0]["baseline_category_frequency"] > 0
    assert result["post_pause_category_jump"]["distraction"]["category_jump"] == 1
