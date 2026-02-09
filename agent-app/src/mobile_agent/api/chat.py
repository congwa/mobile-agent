"""聊天端点 - SSE 流式聊天 + 截图获取

使用 langgraph-agent-kit 的 MobileOrchestrator + create_sse_response
实现标准 StreamEvent 协议的 SSE 流。
"""

from __future__ import annotations

import base64
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from langgraph_agent_kit import create_sse_response

from mobile_agent.api.schemas import ChatRequest, StatusResponse
from mobile_agent.core.service import get_agent_service
from mobile_agent.streaming.orchestrator import MobileOrchestrator

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat")
async def chat(request_data: ChatRequest):
    """SSE 流式聊天

    Agent 接收自然语言指令，自主操作手机设备，
    通过 SSE 实时返回思考过程和工具调用结果。
    事件协议遵循 langgraph-agent-kit StreamEvent 标准。
    """
    service = get_agent_service()
    if not service.is_ready:
        raise HTTPException(status_code=503, detail="Agent 服务未就绪，请稍后重试")

    conversation_id = request_data.conversation_id or str(uuid.uuid4())

    orchestrator = MobileOrchestrator(
        agent_service=service,
        conversation_id=conversation_id,
        user_id="default",
        user_message=request_data.message,
        assistant_message_id=str(uuid.uuid4()),
        user_message_id=str(uuid.uuid4()),
        db=service,
    )

    return create_sse_response(orchestrator.run())


@router.get("/screenshot/{screenshot_id}")
async def get_screenshot(screenshot_id: str):
    """获取截图图片数据

    返回 PNG 图片二进制数据。
    """
    service = get_agent_service()
    data = await service.get_screenshot(screenshot_id)
    if data is None:
        raise HTTPException(status_code=404, detail="截图不存在或已过期")

    # 去掉可能的 data:image/png;base64, 前缀
    if "," in data:
        data = data.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(data)
    except Exception:
        raise HTTPException(status_code=500, detail="截图数据解码失败")

    return Response(content=image_bytes, media_type="image/png")


@router.get("/status", response_model=StatusResponse)
async def status():
    """获取 Agent 和设备连接状态"""
    service = get_agent_service()
    return service.get_status()
