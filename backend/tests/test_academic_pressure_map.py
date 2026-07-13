import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.db.models import (
    Deadline,
    ExposureAckEvent,
    ExposureDecisionEvent,
    ExposureRenderEvent,
    SuppressionEvent,
    Task,
    TaskState,
    User,
)
from app.db.scoping import set_current_user_id
from app.main import app
from app.schemas.academic import AcademicMinuteEnvelope
from app.services.calendar_sync import ExternalEvent
from app.core.config import settings
from app.core.kill_switches import (
    provider_progress_signals_enabled,
    recovery_nudges_enabled,
)
from tests.conftest import auth_headers


client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _clean(db):
    set_current_user_id(None)
    db.rollback()
    db.query(ExposureAckEvent).delete()
    db.query(SuppressionEvent).delete()
    db.query(ExposureRenderEvent).delete()
    db.query(ExposureDecisionEvent).delete()
    db.query(Task).delete()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
    db.query(ExposureAckEvent).delete()
    db.query(SuppressionEvent).delete()
    db.query(ExposureRenderEvent).delete()
    db.query(ExposureDecisionEvent).delete()
    db.query(Task).delete()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()


def _user(db, email: str) -> User:
    user = User(
        email=email,
        google_id=None,
        timezone="Africa/Cairo",
        is_operator=False,
        notion_enabled=False,
        terms_accepted_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _deadline(
    db,
    user_id: int,
    title: str,
    *,
    days: int,
    external_source: str | None = None,
) -> Deadline:
    deadline = Deadline(
        user_id=user_id,
        title=title,
        due_at_utc=datetime.utcnow() + timedelta(days=days),
        category_hint="academic",
        state="planned",
        external_source=external_source,
        external_id=f"{external_source}:{title}" if external_source else None,
        imported_at=datetime.utcnow() if external_source else None,
    )
    db.add(deadline)
    db.commit()
    db.refresh(deadline)
    return deadline


def test_pressure_map_is_user_scoped_and_returns_ranges(db):
    alice = _user(db, "alice-pressure@example.com")
    bob = _user(db, "bob-pressure@example.com")
    _deadline(db, alice.user_id, "Algorithms Quiz 2", days=5, external_source="moodle_ics")
    bob_deadline = _deadline(db, bob.user_id, "Private Final Exam", days=5)

    resp = client.get(
        "/v1/academic/pressure-map?horizon_days=14",
        headers=auth_headers(alice.user_id),
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    titles = [item["title"] for item in data["items"]]
    assert titles == ["Algorithms Quiz 2"]
    item = data["items"][0]
    assert item["source"] == "external_obligation"
    assert item["source_class"] == "external"
    assert item["evidence_class"] == "external_obligation"
    assert item["provider_kind"] == "moodle"
    assert item["raw_authority_level"] == "provider_reachable"
    assert item["redaction_status"] == "metadata_only"
    assert "moodle_ics" not in " ".join(item["estimate"]["assumptions"])
    assert item["estimate"]["low_minutes"] < item["estimate"]["high_minutes"]
    assert item["estimate"]["low_minutes"] % 30 == 0
    assert item["estimate"]["high_minutes"] % 30 == 0
    assert item["trust_state"] == "verified_reachable"
    assert "coverage correctness" in " ".join(item["warnings"])
    assert "pressure_summary" in data
    assert data["surface_id"] == "academic.pressure_map"
    assert data["truth_class"] == "interpretation"
    assert data["signal_targets"] == ["planning_estimate", "deadline_behavior"]
    assert data["clean_profile"] is None
    assert data["fallback_mode"] == "suppress"
    assert data["authority_rung"] == "suggestion"
    assert data["mutation_permission"] == "explicit_user_confirmation_required"
    assert data["public_translator"] == "registered_surface_translator"
    assert data["surface_role"] == "diagnostic_planning_surface"
    assert "recovery_options" in data["allowed_authority"]
    assert "trust_states" in data["allowed_authority"]
    assert "automatic_task_creation" in data["denied_authority"]
    assert "automatic_calendar_mutation" in data["denied_authority"]
    assert "learning_or_mastery_inference" in data["denied_authority"]
    assert data["exposure_id"]
    assert "render_id" not in data
    assert data["render_snapshot"]
    assert data["coverage_questions"][0]["trust_state"] == "verified_reachable"
    assert "3-5 student confirmations" in data["coverage_questions"][0]["reason"]
    assert data["capacity_context"]["google_calendar_connected"] is False
    assert "not true free time" in data["capacity_context"]["caveat"]
    assert data["source_summary"]["external_obligation_count"] == 1
    assert data["source_summary"]["native_obligation_count"] == 0
    assert "moodle_deadlines" not in data["source_summary"]
    assert "native_deadlines" not in data["source_summary"]
    projection_ids = {
        item["obligation_id"]
        for item in data["demand_coverage_projection"]["obligations"]
    }
    assert projection_ids == {data["items"][0]["obligation_id"]}
    assert bob_deadline.deadline_id not in projection_ids

    decision = (
        db.query(ExposureDecisionEvent)
        .filter(ExposureDecisionEvent.exposure_id == data["exposure_id"])
        .one()
    )
    assert decision.decision_status == "reserved"
    assert decision.delivered_at is None
    assert decision.exposure_category == "scheduling_suggestion"
    assert (
        db.query(ExposureRenderEvent)
        .filter(ExposureRenderEvent.exposure_id == decision.exposure_id)
        .count()
        == 0
    )
    assert (
        db.query(ExposureAckEvent)
        .filter(ExposureAckEvent.exposure_id == decision.exposure_id)
        .count()
        == 0
    )

    ack_payload = {
        "surface_id": "academic.pressure_map",
        "client_event_id": f"academic.pressure_map:{decision.exposure_id}",
        "content_snapshot": data["render_snapshot"],
    }
    first_ack = client.post(
        f"/v1/exposures/{decision.exposure_id}/ack/render",
        headers=auth_headers(alice.user_id),
        json=ack_payload,
    )
    assert first_ack.status_code == 200, first_ack.text
    assert first_ack.json()["created"] is True
    second_ack = client.post(
        f"/v1/exposures/{decision.exposure_id}/ack/render",
        headers=auth_headers(alice.user_id),
        json=ack_payload,
    )
    assert second_ack.status_code == 200, second_ack.text
    assert second_ack.json()["created"] is False

    db.refresh(decision)
    render = (
        db.query(ExposureRenderEvent)
        .filter(ExposureRenderEvent.exposure_id == decision.exposure_id)
        .one()
    )
    ack = (
        db.query(ExposureAckEvent)
        .filter(ExposureAckEvent.exposure_id == decision.exposure_id)
        .one()
    )
    assert decision.user_id == alice.user_id
    assert decision.decision_status == "rendered"
    assert decision.delivered_at is not None
    assert render.surface == "academic.pressure_map"
    assert ack.user_id == alice.user_id
    assert "Algorithms Quiz 2" not in render.content_snapshot
    assert "Private Final Exam" not in render.content_snapshot
    assert "coverage correctness" not in render.content_snapshot
    snapshot = json.loads(render.content_snapshot)
    assert snapshot["schema_version"] == "academic_pressure_map_exposure_snapshot_v1"
    assert snapshot["surface_role"] == "diagnostic_planning_surface"
    assert snapshot["authority_rung"] == "suggestion"
    assert "automatic_task_creation" in snapshot["denied_authority"]
    assert snapshot["item_count"] == 1
    assert snapshot["coverage_question_count"] == 1
    assert snapshot["source_summary"]["external_obligation_count"] == 1
    assert snapshot["recovery_actions"]


def test_pressure_map_render_ack_rejects_cross_user(db):
    owner = _user(db, "pressure-owner@example.com")
    other = _user(db, "pressure-other@example.com")
    _deadline(db, owner.user_id, "Owner deadline", days=3)

    response = client.get(
        "/v1/academic/pressure-map?horizon_days=14",
        headers=auth_headers(owner.user_id),
    )
    assert response.status_code == 200, response.text
    data = response.json()

    denied = client.post(
        f"/v1/exposures/{data['exposure_id']}/ack/render",
        headers=auth_headers(other.user_id),
        json={
            "surface_id": "academic.pressure_map",
            "content_snapshot": data["render_snapshot"],
        },
    )
    assert denied.status_code == 404
    assert (
        db.query(ExposureRenderEvent)
        .filter(ExposureRenderEvent.exposure_id == data["exposure_id"])
        .count()
        == 0
    )
    assert (
        db.query(ExposureAckEvent)
        .filter(ExposureAckEvent.exposure_id == data["exposure_id"])
        .count()
        == 0
    )


def test_pressure_map_marks_overdue_without_inferring_completion(db):
    user = _user(db, "overdue-pressure@example.com")
    _deadline(db, user.user_id, "OS Lab", days=-1, external_source="moodle_ics")

    resp = client.get("/v1/academic/pressure-map", headers=auth_headers(user.user_id))

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["items"][0]["pressure_level"] == "overdue"
    assert "do not infer completion" in " ".join(data["items"][0]["warnings"])
    assert "No completion is inferred" in " ".join(data["warnings"])
    assert any(point["kind"] == "overdue" for point in data["compression_points"])
    assert any(option["action"] == "create_plan" for option in data["recovery_options"])
    assert db.query(Task).count() == 0


def test_pressure_map_includes_planned_task_load_but_not_deleted_or_executed(db):
    user = _user(db, "tasks-pressure@example.com")
    now = datetime.utcnow()
    db.add_all(
        [
            Task(
                user_id=user.user_id,
                title="planned block",
                category="study",
                planned_start_utc=now + timedelta(hours=2),
                planned_end_utc=now + timedelta(hours=3),
                planned_duration_minutes=60,
                state=TaskState.PLANNED,
            ),
            Task(
                user_id=user.user_id,
                title="done block",
                category="study",
                planned_start_utc=now + timedelta(hours=4),
                planned_end_utc=now + timedelta(hours=5),
                planned_duration_minutes=60,
                state=TaskState.EXECUTED,
            ),
        ]
    )
    db.commit()

    resp = client.get("/v1/academic/pressure-map", headers=auth_headers(user.user_id))

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["source_summary"]["planned_lyra_minutes"] == 60
    assert data["source_summary"]["study_task_count"] == 1
    assert data["source_summary"]["study_task_minutes"] == 60
    assert data["estimated_low_minutes"] == 60
    assert [item["title"] for item in data["items"]] == ["planned block"]
    assert data["items"][0]["source"] == "lyra_self_study_task"
    assert data["items"][0]["obligation_type"] == "self_study"
    assert "planned duration is visible intention" in " ".join(
        data["items"][0]["estimate"]["assumptions"]
    )


def test_pressure_map_unions_overlapping_calendar_busy_intervals(db, monkeypatch):
    user = _user(db, "overlapping-calendar-pressure@example.com")
    user.google_refresh_token = "fixture-token"
    db.commit()
    now = datetime.utcnow()
    monkeypatch.setattr(
        "app.services.academic_pressure.fetch_google_events",
        lambda _user_id, _start, _end: [
            ExternalEvent(
                id="calendar-a",
                title="Calendar A",
                start=(now + timedelta(hours=1)).isoformat(),
                end=(now + timedelta(hours=3)).isoformat(),
                calendar_id="primary",
            ),
            ExternalEvent(
                id="calendar-b",
                title="Calendar B",
                start=(now + timedelta(hours=2)).isoformat(),
                end=(now + timedelta(hours=4)).isoformat(),
                calendar_id="primary",
            ),
        ],
    )

    response = client.get(
        "/v1/academic/pressure-map?horizon_days=1",
        headers=auth_headers(user.user_id),
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["source_summary"]["google_calendar_connected"] is True
    assert data["source_summary"]["calendar_busy_minutes"] == 180
    assert data["capacity_context"]["known_busy_minutes"] == 180


def test_pressure_projection_keeps_unconfirmed_calendar_mirror_sources_separate(
    db,
    monkeypatch,
):
    user = _user(db, "calendar-mirror-pressure@example.com")
    user.google_refresh_token = "fixture-token"
    now = datetime.utcnow()
    start = now + timedelta(hours=1)
    end = now + timedelta(hours=3)
    task = Task(
        user_id=user.user_id,
        title="Shared systems workshop",
        category="study",
        planned_start_utc=start,
        planned_end_utc=end,
        planned_duration_minutes=120,
        state=TaskState.PLANNED,
    )
    db.add(task)
    db.commit()
    monkeypatch.setattr(
        "app.services.academic_pressure.fetch_google_events",
        lambda _user_id, _start, _end: [
            ExternalEvent(
                id="calendar-original",
                title=task.title,
                start=start.isoformat(),
                end=end.isoformat(),
                calendar_id="primary",
            ),
            ExternalEvent(
                id="calendar-duplicate",
                title=task.title,
                start=start.isoformat(),
                end=end.isoformat(),
                calendar_id="primary",
            ),
        ],
    )

    response = client.get(
        "/v1/academic/pressure-map?horizon_days=1",
        headers=auth_headers(user.user_id),
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["source_summary"]["calendar_busy_minutes"] == 120
    assert data["source_summary"]["planned_lyra_minutes"] == 120
    assert data["capacity_context"]["known_busy_minutes"] == 120
    assert data["capacity_context"]["planned_lyra_minutes"] == 120
    projection = data["demand_coverage_projection"]
    assert projection["obligation_count"] == 0
    assert projection["capacity_status"] == "unavailable_no_authority"
    assert projection["collision_state"] == "unknown"
    assert task.task_id not in json.dumps(projection)


def test_pressure_projection_counts_linked_tasks_as_union_coverage(db):
    user = _user(db, "linked-coverage-pressure@example.com")
    deadline = _deadline(db, user.user_id, "Linked systems project", days=5)
    now = datetime.utcnow()
    first = Task(
        user_id=user.user_id,
        title="Systems project block one",
        category="study",
        planned_start_utc=now + timedelta(hours=2),
        planned_end_utc=now + timedelta(hours=4),
        planned_duration_minutes=120,
        state=TaskState.PLANNED,
        deadline_id=deadline.deadline_id,
        deadline_match_source="user_explicit",
        deadline_match_confidence=1.0,
    )
    second = Task(
        user_id=user.user_id,
        title="Systems project block two",
        category="study",
        planned_start_utc=now + timedelta(hours=3),
        planned_end_utc=now + timedelta(hours=5),
        planned_duration_minutes=120,
        state=TaskState.PLANNED,
        deadline_id=deadline.deadline_id,
        deadline_match_source="user_explicit",
        deadline_match_confidence=1.0,
    )
    db.add_all([first, second])
    db.commit()

    response = client.get(
        "/v1/academic/pressure-map?horizon_days=14",
        headers=auth_headers(user.user_id),
    )

    assert response.status_code == 200, response.text
    data = response.json()
    projection = data["demand_coverage_projection"]
    assert projection["schema_version"] == "academic_demand_coverage_projection_v1"
    assert projection["projection_status"] == "provisional_demand_only"
    assert projection["capacity_status"] == "unavailable_no_authority"
    assert projection["collision_state"] == "unknown"
    assert projection["obligation_count"] == 1
    assert projection["completed_scope_credit"] == {
        "low_minutes": 0,
        "high_minutes": 0,
    }

    obligation = projection["obligations"][0]
    assert obligation["obligation_id"] == deadline.deadline_id
    assert obligation["projection_role"] == "deadline_obligation"
    assert obligation["linked_task_ids"] == [first.task_id, second.task_id]
    assert obligation["coverage_task_ids"] == [first.task_id, second.task_id]
    assert obligation["noncontributing_linked_task_ids"] == []
    assert obligation["feasible_future_coverage"] == {
        "low_minutes": 180,
        "high_minutes": 180,
    }
    assert projection["total_estimate"] == obligation["total_estimate"]
    assert projection["remaining_demand"] == obligation["remaining_demand"]
    assert (
        projection["remaining_demand"]["low_minutes"]
        == projection["applied_coverage"]["low_minutes"]
        + projection["unscheduled_demand"]["low_minutes"]
    )
    assert data["estimated_low_minutes"] > projection["total_estimate"]["low_minutes"]


def test_pressure_projection_keeps_uncovered_deadline_fully_unscheduled(db):
    user = _user(db, "uncovered-deadline-pressure@example.com")
    deadline = _deadline(db, user.user_id, "Uncovered systems exam", days=5)

    response = client.get(
        "/v1/academic/pressure-map?horizon_days=14",
        headers=auth_headers(user.user_id),
    )

    assert response.status_code == 200, response.text
    projection = response.json()["demand_coverage_projection"]
    assert projection["obligation_count"] == 1
    obligation = projection["obligations"][0]
    assert obligation["obligation_id"] == deadline.deadline_id
    assert obligation["linked_task_ids"] == []
    assert obligation["coverage_task_ids"] == []
    assert obligation["noncontributing_linked_task_ids"] == []
    assert obligation["completed_scope_credit"] == {
        "low_minutes": 0,
        "high_minutes": 0,
    }
    assert obligation["feasible_future_coverage"] == {
        "low_minutes": 0,
        "high_minutes": 0,
    }
    assert obligation["applied_coverage"] == {
        "low_minutes": 0,
        "high_minutes": 0,
    }
    assert obligation["overcoverage"] == {
        "low_minutes": 0,
        "high_minutes": 0,
    }
    assert obligation["remaining_demand"] == obligation["total_estimate"]
    assert obligation["unscheduled_demand"] == obligation["remaining_demand"]


def test_pressure_projection_does_not_credit_elapsed_execution_without_scope_evidence(db):
    user = _user(db, "executed-without-scope-credit-pressure@example.com")
    deadline = _deadline(db, user.user_id, "Operating systems project", days=5)
    now = datetime.utcnow()
    executed_block = Task(
        user_id=user.user_id,
        title="Completed timer block without scope evidence",
        category="study",
        planned_start_utc=now - timedelta(hours=3),
        planned_end_utc=now - timedelta(hours=2),
        planned_duration_minutes=60,
        executed_start_utc=now - timedelta(hours=3),
        executed_end_utc=now - timedelta(hours=2),
        executed_duration_minutes=60,
        state=TaskState.EXECUTED,
        deadline_id=deadline.deadline_id,
        deadline_match_source="user_explicit",
        deadline_match_confidence=1.0,
    )
    future_block = Task(
        user_id=user.user_id,
        title="Future project block",
        category="study",
        planned_start_utc=now + timedelta(hours=2),
        planned_end_utc=now + timedelta(hours=3),
        planned_duration_minutes=60,
        state=TaskState.PLANNED,
        deadline_id=deadline.deadline_id,
        deadline_match_source="user_explicit",
        deadline_match_confidence=1.0,
    )
    db.add_all([executed_block, future_block])
    db.commit()

    response = client.get(
        "/v1/academic/pressure-map?horizon_days=14",
        headers=auth_headers(user.user_id),
    )

    assert response.status_code == 200, response.text
    projection = response.json()["demand_coverage_projection"]
    obligation = projection["obligations"][0]
    assert obligation["obligation_id"] == deadline.deadline_id
    assert obligation["completed_scope_credit"] == {
        "low_minutes": 0,
        "high_minutes": 0,
    }
    assert obligation["linked_task_ids"] == [future_block.task_id]
    assert obligation["coverage_task_ids"] == [future_block.task_id]
    assert obligation["feasible_future_coverage"] == {
        "low_minutes": 60,
        "high_minutes": 60,
    }
    assert executed_block.task_id not in json.dumps(projection)


def test_pressure_projection_does_not_transfer_overcoverage_between_obligations(db):
    user = _user(db, "attributed-overcoverage-pressure@example.com")
    covered_deadline = _deadline(db, user.user_id, "Covered reading", days=5)
    uncovered_deadline = _deadline(db, user.user_id, "Uncovered reading", days=6)
    now = datetime.utcnow()
    linked_block = Task(
        user_id=user.user_id,
        title="Long covered reading block",
        category="study",
        planned_start_utc=now + timedelta(hours=2),
        planned_end_utc=now + timedelta(hours=8),
        planned_duration_minutes=360,
        state=TaskState.PLANNED,
        deadline_id=covered_deadline.deadline_id,
        deadline_match_source="user_explicit",
        deadline_match_confidence=1.0,
    )
    db.add(linked_block)
    db.commit()

    response = client.get(
        "/v1/academic/pressure-map?horizon_days=14",
        headers=auth_headers(user.user_id),
    )

    assert response.status_code == 200, response.text
    projection = response.json()["demand_coverage_projection"]
    obligations = {
        item["obligation_id"]: item
        for item in projection["obligations"]
    }
    covered = obligations[covered_deadline.deadline_id]
    uncovered = obligations[uncovered_deadline.deadline_id]
    assert covered["overcoverage"]["low_minutes"] > 0
    assert uncovered["unscheduled_demand"]["low_minutes"] > 0

    for field in (
        "total_estimate",
        "remaining_demand",
        "feasible_future_coverage",
        "applied_coverage",
        "unscheduled_demand",
        "overcoverage",
    ):
        assert projection[field] == {
            "low_minutes": sum(
                obligation[field]["low_minutes"]
                for obligation in obligations.values()
            ),
            "high_minutes": sum(
                obligation[field]["high_minutes"]
                for obligation in obligations.values()
            ),
        }


@pytest.mark.parametrize("category", ["study", "academic"])
def test_pressure_projection_keeps_unlinked_block_out_of_demand_and_coverage(
    db,
    category,
):
    user = _user(db, f"unlinked-{category}-pressure@example.com")
    now = datetime.utcnow()
    task = Task(
        user_id=user.user_id,
        title=f"Standalone {category} block",
        category=category,
        planned_start_utc=now + timedelta(hours=2),
        planned_end_utc=now + timedelta(hours=3),
        planned_duration_minutes=60,
        state=TaskState.PLANNED,
    )
    db.add(task)
    db.commit()

    response = client.get(
        "/v1/academic/pressure-map?horizon_days=14",
        headers=auth_headers(user.user_id),
    )

    assert response.status_code == 200, response.text
    data = response.json()
    projection = data["demand_coverage_projection"]
    assert projection["obligation_count"] == 0
    assert projection["obligations"] == []
    assert projection["total_estimate"] == {
        "low_minutes": 0,
        "high_minutes": 0,
    }
    assert projection["feasible_future_coverage"] == {
        "low_minutes": 0,
        "high_minutes": 0,
    }
    assert data["source_summary"]["planned_lyra_minutes"] == 60


def test_pressure_projection_does_not_mix_unlinked_block_into_linked_obligation(db):
    user = _user(db, "mixed-linkage-pressure@example.com")
    deadline = _deadline(db, user.user_id, "Linked assignment", days=5)
    now = datetime.utcnow()
    linked_block = Task(
        user_id=user.user_id,
        title="Linked assignment block",
        category="study",
        planned_start_utc=now + timedelta(hours=2),
        planned_end_utc=now + timedelta(hours=3),
        planned_duration_minutes=60,
        state=TaskState.PLANNED,
        deadline_id=deadline.deadline_id,
        deadline_match_source="user_explicit",
        deadline_match_confidence=1.0,
    )
    unlinked_block = Task(
        user_id=user.user_id,
        title="Unlinked seminar block",
        category="academic",
        planned_start_utc=now + timedelta(hours=4),
        planned_end_utc=now + timedelta(hours=5, minutes=30),
        planned_duration_minutes=90,
        state=TaskState.PLANNED,
    )
    db.add_all([linked_block, unlinked_block])
    db.commit()

    response = client.get(
        "/v1/academic/pressure-map?horizon_days=14",
        headers=auth_headers(user.user_id),
    )

    assert response.status_code == 200, response.text
    data = response.json()
    projection = data["demand_coverage_projection"]
    assert projection["obligation_count"] == 1
    obligation = projection["obligations"][0]
    assert obligation["obligation_id"] == deadline.deadline_id
    assert obligation["linked_task_ids"] == [linked_block.task_id]
    assert obligation["coverage_task_ids"] == [linked_block.task_id]
    assert unlinked_block.task_id not in json.dumps(projection)
    assert data["source_summary"]["planned_lyra_minutes"] == 150


def test_pressure_projection_does_not_treat_suggested_link_as_canonical(db):
    user = _user(db, "candidate-link-pressure@example.com")
    deadline = _deadline(db, user.user_id, "Candidate assignment", days=5)
    now = datetime.utcnow()
    suggested_block = Task(
        user_id=user.user_id,
        title="Suggested assignment block",
        category="study",
        planned_start_utc=now + timedelta(hours=2),
        planned_end_utc=now + timedelta(hours=3),
        planned_duration_minutes=60,
        state=TaskState.PLANNED,
        llm_inferred_deadline_id=deadline.deadline_id,
    )
    db.add(suggested_block)
    db.commit()

    response = client.get(
        "/v1/academic/pressure-map?horizon_days=14",
        headers=auth_headers(user.user_id),
    )

    assert response.status_code == 200, response.text
    projection = response.json()["demand_coverage_projection"]
    assert projection["obligation_count"] == 1
    obligation = projection["obligations"][0]
    assert obligation["obligation_id"] == deadline.deadline_id
    assert obligation["linked_task_ids"] == []
    assert obligation["coverage_task_ids"] == []
    assert suggested_block.task_id not in json.dumps(projection)


def test_pressure_projection_does_not_apply_linked_work_after_deadline(db):
    user = _user(db, "late-linked-coverage-pressure@example.com")
    deadline = _deadline(db, user.user_id, "Near-term lab", days=1)
    now = datetime.utcnow()
    deadline.due_at_utc = now + timedelta(hours=2)
    late_task = Task(
        user_id=user.user_id,
        title="Lab block scheduled too late",
        category="study",
        planned_start_utc=now + timedelta(hours=3),
        planned_end_utc=now + timedelta(hours=4),
        planned_duration_minutes=60,
        state=TaskState.PLANNED,
        deadline_id=deadline.deadline_id,
        deadline_match_source="user_explicit",
        deadline_match_confidence=1.0,
    )
    db.add(late_task)
    db.commit()

    response = client.get(
        "/v1/academic/pressure-map?horizon_days=14",
        headers=auth_headers(user.user_id),
    )

    assert response.status_code == 200, response.text
    obligation = response.json()["demand_coverage_projection"]["obligations"][0]
    assert obligation["obligation_id"] == deadline.deadline_id
    assert obligation["linked_task_ids"] == [late_task.task_id]
    assert obligation["coverage_task_ids"] == []
    assert obligation["noncontributing_linked_task_ids"] == [late_task.task_id]
    assert obligation["feasible_future_coverage"] == {
        "low_minutes": 0,
        "high_minutes": 0,
    }
    assert obligation["unscheduled_demand"] == obligation["remaining_demand"]


def test_pressure_projection_does_not_promote_block_for_out_of_scope_deadline(db):
    user = _user(db, "out-of-scope-linked-pressure@example.com")
    deadline = _deadline(db, user.user_id, "Later systems project", days=5)
    now = datetime.utcnow()
    linked_block = Task(
        user_id=user.user_id,
        title="Early systems project block",
        category="study",
        planned_start_utc=now + timedelta(hours=2),
        planned_end_utc=now + timedelta(hours=3),
        planned_duration_minutes=60,
        state=TaskState.PLANNED,
        deadline_id=deadline.deadline_id,
        deadline_match_source="user_explicit",
        deadline_match_confidence=1.0,
    )
    db.add(linked_block)
    db.commit()

    response = client.get(
        "/v1/academic/pressure-map?horizon_days=1",
        headers=auth_headers(user.user_id),
    )

    assert response.status_code == 200, response.text
    data = response.json()
    projection = data["demand_coverage_projection"]
    assert projection["capacity_status"] == "unavailable_no_authority"
    assert projection["collision_state"] == "unknown"
    assert projection["obligation_count"] == 0
    assert projection["obligations"] == []
    assert data["source_summary"]["planned_lyra_minutes"] == 60


def test_pressure_projection_schema_rejects_inverted_envelope():
    with pytest.raises(ValidationError, match="low_minutes cannot exceed"):
        AcademicMinuteEnvelope(low_minutes=90, high_minutes=60)


def test_pressure_map_includes_prescheduled_academic_task_blocks(db):
    user = _user(db, "academic-task-pressure@example.com")
    now = datetime.utcnow()
    db.add_all(
        [
            Task(
                user_id=user.user_id,
                title="CO MARS labs",
                category="academic",
                planned_start_utc=now + timedelta(hours=2),
                planned_end_utc=now + timedelta(hours=4),
                planned_duration_minutes=120,
                state=TaskState.PLANNED,
            ),
            Task(
                user_id=user.user_id,
                title="planning task",
                category="planning",
                planned_start_utc=now + timedelta(hours=5),
                planned_end_utc=now + timedelta(hours=6),
                planned_duration_minutes=60,
                state=TaskState.PLANNED,
            ),
        ]
    )
    db.commit()

    resp = client.get("/v1/academic/pressure-map", headers=auth_headers(user.user_id))

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert [item["title"] for item in data["items"]] == ["CO MARS labs"]
    assert data["source_summary"]["academic_task_count"] == 1
    assert data["source_summary"]["academic_task_minutes"] == 120
    assert data["source_summary"]["study_task_count"] == 0
    assert data["estimated_low_minutes"] == 120
    assert data["items"][0]["source"] == "lyra_academic_task"
    assert data["items"][0]["obligation_type"] == "lab"
    assert data["items"][0]["trust_state"] == "requires_user_confirmation"


def test_pressure_map_projects_old_study_lab_rows_as_academic_structure(db):
    user = _user(db, "old-study-lab-pressure@example.com")
    now = datetime.utcnow()
    db.add(
        Task(
            user_id=user.user_id,
            title="CO MARS labs",
            category="study",
            planned_start_utc=now + timedelta(hours=2),
            planned_end_utc=now + timedelta(hours=4),
            planned_duration_minutes=120,
            state=TaskState.PLANNED,
        )
    )
    db.commit()

    resp = client.get("/v1/academic/pressure-map", headers=auth_headers(user.user_id))

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["source_summary"]["academic_task_count"] == 1
    assert data["source_summary"]["study_task_count"] == 0
    assert data["items"][0]["source"] == "lyra_academic_task"
    assert data["items"][0]["obligation_type"] == "lab"


def test_pressure_map_empty_state_has_low_authority_methodology(db):
    user = _user(db, "empty-pressure@example.com")

    resp = client.get("/v1/academic/pressure-map", headers=auth_headers(user.user_id))

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["items"] == []
    assert "No active academic obligations" in data["headline"]
    assert data["pressure_summary"] == "No visible academic pressure in this window."
    assert data["recovery_options"][0]["action"] == "clear_or_ignore"
    assert any("ranges instead of exact-hour claims" in line for line in data["methodology"])


def test_pressure_map_uses_agency_not_panic_copy(db):
    user = _user(db, "agency-pressure@example.com")
    _deadline(db, user.user_id, "Algorithms Quiz", days=1, external_source="moodle_ics")

    resp = client.get("/v1/academic/pressure-map", headers=auth_headers(user.user_id))

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "recovery option" in data["headline"]
    assert "overloaded" not in data["headline"].lower()
    assert "overloaded" not in data["pressure_summary"].lower()
    assert any("clarity and agency" in warning for warning in data["warnings"])
    assert any("trust-state copy" in line for line in data["methodology"])
    assert any("research integrity" in line for line in data["methodology"])


def test_pressure_map_names_deadline_clusters_and_biggest_split_option(db):
    user = _user(db, "cluster-pressure@example.com")
    _deadline(db, user.user_id, "Algorithms Quiz", days=2, external_source="moodle_ics")
    _deadline(db, user.user_id, "Systems Project", days=3, external_source="moodle_ics")

    resp = client.get("/v1/academic/pressure-map", headers=auth_headers(user.user_id))

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert any(point["kind"] == "cluster" for point in data["compression_points"])
    assert any(option["action"] == "split_into_blocks" for option in data["recovery_options"])


def test_baseet_pressure_input_kill_switch_suppresses_baseet_rows(db, monkeypatch):
    monkeypatch.setattr(settings, "LYRA_BASEET_PRESSURE_INPUT_ENABLED", False)
    user = _user(db, "baseet-kill-switch@example.com")
    _deadline(db, user.user_id, "Baseet Assignment 1", days=2, external_source="baseet_mock")
    _deadline(db, user.user_id, "Moodle Quiz", days=2, external_source="moodle_ics")

    resp = client.get(
        "/v1/academic/pressure-map?horizon_days=14",
        headers=auth_headers(user.user_id),
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert [item["title"] for item in data["items"]] == ["Moodle Quiz"]
    assert {item["provider_kind"] for item in data["items"]} == {"moodle"}
    assert data["source_summary"]["external_obligation_count"] == 1
    assert any("Baseet pressure inputs are disabled" in warning for warning in data["warnings"])


def test_recovery_nudge_kill_switch_suppresses_pressure_map_recovery_options(db, monkeypatch):
    monkeypatch.setattr(settings, "LYRA_RECOVERY_NUDGES_ENABLED", False)
    user = _user(db, "recovery-kill-switch@example.com")
    _deadline(db, user.user_id, "Algorithms Quiz", days=1, external_source="moodle_ics")

    resp = client.get(
        "/v1/academic/pressure-map?horizon_days=14",
        headers=auth_headers(user.user_id),
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["items"]
    assert data["recovery_options"] == []
    assert recovery_nudges_enabled() is False
    assert any("Recovery nudges are disabled" in warning for warning in data["warnings"])


def test_read_only_pressure_safe_mode_suppresses_risky_paths(db, monkeypatch):
    monkeypatch.setattr(settings, "LYRA_SAFE_MODE", "read_only_pressure")
    monkeypatch.setattr(settings, "LYRA_PROVIDER_PROGRESS_SIGNALS_ENABLED", True)
    monkeypatch.setattr(settings, "LYRA_RECOVERY_NUDGES_ENABLED", True)
    user = _user(db, "safe-mode-pressure@example.com")
    _deadline(db, user.user_id, "Algorithms Quiz", days=1, external_source="moodle_ics")

    resp = client.get(
        "/v1/academic/pressure-map?horizon_days=14",
        headers=auth_headers(user.user_id),
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["items"]
    assert data["recovery_options"] == []
    assert recovery_nudges_enabled() is False
    assert provider_progress_signals_enabled() is False
    assert any("Read-only pressure safe mode is active" in warning for warning in data["warnings"])
