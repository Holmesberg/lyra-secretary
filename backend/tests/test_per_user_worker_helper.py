from datetime import datetime

from sqlalchemy.orm import object_session

from app.db.models import User
from app.db.scoping import get_current_user_id, set_current_user_id
from app.workers.jobs import _per_user
from tests.conftest import TestingSession


def test_for_each_user_passes_session_attached_user(db, monkeypatch):
    db.rollback()
    db.query(User).delete()
    db.commit()
    user = User(
        email="worker-user@example.com",
        google_id=None,
        timezone="Africa/Cairo",
        is_operator=False,
        notion_enabled=False,
        terms_accepted_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    user_id = user.user_id

    monkeypatch.setattr(_per_user, "SessionLocal", TestingSession)

    def _mutate_user(job_db, scoped_user):
        assert object_session(scoped_user) is job_db
        assert get_current_user_id() == user_id
        scoped_user.moodle_base_url = "https://lms.example.edu"
        job_db.commit()

    _per_user.for_each_user(_mutate_user)

    db.expire_all()
    refreshed = db.query(User).filter(User.user_id == user_id).one()
    assert refreshed.moodle_base_url == "https://lms.example.edu"
    assert get_current_user_id() is None
    set_current_user_id(None)
