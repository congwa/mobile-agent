#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""


功能：
1. 设备连接管理
2. 页面结构获取（snapshot）
3. 元素操作（click, type, swipe等）
4. App管理（launch, stop等）

用法:
    client = MobileClient(device_id=None)
    await client.launch_app("com.example.app")
    await client.click("登录按钮")
"""
import asyncio
import sys
import time
from typing import Dict, Optional, List

from .device_manager import DeviceManager
from ..utils.xml_parser import XMLParser
from ..utils.xml_formatter import XMLFormatter
from .utils.smart_wait import SmartWait
from .dynamic_config import DynamicConfig


class MobileClient:
    """
    用法:
        client = MobileClient(device_id=None, platform="android")
        await client.launch_app("com.example.app")
        await client.click("登录按钮")
    """
    
    def __init__(self, device_id: Optional[str] = None, platform: str = "android", lock_orientation: bool = True, lazy_connect: bool = False):
        """
        初始化移动端客户端
        
        Args:
            device_id: 设备ID，None则自动选择第一个设备
            platform: 平台类型 ("android" 或 "ios")
            lock_orientation: 是否锁定屏幕方向为竖屏（默认True，仅Android有效）
            lazy_connect: 是否延迟连接（默认False）。如果为True，则不立即连接设备
        """
        self.platform = platform
        self._device_id = device_id
        self._lazy_connect = lazy_connect
        
        if platform == "android":
            self.device_manager = DeviceManager(platform="android")
            if not lazy_connect:
                self.u2 = self.device_manager.connect(device_id)
            else:
                self.u2 = None
            self.driver = None  # iOS使用
            
            # 初始化智能等待工具
            if not lazy_connect:
                self.smart_wait = SmartWait(self)
            else:
                self.smart_wait = None
        elif platform == "ios":
            # 🍎 iOS 支持：使用 tidevice + facebook-wda
            from .ios_client_wda import IOSClientWDA
            self._ios_client = IOSClientWDA(device_id=device_id, lazy_connect=lazy_connect)
            self.device_manager = self._ios_client.device_manager
            self.wda = self._ios_client.wda if not lazy_connect else None
            self.driver = None
            self.u2 = None
        else:
            raise ValueError(f"不支持的平台: {platform}")
        
        self.xml_parser = XMLParser()
        self.xml_formatter = XMLFormatter()
        
        # 缓存
        self._snapshot_cache = None
        self._cache_timestamp = 0
        self._cache_ttl = 1  # 缓存1秒
        
        # 操作历史（用于录制）
        self.operation_history: List[Dict] = []
        
        # 🎯 锁定屏幕方向为竖屏（防止测试过程中屏幕旋转）
        if lock_orientation and platform == "android":
            self._lock_screen_orientation()
    
    def _lock_screen_orientation(self):
        """锁定屏幕方向为竖屏"""
        try:
            import subprocess
            device_id = self.device_manager.current_device_id
            
            # 先禁用自动旋转
            subprocess.run(
                ['adb', '-s', device_id, 'shell', 'settings', 'put', 'system', 'accelerometer_rotation', '0'],
                capture_output=True,
                timeout=5
            )
            
            # 强制设置为竖屏（0 = 竖屏）
            result = subprocess.run(
                ['adb', '-s', device_id, 'shell', 'settings', 'put', 'system', 'user_rotation', '0'],
                capture_output=True,
                timeout=5
            )
            
            # 等待旋转完成
            import time
            time.sleep(0.5)
            
            if result.returncode == 0:
                print(f"  🔒 已锁定屏幕方向为竖屏", file=sys.stderr)
            else:
                print(f"  ⚠️  锁定屏幕方向失败（可能设备不支持）", file=sys.stderr)
        except Exception as e:
            print(f"  ⚠️  锁定屏幕方向失败: {e}（可能设备不支持）", file=sys.stderr)
    
    def force_portrait(self):
        """强制旋转回竖屏（如果当前是横屏）"""
        try:
            import subprocess
            device_id = self.device_manager.current_device_id
            
            # 强制旋转回竖屏
            subprocess.run(
                ['adb', '-s', device_id, 'shell', 'settings', 'put', 'system', 'user_rotation', '0'],
                capture_output=True,
                timeout=5
            )
            
            import time
            time.sleep(0.5)
            print(f"  🔄 已强制旋转回竖屏", file=sys.stderr)
        except Exception as e:
            print(f"  ⚠️  强制旋转失败: {e}", file=sys.stderr)
    
    def unlock_screen_orientation(self):
        """解锁屏幕方向（允许自动旋转）"""
        try:
            import subprocess
            device_id = self.device_manager.current_device_id
            
            # 恢复自动旋转
            result = subprocess.run(
                ['adb', '-s', device_id, 'shell', 'settings', 'put', 'system', 'accelerometer_rotation', '1'],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                print(f"  🔓 已解锁屏幕方向（允许自动旋转）", file=sys.stderr)
            else:
                print(f"  ⚠️  解锁屏幕方向失败", file=sys.stderr)
        except Exception as e:
            print(f"  ⚠️  解锁屏幕方向失败: {e}", file=sys.stderr)
    
    async def snapshot(self, use_cache: bool = True) -> str:
        """
        获取页面XML结构（类似Web的snapshot）
        
        Args:
            use_cache: 是否使用缓存
            
        Returns:
            格式化后的页面结构字符串（AI可理解的格式）
        """
        import time
        
        # 检查缓存
        if use_cache and self._snapshot_cache:
            current_time = time.time()
            if current_time - self._cache_timestamp < self._cache_ttl:
                return self._snapshot_cache
        
        # iOS平台使用不同的实现
        if self.platform == "ios":
            if not self.driver:
                raise RuntimeError("iOS设备未连接")
            # 获取iOS页面源码
            xml_string = self.driver.page_source
            if not isinstance(xml_string, str):
                xml_string = str(xml_string)
            # iOS的XML格式可能不同，直接返回或简单格式化
            self._snapshot_cache = xml_string
            self._cache_timestamp = time.time()
            return xml_string
        
        # Android平台
        # 获取XML
        xml_string = self.u2.dump_hierarchy()
        
        # 确保xml_string是字符串类型
        if not isinstance(xml_string, str):
            xml_string = str(xml_string)
        
        # 解析XML
        elements = self.xml_parser.parse(xml_string)
        
        # 确保elements是列表类型
        if not isinstance(elements, list):
            raise ValueError(f"XML解析返回了非列表类型: {type(elements)}")
        
        # 格式化成AI可理解的格式
        formatted = self.xml_formatter.format(elements)
        
        # 更新缓存
        self._snapshot_cache = formatted
        self._cache_timestamp = time.time()
        
        return formatted
    
    async def click(self, element: str, ref: Optional[str] = None, verify: bool = True):
        """
        点击元素
        
        Args:
            element: 元素描述（自然语言）
            ref: 元素引用（resource-id或text），None则自动定位
            verify: 是否验证点击成功（检查页面变化）
            
        Returns:
            操作结果
        """
        # iOS平台使用不同的实现
        if self.platform == "ios":
            if not self.driver:
                return {"success": False, "reason": "iOS设备未连接"}
            return await self._ios_click(element, ref)
        
        # Android平台
        # 如果没有ref，需要先定位（由SmartLocator处理）
        if not ref:
            # 这里会被MobileSmartLocator调用
            raise ValueError("需要先通过SmartLocator定位元素")
        
        # 🎯 记录操作（在点击前记录，ref会在点击成功后更新）
        operation_record = {
            'action': 'click',
            'element': element,
            'ref': ref,
            'success': False,  # 初始状态
        }
        self.operation_history.append(operation_record)
        
        # 根据ref类型执行点击
        try:
            if ref.startswith('cursor_vision_'):
                # Cursor AI视觉识别返回的截图路径
                # 格式: cursor_vision_/path/to/screenshot.png
                screenshot_path = ref.replace('cursor_vision_', '')
                print(f"  ⚠️  检测到Cursor视觉识别标记，但坐标尚未提供", file=sys.stderr)
                print(f"  💡 请使用 mobile_analyze_screenshot 工具分析截图: {screenshot_path}", file=sys.stderr)
                raise ValueError(f"需要先使用Cursor AI分析截图获取坐标: {screenshot_path}")
            elif ref.startswith('vision_coord_'):
                # 视觉识别返回的坐标点
                parts = ref.replace('vision_coord_', '').split('_')
                if len(parts) >= 2:
                    x, y = int(parts[0]), int(parts[1])
                    self.u2.click(x, y)
                else:
                    raise ValueError(f"无效的坐标格式: {ref}")
            elif ref.startswith('com.') or ':' in ref:
                # resource-id定位
                try:
                    elem = self.u2(resourceId=ref)
                    if elem.exists(timeout=2):
                        elem.click()
                        print(f"  ✅ resource-id点击成功: {ref}", file=sys.stderr)
                    else:
                        raise ValueError(f"元素不存在: {ref}")
                except Exception as e:
                    print(f"  ❌ resource-id点击失败: {e}", file=sys.stderr)
                    raise ValueError(f"resource-id点击失败: {ref}, 错误: {e}")
            elif ref.startswith('[') and '][' in ref:
                # bounds坐标定位 "[x1,y1][x2,y2]"
                try:
                    x, y = self._parse_bounds_coords(ref)
                    print(f"  📍 使用bounds坐标点击: {ref} -> ({x}, {y})", file=sys.stderr)
                    self.u2.click(x, y)
                    print(f"  ✅ bounds坐标点击成功: ({x}, {y})", file=sys.stderr)
                except Exception as e:
                    print(f"  ❌ bounds坐标点击失败: {e}", file=sys.stderr)
                    raise ValueError(f"bounds坐标点击失败: {ref}, 错误: {e}")
            else:
                # ⚡ 优化：同时检查text和description，支持弹窗/对话框场景
                # 先快速检查元素是否存在（设置短超时）
                text_elem = self.u2(text=ref)
                desc_elem = self.u2(description=ref)
                
                # 使用exists()快速检查（默认0秒超时，立即返回）
                if text_elem.exists(timeout=0.5):
                    # text元素存在，直接点击
                    try:
                        text_elem.click()
                        print(f"  ✅ text点击成功: {ref}", file=sys.stderr)
                    except Exception as e:
                        print(f"  ❌ text点击失败: {e}", file=sys.stderr)
                        raise ValueError(f"text点击失败: {ref}, 错误: {e}")
                elif desc_elem.exists(timeout=0.5):
                    # description元素存在，直接点击
                    try:
                        desc_elem.click()
                        print(f"  ✅ description点击成功: {ref}", file=sys.stderr)
                    except Exception as e:
                        print(f"  ❌ description点击失败: {e}", file=sys.stderr)
                        raise ValueError(f"description点击失败: {ref}, 错误: {e}")
                else:
                    # 都不存在，尝试包含匹配
                    desc_contains_elem = self.u2(descriptionContains=ref)
                    if desc_contains_elem.exists(timeout=0.5):
                        try:
                            desc_contains_elem.click()
                            print(f"  ✅ descriptionContains点击成功: {ref}", file=sys.stderr)
                        except Exception as e:
                            print(f"  ❌ descriptionContains点击失败: {e}", file=sys.stderr)
                            raise ValueError(f"descriptionContains点击失败: {ref}, 错误: {e}")
                    else:
                        # 🎯 改进：尝试模糊匹配（忽略空格、括号）
                        ref_normalized = ref.replace(' ', '').replace('(', '').replace(')', '').replace('（', '').replace('）', '')
                        # 获取所有元素，手动匹配
                        xml_string = self.u2.dump_hierarchy()
                        elements = self.xml_parser.parse(xml_string)
                        for elem in elements:
                            elem_desc = elem.get('content_desc', '')
                            elem_text = elem.get('text', '')
                            elem_desc_normalized = elem_desc.replace(' ', '').replace('(', '').replace(')', '').replace('（', '').replace('）', '')
                            elem_text_normalized = elem_text.replace(' ', '').replace('(', '').replace(')', '').replace('（', '').replace('）', '')
                            
                            if (elem_desc_normalized and ref_normalized in elem_desc_normalized) or \
                               (elem_text_normalized and ref_normalized in elem_text_normalized):
                                # 找到匹配，使用bounds坐标点击
                                bounds = elem.get('bounds', '')
                                if bounds:
                                    x, y = self._parse_bounds_coords(bounds)
                                    self.u2.click(x, y)
                                    print(f"  ✅ 模糊匹配成功，点击坐标: ({x}, {y})", file=sys.stderr)
                                    # 🎯 修复：找到匹配后直接返回，避免继续执行后面的代码
                                    return {"success": True, "ref": ref}
                        else:
                            # 最后尝试text包含匹配
                            text_contains_elem = self.u2(textContains=ref)
                            if text_contains_elem.exists(timeout=0.5):
                                try:
                                    text_contains_elem.click()
                                    print(f"  ✅ textContains点击成功: {ref}", file=sys.stderr)
                                    return {"success": True, "ref": ref}
                                except Exception as e:
                                    print(f"  ❌ textContains点击失败: {e}", file=sys.stderr)
                                    raise ValueError(f"textContains点击失败: {ref}, 错误: {e}")
                            else:
                                # 🎯 弹窗场景：如果元素不存在，等待更长时间（可能弹窗还没出现）
                                # 重试机制：等待弹窗出现（最多等待3秒）
                                print(f"  ⚠️  元素'{ref}'未找到，等待弹窗/对话框出现...", file=sys.stderr)
                                found = False
                                for attempt in range(6):  # 6次尝试，每次0.5秒，总共3秒
                                    await asyncio.sleep(0.5)
                                    # 重新检查元素是否存在
                                    if text_elem.exists(timeout=0.1):
                                        text_elem.click()
                                        found = True
                                        print(f"  ✅ 弹窗出现，点击成功（等待{attempt * 0.5 + 0.5}秒）", file=sys.stderr)
                                        break
                                    elif desc_elem.exists(timeout=0.1):
                                        desc_elem.click()
                                        found = True
                                        print(f"  ✅ 弹窗出现，点击成功（等待{attempt * 0.5 + 0.5}秒）", file=sys.stderr)
                                        break
                                    elif desc_contains_elem.exists(timeout=0.1):
                                        desc_contains_elem.click()
                                        found = True
                                        print(f"  ✅ 弹窗出现，点击成功（等待{attempt * 0.5 + 0.5}秒）", file=sys.stderr)
                                        break
                                    elif text_contains_elem.exists(timeout=0.1):
                                        text_contains_elem.click()
                                        found = True
                                        print(f"  ✅ 弹窗出现，点击成功（等待{attempt * 0.5 + 0.5}秒）", file=sys.stderr)
                                        break
                                
                                if not found:
                                    # 🎯 定位失败，自动使用Cursor AI视觉识别（截图分析）
                                    print(f"  ⚠️  元素'{ref}'未找到，自动使用Cursor AI视觉识别（截图分析）...", file=sys.stderr)
                                    try:
                                        from .locator.cursor_vision_helper import CursorVisionHelper
                                        cursor_helper = CursorVisionHelper(self)
                                        # 🎯 传递 auto_analyze=True，自动创建请求文件并等待结果
                                        cursor_result = await cursor_helper.analyze_with_cursor(element, auto_analyze=True)
                                        
                                        if cursor_result and cursor_result.get('status') == 'completed':
                                            # ✅ Cursor AI分析完成，获取坐标
                                            coord = cursor_result.get('coordinate')
                                            if coord and 'x' in coord and 'y' in coord:
                                                x, y = coord['x'], coord['y']
                                                self.u2.click(x, y)
                                                print(f"  ✅ Cursor AI视觉识别成功，点击坐标: ({x}, {y})", file=sys.stderr)
                                                
                                                # 🎯 更新操作历史：记录视觉识别坐标
                                                vision_ref = f"vision_coord_{x}_{y}"
                                                if self.operation_history:
                                                    last_op = self.operation_history[-1]
                                                    if last_op.get('action') == 'click' and last_op.get('element') == element:
                                                        last_op['ref'] = vision_ref  # 更新为视觉识别坐标
                                                        last_op['success'] = True
                                                        last_op['method'] = 'vision_coord'
                                                
                                                return {"success": True, "ref": vision_ref}
                                        elif cursor_result and cursor_result.get('status') == 'timeout':
                                            # ⏸️ 超时，提示用户手动分析
                                            screenshot_path = cursor_result.get('screenshot_path')
                                            print(f"  ⏸️  等待超时，请手动分析截图: {screenshot_path}", file=sys.stderr)
                                            raise ValueError(f"Cursor AI分析超时，请手动分析截图: {screenshot_path}")
                                        else:
                                            # 其他情况，抛出异常
                                            screenshot_path = cursor_result.get('screenshot_path', 'unknown') if cursor_result else 'unknown'
                                            raise ValueError(f"Cursor AI分析失败: {screenshot_path}")
                                    except ValueError as ve:
                                        if "Cursor AI" in str(ve):
                                            raise ve
                                        print(f"  ⚠️  Cursor视觉识别失败: {ve}", file=sys.stderr)
                                    
                                    raise ValueError(f"无法找到元素: {ref}（已等待3秒，并尝试Cursor视觉识别，可能元素不存在）")
            
            # 验证点击（可选）
            page_changed = False
            if verify:
                # 获取点击前页面状态
                try:
                    initial_xml = self.u2.dump_hierarchy()
                    initial_length = len(initial_xml)
                    
                    # 等待页面变化
                    page_changed = await self._verify_page_change(initial_length, timeout=2.0)
                    
                    if not page_changed:
                        print(f"  ⚠️  点击后页面未变化，可能点击未生效", file=sys.stderr)
                except Exception as e:
                    print(f"  ⚠️  页面变化检测失败: {e}", file=sys.stderr)
            
            # 🎯 更新操作历史：记录实际使用的ref和成功状态
            if self.operation_history:
                last_op = self.operation_history[-1]
                if last_op.get('action') == 'click' and last_op.get('element') == element:
                    last_op['ref'] = ref  # 更新为实际使用的ref（可能是坐标）
                    last_op['success'] = True if not verify else page_changed
                    last_op['method'] = self._get_ref_method(ref)  # 记录定位方法
                    if verify:
                        last_op['verified'] = True
                        last_op['page_changed'] = page_changed
            
            result = {"success": True, "ref": ref}
            if verify:
                result['verified'] = True
                result['page_changed'] = page_changed
                if not page_changed:
                    result['warning'] = "点击命令执行但页面未变化，可能点击未生效"
            
            return result
            
        except Exception as e:
            # 🎯 更新操作历史：记录失败状态
            if self.operation_history:
                last_op = self.operation_history[-1]
                if last_op.get('action') == 'click' and last_op.get('element') == element:
                    last_op['success'] = False
                    last_op['error'] = str(e)
            
            # 🎯 修复：确保 ref 不为 None
            error_ref = ref if ref else "unknown"
            return {"success": False, "reason": str(e), "ref": error_ref}
    
    def _get_ref_method(self, ref: str) -> str:
        """获取ref的定位方法类型"""
        if ref.startswith('vision_coord_'):
            return 'vision_coord'
        elif ref.startswith('[') and '][' in ref:
            return 'bounds'
        elif ref.startswith('com.') or ':' in ref:
            return 'resource_id'
        else:
            return 'text_or_desc'
    
    async def type_text(self, element: str, text: str, ref: Optional[str] = None, verify: bool = True):
        """
        输入文本（支持智能验证）
        
        Args:
            element: 元素描述（自然语言）
            text: 要输入的文本
            ref: 元素引用，None则自动定位
            verify: 是否验证输入成功（检查文本是否真的输入）
            
        Returns:
            操作结果，包含：
            - success: 是否成功
            - ref: 使用的定位符
            - verified: 是否经过验证
            - input_verified: 输入是否被验证（仅 verify=True）
            - actual_text: 实际输入框中的文本（仅 verify=True）
        """
        # iOS平台使用不同的实现
        if self.platform == "ios":
            if not self.driver:
                return {"success": False, "reason": "iOS设备未连接"}
            return await self._ios_type_text(element, text, ref)
        
        # Android平台
        if not ref:
            raise ValueError("需要先通过SmartLocator定位元素")
        
        # 🎯 记录操作（在输入前记录，ref会在输入成功后更新）
        operation_record = {
            'action': 'type',
            'element': element,
            'text': text,
            'ref': ref,
            'success': False,  # 初始状态
        }
        self.operation_history.append(operation_record)
        
        try:
            if ref.startswith('com.') or ':' in ref:
                # resource-id定位
                try:
                    elem = self.u2(resourceId=ref)
                    if elem.exists(timeout=2):
                        elem.set_text(text)
                        print(f"  ✅ resource-id输入成功: {ref}", file=sys.stderr)
                    else:
                        raise ValueError(f"输入框不存在: {ref}")
                except Exception as e:
                    print(f"  ❌ resource-id输入失败: {e}", file=sys.stderr)
                    raise ValueError(f"resource-id输入失败: {ref}, 错误: {e}")
            elif ref.startswith('[') and '][' in ref:
                # bounds坐标定位 "[x1,y1][x2,y2]"
                try:
                    x, y = self._parse_bounds_coords(ref)
                    # 方法1: 先点击聚焦，然后使用set_text（推荐，支持中文）
                    self.u2.click(x, y)  # 先点击聚焦
                    await asyncio.sleep(0.3)
                    # 尝试使用textbox定位并set_text
                    try:
                        # 查找该位置的textbox元素
                        textbox = self.u2(className='android.widget.EditText')
                        if textbox.exists(timeout=1):
                            textbox.set_text(text)
                            print(f"  ✅ bounds坐标输入成功（使用textbox.set_text）: ({x}, {y})", file=sys.stderr)
                        else:
                            # 如果没有找到textbox，使用send_keys
                            self.u2.send_keys(text)
                            print(f"  ✅ bounds坐标输入成功（使用send_keys）: ({x}, {y})", file=sys.stderr)
                    except Exception:
                        # 如果set_text失败，使用send_keys
                        self.u2.send_keys(text)
                        print(f"  ✅ bounds坐标输入成功（使用send_keys）: ({x}, {y})", file=sys.stderr)
                except Exception as e:
                    print(f"  ❌ bounds坐标输入失败: {e}", file=sys.stderr)
                    raise ValueError(f"bounds坐标输入失败: {ref}, 错误: {e}")
            elif '[' in ref and ']' in ref and not ref.startswith('['):
                # class_name[index]格式，使用索引定位
                # 例如：EditText[0] 表示第一个EditText
                try:
                    import re
                    match = re.match(r'(.+)\[(\d+)\]', ref)
                    if match:
                        class_name = match.group(1)
                        index = int(match.group(2))
                        # 查找所有该类元素并点击第index个
                        elements = self.u2(className=class_name).all()
                        if elements and index < len(elements):
                            elements[index].click()
                            await asyncio.sleep(0.2)
                            self.u2.send_keys(text)
                            print(f"  ✅ class_name[index]输入成功: {class_name}[{index}]", file=sys.stderr)
                        else:
                            raise ValueError(f"无法找到{class_name}[{index}]（共找到{len(elements) if elements else 0}个元素）")
                    else:
                        raise ValueError(f"无效的ref格式: {ref}")
                except Exception as e:
                    print(f"  ❌ class_name[index]输入失败: {e}", file=sys.stderr)
                    raise ValueError(f"class_name[index]输入失败: {ref}, 错误: {e}")
            else:
                # text定位
                try:
                    elem = self.u2(text=ref)
                    if elem.exists(timeout=2):
                        elem.set_text(text)
                        print(f"  ✅ text输入成功: {ref}", file=sys.stderr)
                    else:
                        raise ValueError(f"输入框不存在: {ref}")
                except Exception as e:
                    print(f"  ❌ text输入失败: {e}", file=sys.stderr)
                    raise ValueError(f"text输入失败: {ref}, 错误: {e}")
            
            # 验证输入（可选）
            input_verified = False
            actual_text = None
            if verify:
                try:
                    await asyncio.sleep(0.2)  # 等待输入完成
                    
                    # 尝试获取输入框中的实际文本
                    if ref.startswith('com.') or ':' in ref:
                        # resource-id定位
                        elem = self.u2(resourceId=ref)
                        if elem.exists(timeout=1):
                            actual_text = elem.get_text()
                    elif ref.startswith('[') and '][' in ref:
                        # bounds坐标定位
                        textbox = self.u2(className='android.widget.EditText')
                        if textbox.exists(timeout=1):
                            actual_text = textbox.get_text()
                    else:
                        # text定位
                        elem = self.u2(text=ref)
                        if elem.exists(timeout=1):
                            actual_text = elem.get_text()
                    
                    # 验证输入的文本是否正确
                    if actual_text is not None:
                        # 注意：有些输入法可能会改变文本格式，所以做宽松匹配
                        if text.strip() in actual_text or actual_text in text.strip():
                            input_verified = True
                            print(f"  ✅ 输入验证成功: '{actual_text}'", file=sys.stderr)
                        else:
                            print(f"  ⚠️  输入验证失败: 期望'{text}', 实际'{actual_text}'", file=sys.stderr)
                    else:
                        print(f"  ⚠️  无法获取输入框文本进行验证", file=sys.stderr)
                except Exception as e:
                    print(f"  ⚠️  输入验证失败: {e}", file=sys.stderr)
            
            # 🎯 更新操作历史：记录实际使用的ref和成功状态
            if self.operation_history:
                last_op = self.operation_history[-1]
                if last_op.get('action') == 'type' and last_op.get('element') == element:
                    last_op['ref'] = ref  # 更新为实际使用的ref
                    last_op['success'] = True if not verify else input_verified
                    last_op['method'] = self._get_ref_method(ref)  # 记录定位方法
                    if verify:
                        last_op['verified'] = True
                        last_op['input_verified'] = input_verified
                        if actual_text:
                            last_op['actual_text'] = actual_text
            
            # 🎯 特殊处理：如果是搜索框，输入后自动按搜索键
            if '搜索' in element.lower() or 'search' in element.lower():
                print(f"  🔍 检测到搜索框，输入后按搜索键...", file=sys.stderr)
                await asyncio.sleep(0.3)  # 等待输入完成
                try:
                    # 尝试按搜索键（KEYCODE_SEARCH = 84）
                    self.u2.press_keycode(84)
                    print(f"  ✅ 已按搜索键", file=sys.stderr)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    # 如果KEYCODE_SEARCH不支持，尝试按Enter键
                    try:
                        self.u2.press("enter")
                        print(f"  ✅ 已按Enter键（搜索键不可用）", file=sys.stderr)
                        await asyncio.sleep(0.5)
                    except Exception as e2:
                        print(f"  ⚠️  无法按搜索键: {e2}", file=sys.stderr)
            
            result = {"success": True, "ref": ref}
            if verify:
                result['verified'] = True
                result['input_verified'] = input_verified
                if actual_text is not None:
                    result['actual_text'] = actual_text
                if not input_verified:
                    result['warning'] = "输入命令执行但无法验证文本是否正确输入"
            
            return result
            
        except Exception as e:
            # 🎯 更新操作历史：记录失败状态
            if self.operation_history:
                last_op = self.operation_history[-1]
                if last_op.get('action') == 'type' and last_op.get('element') == element:
                    last_op['success'] = False
                    last_op['error'] = str(e)
            
            # 🎯 修复：确保 ref 不为 None
            error_ref = ref if ref else "unknown"
            return {"success": False, "reason": str(e), "ref": error_ref}
    
    async def swipe(self, direction: str, distance: int = 500, verify: bool = True):
        """
        滑动操作（支持智能验证）
        
        Args:
            direction: 滑动方向 ('up', 'down', 'left', 'right')
            distance: 滑动距离（像素）
            verify: 是否验证滑动成功（检测页面内容变化）
            
        Returns:
            操作结果，包含：
            - success: 是否成功
            - direction: 滑动方向
            - verified: 是否经过验证
            - page_changed: 页面是否变化（仅 verify=True）
        """
        # iOS平台使用不同的实现
        if self.platform == "ios":
            if not self.driver:
                return {"success": False, "reason": "iOS设备未连接"}
            try:
                size = self.driver.get_window_size()
                width = size['width']
                height = size['height']
                
                if direction == 'up':
                    self.driver.swipe(width // 2, int(height * 0.8), width // 2, int(height * 0.2))
                elif direction == 'down':
                    self.driver.swipe(width // 2, int(height * 0.2), width // 2, int(height * 0.8))
                elif direction == 'left':
                    self.driver.swipe(int(width * 0.8), height // 2, int(width * 0.2), height // 2)
                elif direction == 'right':
                    self.driver.swipe(int(width * 0.2), height // 2, int(width * 0.8), height // 2)
                else:
                    return {"success": False, "reason": f"不支持的滑动方向: {direction}"}
                
                return {"success": True, "direction": direction}
            except Exception as e:
                return {"success": False, "reason": str(e)}
        
        # Android平台
        # 获取屏幕尺寸
        width, height = self.u2.window_size()
        
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
        
        try:
            # 验证滑动（可选）
            initial_xml = None
            initial_length = 0
            if verify:
                try:
                    initial_xml = self.u2.dump_hierarchy()
                    initial_length = len(initial_xml)
                except Exception as e:
                    print(f"  ⚠️  获取初始页面状态失败: {e}", file=sys.stderr)
            
            print(f"  📍 滑动方向: {direction}, 坐标: ({x1}, {y1}) -> ({x2}, {y2})", file=sys.stderr)
            self.u2.swipe(x1, y1, x2, y2, duration=0.5)
            
            # 验证滑动效果
            page_changed = False
            if verify and initial_xml is not None:
                # 等待页面内容变化
                page_changed = await self._verify_page_change(initial_length, timeout=1.5, change_threshold=0.03)
                
                if page_changed:
                    print(f"  ✅ 滑动成功，页面内容已变化: {direction}", file=sys.stderr)
                else:
                    print(f"  ⚠️  滑动命令执行但页面内容未变化（可能已到边界）: {direction}", file=sys.stderr)
            else:
                print(f"  ✅ 滑动成功: {direction}", file=sys.stderr)
            
            result = {"success": True, "direction": direction}
            if verify:
                result['verified'] = True
                result['page_changed'] = page_changed
                if not page_changed:
                    result['warning'] = "滑动命令执行但页面内容未变化，可能已到列表边界"
            
            return result
        except Exception as e:
            print(f"  ❌ 滑动失败: {e}", file=sys.stderr)
            return {"success": False, "reason": str(e)}
    
    async def launch_app(self, package_name: str, wait_time: int = 3, smart_wait: bool = True):
        """
        启动App（快速模式：最多等待3秒+截图验证）
        
        Args:
            package_name: App包名（Android）或Bundle ID（iOS），如 "com.example.app"
            wait_time: 等待App启动的时间（秒）- 默认3秒
            smart_wait: 是否启用智能等待（自动关闭广告、截图验证）- 仅Android
            
        Returns:
            操作结果（包含screenshot_path字段供AI验证）
        """
        try:
            # iOS平台使用不同的实现
            if self.platform == "ios":
                if not self.driver:
                    return {"success": False, "reason": "iOS设备未连接"}
                try:
                    print(f"  📱 启动iOS App: {package_name}", file=sys.stderr)
                    self.driver.activate_app(package_name)
                    await asyncio.sleep(wait_time)
                    
                    # 验证是否启动成功
                    current = await self.get_current_package()
                    if current == package_name:
                        print(f"  ✅ iOS App启动成功: {package_name}", file=sys.stderr)
                        return {"success": True, "package": package_name}
                    else:
                        print(f"  ⚠️  iOS App可能未启动成功，当前App: {current}，期望: {package_name}", file=sys.stderr)
                        return {"success": True, "package": package_name, "warning": f"当前App: {current}"}
                except Exception as e:
                    print(f"  ❌ iOS App启动异常: {e}", file=sys.stderr)
                    return {"success": False, "reason": str(e)}
            
            # Android平台
            # 🎯 优先使用智能启动（推荐）
            if smart_wait:
                from .smart_app_launcher import SmartAppLauncher
                launcher = SmartAppLauncher(self)
                # 优化：快速模式，最多3秒
                smart_wait_time = min(wait_time, 3)
                
                # 🎯 从环境变量读取是否自动关闭广告（默认True）
                import os
                auto_close_ads = os.environ.get('AUTO_CLOSE_ADS', 'true').lower() in ['true', '1', 'yes']
                
                result = await launcher.launch_with_smart_wait(
                    package_name,
                    max_wait=smart_wait_time,
                    auto_close_ads=auto_close_ads
                )
                
                # 打印截图路径（供Cursor AI查看验证）
                if result.get('screenshot_path'):
                    print(f"\n📸 启动截图已保存: {result['screenshot_path']}", file=sys.stderr)
                    print(f"💡 提示: 请查看截图确认App是否已正确进入主页", file=sys.stderr)
                
                return result
            
            # 传统方式（快速启动，不等待加载）
            print(f"  📱 启动App: {package_name}", file=sys.stderr)
            self.u2.app_start(package_name)
            
            # 等待App启动，并验证是否成功
            for i in range(wait_time):
                await asyncio.sleep(1)
                current = await self.get_current_package()
                if current == package_name:
                    print(f"  ✅ App启动成功: {package_name}（等待{i+1}秒）", file=sys.stderr)
                    return {"success": True, "package": package_name}
            
            # 如果等待后仍未启动，检查App是否安装
            current = await self.get_current_package()
            if current != package_name:
                print(f"  ⚠️  App可能未启动成功，当前App: {current}，期望: {package_name}", file=sys.stderr)
                # 🎯 检查App是否安装
                try:
                    app_info = self.u2.app_info(package_name)
                    if app_info:
                        # App已安装，但可能启动失败
                        return {"success": False, "reason": f"App启动失败，当前App: {current}，期望: {package_name}"}
                    else:
                        return {"success": False, "reason": f"App未安装: {package_name}"}
                except:
                    # 无法获取App信息，返回警告
                    return {"success": True, "package": package_name, "warning": f"当前App: {current}，无法确认是否启动成功"}
            
            return {"success": True, "package": package_name}
        except Exception as e:
            print(f"  ❌ App启动异常: {e}", file=sys.stderr)
            return {"success": False, "reason": str(e)}
    
    async def stop_app(self, package_name: str):
        """
        停止App
        
        Args:
            package_name: App包名（Android）或Bundle ID（iOS）
            
        Returns:
            操作结果
        """
        try:
            print(f"  📱 停止App: {package_name}", file=sys.stderr)
            
            # iOS平台使用不同的实现
            if self.platform == "ios":
                if not self.driver:
                    return {"success": False, "reason": "iOS设备未连接"}
                try:
                    self.driver.terminate_app(package_name)
                    print(f"  ✅ iOS App已停止: {package_name}", file=sys.stderr)
                    return {"success": True}
                except Exception as e:
                    print(f"  ❌ iOS App停止失败: {e}", file=sys.stderr)
                    return {"success": False, "reason": str(e)}
            
            # Android平台
            self.u2.app_stop(package_name)
            print(f"  ✅ App已停止: {package_name}", file=sys.stderr)
            return {"success": True}
        except Exception as e:
            print(f"  ❌ App停止失败: {e}", file=sys.stderr)
            return {"success": False, "reason": str(e)}
    
    async def get_current_package(self) -> Optional[str]:
        """
        获取当前App包名（Android）或Bundle ID（iOS）
        
        Returns:
            包名/Bundle ID或None
        """
        try:
            if self.platform == "ios":
                if not self.driver:
                    return None
                return self.driver.current_package
            else:
                info = self.u2.app_current()
                return info.get('package')
        except:
            return None
    
    async def press_key(self, key: str, verify: bool = True):
        """
        按键盘按键（支持智能验证）
        
        Args:
            key: 按键名称，支持：
                - "enter" / "回车" - Enter键
                - "search" / "搜索" - 搜索键
                - "back" / "返回" - 返回键
                - "home" - Home键
                - 或者直接使用keycode数字（如 66=Enter, 84=Search）
            verify: 是否验证按键效果（默认True）
                - True: 检测页面变化，确保按键真的生效
                - False: 快速模式，执行后立即返回（不保证效果）
        
        Returns:
            操作结果，包含：
            - success: 是否成功
            - key: 按键名称
            - keycode: 按键代码
            - verified: 是否经过验证
            - page_changed: 页面是否变化（仅 verify=True 时）
            - fallback_used: 是否使用了备选方案（仅搜索键）
        """
        # iOS平台使用不同的实现
        if self.platform == "ios":
            if not self.driver:
                return {"success": False, "reason": "iOS设备未连接"}
            try:
                # iOS按键映射（使用XCUITest的按键）
                ios_key_map = {
                    'enter': 'return',
                    '回车': 'return',
                    'back': 'back',
                    '返回': 'back',
                    'home': 'home',
                }
                
                key_lower = key.lower()
                if key_lower in ios_key_map:
                    ios_key = ios_key_map[key_lower]
                    # iOS使用execute_script发送按键
                    self.driver.execute_script("mobile: pressButton", {"name": ios_key})
                    print(f"  ✅ iOS按键成功: {key} ({ios_key})", file=sys.stderr)
                    return {"success": True, "key": key, "verified": False}
                else:
                    return {"success": False, "reason": f"iOS不支持的按键: {key}"}
            except Exception as e:
                print(f"  ❌ iOS按键失败: {e}", file=sys.stderr)
                return {"success": False, "reason": str(e)}
        
        # Android平台
        key_map = {
            'enter': 66,  # KEYCODE_ENTER
            '回车': 66,
            'search': 84,  # KEYCODE_SEARCH
            '搜索': 84,
            'back': 4,  # KEYCODE_BACK
            '返回': 4,
            'home': 3,  # KEYCODE_HOME
        }
        
        is_search_key = key.lower() in ['search', '搜索'] or key == '84'
        
        try:
            # 尝试解析为keycode数字
            if key.isdigit():
                keycode = int(key)
            elif key.lower() in key_map:
                keycode = key_map[key.lower()]
            else:
                # 尝试直接使用u2.press方法（支持字符串按键名）
                try:
                    if verify:
                        # 获取操作前页面状态
                        initial_xml = self.u2.dump_hierarchy()
                        initial_length = len(initial_xml)
                    
                    self.u2.press(key.lower())
                    print(f"  ✅ 按键成功: {key}", file=sys.stderr)
                    
                    if verify:
                        # 检测页面变化
                        page_changed = await self._verify_page_change(initial_length, timeout=2.0)
                        return {
                            "success": page_changed,
                            "key": key,
                            "verified": True,
                            "page_changed": page_changed,
                            "message": "按键成功且页面已变化" if page_changed else "⚠️ 按键命令执行成功但页面未变化"
                        }
                    else:
                        return {"success": True, "key": key, "verified": False}
                except:
                    return {"success": False, "reason": f"不支持的按键: {key}"}
            
            # 搜索键特殊处理：先尝试keycode=84，失败则自动尝试keycode=66
            if is_search_key and verify:
                result = await self._press_search_key_with_fallback()
                return result
            
            # 标准按键处理
            if verify:
                # 获取操作前页面状态
                initial_xml = self.u2.dump_hierarchy()
                initial_length = len(initial_xml)
            
            # 使用keycode按键 - uiautomator2使用shell命令
            try:
                # 方法1: 尝试使用u2的shell方法
                self.u2.shell(f'input keyevent {keycode}')
            except Exception:
                # 方法2: 使用ADB命令
                import subprocess
                subprocess.run([self.device_manager.adb_path, '-s', self.device_manager.current_device_id, 
                               'shell', 'input', 'keyevent', str(keycode)], 
                               check=True, timeout=5)
            
            if verify:
                # 等待并检测页面变化
                page_changed = await self._verify_page_change(initial_length, timeout=2.0)
                
                if page_changed:
                    print(f"  ✅ 按键成功且页面已变化: {key} (keycode={keycode})", file=sys.stderr)
                    return {
                        "success": True,
                        "key": key,
                        "keycode": keycode,
                        "verified": True,
                        "page_changed": True,
                        "message": "按键成功且页面已变化"
                    }
                else:
                    print(f"  ⚠️  按键命令执行但页面未变化: {key} (keycode={keycode})", file=sys.stderr)
                    return {
                        "success": False,
                        "key": key,
                        "keycode": keycode,
                        "verified": True,
                        "page_changed": False,
                        "message": "按键命令执行成功但页面未变化，可能按键未生效"
                    }
            else:
                # 快速模式：不验证，直接返回
                print(f"  ✅ 按键成功（未验证）: {key} (keycode={keycode})", file=sys.stderr)
                return {"success": True, "key": key, "keycode": keycode, "verified": False}
                
        except Exception as e:
            print(f"  ❌ 按键失败: {e}", file=sys.stderr)
            return {"success": False, "reason": str(e)}
    
    async def _press_search_key_with_fallback(self) -> Dict:
        """
        搜索键的特殊处理：尝试多种方案
        
        策略：
        1. 先尝试 keycode=84 (SEARCH键)
        2. 如果页面没变化，尝试 keycode=66 (ENTER键)
        3. 返回真实的成功/失败状态
        
        Returns:
            操作结果
        """
        print(f"  🔍 智能搜索键：先尝试SEARCH键...", file=sys.stderr)
        
        # 获取初始页面状态
        initial_xml = self.u2.dump_hierarchy()
        initial_length = len(initial_xml)
        
        # 方案1: 尝试 SEARCH 键 (keycode=84)
        try:
            self.u2.shell('input keyevent 84')
            print(f"  ⏳ 已发送SEARCH键，等待页面变化...", file=sys.stderr)
            
            # 检测页面变化
            page_changed = await self._verify_page_change(initial_length, timeout=2.0)
            
            if page_changed:
                print(f"  ✅ SEARCH键生效，页面已变化", file=sys.stderr)
                return {
                    "success": True,
                    "key": "search",
                    "keycode": 84,
                    "verified": True,
                    "page_changed": True,
                    "fallback_used": False,
                    "message": "搜索键(SEARCH)生效"
                }
            else:
                print(f"  ⚠️  SEARCH键未生效，尝试备选方案ENTER键...", file=sys.stderr)
                
                # 方案2: 尝试 ENTER 键 (keycode=66)
                # 重新获取当前页面状态（因为可能有轻微变化）
                current_xml = self.u2.dump_hierarchy()
                current_length = len(current_xml)
                
                self.u2.shell('input keyevent 66')
                print(f"  ⏳ 已发送ENTER键，等待页面变化...", file=sys.stderr)
                
                # 再次检测页面变化
                page_changed_enter = await self._verify_page_change(current_length, timeout=2.0)
                
                if page_changed_enter:
                    print(f"  ✅ ENTER键生效，页面已变化", file=sys.stderr)
                    return {
                        "success": True,
                        "key": "search",
                        "keycode": 66,
                        "verified": True,
                        "page_changed": True,
                        "fallback_used": True,
                        "message": "搜索键(SEARCH)无效，已使用ENTER键替代并成功"
                    }
                else:
                    print(f"  ❌ SEARCH和ENTER键都未生效", file=sys.stderr)
                    return {
                        "success": False,
                        "key": "search",
                        "verified": True,
                        "page_changed": False,
                        "fallback_used": True,
                        "message": "搜索键(SEARCH)和ENTER键都未生效，请检查输入框焦点或应用是否响应"
                    }
        except Exception as e:
            print(f"  ❌ 搜索键执行失败: {e}", file=sys.stderr)
            return {"success": False, "reason": str(e)}
    
    async def _verify_page_change(self, initial_length: int, timeout: float = None, change_threshold: float = None) -> bool:
        """
        验证页面是否发生变化
        
        Args:
            initial_length: 初始页面XML长度
            timeout: 最大等待时间（秒），None则使用动态配置
            change_threshold: 变化阈值（百分比），None则使用动态配置
        
        Returns:
            页面是否发生了明显变化
        """
        # 使用动态配置（支持AI调整）
        if timeout is None:
            timeout = DynamicConfig.page_change_timeout
        if change_threshold is None:
            change_threshold = DynamicConfig.page_change_threshold
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            await asyncio.sleep(0.1)  # 每100ms检查一次
            
            try:
                current_xml = self.u2.dump_hierarchy()
                current_length = len(current_xml)
                
                # 计算变化百分比
                change_percent = abs(current_length - initial_length) / max(1, initial_length)
                
                if change_percent > change_threshold:
                    print(f"  📊 页面变化检测: {change_percent*100:.1f}% (阈值: {change_threshold*100}%)", file=sys.stderr)
                    # 等待页面稳定（使用动态配置）
                    await asyncio.sleep(DynamicConfig.wait_page_stable)
                    print(f"  ⏳ 已等待页面稳定 {DynamicConfig.wait_page_stable}秒", file=sys.stderr)
                    return True
            except Exception as e:
                print(f"  ⚠️  页面变化检测异常: {e}", file=sys.stderr)
                pass
        
        print(f"  📊 页面变化检测: 未检测到明显变化（超时{timeout}秒）", file=sys.stderr)
        return False
    
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
    
    async def _ios_click(self, element: str, ref: Optional[str] = None):
        """
        iOS平台的点击实现
        
        Args:
            element: 元素描述
            ref: 元素定位器
            
        Returns:
            操作结果
        """
        try:
            from selenium.webdriver.common.by import By
            
            # 如果提供了ref，直接使用
            if ref:
                if ref.startswith('//') or ref.startswith('/'):
                    # XPath
                    elem = self.driver.find_element(By.XPATH, ref)
                elif ref.startswith('id='):
                    # accessibility_id
                    elem = self.driver.find_element(By.ID, ref.replace('id=', ''))
                else:
                    # 默认作为accessibility_id
                    elem = self.driver.find_element(By.ID, ref)
            else:
                # 尝试多种定位方式
                selectors = [
                    (By.XPATH, f"//*[@name='{element}']"),
                    (By.XPATH, f"//*[@label='{element}']"),
                    (By.XPATH, f"//*[contains(@name, '{element}')]"),
                ]
                
                elem = None
                for by, selector in selectors:
                    try:
                        elem = self.driver.find_element(by, selector)
                        break
                    except:
                        continue
                
                if not elem:
                    raise ValueError(f"未找到元素: {element}")
            
            elem.click()
            
            # 记录操作
            self.operation_history.append({
                'action': 'click',
                'element': element,
                'ref': ref or 'auto',
                'success': True
            })
            
            return {"success": True, "ref": ref or element}
            
        except Exception as e:
            return {"success": False, "reason": str(e)}
    
    async def _ios_type_text(self, element: str, text: str, ref: Optional[str] = None):
        """
        iOS平台的输入文本实现
        
        Args:
            element: 元素描述
            text: 要输入的文本
            ref: 元素定位器
            
        Returns:
            操作结果
        """
        try:
            from selenium.webdriver.common.by import By
            
            # 定位输入框
            if ref:
                if ref.startswith('//'):
                    elem = self.driver.find_element(By.XPATH, ref)
                else:
                    elem = self.driver.find_element(By.ID, ref)
            else:
                # 查找第一个输入框
                elem = self.driver.find_element(By.XPATH, "//XCUIElementTypeTextField | //XCUIElementTypeSecureTextField")
            
            elem.clear()
            elem.send_keys(text)
            
            # 记录操作
            self.operation_history.append({
                'action': 'type',
                'element': element,
                'text': text,
                'ref': ref or 'auto',
                'success': True
            })
            
            return {"success": True, "ref": ref or element}
            
        except Exception as e:
            return {"success": False, "reason": str(e)}

