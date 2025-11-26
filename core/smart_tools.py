#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能 MCP 工具 - 需要 AI 密钥（可选功能）

提供智能定位和分析功能：
- 自然语言元素定位
- 智能元素识别
- 复杂场景分析

⚠️ 这些功能需要配置 AI 密钥才能使用
"""

from typing import Dict, Optional
import os


class SmartMobileTools:
    """智能移动端工具（需要 AI 密钥）"""
    
    def __init__(self, mobile_client):
        """
        初始化智能工具
        
        Args:
            mobile_client: MobileClient 实例
        """
        self.client = mobile_client
        self.ai_available = self._check_ai_available()
        
        if self.ai_available:
            # 延迟导入，避免没有配置 AI 时报错
            from .locator.mobile_smart_locator import MobileSmartLocator
            self.smart_locator = MobileSmartLocator(mobile_client)
        else:
            self.smart_locator = None
    
    def _check_ai_available(self) -> bool:
        """检查 AI 是否可用（是否配置了 AI 密钥）"""
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            ai_provider = os.getenv('AI_PROVIDER', '')
            
            # 检查是否配置了任何 AI 提供商
            if ai_provider in ['qwen', 'openai', 'claude', 'ollama']:
                # 检查对应的 API Key
                if ai_provider == 'qwen' and os.getenv('QWEN_API_KEY'):
                    return True
                elif ai_provider == 'openai' and os.getenv('OPENAI_API_KEY'):
                    return True
                elif ai_provider == 'claude' and os.getenv('ANTHROPIC_API_KEY'):
                    return True
                elif ai_provider == 'ollama':
                    return True  # Ollama 不需要 API Key
            
            return False
        except:
            return False
    
    def _ensure_ai_available(self):
        """确保 AI 可用，否则抛出友好的错误提示"""
        if not self.ai_available:
            raise ValueError(
                "❌ 智能定位功能需要配置 AI 密钥！\n\n"
                "请选择以下方案之一：\n\n"
                "方案1：使用基础工具（推荐，不需要 AI）\n"
                "  - mobile_list_elements() - 列出所有元素\n"
                "  - mobile_click_by_id(resource_id) - 通过 ID 点击\n"
                "  - mobile_click_at_coords(x, y) - 通过坐标点击\n\n"
                "方案2：配置 AI 密钥（启用智能功能）\n"
                "  创建 .env 文件：\n"
                "  AI_PROVIDER=qwen\n"
                "  QWEN_API_KEY=your-api-key\n\n"
                "详见: backend/mobile_mcp/AI_SETUP.md"
            )
    
    async def smart_click(self, description: str) -> Dict:
        """
        智能定位并点击元素（需要 AI 密钥）
        
        Args:
            description: 元素的自然语言描述（如 "顶部搜索框"、"登录按钮"）
        
        Returns:
            {"success": true/false, "message": "...", "method": "..."}
        
        示例：
            # 需要先配置 AI 密钥
            result = await tools.smart_click("右上角的设置按钮")
        
        ⚠️ 如果没有配置 AI 密钥，请使用基础工具：
            elements = mobile_list_elements()
            mobile_click_by_id("com.app:id/settings")
        """
        self._ensure_ai_available()
        
        try:
            # 使用智能定位器
            result = await self.smart_locator.locate(description)
            
            if result and result.get('ref'):
                # 执行点击
                ref = result['ref']
                method = result.get('method', 'unknown')
                
                # 根据不同的 ref 类型执行点击
                if ref.startswith('[') and ']' in ref:
                    # bounds 坐标
                    import re
                    coords = re.findall(r'\[(\d+),(\d+)\]', ref)
                    if coords:
                        x1, y1 = int(coords[0][0]), int(coords[0][1])
                        x2, y2 = int(coords[1][0]), int(coords[1][1])
                        x, y = (x1 + x2) // 2, (y1 + y2) // 2
                        self.client.u2.click(x, y)
                        return {
                            "success": True,
                            "message": f"智能定位成功: {description}",
                            "method": method,
                            "ref": ref
                        }
                elif ':id/' in ref:
                    # resource-id
                    self.client.u2(resourceId=ref).click()
                    return {
                        "success": True,
                        "message": f"智能定位成功: {description}",
                        "method": method,
                        "ref": ref
                    }
                else:
                    # text
                    self.client.u2(text=ref).click()
                    return {
                        "success": True,
                        "message": f"智能定位成功: {description}",
                        "method": method,
                        "ref": ref
                    }
            else:
                return {
                    "success": False,
                    "message": f"智能定位失败: {description}",
                    "suggestion": "请使用 mobile_list_elements() 查看页面元素，然后使用 mobile_click_by_id()"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"智能点击失败: {str(e)}",
                "suggestion": "建议使用基础工具: mobile_list_elements() + mobile_click_by_id()"
            }
    
    async def smart_input(self, description: str, text: str) -> Dict:
        """
        智能定位输入框并输入文本（需要 AI 密钥）
        
        Args:
            description: 输入框的自然语言描述（如 "用户名输入框"）
            text: 要输入的文本
        
        Returns:
            {"success": true/false, "message": "..."}
        
        示例：
            result = await tools.smart_input("邮箱输入框", "test@example.com")
        
        ⚠️ 如果没有配置 AI 密钥，请使用基础工具：
            mobile_input_text_by_id("com.app:id/email_input", "test@example.com")
        """
        self._ensure_ai_available()
        
        try:
            # 使用智能定位器
            result = await self.smart_locator.locate(description)
            
            if result and result.get('ref'):
                ref = result['ref']
                
                # 根据不同的 ref 类型执行输入
                if ':id/' in ref:
                    # resource-id
                    element = self.client.u2(resourceId=ref)
                    element.set_text(text)
                    return {
                        "success": True,
                        "message": f"智能输入成功: {description} = {text}",
                        "ref": ref
                    }
                else:
                    return {
                        "success": False,
                        "message": f"定位成功但无法输入: {ref}",
                        "suggestion": "请使用 mobile_find_elements_by_class('android.widget.EditText') 查找输入框"
                    }
            else:
                return {
                    "success": False,
                    "message": f"智能定位失败: {description}",
                    "suggestion": "请使用 mobile_list_elements() 查找输入框，然后使用 mobile_input_text_by_id()"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"智能输入失败: {str(e)}",
                "suggestion": "建议使用基础工具: mobile_input_text_by_id()"
            }
    
    async def analyze_screenshot_with_ai(self, screenshot_path: str, description: str) -> Dict:
        """
        使用 AI 分析截图并返回坐标（需要 AI 密钥）
        
        Args:
            screenshot_path: 截图文件路径
            description: 要查找的元素描述
        
        Returns:
            {
                "success": true/false,
                "x": 坐标X（如果成功）,
                "y": 坐标Y（如果成功）,
                "confidence": 置信度,
                "message": "..."
            }
        
        示例：
            # 先截图
            screenshot = mobile_take_screenshot("登录页面")
            
            # 然后用 AI 分析
            result = await tools.analyze_screenshot_with_ai(
                screenshot['screenshot_path'],
                "登录按钮"
            )
            
            # 根据返回的坐标点击
            if result['success']:
                mobile_click_at_coords(result['x'], result['y'])
        
        ⚠️ 需要配置支持视觉识别的 AI（如 GPT-4V、Claude 3、Qwen-VL）
        """
        self._ensure_ai_available()
        
        try:
            # 尝试使用视觉识别
            try:
                from ..vision.vision_locator import MobileVisionLocator
                
                vision_locator = MobileVisionLocator(self.client)
                result = await vision_locator.locate_element_by_vision(
                    description,
                    screenshot_path=screenshot_path
                )
                
                if result and result.get('found'):
                    x, y = result['x'], result['y']
                    confidence = result['confidence']
                    
                    return {
                        "success": True,
                        "x": x,
                        "y": y,
                        "confidence": confidence,
                        "message": f"✅ AI 视觉识别成功: ({x}, {y}), 置信度 {confidence}%"
                    }
                else:
                    reason = result.get('reason', '未知原因') if result else '未知原因'
                    return {
                        "success": False,
                        "message": f"❌ AI 视觉识别未找到元素: {reason}",
                        "suggestion": "请检查截图和元素描述是否准确"
                    }
            except ImportError:
                return {
                    "success": False,
                    "message": "❌ 视觉识别模块未安装",
                    "suggestion": "安装：pip install dashscope pillow"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"❌ 视觉识别失败: {str(e)}",
                "suggestion": "请使用基础工具或检查 AI 配置"
            }
    
    def get_ai_status(self) -> Dict:
        """
        获取 AI 功能状态
        
        Returns:
            {
                "available": true/false,
                "provider": "qwen/openai/...",
                "message": "..."
            }
        """
        if self.ai_available:
            provider = os.getenv('AI_PROVIDER', 'unknown')
            return {
                "available": True,
                "provider": provider,
                "message": f"✅ AI 功能已启用 (Provider: {provider})"
            }
        else:
            return {
                "available": False,
                "provider": None,
                "message": "⚠️ AI 功能未配置，当前仅支持基础工具。如需启用智能定位，请配置 AI 密钥。"
            }

