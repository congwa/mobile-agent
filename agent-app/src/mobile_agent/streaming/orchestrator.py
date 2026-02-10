"""Mobile 流编排器 - 继承 SDK 的 BaseOrchestrator

将 Agent 产生的 LangChain 消息编排为标准 StreamEvent 流。
使用 MobileResponseHandler 处理截图等业务逻辑。

重写 run() 以支持：
- 客户端断开（前端点击停止）时取消 producer_task，终止 Agent 执行
- 通过 abort API 外部取消正在运行的任务

用法：
    orchestrator = MobileOrchestrator(
        agent_service=service,       # MobileAgentService（需有 chat_emit）
        conversation_id=conv_id,
        user_id="default",
        user_message="打开微信",
        assistant_message_id=str(uuid4()),
        db=service,                  # 同一个 service 作为 db 传入 ChatContext
    )
    return create_sse_response(orchestrator.run())

db 字段在 ChatContext 中保存 service 引用，
service.chat_emit() 中通过 handler.service = context.db 访问。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

from langgraph_agent_kit.core.emitter import QueueDomainEmitter
from langgraph_agent_kit.core.events import StreamEventType
from langgraph_agent_kit.core.stream_event import StreamEvent
from langgraph_agent_kit.streaming.orchestrator import BaseOrchestrator
from langgraph_agent_kit.streaming.sse import make_event

logger = logging.getLogger(__name__)

# 全局注册表：conversation_id → asyncio.Task（用于外部取消）
_running_tasks: dict[str, asyncio.Task] = {}


def cancel_conversation(conversation_id: str) -> bool:
    """取消指定会话的 Agent 任务

    Returns:
        True 如果成功取消，False 如果没有运行中的任务
    """
    task = _running_tasks.pop(conversation_id, None)
    if task and not task.done():
        task.cancel()
        logger.info("MobileOrchestrator: 已取消会话 %s 的 Agent 任务", conversation_id)
        return True
    return False


class MobileOrchestrator(BaseOrchestrator):
    """Mobile 专用流编排器

    重写 run() 以在 SSE 连接断开时正确取消 producer_task，
    防止 Agent 在后台继续执行手机操作。
    """

    async def run(self) -> AsyncGenerator[StreamEvent, None]:
        """运行编排流程（增强版：支持取消）"""
        # 1) 发送 meta.start
        yield make_event(
            seq=self._next_seq(),
            conversation_id=self._conversation_id,
            message_id=self._assistant_message_id,
            type=StreamEventType.META_START.value,
            payload={
                "user_message_id": self._user_message_id,
                "assistant_message_id": self._assistant_message_id,
            },
        )

        producer_task: asyncio.Task | None = None

        try:
            loop = asyncio.get_running_loop()
            domain_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(
                maxsize=self._event_queue_size
            )
            emitter = QueueDomainEmitter(queue=domain_queue, loop=loop)
            context = self._create_context(emitter)

            # 2) 启动 Agent 任务
            producer_task = asyncio.create_task(
                self._agent_service.chat_emit(
                    message=self._user_message,
                    conversation_id=self._conversation_id,
                    user_id=self._user_id,
                    context=context,
                    agent_id=self._agent_id,
                )
            )

            # 注册到全局表，允许外部取消
            _running_tasks[self._conversation_id] = producer_task

            # 3) 消费事件队列
            while True:
                try:
                    evt = await asyncio.wait_for(domain_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    # 检查 producer_task 是否已完成（异常终止）
                    if producer_task.done():
                        exc = producer_task.exception()
                        if exc:
                            raise exc
                        break
                    continue

                evt_type = evt.get("type")
                if evt_type == "__end__":
                    break

                payload = evt.get("payload", {})

                yield make_event(
                    seq=self._next_seq(),
                    conversation_id=self._conversation_id,
                    message_id=self._assistant_message_id,
                    type=evt_type,
                    payload=payload,
                )

            await producer_task

        except asyncio.CancelledError:
            logger.info("MobileOrchestrator: 会话 %s 被取消", self._conversation_id)
        except Exception as e:
            logger.error("MobileOrchestrator: 会话 %s 异常: %s", self._conversation_id, e)
            yield make_event(
                seq=self._next_seq(),
                conversation_id=self._conversation_id,
                message_id=self._assistant_message_id,
                type=StreamEventType.ERROR.value,
                payload={"message": str(e)},
            )
        finally:
            # 关键：无论什么原因退出（客户端断开、异常、正常结束），都取消 producer_task
            _running_tasks.pop(self._conversation_id, None)
            if producer_task and not producer_task.done():
                producer_task.cancel()
                logger.info(
                    "MobileOrchestrator: 会话 %s — 已取消后台 Agent 任务",
                    self._conversation_id,
                )
                try:
                    await producer_task
                except (asyncio.CancelledError, Exception):
                    pass
