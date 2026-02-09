"""Agent 构建器 - 使用 langchain.agents.create_agent 构建移动端 Agent"""

from __future__ import annotations

import logging
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.tools import BaseTool

from mobile_agent.core.config import LLMConfig
from mobile_agent.middleware.operation_logger import OperationLoggerMiddleware
from mobile_agent.middleware.retry import RetryMiddleware
from mobile_agent.middleware.screenshot_optimizer import ScreenshotOptimizerMiddleware
from mobile_agent.prompts.system_prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def get_default_middlewares() -> list[AgentMiddleware]:
    """获取默认中间件列表"""
    return [
        OperationLoggerMiddleware(),
        ScreenshotOptimizerMiddleware(),
        RetryMiddleware(),
    ]


def build_mobile_agent(
    tools: list[BaseTool],
    llm_config: LLMConfig,
    *,
    middlewares: list[AgentMiddleware] | None = None,
    system_prompt: str | None = None,
    checkpointer: Any | None = None,
) -> Any:
    """构建移动端 Agent

    使用 langchain.agents.create_agent()（对 langgraph 的高层封装），
    而不是直接使用 langgraph.prebuilt.create_react_agent。

    Args:
        tools: MCP 适配器获取的 LangChain BaseTool 列表
        llm_config: LLM 配置
        middlewares: AgentMiddleware 列表（默认使用内置中间件）
        system_prompt: 系统提示词（默认使用内置提示词）
        checkpointer: 会话记忆检查点器（默认使用 MemorySaver）

    Returns:
        编译好的 LangGraph CompiledStateGraph（Agent 实例）
    """
    if middlewares is None:
        middlewares = get_default_middlewares()

    if system_prompt is None:
        system_prompt = SYSTEM_PROMPT

    if checkpointer is None:
        msg = "checkpointer 不能为 None，请传入 AsyncSqliteSaver 或 MemorySaver"
        raise ValueError(msg)

    logger.info("构建 Agent: model=%s, tools=%d, middlewares=%d", llm_config.model, len(tools), len(middlewares))

    model_instance = _create_model_instance(llm_config)

    agent = create_agent(
        model=model_instance,
        tools=tools,
        system_prompt=system_prompt,
        middleware=middlewares,
        checkpointer=checkpointer,
    )

    logger.info("Agent 构建完成")
    return agent


def _create_model_instance(llm_config: LLMConfig) -> Any:
    """使用 langgraph-agent-kit 的 create_chat_model 统一创建模型实例"""
    model_str = llm_config.model

    # 解析 provider:model 格式
    if ":" in model_str:
        provider, model_name = model_str.split(":", 1)
    else:
        provider = "openai"
        model_name = model_str

    # 如果有自定义 base_url 或 api_key，使用 SDK 工厂
    if llm_config.base_url or llm_config.api_key:
        from langgraph_agent_kit import create_chat_model

        return create_chat_model(
            model=model_name,
            base_url=llm_config.base_url,
            api_key=llm_config.api_key,
            provider=provider,
        )

    # 无自定义配置时，使用 init_chat_model
    from langchain.chat_models import init_chat_model

    return init_chat_model(model_str)
