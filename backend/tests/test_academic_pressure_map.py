from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.db.models import Deadline, Task, TaskState, User
from app.db.scoping import set_current_user_id
from app.main import app
from tests.conftest import auth_headers


client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _clean(db):
    set_current_user_id(None)
    db.rollback()
    db.query(Task).delete()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
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
    assert item["estimate"]["low_minutes"] < item["estimate"]["high_minutes"]
    assert item["estimate"]["low_minutes"] % 30 == 0
    assert item["estimate"]["high_minutes"] % 30 == 0
    assert item["trust_state"] == "verified_reachable"
    assert "coverage correctness" in " ".join(item["warnings"])
    assert "pressure_summary" in data
    assert data["coverage_questions"][0]["trust_state"] == "verified_reachable"
    assert "3-5 student confirmations" in data["coverage_questions"][0]["reason"]
    assert data["capacity_context"]["google_calendar_connected"] is False
    assert "not true free time" in data["capacity_context"]["caveat"]


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
    assert resp.json()["source_summary"]["planned_lyra_minutes"] == 60


def test_pressure_map_empty_state_has_low_authority_methodology(db):
    user = _user(db, "empty-pressure@example.com")

    resp = client.get("/v1/academic/pressure-map", headers=auth_headers(user.user_id))

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["items"] == []
    assert "No active academic deadlines" in data["headline"]
    assert data["pressure_summary"] == "No visible academic deadline pressure in this window."
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
