"""工具调用重试中间件 - 工具调用失败时自动重试

通过 langgraph-agent-kit emitter 发射 model.retry.start / model.retry.failed 事件。
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

from langchain.agents.middleware.types import AgentMiddleware

from langgraph_agent_kit.core.events import StreamEventType
from langgraph_agent_kit.helpers import get_emitter_from_runtime

if TYPE_CHECKING:
    from langchain_core.messages import ToolMessage
    from langgraph.types import Command

logger = logging.getLogger(__name__)

ERROR_KEYWORDS = ["error", "失败", "timeout", "exception", "not found", "无法"]


def _is_error_result(result: Any) -> bool:
    """判断工具结果是否为错误"""
    content = str(getattr(result, "content", result)).lower()
    return any(kw in content for kw in ERROR_KEYWORDS)


class RetryMiddleware(AgentMiddleware):
    """工具调用重试中间件

    当工具调用返回错误时，自动重试指定次数。
    通过 emitter 发射 model.retry.start / model.retry.failed 事件。
    """

    def __init__(self, max_retries: int = 2, retry_delay: float = 1.0) -> None:
        self._max_retries = max_retries
        self._retry_delay = retry_delay

    def wrap_tool_call(
        self,
        request: Any,
        handler: Any,
    ) -> "ToolMessage | Command[Any]":
        """同步工具调用重试"""
        tool_name = request.tool_call["name"]
        runtime = getattr(request, "runtime", None)
        emitter = get_emitter_from_runtime(runtime) if runtime else None

        for attempt in range(self._max_retries + 1):
            result = handler(request)

            if not _is_error_result(result):
                return result

            if attempt < self._max_retries:
                logger.warning(
                    "工具 %s 执行失败 (第 %d/%d 次)，%.1fs 后重试",
                    tool_name,
                    attempt + 1,
                    self._max_retries + 1,
                    self._retry_delay,
                )
                if emitter:
                    emitter.emit(StreamEventType.MODEL_RETRY_START.value, {
                        "tool_name": tool_name,
                        "attempt": attempt + 1,
                        "max_retries": self._max_retries,
                    })
                time.sleep(self._retry_delay)

        logger.error("工具 %s 重试 %d 次后仍然失败", tool_name, self._max_retries + 1)
        if emitter:
            emitter.emit(StreamEventType.MODEL_RETRY_FAILED.value, {
                "tool_name": tool_name,
                "attempts": self._max_retries + 1,
                "error": str(getattr(result, "content", result))[:200],
            })
        return result

    async def awrap_tool_call(
        self,
        request: Any,
        handler: Any,
    ) -> "ToolMessage | Command[Any]":
        """异步工具调用重试"""
        tool_name = request.tool_call["name"]
        runtime = getattr(request, "runtime", None)
        emitter = get_emitter_from_runtime(runtime) if runtime else None

        for attempt in range(self._max_retries + 1):
            result = await handler(request)

            if not _is_error_result(result):
                return result

            if attempt < self._max_retries:
                logger.warning(
                    "工具 %s 执行失败 (第 %d/%d 次)，%.1fs 后重试",
                    tool_name,
                    attempt + 1,
                    self._max_retries + 1,
                    self._retry_delay,
                )
                if emitter:
                    emitter.emit(StreamEventType.MODEL_RETRY_START.value, {
                        "tool_name": tool_name,
                        "attempt": attempt + 1,
                        "max_retries": self._max_retries,
                    })
                await asyncio.sleep(self._retry_delay)

        logger.error("工具 %s 重试 %d 次后仍然失败", tool_name, self._max_retries + 1)
        if emitter:
            emitter.emit(StreamEventType.MODEL_RETRY_FAILED.value, {
                "tool_name": tool_name,
                "attempts": self._max_retries + 1,
                "error": str(getattr(result, "content", result))[:200],
            })
        return result
