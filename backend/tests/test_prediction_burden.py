from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.db.models import PausePredictionLog, User
from app.db.scoping import set_current_user_id
from app.services.prediction_burden import (
    acquire_prediction_spacing_window,
    is_within_prediction_quiet_hours,
)


@pytest.mark.parametrize(
    ("utc_value", "timezone_name", "expected"),
    [
        (datetime(2026, 7, 15, 21, 59), "UTC", False),
        (datetime(2026, 7, 15, 22, 0), "UTC", True),
        (datetime(2026, 7, 16, 7, 59), "UTC", True),
        (datetime(2026, 7, 16, 8, 0), "UTC", False),
        (datetime(2026, 7, 15, 13, 0), "Asia/Tokyo", True),
        (
            datetime(2026, 7, 15, 13, 0, tzinfo=timezone.utc),
            "Asia/Tokyo",
            True,
        ),
    ],
)
def test_prediction_quiet_hours_use_user_local_boundaries(
    utc_value,
    timezone_name,
    expected,
):
    assert (
        is_within_prediction_quiet_hours(utc_value, timezone_name) is expected
    )


@pytest.mark.parametrize("timezone_name", ["", "Not/A-Timezone"])
def test_prediction_quiet_hours_reject_invalid_timezones(timezone_name):
    with pytest.raises(ValueError):
        is_within_prediction_quiet_hours(
            datetime(2026, 7, 15, 12, 0),
            timezone_name,
        )


def test_prediction_spacing_blocks_same_user_inside_window(db):
    user_id = 9911
    set_current_user_id(None)
    db.add(User(user_id=user_id, email="spacing-9911@test", timezone="UTC"))
    db.add(
        PausePredictionLog(
            firing_id=str(uuid4()),
            user_id=user_id,
            fired_at=datetime(2026, 7, 15, 11, 30, 1),
            predicted_at=datetime(2026, 7, 15, 11, 33, 1),
            mechanism="clock_anchor",
            confidence=0.7,
            lead_minutes=3,
            sample_size=7,
        )
    )
    db.commit()
    set_current_user_id(user_id)

    try:
        assert not acquire_prediction_spacing_window(
            db,
            user_id,
            datetime(2026, 7, 15, 12, 0),
        )
    finally:
        db.rollback()
        set_current_user_id(None)
        db.query(PausePredictionLog).filter(
            PausePredictionLog.user_id == user_id
        ).delete(synchronize_session=False)
        db.query(User).filter(User.user_id == user_id).delete(
            synchronize_session=False
        )
        db.commit()


def test_prediction_spacing_allows_exact_boundary_and_other_user(db):
    user_id = 9912
    other_user_id = 9913
    set_current_user_id(None)
    db.add(User(user_id=user_id, email="spacing-9912@test", timezone="UTC"))
    db.add(
        PausePredictionLog(
            firing_id=str(uuid4()),
            user_id=user_id,
            fired_at=datetime(2026, 7, 15, 11, 30),
            predicted_at=datetime(2026, 7, 15, 11, 33),
            mechanism="clock_anchor",
            confidence=0.7,
            lead_minutes=3,
            sample_size=7,
        )
    )
    db.add(
        PausePredictionLog(
            firing_id=str(uuid4()),
            user_id=other_user_id,
            fired_at=datetime(2026, 7, 15, 11, 59),
            predicted_at=datetime(2026, 7, 15, 12, 2),
            mechanism="clock_anchor",
            confidence=0.7,
            lead_minutes=3,
            sample_size=7,
        )
    )
    db.commit()
    set_current_user_id(user_id)

    try:
        assert acquire_prediction_spacing_window(
            db,
            user_id,
            datetime(2026, 7, 15, 12, 0),
        )
    finally:
        db.rollback()
        set_current_user_id(None)
        db.query(PausePredictionLog).filter(
            PausePredictionLog.user_id.in_([user_id, other_user_id])
        ).delete(synchronize_session=False)
        db.query(User).filter(User.user_id == user_id).delete(
            synchronize_session=False
        )
        db.commit()
