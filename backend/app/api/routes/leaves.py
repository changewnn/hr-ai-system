from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdminUser, CurrentActiveUser, ManagerOrAdminUser
from app.common.errors import BusinessError
from app.common.responses import success
from app.db.session import get_db
from app.models.entities import ActiveStatus, ApprovalAction, AttendanceRecord, AttendanceStatus, Department, Employee, EmployeeStatus, LeaveApproval, LeaveRequest, LeaveStatus, LeaveType, MessageType, Role, User
from app.models.support import Message
from app.models.leave_balance import LeaveBalance
from app.schemas.leave import LeaveApprovalRequest, LeaveBalanceUpdate, LeaveRequestCreate, LeaveTypeCreate, LeaveTypeUpdate
from app.services.attendance import business_now
from app.services.audit import record_audit
from app.services.leave import annual_remaining, calculate_leave_days, get_work_days, validate_leave_type, working_dates

router = APIRouter(prefix="/leaves", tags=["leaves"])


def _request_dict(row: LeaveRequest, approval: LeaveApproval | None = None) -> dict:
    return {"id": row.id, "request_no": row.request_no, "employee_id": row.employee_id, "leave_type_id": row.leave_type_id, "start_date": row.start_date, "end_date": row.end_date, "start_period": row.start_period, "end_period": row.end_period, "days": str(row.days), "reason": row.reason, "status": row.status.value, "approval": {"approver_id": approval.approver_id, "action": approval.action.value, "comment": approval.comment, "created_at": approval.created_at} if approval else None}


async def _employee(current_user, session: AsyncSession) -> Employee:
    if current_user.employee_id is None:
        raise BusinessError(10007, "RESOURCE_NOT_FOUND", "当前账号未绑定员工档案", 404)
    employee = await session.get(Employee, current_user.employee_id)
    if employee is None or employee.status != EmployeeStatus.ACTIVE:
        raise BusinessError(30005, "ATTENDANCE_NOT_ALLOWED", "当前员工状态无权提交请假", 403)
    return employee


async def _overlap(session: AsyncSession, employee_id: int, start: date, end: date, exclude_id: int | None = None) -> bool:
    query = select(LeaveRequest).where(LeaveRequest.employee_id == employee_id, LeaveRequest.status.in_([LeaveStatus.DRAFT, LeaveStatus.PENDING, LeaveStatus.APPROVED]), LeaveRequest.start_date <= end, LeaveRequest.end_date >= start)
    rows = (await session.scalars(query)).all()
    return any(row.id != exclude_id for row in rows)


@router.get("/types")
async def list_leave_types(_: CurrentActiveUser, session: AsyncSession = Depends(get_db)) -> dict:
    rows = (await session.scalars(select(LeaveType).where(LeaveType.status == ActiveStatus.ACTIVE).order_by(LeaveType.id))).all()
    return success([{"id": row.id, "name": row.name, "code": row.code, "days_per_year": str(row.days_per_year) if row.days_per_year is not None else None} for row in rows])


@router.post("/types")
async def create_leave_type(payload: LeaveTypeCreate, current_user: AdminUser, session: AsyncSession = Depends(get_db)) -> dict:
    code = payload.code.strip().upper()
    if await session.scalar(select(LeaveType).where(or_(LeaveType.code == code, LeaveType.name == payload.name.strip()))):
        raise BusinessError(40009, "LEAVE_TYPE_EXISTS", "请假类型已存在", 409)
    row = LeaveType(name=payload.name.strip(), code=code, days_per_year=payload.days_per_year)
    session.add(row)
    await session.flush()
    await record_audit(session, actor_user_id=current_user.id, action="LEAVE_TYPE_CREATE", resource_type="leave_type", resource_id=str(row.id))
    await session.commit()
    return success({"id": row.id}, message="请假类型创建成功")


@router.put("/types/{leave_type_id}")
async def update_leave_type(leave_type_id: int, payload: LeaveTypeUpdate, current_user: AdminUser, session: AsyncSession = Depends(get_db)) -> dict:
    row = await session.get(LeaveType, leave_type_id)
    if row is None:
        raise BusinessError(40008, "LEAVE_TYPE_NOT_FOUND", "请假类型不存在", 404)
    if payload.name is not None:
        row.name = payload.name.strip()
    if payload.days_per_year is not None:
        row.days_per_year = payload.days_per_year
    if payload.enabled is not None:
        row.status = ActiveStatus.ACTIVE if payload.enabled else ActiveStatus.INACTIVE
    await record_audit(session, actor_user_id=current_user.id, action="LEAVE_TYPE_UPDATE", resource_type="leave_type", resource_id=str(row.id), after={"name": row.name, "status": row.status.value})
    await session.commit()
    return success(message="请假类型更新成功")


@router.put("/balances")
async def set_balance(payload: LeaveBalanceUpdate, current_user: AdminUser, session: AsyncSession = Depends(get_db)) -> dict:
    await validate_leave_type(session, payload.leave_type_id)
    employee = await session.get(Employee, payload.employee_id)
    if employee is None:
        raise BusinessError(20006, "EMPLOYEE_NOT_FOUND", "员工不存在", 404)
    row = await session.scalar(select(LeaveBalance).where(LeaveBalance.employee_id == payload.employee_id, LeaveBalance.leave_type_id == payload.leave_type_id, LeaveBalance.year == payload.year))
    if row is None:
        row = LeaveBalance(employee_id=payload.employee_id, leave_type_id=payload.leave_type_id, year=payload.year, quota=payload.quota)
        session.add(row)
    else:
        row.quota = payload.quota
    await record_audit(session, actor_user_id=current_user.id, action="LEAVE_BALANCE_UPDATE", resource_type="leave_balance", resource_id=str(row.id if row.id else payload.employee_id), after={"quota": str(payload.quota), "year": payload.year})
    await session.commit()
    return success(message="请假额度更新成功")


@router.post("")
async def create_leave(payload: LeaveRequestCreate, current_user: CurrentActiveUser, session: AsyncSession = Depends(get_db)) -> dict:
    employee = await _employee(current_user, session)
    today = business_now().date()
    if payload.start_date < today:
        raise BusinessError(40001, "LEAVE_DATE_IN_PAST", "请假日期早于当前日期", 400)
    leave_type = await validate_leave_type(session, payload.leave_type_id)
    work_days = await get_work_days(session)
    days = calculate_leave_days(payload.start_date, payload.end_date, payload.start_period, payload.end_period, work_days)
    if await _overlap(session, employee.id, payload.start_date, payload.end_date):
        raise BusinessError(40003, "LEAVE_OVERLAP", "请假时间与已有申请重叠", 409)
    if leave_type.code == "ANNUAL":
        remaining = await annual_remaining(session, employee.id, leave_type.id, payload.start_date.year)
        if remaining < days:
            raise BusinessError(40004, "LEAVE_BALANCE_INSUFFICIENT", f"年假余额不足，剩余 {remaining} 天", 409)
    request_no = f"L{business_now().strftime('%Y%m%d%H%M%S%f')}"
    row = LeaveRequest(request_no=request_no, employee_id=employee.id, leave_type_id=leave_type.id, start_date=payload.start_date, end_date=payload.end_date, start_period=payload.start_period, end_period=payload.end_period, days=days, reason=payload.reason, status=LeaveStatus.PENDING)
    session.add(row)
    await session.flush()
    approver: User | None = None
    department = await session.get(Department, employee.department_id)
    if department and department.leader_id:
        approver = await session.scalar(select(User).where(User.employee_id == department.leader_id, User.status == ActiveStatus.ACTIVE))
    if approver is None or approver.id == current_user.id:
        approver = await session.scalar(select(User).where(User.role == Role.ADMIN, User.status == ActiveStatus.ACTIVE).order_by(User.id).limit(1))
    if approver is None:
        raise BusinessError(40005, "LEAVE_APPROVER_NOT_FOUND", "未找到有效审批人", 409)
    session.add(Message(recipient_user_id=approver.id, type=MessageType.APPROVAL_TODO, title="新的请假审批", content=f"员工 {employee.name} 提交了请假申请", related_id=row.id))
    await record_audit(session, actor_user_id=current_user.id, action="LEAVE_SUBMIT", resource_type="leave_request", resource_id=str(row.id), after={"status": row.status.value, "days": str(days)})
    await session.commit()
    return success(_request_dict(row), message="请假申请已提交")


@router.get("/my")
async def my_leaves(current_user: CurrentActiveUser, session: AsyncSession = Depends(get_db)) -> dict:
    employee = await _employee(current_user, session)
    rows = (await session.scalars(select(LeaveRequest).where(LeaveRequest.employee_id == employee.id).order_by(LeaveRequest.id.desc()))).all()
    return success([_request_dict(row) for row in rows])


@router.get("/pending")
async def pending(current_user: ManagerOrAdminUser, session: AsyncSession = Depends(get_db)) -> dict:
    query = select(LeaveRequest).where(LeaveRequest.status == LeaveStatus.PENDING)
    if current_user.role == Role.MANAGER:
        manager = await session.get(Employee, current_user.employee_id) if current_user.employee_id else None
        if manager is None:
            raise BusinessError(10007, "RESOURCE_NOT_FOUND", "主管未绑定员工档案", 404)
        department = await session.get(Department, manager.department_id)
        if department is None or department.leader_id != manager.id:
            raise BusinessError(40007, "LEAVE_APPROVAL_FORBIDDEN", "当前用户不是本部门审批人", 403)
        query = query.join(Employee, Employee.id == LeaveRequest.employee_id).where(Employee.department_id == manager.department_id)
    rows = (await session.scalars(query.order_by(LeaveRequest.id))).all()
    return success([_request_dict(row) for row in rows])


@router.get("/review")
async def review_history(current_user: ManagerOrAdminUser, session: AsyncSession = Depends(get_db), status: LeaveStatus | None = None) -> dict:
    query = select(LeaveRequest)
    if status is not None:
        query = query.where(LeaveRequest.status == status)
    if current_user.role == Role.MANAGER:
        manager = await session.get(Employee, current_user.employee_id) if current_user.employee_id else None
        if manager is None:
            raise BusinessError(10007, "RESOURCE_NOT_FOUND", "主管未绑定员工档案", 404)
        query = query.join(Employee, Employee.id == LeaveRequest.employee_id).where(Employee.department_id == manager.department_id)
    rows = (await session.scalars(query.order_by(LeaveRequest.id.desc()))).all()
    result = []
    for row in rows:
        approval = await session.scalar(select(LeaveApproval).where(LeaveApproval.leave_request_id == row.id).order_by(LeaveApproval.id.desc()).limit(1))
        result.append(_request_dict(row, approval))
    return success(result)


@router.get("/{request_id}")
async def leave_detail(request_id: int, current_user: ManagerOrAdminUser, session: AsyncSession = Depends(get_db)) -> dict:
    row = await session.get(LeaveRequest, request_id)
    if row is None:
        raise BusinessError(10007, "RESOURCE_NOT_FOUND", "请假申请不存在", 404)
    if current_user.role == Role.MANAGER:
        manager = await session.get(Employee, current_user.employee_id) if current_user.employee_id else None
        employee = await session.get(Employee, row.employee_id)
        if manager is None or employee is None or manager.department_id != employee.department_id:
            raise BusinessError(40007, "LEAVE_APPROVAL_FORBIDDEN", "只能查看本部门请假申请", 403)
    approval = await session.scalar(select(LeaveApproval).where(LeaveApproval.leave_request_id == row.id).order_by(LeaveApproval.id.desc()).limit(1))
    return success(_request_dict(row, approval))


@router.post("/{request_id}/cancel")
async def cancel(request_id: int, current_user: CurrentActiveUser, session: AsyncSession = Depends(get_db)) -> dict:
    employee = await _employee(current_user, session)
    row = await session.get(LeaveRequest, request_id)
    if row is None or row.employee_id != employee.id:
        raise BusinessError(10007, "RESOURCE_NOT_FOUND", "请假申请不存在", 404)
    if row.status != LeaveStatus.PENDING:
        raise BusinessError(40006, "LEAVE_INVALID_TRANSITION", "只有待审批申请可以撤销", 409)
    row.status = LeaveStatus.CANCELLED
    await record_audit(session, actor_user_id=current_user.id, action="LEAVE_CANCEL", resource_type="leave_request", resource_id=str(row.id), after={"status": row.status.value})
    await session.commit()
    return success(message="请假申请已撤销")


@router.post("/{request_id}/approve")
async def approve(request_id: int, payload: LeaveApprovalRequest, current_user: ManagerOrAdminUser, session: AsyncSession = Depends(get_db)) -> dict:
    row = await session.get(LeaveRequest, request_id)
    if row is None:
        raise BusinessError(10007, "RESOURCE_NOT_FOUND", "请假申请不存在", 404)
    if row.status != LeaveStatus.PENDING:
        raise BusinessError(40006, "LEAVE_INVALID_TRANSITION", "当前状态不允许审批", 409)
    employee = await session.get(Employee, row.employee_id)
    if employee is None:
        raise BusinessError(20006, "EMPLOYEE_NOT_FOUND", "员工不存在", 404)
    if current_user.role == Role.MANAGER:
        manager = await session.get(Employee, current_user.employee_id) if current_user.employee_id else None
        if manager is None or manager.department_id != employee.department_id:
            raise BusinessError(40007, "LEAVE_APPROVAL_FORBIDDEN", "主管只能审批本部门申请", 403)
        department = await session.get(Department, employee.department_id)
        if department is None or department.leader_id != current_user.employee_id:
            raise BusinessError(40007, "LEAVE_APPROVAL_FORBIDDEN", "当前用户不是本部门审批人", 403)
    action_approve = payload.action == "APPROVE"
    row.status = LeaveStatus.APPROVED if action_approve else LeaveStatus.REJECTED
    session.add(LeaveApproval(leave_request_id=row.id, approver_id=current_user.id, action=ApprovalAction(payload.action), comment=payload.comment))
    if action_approve:
        work_days = await get_work_days(session)
        for work_date in working_dates(row.start_date, row.end_date, work_days):
            record = await session.scalar(select(AttendanceRecord).where(AttendanceRecord.employee_id == row.employee_id, AttendanceRecord.work_date == work_date))
            if record is None:
                record = AttendanceRecord(employee_id=row.employee_id, work_date=work_date, status=AttendanceStatus.LEAVE)
                session.add(record)
            elif not record.adjust_note:
                record.status = AttendanceStatus.LEAVE
        recipient_id = await session.scalar(select(User.id).where(User.employee_id == row.employee_id))
        if recipient_id is not None:
            session.add(Message(recipient_user_id=recipient_id, type=MessageType.APPROVAL_RESULT, title="请假审批结果", content=f"你的请假申请已{'通过' if action_approve else '驳回'}", related_id=row.id))
    await record_audit(session, actor_user_id=current_user.id, action="LEAVE_APPROVE", resource_type="leave_request", resource_id=str(row.id), after={"status": row.status.value, "comment": payload.comment})
    await session.commit()
    return success(message="审批完成")
