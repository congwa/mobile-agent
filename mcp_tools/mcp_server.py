#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mobile MCP Server - 统一入口

纯 MCP 方案，完全依赖 Cursor 视觉能力：
- 不需要 AI 密钥
- 20 个核心工具
- 支持 Android 和 iOS
- 保留 pytest 脚本生成

使用方式：
    python mcp_server.py
    
配置 Cursor：
    {
        "mcpServers": {
            "mobile": {
                "command": "/path/to/venv/bin/python",
                "args": ["/path/to/mobile_mcp/mcp_server.py"],
                "env": {
                    "MOBILE_PLATFORM": "android"  // 或 "ios"
                }
            }
        }
    }
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional

# 添加项目根目录到 Python 路径
# __file__ 在 mcp/ 目录下，需要往上两级到项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 尝试导入 MCP，处理可能的路径冲突
try:
    from mcp.types import Tool, TextContent
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
except ImportError:
    # 如果本地 mcp 目录冲突，从 site-packages 加载
    import importlib.util
    import site
    
    for site_dir in site.getsitepackages():
        mcp_types_path = Path(site_dir) / 'mcp' / 'types.py'
        if mcp_types_path.exists():
            mcp_pkg_path = Path(site_dir) / 'mcp'
            
            # 加载 mcp.types
            spec = importlib.util.spec_from_file_location("mcp.types", mcp_types_path)
            mcp_types = importlib.util.module_from_spec(spec)
            sys.modules['mcp.types'] = mcp_types
            spec.loader.exec_module(mcp_types)
            
            # 加载 mcp.server
            server_init = mcp_pkg_path / 'server' / '__init__.py'
            spec = importlib.util.spec_from_file_location("mcp.server", server_init)
            mcp_server_mod = importlib.util.module_from_spec(spec)
            sys.modules['mcp.server'] = mcp_server_mod
            spec.loader.exec_module(mcp_server_mod)
            
            # 加载 mcp.server.stdio
            stdio_path = mcp_pkg_path / 'server' / 'stdio.py'
            spec = importlib.util.spec_from_file_location("mcp.server.stdio", stdio_path)
            mcp_stdio = importlib.util.module_from_spec(spec)
            sys.modules['mcp.server.stdio'] = mcp_stdio
            spec.loader.exec_module(mcp_stdio)
            
            Tool = mcp_types.Tool
            TextContent = mcp_types.TextContent
            Server = mcp_server_mod.Server
            stdio_server = mcp_stdio.stdio_server
            break
    else:
        raise ImportError("Cannot find mcp package")


class MobileMCPServer:
    """Mobile MCP Server - 精简版"""
    
    def __init__(self):
        self.client = None
        self.tools = None
        self._initialized = False
    
    @staticmethod
    def format_response(result) -> str:
        """统一格式化返回值"""
        if isinstance(result, (dict, list)):
            return json.dumps(result, ensure_ascii=False, indent=2)
        return str(result)
    
    async def initialize(self):
        """延迟初始化设备连接"""
        # 如果已成功初始化，直接返回
        if self._initialized and self.tools is not None:
            return
        
        platform = self._detect_platform()
        
        try:
            from mobile_mcp.core.mobile_client import MobileClient
            from mobile_mcp.core.basic_tools_lite import BasicMobileToolsLite
            
            self.client = MobileClient(platform=platform)
            self.tools = BasicMobileToolsLite(self.client)
            self._initialized = True  # 只在成功时标记
            print(f"📱 已连接到 {platform.upper()} 设备", file=sys.stderr)
        except Exception as e:
            print(f"⚠️ 设备连接失败: {e}，下次调用时将重试", file=sys.stderr)
            self.client = None
            self.tools = None
            # 不设置 _initialized = True，下次调用会重试
    
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
        """注册 MCP 工具（20 个）"""
        tools = []
        
        # ==================== 元素定位（优先使用）====================
        tools.append(Tool(
            name="mobile_list_elements",
            description="📋 列出页面所有可交互元素（⚠️ 录制测试脚本时必须优先调用！）\n\n"
                       "返回 resource_id, text, bounds 等信息。\n\n"
                       "🎯 【生成测试脚本时的定位策略】按稳定性排序：\n"
                       "1️⃣ 【必须】先调用此工具获取元素列表\n"
                       "2️⃣ 【推荐】有 id → 用 mobile_click_by_id（最稳定）\n"
                       "3️⃣ 【推荐】有 text → 用 mobile_click_by_text（稳定）\n"
                       "4️⃣ 【兜底】游戏/无法获取元素 → mobile_click_at_coords（自动转百分比）\n\n"
                       "💡 优先使用 ID/文本定位，生成的脚本跨设备兼容性更好！",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ))
        
        # ==================== 截图（视觉兜底）====================
        tools.append(Tool(
            name="mobile_take_screenshot",
            description="📸 截图（支持全屏和局部裁剪）\n\n"
                       "🎯 使用场景：\n"
                       "- 游戏（Unity/Cocos）无法获取元素时\n"
                       "- mobile_list_elements 返回空时\n"
                       "- 需要确认页面状态时\n\n"
                       "🔍 【局部裁剪】精确识别小元素（如广告关闭按钮）：\n"
                       "   1. 先全屏截图，AI 返回大概坐标 (600, 200)\n"
                       "   2. 再调用 crop_x=600, crop_y=200, crop_size=200 截取局部\n"
                       "   3. 局部图不压缩，AI 可精确识别\n"
                       "   4. 点击时传入 crop_offset_x/y 自动换算坐标\n\n"
                       "⚠️ 【重要】截图会被压缩！\n"
                       "   - 全屏截图：点击时传 image_width/image_height 转换坐标\n"
                       "   - 局部截图：点击时传 crop_offset_x/crop_offset_y 转换坐标",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "截图描述（可选）"},
                    "crop_x": {"type": "integer", "description": "局部裁剪中心 X 坐标（屏幕坐标，0 表示不裁剪）"},
                    "crop_y": {"type": "integer", "description": "局部裁剪中心 Y 坐标（屏幕坐标，0 表示不裁剪）"},
                    "crop_size": {"type": "integer", "description": "裁剪区域大小（推荐 200-400，0 表示不裁剪）"}
                },
                "required": []
            }
        ))
        
        tools.append(Tool(
            name="mobile_get_screen_size",
            description="📐 获取屏幕尺寸。用于确认坐标范围。",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ))
        
        # ==================== 点击操作 ====================
        tools.append(Tool(
            name="mobile_click_by_text",
            description="👆 通过文本点击（⭐ 录制脚本时推荐！）\n\n"
                       "✅ 优势：跨设备兼容，不受屏幕分辨率影响\n"
                       "📋 使用前请先调用 mobile_list_elements 确认元素有文本\n"
                       "💡 生成的脚本使用 d(text='...') 定位，稳定可靠",
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
            description="👆 通过 resource-id 点击（⭐⭐ 录制脚本时最推荐！）\n\n"
                       "✅ 最稳定的定位方式，跨设备完美兼容\n"
                       "📋 使用前请先调用 mobile_list_elements 获取元素 ID\n"
                       "💡 生成的脚本使用 d(resourceId='...') 定位，最稳定",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_id": {"type": "string", "description": "元素的 resource-id"}
                },
                "required": ["resource_id"]
            }
        ))
        
        tools.append(Tool(
            name="mobile_click_at_coords",
            description="👆 点击指定坐标（⚠️ 兜底方案，优先用 ID/文本定位！）\n\n"
                       "🎯 仅在以下场景使用：\n"
                       "- 游戏（Unity/Cocos）无法获取元素\n"
                       "- mobile_list_elements 返回空\n"
                       "- 元素没有 id 和 text\n\n"
                       "⚠️ 【坐标转换】截图返回的参数直接传入：\n"
                       "   - image_width/image_height: 压缩后尺寸（AI 看到的）\n"
                       "   - original_img_width/original_img_height: 原图尺寸（用于转换）\n"
                       "   - crop_offset_x/crop_offset_y: 局部截图偏移\n\n"
                       "✅ 自动记录百分比坐标，生成脚本时转换为跨分辨率兼容的百分比定位",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "number", "description": "X 坐标（来自 AI 分析截图）"},
                    "y": {"type": "number", "description": "Y 坐标（来自 AI 分析截图）"},
                    "image_width": {"type": "number", "description": "压缩后图片宽度（截图返回的 image_width）"},
                    "image_height": {"type": "number", "description": "压缩后图片高度（截图返回的 image_height）"},
                    "original_img_width": {"type": "number", "description": "原图宽度（截图返回的 original_img_width）"},
                    "original_img_height": {"type": "number", "description": "原图高度（截图返回的 original_img_height）"},
                    "crop_offset_x": {"type": "number", "description": "局部截图 X 偏移（裁剪截图时传入）"},
                    "crop_offset_y": {"type": "number", "description": "局部截图 Y 偏移（裁剪截图时传入）"}
                },
                "required": ["x", "y"]
            }
        ))
        
        tools.append(Tool(
            name="mobile_click_by_percent",
            description="👆 通过百分比位置点击（跨设备兼容！）。\n\n"
                       "🎯 原理：屏幕左上角是 (0%, 0%)，右下角是 (100%, 100%)\n"
                       "📐 示例：\n"
                       "   - (50, 50) = 屏幕正中央\n"
                       "   - (10, 5) = 左上角附近\n"
                       "   - (85, 90) = 右下角附近\n\n"
                       "✅ 优势：同样的百分比在不同分辨率设备上都能点到相同相对位置\n"
                       "💡 录制一次，多设备回放",
            inputSchema={
                "type": "object",
                "properties": {
                    "x_percent": {"type": "number", "description": "X 轴百分比 (0-100)，0=最左，50=中间，100=最右"},
                    "y_percent": {"type": "number", "description": "Y 轴百分比 (0-100)，0=最上，50=中间，100=最下"}
                },
                "required": ["x_percent", "y_percent"]
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
                    "package_name": {"type": "string", "description": "应用包名"}
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
            name="mobile_close_popup",
            description="""🚫 智能关闭弹窗（推荐！）

自动从控件树识别关闭按钮并点击。

🎯 识别策略：
1. 找 clickable=true 且尺寸小（30-100px）的元素
2. 位置在屏幕右上角区域
3. 计算 bounds 中心点一次点击

✅ 优势：比视觉识别更精准，一次成功率高
❌ 限制：如果关闭按钮是图片的一部分（无独立控件），需要用截图+坐标点击""",
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
        
        # ==================== pytest 脚本生成 ====================
        tools.append(Tool(
            name="mobile_get_operation_history",
            description="📜 获取操作历史记录。",
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
            description="🗑️ 清空操作历史记录。\n\n"
                       "⚠️ 开始新的测试录制前必须调用！\n"
                       "📋 录制流程：清空历史 → 执行操作（优先用ID/文本定位）→ 生成脚本",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ))
        
        tools.append(Tool(
            name="mobile_generate_test_script",
            description="📝 生成 pytest 测试脚本。基于操作历史自动生成。\n\n"
                       "⚠️ 【重要】录制操作时请优先使用稳定定位：\n"
                       "1️⃣ 先调用 mobile_list_elements 获取元素列表\n"
                       "2️⃣ 优先用 mobile_click_by_id（最稳定，跨设备兼容）\n"
                       "3️⃣ 其次用 mobile_click_by_text（稳定）\n"
                       "4️⃣ 最后才用坐标点击（会自动转百分比，跨分辨率兼容）\n\n"
                       "使用流程：\n"
                       "1. 清空历史 mobile_clear_operation_history\n"
                       "2. 执行操作（优先用 ID/文本定位）\n"
                       "3. 调用此工具生成脚本\n"
                       "4. 脚本保存到 tests/ 目录\n\n"
                       "💡 定位优先级：ID > 文本 > 百分比 > 坐标",
            inputSchema={
                "type": "object",
                "properties": {
                    "test_name": {"type": "string", "description": "测试用例名称"},
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
                result = self.tools.take_screenshot(
                    description=arguments.get("description", ""),
                    crop_x=arguments.get("crop_x", 0),
                    crop_y=arguments.get("crop_y", 0),
                    crop_size=arguments.get("crop_size", 0)
                )
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_get_screen_size":
                result = self.tools.get_screen_size()
                return [TextContent(type="text", text=self.format_response(result))]
            
            # 点击
            elif name == "mobile_click_at_coords":
                result = self.tools.click_at_coords(
                    arguments["x"], 
                    arguments["y"],
                    arguments.get("image_width", 0),
                    arguments.get("image_height", 0),
                    arguments.get("crop_offset_x", 0),
                    arguments.get("crop_offset_y", 0),
                    arguments.get("original_img_width", 0),
                    arguments.get("original_img_height", 0)
                )
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_click_by_text":
                result = self.tools.click_by_text(arguments["text"])
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_click_by_id":
                result = self.tools.click_by_id(arguments["resource_id"])
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_click_by_percent":
                result = self.tools.click_by_percent(arguments["x_percent"], arguments["y_percent"])
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
            
            elif name == "mobile_close_popup":
                result = self.tools.close_popup()
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
            import traceback
            error_msg = f"❌ 执行失败: {str(e)}\n{traceback.format_exc()}"
            return [TextContent(type="text", text=error_msg)]


async def async_main():
    """启动 MCP Server（异步版本）"""
    server = MobileMCPServer()
    mcp_server = Server("mobile-mcp")
    
    @mcp_server.list_tools()
    async def list_tools():
        return server.get_tools()
    
    @mcp_server.call_tool()
    async def call_tool(name: str, arguments: dict):
        return await server.handle_tool_call(name, arguments)
    
    print("🚀 Mobile MCP Server 启动中... [20 个工具]", file=sys.stderr)
    print("📱 支持 Android / iOS", file=sys.stderr)
    print("👁️ 完全依赖 Cursor 视觉能力，无需 AI 密钥", file=sys.stderr)
    
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(read_stream, write_stream, mcp_server.create_initialization_options())


def main():
    """入口点函数（供 pip 安装后使用）"""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

