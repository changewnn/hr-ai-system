from calendar import monthrange
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdminUser, CurrentActiveUser, ManagerOrAdminUser
from app.common.errors import BusinessError
from app.common.responses import success
from app.db.session import get_db
from app.models.entities import AttendanceRecord, AttendanceStatus, AttendanceRule, Employee, EmployeeStatus, Role
from app.schemas.attendance import AttendanceAdjustRequest, AttendanceRuleUpdate
from app.services.attendance import business_now, classify_status, is_workday, validate_work_days
from app.services.audit import record_audit

router = APIRouter(prefix="/attendance", tags=["attendance"])


async def _rule(session: AsyncSession) -> AttendanceRule:
    rule = await session.scalar(select(AttendanceRule).limit(1))
    if rule is None:
        rule = AttendanceRule()
        session.add(rule)
        await session.flush()
    return rule


def _record_dict(row: AttendanceRecord) -> dict:
    return {"id": row.id, "employee_id": row.employee_id, "work_date": row.work_date, "check_in_time": row.check_in_time, "check_out_time": row.check_out_time, "status": row.status.value, "adjust_note": row.adjust_note}


@router.get("/rule")
async def get_rule(_: AdminUser, session: AsyncSession = Depends(get_db)) -> dict:
    rule = await _rule(session)
    return success({"id": rule.id, "work_start_time": rule.work_start_time, "work_end_time": rule.work_end_time, "late_threshold": rule.late_threshold, "early_leave_threshold": rule.early_leave_threshold, "work_days": rule.work_days, "single_deduct": str(rule.single_deduct)})


@router.put("/rule")
async def update_rule(payload: AttendanceRuleUpdate, current_user: AdminUser, session: AsyncSession = Depends(get_db)) -> dict:
    validate_work_days(payload.work_days)
    if payload.work_end_time <= payload.work_start_time:
        raise BusinessError(30004, "ATTENDANCE_TIME_RANGE_INVALID", "下班时间必须晚于上班时间", 400)
    rule = await _rule(session)
    before = {"work_start_time": str(rule.work_start_time), "work_end_time": str(rule.work_end_time), "work_days": rule.work_days}
    for field in ("work_start_time", "work_end_time", "late_threshold", "early_leave_threshold", "work_days", "single_deduct"):
        setattr(rule, field, getattr(payload, field))
    await record_audit(session, actor_user_id=current_user.id, action="ATTENDANCE_RULE_UPDATE", resource_type="attendance_rule", resource_id=str(rule.id), before=before, after={"work_start_time": str(rule.work_start_time), "work_end_time": str(rule.work_end_time), "work_days": rule.work_days})
    await session.commit()
    return success(message="考勤规则更新成功")


async def _employee_for_user(session: AsyncSession, current_user) -> Employee:
    if current_user.employee_id is None:
        raise BusinessError(10007, "RESOURCE_NOT_FOUND", "当前账号未绑定员工档案", 404)
    employee = await session.get(Employee, current_user.employee_id)
    if employee is None or employee.status != EmployeeStatus.ACTIVE:
        raise BusinessError(30005, "ATTENDANCE_NOT_ALLOWED", "当前员工状态不允许打卡", 400)
    return employee


async def _check_in_or_out(current_user, session: AsyncSession, is_check_in: bool) -> dict:
    employee = await _employee_for_user(session, current_user)
    rule = await _rule(session)
    now = business_now()
    work_date = now.date()
    if not is_workday(work_date, rule.work_days):
        raise BusinessError(30001, "ATTENDANCE_NOT_ALLOWED", "非工作日不允许打卡", 400)
    row = await session.scalar(select(AttendanceRecord).where(AttendanceRecord.employee_id == employee.id, AttendanceRecord.work_date == work_date))
    if row is None:
        row = AttendanceRecord(employee_id=employee.id, work_date=work_date, status=AttendanceStatus.MISSING)
        session.add(row)
    if is_check_in:
        if row.check_in_time is None or now.astimezone(timezone.utc) < row.check_in_time:
            row.check_in_time = now.astimezone(timezone.utc)
    else:
        if row.check_out_time is None or now.astimezone(timezone.utc) > row.check_out_time:
            row.check_out_time = now.astimezone(timezone.utc)
    row.status = classify_status(row.check_in_time, row.check_out_time, rule)
    await session.commit()
    return _record_dict(row)


@router.post("/check-in")
async def check_in(current_user: CurrentActiveUser, session: AsyncSession = Depends(get_db)) -> dict:
    return success(await _check_in_or_out(current_user, session, True), message="上班打卡成功")


@router.post("/check-out")
async def check_out(current_user: CurrentActiveUser, session: AsyncSession = Depends(get_db)) -> dict:
    return success(await _check_in_or_out(current_user, session, False), message="下班打卡成功")


@router.get("/records")
async def records(current_user: CurrentActiveUser, session: AsyncSession = Depends(get_db), month: str = Query(..., pattern=r"^\d{4}-\d{2}$"), employee_id: int | None = None) -> dict:
    target_id = current_user.employee_id if current_user.role == Role.EMPLOYEE else employee_id
    if target_id is None:
        raise BusinessError(30006, "ATTENDANCE_EMPLOYEE_REQUIRED", "请指定员工", 400)
    if current_user.role == Role.EMPLOYEE and target_id != current_user.employee_id:
        raise BusinessError(10006, "PERMISSION_DENIED", "员工只能查看本人考勤", 403)
    if current_user.role == Role.MANAGER:
        manager = await session.get(Employee, current_user.employee_id) if current_user.employee_id else None
        target = await session.get(Employee, target_id)
        if manager is None or target is None or manager.department_id != target.department_id:
            raise BusinessError(10006, "PERMISSION_DENIED", "主管只能查看本部门员工考勤", 403)
    start = date.fromisoformat(f"{month}-01")
    end = date(start.year, start.month, monthrange(start.year, start.month)[1])
    rows = (await session.scalars(select(AttendanceRecord).where(AttendanceRecord.employee_id == target_id, AttendanceRecord.work_date.between(start, end)).order_by(AttendanceRecord.work_date))).all()
    return success([_record_dict(row) for row in rows])


@router.get("/summary")
async def summary(current_user: ManagerOrAdminUser, session: AsyncSession = Depends(get_db), month: str = Query(..., pattern=r"^\d{4}-\d{2}$")) -> dict:
    start = date.fromisoformat(f"{month}-01")
    end = date(start.year, start.month, monthrange(start.year, start.month)[1])
    query = select(AttendanceRecord).where(AttendanceRecord.work_date.between(start, end))
    if current_user.role == Role.MANAGER:
        manager = await session.get(Employee, current_user.employee_id) if current_user.employee_id else None
        if manager is None:
            raise BusinessError(10007, "RESOURCE_NOT_FOUND", "主管未绑定员工档案", 404)
        query = query.join(Employee, Employee.id == AttendanceRecord.employee_id).where(Employee.department_id == manager.department_id)
    rows = (await session.scalars(query)).all()
    grouped: dict[int, dict] = {}
    for row in rows:
        item = grouped.setdefault(row.employee_id, {"employee_id": row.employee_id, "attendance_days": 0, "late_count": 0, "early_leave_count": 0, "leave_days": 0, "absent_days": 0})
        if row.status == AttendanceStatus.NORMAL:
            item["attendance_days"] += 1
        elif row.status == AttendanceStatus.LATE:
            item["late_count"] += 1
            item["attendance_days"] += 1
        elif row.status == AttendanceStatus.EARLY_LEAVE:
            item["early_leave_count"] += 1
            item["attendance_days"] += 1
        elif row.status == AttendanceStatus.LEAVE:
            item["leave_days"] += 1
        elif row.status == AttendanceStatus.MISSING:
            item["absent_days"] += 1
    return success(list(grouped.values()))


@router.patch("/records/{record_id}/adjust")
async def adjust(record_id: int, payload: AttendanceAdjustRequest, current_user: AdminUser, session: AsyncSession = Depends(get_db)) -> dict:
    try:
        status = AttendanceStatus(payload.status)
    except ValueError as exc:
        raise BusinessError(30007, "ATTENDANCE_STATUS_INVALID", "考勤状态无效", 400) from exc
    row = await session.get(AttendanceRecord, record_id)
    if row is None:
        raise BusinessError(30008, "ATTENDANCE_RECORD_NOT_FOUND", "考勤记录不存在", 404)
    before = _record_dict(row)
    row.status = status
    row.adjust_note = payload.adjust_note
    row.adjusted_by = current_user.id
    await record_audit(session, actor_user_id=current_user.id, action="ATTENDANCE_ADJUST", resource_type="attendance_record", resource_id=str(row.id), before=before, after=_record_dict(row))
    await session.commit()
    return success(_record_dict(row), message="考勤记录调整成功")
