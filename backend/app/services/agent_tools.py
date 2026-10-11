from __future__ import annotations

import re
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.encoders import jsonable_encoder

from app.common.errors import BusinessError
from app.models.entities import AttendanceRecord, Employee, EmployeeStatus, LeaveRequest, LeaveStatus, LeaveType, SalaryRecord, SalaryStatus
from app.models.leave_balance import LeaveBalance
from app.models.support import AgentAction
from app.services.attendance import business_now
from app.services.leave import annual_remaining
from app.services.audit import record_audit

READ_TOOLS = {
    "my_attendance": "本人考勤",
    "my_leave_balance": "本人年假余额",
    "my_leave_records": "本人请假记录",
    "my_salary_slips": "本人已发布工资条",
    "my_profile": "本人档案",
}


def detect_tool(text: str) -> str | None:
    value = text.lower()
    if re.search(r"(工资|薪资|工资条)", value):
        return "my_salary_slips"
    if re.search(r"(年假|假期).{0,4}(余额|剩余)|余额", value):
        return "my_leave_balance"
    if re.search(r"(请假|休假).{0,5}(记录|历史|申请过)", value):
        return "my_leave_records"
    if re.search(r"(考勤|打卡).{0,5}(记录|情况|明细)?", value):
        return "my_attendance"
    if re.search(r"(个人|我的).{0,4}(档案|资料|信息)", value):
        return "my_profile"
    return None


def _employee_id(user) -> int:
    if user.employee_id is None:
        raise BusinessError(60002, "AGENT_EMPLOYEE_REQUIRED", "当前账号未绑定员工档案", 403)
    return user.employee_id


def _month(text: str) -> str:
    match = re.search(r"(20\d{2})[-年](\d{1,2})", text)
    now = business_now()
    return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}" if match else now.strftime("%Y-%m")


async def execute_read_tool(session: AsyncSession, user, tool_name: str, text: str) -> dict:
    employee_id = _employee_id(user)
    if tool_name == "my_attendance":
        month = _month(text)
        start = date.fromisoformat(f"{month}-01")
        end = date(start.year, start.month, monthrange(start.year, start.month)[1])
        rows = (await session.scalars(select(AttendanceRecord).where(AttendanceRecord.employee_id == employee_id, AttendanceRecord.work_date.between(start, end)).order_by(AttendanceRecord.work_date))).all()
        return {"tool": tool_name, "month": month, "items": [{"work_date": r.work_date, "check_in_time": r.check_in_time, "check_out_time": r.check_out_time, "status": r.status.value} for r in rows]}
    if tool_name == "my_leave_balance":
        year = int(_month(text)[:4])
        types = (await session.scalars(select(LeaveType).where(LeaveType.status == "ACTIVE").order_by(LeaveType.id))).all()
        return {"tool": tool_name, "year": year, "items": [{"leave_type": t.name, "code": t.code, "remaining_days": str(await annual_remaining(session, employee_id, t.id, year))} for t in types]}
    if tool_name == "my_leave_records":
        rows = (await session.scalars(select(LeaveRequest).where(LeaveRequest.employee_id == employee_id).order_by(LeaveRequest.id.desc()).limit(50))).all()
        return {"tool": tool_name, "items": [{"request_no": r.request_no, "start_date": r.start_date, "end_date": r.end_date, "days": str(r.days), "reason": r.reason, "status": r.status.value} for r in rows]}
    if tool_name == "my_salary_slips":
        month = _month(text)
        rows = (await session.scalars(select(SalaryRecord).where(SalaryRecord.employee_id == employee_id, SalaryRecord.status == SalaryStatus.PUBLISHED, SalaryRecord.month == month))).all()
        return {"tool": tool_name, "month": month, "items": [{"month": r.month, "gross_salary": str(r.gross_salary), "attendance_deduct": str(r.attendance_deduct), "social_security": str(r.social_security), "housing_fund": str(r.housing_fund), "tax": str(r.tax), "net_salary": str(r.net_salary), "published_at": r.published_at} for r in rows]}
    if tool_name == "my_profile":
        row = await session.get(Employee, employee_id)
        if row is None or row.status != EmployeeStatus.ACTIVE:
            raise BusinessError(60002, "AGENT_EMPLOYEE_REQUIRED", "员工档案不存在或已离职", 403)
        return {"tool": tool_name, "item": {"employee_no": row.employee_no, "name": row.name, "phone": row.phone, "email": row.email, "hire_date": row.hire_date, "status": row.status.value}}
    raise BusinessError(60003, "AGENT_TOOL_NOT_FOUND", "未注册的业务工具", 400)


def parse_leave_request(text: str) -> dict | None:
    if not re.search(r"(申请|提交|我要).{0,30}(请假|年假|病假|事假)|(?:请假|年假|病假|事假).{0,30}(申请|提交)", text):
        return None
    dates = re.findall(r"(20\d{2}[-年]\d{1,2}[-月]\d{1,2})", text)
    if len(dates) < 2:
        return {"missing": ["start_date", "end_date"]}
    def parse(value: str) -> str:
        return value.replace("年", "-").replace("月", "-").replace("日", "").replace("/", "-")
    reason = re.search(r"(?:原因|事由)[:：]?\s*(.+)$", text)
    code = "SICK" if "病假" in text else "PERSONAL" if "事假" in text else "ANNUAL"
    return {"start_date": parse(dates[0]), "end_date": parse(dates[1]), "reason": reason.group(1).strip() if reason else "Agent 提交请假", "leave_type_code": code}


async def create_confirmation(session: AsyncSession, user_id: int, conversation_id: int, args: dict) -> tuple[str, AgentAction]:
    token = token_urlsafe(32)
    action = AgentAction(conversation_id=conversation_id, user_id=user_id, tool_name="submit_leave", args=args, token_hash=sha256(token.encode()).hexdigest(), expires_at=datetime.now(timezone.utc) + timedelta(minutes=10), status="PENDING", created_at=datetime.utcnow())
    session.add(action)
    await session.flush()
    return token, action


async def execute_leave(session: AsyncSession, user, args: dict) -> dict:
    from app.api.routes.leaves import create_leave
    from app.schemas.leave import LeaveRequestCreate

    payload = LeaveRequestCreate(
        leave_type_id=int(args["leave_type_id"]),
        start_date=date.fromisoformat(args["start_date"]),
        end_date=date.fromisoformat(args["end_date"]),
        start_period=args.get("start_period", "AM"),
        end_period=args.get("end_period", "PM"),
        reason=args["reason"],
    )
    response = await create_leave(payload, user, session)
    return response.get("data", response)


async def confirm_leave(session: AsyncSession, user, conversation_id: int, token: str) -> dict:
    now = datetime.now(timezone.utc)
    action = await session.scalar(select(AgentAction).where(AgentAction.token_hash == sha256(token.encode()).hexdigest(), AgentAction.user_id == user.id, AgentAction.conversation_id == conversation_id))
    if action is None or action.status != "PENDING" or action.expires_at <= now:
        raise BusinessError(60004, "AGENT_CONFIRMATION_INVALID", "确认令牌无效、已使用或已过期", 409)
    # Mark before the business call; a transaction rollback restores PENDING.
    action.status = "CONSUMED"
    action.consumed_at = now
    result = await execute_leave(session, user, action.args)
    action.result = jsonable_encoder(result if isinstance(result, dict) else {"value": str(result)})
    await record_audit(session, actor_user_id=user.id, action="AGENT_LEAVE_CONFIRMED", resource_type="leave_request", resource_id=str(action.result.get("id", "")), after={"conversation_id": conversation_id, "agent_action_id": action.id}, request_id=None)
    await session.commit()
    return action.result
