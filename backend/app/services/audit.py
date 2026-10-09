from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.support import AuditLog


async def record_audit(
    session: AsyncSession,
    *,
    actor_user_id: int | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    request_id: str | None = None,
    ip: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        before_json=before,
        after_json=after,
        request_id=request_id,
        ip=ip,
    )
    session.add(entry)
    await session.flush()
    return entry
