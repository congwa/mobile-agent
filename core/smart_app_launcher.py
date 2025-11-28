#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能App启动器 - 处理广告、弹窗、加载等待
"""
import asyncio
import sys
from typing import Dict, Optional

from .dynamic_config import DynamicConfig


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
        max_wait: int = 3,  # 优化：最多等待3秒（快速启动）
        auto_close_ads: bool = True
    ) -> Dict:
        """
        智能启动App并等待主页加载
        
        Args:
            package_name: App包名
            max_wait: 最大等待时间（秒，默认3秒 - 快速模式）
            auto_close_ads: 是否自动关闭广告/弹窗
            
        Returns:
            启动结果
        """
        print(f"\n🚀 智能启动App: {package_name}", file=sys.stderr)
        
        try:
            # 🎯 启动前：强制恢复竖屏（防止上次横屏残留）
            print(f"  🔄 检查屏幕方向...", file=sys.stderr)
            self.client.force_portrait()
            
            # 1. 启动App
            print(f"  📱 正在启动...", file=sys.stderr)
            self.client.u2.app_start(package_name)
            await asyncio.sleep(1)  # 等待App进程启动
            
            # 🎯 启动后：再次强制竖屏（防止App启动时强制横屏）
            self.client.force_portrait()
            
            # 2. 验证App是否启动
            current_package = await self._get_current_package()
            if current_package != package_name:
                return {
                    "success": False,
                    "reason": f"App启动失败，当前: {current_package}，期望: {package_name}"
                }
            
            print(f"  ✅ App进程已启动", file=sys.stderr)
            
            # 🎯 关键优化：确保启动后至少等待 2 秒，让界面完全渲染
            print(f"  ⏳ 等待界面渲染...", file=sys.stderr)
            await asyncio.sleep(2)  # 最小等待 2 秒
            print(f"  ✅ 已等待 2 秒，界面应已稳定", file=sys.stderr)
            
            # 3. 快速等待并自动截图验证（新策略）
            result = await self._wait_for_home_page_fast(
                package_name, 
                max_wait=max_wait,
                auto_close_ads=auto_close_ads
            )
            
            # 快速模式：总是返回成功+截图路径
            print(f"  ✅ App已启动{result['wait_time'] + 2:.1f}秒，已自动截图", file=sys.stderr)
            return {
                "success": True,
                "package": package_name,
                "wait_time": result['wait_time'],
                "ads_closed": result['ads_closed'],
                "screenshot_path": result.get('screenshot_path'),
                "message": "App已启动，请查看截图确认是否进入主页"
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
        max_wait: int = 5,  # 优化：从10秒减少到5秒
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
        
        check_interval = 0.3  # 优化：每0.3秒检查一次（更快响应）
        max_checks = int(max_wait / check_interval)
        
        for i in range(max_checks):
            await asyncio.sleep(check_interval)
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
                        await asyncio.sleep(0.3)  # 等待关闭动画（从0.5秒优化到0.3秒）
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
                
                # 优化：每1.5秒打印一次等待进度（从2秒减少）
                if i % 5 == 0 and i > 0:  # 5 * 0.3秒 = 1.5秒
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
        尝试关闭广告和弹窗（更谨慎的检测逻辑）
        
        Args:
            snapshot: 页面XML快照
            
        Returns:
            关闭的数量
        """
        closed_count = 0
        
        try:
            # 解析XML查找关闭按钮
            elements = self.client.xml_parser.parse(snapshot)
            
            # 🎯 改进：先检测是否有弹窗容器（避免误点击正常UI）
            has_popup = False
            for elem in elements:
                class_name = elem.get('class', '').lower()
                resource_id = elem.get('resource_id', '').lower()
                # 检查是否是弹窗容器
                if any(keyword in class_name or keyword in resource_id 
                       for keyword in ['dialog', 'popup', 'alert', 'modal']):
                    has_popup = True
                    break
            
            # 如果没有检测到弹窗容器，不执行关闭操作（避免误点击）
            if not has_popup:
                return 0
            
            # 查找可能的关闭按钮
            close_buttons = []
            
            for elem in elements:
                if not elem.get('clickable', False):
                    continue
                
                text = elem.get('text', '').lower()
                content_desc = elem.get('content_desc', '').lower()
                resource_id = elem.get('resource_id', '').lower()
                bounds = elem.get('bounds', '')
                
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
                
                # 🎯 改进：优先选择右上角的关闭按钮（更可能是真正的关闭按钮）
                if is_close_button and bounds:
                    import re
                    match = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                    if match:
                        x1, y1, x2, y2 = map(int, match.groups())
                        # 计算元素位置（右上角区域优先级更高）
                        elem['_priority'] = 0
                        if x1 > 800:  # 右侧
                            elem['_priority'] += 2
                        if y1 < 500:  # 上部
                            elem['_priority'] += 2
                        close_buttons.append(elem)

            
            # 🎯 改进：按优先级排序（右上角的关闭按钮优先）
            close_buttons.sort(key=lambda x: x.get('_priority', 0), reverse=True)
            
            # 尝试点击关闭按钮（使用动态配置的最大数量，避免误点击）
            max_buttons = DynamicConfig.max_close_buttons
            for button in close_buttons[:max_buttons]:
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
                            
                            button_desc = button.get('text') or button.get('content_desc') or '未知'
                            print(f"  🎯 检测到弹窗，点击关闭按钮: {button_desc} (位置: {center_x}, {center_y})", file=sys.stderr)
                            
                            # 使用动态配置的等待时间
                            await asyncio.sleep(DynamicConfig.wait_before_close_ad)
                            
                            self.client.u2.click(center_x, center_y)
                            closed_count += 1
                            
                            print(f"  ✅ 已关闭弹窗: {button_desc}", file=sys.stderr)
                            
                            # 等待关闭动画（使用动态配置）
                            await asyncio.sleep(DynamicConfig.wait_after_click)
                
                except Exception as e:
                    print(f"  ⚠️  点击关闭按钮失败: {e}", file=sys.stderr)
                    continue
            
            return closed_count
            
        except Exception as e:
            print(f"  ⚠️  关闭广告/弹窗失败: {e}", file=sys.stderr)
            return 0
    
    async def _wait_for_home_page_fast(
        self, 
        package_name: str, 
        max_wait: int = 3,  # 快速模式：最多3秒
        auto_close_ads: bool = True
    ) -> Dict:
        """
        快速启动模式：等待短时间后立即截图，让Cursor AI判断是否已进入主页
        
        策略：
        1. 等待2秒（让App基本启动）
        2. 期间检测并关闭广告/弹窗
        3. 等待结束后立即截图
        4. 提示用户通过Cursor AI验证截图
        
        Returns:
            {
                "loaded": bool,  # 是否加载完成
                "wait_time": float,  # 等待时间
                "ads_closed": int,  # 关闭的广告数
                "screenshot_path": str  # 截图路径（供AI验证）
            }
        """
        import time
        start_time = time.time()
        
        ads_closed = 0
        screenshot_path = None
        
        print(f"  ⏳ 快速启动模式：等待{max_wait}秒并自动截图...", file=sys.stderr)
        
        # 快速检测广告/弹窗（最多检查3次，每次1秒）
        for i in range(min(max_wait, 3)):
            await asyncio.sleep(1)
            elapsed = time.time() - start_time
            
            # 检查当前包名
            current_package = await self._get_current_package()
            if current_package != package_name:
                print(f"  ⚠️  检测到包名变化: {package_name} -> {current_package}", file=sys.stderr)
                await asyncio.sleep(0.5)
                continue
            
            # 检测并关闭广告/弹窗
            if auto_close_ads:
                try:
                    snapshot = self.client.u2.dump_hierarchy()
                    closed = await self._try_close_ads_and_popups(snapshot)
                    if closed:
                        ads_closed += closed
                        print(f"  🎯 已关闭 {closed} 个广告/弹窗", file=sys.stderr)
                except Exception as e:
                    print(f"  ⚠️  检查弹窗失败: {e}", file=sys.stderr)
            
            print(f"  ⏳ 已等待{int(elapsed)}秒...", file=sys.stderr)
        
        # 等待结束，立即截图
        elapsed = time.time() - start_time
        print(f"  📸 App已启动{elapsed:.1f}秒，正在截图供AI验证...", file=sys.stderr)
        
        try:
            import re
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            from pathlib import Path
            project_root = Path(__file__).parent.parent
            screenshot_dir = project_root / "screenshots"
            screenshot_dir.mkdir(exist_ok=True)
            
            # 生成截图文件名
            safe_package = re.sub(r'[^\w\s-]', '', package_name).strip()
            filename = f"app_launch_{safe_package}_{timestamp}.png"
            screenshot_path = screenshot_dir / filename
            
            # 截图
            self.client.u2.screenshot(str(screenshot_path))
            print(f"  ✅ 截图已保存: {screenshot_path}", file=sys.stderr)
            print(f"  💡 提示：请查看截图，确认是否已进入主页", file=sys.stderr)
            
        except Exception as e:
            print(f"  ⚠️  截图失败: {e}", file=sys.stderr)
        
        return {
            "wait_time": elapsed,
            "ads_closed": ads_closed,
            "screenshot_path": str(screenshot_path) if screenshot_path else None
        }
    
    async def _get_current_package(self) -> Optional[str]:
        """获取当前包名"""
        try:
            info = self.client.u2.app_current()
            return info.get('package')
        except:
            return None

