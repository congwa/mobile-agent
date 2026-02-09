"""Mobile 流编排器 - 继承 SDK 的 BaseOrchestrator

将 Agent 产生的 LangChain 消息编排为标准 StreamEvent 流。
使用 MobileResponseHandler 处理截图等业务逻辑。

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

from langgraph_agent_kit.streaming.orchestrator import BaseOrchestrator


class MobileOrchestrator(BaseOrchestrator):
    """Mobile 专用流编排器

    直接使用 BaseOrchestrator，通过 db 参数向下传递 service 引用。
    无需覆盖任何方法 — BaseOrchestrator._create_context 会将 db 注入到
    ChatContext.db 中，service.chat_emit 再从 context.db 获取。
    """

    pass
