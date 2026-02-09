"""Agent 服务 - 管理 Agent 生命周期（参考 embedease-ai 的 AgentService）"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage

from mobile_agent.core.agent_builder import build_mobile_agent
from mobile_agent.core.config import Settings, get_settings
from mobile_agent.core.mcp_connection import MCPConnectionManager
from mobile_agent.core.storage import Storage
from mobile_agent.prompts.system_prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class MobileAgentService:
    """Agent 服务 - 单例模式，管理 Agent 生命周期

    参考 embedease-ai 的 AgentService 设计：
    1. 管理 MCP 连接
    2. 构建和缓存 Agent 实例
    3. 提供聊天流接口
    4. 截图存储
    5. 会话持久化
    6. 运行时设置管理
    """

    _instance: MobileAgentService | None = None

    def __new__(cls) -> MobileAgentService:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._settings: Settings = get_settings()
        self._mcp_manager: MCPConnectionManager | None = None
        self._agent: Any = None
        self._start_time: float = 0.0
        self._checkpointer: Any = None
        self._storage = Storage()
        # 运行时中间件配置
        self._middleware_config: dict[str, Any] = {
            "operation_logger": True,
            "screenshot_optimizer": True,
            "screenshot_max_consecutive": 2,
            "retry": True,
            "retry_max_attempts": 2,
            "retry_interval": 1.0,
        }
        # 运行时 system prompt 覆盖
        self._runtime_system_prompt: str = ""

    @property
    def is_ready(self) -> bool:
        """Agent 是否就绪"""
        return self._agent is not None and self._mcp_manager is not None and self._mcp_manager.is_connected

    @property
    def agent(self) -> Any:
        """获取 Agent 实例"""
        if self._agent is None:
            msg = "Agent 未初始化，请先调用 initialize()"
            raise RuntimeError(msg)
        return self._agent

    async def initialize(self, settings: Settings | None = None) -> None:
        """初始化 MCP 连接和 Agent"""
        if settings is not None:
            self._settings = settings

        logger.info("正在初始化 MobileAgentService...")
        self._start_time = time.time()

        # 1. 初始化 Storage（应用业务数据）
        await self._storage.init()

        # 2. 初始化 Checkpointer（Agent 内部状态）
        self._checkpointer = await self._init_checkpointer()

        # 3. 连接 MCP Server
        self._mcp_manager = MCPConnectionManager(self._settings.mcp)
        tools = await self._mcp_manager.connect()

        # 4. 构建 Agent
        self._agent = build_mobile_agent(
            tools=tools,
            llm_config=self._settings.llm,
            checkpointer=self._checkpointer,
        )

        logger.info("MobileAgentService 初始化完成")

    async def _init_checkpointer(self) -> Any:
        """初始化 LangGraph Checkpointer（AsyncSqliteSaver）"""
        import aiosqlite
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        base = Path(__file__).resolve().parent.parent.parent.parent
        data_dir = base / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        db_path = str(data_dir / "checkpoint.db")

        conn = await aiosqlite.connect(db_path)
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA synchronous=NORMAL")
        await conn.execute("PRAGMA busy_timeout=30000")

        checkpointer = AsyncSqliteSaver(conn)
        await checkpointer.setup()
        logger.info("Checkpointer 初始化完成: %s", db_path)
        return checkpointer

    async def shutdown(self) -> None:
        """关闭服务"""
        if self._mcp_manager is not None:
            await self._mcp_manager.disconnect()
            self._mcp_manager = None
        self._agent = None
        await self._storage.close()
        if self._checkpointer is not None:
            try:
                await self._checkpointer.conn.close()
            except Exception:
                pass
            self._checkpointer = None
        logger.info("MobileAgentService 已关闭")

    # ── Chat ──────────────────────────────────────────────────

    async def chat(
        self,
        *,
        message: str,
        conversation_id: str,
    ) -> Any:
        """同步聊天（非流式），返回最终结果

        Args:
            message: 用户消息
            conversation_id: 会话 ID

        Returns:
            Agent 最终响应
        """
        config = {"configurable": {"thread_id": conversation_id}}
        result = await self.agent.ainvoke(
            {"messages": [HumanMessage(content=message)]},
            config=config,
        )
        return result

    async def chat_stream(
        self,
        *,
        message: str,
        conversation_id: str,
    ):
        """流式聊天，逐步返回 Agent 的消息

        Args:
            message: 用户消息
            conversation_id: 会话 ID

        Yields:
            Agent 流式消息事件
        """
        config = {"configurable": {"thread_id": conversation_id}}

        async for event in self.agent.astream(
            {"messages": [HumanMessage(content=message)]},
            config=config,
            stream_mode="messages",
        ):
            yield event

    async def chat_emit(
        self,
        *,
        message: str,
        conversation_id: str,
        user_id: str = "",
        context: Any = None,
        agent_id: str | None = None,
    ) -> None:
        """通过 emitter 推送事件的聊天接口（供 Orchestrator 使用）

        使用 MobileResponseHandler 处理 Agent 流式输出，
        自动将 AIMessage/ToolMessage 转换为 SDK 标准事件。

        Args:
            message: 用户消息
            conversation_id: 会话 ID
            user_id: 用户 ID
            context: ChatContext（含 emitter）
            agent_id: Agent ID（未使用）
        """
        from mobile_agent.streaming.response_handler import MobileResponseHandler

        emitter = getattr(context, "emitter", None)
        if emitter is None:
            msg = "chat_emit 需要 context.emitter"
            raise ValueError(msg)

        # context.db 携带 service 引用（由 orchestrator 通过 db= 注入）
        svc = getattr(context, "db", None) or self

        handler = MobileResponseHandler(
            emitter=emitter,
            conversation_id=conversation_id,
        )
        handler.service = svc

        # 持久化用户消息
        await svc.add_message(conversation_id, "user", message)

        config = {"configurable": {"thread_id": conversation_id}}

        async for event in self.agent.astream(
            {"messages": [HumanMessage(content=message)]},
            config=config,
            stream_mode="messages",
        ):
            msg_obj = event[0] if isinstance(event, tuple) else event
            await handler.handle_message(msg_obj)

        result = await handler.finalize()

        # 持久化 AI 回复
        ai_content = result.get("content", "")
        if ai_content:
            await svc.add_message(conversation_id, "assistant", ai_content)
        await emitter.aemit("__end__", None)

    # ── Status ────────────────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        """获取服务状态（增强版）"""
        tools = self._mcp_manager.tools if self._mcp_manager else []
        uptime = time.time() - self._start_time if self._start_time else 0.0
        return {
            "ready": self.is_ready,
            "mcp_connected": self._mcp_manager.is_connected if self._mcp_manager else False,
            "tools_count": len(tools),
            "tool_names": [t.name for t in tools],
            "tools": [
                {"name": t.name, "description": t.description or ""}
                for t in tools
            ],
            "mcp_url": self._settings.mcp.url,
            "uptime_seconds": round(uptime, 1),
        }

    # ── Devices ─────────────────────────────────────────────

    async def get_devices(self) -> list[dict[str, Any]]:
        """通过 MCP 工具获取真实设备信息"""
        if not self._mcp_manager or not self._mcp_manager.is_connected:
            return []

        # 查找 mobile_list_devices 工具
        tool = None
        for t in self._mcp_manager.tools:
            if t.name == "mobile_list_devices":
                tool = t
                break

        if tool is None:
            return []

        try:
            import json
            result = await tool.ainvoke({})
            # 结果可能是 JSON 字符串或 dict
            if isinstance(result, str):
                data = json.loads(result)
            else:
                data = result

            # 标准化为列表
            devices_raw = data if isinstance(data, list) else data.get("devices", [data])
            devices = []
            for d in devices_raw:
                if isinstance(d, dict):
                    devices.append({
                        "id": d.get("serial", d.get("id", "unknown")),
                        "name": d.get("name", d.get("model", "Mobile Device")),
                        "platform": d.get("platform", "Android"),
                        "version": d.get("version", d.get("android_version", "")),
                        "resolution": d.get("resolution", ""),
                        "connected": d.get("connected", True),
                    })
            return devices
        except Exception as e:
            logger.warning("获取设备列表失败: %s", e)
            return []

    # ── Screenshot ────────────────────────────────────────────

    async def store_screenshot(self, data: str) -> str:
        """存储截图数据，返回 screenshot_id

        Args:
            data: base64 编码的截图数据

        Returns:
            截图 ID
        """
        return await self._storage.save_screenshot(data)

    async def get_screenshot(self, screenshot_id: str) -> str | None:
        """获取截图数据

        Args:
            screenshot_id: 截图 ID

        Returns:
            base64 编码的截图数据，不存在则返回 None
        """
        return await self._storage.get_screenshot(screenshot_id)

    # ── Conversations ─────────────────────────────────────────

    async def save_conversation(
        self,
        conversation_id: str,
        title: str,
        *,
        status: str = "success",
        steps: int = 0,
        duration: str = "",
    ) -> None:
        """保存会话记录"""
        await self._storage.save_conversation(
            conversation_id, title, status=status, steps=steps, duration=duration,
        )

    async def list_conversations(self, *, query: str = "") -> list[dict[str, Any]]:
        """列出会话记录"""
        return await self._storage.list_conversations(query)

    async def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        """获取会话详情（含消息）"""
        return await self._storage.get_conversation(conversation_id)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """删除会话"""
        return await self._storage.delete_conversation(conversation_id)

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        *,
        tool_name: str = "",
        has_image: bool = False,
    ) -> str:
        """添加消息到会话"""
        return await self._storage.add_message(
            conversation_id, role, content, tool_name=tool_name, has_image=has_image,
        )

    # ── Settings ──────────────────────────────────────────────

    def get_settings_snapshot(self) -> dict[str, Any]:
        """获取当前设置快照"""
        s = self._settings
        return {
            "llm": {
                "model": s.llm.model,
                "api_key": _mask_key(s.llm.api_key),
                "base_url": s.llm.base_url,
            },
            "mcp": {
                "url": s.mcp.url,
            },
            "agent": {
                "max_iterations": s.agent.max_iterations,
                "system_prompt": self._runtime_system_prompt or SYSTEM_PROMPT,
            },
            "middleware": dict(self._middleware_config),
        }

    def update_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        """更新运行时设置

        Args:
            updates: 设置更新字典

        Returns:
            更新后的设置快照
        """
        if "llm" in updates and updates["llm"] is not None:
            llm_data = updates["llm"]
            if "model" in llm_data:
                self._settings.llm.model = llm_data["model"]
            if "api_key" in llm_data and llm_data["api_key"]:
                self._settings.llm.api_key = llm_data["api_key"]
            if "base_url" in llm_data:
                self._settings.llm.base_url = llm_data["base_url"]

        if "mcp" in updates and updates["mcp"] is not None:
            mcp_data = updates["mcp"]
            if "url" in mcp_data:
                self._settings.mcp.url = mcp_data["url"]

        if "agent" in updates and updates["agent"] is not None:
            agent_data = updates["agent"]
            if "max_iterations" in agent_data:
                self._settings.agent.max_iterations = agent_data["max_iterations"]
            if "system_prompt" in agent_data:
                self._runtime_system_prompt = agent_data["system_prompt"]

        if "middleware" in updates and updates["middleware"] is not None:
            self._middleware_config.update(updates["middleware"])

        return self.get_settings_snapshot()

    @property
    def middleware_config(self) -> dict[str, Any]:
        """获取中间件配置"""
        return dict(self._middleware_config)

    async def reconnect_mcp(self) -> dict[str, Any]:
        """重新连接 MCP Server

        Returns:
            连接结果
        """
        try:
            # 每次重连都用最新配置，确保 URL 变更后生效
            if self._mcp_manager is not None:
                await self._mcp_manager.disconnect()
            self._mcp_manager = MCPConnectionManager(self._settings.mcp)
            tools = await self._mcp_manager.connect()
            # 重建 Agent
            self._agent = build_mobile_agent(
                tools=tools,
                llm_config=self._settings.llm,
                checkpointer=self._checkpointer,
            )
            return {
                "success": True,
                "message": f"MCP 重新连接成功，获取到 {len(tools)} 个工具",
                "tools_count": len(tools),
            }
        except Exception as e:
            logger.error("MCP 重新连接失败: %s", e)
            return {
                "success": False,
                "message": f"MCP 重新连接失败: {e}",
                "tools_count": 0,
            }


def _mask_key(key: str) -> str:
    """遮蔽 API Key，只显示前 4 和后 4 位"""
    if not key or len(key) <= 8:
        return "***"
    return f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}"


def get_agent_service() -> MobileAgentService:
    """获取 Agent 服务单例"""
    return MobileAgentService()
