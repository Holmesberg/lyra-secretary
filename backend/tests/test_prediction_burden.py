from datetime import datetime, timezone

import pytest

from app.services.prediction_burden import is_within_prediction_quiet_hours


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
