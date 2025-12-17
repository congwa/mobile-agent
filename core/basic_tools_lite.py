#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精简版基础工具 - 纯 MCP，依赖 Cursor 视觉能力

特点：
- 不需要 AI 密钥
- 核心功能精简
- 保留 pytest 脚本生成
- 支持操作历史记录
"""

import asyncio
import time
import re
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class BasicMobileToolsLite:
    """精简版移动端工具"""
    
    def __init__(self, mobile_client):
        self.client = mobile_client
        
        # 截图目录
        project_root = Path(__file__).parent.parent
        self.screenshot_dir = project_root / "screenshots"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        # 操作历史（用于生成 pytest 脚本）
        self.operation_history: List[Dict] = []
    
    def _is_ios(self) -> bool:
        """判断当前是否为 iOS 平台"""
        return getattr(self.client, 'platform', 'android') == 'ios'
    
    def _get_ios_client(self):
        """获取 iOS 客户端"""
        if hasattr(self.client, '_ios_client') and self.client._ios_client:
            return self.client._ios_client
        if hasattr(self.client, 'wda') and self.client.wda:
            return self.client.wda
        return None
    
    def _record_operation(self, action: str, **kwargs):
        """记录操作到历史"""
        record = {
            'action': action,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        self.operation_history.append(record)
    
    # ==================== 截图 ====================
    
    def take_screenshot(self, description: str = "") -> Dict:
        """截图（核心功能）- 返回屏幕尺寸帮助计算坐标"""
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            platform = "ios" if self._is_ios() else "android"
            
            if description:
                safe_desc = re.sub(r'[^\w\s-]', '', description).strip().replace(' ', '_')
                filename = f"screenshot_{platform}_{safe_desc}_{timestamp}.png"
            else:
                filename = f"screenshot_{platform}_{timestamp}.png"
            
            screenshot_path = self.screenshot_dir / filename
            
            # 获取屏幕尺寸
            width, height = 0, 0
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    ios_client.wda.screenshot(str(screenshot_path))
                    size = ios_client.wda.window_size()
                    width, height = size[0], size[1]
                else:
                    return {"success": False, "message": "❌ iOS 客户端未初始化"}
            else:
                self.client.u2.screenshot(str(screenshot_path))
                info = self.client.u2.info
                width = info.get('displayWidth', 0)
                height = info.get('displayHeight', 0)
            
            return {
                "success": True,
                "screenshot_path": str(screenshot_path),
                "screen_width": width,
                "screen_height": height,
                "message": f"📸 截图已保存: {screenshot_path}\n"
                          f"📐 屏幕尺寸: {width}x{height}\n"
                          f"💡 Cursor 分析图片后，返回的坐标可直接用于 mobile_click_at_coords"
            }
        except Exception as e:
            return {"success": False, "message": f"❌ 截图失败: {e}"}
    
    def get_screen_size(self) -> Dict:
        """获取屏幕尺寸"""
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    size = ios_client.wda.window_size()
                    return {
                        "success": True,
                        "width": size[0],
                        "height": size[1],
                        "size": f"{size[0]}x{size[1]}"
                    }
            else:
                info = self.client.u2.info
                width = info.get('displayWidth', 0)
                height = info.get('displayHeight', 0)
                return {
                    "success": True,
                    "width": width,
                    "height": height,
                    "size": f"{width}x{height}"
                }
        except Exception as e:
            return {"success": False, "message": f"❌ 获取屏幕尺寸失败: {e}"}
    
    # ==================== 点击操作 ====================
    
    def click_at_coords(self, x: int, y: int) -> Dict:
        """点击坐标（核心功能）"""
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    ios_client.wda.click(x, y)
                else:
                    return {"success": False, "message": "❌ iOS 客户端未初始化"}
            else:
                self.client.u2.click(x, y)
            
            time.sleep(0.3)
            
            # 记录操作
            self._record_operation('click', x=x, y=y, ref=f"coords_{x}_{y}")
            
            return {
                "success": True,
                "message": f"✅ 点击成功: ({x}, {y})"
            }
        except Exception as e:
            return {"success": False, "message": f"❌ 点击失败: {e}"}
    
    def click_by_text(self, text: str, timeout: float = 3.0) -> Dict:
        """通过文本点击 - 先查 XML 树，再精准匹配"""
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    elem = ios_client.wda(name=text)
                    if not elem.exists:
                        elem = ios_client.wda(label=text)
                    if elem.exists:
                        elem.click()
                        time.sleep(0.3)
                        self._record_operation('click', element=text, ref=text)
                        return {"success": True, "message": f"✅ 点击成功: '{text}'"}
                    return {"success": False, "message": f"❌ 文本不存在: {text}"}
            else:
                # 🔍 先查 XML 树，找到元素及其属性
                found_elem = self._find_element_in_tree(text)
                
                if found_elem:
                    attr_type = found_elem['attr_type']
                    attr_value = found_elem['attr_value']
                    bounds = found_elem.get('bounds')
                    
                    # 根据找到的属性类型，使用对应的选择器
                    if attr_type == 'text':
                        elem = self.client.u2(text=attr_value)
                    elif attr_type == 'textContains':
                        elem = self.client.u2(textContains=attr_value)
                    elif attr_type == 'description':
                        elem = self.client.u2(description=attr_value)
                    elif attr_type == 'descriptionContains':
                        elem = self.client.u2(descriptionContains=attr_value)
                    else:
                        elem = None
                    
                    if elem and elem.exists(timeout=1):
                        elem.click()
                        time.sleep(0.3)
                        self._record_operation('click', element=text, ref=f"{attr_type}:{attr_value}")
                        return {"success": True, "message": f"✅ 点击成功({attr_type}): '{text}'"}
                    
                    # 如果选择器失败，用坐标兜底
                    if bounds:
                        x = (bounds[0] + bounds[2]) // 2
                        y = (bounds[1] + bounds[3]) // 2
                        self.client.u2.click(x, y)
                        time.sleep(0.3)
                        self._record_operation('click', element=text, x=x, y=y, ref=f"coords:{x},{y}")
                        return {"success": True, "message": f"✅ 点击成功(坐标兜底): '{text}' @ ({x},{y})"}
                
                return {"success": False, "message": f"❌ 文本不存在: {text}"}
        except Exception as e:
            return {"success": False, "message": f"❌ 点击失败: {e}"}
    
    def _find_element_in_tree(self, text: str) -> Optional[Dict]:
        """在 XML 树中查找包含指定文本的元素"""
        try:
            xml = self.client.u2.dump_hierarchy()
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml)
            
            for elem in root.iter():
                elem_text = elem.attrib.get('text', '')
                elem_desc = elem.attrib.get('content-desc', '')
                bounds_str = elem.attrib.get('bounds', '')
                
                # 解析 bounds
                bounds = None
                if bounds_str:
                    import re
                    match = re.findall(r'\d+', bounds_str)
                    if len(match) == 4:
                        bounds = [int(x) for x in match]
                
                # 精确匹配 text
                if elem_text == text:
                    return {'attr_type': 'text', 'attr_value': text, 'bounds': bounds}
                
                # 精确匹配 content-desc
                if elem_desc == text:
                    return {'attr_type': 'description', 'attr_value': text, 'bounds': bounds}
                
                # 模糊匹配 text
                if text in elem_text:
                    return {'attr_type': 'textContains', 'attr_value': text, 'bounds': bounds}
                
                # 模糊匹配 content-desc
                if text in elem_desc:
                    return {'attr_type': 'descriptionContains', 'attr_value': text, 'bounds': bounds}
            
            return None
        except Exception:
            return None
    
    def click_by_id(self, resource_id: str) -> Dict:
        """通过 resource-id 点击"""
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    elem = ios_client.wda(id=resource_id)
                    if not elem.exists:
                        elem = ios_client.wda(name=resource_id)
                    if elem.exists:
                        elem.click()
                        time.sleep(0.3)
                        self._record_operation('click', element=resource_id, ref=resource_id)
                        return {"success": True, "message": f"✅ 点击成功: {resource_id}"}
                    return {"success": False, "message": f"❌ 元素不存在: {resource_id}"}
            else:
                elem = self.client.u2(resourceId=resource_id)
                if elem.exists(timeout=0.5):
                    elem.click()
                    time.sleep(0.3)
                    self._record_operation('click', element=resource_id, ref=resource_id)
                    return {"success": True, "message": f"✅ 点击成功: {resource_id}"}
                return {"success": False, "message": f"❌ 元素不存在: {resource_id}"}
        except Exception as e:
            return {"success": False, "message": f"❌ 点击失败: {e}"}
    
    # ==================== 输入操作 ====================
    
    def input_text_by_id(self, resource_id: str, text: str) -> Dict:
        """通过 resource-id 输入文本"""
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    elem = ios_client.wda(id=resource_id)
                    if not elem.exists:
                        elem = ios_client.wda(name=resource_id)
                    if elem.exists:
                        elem.set_text(text)
                        time.sleep(0.3)
                        self._record_operation('input', element=resource_id, ref=resource_id, text=text)
                        return {"success": True, "message": f"✅ 输入成功: '{text}'"}
                    return {"success": False, "message": f"❌ 输入框不存在: {resource_id}"}
            else:
                elem = self.client.u2(resourceId=resource_id)
                if elem.exists(timeout=0.5):
                    elem.set_text(text)
                    time.sleep(0.3)
                    self._record_operation('input', element=resource_id, ref=resource_id, text=text)
                    return {"success": True, "message": f"✅ 输入成功: '{text}'"}
                return {"success": False, "message": f"❌ 输入框不存在: {resource_id}"}
        except Exception as e:
            return {"success": False, "message": f"❌ 输入失败: {e}"}
    
    def input_at_coords(self, x: int, y: int, text: str) -> Dict:
        """点击坐标后输入文本（适合游戏）"""
        try:
            # 先点击聚焦
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    ios_client.wda.click(x, y)
            else:
                self.client.u2.click(x, y)
            
            time.sleep(0.3)
            
            # 输入文本
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    ios_client.wda.send_keys(text)
            else:
                self.client.u2.send_keys(text)
            
            time.sleep(0.3)
            
            self._record_operation('input', x=x, y=y, ref=f"coords_{x}_{y}", text=text)
            
            return {"success": True, "message": f"✅ 输入成功: ({x}, {y}) -> '{text}'"}
        except Exception as e:
            return {"success": False, "message": f"❌ 输入失败: {e}"}
    
    # ==================== 导航操作 ====================
    
    async def swipe(self, direction: str) -> Dict:
        """滑动屏幕"""
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    size = ios_client.wda.window_size()
                    width, height = size[0], size[1]
                else:
                    return {"success": False, "message": "❌ iOS 客户端未初始化"}
            else:
                width, height = self.client.u2.window_size()
            
            center_x, center_y = width // 2, height // 2
            
            swipe_map = {
                'up': (center_x, int(height * 0.8), center_x, int(height * 0.2)),
                'down': (center_x, int(height * 0.2), center_x, int(height * 0.8)),
                'left': (int(width * 0.8), center_y, int(width * 0.2), center_y),
                'right': (int(width * 0.2), center_y, int(width * 0.8), center_y),
            }
            
            if direction not in swipe_map:
                return {"success": False, "message": f"❌ 不支持的方向: {direction}"}
            
            x1, y1, x2, y2 = swipe_map[direction]
            
            if self._is_ios():
                ios_client.wda.swipe(x1, y1, x2, y2)
            else:
                self.client.u2.swipe(x1, y1, x2, y2, duration=0.5)
            
            self._record_operation('swipe', direction=direction)
            
            return {"success": True, "message": f"✅ 滑动成功: {direction}"}
        except Exception as e:
            return {"success": False, "message": f"❌ 滑动失败: {e}"}
    
    async def press_key(self, key: str) -> Dict:
        """按键操作"""
        key_map = {
            'enter': 66, '回车': 66,
            'search': 84, '搜索': 84,
            'back': 4, '返回': 4,
            'home': 3,
        }
        
        try:
            if self._is_ios():
                ios_key_map = {'enter': 'return', 'back': 'back', 'home': 'home'}
                ios_key = ios_key_map.get(key.lower())
                if ios_key:
                    ios_client = self._get_ios_client()
                    if ios_client and hasattr(ios_client, 'wda'):
                        # iOS 使用不同的按键方式
                        if ios_key == 'return':
                            ios_client.wda.send_keys('\n')
                        elif ios_key == 'home':
                            ios_client.wda.home()
                        return {"success": True, "message": f"✅ 按键成功: {key}"}
                return {"success": False, "message": f"❌ iOS 不支持: {key}"}
            else:
                keycode = key_map.get(key.lower())
                if keycode:
                    self.client.u2.shell(f'input keyevent {keycode}')
                    self._record_operation('press_key', key=key)
                    return {"success": True, "message": f"✅ 按键成功: {key}"}
                return {"success": False, "message": f"❌ 不支持的按键: {key}"}
        except Exception as e:
            return {"success": False, "message": f"❌ 按键失败: {e}"}
    
    def wait(self, seconds: float) -> Dict:
        """等待指定时间"""
        time.sleep(seconds)
        return {"success": True, "message": f"✅ 已等待 {seconds} 秒"}
    
    # ==================== 应用管理 ====================
    
    async def launch_app(self, package_name: str) -> Dict:
        """启动应用"""
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    ios_client.wda.app_activate(package_name)
            else:
                self.client.u2.app_start(package_name)
            
            await asyncio.sleep(2)
            
            self._record_operation('launch_app', package_name=package_name)
            
            return {
                "success": True,
                "message": f"✅ 已启动: {package_name}\n💡 建议等待 2-3 秒让页面加载"
            }
        except Exception as e:
            return {"success": False, "message": f"❌ 启动失败: {e}"}
    
    def terminate_app(self, package_name: str) -> Dict:
        """终止应用"""
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    ios_client.wda.app_terminate(package_name)
            else:
                self.client.u2.app_stop(package_name)
            return {"success": True, "message": f"✅ 已终止: {package_name}"}
        except Exception as e:
            return {"success": False, "message": f"❌ 终止失败: {e}"}
    
    def list_apps(self, filter_keyword: str = "") -> Dict:
        """列出已安装应用"""
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    # iOS 暂不支持列出所有应用
                    return {
                        "success": True,
                        "apps": [],
                        "count": 0,
                        "message": "💡 iOS 暂不支持列出所有应用，请直接使用 bundle_id 启动"
                    }
            else:
                apps = self.client.u2.app_list()
                if filter_keyword:
                    apps = [app for app in apps if filter_keyword.lower() in app.lower()]
                return {
                    "success": True,
                    "apps": apps[:50],  # 限制返回数量
                    "count": len(apps)
                }
        except Exception as e:
            return {"success": False, "message": f"❌ 获取应用列表失败: {e}"}
    
    # ==================== 设备管理 ====================
    
    def list_devices(self) -> Dict:
        """列出已连接设备"""
        try:
            platform = "ios" if self._is_ios() else "android"
            
            if platform == "ios":
                from .ios_device_manager_wda import IOSDeviceManagerWDA
                manager = IOSDeviceManagerWDA()
                devices = manager.list_devices()
            else:
                from .device_manager import DeviceManager
                manager = DeviceManager()
                devices = manager.list_devices()
            
            return {
                "success": True,
                "platform": platform,
                "devices": devices,
                "count": len(devices)
            }
        except Exception as e:
            return {"success": False, "message": f"❌ 获取设备列表失败: {e}"}
    
    def check_connection(self) -> Dict:
        """检查设备连接"""
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    return {"success": True, "connected": True, "platform": "ios"}
                return {"success": False, "connected": False, "message": "❌ iOS 未连接"}
            else:
                info = self.client.u2.device_info
                return {
                    "success": True,
                    "connected": True,
                    "platform": "android",
                    "device": f"{info.get('brand', '')} {info.get('model', '')}"
                }
        except Exception as e:
            return {"success": False, "connected": False, "message": f"❌ 连接检查失败: {e}"}
    
    # ==================== 辅助工具 ====================
    
    def list_elements(self) -> List[Dict]:
        """列出页面元素"""
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'list_elements'):
                    return ios_client.list_elements()
                return [{"error": "iOS 暂不支持元素列表，建议使用截图"}]
            else:
                xml_string = self.client.u2.dump_hierarchy()
                elements = self.client.xml_parser.parse(xml_string)
                
                result = []
                for elem in elements:
                    if elem.get('clickable') or elem.get('focusable'):
                        result.append({
                            'resource_id': elem.get('resource_id', ''),
                            'text': elem.get('text', ''),
                            'content_desc': elem.get('content_desc', ''),
                            'bounds': elem.get('bounds', ''),
                            'clickable': elem.get('clickable', False)
                        })
                return result
        except Exception as e:
            return [{"error": f"获取元素失败: {e}"}]
    
    def assert_text(self, text: str) -> Dict:
        """检查页面是否包含文本"""
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    exists = ios_client.wda(name=text).exists or ios_client.wda(label=text).exists
                else:
                    exists = False
            else:
                exists = self.client.u2(text=text).exists()
            
            return {
                "success": True,
                "found": exists,
                "text": text,
                "message": f"✅ 文本'{text}' {'存在' if exists else '不存在'}"
            }
        except Exception as e:
            return {"success": False, "message": f"❌ 断言失败: {e}"}
    
    # ==================== 脚本生成 ====================
    
    def get_operation_history(self, limit: Optional[int] = None) -> Dict:
        """获取操作历史"""
        history = self.operation_history
        if limit:
            history = history[-limit:]
        return {
            "success": True,
            "count": len(history),
            "total": len(self.operation_history),
            "operations": history
        }
    
    def clear_operation_history(self) -> Dict:
        """清空操作历史"""
        count = len(self.operation_history)
        self.operation_history = []
        return {"success": True, "message": f"✅ 已清空 {count} 条记录"}
    
    def generate_test_script(self, test_name: str, package_name: str, filename: str) -> Dict:
        """生成 pytest 测试脚本（带智能等待和广告处理）"""
        if not self.operation_history:
            return {"success": False, "message": "❌ 没有操作历史，请先执行一些操作"}
        
        # 生成脚本
        safe_name = re.sub(r'[^\w\s-]', '', test_name).strip().replace(' ', '_')
        
        script_lines = [
            "#!/usr/bin/env python3",
            "# -*- coding: utf-8 -*-",
            f'"""',
            f"测试用例: {test_name}",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f'"""',
            "import time",
            "import uiautomator2 as u2",
            "",
            f'PACKAGE_NAME = "{package_name}"',
            "",
            "# === 配置（根据 App 情况调整）===",
            "LAUNCH_WAIT = 3        # 启动后等待时间（秒）",
            "CLOSE_AD_ON_LAUNCH = True  # 是否尝试关闭启动广告",
            "AD_CLOSE_KEYWORDS = ['关闭', '跳过', 'Skip', 'Close', '×', 'X', '我知道了', '稍后再说']",
            "",
            "",
            "def smart_wait(d, seconds=1):",
            '    """等待页面稳定"""',
            "    time.sleep(seconds)",
            "",
            "",
            "def close_ad_if_exists(d, quick=False):",
            '    """尝试关闭广告弹窗（quick=True 时只检查常见的）"""',
            "    keywords = AD_CLOSE_KEYWORDS[:3] if quick else AD_CLOSE_KEYWORDS",
            "    for keyword in keywords:",
            "        elem = d(textContains=keyword)",
            "        if elem.exists(timeout=0.3):  # 缩短超时",
            "            try:",
            "                elem.click()",
            "                print(f'  📢 关闭广告: {keyword}')",
            "                time.sleep(0.3)",
            "                return True",
            "            except:",
            "                pass",
            "    return False",
            "",
            "",
            "def safe_click(d, selector, timeout=3):",
            '    """安全点击（带等待）"""',
            "    try:",
            "        if selector.exists(timeout=timeout):",
            "            selector.click()",
            "            return True",
            "        return False",
            "    except Exception as e:",
            "        print(f'  ⚠️ 点击失败: {e}')",
            "        return False",
            "",
            "",
            "def test_main():",
            "    # 连接设备",
            "    d = u2.connect()",
            "    d.implicitly_wait(10)  # 设置全局等待",
            "    ",
            "    # 启动应用",
            f"    d.app_start(PACKAGE_NAME)",
            "    time.sleep(LAUNCH_WAIT)  # 等待启动（可调整）",
            "    ",
            "    # 尝试关闭启动广告（可选，根据 App 情况调整）",
            "    if CLOSE_AD_ON_LAUNCH:",
            "        close_ad_if_exists(d)",
            "    ",
        ]
        
        # 生成操作代码（跳过启动应用相关操作，因为脚本头部已处理）
        step_num = 0
        for op in self.operation_history:
            action = op.get('action')
            
            # 跳过 launch_app（脚本头部已经有 app_start）
            if action == 'launch_app':
                continue
            
            step_num += 1
            
            if action == 'click':
                ref = op.get('ref', '')
                element = op.get('element', '')
                has_coords = 'x' in op and 'y' in op
                
                # 优先级：ID > 文本 > 坐标
                if ref and (':id/' in ref or ref.startswith('com.')):
                    # 使用 resource-id
                    script_lines.append(f"    # 步骤{step_num}: 点击元素 {element or ref}")
                    script_lines.append(f"    safe_click(d, d(resourceId='{ref}'))")
                elif ref and not ref.startswith('coords_'):
                    # 使用文本
                    script_lines.append(f"    # 步骤{step_num}: 点击文本 '{ref}'")
                    script_lines.append(f"    safe_click(d, d(text='{ref}'))")
                elif has_coords:
                    # 坐标兜底
                    desc = f" ({element})" if element else ""
                    script_lines.append(f"    # 步骤{step_num}: 点击坐标{desc}")
                    script_lines.append(f"    d.click({op['x']}, {op['y']})")
                else:
                    continue  # 无效操作，跳过
                    
                script_lines.append("    time.sleep(0.5)  # 等待响应")
                script_lines.append("    ")
            
            elif action == 'input':
                text = op.get('text', '')
                if 'x' in op and 'y' in op:
                    script_lines.append(f"    # 步骤{step_num}: 点击坐标后输入")
                    script_lines.append(f"    d.click({op['x']}, {op['y']})")
                    script_lines.append(f"    time.sleep(0.3)")
                    script_lines.append(f"    d.send_keys('{text}')")
                elif 'ref' in op:
                    script_lines.append(f"    # 步骤{step_num}: 输入文本 '{text}'")
                    script_lines.append(f"    d(resourceId='{op['ref']}').set_text('{text}')")
                script_lines.append("    time.sleep(0.5)")
                script_lines.append("    ")
            
            elif action == 'swipe':
                direction = op.get('direction', 'up')
                script_lines.append(f"    # 步骤{step_num}: 滑动 {direction}")
                script_lines.append(f"    d.swipe_ext('{direction}')")
                script_lines.append("    time.sleep(0.5)")
                script_lines.append("    ")
            
            elif action == 'press_key':
                key = op.get('key', 'enter')
                script_lines.append(f"    # 步骤{step_num}: 按键 {key}")
                script_lines.append(f"    d.press('{key}')")
                script_lines.append("    time.sleep(0.5)")
                script_lines.append("    ")
        
        script_lines.extend([
            "    print('✅ 测试完成')",
            "",
            "",
            "if __name__ == '__main__':",
            "    test_main()",
        ])
        
        script = '\n'.join(script_lines)
        
        # 保存文件
        output_dir = Path("tests")
        output_dir.mkdir(exist_ok=True)
        
        if not filename.endswith('.py'):
            filename = f"{filename}.py"
        
        file_path = output_dir / filename
        file_path.write_text(script, encoding='utf-8')
        
        return {
            "success": True,
            "file_path": str(file_path),
            "message": f"✅ 脚本已生成: {file_path}",
            "operations_count": len(self.operation_history),
            "preview": script[:500] + "..."
        }

