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
    
    @staticmethod
    def format_response(result) -> str:
        """统一格式化返回值"""
        if isinstance(result, (dict, list)):
            return json.dumps(result, ensure_ascii=False, indent=2)
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
        """注册 MCP 工具（20 个）"""
        tools = []
        
        # ==================== 元素定位（优先使用）====================
        tools.append(Tool(
            name="mobile_list_elements",
            description="📋 列出页面所有可交互元素\n\n"
                       "⚠️ 【重要】点击元素前必须先调用此工具！\n"
                       "如果元素在控件树中存在，使用 click_by_text 或 click_by_id 定位。\n"
                       "只有当此工具返回空或找不到目标元素时，才使用截图+坐标方式。\n\n"
                       "📌 控件树定位优势：\n"
                       "- 实时检测元素是否存在\n"
                       "- 元素消失时会报错，不会误点击\n"
                       "- 跨设备兼容性好",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ))
        
        # ==================== 截图（视觉兜底）====================
        tools.append(Tool(
            name="mobile_take_screenshot",
            description="📸 截图查看屏幕内容\n\n"
                       "⚠️ 【推荐使用 mobile_screenshot_with_som 代替！】\n"
                       "SoM 截图会给元素标号，AI 可以直接说'点击几号'，更精准！\n\n"
                       "🎯 本工具仅用于：\n"
                       "- 快速确认页面状态（不需要点击时）\n"
                       "- 操作后确认结果\n"
                       "- compress=false 时可获取原始分辨率截图（用于添加模板）\n\n"
                       "💡 如需点击元素，请用 mobile_screenshot_with_som + mobile_click_by_som",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "截图描述（可选）"},
                    "compress": {"type": "boolean", "description": "是否压缩，默认 true。设为 false 可获取原始分辨率（用于模板添加）", "default": True},
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
        
        tools.append(Tool(
            name="mobile_screenshot_with_som",
            description="📸🏷️ Set-of-Mark 截图（⭐⭐ 强烈推荐！默认截图方式）\n\n"
                       "【智能标注】给每个可点击元素画框+编号，检测弹窗时额外标注可能的X按钮位置（黄色）。\n"
                       "AI 看图直接说'点击 3 号'，调用 mobile_click_by_som(3) 即可！\n\n"
                       "🎯 优势：\n"
                       "- 元素有编号，精准点击不会误触\n"
                       "- 自动检测弹窗，标注可能的关闭按钮位置\n"
                       "- 适用于所有页面和所有操作\n\n"
                       "⚡ 推荐流程：\n"
                       "1. 任何需要操作的场景，都先调用此工具\n"
                       "2. 看标注图，找到目标元素编号\n"
                       "3. 调用 mobile_click_by_som(编号) 精准点击\n"
                       "4. 🔴【必须】点击后再次截图确认操作是否成功！",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ))
        
        tools.append(Tool(
            name="mobile_click_by_som",
            description="🎯 根据 SoM 编号点击元素\n\n"
                       "配合 mobile_screenshot_with_som 使用。\n"
                       "看图后直接说'点击 3 号'，调用此函数即可。\n\n"
                       "⚠️ 【重要】点击后建议再次截图确认操作是否成功！",
            inputSchema={
                "type": "object",
                "properties": {
                    "index": {
                        "type": "integer",
                        "description": "元素编号（从 1 开始，对应截图中的标注数字）"
                    }
                },
                "required": ["index"]
            }
        ))
        
        tools.append(Tool(
            name="mobile_screenshot_with_grid",
            description="📸📏 带网格坐标的截图（精确定位神器！）\n\n"
                       "在截图上绘制网格线和坐标刻度，帮助快速定位元素位置。\n"
                       "如果检测到弹窗，会用绿色圆圈标注可能的关闭按钮位置。\n\n"
                       "🎯 适用场景：\n"
                       "- 需要精确知道某个元素的坐标\n"
                       "- 关闭广告弹窗时定位 X 按钮\n"
                       "- 元素不在控件树中时的视觉定位\n\n"
                       "💡 返回信息：\n"
                       "- 带网格标注的截图\n"
                       "- 弹窗边界坐标（如果检测到）\n"
                       "- 可能的关闭按钮位置列表（带优先级）\n\n"
                       "🔴 【必须】点击后必须再次截图确认操作是否成功！",
            inputSchema={
                "type": "object",
                "properties": {
                    "grid_size": {
                        "type": "integer", 
                        "description": "网格间距（像素），默认 100。值越小网格越密，建议 50-200"
                    },
                    "show_popup_hints": {
                        "type": "boolean",
                        "description": "是否显示弹窗关闭按钮提示位置，默认 true"
                    }
                },
                "required": []
            }
        ))
        
        # ==================== 点击操作 ====================
        tools.append(Tool(
            name="mobile_click_by_text",
            description="👆 通过文本点击元素（最推荐）\n\n"
                       "✅ 最稳定的定位方式，跨设备兼容\n"
                       "✅ 实时检测元素是否存在，元素不存在会报错\n"
                       "✅ 不会误点击到其他位置\n"
                       "📋 使用前先调用 mobile_list_elements 确认元素文本\n"
                       "💡 定位优先级：文本 > ID > 百分比 > 坐标\n\n"
                       "📍 当页面有多个相同文案时，可使用 position 参数指定位置：\n"
                       "   - 垂直方向: \"top\"/\"upper\"/\"上\", \"bottom\"/\"lower\"/\"下\", \"middle\"/\"center\"/\"中\"\n"
                       "   - 水平方向: \"left\"/\"左\", \"right\"/\"右\", \"center\"/\"中\"\n"
                       "   例如：点击\"底部\"的\"微剧\"tab，使用 position=\"bottom\"",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "元素的文本内容（精确匹配）"},
                    "position": {"type": "string", "description": "位置信息（可选）。当有多个相同文案时使用，支持：top/bottom/left/right/middle 或 上/下/左/右/中"}
                },
                "required": ["text"]
            }
        ))
        
        tools.append(Tool(
            name="mobile_click_by_id",
            description="👆 通过 resource-id 点击元素（推荐）\n\n"
                       "✅ 稳定的定位方式\n"
                       "✅ 实时检测元素是否存在，元素不存在会报错\n"
                       "📋 使用前先调用 mobile_list_elements 获取元素 ID\n"
                       "💡 当有多个相同 ID 的元素时，用 index 指定第几个（从 0 开始）\n"
                       "💡 定位优先级：文本 > ID > 百分比 > 坐标",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_id": {"type": "string", "description": "元素的 resource-id"},
                    "index": {"type": "integer", "description": "第几个元素（从 0 开始），默认 0 表示第一个", "default": 0}
                },
                "required": ["resource_id"]
            }
        ))
        
        tools.append(Tool(
            name="mobile_click_at_coords",
            description="👆 点击指定坐标（兜底方案）\n\n"
                       "⚠️ 【重要】优先使用 mobile_click_by_text 或 mobile_click_by_id！\n"
                       "仅在 mobile_list_elements 无法获取元素时使用此工具。\n\n"
                       "⚠️ 【时序限制】截图分析期间页面可能变化：\n"
                       "- 坐标是基于截图时刻的，点击时页面可能已不同\n"
                       "- 如果误点击，调用 mobile_press_key(back) 返回\n"
                       "- 对于定时弹窗（如广告），建议等待其自动消失\n\n"
                       "📐 坐标转换：截图返回的 image_width/height 等参数直接传入即可\n\n"
                       "🔴 【必须】点击后必须再次截图确认操作是否成功！",
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
                       "💡 录制一次，多设备回放\n\n"
                       "🔴 【必须】点击后必须再次截图确认操作是否成功！",
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
            description="👆 通过 resource-id 长按（⭐⭐ 最稳定！）\n\n"
                       "✅ 最稳定的长按定位方式，跨设备完美兼容\n"
                       "📋 使用前请先调用 mobile_list_elements 获取元素 ID\n"
                       "💡 生成的脚本使用 d(resourceId='...').long_click() 定位，最稳定",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_id": {"type": "string", "description": "元素的 resource-id"},
                    "duration": {"type": "number", "description": "长按持续时间（秒），默认 1.0"}
                },
                "required": ["resource_id"]
            }
        ))
        
        tools.append(Tool(
            name="mobile_long_press_by_text",
            description="👆 通过文本长按（⭐ 推荐！）\n\n"
                       "✅ 优势：跨设备兼容，不受屏幕分辨率影响\n"
                       "📋 使用前请先调用 mobile_list_elements 确认元素有文本\n"
                       "💡 生成的脚本使用 d(text='...').long_click() 定位，稳定可靠",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "元素的文本内容（精确匹配）"},
                    "duration": {"type": "number", "description": "长按持续时间（秒），默认 1.0"}
                },
                "required": ["text"]
            }
        ))
        
        tools.append(Tool(
            name="mobile_long_press_by_percent",
            description="👆 通过百分比位置长按（跨设备兼容！）\n\n"
                       "🎯 原理：屏幕左上角是 (0%, 0%)，右下角是 (100%, 100%)\n"
                       "📐 示例：\n"
                       "   - (50, 50) = 屏幕正中央\n"
                       "   - (10, 5) = 左上角附近\n"
                       "   - (85, 90) = 右下角附近\n\n"
                       "✅ 优势：同样的百分比在不同分辨率设备上都能长按到相同相对位置\n"
                       "💡 录制一次，多设备回放",
            inputSchema={
                "type": "object",
                "properties": {
                    "x_percent": {"type": "number", "description": "X 轴百分比 (0-100)"},
                    "y_percent": {"type": "number", "description": "Y 轴百分比 (0-100)"},
                    "duration": {"type": "number", "description": "长按持续时间（秒），默认 1.0"}
                },
                "required": ["x_percent", "y_percent"]
            }
        ))
        
        tools.append(Tool(
            name="mobile_long_press_at_coords",
            description="👆 长按指定坐标（⚠️ 兜底方案，优先用文本/ID定位！）\n\n"
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
                    "duration": {"type": "number", "description": "长按持续时间（秒），默认 1.0"},
                    "image_width": {"type": "number", "description": "压缩后图片宽度"},
                    "image_height": {"type": "number", "description": "压缩后图片高度"},
                    "original_img_width": {"type": "number", "description": "原图宽度"},
                    "original_img_height": {"type": "number", "description": "原图高度"},
                    "crop_offset_x": {"type": "number", "description": "局部截图 X 偏移"},
                    "crop_offset_y": {"type": "number", "description": "局部截图 Y 偏移"}
                },
                "required": ["x", "y"]
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
            description="👆 滑动屏幕。方向：up/down/left/right\n\n"
                       "💡 左右滑动时，可指定高度坐标或百分比：\n"
                       "- y: 指定高度坐标（像素）\n"
                       "- y_percent: 指定高度百分比 (0-100)\n"
                       "- 两者都未指定时，使用屏幕中心高度",
            inputSchema={
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["up", "down", "left", "right"],
                        "description": "滑动方向"
                    },
                    "y": {
                        "type": "integer",
                        "description": "左右滑动时指定的高度坐标（像素，0-屏幕高度）"
                    },
                    "y_percent": {
                        "type": "number",
                        "description": "左右滑动时指定的高度百分比 (0-100)"
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
            name="mobile_find_close_button",
            description="""🔍 智能查找关闭按钮（只找不点，返回位置）

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
3. 如果返回 success=false，才需要截图分析""",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ))
        
        tools.append(Tool(
            name="mobile_close_popup",
            description="""🚫 智能关闭弹窗

通过控件树识别并点击关闭按钮（×、关闭、跳过等）。

✅ 控件树有元素时：直接点击，实时可靠
❌ 控件树无元素时：截图供 AI 分析

⚠️ 【时序限制】如果需要截图分析：
- 分析期间弹窗可能自动消失
- 对于定时弹窗（如广告），建议等待其自动消失
- 点击前可再次截图确认弹窗是否还在

🔴 【必须】点击关闭后，必须再次截图确认弹窗是否真的关闭了！
如果弹窗仍在，需要尝试其他方法或位置。""",
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
        
        # ==================== Toast 检测工具（仅 Android）====================
        tools.append(Tool(
            name="mobile_start_toast_watch",
            description="""🔔 开始监听 Toast（仅 Android）

⚠️ 【重要】必须在执行操作之前调用！

📋 正确流程（三步走）：
1️⃣ 调用 mobile_start_toast_watch() 开始监听
2️⃣ 执行操作（如点击提交按钮）
3️⃣ 调用 mobile_get_toast() 或 mobile_assert_toast() 获取结果

❌ 错误用法：先点击按钮，再调用此工具（Toast 可能已消失）""",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ))
        
        tools.append(Tool(
            name="mobile_get_toast",
            description="""🍞 获取 Toast 消息（仅 Android）

Toast 是 Android 系统级的短暂提示消息，常用于显示操作结果。
⚠️ Toast 不在控件树中，无法通过 mobile_list_elements 获取。

📋 推荐用法（三步走）：
1️⃣ mobile_start_toast_watch() - 开始监听
2️⃣ 执行操作（点击按钮等）
3️⃣ mobile_get_toast() - 获取 Toast

⏱️ timeout 设置等待时间，默认 5 秒。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "timeout": {"type": "number", "description": "等待 Toast 出现的超时时间（秒），默认 5"},
                    "reset_first": {"type": "boolean", "description": "是否先清除旧缓存，默认 False"}
                },
                "required": []
            }
        ))
        
        tools.append(Tool(
            name="mobile_assert_toast",
            description="""✅ 断言 Toast 消息（仅 Android）

等待 Toast 出现并验证内容是否符合预期。

📋 推荐用法（三步走）：
1️⃣ mobile_start_toast_watch() - 开始监听
2️⃣ 执行操作（点击按钮等）
3️⃣ mobile_assert_toast(expected_text="成功") - 断言

💡 支持包含匹配（默认）和精确匹配。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "expected_text": {"type": "string", "description": "期望的 Toast 文本"},
                    "timeout": {"type": "number", "description": "等待超时时间（秒），默认 5"},
                    "contains": {"type": "boolean", "description": "True=包含匹配（默认），False=精确匹配"}
                },
                "required": ["expected_text"]
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
                       "📋 录制流程：清空历史 → 执行操作（优先用文本/ID定位）→ 生成脚本",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ))
        
        tools.append(Tool(
            name="mobile_generate_test_script",
            description="📝 生成 pytest 测试脚本。基于操作历史自动生成。\n\n"
                       "⚠️ 【重要】录制操作时请优先使用稳定定位：\n"
                       "1️⃣ 先调用 mobile_list_elements 获取元素列表\n"
                       "2️⃣ 优先用 mobile_click_by_text（最稳定，跨设备兼容）\n"
                       "3️⃣ 其次用 mobile_click_by_id（稳定）\n"
                       "4️⃣ 最后才用坐标点击（会自动转百分比，跨分辨率兼容）\n\n"
                       "使用流程：\n"
                       "1. 清空历史 mobile_clear_operation_history\n"
                       "2. 执行操作（优先用文本/ID定位）\n"
                       "3. 调用此工具生成脚本\n"
                       "4. 脚本保存到 tests/ 目录\n\n"
                       "💡 定位优先级：文本 > ID > 百分比 > 坐标",
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
        
        # ==================== 广告弹窗关闭工具 ====================
        tools.append(Tool(
            name="mobile_close_ad",
            description="""🚫 【推荐】智能关闭广告弹窗

⚡ 直接调用即可，无需先截图！会自动按优先级尝试：

1️⃣ **控件树查找**（最可靠，优先）
   - 自动查找 resource-id 包含 close/dismiss
   - 查找文本"关闭"、"跳过"、"×"等
   - 找到直接点击，实时可靠

2️⃣ **模板匹配**（次优）
   - 用 OpenCV 匹配已保存的 X 按钮模板
   - 模板越多成功率越高

3️⃣ **返回截图供 AI 分析**（兜底）
   - 前两步都失败才截图
   - AI 分析后用 mobile_click_by_percent 点击
   - 点击成功后用 mobile_template_add 添加模板

💡 正确流程：
1. 遇到广告弹窗 → 直接调用此工具
2. 如果成功 → 完成
3. 只有失败时才需要截图分析
3. 如果失败 → 看截图找 X → 点击 → 添加模板""",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ))
        
        tools.append(Tool(
            name="mobile_template_close",
            description="""🎯 模板匹配关闭弹窗（仅模板匹配）

只用 OpenCV 模板匹配，不走控件树。
一般建议用 mobile_close_ad 代替（会自动先查控件树）。

⚙️ 参数：
- click: 是否点击，默认 true
- threshold: 匹配阈值 0-1，默认 0.75""",
            inputSchema={
                "type": "object",
                "properties": {
                    "click": {"type": "boolean", "description": "是否点击，默认 true"},
                    "threshold": {"type": "number", "description": "匹配阈值 0-1，默认 0.75"}
                },
                "required": []
            }
        ))
        
        tools.append(Tool(
            name="mobile_template_add",
            description="""➕ 添加 X 号模板

遇到新样式 X 号时，截图并添加到模板库。

⚙️ 两种方式（二选一）：
1. 百分比定位（推荐）：提供 x_percent, y_percent, size
2. 像素定位：提供 screenshot_path, x, y, width, height

📋 流程：
1. mobile_screenshot_with_grid 查看 X 号位置
2. 调用此工具添加模板
3. 下次同样 X 号就能自动匹配

💡 百分比示例：X 在右上角 → x_percent=85, y_percent=12, size=80""",
            inputSchema={
                "type": "object",
                "properties": {
                    "template_name": {"type": "string", "description": "模板名称"},
                    "x_percent": {"type": "number", "description": "X号中心水平百分比 (0-100)"},
                    "y_percent": {"type": "number", "description": "X号中心垂直百分比 (0-100)"},
                    "size": {"type": "integer", "description": "裁剪正方形边长（像素）"},
                    "screenshot_path": {"type": "string", "description": "截图路径（像素定位时用）"},
                    "x": {"type": "integer", "description": "左上角 X 坐标"},
                    "y": {"type": "integer", "description": "左上角 Y 坐标"},
                    "width": {"type": "integer", "description": "裁剪宽度"},
                    "height": {"type": "integer", "description": "裁剪高度"}
                },
                "required": ["template_name"]
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
                    position=arguments.get("position")
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
                    y_percent=arguments.get("y_percent")
                )
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
            
            elif name == "mobile_find_close_button":
                result = self.tools.find_close_button()
                return [TextContent(type="text", text=self.format_response(result))]
            
            elif name == "mobile_close_popup":
                result = self.tools.close_popup()
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
    
    print("🚀 Mobile MCP Server 启动中... [26 个工具]", file=sys.stderr)
    print("📱 支持 Android / iOS", file=sys.stderr)
    print("👁️ 完全依赖 Cursor 视觉能力，无需 AI 密钥", file=sys.stderr)
    
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(read_stream, write_stream, mcp_server.create_initialization_options())


def main():
    """入口点函数（供 pip 安装后使用）"""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

