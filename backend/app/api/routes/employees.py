from datetime import datetime, timezone
from io import BytesIO, StringIO

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdminUser, CurrentActiveUser
from app.common.crypto import decrypt_sensitive, encrypt_sensitive, mask_id_card
from app.common.errors import BusinessError
from app.common.responses import success
from app.db.session import get_db
from app.models.entities import ActiveStatus, Department, Employee, EmployeeStatus, Position, User
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.services.audit import record_audit

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("/export", include_in_schema=True)
async def export_employees_excel(_: AdminUser, session: AsyncSession = Depends(get_db)) -> StreamingResponse:
    rows = (await session.scalars(select(Employee).where(Employee.deleted_at.is_(None)).order_by(Employee.id))).all()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "员工档案"
    sheet.append(["工号", "姓名", "手机号", "部门ID", "岗位ID", "入职日期", "状态"])
    for row in rows:
        sheet.append([row.employee_no, row.name, row.phone, row.department_id, row.position_id, row.hire_date, row.status.value])
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=employees.xlsx"})


def _employee_dict(row: Employee, detail: bool = False) -> dict:
    id_card = decrypt_sensitive(row.id_card_encrypted)
    data = {"id": row.id, "employee_no": row.employee_no, "name": row.name, "gender": row.gender, "phone": row.phone, "email": row.email, "id_card": id_card if detail else mask_id_card(id_card), "department_id": row.department_id, "position_id": row.position_id, "hire_date": row.hire_date, "status": row.status.value, "emergency_contact": row.emergency_contact, "emergency_phone": row.emergency_phone}
    return data


async def _validate_refs(session: AsyncSession, department_id: int, position_id: int) -> None:
    department = await session.scalar(select(Department).where(Department.id == department_id, Department.deleted_at.is_(None)))
    position = await session.scalar(select(Position).where(Position.id == position_id, Position.deleted_at.is_(None)))
    if department is None:
        raise BusinessError(20008, "DEPARTMENT_PARENT_NOT_FOUND", "部门不存在", 404)
    if position is None:
        raise BusinessError(20012, "POSITION_NOT_FOUND", "岗位不存在", 404)


def _next_employee_no(existing: list[str]) -> str:
    prefix = f"E{datetime.now().strftime('%Y%m%d')}"
    numbers = [int(value[-3:]) for value in existing if value.startswith(prefix) and value[-3:].isdigit()]
    return f"{prefix}{max(numbers, default=0) + 1:03d}"


@router.get("")
async def list_employees(_: AdminUser, session: AsyncSession = Depends(get_db), department_id: int | None = None, status: EmployeeStatus | None = None, keyword: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)) -> dict:
    conditions = [Employee.deleted_at.is_(None)]
    if department_id is not None:
        conditions.append(Employee.department_id == department_id)
    if status is not None:
        conditions.append(Employee.status == status)
    if keyword:
        term = f"%{keyword.strip()}%"
        conditions.append(or_(Employee.name.ilike(term), Employee.employee_no.ilike(term), Employee.phone.ilike(term)))
    total = await session.scalar(select(func.count()).select_from(Employee).where(*conditions))
    rows = (await session.scalars(select(Employee).where(*conditions).order_by(Employee.id.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    return success({"items": [_employee_dict(row) for row in rows], "page": page, "page_size": page_size, "total": total or 0})


@router.get("/me")
async def get_my_employee(current_user: CurrentActiveUser, session: AsyncSession = Depends(get_db)) -> dict:
    if current_user.employee_id is None:
        raise BusinessError(20006, "EMPLOYEE_PROFILE_NOT_BOUND", "当前账号未绑定员工档案", 403)
    row = await session.scalar(select(Employee).where(Employee.id == current_user.employee_id, Employee.deleted_at.is_(None)))
    if row is None:
        raise BusinessError(20006, "EMPLOYEE_NOT_FOUND", "员工档案不存在", 404)
    return success(_employee_dict(row, detail=True))


@router.get("/{employee_id}")
async def get_employee(employee_id: int, _: AdminUser, session: AsyncSession = Depends(get_db)) -> dict:
    row = await session.scalar(select(Employee).where(Employee.id == employee_id, Employee.deleted_at.is_(None)))
    if row is None:
        raise BusinessError(20006, "EMPLOYEE_NOT_FOUND", "员工不存在", 404)
    return success(_employee_dict(row, detail=True))


@router.post("")
async def create_employee(payload: EmployeeCreate, current_user: AdminUser, session: AsyncSession = Depends(get_db)) -> dict:
    await _validate_refs(session, payload.department_id, payload.position_id)
    existing = list((await session.scalars(select(Employee.employee_no))).all())
    row = Employee(employee_no=_next_employee_no(existing), name=payload.name.strip(), gender=payload.gender, phone=payload.phone, email=str(payload.email) if payload.email else None, id_card_encrypted=encrypt_sensitive(payload.id_card), department_id=payload.department_id, position_id=payload.position_id, hire_date=payload.hire_date, emergency_contact=payload.emergency_contact, emergency_phone=payload.emergency_phone)
    session.add(row)
    await session.flush()
    await record_audit(session, actor_user_id=current_user.id, action="EMPLOYEE_CREATE", resource_type="employee", resource_id=str(row.id), after={"employee_no": row.employee_no, "name": row.name, "department_id": row.department_id, "position_id": row.position_id})
    await session.commit()
    return success({"id": row.id, "employee_no": row.employee_no}, message="员工创建成功")


@router.put("/{employee_id}")
async def update_employee(employee_id: int, payload: EmployeeUpdate, current_user: AdminUser, session: AsyncSession = Depends(get_db)) -> dict:
    row = await session.scalar(select(Employee).where(Employee.id == employee_id, Employee.deleted_at.is_(None)))
    if row is None:
        raise BusinessError(20006, "EMPLOYEE_NOT_FOUND", "员工不存在", 404)
    department_id = payload.department_id if payload.department_id is not None else row.department_id
    position_id = payload.position_id if payload.position_id is not None else row.position_id
    await _validate_refs(session, department_id, position_id)
    before = _employee_dict(row, detail=False)
    for field in ("name", "gender", "phone", "email", "hire_date", "emergency_contact", "emergency_phone"):
        if field in payload.model_fields_set:
            value = getattr(payload, field)
            setattr(row, field, str(value) if field == "email" and value else value)
    if "id_card" in payload.model_fields_set:
        row.id_card_encrypted = encrypt_sensitive(payload.id_card)
    row.department_id = department_id
    row.position_id = position_id
    await record_audit(session, actor_user_id=current_user.id, action="EMPLOYEE_UPDATE", resource_type="employee", resource_id=str(row.id), before=before, after=_employee_dict(row, detail=False))
    await session.commit()
    return success(message="员工更新成功")


@router.post("/{employee_id}/resign")
async def resign_employee(employee_id: int, current_user: AdminUser, session: AsyncSession = Depends(get_db)) -> dict:
    row = await session.scalar(select(Employee).where(Employee.id == employee_id, Employee.deleted_at.is_(None)))
    if row is None:
        raise BusinessError(20006, "EMPLOYEE_NOT_FOUND", "员工不存在", 404)
    row.status = EmployeeStatus.RESIGNED
    account = await session.scalar(select(User).where(User.employee_id == row.id))
    if account is not None:
        account.status = ActiveStatus.INACTIVE
    await record_audit(session, actor_user_id=current_user.id, action="EMPLOYEE_RESIGN", resource_type="employee", resource_id=str(row.id), after={"status": row.status.value})
    await session.commit()
    return success(message="员工已离职")


@router.get("/export-csv")
async def export_employees(_: AdminUser, session: AsyncSession = Depends(get_db)) -> StreamingResponse:
    rows = (await session.scalars(select(Employee).where(Employee.deleted_at.is_(None)).order_by(Employee.id))).all()
    stream = StringIO()
    stream.write("工号,姓名,手机号,部门ID,岗位ID,入职日期,状态\n")
    for row in rows:
        stream.write(f"{row.employee_no},{row.name},{row.phone},{row.department_id},{row.position_id},{row.hire_date},{row.status.value}\n")
    stream.seek(0)
    return StreamingResponse(iter([stream.getvalue().encode("utf-8-sig")]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=employees.csv"})
