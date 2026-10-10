from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentActiveUser
from app.common.errors import BusinessError
from app.common.responses import success
from app.db.session import get_db
from app.models.support import Message
from app.services.attendance import business_now

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("")
async def list_messages(current_user: CurrentActiveUser, session: AsyncSession = Depends(get_db), unread_only: bool = Query(False)) -> dict:
    query = select(Message).where(Message.recipient_user_id == current_user.id)
    if unread_only:
        query = query.where(Message.read_at.is_(None))
    rows = (await session.scalars(query.order_by(Message.created_at.desc()))).all()
    data = [{"id": row.id, "type": row.type.value, "title": row.title, "content": row.content, "related_id": row.related_id, "read_at": row.read_at, "created_at": row.created_at} for row in rows]
    return success({"items": data, "unread_count": sum(1 for row in rows if row.read_at is None)})


@router.patch("/{message_id}/read")
async def read_message(message_id: int, current_user: CurrentActiveUser, session: AsyncSession = Depends(get_db)) -> dict:
    row = await session.get(Message, message_id)
    if row is None or row.recipient_user_id != current_user.id:
        raise BusinessError(10007, "RESOURCE_NOT_FOUND", "消息不存在", 404)
    row.read_at = business_now()
    await session.commit()
    return success(message="消息已读")


@router.post("/read-all")
async def read_all(current_user: CurrentActiveUser, session: AsyncSession = Depends(get_db)) -> dict:
    await session.execute(update(Message).where(Message.recipient_user_id == current_user.id, Message.read_at.is_(None)).values(read_at=business_now()))
    await session.commit()
    return success(message="消息已全部标记为已读")
