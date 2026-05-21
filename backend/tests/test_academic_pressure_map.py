import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

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
    _deadline(db, bob.user_id, "Private Final Exam", days=5)

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
    assert data["render_id"]
    assert data["coverage_questions"][0]["trust_state"] == "verified_reachable"
    assert "3-5 student confirmations" in data["coverage_questions"][0]["reason"]
    assert data["capacity_context"]["google_calendar_connected"] is False
    assert "not true free time" in data["capacity_context"]["caveat"]
    assert data["source_summary"]["external_obligation_count"] == 1
    assert data["source_summary"]["native_obligation_count"] == 0
    assert "moodle_deadlines" not in data["source_summary"]
    assert "native_deadlines" not in data["source_summary"]

    decision = (
        db.query(ExposureDecisionEvent)
        .filter(ExposureDecisionEvent.exposure_id == data["exposure_id"])
        .one()
    )
    render = (
        db.query(ExposureRenderEvent)
        .filter(ExposureRenderEvent.render_id == data["render_id"])
        .one()
    )
    assert decision.user_id == alice.user_id
    assert decision.exposure_category == "scheduling_suggestion"
    assert render.surface == "academic.pressure_map"
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
