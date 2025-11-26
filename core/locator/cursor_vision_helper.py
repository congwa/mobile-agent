#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor AI 视觉识别辅助工具

当定位失败时，自动截图并请求Cursor AI分析。
这个模块提供了与Cursor AI交互的接口。
"""
import asyncio
import json
import tempfile
import os
from datetime import datetime
from typing import Dict, Optional, Tuple
from pathlib import Path
import time
import inspect
import traceback


class CursorVisionHelper:
    """
    Cursor AI 视觉识别辅助工具
    
    功能：
    1. 截图并保存
    2. 生成提示信息，让Cursor AI分析截图
    3. 解析Cursor AI返回的坐标
    """
    
    def __init__(self, mobile_client):
        """
        初始化Cursor视觉识别辅助工具
        
        Args:
            mobile_client: MobileClient实例
        """
        self.mobile_client = mobile_client
        # 🎯 使用项目内的screenshots目录，而不是临时目录
        project_root = Path(__file__).parent.parent.parent
        self.screenshot_dir = project_root / "screenshots"
        self.screenshot_dir.mkdir(exist_ok=True)
        self.request_dir = self.screenshot_dir / "requests"
        self.request_dir.mkdir(exist_ok=True)
        self.result_dir = self.screenshot_dir / "results"
        self.result_dir.mkdir(exist_ok=True)
    
    async def take_screenshot(self, element_desc: str = "", region: Optional[Dict] = None) -> str:
        """
        截图并保存（支持区域截图）
        
        Args:
            element_desc: 元素描述（用于文件名）
            region: 截图区域 {"x": int, "y": int, "width": int, "height": int}，None表示全屏
            
        Returns:
            截图文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_desc = "".join(c for c in element_desc if c.isalnum() or c in (' ', '-', '_')).strip()[:20]
        if safe_desc:
            filename = f"screenshot_{safe_desc}_{timestamp}.png"
        else:
            filename = f"screenshot_{timestamp}.png"
        
        screenshot_path = self.screenshot_dir / filename
        
        if region:
            # 区域截图：先截全屏，再裁剪
            try:
                from PIL import Image  # type: ignore
                PIL_AVAILABLE = True
            except ImportError:
                PIL_AVAILABLE = False
            
            if PIL_AVAILABLE:
                # 先截全屏
                temp_path = str(screenshot_path).replace('.png', '_full.png')
                self.mobile_client.u2.screenshot(temp_path)
                
                # 裁剪区域
                img = Image.open(temp_path)
                x = region.get('x', 0)
                y = region.get('y', 0)
                width = region.get('width', img.width)
                height = region.get('height', img.height)
                
                # 确保不越界
                x = max(0, min(x, img.width))
                y = max(0, min(y, img.height))
                width = min(width, img.width - x)
                height = min(height, img.height - y)
                
                # 裁剪
                cropped = img.crop((x, y, x + width, y + height))
                cropped.save(str(screenshot_path))
                
                # 删除临时文件
                import os
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
                print(f"  📸 区域截图: ({x}, {y}) - ({x+width}, {y+height}), 尺寸: {width}x{height}")
            else:
                # PIL不可用时，使用全屏截图
                self.mobile_client.u2.screenshot(str(screenshot_path))
                print(f"  ⚠️  PIL未安装，使用全屏截图")
        else:
            # 全屏截图
            self.mobile_client.u2.screenshot(str(screenshot_path))
        
        return str(screenshot_path)
    
    def _smart_region_selection(self, element_desc: str) -> Optional[Dict]:
        """
        智能选择截图区域（根据元素描述推断区域）
        
        Args:
            element_desc: 元素描述
            
        Returns:
            区域信息 或 None（全屏）
        """
        # 获取屏幕尺寸
        screen_info = self.mobile_client.u2.info
        screen_width = screen_info.get('displayWidth', 1080)
        screen_height = screen_info.get('displayHeight', 2400)
        
        desc_lower = element_desc.lower()
        
        # 🎯 角落区域（优先匹配，更精确）
        # 右上角区域（右上角图标、搜索图标等）
        if any(kw in desc_lower for kw in ['右上角', '上角', '搜索图标', 'search icon']):
            return {
                'x': int(screen_width * 0.7),  # 右侧30%
                'y': 0,
                'width': int(screen_width * 0.3),  # 宽度30%
                'height': int(screen_height * 0.15)  # 顶部15%
            }
        
        # 左上角区域
        if '左上角' in desc_lower:
            return {
                'x': 0,
                'y': 0,
                'width': int(screen_width * 0.3),  # 左侧30%
                'height': int(screen_height * 0.15)  # 顶部15%
            }
        
        # 右下角区域
        if '右下角' in desc_lower:
            return {
                'x': int(screen_width * 0.7),  # 右侧30%
                'y': int(screen_height * 0.85),  # 底部15%
                'width': int(screen_width * 0.3),  # 宽度30%
                'height': int(screen_height * 0.15)  # 高度15%
            }
        
        # 左下角区域
        if '左下角' in desc_lower:
            return {
                'x': 0,
                'y': int(screen_height * 0.85),  # 底部15%
                'width': int(screen_width * 0.3),  # 左侧30%
                'height': int(screen_height * 0.15)  # 高度15%
            }
        
        # 底部区域（底部导航栏、底部按钮等）
        if any(kw in desc_lower for kw in ['底部', 'bottom', '导航栏', 'tab']):
            return {
                'x': 0,
                'y': int(screen_height * 0.8),  # 底部20%
                'width': screen_width,
                'height': int(screen_height * 0.2)
            }
        
        # 顶部区域（标题栏、顶部导航、设置图标等）
        if any(kw in desc_lower for kw in ['顶部', 'top', '标题', 'header', '设置', 'settings']):
            return {
                'x': 0,
                'y': 0,
                'width': screen_width,
                'height': int(screen_height * 0.2)  # 顶部20%
            }
        
        # 中间区域（登录按钮、表单等）
        if any(kw in desc_lower for kw in ['登录', 'login', '按钮', 'button', '表单', 'form']):
            return {
                'x': 0,
                'y': int(screen_height * 0.3),
                'width': screen_width,
                'height': int(screen_height * 0.4)  # 中间40%
            }
        
        # 默认全屏
        return None
    
    def generate_analysis_prompt(self, screenshot_path: str, element_desc: str) -> str:
        """
        生成分析提示信息
        
        Args:
            screenshot_path: 截图路径
            element_desc: 元素描述
            
        Returns:
            提示信息
        """
        prompt = f"""
🎯 需要分析移动端截图并定位元素

截图路径: {screenshot_path}
要查找的元素: {element_desc}

请执行以下步骤：
1. 查看截图文件: {screenshot_path}
2. 在截图中找到元素: {element_desc}
3. 返回元素的中心点坐标，格式为JSON：
   {{"x": 100, "y": 200, "confidence": 90}}

注意：
- x, y 是元素中心点的像素坐标
- confidence 是置信度（0-100）
- 如果找不到元素，返回 {{"found": false}}
"""
        return prompt
    
    def parse_coordinate_response(self, response: str) -> Optional[Dict]:
        """
        解析坐标响应
        
        Args:
            response: Cursor AI的响应文本
            
        Returns:
            坐标信息 {"x": int, "y": int, "confidence": int} 或 None
        """
        try:
            # 尝试从响应中提取JSON
            import re
            
            # 查找JSON对象
            json_match = re.search(r'\{[^}]+\}', response)
            if json_match:
                json_str = json_match.group()
                coord = json.loads(json_str)
                
                if coord.get("found") is False:
                    return None
                
                if "x" in coord and "y" in coord:
                    return {
                        "x": int(coord["x"]),
                        "y": int(coord["y"]),
                        "confidence": coord.get("confidence", 80)
                    }
        except Exception as e:
            print(f"  ⚠️  解析坐标响应失败: {e}")
        
        return None
    
    async def analyze_with_cursor(self, element_desc: str, auto_analyze: bool = False) -> Optional[Dict]:
        """
        使用Cursor AI分析截图并返回坐标
        
        Args:
            element_desc: 元素描述
            auto_analyze: 是否自动分析（通过MCP工具调用Cursor AI）
            
        Returns:
            坐标信息 或 None
        """
        # 智能选择截图区域
        region = self._smart_region_selection(element_desc)
        
        # 截图
        screenshot_path = await self.take_screenshot(element_desc, region=region)
        
        if auto_analyze:
            # 🎯 自动分析：通过MCP工具调用Cursor AI
            # 这里需要调用MCP工具，让Cursor AI分析截图
            # 由于是在测试脚本中调用，需要通过某种机制触发Cursor AI
            print(f"\n📸 已截图: {screenshot_path}")
            print(f"🎯 自动调用Cursor AI分析截图...")
            
            # 返回截图路径，等待Cursor AI分析
            # 实际的坐标需要通过MCP工具返回
            # 🎯 创建分析请求文件，让Cursor AI自动处理
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            request_id = f"{timestamp}_{hash(element_desc) % 10000}"
            request_file = self.request_dir / f"request_{request_id}.json"
            result_file = self.result_dir / f"result_{request_id}.json"
            
            # 尝试获取测试脚本路径
            script_path = None
            try:
                frame = inspect.currentframe()
                while frame:
                    filename = frame.f_globals.get('__file__', '')
                    if filename and 'test_' in filename and filename.endswith('.py'):
                        script_path = filename
                        break
                    frame = frame.f_back
            except:
                pass
            
            request_data = {
                "request_id": request_id,
                "screenshot_path": screenshot_path,
                "element_desc": element_desc,
                "region": region,
                "timestamp": timestamp,
                "script_path": script_path,
                "status": "pending"
            }
            
            # 写入请求文件
            with open(request_file, 'w', encoding='utf-8') as f:
                json.dump(request_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n📸 已截图: {screenshot_path}")
            print(f"📝 已创建分析请求: {request_file}")
            print(f"🎯 等待Cursor AI分析...")
            print(f"💡 Cursor AI会自动读取请求文件并分析截图")
            
            # 等待Cursor AI分析（轮询结果文件）
            # 🎯 优化：缩短等待时间，避免阻塞过久
            max_wait = 10  # 最多等待10秒（原30秒太长）
            wait_interval = 0.5  # 每0.5秒检查一次（提高响应速度）
            waited = 0
            
            while waited < max_wait:
                if result_file.exists():
                    try:
                        with open(result_file, 'r', encoding='utf-8') as f:
                            result_data = json.load(f)
                        
                        if result_data.get('status') == 'completed':
                            coord = result_data.get('coordinate')
                            if coord and 'x' in coord and 'y' in coord:
                                print(f"✅ Cursor AI分析完成，坐标: ({coord['x']}, {coord['y']})")
                                
                                # 🎯 可选：更新测试脚本（重新读取请求文件获取脚本路径）
                                try:
                                    with open(request_file, 'r', encoding='utf-8') as rf:
                                        request_data = json.load(rf)
                                    script_path = request_data.get('script_path')
                                    self._update_test_script(element_desc, coord, script_path)
                                except Exception as e:
                                    print(f"  ⚠️  更新脚本失败: {e}")
                                
                                # 清理文件
                                request_file.unlink(missing_ok=True)
                                result_file.unlink(missing_ok=True)
                                return {
                                    "screenshot_path": screenshot_path,
                                    "coordinate": coord,
                                    "confidence": coord.get('confidence', 80),
                                    "status": "completed"
                                }
                    except Exception as e:
                        print(f"  ⚠️  读取结果文件失败: {e}")
                
                await asyncio.sleep(wait_interval)
                waited += wait_interval
                if waited % 5 == 0:
                    print(f"  ⏳ 等待中... ({waited}/{max_wait}秒)")
            
            print(f"  ⚠️  超时：Cursor AI未在{max_wait}秒内返回结果")
            return {
                "screenshot_path": screenshot_path,
                "status": "timeout",
                "request_file": str(request_file),
                "result_file": str(result_file)
            }
        else:
            # 手动分析：生成提示信息
            prompt = self.generate_analysis_prompt(screenshot_path, element_desc)
            
            print(f"\n📸 已截图: {screenshot_path}")
            print(f"🎯 请Cursor AI分析截图，查找元素: {element_desc}")
            print(f"\n{prompt}\n")
            
            return {
                "screenshot_path": screenshot_path,
                "prompt": prompt,
                "status": "waiting_for_ai_analysis"
            }
    
    def _update_test_script(self, element_desc: str, coordinate: Dict, script_path: Optional[str] = None):
        """
        更新测试脚本，添加坐标信息
        
        Args:
            element_desc: 元素描述
            coordinate: 坐标信息 {"x": int, "y": int, "confidence": int}
            script_path: 脚本路径（如果为None，尝试自动查找）
        """
        if not script_path:
            return
        
        try:
            from mobile_mcp.core.locator.script_updater import ScriptUpdater
            updater = ScriptUpdater(script_path)
            success = updater.update_with_coordinate(element_desc, coordinate, method='comment')
            if success:
                print(f"  ✅ 测试脚本已更新: {script_path}")
            else:
                print(f"  ⚠️  更新测试脚本失败")
        except Exception as e:
            print(f"  ⚠️  更新测试脚本异常: {e}")
            import traceback
            traceback.print_exc()

