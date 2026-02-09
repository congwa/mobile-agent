"""CLI 交互模式 - 命令行中输入自然语言指令，Agent 自主操作手机"""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from mobile_agent.core.config import get_settings
from mobile_agent.core.service import MobileAgentService

logger = logging.getLogger(__name__)


def _format_tool_args(args: dict) -> str:
    """格式化工具参数用于打印"""
    if not args:
        return ""
    parts = []
    for k, v in args.items():
        if isinstance(v, str) and len(v) > 50:
            v = v[:50] + "..."
        parts.append(f"{k}={v!r}")
    return ", ".join(parts)


async def run_cli() -> None:
    """运行 CLI 交互模式"""
    settings = get_settings()

    # 初始化 Agent 服务
    service = MobileAgentService()
    print("🔌 正在连接 MCP Server...")
    try:
        await service.initialize(settings)
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return

    status = service.get_status()
    print(f"✅ 连接成功，获取到 {status['tools_count']} 个工具")
    print()
    print("🤖 Mobile Agent 已启动，输入任务开始操作手机")
    print("   输入 'quit' 或 'exit' 退出")
    print("   输入 'status' 查看状态")
    print("   输入 'new' 开始新会话")
    print()

    conversation_id = str(uuid.uuid4())

    try:
        while True:
            try:
                user_input = input("👤 > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n👋 再见！")
                break

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit"):
                print("👋 再见！")
                break

            if user_input.lower() == "status":
                s = service.get_status()
                print(f"  MCP 连接: {'✅' if s['mcp_connected'] else '❌'}")
                print(f"  工具数量: {s['tools_count']}")
                print(f"  会话 ID: {conversation_id}")
                continue

            if user_input.lower() == "new":
                conversation_id = str(uuid.uuid4())
                print(f"  🆕 新会话: {conversation_id[:8]}...")
                continue

            # 发送消息给 Agent
            print()
            try:
                async for event in service.chat_stream(
                    message=user_input,
                    conversation_id=conversation_id,
                ):
                    msg = event[0] if isinstance(event, tuple) else event

                    if isinstance(msg, AIMessage):
                        # 打印助手文本
                        content = getattr(msg, "content", "")
                        if content:
                            print(f"🤖 {content}")

                        # 打印工具调用
                        tool_calls = getattr(msg, "tool_calls", [])
                        for tc in tool_calls:
                            args_str = _format_tool_args(tc.get("args", {}))
                            print(f"  🔧 {tc['name']}({args_str})")

                    elif isinstance(msg, ToolMessage):
                        # 打印工具结果（简略）
                        tool_name = getattr(msg, "name", "")
                        content = str(getattr(msg, "content", ""))
                        # 截图结果不打印完整内容
                        if "screenshot" in tool_name.lower() and len(content) > 200:
                            print(f"  📸 {tool_name} → [截图数据 {len(content)} 字符]")
                        else:
                            preview = content[:150]
                            if len(content) > 150:
                                preview += "..."
                            print(f"  ← {tool_name}: {preview}")

            except Exception as e:
                logger.exception("Agent 执行出错")
                print(f"\n❌ 执行出错: {e}")

            print()

    finally:
        print("🔌 正在断开连接...")
        await service.shutdown()
        print("✅ 已断开")


def main() -> None:
    """CLI 入口"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )
    # 降低第三方库的日志级别
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)

    asyncio.run(run_cli())


if __name__ == "__main__":
    main()
