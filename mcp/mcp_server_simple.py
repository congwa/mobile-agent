#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mobile MCP Server（重构版）- AI 可选

架构说明：
- 基础工具：不需要 AI 密钥，提供精确的元素操作
- 智能工具：需要 AI 密钥（可选），提供自然语言定位

用户可以选择：
1. 只用基础工具 → 不需要配置 AI
2. 启用智能功能 → 需要配置 AI（创建 .env 文件）
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

# 添加项目路径
mobile_mcp_dir = Path(__file__).parent.parent
project_root = mobile_mcp_dir.parent.parent
backend_dir = project_root / "backend"

sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

from mcp.types import Tool, TextContent
from mcp.server import Server
from mcp.server.stdio import stdio_server

from mobile_mcp.core.mobile_client import MobileClient
from mobile_mcp.core.basic_tools import BasicMobileTools
from mobile_mcp.core.smart_tools import SmartMobileTools


class SimpleMobileMCPServer:
    """简化的 Mobile MCP Server"""
    
    def __init__(self):
        """初始化 MCP Server"""
        self.client: Optional[MobileClient] = None
        self.basic_tools: Optional[BasicMobileTools] = None
        self.smart_tools: Optional[SmartMobileTools] = None
        self._initialized = False
    
    async def initialize(self):
        """延迟初始化设备连接"""
        if not self._initialized:
            # 初始化移动客户端
            self.client = MobileClient()
            
            # 初始化基础工具（总是可用）
            self.basic_tools = BasicMobileTools(self.client)
            
            # 初始化智能工具（检查 AI 可用性）
            self.smart_tools = SmartMobileTools(self.client)
            
            ai_status = self.smart_tools.get_ai_status()
            print(f"\n{ai_status['message']}\n", file=sys.stderr)
            
            self._initialized = True
    
    def get_tools(self):
        """注册 MCP 工具"""
        tools = []
        
        # ==================== 基础工具（不需要 AI）====================
        
        tools.extend([
            Tool(
                name="mobile_list_elements",
                description="📋 列出页面所有可交互元素（不需要 AI）。返回 resource_id, text, bounds 等信息，供后续精确操作使用。",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="mobile_click_by_id",
                description="👆 通过 resource-id 点击元素（不需要 AI）。精确可靠的点击方式。先用 mobile_list_elements 查找元素 ID。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "resource_id": {
                            "type": "string",
                            "description": "元素的 resource-id，如 'com.app:id/search_btn'"
                        }
                    },
                    "required": ["resource_id"]
                }
            ),
            Tool(
                name="mobile_click_by_text",
                description="👆 通过文本内容点击元素（不需要 AI）。适合文本完全匹配的场景。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "元素的文本内容（精确匹配），如 '登录'"
                        }
                    },
                    "required": ["text"]
                }
            ),
            Tool(
                name="mobile_click_at_coords",
                description="👆 点击指定坐标（不需要 AI）。可以从 mobile_list_elements 获取的 bounds 计算坐标。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "x": {
                            "type": "number",
                            "description": "X 坐标（像素）"
                        },
                        "y": {
                            "type": "number",
                            "description": "Y 坐标（像素）"
                        }
                    },
                    "required": ["x", "y"]
                }
            ),
            Tool(
                name="mobile_input_text_by_id",
                description="⌨️ 通过 resource-id 在输入框输入文本（不需要 AI）。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "resource_id": {
                            "type": "string",
                            "description": "输入框的 resource-id"
                        },
                        "text": {
                            "type": "string",
                            "description": "要输入的文本"
                        }
                    },
                    "required": ["resource_id", "text"]
                }
            ),
            Tool(
                name="mobile_find_elements_by_class",
                description="🔍 按类名查找元素（不需要 AI）。如查找所有输入框: 'android.widget.EditText'",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "class_name": {
                            "type": "string",
                            "description": "类名，如 'android.widget.EditText'"
                        }
                    },
                    "required": ["class_name"]
                }
            ),
            Tool(
                name="mobile_wait_for_element",
                description="⏳ 等待元素出现（不需要 AI）。用于等待页面加载完成。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "resource_id": {
                            "type": "string",
                            "description": "元素的 resource-id"
                        },
                        "timeout": {
                            "type": "number",
                            "description": "超时时间（秒），默认 10秒",
                            "default": 10
                        }
                    },
                    "required": ["resource_id"]
                }
            ),
            Tool(
                name="mobile_take_screenshot",
                description="📸 截取屏幕截图（不需要 AI）。用于 Cursor AI 视觉识别、调试或记录测试过程。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "截图描述（可选），用于生成文件名"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="mobile_take_screenshot_region",
                description="📸 截取屏幕指定区域（不需要 AI）。用于局部截图和分析。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "x1": {
                            "type": "number",
                            "description": "左上角X坐标"
                        },
                        "y1": {
                            "type": "number",
                            "description": "左上角Y坐标"
                        },
                        "x2": {
                            "type": "number",
                            "description": "右下角X坐标"
                        },
                        "y2": {
                            "type": "number",
                            "description": "右下角Y坐标"
                        },
                        "description": {
                            "type": "string",
                            "description": "截图描述（可选）"
                        }
                    },
                    "required": ["x1", "y1", "x2", "y2"]
                }
            ),
        ])
        
        # ==================== 智能工具（需要 AI，可选）====================
        
        tools.extend([
            Tool(
                name="mobile_smart_click",
                description="🤖 智能定位并点击（需要 AI 密钥，可选功能）。使用自然语言描述元素，如'右上角的设置按钮'。\n\n"
                           "⚠️ 如未配置 AI，请使用基础工具：mobile_list_elements + mobile_click_by_id",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "元素的自然语言描述，如 '顶部搜索框'、'登录按钮'"
                        }
                    },
                    "required": ["description"]
                }
            ),
            Tool(
                name="mobile_smart_input",
                description="🤖 智能定位输入框并输入（需要 AI 密钥，可选功能）。使用自然语言描述输入框。\n\n"
                           "⚠️ 如未配置 AI，请使用：mobile_input_text_by_id",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "输入框的自然语言描述，如 '用户名输入框'"
                        },
                        "text": {
                            "type": "string",
                            "description": "要输入的文本"
                        }
                    },
                    "required": ["description", "text"]
                }
            ),
            Tool(
                name="mobile_analyze_screenshot",
                description="🤖 使用 AI 分析截图并返回坐标（需要 AI 密钥，可选功能）。用于 Cursor AI 无法直接识别的复杂场景。\n\n"
                           "使用流程：\n"
                           "1. 先用 mobile_take_screenshot 截图\n"
                           "2. 调用此工具分析截图\n"
                           "3. 根据返回的坐标使用 mobile_click_at_coords 点击\n\n"
                           "⚠️ 需要配置支持视觉识别的 AI（GPT-4V、Claude 3、Qwen-VL）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "screenshot_path": {
                            "type": "string",
                            "description": "截图文件路径"
                        },
                        "description": {
                            "type": "string",
                            "description": "要查找的元素描述"
                        }
                    },
                    "required": ["screenshot_path", "description"]
                }
            ),
            Tool(
                name="mobile_get_ai_status",
                description="ℹ️ 获取 AI 功能状态。检查是否已配置 AI 密钥，智能工具是否可用。",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
        ])
        
        # ==================== 通用工具 ====================
        
        tools.extend([
            Tool(
                name="mobile_snapshot",
                description="📸 获取页面快照。查看当前页面结构和元素信息。",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="mobile_launch_app",
                description="🚀 启动应用",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "package_name": {
                            "type": "string",
                            "description": "应用包名"
                        }
                    },
                    "required": ["package_name"]
                }
            ),
            Tool(
                name="mobile_press_key",
                description="⌨️ 按键操作（home, back, enter 等）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "按键名称：home, back, enter, search"
                        }
                    },
                    "required": ["key"]
                }
            ),
            Tool(
                name="mobile_swipe",
                description="👆 滑动屏幕",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "direction": {
                            "type": "string",
                            "enum": ["up", "down", "left", "right"],
                            "description": "滑动方向"
                        }
                    },
                    "required": ["direction"]
                }
            ),
        ])
        
        return tools
    
    async def handle_tool_call(self, name: str, arguments: dict):
        """处理工具调用"""
        await self.initialize()
        
        try:
            # ==================== 基础工具 ====================
            if name == "mobile_list_elements":
                result = self.basic_tools.list_elements()
                return [TextContent(type="text", text=str(result))]
            
            elif name == "mobile_click_by_id":
                result = self.basic_tools.click_by_id(arguments["resource_id"])
                return [TextContent(type="text", text=str(result))]
            
            elif name == "mobile_click_by_text":
                result = self.basic_tools.click_by_text(arguments["text"])
                return [TextContent(type="text", text=str(result))]
            
            elif name == "mobile_click_at_coords":
                result = self.basic_tools.click_at_coords(arguments["x"], arguments["y"])
                return [TextContent(type="text", text=str(result))]
            
            elif name == "mobile_input_text_by_id":
                result = self.basic_tools.input_text_by_id(
                    arguments["resource_id"],
                    arguments["text"]
                )
                return [TextContent(type="text", text=str(result))]
            
            elif name == "mobile_find_elements_by_class":
                result = self.basic_tools.find_elements_by_class(arguments["class_name"])
                return [TextContent(type="text", text=str(result))]
            
            elif name == "mobile_wait_for_element":
                timeout = arguments.get("timeout", 10)
                result = self.basic_tools.wait_for_element(arguments["resource_id"], timeout)
                return [TextContent(type="text", text=str(result))]
            
            elif name == "mobile_take_screenshot":
                description = arguments.get("description", "")
                result = self.basic_tools.take_screenshot(description)
                return [TextContent(type="text", text=str(result))]
            
            elif name == "mobile_take_screenshot_region":
                description = arguments.get("description", "")
                result = self.basic_tools.take_screenshot_region(
                    arguments["x1"], arguments["y1"],
                    arguments["x2"], arguments["y2"],
                    description
                )
                return [TextContent(type="text", text=str(result))]
            
            # ==================== 智能工具 ====================
            elif name == "mobile_smart_click":
                result = await self.smart_tools.smart_click(arguments["description"])
                return [TextContent(type="text", text=str(result))]
            
            elif name == "mobile_smart_input":
                result = await self.smart_tools.smart_input(
                    arguments["description"],
                    arguments["text"]
                )
                return [TextContent(type="text", text=str(result))]
            
            elif name == "mobile_analyze_screenshot":
                result = await self.smart_tools.analyze_screenshot_with_ai(
                    arguments["screenshot_path"],
                    arguments["description"]
                )
                return [TextContent(type="text", text=str(result))]
            
            elif name == "mobile_get_ai_status":
                result = self.smart_tools.get_ai_status()
                return [TextContent(type="text", text=str(result))]
            
            # ==================== 通用工具 ====================
            elif name == "mobile_snapshot":
                snapshot = await self.client.snapshot()
                return [TextContent(type="text", text=snapshot)]
            
            elif name == "mobile_launch_app":
                await self.client.launch_app(arguments["package_name"])
                return [TextContent(type="text", text=f"✅ 已启动: {arguments['package_name']}")]
            
            elif name == "mobile_press_key":
                await self.client.press_key(arguments["key"])
                return [TextContent(type="text", text=f"✅ 已按键: {arguments['key']}")]
            
            elif name == "mobile_swipe":
                await self.client.swipe(arguments["direction"])
                return [TextContent(type="text", text=f"✅ 已滑动: {arguments['direction']}")]
            
            else:
                return [TextContent(type="text", text=f"❌ 未知工具: {name}")]
        
        except Exception as e:
            error_msg = str(e)
            return [TextContent(type="text", text=f"❌ 执行失败: {error_msg}")]


async def main():
    """启动 MCP Server"""
    server = SimpleMobileMCPServer()
    mcp_server = Server("mobile-mcp-simplified")
    
    @mcp_server.list_tools()
    async def list_tools():
        return server.get_tools()
    
    @mcp_server.call_tool()
    async def call_tool(name: str, arguments: dict):
        return await server.handle_tool_call(name, arguments)
    
    print("🚀 Mobile MCP Server (简化版) 启动中...", file=sys.stderr)
    print("📋 基础工具：总是可用（不需要 AI）", file=sys.stderr)
    print("🤖 智能工具：需要配置 AI 密钥（可选）", file=sys.stderr)
    
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(read_stream, write_stream, mcp_server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())

