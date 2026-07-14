"""Characterization tests for the Brain Dump onboarding skip boundary."""

from datetime import datetime

from app.api.v1.endpoints import users as users_module
from app.db.models import Deadline, Task, User


def test_skip_onboarding_is_first_write_wins_without_product_rows(
    client,
    db,
    monkeypatch,
):
    user = User(
        email="onboarding-skip-contract@example.com",
        google_id=None,
        timezone="Africa/Cairo",
        is_operator=False,
        notion_enabled=False,
        terms_accepted_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    invalidated_user_ids = []
    monkeypatch.setattr(
        users_module,
        "invalidate_me",
        lambda user_id: invalidated_user_ids.append(user_id),
    )
    headers = {"X-User-Id": str(user.user_id)}

    first = client.post("/v1/users/me/skip-onboarding", headers=headers)
    replay = client.post("/v1/users/me/skip-onboarding", headers=headers)

    assert first.status_code == 200, first.text
    assert replay.status_code == 200, replay.text
    assert first.json() == replay.json()
    assert first.json()["onboarding_completed_at"] is not None
    assert invalidated_user_ids == [user.user_id]

    db.expire_all()
    refreshed = db.query(User).filter(User.user_id == user.user_id).one()
    assert refreshed.onboarding_completed_at is not None
    assert (
        db.query(Task).filter(Task.user_id == user.user_id).count()
        == 0
    )
    assert (
        db.query(Deadline).filter(Deadline.user_id == user.user_id).count()
        == 0
    )
