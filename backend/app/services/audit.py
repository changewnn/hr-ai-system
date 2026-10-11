from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.support import AuditLog

_SENSITIVE_KEYS = {"password", "password_hash", "token", "access_token", "api_key", "secret", "jwt", "confirmation_token"}


def _sanitize(value: Any, key: str | None = None) -> Any:
    if key and any(item in key.lower() for item in _SENSITIVE_KEYS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): _sanitize(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    text = str(value) if value is not None else value
    if isinstance(text, str) and len(text) > 1000:
        return text[:1000] + "...[TRUNCATED]"
    return text


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
        before_json=_sanitize(before),
        after_json=_sanitize(after),
        request_id=request_id,
        ip=ip,
    )
    session.add(entry)
    await session.flush()
    return entry
