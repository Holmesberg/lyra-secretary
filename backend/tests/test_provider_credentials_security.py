from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest

from app.db.models import Deadline, User
from app.db.scoping import set_current_user_id
from app.services import calendar_sync, moodle_ics_sync
from app.utils.encryption import decrypt_secret, is_encrypted_secret
from tests.conftest import TestingSession


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "moodle_sample.ics"


@pytest.fixture(autouse=True)
def _clean_slate(db):
    set_current_user_id(None)
    db.rollback()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()


def _make_user(db, **kwargs) -> User:
    user = User(
        email=f"provider-{uuid4().hex[:8]}@example.test",
        google_id=None,
        timezone="Africa/Cairo",
        terms_accepted_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        **kwargs,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_google_refresh_token_is_encrypted_at_rest(db, monkeypatch):
    user = _make_user(db)
    monkeypatch.setattr(calendar_sync, "SessionLocal", TestingSession)

    calendar_sync.store_refresh_token(user.user_id, "raw-google-refresh-token")

    db.expire_all()
    stored = db.query(User).filter(User.user_id == user.user_id).one()
    assert stored.google_refresh_token != "raw-google-refresh-token"
    assert is_encrypted_secret(stored.google_refresh_token)
    assert decrypt_secret(stored.google_refresh_token) == "raw-google-refresh-token"


def test_moodle_ics_legacy_plaintext_rewrites_encrypted_on_sync(db, monkeypatch):
    user = _make_user(
        db,
        moodle_ics_url=(
            "https://lms.test/calendar/export_execute.php"
            "?userid=1&authtoken=raw-moodle-token&preset_time=recentupcoming"
        ),
    )

    monkeypatch.setattr(
        moodle_ics_sync,
        "fetch_ics",
        lambda url: FIXTURE_PATH.read_bytes(),
    )

    result = moodle_ics_sync.sync_user(user.user_id, db)

    assert result.error is None
    db.expire_all()
    stored = db.query(User).filter(User.user_id == user.user_id).one()
    assert stored.moodle_ics_url is not None
    assert "raw-moodle-token" not in stored.moodle_ics_url
    assert is_encrypted_secret(stored.moodle_ics_url)
    assert decrypt_secret(stored.moodle_ics_url).endswith(
        "authtoken=raw-moodle-token&preset_time=recentupcoming"
    )
