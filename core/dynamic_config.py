#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动态配置管理器 - 运行时可调整的自动化行为配置

功能：
1. 提供默认配置（与硬编码值完全一致，保证兼容性）
2. 支持运行时动态调整（通过 mobile_configure 工具）
3. 让 AI 可以根据 App 特性和场景优化配置

设计原则：
- 默认值 = 当前硬编码值（保证向后兼容）
- 所有配置都可选（不调用就用默认值）
- 运行时可修改（无需重启）
"""
import sys
from typing import Dict, Any, Optional


class DynamicConfig:
    """
    动态配置管理器（运行时可调整）
    
    所有默认值都与当前硬编码值完全一致，保证 100% 向后兼容
    """
    
    # ==================== 等待时间策略 ====================
    
    # 点击后等待时间（秒）- 让页面有时间响应
    wait_after_click: float = 0.3
    
    # 输入后等待时间（秒）- 让UI更新
    wait_after_input: float = 0.3
    
    # 页面稳定等待时间（秒）- 确保动画/过渡完成
    wait_page_stable: float = 0.8
    
    # 元素等待默认超时（秒）
    element_wait_timeout: float = 10.0
    
    # 页面变化检测超时（秒）
    page_change_timeout: float = 2.0
    
    # ==================== 验证策略 ====================
    
    # 是否验证点击操作
    verify_clicks: bool = True
    
    # 是否验证输入操作
    verify_inputs: bool = False
    
    # 是否验证按键操作
    verify_keys: bool = True
    
    # ==================== 页面检测阈值 ====================
    
    # 页面变化阈值（0-1）- 百分比
    # 默认 0.05 = 5% 变化就认为页面发生了变化
    page_change_threshold: float = 0.05
    
    # 页面稳定阈值（秒）- 连续多久无变化认为稳定
    page_stable_threshold: float = 0.3
    
    # ==================== 屏幕方向控制 ====================
    
    # 屏幕方向：portrait(竖屏), landscape(横屏), auto(跟随App)
    screen_orientation: str = "portrait"
    
    # 是否锁定屏幕方向
    lock_screen_orientation: bool = True
    
    # ==================== 广告/弹窗处理 ====================
    
    # 是否自动关闭广告
    auto_close_ads: bool = True
    
    # 点击关闭按钮前的等待时间（秒）
    wait_before_close_ad: float = 0.3
    
    # 最多点击多少个关闭按钮（避免误点击）
    max_close_buttons: int = 1
    
    # ==================== 截图策略 ====================
    
    # 截图策略：always(总是), on_failure(失败时), never(从不), smart(智能)
    screenshot_strategy: str = "smart"
    
    # ==================== 重试策略 ====================
    
    # 操作失败时的最大重试次数
    max_retries: int = 3
    
    # 重试间隔（秒）
    retry_delay: float = 1.0
    
    # ==================== 配置管理 ====================
    
    @classmethod
    def update(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新配置
        
        Args:
            config: 配置字典，支持嵌套结构
            
        Returns:
            更新后的配置摘要
            
        示例:
            DynamicConfig.update({
                "wait_strategy": {
                    "click_wait": 0.5,
                    "input_wait": 0.5
                },
                "screen_orientation": "landscape",
                "page_change_threshold": 0.1
            })
        """
        updated = []
        
        # 处理嵌套的等待策略
        if "wait_strategy" in config:
            wait = config["wait_strategy"]
            if "click_wait" in wait:
                cls.wait_after_click = float(wait["click_wait"])
                updated.append(f"wait_after_click={cls.wait_after_click}")
            if "input_wait" in wait:
                cls.wait_after_input = float(wait["input_wait"])
                updated.append(f"wait_after_input={cls.wait_after_input}")
            if "page_stable_wait" in wait:
                cls.wait_page_stable = float(wait["page_stable_wait"])
                updated.append(f"wait_page_stable={cls.wait_page_stable}")
            if "element_timeout" in wait:
                cls.element_wait_timeout = float(wait["element_timeout"])
                updated.append(f"element_wait_timeout={cls.element_wait_timeout}")
            if "page_change_timeout" in wait:
                cls.page_change_timeout = float(wait["page_change_timeout"])
                updated.append(f"page_change_timeout={cls.page_change_timeout}")
        
        # 处理验证策略
        if "verify_strategy" in config:
            verify = config["verify_strategy"]
            if "verify_clicks" in verify:
                cls.verify_clicks = bool(verify["verify_clicks"])
                updated.append(f"verify_clicks={cls.verify_clicks}")
            if "verify_inputs" in verify:
                cls.verify_inputs = bool(verify["verify_inputs"])
                updated.append(f"verify_inputs={cls.verify_inputs}")
            if "verify_keys" in verify:
                cls.verify_keys = bool(verify["verify_keys"])
                updated.append(f"verify_keys={cls.verify_keys}")
        
        # 处理广告策略
        if "ad_handling" in config:
            ad = config["ad_handling"]
            if "auto_close" in ad:
                cls.auto_close_ads = bool(ad["auto_close"])
                updated.append(f"auto_close_ads={cls.auto_close_ads}")
            if "wait_before_close" in ad:
                cls.wait_before_close_ad = float(ad["wait_before_close"])
                updated.append(f"wait_before_close_ad={cls.wait_before_close_ad}")
            if "max_close_buttons" in ad:
                cls.max_close_buttons = int(ad["max_close_buttons"])
                updated.append(f"max_close_buttons={cls.max_close_buttons}")
        
        # 处理重试策略
        if "retry_strategy" in config:
            retry = config["retry_strategy"]
            if "max_retries" in retry:
                cls.max_retries = int(retry["max_retries"])
                updated.append(f"max_retries={cls.max_retries}")
            if "retry_delay" in retry:
                cls.retry_delay = float(retry["retry_delay"])
                updated.append(f"retry_delay={cls.retry_delay}")
        
        # 处理简单配置项
        simple_configs = {
            "page_change_threshold": (float, "page_change_threshold"),
            "page_stable_threshold": (float, "page_stable_threshold"),
            "screen_orientation": (str, "screen_orientation"),
            "lock_screen_orientation": (bool, "lock_screen_orientation"),
            "screenshot_strategy": (str, "screenshot_strategy"),
        }
        
        for key, (type_cast, attr_name) in simple_configs.items():
            if key in config:
                setattr(cls, attr_name, type_cast(config[key]))
                updated.append(f"{attr_name}={getattr(cls, attr_name)}")
        
        print(f"  ✅ 配置已更新: {', '.join(updated)}", file=sys.stderr)
        
        return {
            "success": True,
            "updated": updated,
            "message": f"成功更新 {len(updated)} 项配置"
        }
    
    @classmethod
    def get_current(cls) -> Dict[str, Any]:
        """
        获取当前配置
        
        Returns:
            当前所有配置的字典
        """
        return {
            "wait_strategy": {
                "click_wait": cls.wait_after_click,
                "input_wait": cls.wait_after_input,
                "page_stable_wait": cls.wait_page_stable,
                "element_timeout": cls.element_wait_timeout,
                "page_change_timeout": cls.page_change_timeout,
            },
            "verify_strategy": {
                "verify_clicks": cls.verify_clicks,
                "verify_inputs": cls.verify_inputs,
                "verify_keys": cls.verify_keys,
            },
            "thresholds": {
                "page_change_threshold": cls.page_change_threshold,
                "page_stable_threshold": cls.page_stable_threshold,
            },
            "screen": {
                "orientation": cls.screen_orientation,
                "lock_orientation": cls.lock_screen_orientation,
            },
            "ad_handling": {
                "auto_close": cls.auto_close_ads,
                "wait_before_close": cls.wait_before_close_ad,
                "max_close_buttons": cls.max_close_buttons,
            },
            "screenshot_strategy": cls.screenshot_strategy,
            "retry_strategy": {
                "max_retries": cls.max_retries,
                "retry_delay": cls.retry_delay,
            }
        }
    
    @classmethod
    def reset(cls) -> Dict[str, str]:
        """
        重置所有配置为默认值
        
        Returns:
            重置结果
        """
        cls.wait_after_click = 0.3
        cls.wait_after_input = 0.3
        cls.wait_page_stable = 0.8
        cls.element_wait_timeout = 10.0
        cls.page_change_timeout = 2.0
        cls.verify_clicks = True
        cls.verify_inputs = False
        cls.verify_keys = True
        cls.page_change_threshold = 0.05
        cls.page_stable_threshold = 0.3
        cls.screen_orientation = "portrait"
        cls.lock_screen_orientation = True
        cls.auto_close_ads = True
        cls.wait_before_close_ad = 0.3
        cls.max_close_buttons = 1
        cls.screenshot_strategy = "smart"
        cls.max_retries = 3
        cls.retry_delay = 1.0
        
        print("  ✅ 配置已重置为默认值", file=sys.stderr)
        
        return {
            "success": True,
            "message": "所有配置已重置为默认值"
        }

