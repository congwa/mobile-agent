"""会话历史端点"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from mobile_agent.api.schemas import (
    ConversationDetail,
    ConversationListResponse,
    ConversationSummary,
)
from mobile_agent.core.service import get_agent_service

router = APIRouter(prefix="/api/v1", tags=["conversations"])


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    query: str = Query(default="", description="搜索关键词"),
):
    """获取会话列表"""
    service = get_agent_service()
    results = await service.list_conversations(query=query)

    summaries = [
        ConversationSummary(
            id=c["id"],
            created_at=c.get("created_at", ""),
            summary=c.get("summary", ""),
            status=c.get("status", "success"),
            steps=c.get("steps", 0),
            duration=c.get("duration", ""),
        )
        for c in results
    ]

    return ConversationListResponse(
        conversations=summaries,
        total=len(summaries),
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str):
    """获取会话详情"""
    service = get_agent_service()
    conv = await service.get_conversation(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 映射 Storage 消息字段 → API schema 字段
    raw_messages = conv.get("messages", [])
    messages = [
        {
            "id": m.get("id", ""),
            "type": m.get("role", m.get("type", "")),
            "content": m.get("content", ""),
            "tool_name": m.get("tool_name", ""),
            "tool_args": {},
            "has_image": bool(m.get("has_image", False)),
            "timestamp": m.get("created_at", m.get("timestamp", "")),
        }
        for m in raw_messages
    ]

    return ConversationDetail(
        id=conv["id"],
        created_at=conv.get("created_at", ""),
        summary=conv.get("summary", conv.get("title", "")),
        status=conv.get("status", "success"),
        steps=conv.get("steps", 0),
        duration=conv.get("duration", ""),
        messages=messages,
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """删除会话"""
    service = get_agent_service()
    deleted = await service.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"ok": True}
