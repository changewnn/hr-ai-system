from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdminUser
from app.common.errors import BusinessError
from app.common.responses import success
from app.db.session import get_db
from app.models.entities import ActiveStatus, Employee, Position
from app.schemas.position import PositionCreate, PositionUpdate
from app.services.audit import record_audit

router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("")
async def list_positions(_: AdminUser, session: AsyncSession = Depends(get_db)) -> dict:
    rows = (await session.scalars(select(Position).where(Position.deleted_at.is_(None)).order_by(Position.name))).all()
    return success([{"id": p.id, "name": p.name, "code": p.code, "status": p.status.value} for p in rows])


@router.post("")
async def create_position(payload: PositionCreate, current_user: AdminUser, session: AsyncSession = Depends(get_db)) -> dict:
    code = payload.code.strip().upper()
    if await session.scalar(select(Position).where(Position.code == code, Position.deleted_at.is_(None))):
        raise BusinessError(20011, "POSITION_CODE_EXISTS", "岗位编码已存在", 409)
    row = Position(name=payload.name.strip(), code=code)
    session.add(row)
    await session.flush()
    await record_audit(session, actor_user_id=current_user.id, action="POSITION_CREATE", resource_type="position", resource_id=str(row.id), after={"name": row.name, "code": row.code})
    await session.commit()
    return success({"id": row.id}, message="岗位创建成功")


@router.put("/{position_id}")
async def update_position(position_id: int, payload: PositionUpdate, current_user: AdminUser, session: AsyncSession = Depends(get_db)) -> dict:
    row = await session.scalar(select(Position).where(Position.id == position_id, Position.deleted_at.is_(None)))
    if row is None:
        raise BusinessError(20012, "POSITION_NOT_FOUND", "岗位不存在", 404)
    if payload.code is not None:
        code = payload.code.strip().upper()
        duplicate = await session.scalar(select(Position).where(Position.code == code, Position.id != position_id, Position.deleted_at.is_(None)))
        if duplicate:
            raise BusinessError(20011, "POSITION_CODE_EXISTS", "岗位编码已存在", 409)
        row.code = code
    if payload.name is not None:
        row.name = payload.name.strip()
    await record_audit(session, actor_user_id=current_user.id, action="POSITION_UPDATE", resource_type="position", resource_id=str(row.id), after={"name": row.name, "code": row.code})
    await session.commit()
    return success(message="岗位更新成功")


@router.delete("/{position_id}")
async def delete_position(position_id: int, current_user: AdminUser, session: AsyncSession = Depends(get_db)) -> dict:
    row = await session.scalar(select(Position).where(Position.id == position_id, Position.deleted_at.is_(None)))
    if row is None:
        raise BusinessError(20012, "POSITION_NOT_FOUND", "岗位不存在", 404)
    used = await session.scalar(select(Employee.id).where(Employee.position_id == position_id, Employee.deleted_at.is_(None)).limit(1))
    if used is not None:
        raise BusinessError(20003, "POSITION_IN_USE", "岗位仍被员工引用", 409)
    row.deleted_at = datetime.now(timezone.utc)
    row.status = ActiveStatus.INACTIVE
    await record_audit(session, actor_user_id=current_user.id, action="POSITION_DELETE", resource_type="position", resource_id=str(row.id))
    await session.commit()
    return success(message="岗位删除成功")
