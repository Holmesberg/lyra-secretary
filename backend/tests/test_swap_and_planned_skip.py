"""
Tests for:
  - POST /v1/tasks/swap  (SKIPPED↔PLANNED atomic swap)
  - POST /v1/tasks/{id}/mark-abandoned  (extended to PLANNED→SKIPPED)
"""
from fastapi.testclient import TestClient

from app.db.models import Task, TaskSource, TaskState
from app.main import app
from app.utils.time_utils import now_utc
from datetime import timedelta
from tests.conftest import TestingSession

client = TestClient(app, raise_server_exceptions=False)


def _seed(
    task_id: str,
    state: TaskState,
    hours_from_now: int = 1,
    *,
    initiation_status: str = "not_started",
    executed_duration_minutes: int | None = None,
):
    db = TestingSession()
    t = Task(
        task_id=task_id,
        title=f"Task {task_id}",
        planned_start_utc=now_utc() + timedelta(hours=hours_from_now),
        planned_end_utc=now_utc() + timedelta(hours=hours_from_now + 1),
        planned_duration_minutes=60,
        executed_duration_minutes=executed_duration_minutes,
        state=state,
        source=TaskSource.MANUAL,
        initiation_status=initiation_status,
        user_id=1,
    )
    db.add(t)
    db.commit()
    db.close()


# ── swap tests ──────────────────────────────────────────────────────────────

def test_swap_skipped_and_planned():
    _seed("swap-s1", TaskState.SKIPPED, hours_from_now=2)
    _seed("swap-p1", TaskState.PLANNED, hours_from_now=4)

    r = client.post("/v1/tasks/swap", json={"task_a_id": "swap-s1", "task_b_id": "swap-p1"})
    assert r.status_code == 200
    body = r.json()
    assert body["swapped"] is True
    assert body["reactivated_task_id"] == "swap-s1"
    assert body["skipped_task_id"] == "swap-p1"

    db = TestingSession()
    reactivated = db.query(Task).filter(Task.task_id == "swap-s1").first()
    skipped = db.query(Task).filter(Task.task_id == "swap-p1").first()
    db.close()

    assert reactivated.state == TaskState.PLANNED
    assert skipped.state == TaskState.SKIPPED
    assert skipped.initiation_status == "user_skipped"
    # Reactivated task adopts the formerly-planned task's time slot
    assert reactivated.planned_start_utc == skipped.planned_start_utc


def test_swap_order_independent():
    """task_a can be either SKIPPED or PLANNED — order doesn't matter."""
    _seed("swap-s2", TaskState.SKIPPED, hours_from_now=3)
    _seed("swap-p2", TaskState.PLANNED, hours_from_now=5)

    r = client.post("/v1/tasks/swap", json={"task_a_id": "swap-p2", "task_b_id": "swap-s2"})
    assert r.status_code == 200
    assert r.json()["reactivated_task_id"] == "swap-s2"
    assert r.json()["skipped_task_id"] == "swap-p2"


def test_swap_rejects_two_planned():
    _seed("swap-pp1", TaskState.PLANNED, hours_from_now=1)
    _seed("swap-pp2", TaskState.PLANNED, hours_from_now=2)

    r = client.post("/v1/tasks/swap", json={"task_a_id": "swap-pp1", "task_b_id": "swap-pp2"})
    assert r.status_code == 400
    assert "SKIPPED" in r.json()["detail"]


def test_swap_rejects_two_skipped():
    _seed("swap-ss1", TaskState.SKIPPED, hours_from_now=1)
    _seed("swap-ss2", TaskState.SKIPPED, hours_from_now=2)

    r = client.post("/v1/tasks/swap", json={"task_a_id": "swap-ss1", "task_b_id": "swap-ss2"})
    assert r.status_code == 400


def test_swap_reactivated_clears_execution_data():
    """A SKIPPED task that had partial execution data gets cleared on swap."""
    db = TestingSession()
    t = Task(
        task_id="swap-exec",
        title="was executing",
        planned_start_utc=now_utc() + timedelta(hours=1),
        planned_end_utc=now_utc() + timedelta(hours=2),
        planned_duration_minutes=60,
        state=TaskState.SKIPPED,
        source=TaskSource.MANUAL,
        executed_duration_minutes=5,
        initiation_status="abandoned",
        user_id=1,
    )
    db.add(t)
    db.commit()
    db.close()

    _seed("swap-plan-for-exec", TaskState.PLANNED, hours_from_now=3)

    r = client.post("/v1/tasks/swap", json={"task_a_id": "swap-exec", "task_b_id": "swap-plan-for-exec"})
    assert r.status_code == 200

    db = TestingSession()
    reactivated = db.query(Task).filter(Task.task_id == "swap-exec").first()
    db.close()

    assert reactivated.executed_duration_minutes is None
    assert reactivated.initiation_status == "not_started"


# ── PLANNED→SKIPPED via mark-abandoned ──────────────────────────────────────

def test_planned_mark_abandoned_transitions_to_skipped():
    _seed("planned-skip-1", TaskState.PLANNED)

    r = client.post("/v1/tasks/planned-skip-1/mark-abandoned", json={"reason": "not needed today"})
    assert r.status_code == 200
    body = r.json()
    assert body["abandoned"] is True
    assert body["new_state"] == "SKIPPED"

    db = TestingSession()
    t = db.query(Task).filter(Task.task_id == "planned-skip-1").first()
    db.close()
    assert t.state == TaskState.SKIPPED
    assert t.initiation_status == "user_skipped"


def test_planned_mark_abandoned_sets_user_skipped_status():
    _seed("planned-skip-2", TaskState.PLANNED)

    r = client.post("/v1/tasks/planned-skip-2/mark-abandoned")
    assert r.status_code == 200

    db = TestingSession()
    t = db.query(Task).filter(Task.task_id == "planned-skip-2").first()
    db.close()
    assert t.initiation_status == "user_skipped"


def test_executed_task_cannot_be_mark_abandoned():
    db = TestingSession()
    t = Task(
        task_id="exec-skip",
        title="done task",
        planned_start_utc=now_utc() - timedelta(hours=2),
        planned_end_utc=now_utc() - timedelta(hours=1),
        planned_duration_minutes=60,
        state=TaskState.EXECUTED,
        source=TaskSource.MANUAL,
        user_id=1,
    )
    db.add(t)
    db.commit()
    db.close()

    r = client.post("/v1/tasks/exec-skip/mark-abandoned")
    assert r.status_code == 400


# ── overdue done affordance ────────────────────────────────────────────────

def test_skipped_overdue_task_can_be_marked_done_retroactively():
    _seed(
        "done-skipped-overdue",
        TaskState.SKIPPED,
        hours_from_now=-2,
        initiation_status="abandoned",
    )

    r = client.post("/v1/tasks/done-skipped-overdue/mark-done")
    assert r.status_code == 200
    body = r.json()
    assert body["done"] is True
    assert body["retrospective"] is True
    assert body["previous_state"] == "SKIPPED"
    assert body["new_state"] == "EXECUTED"
    assert body["initiation_status"] == "retroactive"

    db = TestingSession()
    t = db.query(Task).filter(Task.task_id == "done-skipped-overdue").first()
    db.close()
    assert t.state == TaskState.EXECUTED
    assert t.initiation_status == "retroactive"
    assert t.executed_start_utc == t.planned_start_utc
    assert t.executed_end_utc == t.planned_end_utc
    assert t.executed_duration_minutes == t.planned_duration_minutes


def test_planned_overdue_task_can_be_marked_done_retroactively():
    _seed("done-planned-overdue", TaskState.PLANNED, hours_from_now=-2)

    r = client.post("/v1/tasks/done-planned-overdue/mark-done")
    assert r.status_code == 200

    db = TestingSession()
    t = db.query(Task).filter(Task.task_id == "done-planned-overdue").first()
    db.close()
    assert t.state == TaskState.EXECUTED
    assert t.initiation_status == "retroactive"


def test_future_task_cannot_be_marked_done_retroactively():
    _seed("done-future", TaskState.PLANNED, hours_from_now=2)

    r = client.post("/v1/tasks/done-future/mark-done")
    assert r.status_code == 400
    assert "overdue" in r.json()["detail"]


def test_skipped_task_with_existing_execution_data_cannot_be_overwritten():
    _seed(
        "done-partial",
        TaskState.SKIPPED,
        hours_from_now=-2,
        initiation_status="abandoned",
        executed_duration_minutes=5,
    )

    r = client.post("/v1/tasks/done-partial/mark-done")
    assert r.status_code == 400
    assert "execution data" in r.json()["detail"]
