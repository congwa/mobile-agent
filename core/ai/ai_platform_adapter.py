#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI平台适配器 - 支持多种AI平台的可选增强功能

支持的平台：
1. Cursor AI - 多模态视觉识别
2. Claude (Anthropic) - 通用AI能力
3. OpenAI GPT-4V - 视觉识别
4. 其他支持MCP的AI平台

设计理念：
- 基础功能不依赖AI平台（通用）
- AI增强功能作为可选插件
- 自动检测可用的AI平台
- 优雅降级（AI不可用时使用基础功能）
"""
import os
from typing import Optional, Dict, Any, List
from enum import Enum
from pathlib import Path


class AIPlatform(Enum):
    """支持的AI平台"""
    CURSOR = "cursor"
    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"
    NONE = "none"  # 无AI平台（仅基础功能）


class AIPlatformAdapter:
    """
    AI平台适配器
    
    功能：
    1. 自动检测可用的AI平台
    2. 提供统一的AI能力接口
    3. 支持多平台切换
    4. 优雅降级
    """
    
    def __init__(self):
        """初始化AI平台适配器"""
        self.detected_platform: AIPlatform = self._detect_platform()
        self.platform_config: Dict[str, Any] = {}
        self._initialize_platform()
    
    def _detect_platform(self) -> AIPlatform:
        """
        自动检测可用的AI平台
        
        检测顺序：
        1. Cursor AI (通过环境变量或MCP上下文)
        2. Claude (通过环境变量)
        3. OpenAI (通过环境变量)
        4. 其他平台
        """
        # 检测 Cursor AI
        if self._is_cursor_available():
            return AIPlatform.CURSOR
        
        # 检测 Claude
        if os.getenv("ANTHROPIC_API_KEY"):
            return AIPlatform.CLAUDE
        
        # 检测 OpenAI
        if os.getenv("OPENAI_API_KEY"):
            return AIPlatform.OPENAI
        
        # 检测 Gemini
        if os.getenv("GOOGLE_API_KEY"):
            return AIPlatform.GEMINI
        
        return AIPlatform.NONE
    
    def _is_cursor_available(self) -> bool:
        """检测 Cursor AI 是否可用"""
        # 方法1: 检查环境变量
        if os.getenv("CURSOR_AI_ENABLED", "").lower() == "true":
            return True
        
        # 方法2: 检查MCP上下文（在MCP Server中）
        # 如果是在MCP Server中运行，Cursor AI通常可用
        try:
            # 检查是否有MCP相关的环境
            mcp_server = os.getenv("MCP_SERVER_NAME", "")
            if "cursor" in mcp_server.lower():
                return True
        except:
            pass
        
        # 方法3: 🎯 在 MCP Server 环境中默认启用 Cursor AI
        # 如果没有配置其他 AI 平台，且在 MCP 环境中，默认使用 Cursor
        if self._is_running_in_mcp() and not self._has_other_ai_platform():
            return True
        
        return False
    
    def _is_running_in_mcp(self) -> bool:
        """检测是否在 MCP Server 环境中运行"""
        # 检查是否通过 MCP 协议运行（stdin/stdout）
        import sys
        return not sys.stdin.isatty() or os.getenv("MCP_MODE") == "1"
    
    def _has_other_ai_platform(self) -> bool:
        """检测是否配置了其他 AI 平台"""
        return bool(
            os.getenv("AI_PROVIDER") or
            os.getenv("ANTHROPIC_API_KEY") or
            os.getenv("OPENAI_API_KEY") or
            os.getenv("GOOGLE_API_KEY") or
            os.getenv("QWEN_API_KEY")
        )
    
    def _initialize_platform(self):
        """初始化检测到的平台"""
        if self.detected_platform == AIPlatform.CURSOR:
            self.platform_config = {
                "name": "Cursor AI",
                "multimodal": True,  # 支持多模态
                "vision": True,  # 支持视觉识别
                "free": True,  # Cursor AI免费使用
            }
        elif self.detected_platform == AIPlatform.CLAUDE:
            self.platform_config = {
                "name": "Claude (Anthropic)",
                "multimodal": True,
                "vision": True,
                "free": False,
            }
        elif self.detected_platform == AIPlatform.OPENAI:
            self.platform_config = {
                "name": "OpenAI GPT-4V",
                "multimodal": True,
                "vision": True,
                "free": False,
            }
        elif self.detected_platform == AIPlatform.GEMINI:
            self.platform_config = {
                "name": "Google Gemini",
                "multimodal": True,
                "vision": True,
                "free": True,  # Gemini有免费额度
            }
        else:
            self.platform_config = {
                "name": "None (基础模式)",
                "multimodal": False,
                "vision": False,
                "free": True,
            }
    
    def is_vision_available(self) -> bool:
        """检查是否支持视觉识别"""
        return self.platform_config.get("vision", False)
    
    def is_multimodal_available(self) -> bool:
        """检查是否支持多模态"""
        return self.platform_config.get("multimodal", False)
    
    def get_platform_name(self) -> str:
        """获取平台名称"""
        return self.platform_config.get("name", "Unknown")
    
    async def analyze_screenshot(
        self, 
        screenshot_path: str, 
        element_desc: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        分析截图（统一接口）
        
        Args:
            screenshot_path: 截图路径
            element_desc: 元素描述
            **kwargs: 平台特定参数
            
        Returns:
            坐标信息或None
        """
        if not self.is_vision_available():
            return None
        
        if self.detected_platform == AIPlatform.CURSOR:
            return await self._analyze_with_cursor(screenshot_path, element_desc, **kwargs)
        elif self.detected_platform == AIPlatform.CLAUDE:
            return await self._analyze_with_claude(screenshot_path, element_desc, **kwargs)
        elif self.detected_platform == AIPlatform.OPENAI:
            return await self._analyze_with_openai(screenshot_path, element_desc, **kwargs)
        elif self.detected_platform == AIPlatform.GEMINI:
            return await self._analyze_with_gemini(screenshot_path, element_desc, **kwargs)
        
        return None
    
    async def _analyze_with_cursor(
        self, 
        screenshot_path: str, 
        element_desc: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        使用 Cursor AI 分析截图
        
        Cursor AI 通过 MCP 工具调用，返回结果文件路径
        """
        # Cursor AI 的特殊处理：
        # 1. 创建请求文件
        # 2. 返回提示信息，让 Cursor AI 通过 MCP 工具分析
        # 3. 轮询结果文件
        
        request_id = kwargs.get("request_id")
        if request_id:
            # 自动模式：等待 Cursor AI 写入结果文件
            result_file = kwargs.get("result_file")
            if result_file and Path(result_file).exists():
                import json
                with open(result_file, 'r', encoding='utf-8') as f:
                    result_data = json.load(f)
                    if result_data.get("status") == "completed":
                        coord = result_data.get("coordinate")
                        if coord:
                            return {
                                "x": coord.get("x"),
                                "y": coord.get("y"),
                                "confidence": coord.get("confidence", 90),
                                "platform": "cursor"
                            }
        
        # 手动模式：返回提示信息
        return {
            "platform": "cursor",
            "instruction": f"请使用多模态能力分析截图 {screenshot_path}，找到元素 '{element_desc}' 并返回坐标",
            "screenshot_path": screenshot_path,
            "element_desc": element_desc
        }
    
    async def _analyze_with_claude(
        self, 
        screenshot_path: str, 
        element_desc: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """使用 Claude API 分析截图"""
        # TODO: 实现 Claude API 调用
        # 需要安装 anthropic SDK
        try:
            from anthropic import Anthropic
            
            client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            
            # 读取截图
            with open(screenshot_path, 'rb') as f:
                image_data = f.read()
            
            # 调用 Claude Vision API
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_data.hex()  # 需要base64编码
                            }
                        },
                        {
                            "type": "text",
                            "text": f"分析这个移动端截图，找到元素 '{element_desc}' 并返回其中心点坐标，格式：{{\"x\": 100, \"y\": 200}}"
                        }
                    ]
                }]
            )
            
            # 解析响应
            # TODO: 解析 Claude 返回的坐标
            return None
            
        except ImportError:
            return None
        except Exception as e:
            print(f"⚠️  Claude API 调用失败: {e}")
            return None
    
    async def _analyze_with_openai(
        self, 
        screenshot_path: str, 
        element_desc: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """使用 OpenAI GPT-4V 分析截图"""
        # TODO: 实现 OpenAI Vision API 调用
        try:
            import base64
            from openai import OpenAI
            
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            # 读取并编码截图
            with open(screenshot_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # 调用 GPT-4V
            response = client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"分析这个移动端截图，找到元素 '{element_desc}' 并返回其中心点坐标，格式：{{\"x\": 100, \"y\": 200}}"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_data}"
                            }
                        }
                    ]
                }],
                max_tokens=300
            )
            
            # 解析响应
            # TODO: 解析 OpenAI 返回的坐标
            return None
            
        except ImportError:
            return None
        except Exception as e:
            print(f"⚠️  OpenAI API 调用失败: {e}")
            return None
    
    async def _analyze_with_gemini(
        self, 
        screenshot_path: str, 
        element_desc: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """使用 Google Gemini 分析截图"""
        # TODO: 实现 Gemini Vision API 调用
        return None
    
    def get_enhanced_tools(self) -> List[Dict[str, Any]]:
        """
        获取AI增强的工具列表
        
        Returns:
            AI增强工具的定义列表
        """
        tools = []
        
        if self.is_vision_available():
            # 视觉识别工具（根据平台调整描述）
            platform_name = self.get_platform_name()
            tools.append({
                "name": "mobile_analyze_screenshot",
                "description": f"分析截图并返回元素坐标。使用{platform_name}的多模态能力分析截图，找到指定元素并返回坐标。",
                "platform": self.detected_platform.value,
                "enhanced": True
            })
        
        return tools
    
    def get_capabilities(self) -> Dict[str, Any]:
        """获取当前平台的AI能力"""
        return {
            "platform": self.detected_platform.value,
            "platform_name": self.get_platform_name(),
            "vision": self.is_vision_available(),
            "multimodal": self.is_multimodal_available(),
            "free": self.platform_config.get("free", False),
            "enhanced_tools": [t["name"] for t in self.get_enhanced_tools()]
        }


# 全局实例
_ai_adapter: Optional[AIPlatformAdapter] = None


def get_ai_adapter() -> AIPlatformAdapter:
    """获取全局AI适配器实例"""
    global _ai_adapter
    if _ai_adapter is None:
        _ai_adapter = AIPlatformAdapter()
    return _ai_adapter


def reset_ai_adapter():
    """重置AI适配器（用于测试）"""
    global _ai_adapter
    _ai_adapter = None

