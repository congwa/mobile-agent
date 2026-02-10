"""App 长流程端到端测试 - com.im30.way

使用 TestExecutorMiddleware 状态机驱动测试执行。
用户提供结构化测试用例文本，Agent 自动逐步执行。

测试流程:
    1. 打开 com.im30.way App
    2. 点击消息
    3. 点击立即登录
    验证点: 显示登录或注册

运行方式:
    cd agent-app
    uv run python tests/test_app_flow.py

前提条件:
    1. 手机已连接电脑（USB/WiFi）
    2. agent-app/.env 已配置 LLM API Key
    3. com.im30.way 已安装在设备上
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

# ── 强制无缓冲输出 ──
import builtins
_original_print = builtins.print
def _flush_print(*args, **kwargs):
    kwargs.setdefault('flush', True)
    _original_print(*args, **kwargs)
builtins.print = _flush_print

# ── 路径常量 ──────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent          # mobile-mcp/
AGENT_APP_ROOT = Path(__file__).resolve().parent.parent               # mobile-mcp/agent-app/
MCP_SERVER_SCRIPT = PROJECT_ROOT / "mcp_tools" / "mcp_server.py"
MCP_VENV_PYTHON = PROJECT_ROOT / ".venv_bundle" / "bin" / "python"
MCP_SSE_PORT = 3199
MCP_SSE_URL = f"http://localhost:{MCP_SSE_PORT}/sse"

# 确保 agent-app/src 在 import path 中
_src = str(AGENT_APP_ROOT / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

APP_PACKAGE = "com.im30.way"

# ── 结构化测试用例文本 ────────────────────────────────────────

TEST_CASE_TEXT = """测试任务名称：测试 com.im30.way 登录流程\t
前置条件：com.im30.way 处于关闭状态\t
测试步骤：
1. 打开App
2. 等待3秒
3. 关闭弹窗
4. 点击消息
5. 点击立即登录\t
验证点：显示"登录"或"注册"\t\t\tcom.im30.way
"""


# ── 工具函数 ──────────────────────────────────────────────────────────

def _wait_for_mcp_server(port: int, timeout: int = 30) -> bool:
    """等待 MCP Server 端口可用"""
    import socket
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("localhost", port), timeout=2):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.5)
    return False


def _start_mcp_server() -> subprocess.Popen:
    """启动 MCP Server 子进程"""
    python_bin = str(MCP_VENV_PYTHON) if MCP_VENV_PYTHON.exists() else sys.executable
    proc = subprocess.Popen(
        [python_bin, str(MCP_SERVER_SCRIPT), "--sse", "--port", str(MCP_SSE_PORT)],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
    )
    return proc


async def run_app_flow_test():
    """使用 TestExecutorMiddleware 状态机执行测试用例"""

    print("=" * 60)
    print(f"App 流程测试 (TestExecutorMiddleware): {APP_PACKAGE}")
    print("=" * 60)

    # ── 1. 启动 MCP Server ──
    print(f"\n启动 MCP Server (port={MCP_SSE_PORT})...")
    proc = _start_mcp_server()

    try:
        ready = _wait_for_mcp_server(MCP_SSE_PORT, timeout=30)
        if not ready:
            stderr = proc.stderr.read().decode() if proc.stderr else ""
            print(f"MCP Server 未就绪\n{stderr}")
            return
        if proc.poll() is not None:
            stderr = proc.stderr.read().decode() if proc.stderr else ""
            print(f"MCP Server 启动失败:\n{stderr}")
            return
        print(f"MCP Server 就绪: {MCP_SSE_URL}")

        # ── 2. 初始化 Agent Service ──
        from mobile_agent.core.config import MCPConfig, Settings, LLMConfig, AgentConfig
        from mobile_agent.core.service import MobileAgentService

        settings = Settings(
            llm=LLMConfig(),
            mcp=MCPConfig(url=MCP_SSE_URL),
            agent=AgentConfig(),
        )

        service = MobileAgentService()
        await service.initialize(settings)

        status = service.get_status()
        print(f"Agent 就绪: tools={status['tools_count']}")

        # ── 3. 解析测试用例（预览）──
        from mobile_agent.models.test_case import parse_test_case

        test_case = parse_test_case(TEST_CASE_TEXT)
        print(f"\n测试用例: {test_case.name}")
        print(f"前置条件: {test_case.preconditions}")
        print(f"步骤数: {len(test_case.steps)}")
        print(f"验证点: {test_case.verifications}")
        print(f"App包名: {test_case.app_package}")
        for s in test_case.steps:
            print(f"  {s.index}. [{s.action.value}] {s.target} -> {s.mcp_tool_hint}")

        # ── 4. 执行测试用例 ──
        conversation_id = f"test-flow-{uuid.uuid4().hex[:8]}"
        print(f"\n开始执行测试 (conversation_id={conversation_id})...")
        print("-" * 60)

        result = await service.run_test_case(
            test_case_text=TEST_CASE_TEXT,
            conversation_id=conversation_id,
        )

        # ── 5. 输出结果 ──
        await service.shutdown()

        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)

        phase = result.get("phase", "unknown")
        passed = result.get("passed", False)
        step_results = result.get("step_results", [])
        total = result.get("total_steps", 0)

        passed_count = sum(1 for sr in step_results if sr.get("passed"))
        status_str = "PASS" if passed else "FAIL"

        print(f"  测试用例: {result.get('test_case', '')}")
        print(f"  最终状态: {phase}")
        print(f"  测试结果: {status_str}")
        print(f"  通过步骤: {passed_count}/{total}")
        print()

        for sr in step_results:
            icon = "PASS" if sr.get("passed") else "FAIL"
            raw = sr.get("raw_text", f"{sr['action']} {sr.get('target', '')}")
            print(f"  [{icon}] 步骤 {sr['index'] + 1}: {raw}")

        print()
        if passed:
            print("全部测试步骤通过!")
        else:
            failed_steps = [sr for sr in step_results if not sr.get("passed")]
            print(f"{len(failed_steps)} 个步骤失败")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("MCP Server 已关闭")


if __name__ == "__main__":
    # 加载 .env
    env_file = AGENT_APP_ROOT / ".env"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)

    asyncio.run(run_app_flow_test())
