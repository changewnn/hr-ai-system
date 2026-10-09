from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import bcrypt
from jose import jwt
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.errors import BusinessError
from app.core.config import get_settings
from app.models.entities import ActiveStatus, Employee, EmployeeStatus, User


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def validate_password_strength(password: str) -> None:
    if len(password) < 8 or not any(char.isalpha() for char in password) or not any(char.isdigit() for char in password):
        raise BusinessError(10008, "AUTH_WEAK_PASSWORD", "密码至少 8 位且必须同时包含字母和数字", 400)


def create_access_token(user: User) -> tuple[str, int]:
    settings = get_settings()
    expires_in = settings.jwt_expire_hours * 60 * 60
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role.value,
        "employee_id": user.employee_id,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm), expires_in


async def authenticate(session: AsyncSession, identifier: str, password: str) -> User:
    normalized = identifier.strip()
    user = await session.scalar(
        select(User)
        .outerjoin(Employee, User.employee_id == Employee.id)
        .where(or_(User.username == normalized, Employee.phone == normalized))
    )
    invalid = BusinessError(10001, "AUTH_INVALID_CREDENTIALS", "账号或密码错误", 401)
    if user is None or user.status != ActiveStatus.ACTIVE or not verify_password(password, user.password_hash):
        raise invalid
    if user.employee_id is not None:
        employee = await session.get(Employee, user.employee_id)
        if employee is not None and employee.status == EmployeeStatus.RESIGNED:
            user.status = ActiveStatus.INACTIVE
            await session.commit()
            raise BusinessError(10003, "AUTH_ACCOUNT_DISABLED", "离职员工账号已停用", 403)
    return user
