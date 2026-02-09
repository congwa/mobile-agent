"""MCP 连接管理 - 通过 SSE 连接独立运行的 MCP Server"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from mobile_agent.core.config import MCPConfig

logger = logging.getLogger(__name__)


class MCPConnectionManager:
    """通过 SSE 连接独立运行的 MCP Server

    MCP Server 由 Electron 主进程或用户手动启动（--sse 模式），
    Backend 通过 SSE 端点连接，获取 LangChain BaseTool 列表。
    """

    def __init__(self, config: MCPConfig) -> None:
        self._config = config
        self._client: MultiServerMCPClient | None = None
        self._tools: list[BaseTool] = []

    @property
    def tools(self) -> list[BaseTool]:
        """获取已连接的工具列表"""
        return self._tools

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._client is not None

    @property
    def url(self) -> str:
        """MCP Server SSE 端点 URL"""
        return self._config.url

    async def connect(self) -> list[BaseTool]:
        """通过 SSE 连接 MCP Server，返回 LangChain BaseTool 列表"""
        if self._client is not None:
            logger.warning("MCP 连接已存在，先断开再重连")
            await self.disconnect()

        server_config: dict[str, Any] = {
            "mobile-mcp": {
                "url": self._config.url,
                "transport": "sse",
            }
        }

        logger.info("正在连接 MCP Server (SSE): %s", self._config.url)

        self._client = MultiServerMCPClient(server_config)
        self._tools = await self._client.get_tools()

        logger.info("MCP 连接成功，获取到 %d 个工具", len(self._tools))
        for tool in self._tools:
            logger.debug("  - %s: %s", tool.name, tool.description[:80] if tool.description else "")

        return self._tools

    async def disconnect(self) -> None:
        """断开 MCP 连接"""
        if self._client is not None:
            try:
                logger.info("MCP 连接已断开")
            except Exception as e:
                logger.warning("断开 MCP 连接时出错: %s", e)
            finally:
                self._client = None
                self._tools = []

    async def reconnect(self) -> list[BaseTool]:
        """重新连接"""
        await self.disconnect()
        return await self.connect()

    async def __aenter__(self) -> "MCPConnectionManager":
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.disconnect()
