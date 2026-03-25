from datetime import datetime
from app.utils.time_utils import to_utc

def test_naive_cairo_to_utc_conversion():
    dt_input = datetime.strptime("2026-03-31T11:00:00", "%Y-%m-%dT%H:%M:%S")
    dt_utc = to_utc(dt_input)
    assert dt_utc.strftime("%Y-%m-%dT%H:%M:%S") == "2026-03-31T09:00:00"
