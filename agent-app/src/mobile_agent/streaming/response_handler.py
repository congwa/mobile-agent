"""Mobile 流式响应处理器 - 继承 SDK 的 StreamingResponseHandler

处理 MCP 工具返回的截图数据，将其存储并通过 tool.end 事件传递 screenshot_id。
"""

from __future__ import annotations

import re
from typing import Any

from langchain_core.messages import ToolMessage

from langgraph_agent_kit.core.events import StreamEventType
from langgraph_agent_kit.streaming.response_handler import StreamingResponseHandler


def _contains_base64_image(content: str) -> bool:
    """检查内容是否包含 base64 编码的图片"""
    if len(content) < 100:
        return False
    return bool(re.search(r"[A-Za-z0-9+/]{100,}={0,2}", content))


class MobileResponseHandler(StreamingResponseHandler):
    """Mobile 专用响应处理器

    继承 SDK 的 StreamingResponseHandler，覆盖 _handle_tool_message：
    - 截图工具：存储 base64 数据，发射 tool.end 含 screenshot_id
    - 其他工具：发射标准 tool.end 含 output_preview
    """

    service: Any = None

    async def _handle_tool_message(self, msg: ToolMessage) -> None:
        """处理工具消息 - 发射 tool.end 事件"""
        # 去重
        msg_id = getattr(msg, "id", None)
        if isinstance(msg_id, str) and msg_id in self.seen_tool_ids:
            return
        if isinstance(msg_id, str):
            self.seen_tool_ids.add(msg_id)

        tool_name = getattr(msg, "name", "") or ""
        tool_call_id = getattr(msg, "tool_call_id", "") or ""
        content = str(getattr(msg, "content", ""))

        payload: dict[str, Any] = {
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "status": "success",
        }

        # 截图数据：存储并传递 screenshot_id
        has_image = False
        if "screenshot" in tool_name.lower() and _contains_base64_image(content):
            has_image = True
            if self.service is not None:
                screenshot_id = await self.service.store_screenshot(content)
                payload["screenshot_id"] = screenshot_id
            payload["output_preview"] = "[截图已保存]"
        else:
            payload["output_preview"] = content[:500]

        # 持久化工具消息
        if self.service is not None and self.conversation_id:
            await self.service.add_message(
                self.conversation_id,
                "tool",
                content[:500] if not has_image else "[截图]",
                tool_name=tool_name,
                has_image=has_image,
            )

        await self.emitter.aemit(StreamEventType.TOOL_END.value, payload)
