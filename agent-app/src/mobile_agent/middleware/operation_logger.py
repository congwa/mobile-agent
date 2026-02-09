"""操作日志中间件 - 记录每步工具调用，用于调试和测试脚本生成

通过 langgraph-agent-kit 的 helpers 发射 tool.start / tool.end SSE 事件。
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from langchain.agents.middleware.types import AgentMiddleware

from langgraph_agent_kit.helpers import (
    emit_tool_start,
    emit_tool_end,
    get_emitter_from_runtime,
)

if TYPE_CHECKING:
    from langchain_core.messages import ToolMessage
    from langgraph.types import Command

logger = logging.getLogger(__name__)


class OperationLoggerMiddleware(AgentMiddleware):
    """记录每步工具调用的中间件

    拦截 wrap_tool_call，记录工具名称、参数、结果和耗时。
    同时通过 emitter 发射 tool.start / tool.end SSE 事件。
    """

    def wrap_tool_call(
        self,
        request: Any,
        handler: Any,
    ) -> "ToolMessage | Command[Any]":
        """拦截工具调用 — 记录日志 + 发射事件"""
        tool_name = request.tool_call["name"]
        tool_args = request.tool_call["args"]
        tool_call_id = request.tool_call.get("id", "")

        logger.info("📱 调用工具: %s(%s)", tool_name, tool_args)

        # 发射 tool.start 事件
        runtime = getattr(request, "runtime", None)
        if runtime:
            emit_tool_start(runtime, tool_call_id, tool_name, input=tool_args)

        start_time = time.time()
        result = handler(request)
        elapsed = time.time() - start_time

        result_preview = str(getattr(result, "content", result))[:200]
        logger.info("📱 工具结果 (%.2fs): %s", elapsed, result_preview)

        return result

    async def awrap_tool_call(
        self,
        request: Any,
        handler: Any,
    ) -> "ToolMessage | Command[Any]":
        """异步版本 — 拦截工具调用 + 发射事件"""
        tool_name = request.tool_call["name"]
        tool_args = request.tool_call["args"]
        tool_call_id = request.tool_call.get("id", "")

        logger.info("📱 调用工具: %s(%s)", tool_name, tool_args)

        # 发射 tool.start 事件
        runtime = getattr(request, "runtime", None)
        if runtime:
            emit_tool_start(runtime, tool_call_id, tool_name, input=tool_args)

        start_time = time.time()
        result = await handler(request)
        elapsed = time.time() - start_time

        result_preview = str(getattr(result, "content", result))[:200]
        logger.info("📱 工具结果 (%.2fs): %s", elapsed, result_preview)

        return result
