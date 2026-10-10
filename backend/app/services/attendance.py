from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.common.errors import BusinessError
from app.core.config import get_settings
from app.models.entities import AttendanceStatus


def business_now() -> datetime:
    return datetime.now(ZoneInfo(get_settings().timezone))


def is_workday(work_date: date, work_days: list[int]) -> bool:
    return work_date.isoweekday() in work_days


def classify_status(check_in: datetime | None, check_out: datetime | None, rule) -> AttendanceStatus:
    if check_in is None or check_out is None:
        return AttendanceStatus.MISSING
    local_tz = ZoneInfo(get_settings().timezone)
    in_local = check_in.astimezone(local_tz)
    out_local = check_out.astimezone(local_tz)
    start = datetime.combine(in_local.date(), rule.work_start_time, tzinfo=local_tz)
    end = datetime.combine(out_local.date(), rule.work_end_time, tzinfo=local_tz)
    late = in_local > start + timedelta(minutes=rule.late_threshold)
    early = out_local < end - timedelta(minutes=rule.early_leave_threshold)
    if late and early:
        return AttendanceStatus.LATE
    if late:
        return AttendanceStatus.LATE
    if early:
        return AttendanceStatus.EARLY_LEAVE
    return AttendanceStatus.NORMAL


def validate_work_days(work_days: list[int]) -> None:
    if any(day < 1 or day > 7 for day in work_days) or len(set(work_days)) != len(work_days):
        raise BusinessError(30003, "ATTENDANCE_WORK_DAYS_INVALID", "工作日必须为 1 到 7 的不重复数字", 400)
