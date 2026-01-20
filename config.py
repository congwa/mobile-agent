#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mobile MCP 配置系统

功能：
1. 功能开关（启用/禁用AI增强）
2. 平台选择（强制使用特定平台）
3. 降级策略配置
"""
import os
from typing import Optional


class Config:
    """Mobile MCP 配置类"""
    
    # ==================== AI增强功能 ====================
    # AI增强功能开关（默认启用）
    AI_ENHANCEMENT_ENABLED: bool = os.getenv(
        "AI_ENHANCEMENT_ENABLED", 
        "true"
    ).lower() == "true"
    
    # 优先使用的AI平台（None=自动检测）
    # 可选值: "cursor", "claude", "openai", "gemini", None
    PREFERRED_AI_PLATFORM: Optional[str] = os.getenv(
        "PREFERRED_AI_PLATFORM",
        None
    )
    
    # AI失败时是否降级到基础功能
    FALLBACK_TO_BASIC_ON_AI_FAILURE: bool = os.getenv(
        "FALLBACK_TO_BASIC_ON_AI_FAILURE",
        "true"
    ).lower() == "true"
    
    # ==================== 平台支持 ====================
    # iOS支持开关（默认启用，需要安装iOS依赖）
    IOS_SUPPORT_ENABLED: bool = os.getenv(
        "IOS_SUPPORT_ENABLED",
        "true"
    ).lower() == "true"
    
    # 默认平台（"android" 或 "ios"）
    # 兼容两种环境变量名：MOBILE_PLATFORM（新）和 DEFAULT_PLATFORM（旧）
    DEFAULT_PLATFORM: str = os.getenv(
        "MOBILE_PLATFORM",
        os.getenv("DEFAULT_PLATFORM", "android")
    )
    
    # Android支持（默认启用）
    ANDROID_SUPPORT_ENABLED: bool = os.getenv(
        "ANDROID_SUPPORT_ENABLED",
        "true"
    ).lower() == "true"
    
    # ==================== 设备管理 ====================
    # 默认设备ID（"auto"=自动选择第一个）
    DEFAULT_DEVICE_ID: str = os.getenv("MOBILE_DEVICE_ID", "auto")
    
    # 锁定屏幕方向（默认启用）
    LOCK_SCREEN_ORIENTATION: bool = os.getenv(
        "LOCK_SCREEN_ORIENTATION",
        "true"
    ).lower() == "true"
    
    # ==================== 智能定位 ====================
    # 启用智能定位（默认启用）
    SMART_LOCATOR_ENABLED: bool = os.getenv(
        "SMART_LOCATOR_ENABLED",
        "true"
    ).lower() == "true"
    
    # 启用H5处理（默认启用）
    H5_HANDLER_ENABLED: bool = os.getenv(
        "H5_HANDLER_ENABLED",
        "true"
    ).lower() == "true"
    
    # ==================== 性能优化 ====================
    # 快照缓存TTL（秒）
    SNAPSHOT_CACHE_TTL: int = int(os.getenv("SNAPSHOT_CACHE_TTL", "1"))
    
    # 定位缓存TTL（秒）
    LOCATOR_CACHE_TTL: int = int(os.getenv("LOCATOR_CACHE_TTL", "300"))
    
    # ==================== HTTP服务器 ====================
    # HTTP服务器默认端口
    HTTP_SERVER_PORT: int = int(os.getenv("HTTP_SERVER_PORT", "8080"))
    
    # HTTP服务器默认主机
    HTTP_SERVER_HOST: str = os.getenv("HTTP_SERVER_HOST", "0.0.0.0")
    
    # ==================== 日志 ====================
    # 日志级别
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # 启用详细日志
    VERBOSE_LOGGING: bool = os.getenv(
        "VERBOSE_LOGGING",
        "false"
    ).lower() == "true"
    
    # ==================== Token 优化（省钱模式）====================
    # 启用 Token 优化（默认开启，只精简格式，不影响准确度）
    TOKEN_OPTIMIZATION_ENABLED: bool = os.getenv(
        "TOKEN_OPTIMIZATION_ENABLED",
        "true"
    ).lower() == "true"
    
    # list_elements 最大返回元素数量（默认 0 = 不限制，确保准确度）
    MAX_ELEMENTS_RETURN: int = int(os.getenv("MAX_ELEMENTS_RETURN", "0"))
    
    # take_screenshot_with_som 最大返回元素数量（默认 0 = 不限制）
    MAX_SOM_ELEMENTS_RETURN: int = int(os.getenv("MAX_SOM_ELEMENTS_RETURN", "0"))
    
    # 精简返回信息（只移除冗余提示文字，不影响数据）
    COMPACT_RESPONSE: bool = os.getenv(
        "COMPACT_RESPONSE",
        "true"
    ).lower() == "true"
    
    # 精简工具描述（减少每次请求的 token）
    COMPACT_TOOL_DESCRIPTION: bool = os.getenv(
        "COMPACT_TOOL_DESCRIPTION",
        "true"
    ).lower() == "true"
    
    @classmethod
    def get_ai_platform(cls) -> Optional[str]:
        """获取优先使用的AI平台"""
        return cls.PREFERRED_AI_PLATFORM
    
    @classmethod
    def is_ai_enhancement_enabled(cls) -> bool:
        """检查AI增强功能是否启用"""
        return cls.AI_ENHANCEMENT_ENABLED
    
    @classmethod
    def should_fallback_on_ai_failure(cls) -> bool:
        """检查AI失败时是否降级"""
        return cls.FALLBACK_TO_BASIC_ON_AI_FAILURE
    
    @classmethod
    def get_summary(cls) -> dict:
        """获取配置摘要"""
        return {
            "ai_enhancement": {
                "enabled": cls.AI_ENHANCEMENT_ENABLED,
                "preferred_platform": cls.PREFERRED_AI_PLATFORM or "auto",
                "fallback_on_failure": cls.FALLBACK_TO_BASIC_ON_AI_FAILURE,
            },
            "platform_support": {
                "android": cls.ANDROID_SUPPORT_ENABLED,
                "ios": cls.IOS_SUPPORT_ENABLED,
            },
            "features": {
                "smart_locator": cls.SMART_LOCATOR_ENABLED,
                "h5_handler": cls.H5_HANDLER_ENABLED,
            },
            "device": {
                "default_device_id": cls.DEFAULT_DEVICE_ID,
                "lock_orientation": cls.LOCK_SCREEN_ORIENTATION,
            },
            "token_optimization": {
                "enabled": cls.TOKEN_OPTIMIZATION_ENABLED,
                "max_elements": cls.MAX_ELEMENTS_RETURN,
                "max_som_elements": cls.MAX_SOM_ELEMENTS_RETURN,
                "compact_response": cls.COMPACT_RESPONSE,
                "compact_tool_desc": cls.COMPACT_TOOL_DESCRIPTION,
            }
        }

