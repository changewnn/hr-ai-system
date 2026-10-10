from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.errors import BusinessError
from app.models.entities import AttendanceRule, LeaveRequest, LeaveStatus, LeaveType
from app.models.leave_balance import LeaveBalance
from app.services.attendance import business_now


def working_dates(start: date, end: date, work_days: list[int]) -> list[date]:
    result: list[date] = []
    cursor = start
    while cursor <= end:
        if cursor.isoweekday() in work_days:
            result.append(cursor)
        cursor += timedelta(days=1)
    return result


def calculate_leave_days(start: date, end: date, start_period: str, end_period: str, work_days: list[int]) -> Decimal:
    if end < start:
        raise BusinessError(40002, "LEAVE_INVALID_RANGE", "请假日期范围无效", 400)
    dates = working_dates(start, end, work_days)
    if not dates:
        raise BusinessError(40002, "LEAVE_INVALID_RANGE", "请假日期不包含工作日", 400)
    if start == end:
        if start_period == "PM" and end_period == "AM":
            raise BusinessError(40002, "LEAVE_INVALID_RANGE", "单日请假时段无效", 400)
        return Decimal("0.5") if start_period != "AM" or end_period != "PM" else Decimal("1.0")
    total = Decimal("0")
    for index, _ in enumerate(dates):
        if index == 0:
            total += Decimal("0.5") if start_period == "PM" else Decimal("1.0")
        elif index == len(dates) - 1:
            total += Decimal("0.5") if end_period == "AM" else Decimal("1.0")
        else:
            total += Decimal("1.0")
    return total


async def get_work_days(session: AsyncSession) -> list[int]:
    rule = await session.scalar(select(AttendanceRule).limit(1))
    return rule.work_days if rule else [1, 2, 3, 4, 5]


async def validate_leave_type(session: AsyncSession, leave_type_id: int) -> LeaveType:
    leave_type = await session.get(LeaveType, leave_type_id)
    if leave_type is None or leave_type.status.value != "ACTIVE":
        raise BusinessError(40008, "LEAVE_TYPE_NOT_FOUND", "请假类型不存在或已停用", 404)
    return leave_type


async def annual_remaining(session: AsyncSession, employee_id: int, leave_type_id: int, year: int, pending_exclude_id: int | None = None) -> Decimal:
    balance = await session.scalar(select(LeaveBalance).where(LeaveBalance.employee_id == employee_id, LeaveBalance.leave_type_id == leave_type_id, LeaveBalance.year == year))
    quota = balance.quota if balance else Decimal("0")
    query = select(LeaveRequest).where(LeaveRequest.employee_id == employee_id, LeaveRequest.leave_type_id == leave_type_id, LeaveRequest.status.in_([LeaveStatus.PENDING, LeaveStatus.APPROVED]), LeaveRequest.start_date.between(date(year, 1, 1), date(year, 12, 31)))
    requests = (await session.scalars(query)).all()
    used = sum((row.days for row in requests if row.id != pending_exclude_id), Decimal("0"))
    return quota - used
