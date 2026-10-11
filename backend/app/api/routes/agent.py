from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentActiveUser, agent_rate_limit, agent_sse_rate_limit
from app.common.responses import success
from app.db.session import get_db
from app.models.entities import User
from app.models.support import AgentConversation, AgentMessage
from app.schemas.agent import AgentConfirmation, AgentMessageCreate, ConversationCreate, ConversationRename
from app.services.agent import create_conversation, ensure_conversation, run_turn
from app.services.agent_tools import confirm_leave

router = APIRouter(prefix="/agent", tags=["agent"])


def _message_dict(row: AgentMessage) -> dict:
    return {
        "id": row.id,
        "role": row.role,
        "content": row.content,
        "citations": row.citations or [],
        "status": row.status,
        "created_at": row.created_at,
    }


@router.post("/conversations")
async def create_agent_conversation(
    payload: ConversationCreate,
    current_user: CurrentActiveUser,
    session: AsyncSession = Depends(get_db),
) -> dict:
    row = await create_conversation(
        session, current_user.id, current_user.employee_id, payload.title
    )
    return success(
        {"id": row.id, "title": row.title, "status": row.status, "created_at": row.created_at}
    )


@router.get("/conversations")
async def list_agent_conversations(
    current_user: CurrentActiveUser,
    session: AsyncSession = Depends(get_db),
) -> dict:
    rows = (
        await session.scalars(
            select(AgentConversation)
            .where(AgentConversation.user_id == current_user.id)
            .order_by(AgentConversation.updated_at.desc())
        )
    ).all()
    return success(
        [
            {"id": row.id, "title": row.title, "status": row.status, "updated_at": row.updated_at}
            for row in rows
        ]
    )


@router.get("/conversations/{conversation_id}")
async def get_agent_conversation(
    conversation_id: int,
    current_user: CurrentActiveUser,
    session: AsyncSession = Depends(get_db),
) -> dict:
    conversation = await ensure_conversation(session, conversation_id, current_user.id)
    messages = (
        await session.scalars(
            select(AgentMessage)
            .where(AgentMessage.conversation_id == conversation.id)
            .order_by(AgentMessage.created_at.asc(), AgentMessage.id.asc())
        )
    ).all()
    return success(
        {
            "id": conversation.id,
            "title": conversation.title,
            "status": conversation.status,
            "messages": [_message_dict(row) for row in messages],
        }
    )


@router.patch("/conversations/{conversation_id}")
async def rename_agent_conversation(
    conversation_id: int,
    payload: ConversationRename,
    current_user: CurrentActiveUser,
    session: AsyncSession = Depends(get_db),
) -> dict:
    conversation = await ensure_conversation(session, conversation_id, current_user.id)
    conversation.title = payload.title.strip()
    await session.commit()
    return success(message="会话名称已更新")


@router.post("/conversations/{conversation_id}/messages")
async def send_agent_message(
    conversation_id: int,
    payload: AgentMessageCreate,
    current_user: CurrentActiveUser,
    _: User = Depends(agent_rate_limit),
    session: AsyncSession = Depends(get_db),
) -> dict:
    conversation = await ensure_conversation(session, conversation_id, current_user.id)
    result = await run_turn(session, conversation, payload.content, current_user.id)
    return success({"conversation_id": conversation.id, **result})


@router.post("/conversations/{conversation_id}/confirm-leave")
async def confirm_agent_leave(
    conversation_id: int,
    payload: AgentConfirmation,
    current_user: CurrentActiveUser,
    session: AsyncSession = Depends(get_db),
) -> dict:
    conversation = await ensure_conversation(session, conversation_id, current_user.id)
    result = await confirm_leave(session, current_user, conversation.id, payload.confirmation_token)
    return success({"conversation_id": conversation.id, "result": result}, message="请假申请已提交")


@router.post("/conversations/{conversation_id}/messages/stream")
async def stream_agent_message(
    conversation_id: int,
    payload: AgentMessageCreate,
    current_user: CurrentActiveUser,
    _: User = Depends(agent_sse_rate_limit),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    conversation = await ensure_conversation(session, conversation_id, current_user.id)
    result = await run_turn(session, conversation, payload.content, current_user.id)

    async def events():
        yield f"event: start\ndata: {json.dumps({'conversation_id': conversation.id})}\n\n"
        for index in range(0, len(result["answer"]), 24):
            payload = {"delta": result["answer"][index : index + 24]}
            yield f"event: message_delta\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)
        for citation in result["citations"]:
            yield f"event: citation\ndata: {json.dumps(citation, ensure_ascii=False)}\n\n"
        if result["transferred_to_hr"]:
            payload = {"message": "已转交 HR"}
            yield f"event: hr_transferred\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        yield f"event: completed\ndata: {json.dumps({'request_id': result['request_id'], 'requires_confirmation': result.get('requires_confirmation', False), 'confirmation_token': result.get('confirmation_token')}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
