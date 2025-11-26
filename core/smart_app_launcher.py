#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能App启动器 - 处理广告、弹窗、加载等待
"""
import asyncio
import sys
from typing import Dict, Optional


class SmartAppLauncher:
    """
    智能App启动器
    
    功能：
    1. 启动App后智能等待主页加载
    2. 自动检测并关闭广告/弹窗
    3. 等待网络加载完成
    4. 智能判断是否进入主页
    """
    
    def __init__(self, mobile_client):
        """
        初始化智能启动器
        
        Args:
            mobile_client: MobileClient实例
        """
        self.client = mobile_client
        
        # 常见的广告/弹窗关闭按钮特征
        self.ad_close_keywords = [
            '跳过', '关闭', '×', 'X', 'x', '✕',
            'skip', 'close', '稍后', '取消',
            '我知道了', '不再提示', '下次再说',
            '暂不', '以后再说', '返回'
        ]
        
        # 常见的弹窗容器特征
        self.popup_keywords = [
            'dialog', 'popup', 'alert', 'modal',
            '弹窗', '对话框', '提示'
        ]
    
    async def launch_with_smart_wait(
        self, 
        package_name: str, 
        max_wait: int = 10,
        auto_close_ads: bool = True
    ) -> Dict:
        """
        智能启动App并等待主页加载
        
        Args:
            package_name: App包名
            max_wait: 最大等待时间（秒）
            auto_close_ads: 是否自动关闭广告/弹窗
            
        Returns:
            启动结果
        """
        print(f"\n🚀 智能启动App: {package_name}", file=sys.stderr)
        
        try:
            # 1. 启动App
            print(f"  📱 正在启动...", file=sys.stderr)
            self.client.u2.app_start(package_name)
            await asyncio.sleep(1)  # 等待App进程启动
            
            # 2. 验证App是否启动
            current_package = await self._get_current_package()
            if current_package != package_name:
                return {
                    "success": False,
                    "reason": f"App启动失败，当前: {current_package}，期望: {package_name}"
                }
            
            print(f"  ✅ App进程已启动", file=sys.stderr)
            
            # 3. 智能等待主页加载（检测广告、弹窗、加载状态）
            result = await self._wait_for_home_page(
                package_name, 
                max_wait=max_wait,
                auto_close_ads=auto_close_ads
            )
            
            if result['loaded']:
                print(f"  ✅ 主页加载完成！", file=sys.stderr)
                return {
                    "success": True,
                    "package": package_name,
                    "wait_time": result['wait_time'],
                    "ads_closed": result['ads_closed'],
                    "popups_closed": result['popups_closed']
                }
            else:
                print(f"  ⚠️  等待超时，但App已启动", file=sys.stderr)
                return {
                    "success": True,
                    "package": package_name,
                    "warning": "主页加载超时，但App已启动",
                    "wait_time": result['wait_time'],
                    "ads_closed": result['ads_closed'],
                    "popups_closed": result['popups_closed']
                }
            
        except Exception as e:
            print(f"  ❌ 智能启动失败: {e}", file=sys.stderr)
            return {
                "success": False,
                "reason": str(e)
            }
    
    async def _wait_for_home_page(
        self, 
        package_name: str, 
        max_wait: int = 10,
        auto_close_ads: bool = True
    ) -> Dict:
        """
        等待主页加载完成
        
        策略：
        1. 每0.5秒检查一次页面状态
        2. 检测广告/弹窗并自动关闭
        3. 检测页面是否稳定（元素不再变化）
        4. 超时后返回当前状态
        
        Returns:
            {
                "loaded": bool,  # 是否加载完成
                "wait_time": float,  # 等待时间
                "ads_closed": int,  # 关闭的广告数
                "popups_closed": int  # 关闭的弹窗数
            }
        """
        import time
        start_time = time.time()
        
        ads_closed = 0
        popups_closed = 0
        last_snapshot = None
        stable_count = 0  # 页面稳定计数（连续2次快照相同认为稳定）
        
        print(f"  ⏳ 等待主页加载（最多{max_wait}秒）...", file=sys.stderr)
        
        for i in range(max_wait * 2):  # 每0.5秒检查一次
            await asyncio.sleep(0.5)
            elapsed = time.time() - start_time
            
            # 检查当前包名（防止跳转到其他App）
            current_package = await self._get_current_package()
            if current_package != package_name:
                print(f"  ⚠️  检测到包名变化: {package_name} -> {current_package}", file=sys.stderr)
                # 可能跳转到其他页面（如授权页），继续等待
                await asyncio.sleep(1)
                continue
            
            # 获取页面快照
            try:
                snapshot = self.client.u2.dump_hierarchy()
                
                # 1. 检测并关闭广告/弹窗
                if auto_close_ads:
                    closed = await self._try_close_ads_and_popups(snapshot)
                    if closed:
                        ads_closed += closed
                        print(f"  🎯 已关闭 {closed} 个广告/弹窗", file=sys.stderr)
                        await asyncio.sleep(0.5)  # 等待关闭动画
                        continue  # 重新检查
                
                # 2. 检测页面是否稳定
                if last_snapshot and snapshot == last_snapshot:
                    stable_count += 1
                    if stable_count >= 2:
                        # 页面已稳定（连续2次快照相同）
                        print(f"  ✅ 页面稳定，加载完成（耗时{elapsed:.1f}秒）", file=sys.stderr)
                        return {
                            "loaded": True,
                            "wait_time": elapsed,
                            "ads_closed": ads_closed,
                            "popups_closed": popups_closed
                        }
                else:
                    stable_count = 0
                
                last_snapshot = snapshot
                
                # 每2秒打印一次等待进度
                if i % 4 == 0 and i > 0:
                    print(f"  ⏳ 等待中... ({elapsed:.1f}秒)", file=sys.stderr)
            
            except Exception as e:
                print(f"  ⚠️  检查页面状态失败: {e}", file=sys.stderr)
                continue
        
        # 超时
        elapsed = time.time() - start_time
        print(f"  ⏰ 等待超时（{elapsed:.1f}秒），但App已启动", file=sys.stderr)
        return {
            "loaded": False,
            "wait_time": elapsed,
            "ads_closed": ads_closed,
            "popups_closed": popups_closed
        }
    
    async def _try_close_ads_and_popups(self, snapshot: str) -> int:
        """
        尝试关闭广告和弹窗
        
        Args:
            snapshot: 页面XML快照
            
        Returns:
            关闭的数量
        """
        closed_count = 0
        
        try:
            # 解析XML查找关闭按钮
            elements = self.client.xml_parser.parse(snapshot)
            
            # 查找可能的关闭按钮
            close_buttons = []
            
            for elem in elements:
                if not elem.get('clickable', False):
                    continue
                
                text = elem.get('text', '').lower()
                content_desc = elem.get('content_desc', '').lower()
                resource_id = elem.get('resource_id', '').lower()
                
                # 检查是否是关闭按钮
                is_close_button = False
                for keyword in self.ad_close_keywords:
                    keyword_lower = keyword.lower()
                    if (keyword_lower in text or 
                        keyword_lower in content_desc or
                        keyword_lower in resource_id or
                        ('close' in resource_id and 'btn' in resource_id) or
                        ('skip' in resource_id)):
                        is_close_button = True
                        break
                
                if is_close_button:
                    close_buttons.append(elem)
            
            # 尝试点击关闭按钮
            for button in close_buttons[:3]:  # 最多尝试3个
                try:
                    # 优先使用bounds点击（更可靠）
                    bounds = button.get('bounds', '')
                    if bounds:
                        # 解析bounds并点击中心点
                        import re
                        match = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                        if match:
                            x1, y1, x2, y2 = map(int, match.groups())
                            center_x = (x1 + x2) // 2
                            center_y = (y1 + y2) // 2
                            
                            self.client.u2.click(center_x, center_y)
                            closed_count += 1
                            
                            button_desc = button.get('text') or button.get('content_desc') or '未知'
                            print(f"  🎯 已点击关闭按钮: {button_desc}", file=sys.stderr)
                            
                            await asyncio.sleep(0.3)  # 等待关闭动画
                
                except Exception as e:
                    print(f"  ⚠️  点击关闭按钮失败: {e}", file=sys.stderr)
                    continue
            
            return closed_count
            
        except Exception as e:
            print(f"  ⚠️  关闭广告/弹窗失败: {e}", file=sys.stderr)
            return 0
    
    async def _get_current_package(self) -> Optional[str]:
        """获取当前包名"""
        try:
            info = self.client.u2.app_current()
            return info.get('package')
        except:
            return None

