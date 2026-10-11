"""Delete expired Agent session data without touching formal HR records."""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.support import AgentAction, AgentConversation, AgentMessage, AuditLog


async def cleanup() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=get_settings().agent_retention_days)
    async with AsyncSessionLocal() as session:
        ids = list((await session.scalars(select(AgentConversation.id).where(AgentConversation.updated_at < cutoff).limit(500))).all())
        if not ids:
            return 0
        await session.execute(delete(AgentAction).where(AgentAction.conversation_id.in_(ids)))
        await session.execute(delete(AgentMessage).where(AgentMessage.conversation_id.in_(ids)))
        await session.execute(delete(AgentConversation).where(AgentConversation.id.in_(ids)))
        session.add(AuditLog(actor_user_id=None, action="AGENT_RETENTION_CLEANUP", resource_type="agent_data", resource_id=str(len(ids)), after_json={"deleted_conversations": len(ids), "cutoff": cutoff.isoformat()}))
        await session.commit()
        return len(ids)


if __name__ == "__main__":
    print(f"deleted_conversations={asyncio.run(cleanup())}")
