#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础 MCP 工具 - 不需要 AI 密钥

提供基础的移动端自动化工具：
- 元素列表获取
- 精确点击（resource-id/坐标/文本）
- 输入、滑动、按键等
- 截图功能
- 设备管理（列表、屏幕尺寸、方向）
- 应用管理（启动、安装、卸载、终止）
- 高级交互（双击、长按）
"""

from typing import Dict, List, Optional
from pathlib import Path
import time
import json

from .dynamic_config import DynamicConfig
from .utils.operation_history_manager import OperationHistoryManager


class BasicMobileTools:
    """基础移动端工具（不依赖 AI）"""
    
    def __init__(self, mobile_client):
        """
        初始化基础工具
        
        Args:
            mobile_client: MobileClient 实例
        """
        self.client = mobile_client
        
        # 截图目录
        project_root = Path(__file__).parent.parent.parent.parent
        self.screenshot_dir = project_root / "backend" / "mobile_mcp" / "screenshots"
        self.screenshot_dir.mkdir(exist_ok=True)
    
    def list_elements(self) -> List[Dict]:
        """
        列出页面所有可交互元素
        
        Returns:
            元素列表，每个元素包含：
            - resource_id: 资源ID
            - text: 文本内容
            - content_desc: 描述
            - class_name: 类名
            - bounds: 坐标 [x1,y1][x2,y2]
            - clickable: 是否可点击
            - enabled: 是否启用
        
        示例：
            elements = tools.list_elements()
            # [
            #   {
            #     "resource_id": "com.app:id/search",
            #     "text": "搜索",
            #     "bounds": "[100,200][300,400]",
            #     "clickable": true
            #   },
            #   ...
            # ]
        """
        xml_string = self.client.u2.dump_hierarchy()
        elements = self.client.xml_parser.parse(xml_string)
        
        # 过滤掉不可交互的元素，简化返回
        interactive_elements = []
        for elem in elements:
            if elem.get('clickable') or elem.get('long_clickable') or elem.get('focusable'):
                interactive_elements.append({
                    'resource_id': elem.get('resource_id', ''),
                    'text': elem.get('text', ''),
                    'content_desc': elem.get('content_desc', ''),
                    'class_name': elem.get('class_name', ''),
                    'bounds': elem.get('bounds', ''),
                    'clickable': elem.get('clickable', False),
                    'enabled': elem.get('enabled', True)
                })
        
        return interactive_elements
    
    def click_by_id(self, resource_id: str) -> Dict:
        """
        通过 resource-id 点击元素
        
        Args:
            resource_id: 元素的 resource-id（如 "com.app:id/search"）
        
        Returns:
            {"success": true/false, "message": "..."}
        
        示例：
            tools.click_by_id("com.duitang.main:id/search_btn")
        """
        try:
            element = self.client.u2(resourceId=resource_id)
            
            # 先检查元素是否存在（timeout=0.5秒快速检查）
            if not element.exists(timeout=0.5):
                return {"success": False, "message": f"❌ 元素不存在: {resource_id}"}
            
            # 元素存在，执行点击
            element.click()
            
            # 点击后等待页面响应（使用动态配置）
            time.sleep(DynamicConfig.wait_after_click)
            
            return {
                "success": True, 
                "message": f"✅ 点击成功！已点击元素: {resource_id}\n⚠️ 无需重复点击，操作已完成。"
            }
        except Exception as e:
            return {"success": False, "message": f"❌ 点击失败: {str(e)}"}
    
    def click_by_text(self, text: str) -> Dict:
        """
        通过文本内容点击元素
        
        Args:
            text: 元素的文本内容（精确匹配）
        
        Returns:
            {"success": true/false, "message": "..."}
        
        示例：
            tools.click_by_text("登录")
        """
        try:
            element = self.client.u2(text=text)
            
            # 先检查元素是否存在（timeout=0.5秒快速检查）
            if not element.exists(timeout=0.5):
                return {"success": False, "message": f"❌ 文本不存在: {text}"}
            
            # 元素存在，执行点击
            element.click()
            
            # 点击后等待页面响应（使用动态配置）
            time.sleep(DynamicConfig.wait_after_click)
            
            return {
                "success": True, 
                "message": f"✅ 点击成功！已点击按钮: '{text}'\n⚠️ 无需重复点击或使用其他方式点击，操作已完成。"
            }
        except Exception as e:
            return {"success": False, "message": f"❌ 点击失败: {str(e)}"}
    
    def click_at_coords(self, x: int, y: int) -> Dict:
        """
        点击指定坐标
        
        Args:
            x: X 坐标
            y: Y 坐标
        
        Returns:
            {"success": true/false, "message": "..."}
        
        示例：
            tools.click_at_coords(500, 300)
        """
        try:
            self.client.u2.click(x, y)
            # 点击后等待页面响应（使用动态配置）
            time.sleep(DynamicConfig.wait_after_click)
            return {
                "success": True, 
                "message": f"✅ 点击成功！坐标: ({x}, {y})\n⚠️ 无需重复点击，操作已完成。"
            }
        except Exception as e:
            return {"success": False, "message": f"❌ 点击失败: {str(e)}"}
    
    def input_text_by_id(self, resource_id: str, text: str) -> Dict:
        """
        通过 resource-id 在输入框输入文本
        
        Args:
            resource_id: 输入框的 resource-id
            text: 要输入的文本
        
        Returns:
            {"success": true/false, "message": "..."}
        
        示例:
            tools.input_text_by_id("com.app:id/username", "test@example.com")
        """
        try:
            element = self.client.u2(resourceId=resource_id)
            if element.exists:
                element.set_text(text)
                # 输入后等待UI更新（使用动态配置）
                time.sleep(DynamicConfig.wait_after_input)
                return {
                    "success": True, 
                    "message": f"✅ 输入成功！已输入文本: '{text}'\n⚠️ 无需重复输入，操作已完成。"
                }
            else:
                return {"success": False, "message": f"❌ 输入框不存在: {resource_id}"}
        except Exception as e:
            return {"success": False, "message": f"❌ 输入失败: {str(e)}"}
    
    def get_element_info(self, resource_id: str) -> Optional[Dict]:
        """
        获取指定元素的详细信息
        
        Args:
            resource_id: 元素的 resource-id
        
        Returns:
            元素信息字典，如果不存在返回 None
        
        示例：
            info = tools.get_element_info("com.app:id/search")
            # {
            #   "text": "搜索",
            #   "bounds": "[100,200][300,400]",
            #   "enabled": true
            # }
        """
        try:
            element = self.client.u2(resourceId=resource_id)
            if element.exists:
                info = element.info
                return {
                    'text': info.get('text', ''),
                    'content_desc': info.get('contentDescription', ''),
                    'class_name': info.get('className', ''),
                    'bounds': info.get('bounds', {}),
                    'clickable': info.get('clickable', False),
                    'enabled': info.get('enabled', True),
                    'focused': info.get('focused', False),
                    'selected': info.get('selected', False)
                }
            else:
                return None
        except Exception as e:
            return None
    
    def find_elements_by_class(self, class_name: str) -> List[Dict]:
        """
        查找指定类名的所有元素
        
        Args:
            class_name: 类名（如 "android.widget.EditText"）
        
        Returns:
            元素列表
        
        示例：
            # 查找所有输入框
            edit_texts = tools.find_elements_by_class("android.widget.EditText")
        """
        xml_string = self.client.u2.dump_hierarchy()
        elements = self.client.xml_parser.parse(xml_string)
        
        matched = []
        for elem in elements:
            if elem.get('class_name') == class_name:
                matched.append({
                    'resource_id': elem.get('resource_id', ''),
                    'text': elem.get('text', ''),
                    'content_desc': elem.get('content_desc', ''),
                    'bounds': elem.get('bounds', ''),
                    'clickable': elem.get('clickable', False),
                })
        
        return matched
    
    def wait_for_element(self, resource_id: str, timeout: int = 10) -> Dict:
        """
        等待元素出现
        
        Args:
            resource_id: 元素的 resource-id
            timeout: 超时时间（秒）
        
        Returns:
            {"success": true/false, "message": "...", "exists": true/false}
        
        示例：
            result = tools.wait_for_element("com.app:id/login_btn", timeout=5)
        """
        try:
            exists = self.client.u2(resourceId=resource_id).wait(timeout=timeout)
            if exists:
                return {
                    "success": True,
                    "exists": True,
                    "message": f"元素已出现: {resource_id}"
                }
            else:
                return {
                    "success": False,
                    "exists": False,
                    "message": f"等待超时: {resource_id}"
                }
        except Exception as e:
            return {
                "success": False,
                "exists": False,
                "message": f"等待失败: {str(e)}"
            }
    
    def take_screenshot(self, description: str = "") -> Dict:
        """
        截取屏幕截图（不需要 AI）
        
        Args:
            description: 截图描述（可选），用于生成文件名
        
        Returns:
            {
                "success": true/false,
                "screenshot_path": "截图保存路径",
                "message": "..."
            }
        
        示例：
            result = tools.take_screenshot("登录页面")
            # {"success": true, "screenshot_path": "/path/to/screenshot_登录页面_xxx.png"}
        
        用途：
        - 用于 Cursor AI 视觉识别
        - 调试页面状态
        - 记录测试过程
        """
        try:
            import re
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            
            # 清理描述中的特殊字符
            if description:
                safe_desc = re.sub(r'[^\w\s-]', '', description).strip()
                safe_desc = re.sub(r'[\s]+', '_', safe_desc)
                filename = f"screenshot_{safe_desc}_{timestamp}.png"
            else:
                filename = f"screenshot_{timestamp}.png"
            
            screenshot_path = self.screenshot_dir / filename
            
            # 截图
            self.client.u2.screenshot(str(screenshot_path))
            
            return {
                "success": True,
                "screenshot_path": str(screenshot_path),
                "message": f"截图已保存: {screenshot_path}"
            }
        except Exception as e:
            return {
                "success": False,
                "screenshot_path": "",
                "message": f"截图失败: {str(e)}"
            }
    
    def take_screenshot_region(self, x1: int, y1: int, x2: int, y2: int, description: str = "") -> Dict:
        """
        截取屏幕指定区域（不需要 AI）
        
        Args:
            x1, y1: 左上角坐标
            x2, y2: 右下角坐标
            description: 截图描述（可选）
        
        Returns:
            {"success": true/false, "screenshot_path": "...", "message": "..."}
        
        示例：
            result = tools.take_screenshot_region(100, 200, 500, 800, "搜索框区域")
        """
        try:
            from PIL import Image
            import re
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            
            # 清理描述
            if description:
                safe_desc = re.sub(r'[^\w\s-]', '', description).strip()
                safe_desc = re.sub(r'[\s]+', '_', safe_desc)
                filename = f"screenshot_region_{safe_desc}_{timestamp}.png"
            else:
                filename = f"screenshot_region_{timestamp}.png"
            
            # 先截全屏
            temp_path = self.screenshot_dir / f"temp_{timestamp}.png"
            self.client.u2.screenshot(str(temp_path))
            
            # 裁剪指定区域
            img = Image.open(str(temp_path))
            cropped = img.crop((x1, y1, x2, y2))
            
            screenshot_path = self.screenshot_dir / filename
            cropped.save(str(screenshot_path))
            
            # 删除临时文件
            temp_path.unlink()
            
            return {
                "success": True,
                "screenshot_path": str(screenshot_path),
                "message": f"区域截图已保存: {screenshot_path}"
            }
        except Exception as e:
            return {
                "success": False,
                "screenshot_path": "",
                "message": f"区域截图失败: {str(e)}"
            }
    
    # ==================== 设备管理工具 ====================
    
    def list_devices(self) -> Dict:
        """
        列出所有已连接的 Android 设备
        
        Returns:
            {"success": true/false, "devices": [...], "count": N}
        """
        try:
            from .device_manager import DeviceManager
            manager = DeviceManager()
            devices = manager.list_devices()
            
            return {
                "success": True,
                "devices": devices,
                "count": len(devices),
                "message": f"找到 {len(devices)} 个设备"
            }
        except Exception as e:
            return {"success": False, "error": f"获取设备列表失败: {str(e)}"}
    
    def get_screen_size(self) -> Dict:
        """
        获取设备屏幕尺寸
        
        Returns:
            {"success": true/false, "width": N, "height": N, "size": "WxH"}
        """
        try:
            info = self.client.u2.info
            width = info.get('displayWidth', 0)
            height = info.get('displayHeight', 0)
            
            return {
                "success": True,
                "width": width,
                "height": height,
                "size": f"{width}x{height}",
                "message": f"屏幕尺寸: {width}x{height}"
            }
        except Exception as e:
            return {"success": False, "error": f"获取屏幕尺寸失败: {str(e)}"}
    
    def get_orientation(self) -> Dict:
        """
        获取当前屏幕方向
        
        Returns:
            {"success": true/false, "orientation": "portrait/landscape", "rotation": N}
        """
        try:
            info = self.client.u2.info
            rotation = info.get('displayRotation', 0)
            
            # 0或2 = 竖屏, 1或3 = 横屏
            is_portrait = rotation in [0, 2]
            orientation = "portrait" if is_portrait else "landscape"
            
            return {
                "success": True,
                "orientation": orientation,
                "rotation": rotation,
                "message": f"当前方向: {orientation}"
            }
        except Exception as e:
            return {"success": False, "error": f"获取屏幕方向失败: {str(e)}"}
    
    def set_orientation(self, orientation: str) -> Dict:
        """
        设置屏幕方向
        
        Args:
            orientation: "portrait"（竖屏）或 "landscape"（横屏）
        
        Returns:
            {"success": true/false, "orientation": "...", "message": "..."}
        """
        try:
            if orientation not in ["portrait", "landscape"]:
                return {"success": False, "error": "orientation必须是'portrait'或'landscape'"}
            
            # 设置方向
            if orientation == "portrait":
                self.client.u2.set_orientation("n")
            else:
                self.client.u2.set_orientation("l")
            
            return {
                "success": True,
                "orientation": orientation,
                "message": f"屏幕方向已设置为: {orientation}"
            }
        except Exception as e:
            return {"success": False, "error": f"设置屏幕方向失败: {str(e)}"}
    
    # ==================== 应用管理工具 ====================
    
    def list_apps(self, filter_keyword: str = "") -> Dict:
        """
        列出设备上已安装的应用
        
        Args:
            filter_keyword: 过滤关键词（可选）
        
        Returns:
            {"success": true/false, "apps": [...], "count": N}
        """
        try:
            apps = self.client.u2.app_list()
            
            # 过滤
            if filter_keyword:
                filtered_apps = [
                    app for app in apps
                    if filter_keyword.lower() in app.lower()
                ]
            else:
                filtered_apps = apps
            
            return {
                "success": True,
                "apps": filtered_apps,
                "count": len(filtered_apps),
                "total": len(apps),
                "message": f"找到 {len(filtered_apps)}/{len(apps)} 个应用"
            }
        except Exception as e:
            return {"success": False, "error": f"获取应用列表失败: {str(e)}"}
    
    def install_app(self, apk_path: str) -> Dict:
        """
        安装 APK 文件
        
        Args:
            apk_path: APK 文件路径
        
        Returns:
            {"success": true/false, "message": "..."}
        """
        try:
            import os
            
            # 检查文件是否存在
            if not os.path.exists(apk_path):
                return {"success": False, "error": f"APK文件不存在: {apk_path}"}
            
            # 安装应用
            self.client.u2.app_install(apk_path)
            
            return {
                "success": True,
                "apk_path": apk_path,
                "message": f"应用安装成功: {apk_path}"
            }
        except Exception as e:
            return {"success": False, "error": f"安装应用失败: {str(e)}"}
    
    def uninstall_app(self, package_name: str) -> Dict:
        """
        卸载应用
        
        Args:
            package_name: 应用包名
        
        Returns:
            {"success": true/false, "message": "..."}
        """
        try:
            self.client.u2.app_uninstall(package_name)
            
            return {
                "success": True,
                "package_name": package_name,
                "message": f"应用卸载成功: {package_name}"
            }
        except Exception as e:
            return {"success": False, "error": f"卸载应用失败: {str(e)}"}
    
    def terminate_app(self, package_name: str) -> Dict:
        """
        终止应用（强制停止）
        
        Args:
            package_name: 应用包名
        
        Returns:
            {"success": true/false, "message": "..."}
        """
        try:
            self.client.u2.app_stop(package_name)
            
            return {
                "success": True,
                "package_name": package_name,
                "message": f"应用已终止: {package_name}"
            }
        except Exception as e:
            return {"success": False, "error": f"终止应用失败: {str(e)}"}
    
    def get_current_package(self) -> Dict:
        """
        获取当前前台应用的包名
        
        Returns:
            {"success": true/false, "package": "...", "activity": "..."}
        """
        try:
            current = self.client.u2.app_current()
            
            return {
                "success": True,
                "package": current.get('package', ''),
                "activity": current.get('activity', ''),
                "message": f"当前应用: {current.get('package', '')}"
            }
        except Exception as e:
            return {"success": False, "error": f"获取当前包名失败: {str(e)}"}
    
    # ==================== 高级交互工具 ====================
    
    def double_click_at_coords(self, x: int, y: int) -> Dict:
        """
        双击指定坐标
        
        Args:
            x: X 坐标
            y: Y 坐标
        
        Returns:
            {"success": true/false, "message": "..."}
        """
        try:
            self.client.u2.double_click(x, y)
            return {
                "success": True,
                "x": x,
                "y": y,
                "message": f"双击坐标: ({x}, {y})"
            }
        except Exception as e:
            return {"success": False, "error": f"双击失败: {str(e)}"}
    
    def long_press_at_coords(self, x: int, y: int, duration: float = 1.0) -> Dict:
        """
        长按指定坐标
        
        Args:
            x: X 坐标
            y: Y 坐标
            duration: 长按时长（秒），默认 1.0
        
        Returns:
            {"success": true/false, "message": "..."}
        """
        try:
            self.client.u2.long_click(x, y, duration=duration)
            return {
                "success": True,
                "x": x,
                "y": y,
                "duration": duration,
                "message": f"长按坐标: ({x}, {y}), 持续{duration}秒"
            }
        except Exception as e:
            return {"success": False, "error": f"长按失败: {str(e)}"}
    
    def open_url(self, url: str) -> Dict:
        """
        在设备浏览器中打开 URL
        
        Args:
            url: 要打开的 URL
        
        Returns:
            {"success": true/false, "message": "..."}
        """
        try:
            self.client.u2.open_url(url)
            return {
                "success": True,
                "url": url,
                "message": f"已打开URL: {url}"
            }
        except Exception as e:
            return {"success": False, "error": f"打开URL失败: {str(e)}"}
    
    def assert_text(self, text: str) -> Dict:
        """
        断言页面中是否包含指定文本
        
        Args:
            text: 要检查的文本
        
        Returns:
            {"success": true/false, "found": true/false, "message": "..."}
        """
        try:
            exists = self.client.u2(text=text).exists()
            
            return {
                "success": True,
                "found": exists,
                "text": text,
                "message": f"文本'{text}' {'存在' if exists else '不存在'}"
            }
        except Exception as e:
            return {"success": False, "error": f"断言失败: {str(e)}"}
    
    # ==================== 等待工具 ====================
    
    def wait(self, seconds: Optional[float] = None, wait_for_text: Optional[str] = None, 
             wait_for_id: Optional[str] = None, timeout: float = 10) -> Dict:
        """
        通用等待工具 - 让 AI 根据场景灵活控制等待
        
        Args:
            seconds: 固定等待时间（秒），如等待广告加载
            wait_for_text: 等待指定文本出现，如 "首页"、"搜索结果"
            wait_for_id: 等待指定元素ID出现，如 "com.app:id/home"
            timeout: 等待元素的超时时间（秒），默认10秒
        
        Returns:
            {"success": true/false, "message": "...", "waited": N}
        
        使用场景：
        1. 打开App等广告：wait(seconds=5)
        2. 等待搜索结果：wait(wait_for_text="搜索结果")
        3. 等待页面加载：wait(wait_for_id="com.app:id/main")
        
        示例：
            # 等待3秒广告
            tools.wait(seconds=3)
            
            # 等待"首页"文本出现
            tools.wait(wait_for_text="首页", timeout=5)
            
            # 等待主页元素出现
            tools.wait(wait_for_id="com.app:id/home_layout")
        """
        import time
        
        try:
            start_time = time.time()
            
            # 场景1: 固定等待时间
            if seconds:
                time.sleep(seconds)
                return {
                    "success": True,
                    "waited": seconds,
                    "message": f"已等待 {seconds} 秒"
                }
            
            # 场景2: 等待文本出现
            elif wait_for_text:
                exists = self.client.u2(text=wait_for_text).wait(timeout=timeout)
                waited_time = time.time() - start_time
                
                if exists:
                    return {
                        "success": True,
                        "waited": round(waited_time, 2),
                        "message": f"文本'{wait_for_text}'已出现，等待了 {waited_time:.1f} 秒"
                    }
                else:
                    return {
                        "success": False,
                        "waited": timeout,
                        "message": f"等待超时：文本'{wait_for_text}'未出现（{timeout}秒）"
                    }
            
            # 场景3: 等待元素ID出现
            elif wait_for_id:
                exists = self.client.u2(resourceId=wait_for_id).wait(timeout=timeout)
                waited_time = time.time() - start_time
                
                if exists:
                    return {
                        "success": True,
                        "waited": round(waited_time, 2),
                        "message": f"元素'{wait_for_id}'已出现，等待了 {waited_time:.1f} 秒"
                    }
                else:
                    return {
                        "success": False,
                        "waited": timeout,
                        "message": f"等待超时：元素'{wait_for_id}'未出现（{timeout}秒）"
                    }
            
            else:
                return {
                    "success": False,
                    "error": "请指定等待条件：seconds, wait_for_text 或 wait_for_id"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"等待失败: {str(e)}"
            }
    
    def check_connection(self) -> Dict:
        """
        检查设备连接状态
        
        Returns:
            连接状态信息
        """
        try:
            # 尝试获取设备信息
            device_info = self.client.u2.device_info
            screen_size = self.client.u2.window_size()
            
            return {
                "success": True,
                "connected": True,
                "device_info": {
                    "serial": device_info.get("serial", "unknown"),
                    "brand": device_info.get("brand", "unknown"),
                    "model": device_info.get("model", "unknown"),
                    "version": device_info.get("version", "unknown"),
                    "screen_size": f"{screen_size[0]}x{screen_size[1]}"
                },
                "message": "✅ 设备已连接"
            }
        except Exception as e:
            return {
                "success": False,
                "connected": False,
                "error": str(e),
                "message": f"❌ 设备未连接: {str(e)}"
            }
    
    def reconnect_device(self) -> Dict:
        """
        重新连接设备
        
        Returns:
            重连结果
        """
        try:
            # 通过 device_manager 重新连接，保持原有配置
            if hasattr(self.client, 'device_manager') and self.client.device_manager:
                self.client.u2 = self.client.device_manager.connect()
            else:
                # 降级方案：直接重连默认设备
                import uiautomator2 as u2
                self.client.u2 = u2.connect()
            
            # 验证连接
            device_info = self.client.u2.device_info
            
            return {
                "success": True,
                "device_info": {
                    "serial": device_info.get("serial", "unknown"),
                    "model": device_info.get("model", "unknown")
                },
                "message": f"✅ 重连成功: {device_info.get('brand', '')} {device_info.get('model', 'unknown')}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ 重连失败: {str(e)}",
                "suggestion": "请检查设备USB连接或执行 'adb devices'"
            }
    
    def get_operation_history(self, limit: Optional[int] = None) -> Dict:
        """
        获取操作历史记录
        
        Args:
            limit: 返回最近的N条记录，None表示全部
            
        Returns:
            历史记录信息
        """
        try:
            history_manager = OperationHistoryManager()
            operations = history_manager.load(limit=limit)  # load已经处理了limit
            statistics = history_manager.get_statistics()
            
            return {
                "success": True,
                "count": len(operations),
                "total": statistics.get("total", 0),
                "operations": operations,  # 不需要再次切片
                "statistics": statistics,
                "message": f"✅ 获取到 {len(operations)} 条操作记录"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ 获取历史记录失败: {str(e)}"
            }
    
    def clear_operation_history(self) -> Dict:
        """
        清空操作历史记录
        
        Returns:
            清空结果
        """
        try:
            history_manager = OperationHistoryManager()
            
            # 获取清空前的统计
            old_stats = history_manager.get_statistics()
            old_count = old_stats.get("total", 0)
            
            # 清空历史
            history_manager.clear()
            
            return {
                "success": True,
                "cleared_count": old_count,
                "message": f"✅ 已清空 {old_count} 条操作记录"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ 清空历史记录失败: {str(e)}"
            }


