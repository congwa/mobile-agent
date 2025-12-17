#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mobile MCP Server Lite - 精简版（纯 MCP，依赖 Cursor 视觉能力）

特点：
- 不需要 AI 密钥，完全依赖 Cursor 的视觉分析能力
- 核心工具精简到 ~20 个
- 保留 pytest 脚本生成功能
- 支持 Android 和 iOS

工作流程：
1. mobile_take_screenshot -> 截图
2. Cursor AI 分析图片 -> 返回坐标
3. mobile_click_at_coords -> 点击坐标
4. mobile_generate_test_script -> 生成测试脚本
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional
import importlib.util

# 🔧 关键：直接从 site-packages 加载系统的 mcp 包
# 避免被本地 mcp 目录覆盖
def _load_system_mcp():
    """从 site-packages 加载系统的 mcp 包"""
    import site
    for site_dir in site.getsitepackages():
        mcp_types_path = Path(site_dir) / 'mcp' / 'types.py'
        if mcp_types_path.exists():
            # 找到了系统的 mcp 包
            mcp_pkg_path = Path(site_dir) / 'mcp'
            
            # 加载 mcp.types
            spec = importlib.util.spec_from_file_location("mcp.types", mcp_types_path)
            mcp_types = importlib.util.module_from_spec(spec)
            sys.modules['mcp.types'] = mcp_types
            spec.loader.exec_module(mcp_types)
            
            # 加载 mcp.server
            server_init = mcp_pkg_path / 'server' / '__init__.py'
            spec = importlib.util.spec_from_file_location("mcp.server", server_init)
            mcp_server = importlib.util.module_from_spec(spec)
            sys.modules['mcp.server'] = mcp_server
            spec.loader.exec_module(mcp_server)
            
            # 加载 mcp.server.stdio
            stdio_path = mcp_pkg_path / 'server' / 'stdio.py'
            spec = importlib.util.spec_from_file_location("mcp.server.stdio", stdio_path)
            mcp_stdio = importlib.util.module_from_spec(spec)
            sys.modules['mcp.server.stdio'] = mcp_stdio
            spec.loader.exec_module(mcp_stdio)
            
            return mcp_types, mcp_server, mcp_stdio
    
    raise ImportError("Cannot find system mcp package in site-packages")

_mcp_types, _mcp_server, _mcp_stdio = _load_system_mcp()

Tool = _mcp_types.Tool
TextContent = _mcp_types.TextContent
Server = _mcp_server.Server
stdio_server = _mcp_stdio.stdio_server

# 添加项目路径
mobile_mcp_dir = Path(__file__).parent.parent
sys.path.insert(0, str(mobile_mcp_dir.parent))

from mobile_mcp.core.mobile_client import MobileClient
from mobile_mcp.core.basic_tools_lite import BasicMobileToolsLite


class MobileMCPServerLite:
    """精简版 Mobile MCP Server"""
    
    def __init__(self):
        self.client: Optional[MobileClient] = None
        self.tools: Optional[BasicMobileToolsLite] = None
        self._initialized = False
    
    @staticmethod
    def format_response(result) -> str:
        """统一格式化返回值为 JSON 字符串"""
        if isinstance(result, (dict, list)):
            return json.dumps(result, ensure_ascii=False, indent=2)
        return str(result)
    
    async def initialize(self):
        """延迟初始化设备连接"""
        if self._initialized:
            return
        
        platform = self._detect_platform()
        
        try:
            self.client = MobileClient(platform=platform)
            self.tools = BasicMobileToolsLite(self.client)
            print(f"📱 已连接到 {platform.upper()} 设备", file=sys.stderr)
        except Exception as e:
            print(f"⚠️ 设备连接失败: {e}", file=sys.stderr)
            # 创建占位符，部分功能仍可用
            self.client = type('MockClient', (), {'platform': platform})()
            self.tools = None
        
        self._initialized = True
    
    def _detect_platform(self) -> str:
        """自动检测设备平台"""
        platform = os.getenv("MOBILE_PLATFORM", "").lower()
        if platform in ["android", "ios"]:
            return platform
        
        # 尝试检测 iOS 设备
        try:
            from mobile_mcp.core.ios_device_manager_wda import IOSDeviceManagerWDA
            ios_manager = IOSDeviceManagerWDA()
            if ios_manager.list_devices():
                return "ios"
        except:
            pass
        
        return "android"
    
    def get_tools(self):
        """注册精简版 MCP 工具（约 20 个）"""
        tools = []
        
        # ==================== 截图（核心！给 Cursor 看）====================
        tools.append(Tool(
            name="mobile_take_screenshot",
            description="📸 截图（核心工具）。截图后 Cursor 会自动分析图片，找到你需要的元素位置。\n\n"
                       "使用示例：\n"
                       "1. 调用此工具截图\n"
                       "2. Cursor 分析图片，告诉你坐标\n"
                       "3. 使用 mobile_click_at_coords 点击",
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
        ))
        
        tools.append(Tool(
            name="mobile_get_screen_size",
            description="📐 获取屏幕尺寸。用于计算坐标比例。",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ))
        
        # ==================== 点击操作 ====================
        tools.append(Tool(
            name="mobile_click_at_coords",
            description="👆 点击指定坐标（核心工具）。配合截图使用，Cursor 分析图片后告诉你坐标。\n\n"
                       "✅ 点击成功后会自动等待 0.3 秒",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "number", "description": "X 坐标（像素）"},
                    "y": {"type": "number", "description": "Y 坐标（像素）"}
                },
                "required": ["x", "y"]
            }
        ))
        
        tools.append(Tool(
            name="mobile_click_by_text",
            description="👆 通过文本点击元素。适合文本完全匹配的场景。",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "元素的文本内容（精确匹配）"}
                },
                "required": ["text"]
            }
        ))
        
        tools.append(Tool(
            name="mobile_click_by_id",
            description="👆 通过 resource-id 点击元素。需要先用 mobile_list_elements 获取 ID。",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_id": {"type": "string", "description": "元素的 resource-id"}
                },
                "required": ["resource_id"]
            }
        ))
        
        # ==================== 输入操作 ====================
        tools.append(Tool(
            name="mobile_input_text_by_id",
            description="⌨️ 在输入框输入文本。需要先用 mobile_list_elements 获取输入框 ID。",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_id": {"type": "string", "description": "输入框的 resource-id"},
                    "text": {"type": "string", "description": "要输入的文本"}
                },
                "required": ["resource_id", "text"]
            }
        ))
        
        tools.append(Tool(
            name="mobile_input_at_coords",
            description="⌨️ 点击坐标后输入文本。适合游戏等无法获取元素 ID 的场景。",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "number", "description": "输入框 X 坐标"},
                    "y": {"type": "number", "description": "输入框 Y 坐标"},
                    "text": {"type": "string", "description": "要输入的文本"}
                },
                "required": ["x", "y", "text"]
            }
        ))
        
        # ==================== 导航操作 ====================
        tools.append(Tool(
            name="mobile_swipe",
            description="👆 滑动屏幕。方向：up/down/left/right",
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
        ))
        
        tools.append(Tool(
            name="mobile_press_key",
            description="⌨️ 按键操作。支持：home, back, enter, search",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "按键名称：home, back, enter, search"}
                },
                "required": ["key"]
            }
        ))
        
        tools.append(Tool(
            name="mobile_wait",
            description="⏰ 等待指定时间。用于等待页面加载、动画完成等。",
            inputSchema={
                "type": "object",
                "properties": {
                    "seconds": {"type": "number", "description": "等待时间（秒）"}
                },
                "required": ["seconds"]
            }
        ))
        
        # ==================== 应用管理 ====================
        tools.append(Tool(
            name="mobile_launch_app",
            description="🚀 启动应用。启动后建议等待 2-3 秒让页面加载。",
            inputSchema={
                "type": "object",
                "properties": {
                    "package_name": {"type": "string", "description": "应用包名，如 'com.example.app'"}
                },
                "required": ["package_name"]
            }
        ))
        
        tools.append(Tool(
            name="mobile_terminate_app",
            description="⏹️ 终止应用。",
            inputSchema={
                "type": "object",
                "properties": {
                    "package_name": {"type": "string", "description": "应用包名"}
                },
                "required": ["package_name"]
            }
        ))
        
        tools.append(Tool(
            name="mobile_list_apps",
            description="📦 列出已安装的应用。可按关键词过滤。",
            inputSchema={
                "type": "object",
                "properties": {
                    "filter": {"type": "string", "description": "过滤关键词（可选）"}
                },
                "required": []
            }
        ))
        
        # ==================== 设备管理 ====================
        tools.append(Tool(
            name="mobile_list_devices",
            description="📱 列出已连接的设备。",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ))
        
        tools.append(Tool(
            name="mobile_check_connection",
            description="🔌 检查设备连接状态。",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ))
        
        # ==================== 辅助工具 ====================
        tools.append(Tool(
            name="mobile_list_elements",
            description="📋 列出页面所有可交互元素。返回 resource_id, text, bounds 等信息。\n"
                       "💡 提示：对于游戏等无法获取元素的场景，建议用截图 + 坐标点击。",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ))
        
        tools.append(Tool(
            name="mobile_assert_text",
            description="✅ 检查页面是否包含指定文本。用于验证操作结果。",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "要检查的文本"}
                },
                "required": ["text"]
            }
        ))
        
        # ==================== pytest 脚本生成（保留）====================
        tools.append(Tool(
            name="mobile_get_operation_history",
            description="📜 获取操作历史记录。查看之前执行的所有操作。",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "number", "description": "返回最近的N条记录"}
                },
                "required": []
            }
        ))
        
        tools.append(Tool(
            name="mobile_clear_operation_history",
            description="🗑️ 清空操作历史记录。开始新的测试录制前调用。",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ))
        
        tools.append(Tool(
            name="mobile_generate_test_script",
            description="📝 生成 pytest 测试脚本。基于操作历史自动生成可执行的测试代码。\n\n"
                       "使用流程：\n"
                       "1. 执行一系列操作（点击、输入等）\n"
                       "2. 调用此工具生成脚本\n"
                       "3. 脚本保存到 tests/ 目录",
            inputSchema={
                "type": "object",
                "properties": {
                    "test_name": {"type": "string", "description": "测试用例名称，如 '登录测试'"},
                    "package_name": {"type": "string", "description": "App 包名"},
                    "filename": {"type": "string", "description": "脚本文件名（不含 .py）"}
                },
                "required": ["test_name", "package_name", "filename"]
            }
        ))
        
        return tools
    
    async def handle_tool_call(self, name: str, arguments: dict):
        """处理工具调用"""
        await self.initialize()
        
        if not self.tools:
            return [TextContent(type="text", text="❌ 设备未连接，请检查连接状态")]
        
        try:
            # 截图
            if name == "mobile_take_screenshot":
                result = self.tools.take_screenshot(arguments.get("description", ""))
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_get_screen_size":
                result = self.tools.get_screen_size()
                return [TextContent(type="text", text=self.format_response(result))]
            
            # 点击
            elif name == "mobile_click_at_coords":
                result = self.tools.click_at_coords(arguments["x"], arguments["y"])
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_click_by_text":
                result = self.tools.click_by_text(arguments["text"])
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_click_by_id":
                result = self.tools.click_by_id(arguments["resource_id"])
                return [TextContent(type="text", text=self.format_response(result))]
            
            # 输入
            elif name == "mobile_input_text_by_id":
                result = self.tools.input_text_by_id(arguments["resource_id"], arguments["text"])
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_input_at_coords":
                result = self.tools.input_at_coords(arguments["x"], arguments["y"], arguments["text"])
                return [TextContent(type="text", text=self.format_response(result))]
            
            # 导航
            elif name == "mobile_swipe":
                result = await self.tools.swipe(arguments["direction"])
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_press_key":
                result = await self.tools.press_key(arguments["key"])
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_wait":
                result = self.tools.wait(arguments["seconds"])
                return [TextContent(type="text", text=self.format_response(result))]
            
            # 应用管理
            elif name == "mobile_launch_app":
                result = await self.tools.launch_app(arguments["package_name"])
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_terminate_app":
                result = self.tools.terminate_app(arguments["package_name"])
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_list_apps":
                result = self.tools.list_apps(arguments.get("filter", ""))
                return [TextContent(type="text", text=self.format_response(result))]
            
            # 设备管理
            elif name == "mobile_list_devices":
                result = self.tools.list_devices()
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_check_connection":
                result = self.tools.check_connection()
                return [TextContent(type="text", text=self.format_response(result))]
            
            # 辅助
            elif name == "mobile_list_elements":
                result = self.tools.list_elements()
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_assert_text":
                result = self.tools.assert_text(arguments["text"])
                return [TextContent(type="text", text=self.format_response(result))]
            
            # 脚本生成
            elif name == "mobile_get_operation_history":
                result = self.tools.get_operation_history(arguments.get("limit"))
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_clear_operation_history":
                result = self.tools.clear_operation_history()
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_generate_test_script":
                result = self.tools.generate_test_script(
                    arguments["test_name"],
                    arguments["package_name"],
                    arguments["filename"]
                )
                return [TextContent(type="text", text=self.format_response(result))]
            
            else:
                return [TextContent(type="text", text=f"❌ 未知工具: {name}")]
        
        except Exception as e:
            return [TextContent(type="text", text=f"❌ 执行失败: {str(e)}")]


async def main():
    """启动精简版 MCP Server"""
    server = MobileMCPServerLite()
    mcp_server = Server("mobile-mcp-lite")
    
    @mcp_server.list_tools()
    async def list_tools():
        return server.get_tools()
    
    @mcp_server.call_tool()
    async def call_tool(name: str, arguments: dict):
        return await server.handle_tool_call(name, arguments)
    
    print("🚀 Mobile MCP Server Lite 启动中... [精简版 - 20 个工具]", file=sys.stderr)
    print("💡 完全依赖 Cursor 视觉能力，无需 AI 密钥", file=sys.stderr)
    
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(read_stream, write_stream, mcp_server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())

