#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iOS客户端 - 使用 facebook-wda（API风格和 uiautomator2 一样）

优势：
1. API和Android端(uiautomator2)几乎完全一致
2. 不需要Appium Server
3. 代码可以跨平台复用

用法:
    client = IOSClientWDA(device_id=None)
    await client.launch_app("com.example.app")
    await client.click("登录")  # 和Android端一样的调用方式！
"""
import asyncio
import sys
import time
from typing import Dict, Optional, List

from .ios_device_manager_wda import IOSDeviceManagerWDA


class IOSClientWDA:
    """
    iOS客户端 - 使用 facebook-wda
    
    API风格和MobileClient(Android)保持一致
    
    用法:
        client = IOSClientWDA(device_id=None)
        await client.launch_app("com.apple.Preferences")
        await client.click("通用")
    """
    
    def __init__(self, device_id: Optional[str] = None, lazy_connect: bool = False):
        """
        初始化iOS客户端
        
        Args:
            device_id: 设备UDID，None则自动选择第一个设备
            lazy_connect: 是否延迟连接（默认False）
        """
        self.device_manager = IOSDeviceManagerWDA()
        self._device_id = device_id
        self._lazy_connect = lazy_connect
        
        if not lazy_connect:
            self.wda = self.device_manager.connect(device_id)
        else:
            self.wda = None
        
        # 操作历史（用于录制）
        self.operation_history: List[Dict] = []
        
        # 缓存
        self._snapshot_cache = None
        self._cache_timestamp = 0
        self._cache_ttl = 1  # 缓存1秒
    
    def _ensure_connected(self):
        """确保设备已连接"""
        if self.wda is None:
            self.wda = self.device_manager.connect(self._device_id)
    
    async def snapshot(self, use_cache: bool = True) -> str:
        """
        获取页面XML结构
        
        Args:
            use_cache: 是否使用缓存
            
        Returns:
            页面结构字符串
        """
        self._ensure_connected()
        
        # 检查缓存
        if use_cache and self._snapshot_cache:
            current_time = time.time()
            if current_time - self._cache_timestamp < self._cache_ttl:
                return self._snapshot_cache
        
        try:
            # 获取页面源码
            source = self.wda.source()
            
            # 更新缓存
            self._snapshot_cache = source
            self._cache_timestamp = time.time()
            
            return source
        except Exception as e:
            raise RuntimeError(f"获取页面结构失败: {e}")
    
    async def click(self, element: str, ref: Optional[str] = None, verify: bool = True):
        """
        点击元素（API和Android端一致）
        
        Args:
            element: 元素描述（自然语言）
            ref: 元素定位器，支持多种格式：
                - text: 如 "登录"
                - accessibility_id: 如 "login_button"
                - xpath: 如 "//XCUIElementTypeButton[@name='登录']"
                - bounds: 如 "[100,200][300,400]" 或坐标 (x, y)
            verify: 是否验证点击成功
            
        Returns:
            操作结果
        """
        self._ensure_connected()
        
        # 记录操作
        operation_record = {
            'action': 'click',
            'element': element,
            'ref': ref,
            'success': False,
        }
        self.operation_history.append(operation_record)
        
        try:
            if ref:
                # 根据ref类型执行点击
                if ref.startswith('//'):
                    # XPath
                    elem = self.wda(xpath=ref)
                elif ref.startswith('[') and '][' in ref:
                    # bounds坐标 "[x1,y1][x2,y2]"
                    x, y = self._parse_bounds_coords(ref)
                    self.wda.click(x, y)
                    print(f"  ✅ 坐标点击成功: ({x}, {y})", file=sys.stderr)
                    operation_record['success'] = True
                    return {"success": True, "ref": ref}
                elif ',' in ref and ref.replace(',', '').replace(' ', '').isdigit():
                    # 直接坐标 "x,y"
                    parts = ref.split(',')
                    x, y = int(parts[0].strip()), int(parts[1].strip())
                    self.wda.click(x, y)
                    print(f"  ✅ 坐标点击成功: ({x}, {y})", file=sys.stderr)
                    operation_record['success'] = True
                    return {"success": True, "ref": ref}
                else:
                    # 默认尝试多种定位方式
                    elem = self._find_element(ref)
            else:
                # 使用元素描述进行定位
                elem = self._find_element(element)
            
            # 点击元素
            if elem and elem.exists:
                elem.click()
                print(f"  ✅ 点击成功: {ref or element}", file=sys.stderr)
                operation_record['success'] = True
                
                # 等待页面稳定
                await asyncio.sleep(0.3)
                
                return {"success": True, "ref": ref or element}
            else:
                raise ValueError(f"未找到元素: {ref or element}")
            
        except Exception as e:
            operation_record['error'] = str(e)
            print(f"  ❌ 点击失败: {e}", file=sys.stderr)
            return {"success": False, "reason": str(e)}
    
    def _find_element(self, locator: str):
        """
        尝试多种方式定位元素
        
        Args:
            locator: 定位器字符串
            
        Returns:
            元素对象或None
        """
        # 尝试顺序：name > label > text > accessibility_id
        strategies = [
            lambda: self.wda(name=locator),
            lambda: self.wda(label=locator),
            lambda: self.wda(text=locator),
            lambda: self.wda(nameContains=locator),
            lambda: self.wda(labelContains=locator),
        ]
        
        for strategy in strategies:
            try:
                elem = strategy()
                if elem.exists:
                    return elem
            except:
                continue
        
        return None
    
    async def type_text(self, element: str, text: str, ref: Optional[str] = None, verify: bool = True):
        """
        输入文本（API和Android端一致）
        
        Args:
            element: 元素描述
            text: 要输入的文本
            ref: 元素定位器
            verify: 是否验证输入成功
            
        Returns:
            操作结果
        """
        self._ensure_connected()
        
        # 记录操作
        operation_record = {
            'action': 'type',
            'element': element,
            'text': text,
            'ref': ref,
            'success': False,
        }
        self.operation_history.append(operation_record)
        
        try:
            if ref:
                if ref.startswith('//'):
                    elem = self.wda(xpath=ref)
                else:
                    elem = self._find_element(ref)
            else:
                # 查找第一个输入框
                elem = self.wda(className='XCUIElementTypeTextField')
                if not elem.exists:
                    elem = self.wda(className='XCUIElementTypeSecureTextField')
                if not elem.exists:
                    elem = self._find_element(element)
            
            if elem and elem.exists:
                elem.clear_text()
                elem.set_text(text)
                print(f"  ✅ 输入成功: {text}", file=sys.stderr)
                operation_record['success'] = True
                return {"success": True, "ref": ref or element}
            else:
                raise ValueError(f"未找到输入框: {ref or element}")
            
        except Exception as e:
            operation_record['error'] = str(e)
            print(f"  ❌ 输入失败: {e}", file=sys.stderr)
            return {"success": False, "reason": str(e)}
    
    async def swipe(self, direction: str, distance: int = 500, verify: bool = True):
        """
        滑动操作
        
        Args:
            direction: 滑动方向 ('up', 'down', 'left', 'right')
            distance: 滑动距离（像素）
            verify: 是否验证滑动成功
            
        Returns:
            操作结果
        """
        self._ensure_connected()
        
        try:
            # 获取屏幕尺寸
            window = self.wda.window_size()
            width = window.width
            height = window.height
            
            # 计算滑动坐标
            center_x = width // 2
            center_y = height // 2
            
            direction_map = {
                'up': (center_x, int(height * 0.8), center_x, int(height * 0.2)),
                'down': (center_x, int(height * 0.2), center_x, int(height * 0.8)),
                'left': (int(width * 0.8), center_y, int(width * 0.2), center_y),
                'right': (int(width * 0.2), center_y, int(width * 0.8), center_y),
            }
            
            if direction not in direction_map:
                return {"success": False, "reason": f"不支持的滑动方向: {direction}"}
            
            x1, y1, x2, y2 = direction_map[direction]
            
            print(f"  📍 滑动方向: {direction}, 坐标: ({x1}, {y1}) -> ({x2}, {y2})", file=sys.stderr)
            self.wda.swipe(x1, y1, x2, y2, duration=0.5)
            
            print(f"  ✅ 滑动成功: {direction}", file=sys.stderr)
            return {"success": True, "direction": direction}
            
        except Exception as e:
            print(f"  ❌ 滑动失败: {e}", file=sys.stderr)
            return {"success": False, "reason": str(e)}
    
    async def launch_app(self, bundle_id: str, wait_time: int = 3):
        """
        启动应用
        
        Args:
            bundle_id: 应用Bundle ID，如 'com.apple.Preferences'
            wait_time: 等待时间（秒）
            
        Returns:
            操作结果
        """
        self._ensure_connected()
        
        try:
            print(f"  📱 启动App: {bundle_id}", file=sys.stderr)
            
            # 使用 wda 启动应用
            self.wda.session().app_activate(bundle_id)
            
            # 等待应用启动
            await asyncio.sleep(wait_time)
            
            # 验证是否启动成功
            current = await self.get_current_package()
            if current == bundle_id:
                print(f"  ✅ App启动成功: {bundle_id}", file=sys.stderr)
                return {"success": True, "package": bundle_id}
            else:
                print(f"  ⚠️  App可能未启动成功，当前App: {current}", file=sys.stderr)
                return {"success": True, "package": bundle_id, "warning": f"当前App: {current}"}
            
        except Exception as e:
            print(f"  ❌ App启动失败: {e}", file=sys.stderr)
            return {"success": False, "reason": str(e)}
    
    async def stop_app(self, bundle_id: str):
        """
        停止应用
        
        Args:
            bundle_id: 应用Bundle ID
            
        Returns:
            操作结果
        """
        self._ensure_connected()
        
        try:
            print(f"  📱 停止App: {bundle_id}", file=sys.stderr)
            self.wda.session().app_terminate(bundle_id)
            print(f"  ✅ App已停止: {bundle_id}", file=sys.stderr)
            return {"success": True}
        except Exception as e:
            print(f"  ❌ App停止失败: {e}", file=sys.stderr)
            return {"success": False, "reason": str(e)}
    
    async def get_current_package(self) -> Optional[str]:
        """获取当前前台应用的Bundle ID"""
        self._ensure_connected()
        
        try:
            app_info = self.wda.session().app_current()
            return app_info.get('bundleId')
        except:
            return None
    
    async def press_key(self, key: str, verify: bool = True):
        """
        按键盘按键
        
        Args:
            key: 按键名称，支持：
                - "enter" / "回车" - Enter键
                - "back" / "返回" - 返回（在iOS上是导航返回）
                - "home" - Home键
            verify: 是否验证按键效果
        
        Returns:
            操作结果
        """
        self._ensure_connected()
        
        try:
            key_lower = key.lower()
            
            if key_lower in ['enter', '回车', 'return']:
                # 发送回车键
                self.wda(className='XCUIElementTypeKeyboard').buttons['return'].click()
                print(f"  ✅ 按键成功: Enter", file=sys.stderr)
            elif key_lower in ['back', '返回']:
                # iOS没有真正的返回键，尝试点击导航栏的返回按钮
                back_buttons = [
                    self.wda(name='返回'),
                    self.wda(name='Back'),
                    self.wda(label='返回'),
                    self.wda(label='Back'),
                ]
                clicked = False
                for btn in back_buttons:
                    if btn.exists:
                        btn.click()
                        clicked = True
                        break
                
                if clicked:
                    print(f"  ✅ 返回按钮点击成功", file=sys.stderr)
                else:
                    # 如果没有返回按钮，尝试从左边缘滑动
                    window = self.wda.window_size()
                    self.wda.swipe(0, window.height // 2, window.width // 2, window.height // 2)
                    print(f"  ✅ 边缘滑动返回成功", file=sys.stderr)
            elif key_lower == 'home':
                # 按Home键
                self.wda.home()
                print(f"  ✅ 按键成功: Home", file=sys.stderr)
            else:
                return {"success": False, "reason": f"不支持的按键: {key}"}
            
            return {"success": True, "key": key, "verified": False}
            
        except Exception as e:
            print(f"  ❌ 按键失败: {e}", file=sys.stderr)
            return {"success": False, "reason": str(e)}
    
    async def take_screenshot(self, filename: Optional[str] = None) -> str:
        """
        截图
        
        Args:
            filename: 保存的文件名（可选）
            
        Returns:
            截图文件路径
        """
        self._ensure_connected()
        
        import os
        from datetime import datetime
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ios_screenshot_{timestamp}.png"
        
        # 确保截图目录存在
        screenshots_dir = os.path.join(os.getcwd(), 'screenshots')
        os.makedirs(screenshots_dir, exist_ok=True)
        
        filepath = os.path.join(screenshots_dir, filename)
        
        try:
            # 使用 wda 截图
            self.wda.screenshot(filepath)
            print(f"  📸 截图已保存: {filepath}", file=sys.stderr)
            return filepath
        except Exception as e:
            print(f"  ❌ 截图失败: {e}", file=sys.stderr)
            raise
    
    def _parse_bounds_coords(self, bounds_str: str) -> tuple:
        """
        解析bounds字符串，返回中心点坐标
        
        Args:
            bounds_str: 格式如 "[100,200][300,400]"
            
        Returns:
            (x, y) 中心点坐标
        """
        import re
        match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
        if match:
            x1, y1, x2, y2 = map(int, match.groups())
            return ((x1 + x2) // 2, (y1 + y2) // 2)
        return (0, 0)
    
    def get_screen_size(self) -> tuple:
        """获取屏幕尺寸"""
        self._ensure_connected()
        
        window = self.wda.window_size()
        return (window.width, window.height)
    
    def list_elements(self) -> List[Dict]:
        """
        列出所有可交互元素（类似Android的mobile_list_elements）
        
        Returns:
            元素列表
        """
        self._ensure_connected()
        
        elements = []
        
        try:
            # 获取页面源码并解析
            source = self.wda.source(format='json')
            
            def extract_elements(node, depth=0):
                """递归提取元素"""
                if not isinstance(node, dict):
                    return
                
                elem_type = node.get('type', '')
                name = node.get('name', '')
                label = node.get('label', '')
                value = node.get('value', '')
                rect = node.get('rect', {})
                enabled = node.get('enabled', True)
                
                # 只收集可交互的元素
                interactable_types = [
                    'XCUIElementTypeButton',
                    'XCUIElementTypeTextField',
                    'XCUIElementTypeSecureTextField',
                    'XCUIElementTypeTextView',
                    'XCUIElementTypeSwitch',
                    'XCUIElementTypeSlider',
                    'XCUIElementTypeLink',
                    'XCUIElementTypeCell',
                    'XCUIElementTypeStaticText',
                ]
                
                if elem_type in interactable_types and enabled:
                    elements.append({
                        'type': elem_type,
                        'name': name,
                        'label': label,
                        'value': value,
                        'bounds': f"[{rect.get('x', 0)},{rect.get('y', 0)}][{rect.get('x', 0) + rect.get('width', 0)},{rect.get('y', 0) + rect.get('height', 0)}]",
                        'enabled': enabled,
                    })
                
                # 递归处理子元素
                for child in node.get('children', []):
                    extract_elements(child, depth + 1)
            
            extract_elements(source)
            
        except Exception as e:
            print(f"  ⚠️  获取元素列表失败: {e}", file=sys.stderr)
        
        return elements












