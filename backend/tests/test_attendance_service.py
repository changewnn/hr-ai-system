from datetime import datetime, time, timezone
from types import SimpleNamespace

from app.models.entities import AttendanceStatus
from app.services.attendance import classify_status, is_workday, validate_work_days


RULE = SimpleNamespace(work_start_time=time(9, 0), work_end_time=time(18, 0), late_threshold=5, early_leave_threshold=5)


def test_attendance_status_thresholds() -> None:
    normal_in = datetime(2026, 10, 9, 1, 5, tzinfo=timezone.utc)
    normal_out = datetime(2026, 10, 9, 10, 0, tzinfo=timezone.utc)
    assert classify_status(normal_in, normal_out, RULE) == AttendanceStatus.NORMAL

    late_in = datetime(2026, 10, 9, 1, 6, tzinfo=timezone.utc)
    assert classify_status(late_in, normal_out, RULE) == AttendanceStatus.LATE
    assert classify_status(normal_in, None, RULE) == AttendanceStatus.MISSING


def test_workday_and_invalid_rule_days() -> None:
    assert is_workday(datetime(2026, 10, 9).date(), [1, 2, 3, 4, 5])
    assert not is_workday(datetime(2026, 10, 10).date(), [1, 2, 3, 4, 5])
    validate_work_days([1, 2, 3, 4, 5])
