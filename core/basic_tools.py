#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础 MCP 工具 - 不需要 AI 密钥

提供基础的移动端自动化工具：
- 元素列表获取
- 精确点击（resource-id/坐标）
- 输入、滑动、按键等
- 截图功能
"""

from typing import Dict, List, Optional
from pathlib import Path
import time


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
            result = self.client.u2(resourceId=resource_id).click()
            if result:
                return {"success": True, "message": f"成功点击: {resource_id}"}
            else:
                return {"success": False, "message": f"元素不存在: {resource_id}"}
        except Exception as e:
            return {"success": False, "message": f"点击失败: {str(e)}"}
    
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
            result = self.client.u2(text=text).click()
            if result:
                return {"success": True, "message": f"成功点击: {text}"}
            else:
                return {"success": False, "message": f"文本不存在: {text}"}
        except Exception as e:
            return {"success": False, "message": f"点击失败: {str(e)}"}
    
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
            return {"success": True, "message": f"成功点击坐标: ({x}, {y})"}
        except Exception as e:
            return {"success": False, "message": f"点击失败: {str(e)}"}
    
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
                return {"success": True, "message": f"成功输入: {text}"}
            else:
                return {"success": False, "message": f"输入框不存在: {resource_id}"}
        except Exception as e:
            return {"success": False, "message": f"输入失败: {str(e)}"}
    
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


