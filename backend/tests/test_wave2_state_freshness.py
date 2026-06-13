from datetime import timedelta
from uuid import uuid4

from app.db.models import Task, TaskState, User
from app.services.task_manager import TaskManager
from app.utils.time_utils import now_utc


class _FakeRedis:
    def queue_notion_sync(self, *_args, **_kwargs):
        return None

    def cache_undo_action(self, *_args, **_kwargs):
        return None

    def set_last_task(self, *_args, **_kwargs):
        return None


class _FakeNotion:
    def sync_task(self, *_args, **_kwargs):
        return None

    def archive_page(self, *_args, **_kwargs):
        return None


def _manager(db):
    manager = TaskManager(db)
    manager.redis = _FakeRedis()
    manager.notion = _FakeNotion()
    return manager


def _seed_user(db, user_id: int) -> User:
    user = db.query(User).filter(User.user_id == user_id).first()
    if user:
        return user
    now = now_utc()
    user = User(
        user_id=user_id,
        email=f"wave2-cache-{user_id}@example.test",
        is_operator=True,
        created_at=now - timedelta(days=3),
    )
    db.add(user)
    db.commit()
    return user


def _seed_task(db, *, user_id: int, state: TaskState) -> Task:
    now = now_utc()
    task = Task(
        task_id=str(uuid4()),
        user_id=user_id,
        title=f"Wave 2 cache {state.value}",
        category="study",
        planned_start_utc=now + timedelta(hours=1),
        planned_end_utc=now + timedelta(hours=2),
        planned_duration_minutes=60,
        state=state,
        source="manual",
        created_at=now,
        last_modified_at=now,
    )
    db.add(task)
    db.commit()
    return task


def _capture_invalidations(monkeypatch):
    calls: list[int] = []
    monkeypatch.setattr(
        "app.services.task_manager.invalidate_user_ranges",
        lambda uid: calls.append(int(uid)),
    )
    monkeypatch.setattr(
        "app.services.task_manager.invalidate_me",
        lambda _uid: None,
    )
    return calls


def test_task_state_transitions_invalidate_user_range_cache(db, monkeypatch):
    user_id = 9961
    _seed_user(db, user_id)
    planned_for_start = _seed_task(db, user_id=user_id, state=TaskState.PLANNED)
    executing_for_complete = _seed_task(
        db, user_id=user_id, state=TaskState.EXECUTING
    )
    planned_for_skip = _seed_task(db, user_id=user_id, state=TaskState.PLANNED)
    planned_for_delete = _seed_task(db, user_id=user_id, state=TaskState.PLANNED)
    calls = _capture_invalidations(monkeypatch)
    manager = _manager(db)

    manager.start_task(planned_for_start.task_id)
    manager.complete_task(
        executing_for_complete.task_id,
        now_utc() - timedelta(minutes=45),
        now_utc(),
    )
    manager.skip_task(planned_for_skip.task_id)
    manager.delete_task(planned_for_delete.task_id)

    assert calls.count(user_id) >= 4


def test_swap_and_reschedule_invalidate_user_range_cache(db, monkeypatch):
    user_id = 9962
    _seed_user(db, user_id)
    skipped = _seed_task(db, user_id=user_id, state=TaskState.SKIPPED)
    planned = _seed_task(db, user_id=user_id, state=TaskState.PLANNED)
    movable = _seed_task(db, user_id=user_id, state=TaskState.PLANNED)
    calls = _capture_invalidations(monkeypatch)
    manager = _manager(db)

    manager.swap_tasks(skipped.task_id, planned.task_id)
    manager.reschedule_task(
        movable.task_id,
        now_utc() + timedelta(hours=3),
        now_utc() + timedelta(hours=4),
    )

    assert user_id in calls
    assert calls.count(user_id) >= 2
