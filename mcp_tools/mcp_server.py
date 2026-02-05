#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mobile MCP Server - 统一入口

纯 MCP 方案，完全依赖 Cursor 视觉能力：
- 不需要 AI 密钥
- 24 个核心工具（含 4 个长按工具）
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
# 支持两种运行方式：
# 1. 从源码运行：__file__ 在 mcp_tools/ 目录下，往上两级到项目根目录
# 2. 从已安装包运行：包已安装时，mobile_mcp 应该可以直接导入
# 先尝试从已安装的包导入，如果失败则从源码路径导入
try:
    # 尝试导入已安装的包
    import mobile_mcp.core.mobile_client
    import mobile_mcp.core.basic_tools_lite
    # 如果成功，说明包已安装，不需要添加路径
except ImportError:
    # 包未安装或导入失败，从源码运行
    # __file__ 在 mcp_tools/ 目录下，往上两级到项目根目录
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
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
        self._last_error = None  # 保存最后一次连接失败的错误
        
        # Token 优化配置
        try:
            from mobile_mcp.config import Config
            self._compact_desc = Config.COMPACT_TOOL_DESCRIPTION
        except ImportError:
            self._compact_desc = True  # 默认开启精简模式
    
    @staticmethod
    def format_response(result) -> str:
        """统一格式化返回值（Token 优化：无缩进）"""
        if isinstance(result, (dict, list)):
            return json.dumps(result, ensure_ascii=False, separators=(',', ':'))
        return str(result)
    
    async def initialize(self):
        """延迟初始化设备连接"""
        # 如果已成功初始化，检查连接是否仍然有效
        if self._initialized and self.tools is not None:
            # 验证设备连接是否仍然有效
            if self._is_connection_valid():
                return
            else:
                # 连接已失效，重置状态
                print("⚠️ 检测到设备连接已断开，正在重新连接...", file=sys.stderr)
                self._initialized = False
                self.client = None
                self.tools = None
        
        platform = self._detect_platform()
        
        try:
            # 尝试导入，如果失败会抛出 ImportError
            try:
                from mobile_mcp.core.mobile_client import MobileClient
                from mobile_mcp.core.basic_tools_lite import BasicMobileToolsLite
            except ImportError as import_err:
                # 如果导入失败，尝试从源码路径导入
                # 这通常发生在开发模式下，包未安装时
                project_root = Path(__file__).parent.parent
                if str(project_root) not in sys.path:
                    sys.path.insert(0, str(project_root))
                # 再次尝试导入
                from mobile_mcp.core.mobile_client import MobileClient
                from mobile_mcp.core.basic_tools_lite import BasicMobileToolsLite
            
            self.client = MobileClient(platform=platform)
            self.tools = BasicMobileToolsLite(self.client)
            self._initialized = True  # 只在成功时标记
            print(f"📱 已连接到 {platform.upper()} 设备", file=sys.stderr)
        except Exception as e:
            error_msg = str(e)
            print(f"⚠️ 设备连接失败: {error_msg}，下次调用时将重试", file=sys.stderr)
            self.client = None
            self.tools = None
            self._last_error = error_msg  # 保存错误信息
            # 不设置 _initialized = True，下次调用会重试
    
    def _is_connection_valid(self) -> bool:
        """检查设备连接是否仍然有效"""
        try:
            if self.client is None:
                return False
            
            # Android: 检查 u2 连接
            if hasattr(self.client, 'u2') and self.client.u2:
                # 尝试获取设备信息，如果失败说明连接断开
                self.client.u2.info
                return True
            
            # iOS: 检查 wda 连接
            if hasattr(self.client, 'wda') and self.client.wda:
                self.client.wda.status()
                return True
            
            # iOS (通过 _ios_client)
            if hasattr(self.client, '_ios_client') and self.client._ios_client:
                if hasattr(self.client._ios_client, 'wda') and self.client._ios_client.wda:
                    self.client._ios_client.wda.status()
                    return True
            
            return False
        except Exception:
            return False
    
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
        """注册 MCP 工具"""
        tools = []
        
        # 根据配置选择精简或完整描述
        compact = getattr(self, '_compact_desc', True)
        
        # ==================== 元素定位（优先使用）====================
        if compact:
            desc_list_elements = "📋 【首选】列出页面元素(token低)。返回text/id用于点击，替代截图确认页面状态。"
        else:
            desc_list_elements = ("📋 【⭐首选工具】列出页面所有可交互元素\n\n"
                       "🚀 Token 优化：返回文本数据(~500 tokens)，远小于截图(~2000 tokens)！\n\n"
                       "✅ 推荐使用场景：\n"
                       "- 点击前确认元素存在\n"
                       "- 点击后确认页面变化（替代截图确认）\n"
                       "- 获取 text/id 用于 click_by_text/click_by_id\n\n"
                       "❌ 不要用截图确认页面，用此工具！\n"
                       "📌 只有需要看视觉布局时才用截图")
        
        tools.append(Tool(
            name="mobile_list_elements",
            description=desc_list_elements,
            inputSchema={"type": "object", "properties": {}, "required": []}
        ))
        
        # ==================== 截图（视觉兜底）====================
        if compact:
            desc_screenshot = "📸 截图(token高~2000)。优先用list_elements(~500)确认页面状态。"
        else:
            desc_screenshot = ("📸 截图查看屏幕内容（⚠️ Token 消耗高 ~2000）\n\n"
                       "❌ 【不推荐】确认页面状态请用 list_elements（Token 仅 ~500）！\n\n"
                       "✅ 仅在以下场景使用：\n"
                       "- 需要看视觉布局/图片内容\n"
                       "- 元素无 text/id，只能靠位置点击\n"
                       "- 调试问题需要可视化\n\n"
                       "💡 compress=false 可获取原图（用于添加模板）")
        
        tools.append(Tool(
            name="mobile_take_screenshot",
            description=desc_screenshot,
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "截图描述"},
                    "compress": {"type": "boolean", "description": "是否压缩", "default": True},
                    "crop_x": {"type": "integer", "description": "裁剪中心 X"},
                    "crop_y": {"type": "integer", "description": "裁剪中心 Y"},
                    "crop_size": {"type": "integer", "description": "裁剪大小"}
                },
                "required": []
            }
        ))
        
        tools.append(Tool(
            name="mobile_get_screen_size",
            description="📐 获取屏幕尺寸。用于确认坐标范围。",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ))
        
        if compact:
            desc_som = "📸 SoM截图(token高)。元素有text时优先用list_elements+click_by_text。"
        else:
            desc_som = ("📸🏷️ Set-of-Mark 截图（⚠️ Token 消耗高 ~2000）\n\n"
                       "【智能标注】给每个可点击元素画框+编号\n\n"
                       "❌ 【不推荐常规使用】：\n"
                       "- 如果元素有 text，用 list_elements + click_by_text 更省 token\n"
                       "- 确认页面状态用 list_elements，不要截图确认！\n\n"
                       "✅ 仅在以下场景使用：\n"
                       "- 元素无 text/id，只能看图点击\n"
                       "- 需要视觉布局信息\n"
                       "- 首次探索未知页面\n\n"
                       "💡 点击后用 list_elements 确认，不要再截图！")
        
        tools.append(Tool(
            name="mobile_screenshot_with_som",
            description=desc_som,
            inputSchema={"type": "object", "properties": {}, "required": []}
        ))
        
        tools.append(Tool(
            name="mobile_click_by_som",
            description="🎯 根据SoM编号点击。配合screenshot_with_som使用。",
            inputSchema={
                "type": "object",
                "properties": {
                    "index": {"type": "integer", "description": "元素编号(从1开始)"}
                },
                "required": ["index"]
            }
        ))
        
        tools.append(Tool(
            name="mobile_screenshot_with_grid",
            description="📸 带网格坐标截图。用于精确定位元素坐标。",
            inputSchema={
                "type": "object",
                "properties": {
                    "grid_size": {"type": "integer", "description": "网格间距(px),默认100"},
                    "show_popup_hints": {"type": "boolean", "description": "显示弹窗提示"}
                },
                "required": []
            }
        ))
        
        # ==================== 点击操作 ====================
        if compact:
            desc_click_text = "👆 文本点击（推荐）。verify可验证点击结果，无需截图确认。position可选top/bottom/left/right。"
        else:
            desc_click_text = ("👆 通过文本点击元素（⭐ 最推荐）\n\n"
                       "✅ 最稳定的定位方式，跨设备兼容\n"
                       "✅ 元素不存在会报错，不会误点击\n\n"
                       "🚀 Token 优化流程：\n"
                       "1. list_elements 确认元素存在\n"
                       "2. click_by_text 点击\n"
                       "3. list_elements 确认页面变化（❌不要截图确认！）\n\n"
                       "📍 position 参数：多个相同文案时指定位置\n"
                       "   - top/bottom/left/right/center\n\n"
                       "🔍 verify 参数：点击后自动验证文本是否出现\n"
                       "   - 设置后无需额外调用 list_elements 确认")
        
        tools.append(Tool(
            name="mobile_click_by_text",
            description=desc_click_text,
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "元素文本"},
                    "position": {"type": "string", "description": "位置：top/bottom/left/right"},
                    "verify": {"type": "string", "description": "点击后验证的文本（可选）"}
                },
                "required": ["text"]
            }
        ))
        
        if compact:
            desc_click_id = "👆 通过resource-id点击。index指定第几个(从0开始)。点击后用list_elements确认。"
        else:
            desc_click_id = ("👆 通过 resource-id 点击元素（推荐）\n\n"
                       "✅ 稳定的定位方式，元素不存在会报错\n"
                       "📋 使用前 list_elements 获取元素 ID\n"
                       "📋 点击后 list_elements 确认（❌不要截图确认！）\n"
                       "💡 多个相同 ID 时用 index 指定第几个（从 0 开始）")
        
        tools.append(Tool(
            name="mobile_click_by_id",
            description=desc_click_id,
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_id": {"type": "string", "description": "resource-id"},
                    "index": {"type": "integer", "description": "第几个（从0开始）", "default": 0}
                },
                "required": ["resource_id"]
            }
        ))
        
        if compact:
            desc_click_coords = "👆 坐标点击(兜底)。优先用click_by_text/id，点击后用list_elements确认。"
        else:
            desc_click_coords = ("👆 点击指定坐标（⚠️ 兜底方案）\n\n"
                       "❌ 优先使用 click_by_text 或 click_by_id！\n"
                       "仅在 list_elements 无法获取元素时使用。\n\n"
                       "📐 坐标转换：截图返回的参数直接传入即可\n"
                       "📋 点击后用 list_elements 确认（❌不要截图确认！）")
        
        tools.append(Tool(
            name="mobile_click_at_coords",
            description=desc_click_coords,
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "number", "description": "X 坐标"},
                    "y": {"type": "number", "description": "Y 坐标"},
                    "image_width": {"type": "number", "description": "图片宽度"},
                    "image_height": {"type": "number", "description": "图片高度"},
                    "original_img_width": {"type": "number", "description": "原图宽"},
                    "original_img_height": {"type": "number", "description": "原图高"},
                    "crop_offset_x": {"type": "number", "description": "裁剪X偏移"},
                    "crop_offset_y": {"type": "number", "description": "裁剪Y偏移"}
                },
                "required": ["x", "y"]
            }
        ))
        
        tools.append(Tool(
            name="mobile_click_by_percent",
            description="👆 百分比点击。(50,50)=屏幕中心。跨设备兼容。",
            inputSchema={
                "type": "object",
                "properties": {
                    "x_percent": {"type": "number", "description": "X 轴百分比 (0-100)，0=最左，50=中间，100=最右"},
                    "y_percent": {"type": "number", "description": "Y 轴百分比 (0-100)，0=最上，50=中间，100=最下"}
                },
                "required": ["x_percent", "y_percent"]
            }
        ))
        
        # ==================== 长按操作 ====================
        tools.append(Tool(
            name="mobile_long_press_by_id",
            description="👆 通过resource-id长按。",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_id": {"type": "string", "description": "resource-id"},
                    "duration": {"type": "number", "description": "长按秒数,默认1.0"}
                },
                "required": ["resource_id"]
            }
        ))
        
        tools.append(Tool(
            name="mobile_long_press_by_text",
            description="👆 通过文本长按。",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "文本内容"},
                    "duration": {"type": "number", "description": "长按秒数,默认1.0"}
                },
                "required": ["text"]
            }
        ))
        
        tools.append(Tool(
            name="mobile_long_press_by_percent",
            description="👆 百分比长按。(50,50)=屏幕中心。",
            inputSchema={
                "type": "object",
                "properties": {
                    "x_percent": {"type": "number", "description": "X百分比(0-100)"},
                    "y_percent": {"type": "number", "description": "Y百分比(0-100)"},
                    "duration": {"type": "number", "description": "长按秒数,默认1.0"}
                },
                "required": ["x_percent", "y_percent"]
            }
        ))
        
        tools.append(Tool(
            name="mobile_long_press_at_coords",
            description="👆 坐标长按(兜底)。优先用text/id。",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "number", "description": "X坐标"},
                    "y": {"type": "number", "description": "Y坐标"},
                    "duration": {"type": "number", "description": "长按秒数"},
                    "image_width": {"type": "number", "description": "图片宽"},
                    "image_height": {"type": "number", "description": "图片高"},
                    "original_img_width": {"type": "number", "description": "原图宽"},
                    "original_img_height": {"type": "number", "description": "原图高"},
                    "crop_offset_x": {"type": "number", "description": "裁剪X偏移"},
                    "crop_offset_y": {"type": "number", "description": "裁剪Y偏移"}
                },
                "required": ["x", "y"]
            }
        ))
        
        # ==================== 输入操作 ====================
        tools.append(Tool(
            name="mobile_input_text_by_id",
            description="⌨️ 通过ID输入文本。",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_id": {"type": "string", "description": "resource-id"},
                    "text": {"type": "string", "description": "输入文本"}
                },
                "required": ["resource_id", "text"]
            }
        ))
        
        tools.append(Tool(
            name="mobile_input_at_coords",
            description="⌨️ 坐标输入文本。",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "number", "description": "X坐标"},
                    "y": {"type": "number", "description": "Y坐标"},
                    "text": {"type": "string", "description": "输入文本"}
                },
                "required": ["x", "y", "text"]
            }
        ))
        
        # ==================== 导航操作 ====================
        tools.append(Tool(
            name="mobile_swipe",
            description="👆 滑动屏幕。方向：up/down/left/right\n\n"
                       "🎯 适用场景：\n"
                       "- 滑动页面（列表、页面切换）\n"
                       "- 拖动进度条/滑块（SeekBar、ProgressBar）\n"
                       "- 滑动选择器（Picker、Slider）\n\n"
                       "💡 左右滑动时，可指定高度坐标或百分比：\n"
                       "- y: 指定高度坐标（像素）\n"
                       "- y_percent: 指定高度百分比 (0-100)\n"
                       "- 两者都未指定时，使用屏幕中心高度\n"
                       "- 📌 拖动进度条时，使用进度条的 Y 位置（百分比或像素）\n\n"
                       "💡 横向滑动（left/right）时，可指定滑动距离：\n"
                       "- distance: 滑动距离（像素）\n"
                       "- distance_percent: 滑动距离百分比 (0-100)\n"
                       "- 两者都未指定时，使用默认距离（屏幕宽度的 60%）\n"
                       "- 📌 拖动进度条时，distance_percent 控制拖动幅度\n\n"
                       "💡 拖动进度条示例：\n"
                       "- 倒退：direction='left', y_percent=91（进度条位置）, distance_percent=30\n"
                       "- 前进：direction='right', y_percent=91, distance_percent=30\n\n"
                       "⚠️ **推荐使用 mobile_drag_progress_bar 拖动进度条**（自动检测进度条位置，无需手动指定）",
            inputSchema={
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["up", "down", "left", "right"], "description": "方向"},
                    "y": {"type": "integer", "description": "左右滑动时指定的高度坐标（像素）"},
                    "y_percent": {"type": "number", "description": "左右滑动时指定的高度百分比 (0-100)"},
                    "distance": {"type": "integer", "description": "横向滑动时指定的滑动距离（像素），仅用于 left/right"},
                    "distance_percent": {"type": "number", "description": "横向滑动时指定的滑动距离百分比 (0-100)，仅用于 left/right"}
                },
                "required": ["direction"]
            }
        ))
        
        tools.append(Tool(
            name="mobile_drag_progress_bar",
            description="🎯 智能拖动进度条（⭐⭐ 推荐用于拖动视频/音频进度条）\n\n"
                       "✅ **自动检测进度条是否可见**：\n"
                       "- 如果进度条已显示，直接拖动（无需先点击播放区域）\n"
                       "- 如果进度条未显示，自动点击播放区域显示控制栏，再拖动\n\n"
                       "🎯 优势：\n"
                       "- 自动检测进度条位置，无需手动指定 y_percent\n"
                       "- 智能判断是否需要显示控制栏\n"
                       "- 使用 swipe 拖动，更稳定可靠\n\n"
                       "💡 参数说明：\n"
                       "- direction: 'left'（倒退）或 'right'（前进），默认 'right'\n"
                       "- distance_percent: 拖动距离百分比 (0-100)，默认 30%\n"
                       "- y_percent: 进度条位置（可选，未指定则自动检测）\n"
                       "- y: 进度条位置坐标（可选，未指定则自动检测）\n\n"
                       "📋 使用示例：\n"
                       "- 前进30%：mobile_drag_progress_bar(direction='right', distance_percent=30)\n"
                       "- 倒退30%：mobile_drag_progress_bar(direction='left', distance_percent=30)\n"
                       "- 前进到指定位置：先点击进度条位置，或使用 mobile_swipe",
            inputSchema={
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["left", "right"],
                        "description": "拖动方向：'left'（倒退）或 'right'（前进），默认 'right'"
                    },
                    "distance_percent": {
                        "type": "number",
                        "description": "拖动距离百分比 (0-100)，默认 30%"
                    },
                    "y_percent": {
                        "type": "number",
                        "description": "进度条的垂直位置百分比 (0-100)，可选，未指定则自动检测"
                    },
                    "y": {
                        "type": "integer",
                        "description": "进度条的垂直位置坐标（像素），可选，未指定则自动检测"
                    }
                },
                "required": []
            }
        ))
        
        tools.append(Tool(
            name="mobile_press_key",
            description="⌨️ 按键:home/back/enter/search。",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "按键名"}
                },
                "required": ["key"]
            }
        ))
        
        tools.append(Tool(
            name="mobile_wait",
            description="⏰ 等待指定秒数。",
            inputSchema={
                "type": "object",
                "properties": {
                    "seconds": {"type": "number", "description": "等待秒数"}
                },
                "required": ["seconds"]
            }
        ))
        
        tools.append(Tool(
            name="mobile_hide_keyboard",
            description="⌨️ 收起键盘。【重要】输入密码后勾选协议前必须调用，确保复选框不被键盘遮挡。登录场景必备！",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ))
        
        # ==================== 应用管理 ====================
        tools.append(Tool(
            name="mobile_launch_app",
            description="🚀 启动应用。",
            inputSchema={
                "type": "object",
                "properties": {
                    "package_name": {"type": "string", "description": "包名"}
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
                    "package_name": {"type": "string", "description": "包名"}
                },
                "required": ["package_name"]
            }
        ))
        
        tools.append(Tool(
            name="mobile_list_apps",
            description="📦 列出应用。",
            inputSchema={
                "type": "object",
                "properties": {
                    "filter": {"type": "string", "description": "过滤词"}
                },
                "required": []
            }
        ))
        
        # ==================== 设备管理 ====================
        tools.append(Tool(
            name="mobile_list_devices",
            description="📱 列出设备。",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ))
        
        tools.append(Tool(
            name="mobile_check_connection",
            description="🔌 检查连接。",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ))
        
        # ==================== 辅助工具 ====================
        if compact:
            desc_find_close = "🔍 查找关闭按钮（只找不点）。返回坐标和推荐的点击命令。"
        else:
            desc_find_close = """🔍 智能查找关闭按钮（只找不点，返回位置）

⚡ 【推荐首选】遇到弹窗时优先调用此工具！无需先截图。

从元素树中找最可能的关闭按钮，返回坐标和推荐的点击命令。

🎯 识别策略（优先级）：
1. 文本匹配：×、X、关闭、取消、跳过 等（得分100）
2. resource-id 匹配：包含 close/dismiss/skip（得分95）
3. content-desc 匹配：包含 close/关闭（得分90）
4. 小尺寸 clickable 元素（右上角优先，得分70+）

✅ 返回内容：
- 坐标 (x, y) 和百分比 (x%, y%)
- resource-id（如果有）
- 推荐的点击命令（优先 click_by_text，其次 click_by_id，最后 click_by_percent）

💡 使用流程：
1. 直接调用此工具（无需先截图/列元素）
2. 根据返回的 click_command 执行点击
3. 如果返回 success=false，才需要截图分析"""
        
        tools.append(Tool(
            name="mobile_find_close_button",
            description=desc_find_close,
            inputSchema={"type": "object", "properties": {}, "required": []}
        ))
        
        if compact:
            desc_close_popup = "🚫 智能检测并关闭弹窗。自动查找×/关闭/跳过按钮。"
        else:
            desc_close_popup = """🚫 智能检测并关闭弹窗

⚡ 【自动检测】会先检测是否存在弹窗：
- 如果没有弹窗 → 直接返回"无弹窗"，不执行任何操作
- 如果有弹窗 → 自动查找并点击关闭按钮

💡 【优化】如果已通过list_elements识别到弹窗，可传入popup_detected=true跳过重复检测

✅ 适用场景：
- 启动应用后检测并关闭可能出现的弹窗
- 页面跳转后检测并关闭弹窗
- 无需先截图确认弹窗是否存在

🎯 检测策略：
- 查找控件树中的关闭按钮（×、关闭、跳过等）
- 检测弹窗区域（Dialog/Popup/Alert 等）
- 查找小尺寸的可点击元素（优先角落位置）

🔴 【必须】如果返回已点击，需再次截图确认弹窗是否真的关闭了！"""
        
        tools.append(Tool(
            name="mobile_close_popup",
            description=desc_close_popup,
            inputSchema={
                "type": "object",
                "properties": {
                    "popup_detected": {
                        "type": "boolean",
                        "description": "可选，如果已通过list_elements识别到弹窗，传入true可跳过重复检测"
                    },
                    "popup_bounds": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "可选，弹窗边界[x1, y1, x2, y2]，如果已识别到弹窗区域可传入"
                    }
                },
                "required": []
            }
        ))
        
        tools.append(Tool(
            name="mobile_assert_text",
            description="✅ 检查页面是否包含文本。",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "文本"}
                },
                "required": ["text"]
            }
        ))
        
        # ==================== Toast 检测（仅 Android）====================
        tools.append(Tool(
            name="mobile_start_toast_watch",
            description="🔔 开始监听Toast。必须在操作前调用。",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ))
        
        tools.append(Tool(
            name="mobile_get_toast",
            description="🍞 获取Toast消息。配合start_toast_watch使用。",
            inputSchema={
                "type": "object",
                "properties": {
                    "timeout": {"type": "number", "description": "超时秒数,默认5"},
                    "reset_first": {"type": "boolean", "description": "清除旧缓存"}
                },
                "required": []
            }
        ))
        
        tools.append(Tool(
            name="mobile_assert_toast",
            description="✅ 断言Toast内容。",
            inputSchema={
                "type": "object",
                "properties": {
                    "expected_text": {"type": "string", "description": "期望文本"},
                    "timeout": {"type": "number", "description": "超时秒数"},
                    "contains": {"type": "boolean", "description": "包含匹配(默认true)"}
                },
                "required": ["expected_text"]
            }
        ))
        
        # ==================== pytest 脚本生成 ====================
        tools.append(Tool(
            name="mobile_get_operation_history",
            description="📜 获取操作历史。",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "number", "description": "条数"}
                },
                "required": []
            }
        ))
        
        tools.append(Tool(
            name="mobile_clear_operation_history",
            description="🗑️ 清空操作历史。录制前调用。",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ))
        
        tools.append(Tool(
            name="mobile_generate_test_script",
            description="📝 生成pytest脚本。基于操作历史生成。",
            inputSchema={
                "type": "object",
                "properties": {
                    "test_name": {"type": "string", "description": "用例名"},
                    "package_name": {"type": "string", "description": "包名"},
                    "filename": {"type": "string", "description": "文件名(不含.py)"}
                },
                "required": ["test_name", "package_name", "filename"]
            }
        ))
        
        # ==================== 广告弹窗关闭工具 ====================
        if compact:
            desc_close_ad = "🚫 智能关闭广告弹窗。优先级：控件树→截图AI→模板匹配。"
        else:
            desc_close_ad = """🚫 【推荐】智能检测并关闭广告弹窗

⚡ 【自动检测】会先检测是否存在弹窗：
- 如果没有弹窗 → 直接返回"无弹窗"，不执行任何操作
- 如果有弹窗 → 自动按优先级尝试关闭

🎯 关闭策略（优先级从高到低）：
1️⃣ **控件树查找**（最可靠）
   - 查找文本"关闭"、"跳过"、"×"等
   - 查找 resource-id 包含 close/dismiss
   
2️⃣ **截图 AI 分析**（次优）
   - 返回 SoM 标注截图供 AI 视觉分析
   - AI 找到 X 按钮后用 click_by_som(编号) 点击

3️⃣ **模板匹配**（兜底）
   - 用 OpenCV 匹配已保存的 X 按钮模板

✅ 适用场景：
- 启动应用后检测并关闭可能出现的广告
- 无需先截图确认弹窗是否存在"""
        
        tools.append(Tool(
            name="mobile_close_ad",
            description=desc_close_ad,
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ))
        
        tools.append(Tool(
            name="mobile_template_close",
            description="🎯 模板匹配关闭弹窗。",
            inputSchema={
                "type": "object",
                "properties": {
                    "click": {"type": "boolean", "description": "是否点击"},
                    "threshold": {"type": "number", "description": "阈值0-1"}
                },
                "required": []
            }
        ))
        
        tools.append(Tool(
            name="mobile_template_add",
            description="➕ 添加X号模板。",
            inputSchema={
                "type": "object",
                "properties": {
                    "template_name": {"type": "string", "description": "模板名"},
                    "x_percent": {"type": "number", "description": "X百分比"},
                    "y_percent": {"type": "number", "description": "Y百分比"},
                    "size": {"type": "integer", "description": "裁剪大小(px)"},
                    "screenshot_path": {"type": "string", "description": "截图路径"},
                    "x": {"type": "integer", "description": "左上X"},
                    "y": {"type": "integer", "description": "左上Y"},
                    "width": {"type": "integer", "description": "宽"},
                    "height": {"type": "integer", "description": "高"}
                },
                "required": ["template_name"]
            }
        ))
        
        # ==================== Cursor 会话管理 ====================
        tools.append(Tool(
            name="mobile_open_new_chat",
            description="🆕 打开Cursor新会话。用于飞书用例批量执行时自动分批继续。",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "发送到新会话的消息", "default": "继续执行飞书用例"}
                },
                "required": []
            }
        ))
        
        return tools
    
    async def handle_tool_call(self, name: str, arguments: dict):
        """处理工具调用"""
        await self.initialize()
        
        if not self.tools:
            # 提供详细的错误信息和解决方案
            error_detail = self._last_error or "未知错误"
            help_msg = (
                f"❌ 设备连接失败\n\n"
                f"错误详情: {error_detail}\n\n"
                f"🔧 解决方案:\n"
                f"1. 检查 USB 连接: adb devices\n"
                f"2. 重启 adb: adb kill-server && adb start-server\n"
                f"3. 初始化 uiautomator2: python -m uiautomator2 init\n"
                f"4. 手机上允许 USB 调试授权\n"
                f"5. 确保手机已解锁\n\n"
                f"完成后请重试操作。"
            )
            return [TextContent(type="text", text=help_msg)]
        
        try:
            # 截图
            if name == "mobile_take_screenshot":
                result = self.tools.take_screenshot(
                    description=arguments.get("description", ""),
                    compress=arguments.get("compress", True),
                    crop_x=arguments.get("crop_x", 0),
                    crop_y=arguments.get("crop_y", 0),
                    crop_size=arguments.get("crop_size", 0)
                )
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_get_screen_size":
                result = self.tools.get_screen_size()
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_screenshot_with_grid":
                result = self.tools.take_screenshot_with_grid(
                    grid_size=arguments.get("grid_size", 100),
                    show_popup_hints=arguments.get("show_popup_hints", False)
                )
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_screenshot_with_som":
                result = self.tools.take_screenshot_with_som()
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_click_by_som":
                result = self.tools.click_by_som(arguments["index"])
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
                result = self.tools.click_by_text(
                    arguments["text"],
                    position=arguments.get("position"),
                    verify=arguments.get("verify")
                )
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_click_by_id":
                result = self.tools.click_by_id(
                    arguments["resource_id"],
                    arguments.get("index", 0)
                )
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_click_by_percent":
                result = self.tools.click_by_percent(arguments["x_percent"], arguments["y_percent"])
                return [TextContent(type="text", text=self.format_response(result))]
            
            # 长按
            elif name == "mobile_long_press_by_id":
                result = self.tools.long_press_by_id(
                    arguments["resource_id"],
                    arguments.get("duration", 1.0)
                )
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_long_press_by_text":
                result = self.tools.long_press_by_text(
                    arguments["text"],
                    arguments.get("duration", 1.0)
                )
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_long_press_by_percent":
                result = self.tools.long_press_by_percent(
                    arguments["x_percent"],
                    arguments["y_percent"],
                    arguments.get("duration", 1.0)
                )
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_long_press_at_coords":
                result = self.tools.long_press_at_coords(
                    arguments["x"],
                    arguments["y"],
                    arguments.get("duration", 1.0),
                    arguments.get("image_width", 0),
                    arguments.get("image_height", 0),
                    arguments.get("crop_offset_x", 0),
                    arguments.get("crop_offset_y", 0),
                    arguments.get("original_img_width", 0),
                    arguments.get("original_img_height", 0)
                )
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
                result = await self.tools.swipe(
                    arguments["direction"],
                    y=arguments.get("y"),
                    y_percent=arguments.get("y_percent"),
                    distance=arguments.get("distance"),
                    distance_percent=arguments.get("distance_percent")
                )
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_drag_progress_bar":
                result = await self.tools.drag_progress_bar(
                    direction=arguments.get("direction", "right"),
                    distance_percent=arguments.get("distance_percent", 30.0),
                    y_percent=arguments.get("y_percent"),
                    y=arguments.get("y")
                )
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_press_key":
                result = await self.tools.press_key(arguments["key"])
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_wait":
                result = self.tools.wait(arguments["seconds"])
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_hide_keyboard":
                result = await self.tools.hide_keyboard()
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
            
            elif name == "mobile_find_close_button":
                result = self.tools.find_close_button()
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_close_popup":
                popup_detected = arguments.get("popup_detected")
                popup_bounds = arguments.get("popup_bounds")
                # 如果传入了popup_bounds，转换为tuple
                if popup_bounds and isinstance(popup_bounds, list) and len(popup_bounds) == 4:
                    popup_bounds = tuple(popup_bounds)
                elif popup_bounds:
                    popup_bounds = None  # 格式不正确，忽略
                result = self.tools.close_popup(
                    popup_detected=popup_detected,
                    popup_bounds=popup_bounds
                )
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_assert_text":
                result = self.tools.assert_text(arguments["text"])
                return [TextContent(type="text", text=self.format_response(result))]
            
            # Toast 检测（仅 Android）
            elif name == "mobile_start_toast_watch":
                result = self.tools.start_toast_watch()
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_get_toast":
                timeout = arguments.get("timeout", 5.0)
                reset_first = arguments.get("reset_first", False)
                result = self.tools.get_toast(timeout=timeout, reset_first=reset_first)
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_assert_toast":
                result = self.tools.assert_toast(
                    expected_text=arguments["expected_text"],
                    timeout=arguments.get("timeout", 5.0),
                    contains=arguments.get("contains", True)
                )
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
            
            # 智能关闭广告弹窗
            elif name == "mobile_close_ad":
                result = self.tools.close_ad_popup(auto_learn=True)
                return [TextContent(type="text", text=self.format_response(result))]
            
            # 模板匹配（精简版）
            elif name == "mobile_template_close":
                click = arguments.get("click", True)
                threshold = arguments.get("threshold", 0.75)
                if click:
                    result = self.tools.template_click_close(threshold=threshold)
                else:
                    result = self.tools.template_match_close(threshold=threshold)
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_template_add":
                template_name = arguments["template_name"]
                # 判断使用哪种方式
                if "x_percent" in arguments and "y_percent" in arguments:
                    # 百分比方式
                    result = self.tools.template_add_by_percent(
                        arguments["x_percent"],
                        arguments["y_percent"],
                        arguments.get("size", 80),
                        template_name
                    )
                elif "screenshot_path" in arguments:
                    # 像素方式
                    result = self.tools.template_add(
                        arguments["screenshot_path"],
                        arguments["x"],
                        arguments["y"],
                        arguments["width"],
                        arguments["height"],
                        template_name
                    )
                else:
                    result = {"success": False, "error": "请提供 x_percent/y_percent 或 screenshot_path/x/y/width/height"}
                return [TextContent(type="text", text=self.format_response(result))]
            
            # Cursor 会话管理
            elif name == "mobile_open_new_chat":
                message = arguments.get("message", "继续执行飞书用例")
                result = self.tools.open_new_chat(message)
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
    
    print("🚀 Mobile MCP Server 启动中... [27 个工具]", file=sys.stderr)
    print("📱 支持 Android / iOS", file=sys.stderr)
    print("👁️ 完全依赖 Cursor 视觉能力，无需 AI 密钥", file=sys.stderr)
    
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(read_stream, write_stream, mcp_server.create_initialization_options())


def main():
    """入口点函数（供 pip 安装后使用）"""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

