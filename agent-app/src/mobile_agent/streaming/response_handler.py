"""Mobile 流式响应处理器 - 继承 SDK 的 StreamingResponseHandler

处理 MCP 工具返回的截图数据，将其存储并通过 tool.end 事件传递 screenshot_id。

事件顺序遵循 embedease-ai 协议（每轮循环）：
  llm.call.start → [reasoning.delta, delta...] → llm.call.end → tool.start → tool.end

修复项：
- P0: 检测 AIMessageChunk.tool_calls → 先发 llm.call.end，再发 tool.start
- P0: 解析 <think>...</think> 标签，将思考内容与正文分离
- P1: 多轮 Agent 循环中每轮正确关闭/重开 LLM call 边界
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessageChunk, ToolMessage

from langgraph_agent_kit.core.events import StreamEventType
from langgraph_agent_kit.streaming.response_handler import StreamingResponseHandler


def _contains_base64_image(content: str) -> bool:
    """检查内容是否包含 base64 编码的图片"""
    if len(content) < 100:
        return False
    return bool(re.search(r"[A-Za-z0-9+/]{100,}={0,2}", content))


# ── <think> 标签解析 ──────────────────────────────────────────

_THINK_OPEN = re.compile(r"<think>", re.IGNORECASE)
_THINK_CLOSE = re.compile(r"</think>", re.IGNORECASE)


def _split_think_tags(text: str, in_think: bool) -> tuple[str, str, bool]:
    """将文本按 <think>...</think> 标签分离为 (reasoning, content, still_in_think)。

    支持流式增量：调用者传入上次的 in_think 状态，
    本函数返回本次增量的 reasoning 部分、content 部分和新的 in_think 状态。
    """
    reasoning_parts: list[str] = []
    content_parts: list[str] = []
    pos = 0

    while pos < len(text):
        if in_think:
            m = _THINK_CLOSE.search(text, pos)
            if m:
                reasoning_parts.append(text[pos:m.start()])
                pos = m.end()
                in_think = False
            else:
                reasoning_parts.append(text[pos:])
                pos = len(text)
        else:
            m = _THINK_OPEN.search(text, pos)
            if m:
                content_parts.append(text[pos:m.start()])
                pos = m.end()
                in_think = True
            else:
                content_parts.append(text[pos:])
                pos = len(text)

    return "".join(reasoning_parts), "".join(content_parts), in_think


@dataclass
class MobileResponseHandler(StreamingResponseHandler):
    """Mobile 专用响应处理器

    继承 SDK 的 StreamingResponseHandler，增强：
    - 从 AIMessageChunk.tool_calls 检测并发射 tool.start 事件
    - 解析 <think> 标签分离 reasoning / content
    - ToolMessage 后关闭当前 LLM call，支持多轮工具调用
    - 截图工具：存储 base64 数据，发射 tool.end 含 screenshot_id
    - 其他工具：发射标准 tool.end 含 output_preview
    """

    service: Any = None

    # <think> 标签流式状态
    _in_think: bool = False
    # 已发射过 tool.start 的 tool_call_id 集合（防止重复）
    _emitted_tool_starts: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self._in_think = False
        self._emitted_tool_starts = set()

    async def _close_llm_call(self) -> None:
        """关闭当前 LLM call（发射 llm.call.end）"""
        if self._in_llm_call:
            elapsed_ms = 0
            if self._llm_call_start_time:
                elapsed_ms = int((time.time() - self._llm_call_start_time) * 1000)
            await self.emitter.aemit(
                StreamEventType.LLM_CALL_END.value,
                {"elapsed_ms": elapsed_ms},
            )
            self._in_llm_call = False

    async def _handle_ai_chunk(self, msg: AIMessageChunk) -> None:
        """处理 AI 增量消息 — 增加 tool.start 检测 + <think> 标签解析

        事件顺序遵循 embedease-ai 协议：
        llm.call.start → reasoning.delta → delta → llm.call.end → tool.start
        """
        # ── 开始 LLM 调用 ──
        if not self._in_llm_call:
            self._in_llm_call = True
            self._llm_call_start_time = time.time()
            await self.emitter.aemit(
                StreamEventType.LLM_CALL_START.value,
                {"message_count": 0},
            )

        # ── 检测 tool_calls → 先关闭 llm.call.end，再发射 tool.start ──
        tool_calls = getattr(msg, "tool_calls", None) or []
        tool_call_chunks = getattr(msg, "tool_call_chunks", None) or []

        pending_tool_starts: list[dict[str, Any]] = []

        for tc in tool_calls:
            tc_id = tc.get("id") or tc.get("tool_call_id", "")
            if tc_id and tc_id not in self._emitted_tool_starts:
                self._emitted_tool_starts.add(tc_id)
                pending_tool_starts.append({
                    "tool_call_id": tc_id,
                    "name": tc.get("name", "unknown"),
                    "input": tc.get("args", tc.get("input")),
                })

        for tc in tool_call_chunks:
            tc_id = tc.get("id") or tc.get("tool_call_id", "")
            tc_name = tc.get("name", "")
            if tc_id and tc_name and tc_id not in self._emitted_tool_starts:
                self._emitted_tool_starts.add(tc_id)
                pending_tool_starts.append({
                    "tool_call_id": tc_id,
                    "name": tc_name,
                    "input": tc.get("args", tc.get("input")),
                })

        if pending_tool_starts:
            # 协议顺序：先 llm.call.end，再 tool.start
            await self._close_llm_call()
            for ts_payload in pending_tool_starts:
                await self.emitter.aemit(
                    StreamEventType.TOOL_START.value,
                    ts_payload,
                )

        # ── 提取文本内容 ──
        raw_text = ""
        content = msg.content
        if isinstance(content, str):
            raw_text = content
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, str):
                    raw_text += block
                elif isinstance(block, dict):
                    if block.get("type") == "reasoning":
                        reasoning_delta = block.get("reasoning", "")
                        if reasoning_delta:
                            self.full_reasoning += reasoning_delta
                            self.reasoning_chars += len(reasoning_delta)
                            self.reasoning_events += 1
                            await self.emitter.aemit(
                                StreamEventType.ASSISTANT_REASONING_DELTA.value,
                                {"delta": reasoning_delta},
                            )
                    elif block.get("type") == "text":
                        raw_text += block.get("text", "")

        if not raw_text:
            return

        # ── <think> 标签分离 ──
        reasoning_delta, content_delta, self._in_think = _split_think_tags(
            raw_text, self._in_think
        )

        if reasoning_delta:
            self.full_reasoning += reasoning_delta
            self.reasoning_chars += len(reasoning_delta)
            self.reasoning_events += 1
            await self.emitter.aemit(
                StreamEventType.ASSISTANT_REASONING_DELTA.value,
                {"delta": reasoning_delta},
            )

        if content_delta:
            self.full_content += content_delta
            self.content_events += 1
            await self.emitter.aemit(
                StreamEventType.ASSISTANT_DELTA.value,
                {"delta": content_delta},
            )

    async def _handle_tool_message(self, msg: ToolMessage) -> None:
        """处理工具消息 - 发射 tool.end 事件

        事件顺序遵循 embedease-ai 协议：
        llm.call.end → tool.start → tool.end

        正常情况下 llm.call.end 和 tool.start 已在 _handle_ai_chunk
        检测到 tool_calls 时发射。此处做兜底处理。
        """
        # 去重
        msg_id = getattr(msg, "id", None)
        if isinstance(msg_id, str) and msg_id in self.seen_tool_ids:
            return
        if isinstance(msg_id, str):
            self.seen_tool_ids.add(msg_id)

        tool_name = getattr(msg, "name", "") or ""
        tool_call_id = getattr(msg, "tool_call_id", "") or ""
        content = str(getattr(msg, "content", ""))

        # ── 兜底：若 llm.call.end 尚未发射，先关闭 LLM call ──
        await self._close_llm_call()

        # ── 兜底：若 tool.start 尚未发射（AIMessageChunk 中未检测到），补发 ──
        if tool_call_id and tool_call_id not in self._emitted_tool_starts:
            self._emitted_tool_starts.add(tool_call_id)
            await self.emitter.aemit(
                StreamEventType.TOOL_START.value,
                {
                    "tool_call_id": tool_call_id,
                    "name": tool_name,
                    "input": None,
                },
            )

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
