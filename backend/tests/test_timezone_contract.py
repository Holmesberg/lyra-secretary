from datetime import datetime
from app.utils.time_utils import to_utc
import sys

def test_naive_cairo_to_utc_conversion():
    # Input: "2026-03-31T11:00:00" (naive Cairo)
    input_str = "2026-03-31T11:00:00"
    dt_input = datetime.strptime(input_str, "%Y-%m-%dT%H:%M:%S")
    
    # Perform conversion using the backend's exact unit (to_utc)
    dt_utc = to_utc(dt_input)
    
    # Expected stored value: "2026-03-31T09:00:00" (UTC)
    expected_str = "2026-03-31T09:00:00"
    
    if dt_utc.isoformat() == expected_str:
        print("Test passed: Naive Cairo local time correctly converted to UTC.")
        sys.exit(0)
    else:
        print(f"Test failed: Expected {expected_str}, got {dt_utc.isoformat()}")
        sys.exit(1)

if __name__ == "__main__":
    test_naive_cairo_to_utc_conversion()
