#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能等待工具 - 为移动端操作提供智能等待机制

功能：
1. 页面稳定检测（避免固定等待时间）
2. 元素出现等待
3. 页面变化检测
4. 操作后自动等待
"""
import asyncio
import sys
import time
from typing import Optional, Callable


class SmartWait:
    """
    智能等待工具
    
    策略：
    1. 不使用固定等待时间，而是检测页面状态
    2. 快速轮询（100ms一次），减少不必要的等待
    3. 最大等待时间保护
    """
    
    def __init__(self, mobile_client):
        """
        初始化智能等待工具
        
        Args:
            mobile_client: MobileClient实例
        """
        self.client = mobile_client
        
        # 默认配置
        self.default_timeout = 5.0  # 默认最大等待5秒
        self.poll_interval = 0.1  # 轮询间隔100ms
        self.page_stable_threshold = 0.3  # 页面稳定阈值（连续300ms无变化认为稳定）
    
    async def wait_for_page_stable(self, timeout: float = None, element_threshold: int = 10) -> bool:
        """
        等待页面稳定（页面元素不再变化）
        
        Args:
            timeout: 最大等待时间（秒），None使用默认值
            element_threshold: 元素变化阈值，元素数量变化小于此值认为稳定
            
        Returns:
            是否稳定
        """
        timeout = timeout or self.default_timeout
        start_time = time.time()
        last_snapshot = None
        stable_count = 0
        required_stable_count = int(self.page_stable_threshold / self.poll_interval)
        
        print(f"  ⏳ 等待页面稳定（最多{timeout}秒）...", file=sys.stderr)
        
        while time.time() - start_time < timeout:
            try:
                # 获取当前页面快照（只获取元素数量，不解析详细内容）
                xml = self.client.u2.dump_hierarchy()
                current_snapshot = len(xml)  # 使用XML长度作为简单的页面状态标识
                
                if last_snapshot is not None:
                    change = abs(current_snapshot - last_snapshot)
                    if change <= element_threshold:
                        stable_count += 1
                        if stable_count >= required_stable_count:
                            elapsed = time.time() - start_time
                            print(f"  ✅ 页面已稳定（耗时{elapsed:.2f}秒）", file=sys.stderr)
                            return True
                    else:
                        stable_count = 0  # 页面仍在变化，重置计数
                
                last_snapshot = current_snapshot
                await asyncio.sleep(self.poll_interval)
                
            except Exception as e:
                print(f"  ⚠️  页面稳定检测失败: {e}", file=sys.stderr)
                await asyncio.sleep(self.poll_interval)
        
        print(f"  ⏰ 等待超时（{timeout}秒），但继续执行", file=sys.stderr)
        return False
    
    async def wait_for_element_appear(
        self, 
        element_check: Callable[[], bool],
        timeout: float = None,
        element_desc: str = "元素"
    ) -> bool:
        """
        等待元素出现
        
        Args:
            element_check: 检查元素是否存在的函数（返回bool）
            timeout: 最大等待时间（秒）
            element_desc: 元素描述（用于日志）
            
        Returns:
            元素是否出现
        """
        timeout = timeout or self.default_timeout
        start_time = time.time()
        
        print(f"  ⏳ 等待元素出现: {element_desc}（最多{timeout}秒）...", file=sys.stderr)
        
        while time.time() - start_time < timeout:
            try:
                if element_check():
                    elapsed = time.time() - start_time
                    print(f"  ✅ 元素已出现（耗时{elapsed:.2f}秒）", file=sys.stderr)
                    return True
            except Exception as e:
                # 忽略检查过程中的异常
                pass
            
            await asyncio.sleep(self.poll_interval)
        
        print(f"  ⏰ 元素未出现（超时{timeout}秒）", file=sys.stderr)
        return False
    
    async def wait_for_page_change(self, timeout: float = None) -> bool:
        """
        等待页面发生变化（用于点击后等待）
        
        Args:
            timeout: 最大等待时间（秒）
            
        Returns:
            页面是否变化
        """
        timeout = timeout or 2.0  # 点击后等待时间较短，默认2秒
        start_time = time.time()
        
        try:
            # 获取初始页面状态
            initial_xml = self.client.u2.dump_hierarchy()
            initial_length = len(initial_xml)
            
            while time.time() - start_time < timeout:
                await asyncio.sleep(self.poll_interval)
                
                try:
                    current_xml = self.client.u2.dump_hierarchy()
                    current_length = len(current_xml)
                    
                    # 页面变化超过5%认为有变化
                    change_percent = abs(current_length - initial_length) / max(1, initial_length)
                    if change_percent > 0.05:
                        elapsed = time.time() - start_time
                        print(f"  ✅ 页面已变化（耗时{elapsed:.2f}秒，变化{change_percent*100:.1f}%）", file=sys.stderr)
                        # 继续等待页面稳定
                        await self.wait_for_page_stable(timeout=1.0)
                        return True
                except Exception:
                    pass
            
            print(f"  ⚠️  页面未明显变化（可能是快速操作）", file=sys.stderr)
            return False
            
        except Exception as e:
            print(f"  ⚠️  页面变化检测失败: {e}", file=sys.stderr)
            return False
    
    async def wait_after_action(self, action_name: str = "操作", quick: bool = False):
        """
        操作后的智能等待
        
        Args:
            action_name: 操作名称（用于日志）
            quick: 是否快速模式（快速模式只等待页面稳定，不检测变化）
        """
        if quick:
            # 快速模式：只等待页面稳定（适用于不触发页面跳转的操作，如输入）
            await asyncio.sleep(0.2)  # 先等200ms，让UI有时间响应
            await self.wait_for_page_stable(timeout=1.0)
        else:
            # 标准模式：等待页面变化+稳定（适用于点击等会触发页面跳转的操作）
            await self.wait_for_page_change(timeout=2.0)
    
    async def smart_wait(
        self, 
        condition: Callable[[], bool],
        timeout: float = None,
        description: str = "条件满足"
    ) -> bool:
        """
        通用智能等待
        
        Args:
            condition: 条件检查函数（返回bool）
            timeout: 最大等待时间
            description: 条件描述
            
        Returns:
            条件是否满足
        """
        timeout = timeout or self.default_timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if condition():
                    elapsed = time.time() - start_time
                    print(f"  ✅ {description}（耗时{elapsed:.2f}秒）", file=sys.stderr)
                    return True
            except Exception:
                pass
            
            await asyncio.sleep(self.poll_interval)
        
        print(f"  ⏰ {description}超时（{timeout}秒）", file=sys.stderr)
        return False


# 使用示例
"""
# 在 MobileClient 中使用：

from .utils.smart_wait import SmartWait

class MobileClient:
    def __init__(self):
        self.smart_wait = SmartWait(self)
    
    async def click(self, element, ref):
        # 点击前等待元素出现
        await self.smart_wait.wait_for_element_appear(
            lambda: self.u2(text=ref).exists(),
            element_desc=element
        )
        
        # 执行点击
        self.u2(text=ref).click()
        
        # 点击后等待页面稳定
        await self.smart_wait.wait_after_action("点击")
        
        return {"success": True}
"""

