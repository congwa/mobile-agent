"""截图优化中间件 - 引导 Agent 优先使用 list_elements，减少截图频率"""

from __future__ import annotations

import logging
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware

logger = logging.getLogger(__name__)

SCREENSHOT_TOOL_NAMES = {"mobile_take_screenshot", "mobile_screenshot_with_som", "mobile_screenshot_with_grid"}


class ScreenshotOptimizerMiddleware(AgentMiddleware):
    """截图优化中间件

    在 LLM 调用前检查最近的工具调用历史：
    - 如果连续截图次数过多，注入提示引导 Agent 使用 mobile_list_elements
    """

    def __init__(self, max_consecutive_screenshots: int = 2) -> None:
        self._max_consecutive = max_consecutive_screenshots

    async def abefore_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        """在 LLM 调用前检查截图频率"""
        messages = state.get("messages", [])

        # 统计最近 N 条消息中的截图工具调用次数
        recent_screenshot_count = 0
        for msg in messages[-8:]:
            msg_name = getattr(msg, "name", None) or ""
            if msg_name in SCREENSHOT_TOOL_NAMES:
                recent_screenshot_count += 1

        if recent_screenshot_count >= self._max_consecutive:
            logger.info(
                "检测到连续 %d 次截图，注入优化提示",
                recent_screenshot_count,
            )
            return {
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "提示：你已连续截图多次，请优先使用 mobile_list_elements 获取页面文本信息，"
                            "减少 token 消耗。仅在 list_elements 无法判断页面状态时才使用截图。"
                        ),
                    }
                ]
            }
        return None
