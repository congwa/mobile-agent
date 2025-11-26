#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mobile MCP Server - 让 AI 助手通过自然语言控制 Android 手机

用法：
1. 在 Cursor 中配置 MCP Server
2. AI 可以直接调用 mobile_click("登录按钮") 等工具
3. 享受 Cursor AI 的智能能力！

配置 Cursor：
在项目根目录创建 .cursor/mcp.json：
{
  "mcpServers": {
    "mobile-automation": {
      "command": "python",
      "args": ["backend/mobile_mcp/mcp/mcp_server.py"],
      "env": {
        "PYTHONPATH": ".",
        "MOBILE_DEVICE_ID": "auto"
      }
    }
  }
}
"""
import asyncio
import sys
import json
from pathlib import Path
from typing import Any, Dict, Optional

# 添加项目根目录和backend目录到路径
# mcp_server.py现在在 mcp/ 目录下，所以需要向上2级到mobile_mcp目录
mobile_mcp_dir = Path(__file__).parent.parent  # mobile_mcp目录
project_root = mobile_mcp_dir.parent.parent  # 项目根目录
backend_dir = project_root / "backend"

# 先导入MCP SDK（在添加本地路径之前，避免本地mcp目录冲突）
# 临时清理sys.path，确保导入的是安装的mcp包而不是本地mcp目录
_original_sys_path = sys.path.copy()
_mobile_mcp_dir_str = str(mobile_mcp_dir)
_project_root_str = str(project_root)
_backend_dir_str = str(backend_dir)

# 只移除精确匹配的项目路径，保留所有其他路径（包括site-packages）
sys.path = [
    p for p in sys.path 
    if p not in [_mobile_mcp_dir_str, _project_root_str, _backend_dir_str, '', '.']
]

try:
    from mcp.types import Tool, TextContent
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    MCP_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  MCP SDK 未安装或导入失败: {e}", file=sys.stderr)
    print("请运行: pip install mcp", file=sys.stderr)
    MCP_AVAILABLE = False
    sys.exit(1)
finally:
    # 恢复原始路径
    sys.path = _original_sys_path

# 现在添加本地路径（MCP SDK已导入，不会冲突）
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

from mobile_mcp.core.mobile_client import MobileClient
from mobile_mcp.core.locator.mobile_smart_locator import MobileSmartLocator
from mobile_mcp.config import Config
from mobile_mcp.core.ai.ai_platform_adapter import get_ai_adapter


class MobileMCPServer:
    """Mobile MCP Server - 封装移动端自动化能力为 MCP Tools"""
    
    def __init__(self):
        """初始化 MCP Server"""
        self.client: Optional[MobileClient] = None
        self.locator: Optional[MobileSmartLocator] = None
        self._initialized = False
        
        # AI平台适配器（可选）
        self.ai_adapter = None
        if Config.is_ai_enhancement_enabled():
            try:
                self.ai_adapter = get_ai_adapter()
                platform_name = self.ai_adapter.get_platform_name()
                print(f"✅ AI增强功能已启用: {platform_name}", file=sys.stderr)
            except Exception as e:
                print(f"⚠️  AI适配器初始化失败: {e}", file=sys.stderr)
                if not Config.should_fallback_on_ai_failure():
                    raise
    
    async def initialize(self):
        """延迟初始化（避免启动时连接设备）"""
        if not self._initialized:
            import os
            from mobile_mcp.config import Config
            
            device_id = os.environ.get("MOBILE_DEVICE_ID")
            if device_id == "auto" or device_id is None:
                device_id = None  # 自动选择设备
            
            # 🎯 根据配置选择平台
            platform = os.environ.get("DEFAULT_PLATFORM", Config.DEFAULT_PLATFORM)
            
            if platform == "ios":
                # iOS平台
                if not Config.IOS_SUPPORT_ENABLED:
                    raise RuntimeError("iOS支持未启用，请设置 IOS_SUPPORT_ENABLED=true")
                from mobile_mcp.core.ios_client import IOSClient
                self.client = IOSClient(device_id=device_id)
                self.locator = None  # iOS暂不支持智能定位器
                print("✅ Mobile MCP Server 已初始化 (iOS)", file=sys.stderr)
            else:
                # Android平台（默认）
                self.client = MobileClient(device_id=device_id, platform="android", lock_orientation=True)
                self.locator = MobileSmartLocator(self.client)
                print("✅ Mobile MCP Server 已初始化 (Android)", file=sys.stderr)
            
            self._initialized = True
    
    def get_tools(self) -> list[Tool]:
        """定义所有可用的 MCP Tools（根据配置动态生成）"""
        tools = [
            Tool(
                name="mobile_click",
                description="点击手机屏幕上的元素（按钮、链接等）。使用自然语言描述元素，如'登录按钮'、'右上角设置图标'。如果定位失败，可以使用bounds坐标格式 '[x1,y1][x2,y2]' 直接点击。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "element_desc": {
                            "type": "string",
                            "description": "元素描述（自然语言），如'登录按钮'、'提交'、'右上角返回'。或者bounds坐标格式 '[x1,y1][x2,y2]'"
                        }
                    },
                    "required": ["element_desc"]
                }
            ),
            Tool(
                name="mobile_input",
                description="在输入框中输入文本。先定位输入框，然后输入内容。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "element_desc": {
                            "type": "string",
                            "description": "输入框描述（自然语言），如'用户名输入框'、'搜索框'"
                        },
                        "text": {
                            "type": "string",
                            "description": "要输入的文本内容"
                        }
                    },
                    "required": ["element_desc", "text"]
                }
            ),
            Tool(
                name="mobile_swipe",
                description="滑动手机屏幕（上下左右）。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "direction": {
                            "type": "string",
                            "enum": ["up", "down", "left", "right"],
                            "description": "滑动方向：up(向上)、down(向下)、left(向左)、right(向右)"
                        }
                    },
                    "required": ["direction"]
                }
            ),
            Tool(
                name="mobile_press_key",
                description="按键盘按键。支持Enter键、搜索键、返回键等。在搜索框输入后，可以使用此工具按搜索键执行搜索。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "按键名称：'enter'/'回车'（Enter键）、'search'/'搜索'（搜索键）、'back'/'返回'（返回键）、'home'（Home键），或直接使用keycode数字（如66=Enter, 84=Search）"
                        }
                    },
                    "required": ["key"]
                }
            ),
            Tool(
                name="mobile_snapshot",
                description="获取当前页面的结构信息（XML树、可点击元素列表等）。用于分析页面结构，帮助定位元素。",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="mobile_launch_app",
                description="启动指定的 Android 应用。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "package_name": {
                            "type": "string",
                            "description": "应用包名，如 'com.im30.mind'"
                        },
                        "wait_time": {
                            "type": "number",
                            "description": "等待应用启动的时间（秒），默认3秒",
                            "default": 3
                        }
                    },
                    "required": ["package_name"]
                }
            ),
            Tool(
                name="mobile_assert_text",
                description="断言页面中是否包含指定文本。用于验证操作结果。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "要检查的文本内容"
                        }
                    },
                    "required": ["text"]
                }
            ),
            Tool(
                name="mobile_get_current_package",
                description="获取当前前台应用的包名。用于确认当前在哪个应用。",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="mobile_list_devices",
                description="列出所有连接的Android设备。返回设备ID和状态信息。",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="mobile_get_screen_size",
                description="获取设备的屏幕尺寸（宽度和高度，单位：像素）。",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="mobile_get_orientation",
                description="获取当前屏幕方向（portrait=竖屏，landscape=横屏）。",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="mobile_set_orientation",
                description="设置屏幕方向。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "orientation": {
                            "type": "string",
                            "enum": ["portrait", "landscape"],
                            "description": "屏幕方向：portrait(竖屏) 或 landscape(横屏)"
                        }
                    },
                    "required": ["orientation"]
                }
            ),
            Tool(
                name="mobile_list_apps",
                description="列出设备上已安装的应用。可以按包名过滤。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "过滤关键词（可选），如包名或应用名"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="mobile_install_app",
                description="安装应用（从APK文件）。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "apk_path": {
                            "type": "string",
                            "description": "APK文件路径"
                        }
                    },
                    "required": ["apk_path"]
                }
            ),
            Tool(
                name="mobile_uninstall_app",
                description="卸载应用（通过包名）。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "package_name": {
                            "type": "string",
                            "description": "应用包名，如 'com.example.app'"
                        }
                    },
                    "required": ["package_name"]
                }
            ),
            Tool(
                name="mobile_terminate_app",
                description="终止应用（通过包名）。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "package_name": {
                            "type": "string",
                            "description": "应用包名，如 'com.example.app'"
                        }
                    },
                    "required": ["package_name"]
                }
            ),
            Tool(
                name="mobile_double_click",
                description="双击屏幕上的元素。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "element_desc": {
                            "type": "string",
                            "description": "元素描述（自然语言），如'头像'、'图片'"
                        },
                        "x": {
                            "type": "number",
                            "description": "X坐标（可选，如果提供则直接点击坐标）"
                        },
                        "y": {
                            "type": "number",
                            "description": "Y坐标（可选，如果提供则直接点击坐标）"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="mobile_long_press",
                description="长按屏幕上的元素。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "element_desc": {
                            "type": "string",
                            "description": "元素描述（自然语言），如'删除按钮'、'菜单项'"
                        },
                        "duration": {
                            "type": "number",
                            "description": "长按持续时间（秒），默认1秒",
                            "default": 1.0
                        },
                        "x": {
                            "type": "number",
                            "description": "X坐标（可选，如果提供则直接长按坐标）"
                        },
                        "y": {
                            "type": "number",
                            "description": "Y坐标（可选，如果提供则直接长按坐标）"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="mobile_open_url",
                description="在设备浏览器中打开URL。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "要打开的URL，如 'https://example.com'"
                        }
                    },
                    "required": ["url"]
                }
            ),
            Tool(
                name="mobile_take_screenshot",
                description="截图并保存，返回截图路径。用于视觉识别分析。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "save_path": {
                            "type": "string",
                            "description": "截图保存路径（可选，默认保存到项目screenshots目录）"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="mobile_generate_test_script",
                description="基于操作历史生成pytest格式的测试脚本。使用已验证的定位方式（坐标、bounds等），确保生成的脚本100%可执行。生成的脚本支持pytest批量执行和allure报告生成。脚本默认保存到当前工作目录的tests子目录。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "test_name": {
                            "type": "string",
                            "description": "测试用例名称，如'建议发帖测试'"
                        },
                        "package_name": {
                            "type": "string",
                            "description": "App包名，如'com.im30.way'"
                        },
                        "filename": {
                            "type": "string",
                            "description": "生成的脚本文件名（不含.py后缀），如'test_建议发帖'"
                        },
                        "output_dir": {
                            "type": "string",
                            "description": "输出目录路径（可选）。默认为当前工作目录的tests子目录"
                        }
                    },
                    "required": ["test_name", "package_name", "filename"]
                }
            ),
            Tool(
                name="mobile_analyze_screenshot",
                description="分析截图并返回元素坐标。使用AI多模态能力分析截图，找到指定元素并返回坐标。支持自动模式（通过request_id）和手动模式（直接提供screenshot_path）。需要AI增强功能支持。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "screenshot_path": {
                            "type": "string",
                            "description": "截图文件路径（手动模式）"
                        },
                        "element_desc": {
                            "type": "string",
                            "description": "要查找的元素描述（自然语言），如'设置按钮'、'语言选项'、'保存按钮'"
                        },
                        "request_id": {
                            "type": "string",
                            "description": "请求ID（自动模式），从请求文件中读取截图路径和元素描述"
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="mobile_execute_test_case",
                description="智能执行测试用例。AI会自动规划、执行、验证每一步操作，遇到问题自动分析解决，找不到元素时自动截图分析，自动判断操作是否成功（通过页面元素变化）。需要AI增强功能支持。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "test_description": {
                            "type": "string",
                            "description": "自然语言描述的测试用例，如：'打开 com.im30.mind\n点击底部云文档\n点击我的空间'"
                        }
                    },
                    "required": ["test_description"]
                }
            )
        ]
        
        # 🎯 AI增强工具（可选，根据配置和平台能力动态添加）
        if self.ai_adapter and self.ai_adapter.is_vision_available():
            # 更新视觉识别工具的描述，使用检测到的平台名称
            platform_name = self.ai_adapter.get_platform_name()
            
            # 更新 mobile_analyze_screenshot 工具描述
            for tool in tools:
                if tool.name == "mobile_analyze_screenshot":
                    tool.description = f"分析截图并返回元素坐标。使用{platform_name}的多模态能力分析截图，找到指定元素并返回坐标。支持自动模式（通过request_id）和手动模式（直接提供screenshot_path）。"
                    break
        
        # 如果没有AI平台，移除需要AI视觉能力的工具
        # 注意：mobile_generate_test_script 不需要AI，只是基于操作历史生成脚本，所以保留
        if not self.ai_adapter or not self.ai_adapter.is_vision_available():
            tools = [t for t in tools if t.name not in [
                "mobile_analyze_screenshot",
                "mobile_execute_test_case"
            ]]
            if Config.is_ai_enhancement_enabled():
                print("⚠️  AI视觉增强工具已禁用（未检测到可用的AI平台）", file=sys.stderr)
        
        return tools
    
    async def handle_mobile_click(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """处理点击操作"""
        await self.initialize()
        element_desc = arguments.get("element_desc")
        
        try:
            result = None  # 初始化result变量
            # 🎯 检查是否是bounds坐标格式 "[x1,y1][x2,y2]"
            if element_desc.startswith('[') and '][' in element_desc:
                # 直接使用bounds坐标点击
                print(f"  📍 检测到bounds坐标格式，直接使用坐标点击: {element_desc}", file=sys.stderr)
                click_result = await self.client.click(
                    element_desc,
                    ref=element_desc,
                    verify=False
                )
                result = {'method': 'bounds', 'ref': element_desc}  # 设置result用于后续使用
            else:
                # 使用智能定位器定位元素
                result = await self.locator.locate(element_desc)
                if not result:
                    # 🎯 定位失败时，自动使用Cursor AI视觉识别
                    # 检查是否有待分析的请求文件
                    from pathlib import Path
                    project_root = Path(__file__).parent.parent
                    request_dir = project_root / "screenshots" / "requests"
                    if request_dir.exists():
                        # 查找最新的请求文件
                        request_files = sorted(request_dir.glob("request_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
                        if request_files:
                            latest_request = request_files[0]
                            try:
                                import json as json_lib
                                with open(latest_request, 'r', encoding='utf-8') as f:
                                    request_data = json_lib.load(f)
                                if request_data.get('element_desc') == element_desc and request_data.get('status') == 'pending':
                                    # 🎯 自动调用Cursor AI分析
                                    request_id = request_data.get('request_id')
                                    print(f"  🎯 检测到待分析的请求文件，自动调用Cursor AI分析: request_id={request_id}", file=sys.stderr)
                                    # 调用mobile_analyze_screenshot工具
                                    analyze_result = await self.handle_mobile_analyze_screenshot({
                                        "request_id": request_id
                                    })
                                    # 检查分析结果
                                    if analyze_result and len(analyze_result) > 0:
                                        analyze_text = analyze_result[0].text
                                        analyze_data = json_lib.loads(analyze_text)
                                        if analyze_data.get('success') and analyze_data.get('coordinate'):
                                            # ✅ Cursor AI分析成功，重新定位
                                            coord = analyze_data['coordinate']
                                            ref = f"vision_coord_{coord['x']}_{coord['y']}"
                                            click_result = await self.client.click(
                                                element_desc,
                                                ref=ref,
                                                verify=False
                                            )
                                            if click_result.get('success'):
                                                return [TextContent(
                                                    type="text",
                                                    text=json.dumps({
                                                        "success": True,
                                                        "element": element_desc,
                                                        "method": "cursor_vision_auto",
                                                        "message": f"成功点击: {element_desc}（通过Cursor AI自动分析）"
                                                    }, ensure_ascii=False, indent=2)
                                                )]
                            except Exception as e:
                                print(f"  ⚠️  自动分析失败: {e}", file=sys.stderr)
                    
                    # 如果自动分析失败或没有请求文件，返回错误
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": f"未找到元素: {element_desc}",
                            "suggestion": "尝试使用 mobile_snapshot 查看页面结构，或使用 mobile_take_screenshot 截图后使用 mobile_analyze_screenshot 分析，或直接使用bounds坐标格式 '[x1,y1][x2,y2]'"
                        }, ensure_ascii=False, indent=2)
                    )]
                
                # 🎯 记录定位结果（用于调试）
                ref = result.get('ref', '')
                method = result.get('method', 'unknown')
                print(f"  📍 定位结果: {element_desc} -> ref={ref}, method={method}", file=sys.stderr)
                
                # 🎯 检查是否是待分析的Cursor AI视觉识别请求
                if method == 'cursor_vision_pending' and result.get('status') == 'pending_analysis':
                    request_id = result.get('request_id')
                    screenshot_path = result.get('screenshot_path')
                    print(f"  🎯 检测到待分析的Cursor AI请求，自动调用分析工具: request_id={request_id}", file=sys.stderr)
                    
                    # 自动调用mobile_analyze_screenshot工具
                    analyze_result = await self.handle_mobile_analyze_screenshot({
                        "request_id": request_id
                    })
                    
                    # 检查分析结果
                    if analyze_result and len(analyze_result) > 0:
                        analyze_text = analyze_result[0].text
                        analyze_data = json.loads(analyze_text)
                        if analyze_data.get('success') and analyze_data.get('coordinate'):
                            # ✅ Cursor AI分析成功，使用坐标点击
                            coord = analyze_data['coordinate']
                            ref = f"vision_coord_{coord['x']}_{coord['y']}"
                            click_result = await self.client.click(
                                element_desc,
                                ref=ref,
                                verify=False
                            )
                            if click_result.get('success'):
                                return [TextContent(
                                    type="text",
                                    text=json.dumps({
                                        "success": True,
                                        "element": element_desc,
                                        "method": "cursor_vision_auto",
                                        "message": f"成功点击: {element_desc}（通过Cursor AI自动分析）",
                                        "coordinate": coord
                                    }, ensure_ascii=False, indent=2)
                                )]
                    
                    # 如果分析失败，返回错误
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": f"Cursor AI分析失败: {element_desc}",
                            "screenshot_path": screenshot_path,
                            "request_id": request_id
                        }, ensure_ascii=False, indent=2)
                    )]
                
                # 执行点击
                click_result = await self.client.click(
                    element_desc,
                    ref=ref,
                    verify=False
                )
            
            if click_result.get('success'):
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "element": element_desc,
                        "method": result.get('method', 'unknown') if result else 'bounds',
                        "message": f"成功点击: {element_desc}"
                    }, ensure_ascii=False, indent=2)
                )]
            else:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": click_result.get('reason', '点击失败'),
                        "element": element_desc
                    }, ensure_ascii=False, indent=2)
                )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"点击异常: {str(e)}"
                }, ensure_ascii=False, indent=2)
            )]
    
    async def handle_mobile_input(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """处理输入操作"""
        await self.initialize()
        element_desc = arguments.get("element_desc")
        text = arguments.get("text")
        
        try:
            # 🎯 检查是否是bounds坐标格式 "[x1,y1][x2,y2]"
            if element_desc.startswith('[') and '][' in element_desc:
                # 直接使用bounds坐标输入
                print(f"  📍 检测到bounds坐标格式，直接使用坐标输入: {element_desc}", file=sys.stderr)
                input_result = await self.client.type_text(element_desc, text, ref=element_desc)
            else:
                # 定位输入框
                result = await self.locator.locate(element_desc)
                if not result:
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": f"未找到输入框: {element_desc}",
                            "suggestion": "尝试使用bounds坐标格式 '[x1,y1][x2,y2]' 直接输入"
                        }, ensure_ascii=False, indent=2)
                    )]
                
                # 执行输入
                input_result = await self.client.type_text(element_desc, text, ref=result['ref'])
            
            # 🎯 修复：检查输入结果
            if not input_result.get('success'):
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": input_result.get('reason', '输入失败'),
                        "element": element_desc,
                        "text": text
                    }, ensure_ascii=False, indent=2)
                )]
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "element": element_desc,
                    "text": text,
                    "message": f"成功在 {element_desc} 中输入: {text}"
                }, ensure_ascii=False, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"输入异常: {str(e)}"
                }, ensure_ascii=False, indent=2)
            )]
    
    async def handle_mobile_swipe(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """处理滑动操作"""
        await self.initialize()
        direction = arguments.get("direction")
        
        try:
            result = await self.client.swipe(direction)
            if result.get('success'):
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "direction": direction,
                        "message": f"成功滑动: {direction}"
                    }, ensure_ascii=False, indent=2)
                )]
            else:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": result.get('reason', '滑动失败')
                    }, ensure_ascii=False, indent=2)
                )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"滑动异常: {str(e)}"
                }, ensure_ascii=False, indent=2)
            )]
    
    async def handle_mobile_press_key(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """处理按键操作"""
        await self.initialize()
        key = arguments.get("key")
        
        try:
            result = await self.client.press_key(key)
            if result.get('success'):
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "key": key,
                        "keycode": result.get('keycode'),
                        "message": f"成功按键: {key}"
                    }, ensure_ascii=False, indent=2)
                )]
            else:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": result.get('reason', '按键失败'),
                        "key": key
                    }, ensure_ascii=False, indent=2)
                )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"按键异常: {str(e)}"
                }, ensure_ascii=False, indent=2)
            )]
    
    async def handle_mobile_snapshot(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """获取页面快照"""
        await self.initialize()
        
        try:
            # client.snapshot() 已经返回格式化后的字符串，不需要再次格式化
            snapshot = await self.client.snapshot()
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "snapshot": snapshot,
                    "message": "页面结构已获取"
                }, ensure_ascii=False, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"获取快照异常: {str(e)}"
                }, ensure_ascii=False, indent=2)
            )]
    
    async def handle_mobile_launch_app(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """启动应用"""
        await self.initialize()
        package_name = arguments.get("package_name")
        wait_time = arguments.get("wait_time", 3)
        
        try:
            await self.client.launch_app(package_name, wait_time=wait_time)
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "package": package_name,
                    "message": f"成功启动应用: {package_name}"
                }, ensure_ascii=False, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"启动应用异常: {str(e)}"
                }, ensure_ascii=False, indent=2)
            )]
    
    async def handle_mobile_assert_text(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """断言文本"""
        await self.initialize()
        text = arguments.get("text")
        
        try:
            snapshot = await self.client.snapshot()
            found = text in snapshot
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": found,
                    "text": text,
                    "found": found,
                    "message": f"文本 '{text}' {'已找到' if found else '未找到'}"
                }, ensure_ascii=False, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"断言异常: {str(e)}"
                }, ensure_ascii=False, indent=2)
            )]
    
    async def handle_mobile_get_current_package(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """获取当前应用包名"""
        await self.initialize()
        
        try:
            package = self.client.u2.app_current()['package']
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "package": package,
                    "message": f"当前应用: {package}"
                }, ensure_ascii=False, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"获取包名异常: {str(e)}"
                }, ensure_ascii=False, indent=2)
            )]
    
    async def handle_mobile_take_screenshot(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """截图并保存"""
        await self.initialize()
        
        try:
            import os
            from datetime import datetime
            
            save_path = arguments.get("save_path")
            if not save_path:
                # 默认保存到项目内的screenshots目录
                mobile_mcp_dir = Path(__file__).parent.parent
                screenshot_dir = mobile_mcp_dir / "screenshots"
                screenshot_dir.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = str(screenshot_dir / f"mobile_screenshot_{timestamp}.png")
            
            # 截图
            self.client.u2.screenshot(save_path)
            
            # 🎯 返回截图路径，Cursor AI可以通过读取文件来查看截图
            # 注意：MCP协议只支持文本返回，但Cursor AI可以读取文件内容
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "screenshot_path": save_path,
                    "message": f"截图已保存: {save_path}",
                    "note": "Cursor AI可以通过读取此文件路径来查看截图内容"
                }, ensure_ascii=False, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"截图异常: {str(e)}"
                }, ensure_ascii=False, indent=2)
            )]
    
    async def handle_mobile_analyze_screenshot(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """
        分析截图并返回元素坐标（支持自动模式）
        
        这个工具会：
        1. 读取请求文件（如果提供request_id）- 自动模式
        2. 或者直接分析截图（如果提供screenshot_path）- 手动模式
        3. 使用AI平台的多模态能力分析截图（自动检测平台）
        4. 返回坐标并写入结果文件（自动模式）
        """
        await self.initialize()
        
        # 🎯 检查AI平台是否可用
        if not self.ai_adapter or not self.ai_adapter.is_vision_available():
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": "AI视觉识别功能不可用",
                    "suggestion": "请确保AI增强功能已启用，并且有可用的AI平台（Cursor、Claude、OpenAI等）"
                }, ensure_ascii=False, indent=2)
            )]
        
        screenshot_path = arguments.get("screenshot_path")
        element_desc = arguments.get("element_desc")
        request_id = arguments.get("request_id")  # 自动模式：从请求文件读取
        
        try:
            import os
            
            # 🎯 自动模式：如果有request_id，从请求文件读取信息
            if request_id:
                # 使用项目内的screenshots目录
                # mcp_server.py在mcp/目录下，所以需要向上1级到mobile_mcp目录
                mobile_mcp_dir = Path(__file__).parent.parent  # mobile_mcp目录
                request_dir = mobile_mcp_dir / "screenshots" / "requests"
                request_file = request_dir / f"request_{request_id}.json"
                result_dir = mobile_mcp_dir / "screenshots" / "results"
                result_file = result_dir / f"result_{request_id}.json"
                
                if request_file.exists():
                    with open(request_file, 'r', encoding='utf-8') as f:
                        request_data = json.load(f)
                    screenshot_path = request_data.get('screenshot_path')
                    element_desc = request_data.get('element_desc')
                    script_path = request_data.get('script_path')
                    print(f"📝 读取请求文件: {request_file}", file=sys.stderr)
                else:
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": f"请求文件不存在: {request_file}"
                        }, ensure_ascii=False, indent=2)
                    )]
            
            # 检查截图文件是否存在
            if not screenshot_path or not os.path.exists(screenshot_path):
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": f"截图文件不存在: {screenshot_path}"
                    }, ensure_ascii=False, indent=2)
                )]
            
            # 🎯 使用AI平台适配器分析截图
            platform_name = self.ai_adapter.get_platform_name()
            
            # 尝试使用适配器分析
            analyze_result = await self.ai_adapter.analyze_screenshot(
                screenshot_path=screenshot_path,
                element_desc=element_desc,
                request_id=request_id,
                result_file=str(result_file) if request_id else None,
                script_path=script_path if request_id else None
            )
            
            # 🎯 构建响应数据
            if analyze_result and "x" in analyze_result:
                # 直接返回坐标（适配器已分析完成）
                response_data = {
                    "success": True,
                    "screenshot_path": screenshot_path,
                    "element_desc": element_desc,
                    "coordinate": {
                        "x": analyze_result["x"],
                        "y": analyze_result["y"],
                        "confidence": analyze_result.get("confidence", 90)
                    },
                    "platform": analyze_result.get("platform", "unknown"),
                    "message": f"成功分析截图，找到元素坐标"
                }
                
                # 如果是自动模式，写入结果文件
                if request_id and result_file:
                    result_data = {
                        "request_id": request_id,
                        "status": "completed",
                        "coordinate": response_data["coordinate"]
                    }
                    result_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(result_file, 'w', encoding='utf-8') as f:
                        json.dump(result_data, f, ensure_ascii=False, indent=2)
                
                return [TextContent(
                    type="text",
                    text=json.dumps(response_data, ensure_ascii=False, indent=2)
                )]
            
            # 如果适配器返回指令（需要AI平台进一步处理）
            if analyze_result and "instruction" in analyze_result:
                instruction = analyze_result["instruction"]
            else:
                # 默认指令
                instruction = f"""
🎯 任务：分析移动端截图，找到元素并返回坐标

截图路径: {screenshot_path}
要查找的元素: {element_desc}
截图尺寸: 1080x2400 (竖屏)
AI平台: {platform_name}

请执行以下步骤：
1. 读取截图文件: {screenshot_path}
2. 使用多模态能力分析截图，找到元素: {element_desc}
3. 返回元素的中心点坐标，格式为JSON：
   {{"x": 100, "y": 200, "confidence": 90}}

注意：
- x, y 是元素中心点的像素坐标（屏幕坐标，左上角为0,0）
- confidence 是置信度（0-100）
- 如果找不到元素，返回 {{"found": false}}
- 截图是竖屏，尺寸为1080x2400
                """.strip()
            
            response_data = {
                "success": True,
                "screenshot_path": screenshot_path,
                "element_desc": element_desc,
                "platform": platform_name,
                "message": f"请{platform_name}分析截图并返回坐标",
                "instruction": instruction
            }
            
            # 🎯 自动模式：如果有request_id，需要写入结果文件
            if request_id:
                response_data["request_id"] = request_id
                response_data["result_file"] = str(result_file)
                response_data["script_path"] = script_path
                response_data["auto_mode"] = True
                response_data["instruction"] += f"""

⚠️  自动模式：请执行以下步骤：
1. 读取截图文件: {screenshot_path}
2. 使用多模态能力分析截图，找到元素: {element_desc}
3. 返回坐标JSON格式: {{"x": 100, "y": 200, "confidence": 90}}
4. **重要**：将结果写入文件: {result_file}
   格式：{{"request_id": "{request_id}", "status": "completed", "coordinate": {{"x": 100, "y": 200, "confidence": 90}}}}
"""
            
            return [TextContent(
                type="text",
                text=json.dumps(response_data, ensure_ascii=False, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"分析截图异常: {str(e)}"
                }, ensure_ascii=False, indent=2)
            )]
    
    async def handle_mobile_execute_test_case(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """智能执行测试用例"""
        await self.initialize()
        
        try:
            test_description = arguments.get("test_description")
            
            if not test_description:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "缺少测试用例描述"
                    }, ensure_ascii=False, indent=2)
                )]
            
            # 导入智能执行器
            from mobile_mcp.core.ai.smart_test_executor import SmartTestExecutor
            
            executor = SmartTestExecutor(self.client, self.locator)
            result = await executor.execute_test_case(test_description)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "total_steps": result['total_steps'],
                    "success_count": result['success_count'],
                    "fail_count": result['fail_count'],
                    "success_rate": f"{result['success_count']/result['total_steps']*100:.1f}%",
                    "results": result['results'],
                    "message": f"测试执行完成：{result['success_count']}/{result['total_steps']} 成功"
                }, ensure_ascii=False, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"执行测试用例异常: {str(e)}"
                }, ensure_ascii=False, indent=2)
            )]
    
    async def handle_mobile_generate_test_script(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """生成测试脚本"""
        await self.initialize()
        
        try:
            test_name = arguments.get("test_name")
            package_name = arguments.get("package_name")
            filename = arguments.get("filename")
            
            # 🎯 使用独立测试生成器（不依赖 mobile_mcp 包）
            from mobile_mcp.core.ai.test_generator_standalone import StandaloneTestGenerator
            import os
            
            # 🎯 保存到用户当前工作目录的 tests 子目录
            # 如果用户在 Cursor 中打开了项目，cwd 就是项目根目录
            output_dir = arguments.get("output_dir")  # 用户可以指定输出目录
            if not output_dir:
                # 默认：当前工作目录的 tests 子目录
                cwd = Path(os.getcwd())
                output_dir_path = cwd / "tests"
            else:
                output_dir_path = Path(output_dir)
            
            output_dir_path.mkdir(parents=True, exist_ok=True)
            
            # 确保传入字符串路径
            output_dir_str = str(output_dir_path.resolve())
            generator = StandaloneTestGenerator(output_dir=output_dir_str)
            
            # 从client获取操作历史，只保留成功的操作
            operation_history = getattr(self.client, 'operation_history', [])
            successful_operations = [
                op for op in operation_history 
                if op.get('success', False)
            ]
            
            if not successful_operations:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "没有成功的操作记录，无法生成脚本"
                    }, ensure_ascii=False, indent=2)
                )]
            
            # 🎯 获取当前使用的设备ID（重要！多设备时必须指定）
            device_id = getattr(self.client, 'device_id', None)
            if not device_id and hasattr(self.client, 'u2'):
                # 尝试从 u2 对象获取
                device_id = getattr(self.client.u2, 'serial', None)
            
            # 生成脚本
            script = generator.generate_from_history(
                test_name=test_name,
                package_name=package_name,
                operation_history=successful_operations,
                device_id=device_id  # 传递设备ID
            )
            
            # 保存脚本
            script_path = generator.save(filename, script)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "test_name": test_name,
                    "script_path": str(script_path),
                    "output_dir": str(output_dir_path),
                    "operation_count": len(successful_operations),
                    "format": "pytest",
                    "message": f"✅ 测试脚本已生成到用户项目: {script_path}",
                    "usage": {
                        "run_test": f"pytest {script_path.name} -v",
                        "with_allure": f"pytest {script_path.name} --alluredir=./allure-results",
                        "view_report": "allure serve ./allure-results"
                    }
                }, ensure_ascii=False, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"生成测试脚本异常: {str(e)}"
                }, ensure_ascii=False, indent=2)
            )]
    
    async def handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> list[TextContent]:
        """路由工具调用"""
        handlers = {
            "mobile_click": self.handle_mobile_click,
            "mobile_input": self.handle_mobile_input,
            "mobile_swipe": self.handle_mobile_swipe,
            "mobile_press_key": self.handle_mobile_press_key,
            "mobile_snapshot": self.handle_mobile_snapshot,
            "mobile_launch_app": self.handle_mobile_launch_app,
            "mobile_assert_text": self.handle_mobile_assert_text,
            "mobile_get_current_package": self.handle_mobile_get_current_package,
            "mobile_take_screenshot": self.handle_mobile_take_screenshot,
            "mobile_analyze_screenshot": self.handle_mobile_analyze_screenshot,
            "mobile_execute_test_case": self.handle_mobile_execute_test_case,
            "mobile_generate_test_script": self.handle_mobile_generate_test_script,
            "mobile_list_devices": self.handle_mobile_list_devices,
            "mobile_get_screen_size": self.handle_mobile_get_screen_size,
            "mobile_get_orientation": self.handle_mobile_get_orientation,
            "mobile_set_orientation": self.handle_mobile_set_orientation,
            "mobile_list_apps": self.handle_mobile_list_apps,
            "mobile_install_app": self.handle_mobile_install_app,
            "mobile_uninstall_app": self.handle_mobile_uninstall_app,
            "mobile_terminate_app": self.handle_mobile_terminate_app,
            "mobile_double_click": self.handle_mobile_double_click,
            "mobile_long_press": self.handle_mobile_long_press,
            "mobile_open_url": self.handle_mobile_open_url,
        }
        
        handler = handlers.get(name)
        if not handler:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"未知工具: {name}"
                }, ensure_ascii=False, indent=2)
            )]
        
        return await handler(arguments)
    
    # ==================== 新增工具处理函数 ====================
    
    async def handle_mobile_list_devices(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """列出所有连接的设备"""
        try:
            from mobile_mcp.core.device_manager import DeviceManager
            manager = DeviceManager()
            devices = manager.list_devices()
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "devices": devices,
                    "count": len(devices),
                    "message": f"找到 {len(devices)} 个设备"
                }, ensure_ascii=False, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"获取设备列表失败: {str(e)}"
                }, ensure_ascii=False, indent=2)
            )]
    
    async def handle_mobile_get_screen_size(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """获取屏幕尺寸"""
        await self.initialize()
        
        try:
            info = self.client.u2.info
            width = info.get('displayWidth', 0)
            height = info.get('displayHeight', 0)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "width": width,
                    "height": height,
                    "size": f"{width}x{height}",
                    "message": f"屏幕尺寸: {width}x{height}"
                }, ensure_ascii=False, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"获取屏幕尺寸失败: {str(e)}"
                }, ensure_ascii=False, indent=2)
            )]
    
    async def handle_mobile_get_orientation(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """获取屏幕方向"""
        await self.initialize()
        
        try:
            info = self.client.u2.info
            orientation = info.get('displayRotation', 0)
            
            # 0或2 = 竖屏, 1或3 = 横屏
            is_portrait = orientation in [0, 2]
            orientation_name = "portrait" if is_portrait else "landscape"
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "orientation": orientation_name,
                    "rotation": orientation,
                    "message": f"当前方向: {orientation_name}"
                }, ensure_ascii=False, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"获取屏幕方向失败: {str(e)}"
                }, ensure_ascii=False, indent=2)
            )]
    
    async def handle_mobile_set_orientation(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """设置屏幕方向"""
        await self.initialize()
        
        try:
            orientation = arguments.get("orientation")
            if orientation not in ["portrait", "landscape"]:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "orientation必须是'portrait'或'landscape'"
                    }, ensure_ascii=False, indent=2)
                )]
            
            # 设置方向
            if orientation == "portrait":
                self.client.u2.set_orientation("n")
            else:
                self.client.u2.set_orientation("l")
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "orientation": orientation,
                    "message": f"屏幕方向已设置为: {orientation}"
                }, ensure_ascii=False, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"设置屏幕方向失败: {str(e)}"
                }, ensure_ascii=False, indent=2)
            )]
    
    async def handle_mobile_list_apps(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """列出已安装的应用"""
        await self.initialize()
        
        try:
            filter_keyword = arguments.get("filter", "")
            
            # 获取所有应用
            apps = self.client.u2.app_list()
            
            # 过滤
            if filter_keyword:
                filtered_apps = [
                    app for app in apps
                    if filter_keyword.lower() in app.lower()
                ]
            else:
                filtered_apps = apps
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "apps": filtered_apps,
                    "count": len(filtered_apps),
                    "total": len(apps),
                    "filter": filter_keyword if filter_keyword else None,
                    "message": f"找到 {len(filtered_apps)} 个应用"
                }, ensure_ascii=False, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"获取应用列表失败: {str(e)}"
                }, ensure_ascii=False, indent=2)
            )]
    
    async def handle_mobile_install_app(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """安装应用"""
        await self.initialize()
        
        try:
            apk_path = arguments.get("apk_path")
            if not apk_path:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "缺少apk_path参数"
                    }, ensure_ascii=False, indent=2)
                )]
            
            # 检查文件是否存在
            import os
            if not os.path.exists(apk_path):
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": f"APK文件不存在: {apk_path}"
                    }, ensure_ascii=False, indent=2)
                )]
            
            # 安装应用
            result = self.client.u2.app_install(apk_path)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": result,
                    "apk_path": apk_path,
                    "message": "应用安装成功" if result else "应用安装失败"
                }, ensure_ascii=False, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"安装应用失败: {str(e)}"
                }, ensure_ascii=False, indent=2)
            )]
    
    async def handle_mobile_uninstall_app(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """卸载应用"""
        await self.initialize()
        
        try:
            package_name = arguments.get("package_name")
            if not package_name:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "缺少package_name参数"
                    }, ensure_ascii=False, indent=2)
                )]
            
            # 卸载应用
            result = self.client.u2.app_uninstall(package_name)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": result,
                    "package": package_name,
                    "message": "应用卸载成功" if result else "应用卸载失败"
                }, ensure_ascii=False, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"卸载应用失败: {str(e)}"
                }, ensure_ascii=False, indent=2)
            )]
    
    async def handle_mobile_terminate_app(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """终止应用"""
        await self.initialize()
        
        try:
            package_name = arguments.get("package_name")
            if not package_name:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "缺少package_name参数"
                    }, ensure_ascii=False, indent=2)
                )]
            
            # 终止应用
            self.client.u2.app_stop(package_name)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "package": package_name,
                    "message": f"应用 {package_name} 已终止"
                }, ensure_ascii=False, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"终止应用失败: {str(e)}"
                }, ensure_ascii=False, indent=2)
            )]
    
    async def handle_mobile_double_click(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """双击元素"""
        await self.initialize()
        
        try:
            element_desc = arguments.get("element_desc")
            x = arguments.get("x")
            y = arguments.get("y")
            
            if x is not None and y is not None:
                # 直接使用坐标
                self.client.u2.double_click(x, y)
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "x": x,
                        "y": y,
                        "method": "coordinate",
                        "message": f"双击坐标: ({x}, {y})"
                    }, ensure_ascii=False, indent=2)
                )]
            elif element_desc:
                # 定位元素后双击
                result = await self.locator.locate(element_desc)
                if not result:
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": f"未找到元素: {element_desc}"
                        }, ensure_ascii=False, indent=2)
                    )]
                
                ref = result.get('ref', '')
                # 获取元素中心点坐标
                if ref.startswith('[') and '][' in ref:
                    # 解析bounds坐标
                    import re
                    match = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', ref)
                    if match:
                        x1, y1, x2, y2 = map(int, match.groups())
                        x, y = (x1 + x2) // 2, (y1 + y2) // 2
                        self.client.u2.double_click(x, y)
                    else:
                        return [TextContent(
                            type="text",
                            text=json.dumps({
                                "success": False,
                                "error": f"无效的bounds格式: {ref}"
                            }, ensure_ascii=False, indent=2)
                        )]
                else:
                    # 使用元素双击
                    elem = self.client.u2(resourceId=ref) if (ref.startswith('com.') or ':' in ref) else self.client.u2(text=ref)
                    if elem.exists():
                        elem.double_click()
                    else:
                        return [TextContent(
                            type="text",
                            text=json.dumps({
                                "success": False,
                                "error": f"元素不存在: {element_desc}"
                            }, ensure_ascii=False, indent=2)
                        )]
                
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "element": element_desc,
                        "method": result.get('method', 'unknown'),
                        "message": f"双击成功: {element_desc}"
                    }, ensure_ascii=False, indent=2)
                )]
            else:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "需要提供element_desc或x,y坐标"
                    }, ensure_ascii=False, indent=2)
                )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"双击失败: {str(e)}"
                }, ensure_ascii=False, indent=2)
            )]
    
    async def handle_mobile_long_press(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """长按元素"""
        await self.initialize()
        
        try:
            element_desc = arguments.get("element_desc")
            duration = arguments.get("duration", 1.0)
            x = arguments.get("x")
            y = arguments.get("y")
            
            if x is not None and y is not None:
                # 直接使用坐标
                self.client.u2.long_click(x, y, duration=duration)
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "x": x,
                        "y": y,
                        "duration": duration,
                        "method": "coordinate",
                        "message": f"长按坐标: ({x}, {y}), 持续{duration}秒"
                    }, ensure_ascii=False, indent=2)
                )]
            elif element_desc:
                # 定位元素后长按
                result = await self.locator.locate(element_desc)
                if not result:
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": f"未找到元素: {element_desc}"
                        }, ensure_ascii=False, indent=2)
                    )]
                
                ref = result.get('ref', '')
                # 获取元素中心点坐标
                if ref.startswith('[') and '][' in ref:
                    # 解析bounds坐标
                    import re
                    match = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', ref)
                    if match:
                        x1, y1, x2, y2 = map(int, match.groups())
                        x, y = (x1 + x2) // 2, (y1 + y2) // 2
                        self.client.u2.long_click(x, y, duration=duration)
                    else:
                        return [TextContent(
                            type="text",
                            text=json.dumps({
                                "success": False,
                                "error": f"无效的bounds格式: {ref}"
                            }, ensure_ascii=False, indent=2)
                        )]
                else:
                    # 使用元素长按
                    elem = self.client.u2(resourceId=ref) if (ref.startswith('com.') or ':' in ref) else self.client.u2(text=ref)
                    if elem.exists():
                        elem.long_click(duration=duration)
                    else:
                        return [TextContent(
                            type="text",
                            text=json.dumps({
                                "success": False,
                                "error": f"元素不存在: {element_desc}"
                            }, ensure_ascii=False, indent=2)
                        )]
                
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "element": element_desc,
                        "duration": duration,
                        "method": result.get('method', 'unknown'),
                        "message": f"长按成功: {element_desc}, 持续{duration}秒"
                    }, ensure_ascii=False, indent=2)
                )]
            else:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "需要提供element_desc或x,y坐标"
                    }, ensure_ascii=False, indent=2)
                )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"长按失败: {str(e)}"
                }, ensure_ascii=False, indent=2)
            )]
    
    async def handle_mobile_open_url(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """打开URL"""
        await self.initialize()
        
        try:
            url = arguments.get("url")
            if not url:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": "缺少url参数"
                    }, ensure_ascii=False, indent=2)
                )]
            
            # 打开URL（使用默认浏览器）
            self.client.u2.open_url(url)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "url": url,
                    "message": f"已在浏览器中打开: {url}"
                }, ensure_ascii=False, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"打开URL失败: {str(e)}"
                }, ensure_ascii=False, indent=2)
            )]


async def main():
    """MCP Server 主函数"""
    server_instance = MobileMCPServer()
    
    # 创建 MCP Server
    server = Server("mobile-mcp-ai")
    
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return server_instance.get_tools()
    
    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
        return await server_instance.handle_tool_call(name, arguments)
    
    # 运行 stdio 服务器
    async with stdio_server() as (read_stream, write_stream):
        # 使用 Server 的方法创建正确的 InitializationOptions
        initialization_options = server.create_initialization_options()
        await server.run(
            read_stream, 
            write_stream, 
            initialization_options=initialization_options
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⚠️  MCP Server 已停止", file=sys.stderr)
    except Exception as e:
        print(f"❌ MCP Server 错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


