from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.dependencies import CurrentActiveUser, CurrentUser
from app.common.responses import success
from app.common.errors import BusinessError
from app.core.security import check_login_rate_limit, clear_login_failures, decode_access_token, record_login_failure, revoke_token
from app.db.session import get_db
from app.schemas.auth import AccountCreateRequest, AccountStatusRequest, ChangePasswordRequest, LoginRequest, LoginResponse, UserSummary
from app.models.entities import ActiveStatus, Employee, Role, User
from app.services.audit import record_audit
from app.services.auth import authenticate, create_access_token, hash_password, validate_password_strength, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=None, summary="账号登录")
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_db)) -> dict:
    await check_login_rate_limit(payload.identifier)
    try:
        user = await authenticate(session, payload.identifier, payload.password)
    except BusinessError:
        await record_login_failure(payload.identifier)
        raise
    await clear_login_failures(payload.identifier)
    token, expires_in = create_access_token(user)
    result = LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserSummary(id=user.id, username=user.username, role=user.role, employee_id=user.employee_id, status=user.status.value, must_change_password=user.must_change_password),
    )
    return success(result.model_dump(mode="json"))


@router.post("/logout", summary="登出并撤销当前 Token")
async def logout(request: Request, current_user: CurrentUser) -> dict:
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    payload = decode_access_token(token)
    exp = int(payload["exp"])
    ttl = exp - int(datetime.now(timezone.utc).timestamp())
    await revoke_token(str(payload["jti"]), current_user.id, ttl)
    return success(message="已安全登出")


@router.post("/refresh", summary="刷新访问 Token")
async def refresh_token(current_user: CurrentUser) -> dict:
    token, expires_in = create_access_token(current_user)
    return success({"access_token": token, "token_type": "bearer", "expires_in": expires_in})


@router.get("/me", summary="当前用户信息")
async def me(current_user: CurrentUser) -> dict:
    return success(UserSummary(id=current_user.id, username=current_user.username, role=current_user.role, employee_id=current_user.employee_id, status=current_user.status.value, must_change_password=current_user.must_change_password).model_dump(mode="json"))


@router.post("/change-password", summary="修改密码")
async def change_password(payload: ChangePasswordRequest, current_user: CurrentUser, session: AsyncSession = Depends(get_db)) -> dict:
    if not verify_password(payload.old_password, current_user.password_hash):
        raise BusinessError(10001, "AUTH_INVALID_CREDENTIALS", "原密码错误", 401)
    validate_password_strength(payload.new_password)
    current_user.password_hash = hash_password(payload.new_password)
    current_user.must_change_password = False
    await record_audit(session, actor_user_id=current_user.id, action="PASSWORD_CHANGE", resource_type="user", resource_id=str(current_user.id))
    await session.commit()
    return success(message="密码修改成功")


@router.get("/accounts", summary="查询账号")
async def list_accounts(current_user: CurrentActiveUser, session: AsyncSession = Depends(get_db)) -> dict:
    if current_user.role != Role.ADMIN:
        raise BusinessError(10006, "PERMISSION_DENIED", "仅 ADMIN 可以管理账号", 403)
    users = (await session.scalars(select(User).order_by(User.id))).all()
    return success([UserSummary(id=u.id, username=u.username, role=u.role, employee_id=u.employee_id, status=u.status.value, must_change_password=u.must_change_password).model_dump(mode="json") for u in users])


@router.post("/accounts", summary="创建账号")
async def create_account(payload: AccountCreateRequest, current_user: CurrentActiveUser, session: AsyncSession = Depends(get_db)) -> dict:
    if current_user.role != Role.ADMIN:
        raise BusinessError(10006, "PERMISSION_DENIED", "仅 ADMIN 可以创建账号", 403)
    validate_password_strength(payload.password)
    if await session.scalar(select(User).where(User.username == payload.username.strip())):
        raise BusinessError(10009, "AUTH_USERNAME_EXISTS", "账号已存在", 409)
    if payload.employee_id is not None:
        employee = await session.get(Employee, payload.employee_id)
        if employee is None:
            raise BusinessError(20006, "EMPLOYEE_NOT_FOUND", "绑定的员工不存在", 404)
        if await session.scalar(select(User).where(User.employee_id == payload.employee_id)):
            raise BusinessError(10010, "AUTH_EMPLOYEE_ALREADY_BOUND", "员工已绑定账号", 409)
    user = User(username=payload.username.strip(), password_hash=hash_password(payload.password), role=payload.role, employee_id=payload.employee_id, status=ActiveStatus.ACTIVE, must_change_password=True)
    session.add(user)
    await session.flush()
    await record_audit(session, actor_user_id=current_user.id, action="ACCOUNT_CREATE", resource_type="user", resource_id=str(user.id), after={"username": user.username, "role": user.role.value, "employee_id": user.employee_id})
    await session.commit()
    return success(UserSummary(id=user.id, username=user.username, role=user.role, employee_id=user.employee_id, status=user.status.value, must_change_password=user.must_change_password).model_dump(mode="json"), message="账号创建成功")


@router.patch("/accounts/{user_id}/status", summary="启停用账号")
async def update_account_status(user_id: int, payload: AccountStatusRequest, current_user: CurrentActiveUser, session: AsyncSession = Depends(get_db)) -> dict:
    if current_user.role != Role.ADMIN:
        raise BusinessError(10006, "PERMISSION_DENIED", "仅 ADMIN 可以管理账号", 403)
    user = await session.get(User, user_id)
    if user is None:
        raise BusinessError(10007, "RESOURCE_NOT_FOUND", "账号不存在", 404)
    user.status = ActiveStatus.ACTIVE if payload.enabled else ActiveStatus.INACTIVE
    await record_audit(session, actor_user_id=current_user.id, action="ACCOUNT_STATUS_UPDATE", resource_type="user", resource_id=str(user.id), after={"status": user.status.value})
    await session.commit()
    return success(message="账号状态已更新")
