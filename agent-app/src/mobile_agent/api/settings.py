"""设置端点 - 配置读写、LLM 测试、MCP 重连"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException

from mobile_agent.api.schemas import (
    SettingsResponse,
    SettingsUpdateRequest,
    TestLLMResponse,
)
from mobile_agent.core.service import get_agent_service

router = APIRouter(prefix="/api/v1", tags=["settings"])


@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """获取当前配置"""
    service = get_agent_service()
    return service.get_settings_snapshot()


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(request_data: SettingsUpdateRequest):
    """更新配置（部分更新）

    注意：LLM/MCP 配置修改后需要重新初始化才能生效。
    """
    service = get_agent_service()
    updates: dict[str, Any] = {}

    if request_data.llm is not None:
        updates["llm"] = request_data.llm.model_dump(exclude_unset=True)
    if request_data.mcp is not None:
        updates["mcp"] = request_data.mcp.model_dump(exclude_unset=True)
    if request_data.agent is not None:
        updates["agent"] = request_data.agent.model_dump(exclude_unset=True)
    if request_data.middleware is not None:
        updates["middleware"] = request_data.middleware.model_dump(exclude_unset=True)

    result = service.update_settings(updates)
    return result


@router.post("/settings/test-llm", response_model=TestLLMResponse)
async def test_llm():
    """测试 LLM 连接

    向当前配置的 LLM 发送一条简单消息，验证连接是否正常。
    """
    service = get_agent_service()
    settings = service._settings

    try:
        from mobile_agent.core.agent_builder import _create_model_instance

        model_str = settings.llm.model
        if not settings.llm.api_key:
            return TestLLMResponse(
                success=False,
                message="请先配置 API Key",
                model=model_str,
            )

        llm = _create_model_instance(settings.llm)

        start = time.time()
        response = await llm.ainvoke("Say 'ok' in one word.")
        latency = (time.time() - start) * 1000

        return TestLLMResponse(
            success=True,
            message="LLM 连接正常",
            model=model_str,
            latency_ms=round(latency, 1),
        )

    except Exception as e:
        return TestLLMResponse(
            success=False,
            message=f"LLM 连接失败: {e}",
            model=settings.llm.model,
        )


@router.post("/settings/reconnect-mcp")
async def reconnect_mcp():
    """重新连接 MCP Server"""
    service = get_agent_service()
    result = await service.reconnect_mcp()

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])

    return result
