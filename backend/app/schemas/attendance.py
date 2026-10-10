from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, Field


class AttendanceRuleUpdate(BaseModel):
    work_start_time: time
    work_end_time: time
    late_threshold: int = Field(ge=0, le=1440)
    early_leave_threshold: int = Field(ge=0, le=1440)
    work_days: list[int] = Field(min_length=1)
    single_deduct: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class AttendanceAdjustRequest(BaseModel):
    status: str
    adjust_note: str = Field(min_length=1, max_length=500)


class AttendanceRecordResponse(BaseModel):
    id: int
    employee_id: int
    work_date: date
    check_in_time: datetime | None
    check_out_time: datetime | None
    status: str
    adjust_note: str | None
