"""配置管理 - 使用 pydantic-settings 管理环境变量"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """LLM 配置"""

    model_config = SettingsConfigDict(env_prefix="LLM_")

    model: str = Field(default="openai:gpt-4o", description="langchain 模型字符串，如 openai:gpt-4o")
    api_key: str = Field(default="", description="LLM API Key")
    base_url: str = Field(default="", description="LLM API Base URL（可选）")


class MCPConfig(BaseSettings):
    """MCP Server 连接配置（SSE 模式）

    Backend 通过 SSE 连接到独立运行的 MCP Server。
    MCP Server 由 Electron 主进程或用户手动启动。
    """

    model_config = SettingsConfigDict(env_prefix="MCP_SERVER_")

    url: str = Field(
        default="http://localhost:3100/sse",
        description="MCP Server SSE 端点 URL",
    )


class AgentConfig(BaseSettings):
    """Agent 行为配置"""

    model_config = SettingsConfigDict(env_prefix="AGENT_")

    host: str = Field(default="0.0.0.0", description="HTTP 服务地址")
    port: int = Field(default=8088, description="HTTP 服务端口")
    max_iterations: int = Field(default=20, description="Agent 最大迭代次数（防止死循环）")


class Settings(BaseSettings):
    """全局配置聚合"""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)


@lru_cache
def get_settings() -> Settings:
    """获取全局配置（单例）"""
    # 加载 .env 文件
    env_file = Path(__file__).resolve().parent.parent.parent.parent / ".env"
    if env_file.exists():
        from dotenv import load_dotenv

        load_dotenv(env_file)

    return Settings()
