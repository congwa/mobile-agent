"""MobileOrchestrator 单元测试（SDK v0.2.0）

测试 MobileOrchestrator 的事件编排和取消功能：
- meta.start 自动发送
- 事件转发
- 任务取消（cancel_conversation）
- 异常处理
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock

import pytest

from langgraph_agent_kit.core.context import ChatContext
from langgraph_agent_kit.core.events import StreamEventType

# 所有 async 测试的超时（秒）
ASYNC_TIMEOUT = 10


# ==================== Fixtures ====================


class FakeAgentService:
    """模拟 MobileAgentService"""

    def __init__(self, events: list[tuple[str, dict[str, Any]]] | None = None):
        self._events = events or []

    async def chat_emit(
        self,
        *,
        message: str,
        conversation_id: str,
        user_id: str = "",
        context: Any = None,
        agent_id: str | None = None,
    ) -> None:
        emitter = context.emitter
        for evt_type, payload in self._events:
            await emitter.aemit(evt_type, payload)
        await emitter.aemit("__end__", None)


async def _run_orchestrator(
    events: list[tuple[str, dict[str, Any]]],
    message: str = "打开微信",
) -> list[dict]:
    """辅助：运行 MobileOrchestrator 并收集事件（带超时）"""
    from mobile_agent.streaming.orchestrator import MobileOrchestrator

    agent_service = FakeAgentService(events)
    orchestrator = MobileOrchestrator(
        agent_service=agent_service,
        conversation_id="test-conv-1",
        user_id="default",
        user_message=message,
        assistant_message_id="amsg-1",
        user_message_id="umsg-1",
        db=None,
    )

    collected: list[dict] = []

    async def _collect():
        async for event in orchestrator.run():
            collected.append(
                event.model_dump() if hasattr(event, "model_dump") else dict(event)
            )

    await asyncio.wait_for(_collect(), timeout=ASYNC_TIMEOUT)
    return collected


# ==================== Tests ====================


@pytest.mark.anyio
class TestMobileOrchestrator:
    """测试 MobileOrchestrator 事件编排"""

    async def test_meta_start_emitted(self):
        """meta.start 事件应自动发送"""
        events = await _run_orchestrator([])

        start_events = [e for e in events if e.get("type") == "meta.start"]
        assert len(start_events) == 1
        payload = start_events[0]["payload"]
        assert payload["user_message_id"] == "umsg-1"
        assert payload["assistant_message_id"] == "amsg-1"

    async def test_assistant_delta_forwarded(self):
        """assistant.delta 事件应正确转发"""
        domain_events = [
            (StreamEventType.ASSISTANT_DELTA.value, {"delta": "正在"}),
            (StreamEventType.ASSISTANT_DELTA.value, {"delta": "操作"}),
        ]
        events = await _run_orchestrator(domain_events)

        deltas = [e for e in events if e.get("type") == "assistant.delta"]
        assert len(deltas) == 2
        assert deltas[0]["payload"]["delta"] == "正在"
        assert deltas[1]["payload"]["delta"] == "操作"

    async def test_tool_events_forwarded(self):
        """tool.start / tool.end 事件应正确转发"""
        domain_events = [
            (StreamEventType.TOOL_START.value, {
                "tool_call_id": "tc-1",
                "name": "mobile_take_screenshot",
                "input": {},
            }),
            (StreamEventType.TOOL_END.value, {
                "tool_call_id": "tc-1",
                "name": "mobile_take_screenshot",
                "status": "success",
                "screenshot_id": "ss-123",
                "output_preview": "[截图已保存]",
            }),
        ]
        events = await _run_orchestrator(domain_events)

        tool_starts = [e for e in events if e.get("type") == "tool.start"]
        tool_ends = [e for e in events if e.get("type") == "tool.end"]
        assert len(tool_starts) == 1
        assert len(tool_ends) == 1
        assert tool_ends[0]["payload"]["screenshot_id"] == "ss-123"

    async def test_seq_monotonically_increasing(self):
        """事件序号应单调递增"""
        domain_events = [
            (StreamEventType.ASSISTANT_DELTA.value, {"delta": "a"}),
            (StreamEventType.ASSISTANT_DELTA.value, {"delta": "b"}),
        ]
        events = await _run_orchestrator(domain_events)

        seqs = [e.get("seq") for e in events if e.get("seq") is not None]
        for i in range(1, len(seqs)):
            assert seqs[i] > seqs[i - 1], f"seq 不单调递增: {seqs}"

    async def test_error_event_on_exception(self):
        """Agent 异常应产生 error 事件（不卡死）"""

        class ErrorAgentService:
            async def chat_emit(self, **kwargs):
                emitter = kwargs["context"].emitter
                # 先发一些事件再失败
                await emitter.aemit(StreamEventType.ASSISTANT_DELTA.value, {"delta": "开始"})
                raise RuntimeError("MCP 连接断开")

        from mobile_agent.streaming.orchestrator import MobileOrchestrator

        orchestrator = MobileOrchestrator(
            agent_service=ErrorAgentService(),
            conversation_id="test-conv-err",
            user_id="default",
            user_message="测试",
            assistant_message_id="amsg-err",
            user_message_id="umsg-err",
            db=None,
        )

        collected: list[dict] = []

        async def _collect():
            async for event in orchestrator.run():
                collected.append(
                    event.model_dump() if hasattr(event, "model_dump") else dict(event)
                )

        await asyncio.wait_for(_collect(), timeout=ASYNC_TIMEOUT)

        error_events = [e for e in collected if e.get("type") == "error"]
        assert len(error_events) >= 1
        assert "MCP 连接断开" in error_events[0]["payload"]["message"]


@pytest.mark.anyio
class TestCancelConversation:
    """测试任务取消功能"""

    async def test_cancel_nonexistent(self):
        """取消不存在的会话应返回 False"""
        from mobile_agent.streaming.orchestrator import cancel_conversation

        assert cancel_conversation("nonexistent-conv") is False

    async def test_cancel_running_task(self):
        """取消运行中的任务应返回 True"""
        from mobile_agent.streaming.orchestrator import (
            MobileOrchestrator,
            cancel_conversation,
            _running_tasks,
        )

        class SlowAgentService:
            async def chat_emit(self, **kwargs):
                emitter = kwargs["context"].emitter
                await emitter.aemit(StreamEventType.ASSISTANT_DELTA.value, {"delta": "慢"})
                # 模拟长时间运行
                await asyncio.sleep(30)
                await emitter.aemit("__end__", None)

        orchestrator = MobileOrchestrator(
            agent_service=SlowAgentService(),
            conversation_id="cancel-test",
            user_id="default",
            user_message="慢操作",
            assistant_message_id="amsg-cancel",
            db=None,
        )

        # 在后台运行编排器
        collected: list[dict] = []

        async def _consume():
            async for event in orchestrator.run():
                collected.append(
                    event.model_dump() if hasattr(event, "model_dump") else dict(event)
                )

        task = asyncio.create_task(_consume())

        # 等一下让 producer 启动
        await asyncio.sleep(0.2)

        # 应该有注册的任务
        assert "cancel-test" in _running_tasks

        # 取消
        result = cancel_conversation("cancel-test")
        assert result is True

        # 等编排器结束
        await asyncio.wait_for(task, timeout=5)

        # 取消后不应再在注册表
        assert "cancel-test" not in _running_tasks


class TestMobileOrchestratorSync:
    """同步测试"""

    def test_constructor(self):
        """构造函数应接受所有参数"""
        from mobile_agent.streaming.orchestrator import MobileOrchestrator

        orchestrator = MobileOrchestrator(
            agent_service=MagicMock(),
            conversation_id="c1",
            user_id="u1",
            user_message="msg",
            assistant_message_id="am1",
            user_message_id="um1",
            db=None,
        )
        assert orchestrator is not None
