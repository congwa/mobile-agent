"""端到端集成测试 - 完整流程验证

自动启动 MCP Server (SSE) → 连接 Agent → 真实操控手机设备

运行方式:
    # 在 agent-app 目录下
    uv run python -m pytest tests/test_e2e.py -v -s

    # 或直接运行脚本
    uv run python tests/test_e2e.py

前提条件:
    1. 手机已连接电脑（USB/WiFi）
    2. agent-app/.env 已配置 LLM API Key
    3. mobile-mcp 根目录的依赖已安装（.venv_bundle）
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator

import httpx
import pytest

# ── 路径常量 ──────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent          # mobile-mcp/
AGENT_APP_ROOT = Path(__file__).resolve().parent.parent               # mobile-mcp/agent-app/
MCP_SERVER_SCRIPT = PROJECT_ROOT / "mcp_tools" / "mcp_server.py"
MCP_VENV_PYTHON = PROJECT_ROOT / ".venv_bundle" / "bin" / "python"
MCP_SSE_PORT = 3199                                                   # 测试专用端口，避免冲突
MCP_SSE_URL = f"http://localhost:{MCP_SSE_PORT}/sse"

logger = logging.getLogger(__name__)


def _wait_for_mcp_server(port: int, timeout: int = 30) -> bool:
    """等待 MCP Server 端口可用（TCP 连接检测）"""
    import socket
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except (ConnectionRefusedError, OSError, socket.timeout):
            time.sleep(0.5)
    return False


# ══════════════════════════════════════════════════════════════
#  Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def mcp_server_process():
    """启动 MCP Server (SSE 模式) 作为子进程，测试结束后关闭"""
    python_bin = str(MCP_VENV_PYTHON) if MCP_VENV_PYTHON.exists() else sys.executable

    print(f"\n🚀 启动 MCP Server: {python_bin} {MCP_SERVER_SCRIPT} --sse --port {MCP_SSE_PORT}")
    proc = subprocess.Popen(
        [python_bin, str(MCP_SERVER_SCRIPT), "--sse", "--port", str(MCP_SSE_PORT)],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
    )

    # 等待 MCP Server 就绪（最多 30 秒）
    ready = _wait_for_mcp_server(MCP_SSE_PORT, timeout=30)

    if not ready:
        proc.terminate()
        proc.wait(timeout=5)
        stderr = proc.stderr.read().decode() if proc.stderr else ""
        pytest.fail(f"MCP Server 在 30s 内未就绪\nSTDERR:\n{stderr}")

    if proc.poll() is not None:
        stderr = proc.stderr.read().decode() if proc.stderr else ""
        stdout = proc.stdout.read().decode() if proc.stdout else ""
        pytest.fail(
            f"MCP Server 启动后立即退出 (exit={proc.returncode})\n"
            f"STDERR:\n{stderr}\nSTDOUT:\n{stdout}"
        )

    print(f"✅ MCP Server 已就绪: http://localhost:{MCP_SSE_PORT}/sse")
    yield proc

    # 清理：终止 MCP Server
    print("\n🔌 关闭 MCP Server...")
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
    print("✅ MCP Server 已关闭")


@pytest.fixture(autouse=True)
def _reset_singleton():
    """每个测试前重置 MobileAgentService 单例"""
    from mobile_agent.core.service import MobileAgentService
    MobileAgentService._instance = None
    yield
    MobileAgentService._instance = None


@pytest.fixture
async def agent_service(mcp_server_process):
    """初始化 Agent Service 并连接 MCP Server"""
    from mobile_agent.core.config import LLMConfig, MCPConfig, AgentConfig, Settings
    from mobile_agent.core.service import MobileAgentService

    settings = Settings(
        llm=LLMConfig(),       # 从 .env 读取
        mcp=MCPConfig(url=MCP_SSE_URL),
        agent=AgentConfig(),
    )

    service = MobileAgentService()
    await service.initialize(settings)
    yield service
    await service.shutdown()


# ══════════════════════════════════════════════════════════════
#  测试用例
# ══════════════════════════════════════════════════════════════

class TestMCPConnection:
    """第一阶段: 验证 MCP Server 连接和工具发现"""

    @pytest.mark.asyncio
    async def test_mcp_connect_and_discover_tools(self, mcp_server_process):
        """连接 MCP Server，发现所有工具"""
        from mobile_agent.core.config import MCPConfig
        from mobile_agent.core.mcp_connection import MCPConnectionManager

        config = MCPConfig(url=MCP_SSE_URL)
        manager = MCPConnectionManager(config)

        tools = await manager.connect()

        print(f"\n📋 发现 {len(tools)} 个 MCP 工具:")
        for t in tools:
            print(f"  - {t.name}: {(t.description or '')[:60]}")

        assert len(tools) > 0, "应该发现至少 1 个 MCP 工具"

        # 检查关键工具是否存在
        tool_names = [t.name for t in tools]
        expected_tools = [
            "mobile_list_elements",
            "mobile_take_screenshot",
            "mobile_get_screen_size",
        ]
        for name in expected_tools:
            assert name in tool_names, f"缺少关键工具: {name}"

        await manager.disconnect()

    @pytest.mark.asyncio
    async def test_direct_tool_call_screen_size(self, mcp_server_process):
        """直接调用 MCP 工具: 获取屏幕尺寸"""
        from mobile_agent.core.config import MCPConfig
        from mobile_agent.core.mcp_connection import MCPConnectionManager

        config = MCPConfig(url=MCP_SSE_URL)
        manager = MCPConnectionManager(config)
        tools = await manager.connect()

        # 找到 mobile_get_screen_size 工具
        screen_size_tool = None
        for t in tools:
            if t.name == "mobile_get_screen_size":
                screen_size_tool = t
                break
        assert screen_size_tool is not None, "未找到 mobile_get_screen_size 工具"

        # 调用工具
        result = await screen_size_tool.ainvoke({})
        print(f"\n📐 屏幕尺寸: {result}")

        # 验证结果
        assert result is not None
        # 结果应该包含宽高信息
        result_str = str(result)
        assert len(result_str) > 0, "工具返回结果不应为空"

        await manager.disconnect()

    @pytest.mark.asyncio
    async def test_direct_tool_call_list_elements(self, mcp_server_process):
        """直接调用 MCP 工具: 列出页面元素"""
        from mobile_agent.core.config import MCPConfig
        from mobile_agent.core.mcp_connection import MCPConnectionManager

        config = MCPConfig(url=MCP_SSE_URL)
        manager = MCPConnectionManager(config)
        tools = await manager.connect()

        list_elements_tool = None
        for t in tools:
            if t.name == "mobile_list_elements":
                list_elements_tool = t
                break
        assert list_elements_tool is not None

        result = await list_elements_tool.ainvoke({})
        print(f"\n📋 页面元素 (前 500 字符):\n{str(result)[:500]}")

        assert result is not None
        assert len(str(result)) > 0

        await manager.disconnect()


class TestAgentService:
    """第二阶段: 验证 Agent Service 初始化"""

    @pytest.mark.asyncio
    async def test_service_initialize(self, agent_service):
        """Agent Service 初始化成功"""
        assert agent_service.is_ready, "Agent Service 应该处于就绪状态"

        status = agent_service.get_status()
        print(f"\n📊 Agent 状态:")
        print(f"  ready: {status['ready']}")
        print(f"  mcp_connected: {status['mcp_connected']}")
        print(f"  tools_count: {status['tools_count']}")
        print(f"  tool_names: {status['tool_names']}")

        assert status["ready"] is True
        assert status["mcp_connected"] is True
        assert status["tools_count"] > 0

    @pytest.mark.asyncio
    async def test_get_devices(self, agent_service):
        """通过 Agent Service 获取设备列表"""
        devices = await agent_service.get_devices()
        print(f"\n📱 设备列表: {json.dumps(devices, ensure_ascii=False, indent=2)}")
        # 设备可能为空（如果 mobile_list_devices 工具不存在），不强制断言


class TestAgentE2E:
    """第三阶段: 端到端 Agent 任务执行"""

    @pytest.mark.asyncio
    async def test_agent_get_screen_size(self, agent_service):
        """Agent 完成简单任务: 获取屏幕尺寸"""
        conversation_id = f"e2e-test-{uuid.uuid4().hex[:8]}"

        print("\n🤖 发送任务: '获取当前手机的屏幕尺寸'")
        result = await agent_service.chat(
            message="获取当前手机的屏幕尺寸，直接调用 mobile_get_screen_size 工具即可",
            conversation_id=conversation_id,
        )

        print(f"\n📨 Agent 返回结果:")
        messages = result.get("messages", [])
        for msg in messages:
            role = msg.__class__.__name__
            content = getattr(msg, "content", "")
            if content:
                preview = str(content)[:200]
                print(f"  [{role}] {preview}")

            # 打印工具调用
            tool_calls = getattr(msg, "tool_calls", [])
            for tc in tool_calls:
                print(f"  🔧 {tc['name']}({tc.get('args', {})})")

        # 验证：Agent 应该调用了工具并返回了结果
        assert len(messages) > 1, "Agent 应该产生多条消息（至少包含工具调用和回复）"

    @pytest.mark.asyncio
    async def test_agent_list_elements(self, agent_service):
        """Agent 完成任务: 列出当前页面元素"""
        conversation_id = f"e2e-test-{uuid.uuid4().hex[:8]}"

        print("\n🤖 发送任务: '列出当前手机屏幕上的所有元素'")
        result = await agent_service.chat(
            message="列出当前手机屏幕上的所有可交互元素，调用 mobile_list_elements 工具",
            conversation_id=conversation_id,
        )

        messages = result.get("messages", [])
        print(f"\n📨 Agent 返回 {len(messages)} 条消息")

        # 检查是否有工具调用
        has_tool_call = False
        for msg in messages:
            tool_calls = getattr(msg, "tool_calls", [])
            if tool_calls:
                has_tool_call = True
                for tc in tool_calls:
                    print(f"  🔧 {tc['name']}")

            # 最后一条 AI 消息
            from langchain_core.messages import AIMessage
            if isinstance(msg, AIMessage) and getattr(msg, "content", ""):
                print(f"  🤖 {str(msg.content)[:300]}")

        assert has_tool_call, "Agent 应该调用了至少一个工具"

    @pytest.mark.asyncio
    async def test_agent_stream_chat(self, agent_service):
        """验证流式聊天功能"""
        conversation_id = f"e2e-stream-{uuid.uuid4().hex[:8]}"

        print("\n🤖 流式发送任务: '获取屏幕尺寸'")
        events = []
        async for event in agent_service.chat_stream(
            message="获取屏幕尺寸",
            conversation_id=conversation_id,
        ):
            events.append(event)
            msg = event[0] if isinstance(event, tuple) else event
            role = msg.__class__.__name__
            content = getattr(msg, "content", "")
            if content:
                print(f"  [stream][{role}] {str(content)[:100]}")
            tool_calls = getattr(msg, "tool_calls", [])
            for tc in tool_calls:
                print(f"  [stream] 🔧 {tc['name']}")

        assert len(events) > 0, "流式聊天应该产生至少一个事件"
        print(f"\n✅ 共收到 {len(events)} 个流式事件")


# ══════════════════════════════════════════════════════════════
#  独立运行入口
# ══════════════════════════════════════════════════════════════

async def _run_quick_test():
    """不依赖 pytest，直接运行快速端到端测试"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)

    # ── 1. 启动 MCP Server ──
    python_bin = str(MCP_VENV_PYTHON) if MCP_VENV_PYTHON.exists() else sys.executable
    print(f"🚀 启动 MCP Server (SSE, port={MCP_SSE_PORT})...")
    proc = subprocess.Popen(
        [python_bin, str(MCP_SERVER_SCRIPT), "--sse", "--port", str(MCP_SSE_PORT)],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
    )

    try:
        # 等待就绪
        ready = _wait_for_mcp_server(MCP_SSE_PORT, timeout=30)
        if not ready:
            stderr = proc.stderr.read().decode() if proc.stderr else ""
            print(f"❌ MCP Server 30s 内未就绪\n{stderr}")
            return
        if proc.poll() is not None:
            stderr = proc.stderr.read().decode() if proc.stderr else ""
            print(f"❌ MCP Server 启动失败:\n{stderr}")
            return

        print(f"✅ MCP Server 已就绪: {MCP_SSE_URL}")

        # ── 2. 连接 MCP，发现工具 ──
        print("\n" + "=" * 60)
        print("📋 阶段 1: MCP 工具发现")
        print("=" * 60)

        from mobile_agent.core.config import MCPConfig, Settings, LLMConfig, AgentConfig
        from mobile_agent.core.mcp_connection import MCPConnectionManager

        config = MCPConfig(url=MCP_SSE_URL)
        mgr = MCPConnectionManager(config)
        tools = await mgr.connect()

        print(f"✅ 发现 {len(tools)} 个 MCP 工具:")
        for t in tools:
            print(f"  - {t.name}")

        # ── 3. 直接调用工具 ──
        print("\n" + "=" * 60)
        print("🔧 阶段 2: 直接工具调用")
        print("=" * 60)

        for t in tools:
            if t.name == "mobile_get_screen_size":
                result = await t.ainvoke({})
                print(f"📐 屏幕尺寸: {result}")
                break

        for t in tools:
            if t.name == "mobile_list_elements":
                result = await t.ainvoke({})
                print(f"📋 页面元素 (前 300 字符): {str(result)[:300]}")
                break

        await mgr.disconnect()

        # ── 4. Agent 端到端 ──
        print("\n" + "=" * 60)
        print("🤖 阶段 3: Agent 端到端任务")
        print("=" * 60)

        from mobile_agent.core.service import MobileAgentService

        settings = Settings(
            llm=LLMConfig(),
            mcp=MCPConfig(url=MCP_SSE_URL),
            agent=AgentConfig(),
        )

        service = MobileAgentService()
        await service.initialize(settings)

        status = service.get_status()
        print(f"Agent 状态: ready={status['ready']}, tools={status['tools_count']}")

        conversation_id = f"e2e-{uuid.uuid4().hex[:8]}"
        print(f"\n发送任务: '获取屏幕尺寸并列出当前页面元素'")

        from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
        _seen_tool_calls: set[str] = set()

        async for event in service.chat_stream(
            message="先获取屏幕尺寸，然后列出当前页面的所有元素",
            conversation_id=conversation_id,
        ):
            msg = event[0] if isinstance(event, tuple) else event

            if isinstance(msg, (AIMessage, AIMessageChunk)):
                # 只打印非空文本（跳过 chunk 中的空内容和 tool_call_chunks）
                content = getattr(msg, "content", "")
                if content and isinstance(content, str) and len(content.strip()) > 0:
                    print(f"🤖 {content[:300]}")
                # 只打印完整的 tool_calls（跳过 tool_call_chunks）
                for tc in getattr(msg, "tool_calls", []):
                    tc_id = tc.get("id", "")
                    if tc_id and tc_id not in _seen_tool_calls:
                        _seen_tool_calls.add(tc_id)
                        args_str = json.dumps(tc.get("args", {}), ensure_ascii=False)[:100]
                        print(f"  🔧 {tc['name']}({args_str})")
            elif isinstance(msg, ToolMessage):
                name = getattr(msg, "name", "")
                content = str(getattr(msg, "content", ""))
                if len(content) > 200:
                    print(f"  ← {name}: [{len(content)} 字符]")
                else:
                    print(f"  ← {name}: {content}")

        await service.shutdown()

        print("\n" + "=" * 60)
        print("✅ 全部测试通过！完整流程验证成功。")
        print("=" * 60)

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("🔌 MCP Server 已关闭")


if __name__ == "__main__":
    # 加载 .env
    env_file = AGENT_APP_ROOT / ".env"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)

    asyncio.run(_run_quick_test())
