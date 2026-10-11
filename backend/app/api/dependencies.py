from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.errors import BusinessError
from app.core.security import decode_access_token, is_token_revoked
from app.db.session import get_db
from app.models.entities import ActiveStatus, Employee, EmployeeStatus, Role, User
from sqlalchemy import select

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], session: DbSession) -> User:
    payload = decode_access_token(token)
    if await is_token_revoked(str(payload["jti"])):
        raise BusinessError(10002, "AUTH_TOKEN_INVALID", "Token 已登出", 401)
    user = await session.scalar(select(User).where(User.id == int(payload["sub"])))
    if user is None or user.status != ActiveStatus.ACTIVE:
        raise BusinessError(10003, "AUTH_ACCOUNT_DISABLED", "账号已停用", 403)
    if user.employee_id is not None:
        employee = await session.get(Employee, user.employee_id)
        if employee is not None and employee.status == EmployeeStatus.RESIGNED:
            user.status = ActiveStatus.INACTIVE
            await session.commit()
            raise BusinessError(10003, "AUTH_ACCOUNT_DISABLED", "离职员工账号已停用", 403)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_active_user(current_user: CurrentUser) -> User:
    if current_user.must_change_password:
        raise BusinessError(10004, "AUTH_PASSWORD_CHANGE_REQUIRED", "首次登录必须先修改密码", 403)
    return current_user


CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]


def require_roles(*roles: Role):
    async def dependency(current_user: CurrentActiveUser) -> User:
        if current_user.role not in roles:
            raise BusinessError(10006, "PERMISSION_DENIED", "当前角色无权执行此操作", 403)
        return current_user
    return dependency


AdminUser = Annotated[User, Depends(require_roles(Role.ADMIN))]
ManagerOrAdminUser = Annotated[User, Depends(require_roles(Role.ADMIN, Role.MANAGER))]


def ensure_employee_scope(current_user: User, employee_id: int) -> None:
    if current_user.role == Role.EMPLOYEE and current_user.employee_id != employee_id:
        raise BusinessError(10006, "PERMISSION_DENIED", "员工只能访问本人的数据", 403)


async def ensure_employee_department_scope(session: AsyncSession, current_user: User, employee_id: int) -> None:
    if current_user.role == Role.ADMIN:
        return
    employee = await session.get(Employee, employee_id)
    if employee is None:
        raise BusinessError(10007, "RESOURCE_NOT_FOUND", "员工不存在或不可见", 404)
    if current_user.role == Role.EMPLOYEE and current_user.employee_id != employee_id:
        raise BusinessError(10006, "PERMISSION_DENIED", "员工只能访问本人的数据", 403)
    if current_user.role == Role.MANAGER:
        manager = await session.get(Employee, current_user.employee_id) if current_user.employee_id else None
        if manager is None or manager.department_id != employee.department_id:
            raise BusinessError(10006, "PERMISSION_DENIED", "主管只能访问本部门员工数据", 403)


async def agent_rate_limit(current_user: CurrentActiveUser) -> User:
    from app.core.security import check_agent_rate_limit
    await check_agent_rate_limit(current_user.id)
    return current_user


async def agent_sse_rate_limit(current_user: CurrentActiveUser) -> User:
    from app.core.security import check_agent_rate_limit
    await check_agent_rate_limit(current_user.id, stream=True)
    return current_user
