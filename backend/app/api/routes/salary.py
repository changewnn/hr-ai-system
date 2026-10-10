from calendar import monthrange
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdminUser, CurrentActiveUser
from app.common.errors import BusinessError
from app.common.responses import success
from app.db.session import get_db
from app.models.entities import AttendanceRecord, AttendanceRule, AttendanceStatus, Employee, EmployeeStatus, MessageType, SalaryConfig, SalaryRecord, SalaryStatus, User
from app.models.support import Message, SalaryAdjustment
from app.models.tax import TaxBracket
from app.schemas.salary import SalaryAdjustmentCreate, SalaryConfigCreate, SalaryMonthRequest
from app.services.audit import record_audit
from app.services.attendance import business_now
from app.services.salary import calculate_salary

router = APIRouter(prefix="/salary", tags=["salary"])


def _record_dict(row: SalaryRecord) -> dict:
    return {"id": row.id, "employee_id": row.employee_id, "month": row.month, "base_salary": str(row.base_salary), "allowance": str(row.allowance), "attendance_deduct": str(row.attendance_deduct), "social_security": str(row.social_security), "housing_fund": str(row.housing_fund), "tax": str(row.tax), "gross_salary": str(row.gross_salary), "net_salary": str(row.net_salary), "status": row.status.value, "published_at": row.published_at}


def _month_range(month: str) -> tuple[date, date]:
    start = date.fromisoformat(f"{month}-01")
    return start, date(start.year, start.month, monthrange(start.year, start.month)[1])


@router.get("/config")
async def get_configs(_: AdminUser, session: AsyncSession = Depends(get_db), employee_id: int | None = None) -> dict:
    query = select(SalaryConfig).order_by(SalaryConfig.employee_id, SalaryConfig.effective_date.desc())
    if employee_id is not None:
        query = query.where(SalaryConfig.employee_id == employee_id)
    rows = (await session.scalars(query)).all()
    return success([{"id": row.id, "employee_id": row.employee_id, "base_salary": str(row.base_salary), "allowance": str(row.allowance), "social_security": str(row.social_security), "housing_fund": str(row.housing_fund), "tax_threshold": str(row.tax_threshold), "effective_date": row.effective_date} for row in rows])


@router.put("/config")
async def set_config(payload: SalaryConfigCreate, current_user: AdminUser, session: AsyncSession = Depends(get_db)) -> dict:
    employee = await session.get(Employee, payload.employee_id)
    if employee is None:
        raise BusinessError(20006, "EMPLOYEE_NOT_FOUND", "员工不存在", 404)
    row = await session.scalar(select(SalaryConfig).where(SalaryConfig.employee_id == payload.employee_id, SalaryConfig.effective_date == payload.effective_date))
    before = None
    if row is None:
        row = SalaryConfig(employee_id=payload.employee_id, effective_date=payload.effective_date)
        session.add(row)
    else:
        before = {"base_salary": str(row.base_salary), "allowance": str(row.allowance)}
    for field in ("base_salary", "allowance", "social_security", "housing_fund", "tax_threshold"):
        setattr(row, field, getattr(payload, field))
    await session.flush()
    await record_audit(session, actor_user_id=current_user.id, action="SALARY_CONFIG_UPDATE", resource_type="salary_config", resource_id=str(row.id), before=before, after={"employee_id": row.employee_id, "base_salary": str(row.base_salary), "effective_date": str(row.effective_date)})
    await session.commit()
    return success({"id": row.id}, message="薪酬档案保存成功")


@router.post("/calculate")
async def calculate(payload: SalaryMonthRequest, current_user: AdminUser, session: AsyncSession = Depends(get_db)) -> dict:
    start, end = _month_range(payload.month)
    employees = (await session.scalars(select(Employee).where(Employee.deleted_at.is_(None), Employee.status == EmployeeStatus.ACTIVE).order_by(Employee.id))).all()
    rule = await session.scalar(select(AttendanceRule).limit(1))
    if rule is None:
        raise BusinessError(50002, "SALARY_CALCULATION_INVALID", "未配置考勤规则", 409)
    brackets = list((await session.scalars(select(TaxBracket).where(TaxBracket.enabled.is_(True)).order_by(TaxBracket.sort_order))).all())
    if not brackets:
        raise BusinessError(50002, "SALARY_CALCULATION_INVALID", "未配置个税税率表", 409)
    records: list[dict] = []
    for employee in employees:
        config = await session.scalar(select(SalaryConfig).where(SalaryConfig.employee_id == employee.id, SalaryConfig.effective_date <= end).order_by(SalaryConfig.effective_date.desc()).limit(1))
        if config is None:
            raise BusinessError(50001, "SALARY_CONFIG_NOT_FOUND", f"员工 {employee.employee_no} 缺少有效薪酬档案", 409)
        attendance = (await session.scalars(select(AttendanceRecord).where(AttendanceRecord.employee_id == employee.id, AttendanceRecord.work_date.between(start, end)))).all()
        effective_end = min(end, business_now().date())
        expected_start = max(start, employee.hire_date)
        expected_days = 0
        if expected_start <= effective_end:
            cursor = expected_start
            while cursor <= effective_end:
                if cursor.isoweekday() in rule.work_days:
                    expected_days += 1
                cursor = date.fromordinal(cursor.toordinal() + 1)
        non_absent_dates = {item.work_date for item in attendance if item.status in (AttendanceStatus.NORMAL, AttendanceStatus.LATE, AttendanceStatus.EARLY_LEAVE, AttendanceStatus.LEAVE)}
        absent_days = Decimal(max(0, expected_days - len(non_absent_dates)))
        late_early_count = sum(1 for item in attendance if item.status in (AttendanceStatus.LATE, AttendanceStatus.EARLY_LEAVE))
        values = calculate_salary(config, absent_days, late_early_count, rule.single_deduct, brackets)
        row = await session.scalar(select(SalaryRecord).where(SalaryRecord.employee_id == employee.id, SalaryRecord.month == payload.month))
        if row is not None and row.status == SalaryStatus.PUBLISHED:
            records.append(_record_dict(row))
            continue
        if row is None:
            row = SalaryRecord(employee_id=employee.id, month=payload.month, status=SalaryStatus.DRAFT, **values)
            session.add(row)
        else:
            for field, value in values.items():
                setattr(row, field, value)
        await session.flush()
        records.append(_record_dict(row))
    await record_audit(session, actor_user_id=current_user.id, action="SALARY_CALCULATE", resource_type="salary_record", resource_id=payload.month, after={"count": len(records)})
    await session.commit()
    return success(records, message="月度薪酬试算完成")


@router.post("/publish")
async def publish(payload: SalaryMonthRequest, current_user: AdminUser, session: AsyncSession = Depends(get_db)) -> dict:
    rows = (await session.scalars(select(SalaryRecord).where(SalaryRecord.month == payload.month, SalaryRecord.status == SalaryStatus.DRAFT).with_for_update())).all()
    if not rows:
        raise BusinessError(50004, "SALARY_DRAFT_NOT_FOUND", "没有可发布的工资条草稿", 404)
    published_at = datetime.now(timezone.utc)
    for row in rows:
        row.status = SalaryStatus.PUBLISHED
        row.published_at = published_at
        recipient_id = await session.scalar(select(User.id).where(User.employee_id == row.employee_id))
        if recipient_id is not None:
            session.add(Message(recipient_user_id=recipient_id, type=MessageType.SALARY_PUBLISHED, title="工资条已发布", content=f"{payload.month} 月工资条已发布", related_id=row.id))
    await record_audit(session, actor_user_id=current_user.id, action="SALARY_PUBLISH", resource_type="salary_record", resource_id=payload.month, after={"count": len(rows)})
    await session.commit()
    return success({"count": len(rows)}, message="工资条发布成功")


@router.get("/records")
async def admin_records(_: AdminUser, session: AsyncSession = Depends(get_db), month: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")) -> dict:
    rows = (await session.scalars(select(SalaryRecord).where(SalaryRecord.month == month).order_by(SalaryRecord.employee_id))).all()
    return success([_record_dict(row) for row in rows])


@router.get("/mine")
async def mine(current_user: CurrentActiveUser, session: AsyncSession = Depends(get_db), month: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")) -> dict:
    if current_user.employee_id is None:
        raise BusinessError(10007, "RESOURCE_NOT_FOUND", "当前账号未绑定员工档案", 404)
    query = select(SalaryRecord).where(SalaryRecord.employee_id == current_user.employee_id, SalaryRecord.status == SalaryStatus.PUBLISHED)
    if month:
        query = query.where(SalaryRecord.month == month)
    rows = (await session.scalars(query.order_by(SalaryRecord.month.desc()))).all()
    return success([_record_dict(row) for row in rows])


@router.post("/adjustments")
async def create_adjustment(payload: SalaryAdjustmentCreate, current_user: AdminUser, session: AsyncSession = Depends(get_db)) -> dict:
    salary = await session.get(SalaryRecord, payload.salary_record_id)
    if salary is None or salary.status != SalaryStatus.PUBLISHED:
        raise BusinessError(50005, "SALARY_ADJUSTMENT_INVALID", "只有已发布工资条可以创建补发记录", 409)
    row = SalaryAdjustment(salary_record_id=salary.id, amount=payload.amount, reason=payload.reason, status=SalaryStatus.DRAFT, approved_by=current_user.id)
    session.add(row)
    await session.flush()
    await record_audit(session, actor_user_id=current_user.id, action="SALARY_ADJUSTMENT_CREATE", resource_type="salary_adjustment", resource_id=str(row.id), after={"amount": str(row.amount), "reason": row.reason})
    await session.commit()
    return success({"id": row.id}, message="补发记录创建成功")
