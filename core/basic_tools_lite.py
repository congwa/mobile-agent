#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精简版基础工具 - 纯 MCP，依赖 Cursor 视觉能力

特点：
- 不需要 AI 密钥
- 核心功能精简
- 保留 pytest 脚本生成
- 支持操作历史记录
- Token 优化模式（省钱）
"""

import asyncio
import time
import re
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Token 优化配置（只精简格式，不限制数量，确保准确度）
try:
    from mobile_mcp.config import Config
    TOKEN_OPTIMIZATION = Config.TOKEN_OPTIMIZATION_ENABLED
    MAX_ELEMENTS = Config.MAX_ELEMENTS_RETURN
    MAX_SOM_ELEMENTS = Config.MAX_SOM_ELEMENTS_RETURN
    COMPACT_RESPONSE = Config.COMPACT_RESPONSE
except ImportError:
    TOKEN_OPTIMIZATION = True
    MAX_ELEMENTS = 0  # 0 = 不限制
    MAX_SOM_ELEMENTS = 0  # 0 = 不限制
    COMPACT_RESPONSE = True


class BasicMobileToolsLite:
    """精简版移动端工具"""
    
    def __init__(self, mobile_client):
        self.client = mobile_client
        
        # 截图目录
        project_root = Path(__file__).parent.parent
        self.screenshot_dir = project_root / "screenshots"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        # 操作历史（用于生成 pytest 脚本）
        self.operation_history: List[Dict] = []
        
        # 目标应用包名（用于监测应用跳转）
        self.target_package: Optional[str] = None
    
    def _is_ios(self) -> bool:
        """判断当前是否为 iOS 平台"""
        return getattr(self.client, 'platform', 'android') == 'ios'
    
    def _get_ios_client(self):
        """获取 iOS 客户端"""
        if hasattr(self.client, '_ios_client') and self.client._ios_client:
            return self.client._ios_client
        if hasattr(self.client, 'wda') and self.client.wda:
            return self.client.wda
        return None
    
    def _record_operation(self, action: str, **kwargs):
        """记录操作到历史（旧接口，保持兼容）"""
        record = {
            'action': action,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        self.operation_history.append(record)
    
    def _record_click(self, locator_type: str, locator_value: str, 
                      x_percent: float = 0, y_percent: float = 0,
                      element_desc: str = '', locator_attr: str = ''):
        """记录点击操作（标准格式）
        
        Args:
            locator_type: 定位类型 'text' | 'id' | 'percent' | 'coords'
            locator_value: 定位值（文本内容、resource-id、或坐标描述）
            x_percent: 百分比 X 坐标（兜底方案）
            y_percent: 百分比 Y 坐标（兜底方案）
            element_desc: 元素描述（用于脚本注释）
            locator_attr: Android 选择器属性 'text'|'textContains'|'description'|'descriptionContains'
        """
        record = {
            'action': 'click',
            'timestamp': datetime.now().isoformat(),
            'locator_type': locator_type,
            'locator_value': locator_value,
            'locator_attr': locator_attr or locator_type,  # 默认与 type 相同
            'x_percent': x_percent,
            'y_percent': y_percent,
            'element_desc': element_desc or locator_value,
        }
        self.operation_history.append(record)
    
    def _record_long_press(self, locator_type: str, locator_value: str,
                           duration: float = 1.0,
                           x_percent: float = 0, y_percent: float = 0,
                           element_desc: str = '', locator_attr: str = ''):
        """记录长按操作（标准格式）"""
        record = {
            'action': 'long_press',
            'timestamp': datetime.now().isoformat(),
            'locator_type': locator_type,
            'locator_value': locator_value,
            'locator_attr': locator_attr or locator_type,
            'duration': duration,
            'x_percent': x_percent,
            'y_percent': y_percent,
            'element_desc': element_desc or locator_value,
        }
        self.operation_history.append(record)
    
    def _record_input(self, text: str, locator_type: str = '', locator_value: str = '',
                      x_percent: float = 0, y_percent: float = 0):
        """记录输入操作（标准格式）"""
        record = {
            'action': 'input',
            'timestamp': datetime.now().isoformat(),
            'text': text,
            'locator_type': locator_type,
            'locator_value': locator_value,
            'x_percent': x_percent,
            'y_percent': y_percent,
        }
        self.operation_history.append(record)
    
    def _record_swipe(self, direction: str):
        """记录滑动操作"""
        record = {
            'action': 'swipe',
            'timestamp': datetime.now().isoformat(),
            'direction': direction,
        }
        self.operation_history.append(record)
    
    def _record_key(self, key: str):
        """记录按键操作"""
        record = {
            'action': 'press_key',
            'timestamp': datetime.now().isoformat(),
            'key': key,
        }
        self.operation_history.append(record)
    
    def _get_current_package(self) -> Optional[str]:
        """获取当前前台应用的包名/Bundle ID"""
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    app_info = ios_client.wda.session().app_current()
                    return app_info.get('bundleId')
            else:
                info = self.client.u2.app_current()
                return info.get('package')
        except Exception:
            return None

    def _normalize_resource_id(self, resource_id: str) -> str:
        """标准化 resource-id，支持前端只传简写 id 时自动补全包名

        约定：
        - Android:
            - 如果传入的是完整 id（包含 ':' 或 '/'），直接返回
            - 如果是简写（如 'qylt_search_input_layout'），自动补全为
              '{package}:id/{resource_id}'，package 优先使用 target_package，
              否则使用当前前台应用包名
        - iOS: 直接原样返回
        """
        # iOS 不做处理，保持与 WDA 一致
        if self._is_ios():
            return resource_id

        # 已经是完整 id 或者包含路径信息时，不再修改
        if ":" in resource_id or "/" in resource_id:
            return resource_id

        # 尝试获取包名：优先使用目标应用包名，其次当前前台应用
        package = getattr(self, "target_package", None) or self._get_current_package()
        if not package:
            # 没有包名信息时，回退为原值，避免误拼接错误包名
            return resource_id

        return f"{package}:id/{resource_id}"
    
    def _check_app_switched(self) -> Dict:
        """检查是否已跳出目标应用
        
        Returns:
            {
                'switched': bool,  # 是否跳转
                'current_package': str,  # 当前应用包名
                'target_package': str,  # 目标应用包名
                'message': str  # 提示信息
            }
        """
        if not self.target_package:
            return {
                'switched': False,
                'current_package': None,
                'target_package': None,
                'message': '⚠️ 未设置目标应用，无法监测应用跳转'
            }
        
        current = self._get_current_package()
        if not current:
            return {
                'switched': False,
                'current_package': None,
                'target_package': self.target_package,
                'message': '⚠️ 无法获取当前应用包名'
            }
        
        if current != self.target_package:
            return {
                'switched': True,
                'current_package': current,
                'target_package': self.target_package,
                'message': f'⚠️ 应用已跳转！当前应用: {current}，目标应用: {self.target_package}'
            }
        
        return {
            'switched': False,
            'current_package': current,
            'target_package': self.target_package,
            'message': f'✅ 仍在目标应用: {current}'
        }
    
    def _return_to_target_app(self) -> Dict:
        """返回到目标应用
        
        策略：
        1. 先按返回键（可能关闭弹窗或返回上一页）
        2. 如果还在其他应用，启动目标应用
        3. 验证是否成功返回
        
        Returns:
            {
                'success': bool,
                'message': str,
                'method': str  # 使用的返回方法
            }
        """
        if not self.target_package:
            return {
                'success': False,
                'message': '❌ 未设置目标应用，无法返回',
                'method': None
            }
        
        try:
            # 先检查当前应用
            current = self._get_current_package()
            if not current:
                return {
                    'success': False,
                    'message': '❌ 无法获取当前应用包名',
                    'method': None
                }
            
            # 如果已经在目标应用，不需要返回
            if current == self.target_package:
                return {
                    'success': True,
                    'message': f'✅ 已在目标应用: {self.target_package}',
                    'method': 'already_in_target'
                }
            
            # 策略1: 先按返回键（可能关闭弹窗或返回）
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    # iOS 返回键
                    ios_client.wda.press('home')  # iOS 先按 home
                    time.sleep(0.5)
                    # 然后启动目标应用
                    ios_client.wda.app_activate(self.target_package)
                else:
                    return {
                        'success': False,
                        'message': '❌ iOS 客户端未初始化',
                        'method': None
                    }
            else:
                # Android: 先按返回键
                self.client.u2.press('back')
                time.sleep(0.5)
                
                # 检查是否已返回
                current = self._get_current_package()
                if current == self.target_package:
                    return {
                        'success': True,
                        'message': f'✅ 已返回目标应用: {self.target_package}（通过返回键）',
                        'method': 'back_key'
                    }
                
                # 如果还在其他应用，启动目标应用
                self.client.u2.app_start(self.target_package)
                time.sleep(1)
            
            # 验证是否成功返回
            current = self._get_current_package()
            if current == self.target_package:
                return {
                    'success': True,
                    'message': f'✅ 已返回目标应用: {self.target_package}',
                    'method': 'app_start'
                }
            else:
                return {
                    'success': False,
                    'message': f'❌ 返回失败：当前应用仍为 {current}，期望 {self.target_package}',
                    'method': 'app_start'
                }
        except Exception as e:
            return {
                'success': False,
                'message': f'❌ 返回目标应用失败: {e}',
                'method': None
            }
    
    
    # ==================== 截图 ====================
    
    def take_screenshot(self, description: str = "", compress: bool = True, 
                        max_width: int = 720, quality: int = 75,
                        crop_x: int = 0, crop_y: int = 0, crop_size: int = 0) -> Dict:
        """截图（支持压缩和局部裁剪）
        
        压缩原理：
        1. 先截取原始 PNG 图片
        2. 缩小尺寸（如 1080p → 720p）
        3. 转换为 JPEG 格式 + 降低质量（如 100% → 75%）
        4. 最终文件从 2MB 压缩到约 80KB（节省 96%）
        
        局部裁剪（用于精确识别小元素）：
        - 第一次全屏截图，AI 返回大概坐标
        - 第二次传入 crop_x, crop_y, crop_size 截取局部区域
        - 局部区域不压缩，保持清晰度，AI 可精确识别
        - 返回 crop_offset_x/y 用于坐标换算
        
        Args:
            description: 截图描述（可选）
            compress: 是否压缩（默认 True，推荐开启省 token）
            max_width: 压缩后最大宽度（默认 720，对 AI 识别足够）
            quality: JPEG 质量 1-100（默认 75，肉眼几乎看不出区别）
            crop_x: 裁剪中心点 X 坐标（屏幕坐标，0 表示不裁剪）
            crop_y: 裁剪中心点 Y 坐标（屏幕坐标，0 表示不裁剪）
            crop_size: 裁剪区域大小（默认 0 不裁剪，推荐 200-400）
        
        压缩效果示例：
            原图 PNG: 2048KB
            压缩后 JPEG (720p, 75%): ~80KB
            节省: 96%
        """
        try:
            from PIL import Image
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            platform = "ios" if self._is_ios() else "android"
            
            # 第1步：截图保存为临时 PNG
            temp_filename = f"temp_{timestamp}.png"
            temp_path = self.screenshot_dir / temp_filename
            
            # 获取屏幕尺寸并截图
            screen_width, screen_height = 0, 0
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    ios_client.wda.screenshot(str(temp_path))
                    size = ios_client.wda.window_size()
                    screen_width, screen_height = size[0], size[1]
                else:
                    return {"success": False, "msg": "iOS未初始化"}
            else:
                self.client.u2.screenshot(str(temp_path))
                info = self.client.u2.info
                screen_width = info.get('displayWidth', 0)
                screen_height = info.get('displayHeight', 0)
            
            original_size = temp_path.stat().st_size
            
            # 第2步：打开图片
            img = Image.open(temp_path)
            
            # 第2.5步：局部裁剪（如果指定了裁剪参数）
            crop_offset_x, crop_offset_y = 0, 0
            is_cropped = False
            
            if crop_x > 0 and crop_y > 0 and crop_size > 0:
                # 计算裁剪区域（以 crop_x, crop_y 为中心）
                half_size = crop_size // 2
                left = max(0, crop_x - half_size)
                top = max(0, crop_y - half_size)
                right = min(img.width, crop_x + half_size)
                bottom = min(img.height, crop_y + half_size)
                
                # 记录偏移量（用于坐标换算）
                crop_offset_x = left
                crop_offset_y = top
                
                # 裁剪
                img = img.crop((left, top, right, bottom))
                is_cropped = True
            
            # ========== 情况1：局部裁剪截图（不压缩，保持清晰度）==========
            if is_cropped:
                # 生成文件名
                if description:
                    safe_desc = re.sub(r'[^\w\s-]', '', description).strip().replace(' ', '_')
                    filename = f"screenshot_{platform}_crop_{safe_desc}_{timestamp}.png"
                else:
                    filename = f"screenshot_{platform}_crop_{timestamp}.png"
                
                final_path = self.screenshot_dir / filename
                
                # 保存为 PNG（保持清晰度）
                img.save(str(final_path), "PNG")
                
                # 删除临时文件
                temp_path.unlink()
                
                cropped_size = final_path.stat().st_size
                
                # 返回结果
                return {
                    "success": True,
                    "screenshot_path": str(final_path),
                    "image_width": img.width,
                    "image_height": img.height,
                    "crop_offset_x": crop_offset_x,
                    "crop_offset_y": crop_offset_y
                }
            
            # ========== 情况2：全屏压缩截图 ==========
            elif compress:
                # 🔴 关键：记录原始图片尺寸（用于坐标转换）
                # 注意：截图尺寸可能和 u2.info 的 displayWidth 不一致！
                original_img_width = img.width
                original_img_height = img.height
                
                # 第3步：缩小尺寸（保持宽高比）
                image_width, image_height = img.width, img.height
                
                if img.width > max_width:
                    ratio = max_width / img.width
                    new_w = max_width
                    new_h = int(img.height * ratio)
                    # 兼容不同版本的 Pillow
                    try:
                        resample = Image.Resampling.LANCZOS
                    except AttributeError:
                        try:
                            resample = Image.LANCZOS
                        except AttributeError:
                            resample = Image.ANTIALIAS
                    img = img.resize((new_w, new_h), resample)
                    image_width, image_height = new_w, new_h
                
                # 生成文件名（JPEG 格式）
                if description:
                    safe_desc = re.sub(r'[^\w\s-]', '', description).strip().replace(' ', '_')
                    filename = f"screenshot_{platform}_{safe_desc}_{timestamp}.jpg"
                else:
                    filename = f"screenshot_{platform}_{timestamp}.jpg"
                
                final_path = self.screenshot_dir / filename
                
                # 保存为 JPEG（处理透明通道）
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert("RGB")
                
                img.save(str(final_path), "JPEG", quality=quality)
                temp_path.unlink()
                
                compressed_size = final_path.stat().st_size
                saved_percent = (1 - compressed_size / original_size) * 100
                
                # 返回结果
                return {
                    "success": True,
                    "screenshot_path": str(final_path),
                    "image_width": image_width,
                    "image_height": image_height,
                    "original_img_width": original_img_width,
                    "original_img_height": original_img_height
                }
            
            # ========== 情况3：全屏不压缩截图 ==========
            else:
                if description:
                    safe_desc = re.sub(r'[^\w\s-]', '', description).strip().replace(' ', '_')
                    filename = f"screenshot_{platform}_{safe_desc}_{timestamp}.png"
                else:
                    filename = f"screenshot_{platform}_{timestamp}.png"
                
                final_path = self.screenshot_dir / filename
                temp_path.rename(final_path)
                
                # 返回结果（不压缩时尺寸相同）
                return {
                    "success": True,
                    "screenshot_path": str(final_path),
                    "image_width": img.width,
                    "image_height": img.height
                }
        except ImportError:
            # 如果没有 PIL，回退到原始方式（不压缩）
            return self._take_screenshot_no_compress(description)
        except Exception as e:
            return {"success": False, "message": f"❌ 截图失败: {e}"}
    
    def take_screenshot_with_grid(self, grid_size: int = 100, show_popup_hints: bool = False) -> Dict:
        """截图并添加网格坐标标注（用于精确定位元素）
        
        在截图上绘制网格线和坐标刻度，帮助快速定位元素位置。
        如果检测到弹窗，会标注弹窗区域和可能的关闭按钮位置。
        
        Args:
            grid_size: 网格间距（像素），默认 100。建议值：50-200
            show_popup_hints: 是否显示弹窗关闭按钮提示位置，默认 True
        
        Returns:
            包含标注截图路径和弹窗信息的字典
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
            import re
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            platform = "ios" if self._is_ios() else "android"
            
            # 第1步：截图
            temp_filename = f"temp_grid_{timestamp}.png"
            temp_path = self.screenshot_dir / temp_filename
            
            screen_width, screen_height = 0, 0
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    ios_client.wda.screenshot(str(temp_path))
                    size = ios_client.wda.window_size()
                    screen_width, screen_height = size[0], size[1]
                else:
                    return {"success": False, "msg": "iOS未初始化"}
            else:
                self.client.u2.screenshot(str(temp_path))
                info = self.client.u2.info
                screen_width = info.get('displayWidth', 720)
                screen_height = info.get('displayHeight', 1280)
            
            img = Image.open(temp_path)
            draw = ImageDraw.Draw(img, 'RGBA')
            
            # 尝试加载字体
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
                font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 11)
            except:
                font = ImageFont.load_default()
                font_small = font
            
            img_width, img_height = img.size
            
            # 第2步：绘制网格线和坐标
            grid_color = (255, 0, 0, 80)  # 半透明红色
            text_color = (255, 0, 0, 200)  # 红色文字
            
            # 绘制垂直网格线
            for x in range(0, img_width, grid_size):
                draw.line([(x, 0), (x, img_height)], fill=grid_color, width=1)
                # 顶部标注 X 坐标
                draw.text((x + 2, 2), str(x), fill=text_color, font=font_small)
            
            # 绘制水平网格线
            for y in range(0, img_height, grid_size):
                draw.line([(0, y), (img_width, y)], fill=grid_color, width=1)
                # 左侧标注 Y 坐标
                draw.text((2, y + 2), str(y), fill=text_color, font=font_small)
            
            # 第3步：检测弹窗并标注（使用严格的置信度检测，避免误识别）
            popup_info = None
            close_positions = []
            
            if show_popup_hints and not self._is_ios():
                try:
                    import xml.etree.ElementTree as ET
                    xml_string = self.client.u2.dump_hierarchy(compressed=False)
                    root = ET.fromstring(xml_string)
                    
                    # 使用严格的弹窗检测（置信度 >= 0.6 才认为是弹窗）
                    popup_bounds, popup_confidence = self._detect_popup_with_confidence(
                        root, screen_width, screen_height
                    )
                    
                    if popup_bounds and popup_confidence >= 0.6:
                        px1, py1, px2, py2 = popup_bounds
                        popup_width = px2 - px1
                        popup_height = py2 - py1
                        
                        # 绘制弹窗边框（蓝色）
                        draw.rectangle([px1, py1, px2, py2], outline=(0, 100, 255, 200), width=3)
                        draw.text((px1 + 5, py1 + 5), f"弹窗区域", fill=(0, 100, 255), font=font)
                        
                        # 计算可能的 X 按钮位置（基于弹窗尺寸动态计算，适配不同分辨率）
                        offset_x = max(25, int(popup_width * 0.05))  # 宽度的5%，最小25px
                        offset_y = max(25, int(popup_height * 0.04))  # 高度的4%，最小25px
                        outer_offset = max(15, int(popup_width * 0.025))  # 外部偏移
                        
                        close_positions = [
                            {"name": "右上角内", "x": px2 - offset_x, "y": py1 + offset_y, "priority": 1},
                            {"name": "右上角外", "x": px2 + outer_offset, "y": py1 - outer_offset, "priority": 2},
                            {"name": "正上方", "x": (px1 + px2) // 2, "y": py1 - offset_y, "priority": 3},
                            {"name": "底部下方", "x": (px1 + px2) // 2, "y": py2 + offset_y, "priority": 4},
                        ]
                        
                        # 绘制可能的 X 按钮位置（绿色圆圈 + 数字）
                        for i, pos in enumerate(close_positions):
                            cx, cy = pos["x"], pos["y"]
                            if 0 <= cx <= img_width and 0 <= cy <= img_height:
                                # 绿色圆圈
                                draw.ellipse([cx-15, cy-15, cx+15, cy+15], 
                                           outline=(0, 255, 0, 200), width=2)
                                # 数字标注
                                draw.text((cx-5, cy-8), str(i+1), fill=(0, 255, 0), font=font)
                                # 坐标标注
                                draw.text((cx+18, cy-8), f"({cx},{cy})", fill=(0, 255, 0), font=font_small)
                        
                        popup_info = {
                            "bounds": f"[{px1},{py1}][{px2},{py2}]",
                            "width": px2 - px1,
                            "height": py2 - py1,
                            "close_positions": close_positions
                        }
                
                except Exception as e:
                    pass  # 弹窗检测失败不影响主功能
            
            # 第4步：保存标注后的截图
            filename = f"screenshot_{platform}_grid_{timestamp}.jpg"
            final_path = self.screenshot_dir / filename
            
            # 转换为 RGB 并保存
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert("RGB")
            
            img.save(str(final_path), "JPEG", quality=85)
            temp_path.unlink()
            
            result = {
                "success": True,
                "screenshot_path": str(final_path),
                "image_width": img_width,
                "image_height": img_height,
                "grid_size": grid_size
            }
            
            if popup_info:
                result["popup"] = popup_info["bounds"]
                # 只返回前3个最可能的关闭按钮位置
                if close_positions:
                    result["close_hints"] = [(p['x'], p['y']) for p in close_positions[:3]]
            
            return result
            
        except ImportError:
            return {"success": False, "message": "❌ 需要安装 Pillow: pip install Pillow"}
        except Exception as e:
            return {"success": False, "message": f"❌ 网格截图失败: {e}"}
    
    def take_screenshot_with_som(self) -> Dict:
        """Set-of-Mark 截图：给每个可点击元素标上数字（超级好用！）
        
        在截图上给每个可点击元素画框并标上数字编号。
        AI 看图后直接说"点击 3 号"，然后调用 click_by_som(3) 即可。
        
        Returns:
            包含标注截图和元素列表的字典
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
            import re
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            platform = "ios" if self._is_ios() else "android"
            
            # 第1步：截图
            temp_filename = f"temp_som_{timestamp}.png"
            temp_path = self.screenshot_dir / temp_filename
            
            screen_width, screen_height = 0, 0
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    ios_client.wda.screenshot(str(temp_path))
                    size = ios_client.wda.window_size()
                    screen_width, screen_height = size[0], size[1]
                else:
                    return {"success": False, "msg": "iOS未初始化"}
            else:
                self.client.u2.screenshot(str(temp_path))
                info = self.client.u2.info
                screen_width = info.get('displayWidth', 720)
                screen_height = info.get('displayHeight', 1280)
            
            img = Image.open(temp_path)
            draw = ImageDraw.Draw(img, 'RGBA')
            img_width, img_height = img.size
            
            # 尝试加载字体
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
                font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
            except:
                font = ImageFont.load_default()
                font_small = font
            
            # 第2步：获取所有可点击元素
            elements = []
            if self._is_ios():
                # iOS 暂不支持
                pass
            else:
                try:
                    import xml.etree.ElementTree as ET
                    xml_string = self.client.u2.dump_hierarchy(compressed=False)
                    root = ET.fromstring(xml_string)
                    
                    for elem in root.iter():
                        clickable = elem.attrib.get('clickable', 'false') == 'true'
                        bounds_str = elem.attrib.get('bounds', '')
                        text = elem.attrib.get('text', '')
                        content_desc = elem.attrib.get('content-desc', '')
                        resource_id = elem.attrib.get('resource-id', '')
                        class_name = elem.attrib.get('class', '')
                        
                        if not clickable or not bounds_str:
                            continue
                        
                        match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
                        if not match:
                            continue
                        
                        x1, y1, x2, y2 = map(int, match.groups())
                        width = x2 - x1
                        height = y2 - y1
                        
                        # 过滤太小或太大的元素
                        if width < 20 or height < 20:
                            continue
                        if width >= screen_width * 0.98 and height >= screen_height * 0.5:
                            continue  # 全屏或大面积容器
                        
                        center_x = (x1 + x2) // 2
                        center_y = (y1 + y2) // 2
                        
                        # 生成描述
                        desc = text or content_desc or resource_id.split('/')[-1] if resource_id else class_name.split('.')[-1]
                        if len(desc) > 20:
                            desc = desc[:17] + "..."
                        
                        elements.append({
                            'bounds': (x1, y1, x2, y2),
                            'center': (center_x, center_y),
                            'text': text,
                            'desc': desc,
                            'resource_id': resource_id
                        })
                except Exception as e:
                    pass
            
            # 第3步：在截图上标注元素
            # 颜色列表（循环使用）
            colors = [
                (255, 0, 0),      # 红
                (0, 255, 0),      # 绿
                (0, 100, 255),    # 蓝
                (255, 165, 0),    # 橙
                (255, 0, 255),    # 紫
                (0, 255, 255),    # 青
            ]
            
            som_elements = []  # 保存标注信息，供 click_by_som 使用
            
            for i, elem in enumerate(elements):
                x1, y1, x2, y2 = elem['bounds']
                cx, cy = elem['center']
                color = colors[i % len(colors)]
                
                # 画边框
                draw.rectangle([x1, y1, x2, y2], outline=color + (200,), width=2)
                
                # 画编号标签背景
                label = str(i + 1)
                label_w, label_h = 20, 18
                label_x = x1
                label_y = max(0, y1 - label_h - 2)
                draw.rectangle([label_x, label_y, label_x + label_w, label_y + label_h], 
                             fill=color + (220,))
                
                # 画编号文字
                draw.text((label_x + 4, label_y + 1), label, fill=(255, 255, 255), font=font_small)
                
                som_elements.append({
                    'index': i + 1,
                    'center': (cx, cy),
                    'bounds': f"[{x1},{y1}][{x2},{y2}]",
                    'desc': elem['desc'],
                    'text': elem.get('text', ''),
                    'resource_id': elem.get('resource_id', '')
                })
            
            # 第3.5步：检测弹窗区域（使用严格的置信度检测，避免误识别普通页面）
            popup_bounds = None
            popup_confidence = 0
            
            if not self._is_ios():
                try:
                    # 使用严格的弹窗检测（置信度 >= 0.6 才认为是弹窗）
                    popup_bounds, popup_confidence = self._detect_popup_with_confidence(
                        root, screen_width, screen_height
                    )
                    
                    # 如果检测到弹窗，标注弹窗边界（不再猜测X按钮位置）
                    if popup_bounds and popup_confidence >= 0.6:
                        px1, py1, px2, py2 = popup_bounds
                        
                        # 只画弹窗边框（蓝色），不再猜测X按钮位置
                        draw.rectangle([px1, py1, px2, py2], outline=(0, 150, 255, 180), width=3)
                        
                        # 在弹窗边框上标注提示文字
                        try:
                            draw.text((px1+5, py1-25), "弹窗区域", fill=(0, 150, 255), font=font_small)
                        except:
                            pass
                
                except Exception as e:
                    pass  # 弹窗检测失败不影响主功能
            
            # 保存到实例变量，供 click_by_som 使用
            self._som_elements = som_elements
            
            # 第4步：保存标注后的截图
            filename = f"screenshot_{platform}_som_{timestamp}.jpg"
            final_path = self.screenshot_dir / filename
            
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert("RGB")
            
            img.save(str(final_path), "JPEG", quality=85)
            temp_path.unlink()
            
            # 返回结果（Token 优化：不返回 elements 列表，已存储在 self._som_elements）
            return {
                "success": True,
                "screenshot_path": str(final_path),
                "screen_width": screen_width,
                "screen_height": screen_height,
                "element_count": len(som_elements),
                "popup_detected": popup_bounds is not None,
                "hint": "查看截图上的编号，用 click_by_som(编号) 点击"
            }
            
        except ImportError:
            return {"success": False, "message": "❌ 需要安装 Pillow: pip install Pillow"}
        except Exception as e:
            return {"success": False, "message": f"❌ SoM 截图失败: {e}"}
    
    def click_by_som(self, index: int) -> Dict:
        """根据 SoM 编号点击元素
        
        配合 take_screenshot_with_som 使用。
        看图后直接说"点击 3 号"，调用此函数即可。
        
        Args:
            index: 元素编号（从 1 开始）
        
        Returns:
            点击结果
        """
        try:
            if not hasattr(self, '_som_elements') or not self._som_elements:
                return {
                    "success": False, 
                    "message": "❌ 请先调用 mobile_screenshot_with_som 获取元素列表"
                }
            
            # 查找对应编号的元素
            target = None
            for elem in self._som_elements:
                if elem['index'] == index:
                    target = elem
                    break
            
            if not target:
                return {
                    "success": False,
                    "message": f"❌ 未找到编号 {index} 的元素，有效范围: 1-{len(self._som_elements)}"
                }
            
            # 点击
            cx, cy = target['center']
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    ios_client.wda.click(cx, cy)
                    size = ios_client.wda.window_size()
                    screen_width, screen_height = size[0], size[1]
            else:
                self.client.u2.click(cx, cy)
                info = self.client.u2.info
                screen_width = info.get('displayWidth', 0)
                screen_height = info.get('displayHeight', 0)

            time.sleep(0.3)
            
            # 计算百分比坐标用于跨设备兼容
            x_percent = round(cx / screen_width * 100, 1) if screen_width > 0 else 0
            y_percent = round(cy / screen_height * 100, 1) if screen_height > 0 else 0
            
            # 使用标准记录格式
            # 优先使用元素的文本/描述信息，这样生成脚本时可以用文本定位
            elem_text = target.get('text', '')
            elem_id = target.get('resource_id', '')
            elem_desc = target.get('desc', '')
            
            if elem_text and not elem_text.startswith('['):  # 排除类似 "[可点击]" 的描述
                # 有文本，使用文本定位
                self._record_click('text', elem_text, x_percent, y_percent,
                                  element_desc=f"[{index}]{elem_desc}", locator_attr='text')
            elif elem_id:
                # 有 resource-id，使用 ID 定位
                self._record_click('id', elem_id, x_percent, y_percent,
                                  element_desc=f"[{index}]{elem_desc}")
            else:
                # 都没有，使用百分比定位
                self._record_click('percent', f"{x_percent}%,{y_percent}%", x_percent, y_percent,
                                  element_desc=f"[{index}]{elem_desc}")

            return {
                "success": True,
                "clicked": {
                    "index": index,
                    "desc": target['desc'],
                    "coords": (cx, cy),
                    "bounds": target['bounds']
                }
            }
            
        except Exception as e:
            return {"success": False, "message": f"❌ 点击失败: {e}\n💡 如果页面已变化，请重新调用 mobile_screenshot_with_som 刷新元素列表"}
    
    def _take_screenshot_no_compress(self, description: str = "") -> Dict:
        """截图（不压缩，PIL 不可用时的备用方案）"""
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            platform = "ios" if self._is_ios() else "android"
            
            if description:
                safe_desc = re.sub(r'[^\w\s-]', '', description).strip().replace(' ', '_')
                filename = f"screenshot_{platform}_{safe_desc}_{timestamp}.png"
            else:
                filename = f"screenshot_{platform}_{timestamp}.png"
            
            screenshot_path = self.screenshot_dir / filename
            
            width, height = 0, 0
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    ios_client.wda.screenshot(str(screenshot_path))
                    size = ios_client.wda.window_size()
                    width, height = size[0], size[1]
                else:
                    return {"success": False, "msg": "iOS未初始化"}
            else:
                self.client.u2.screenshot(str(screenshot_path))
                info = self.client.u2.info
                width = info.get('displayWidth', 0)
                height = info.get('displayHeight', 0)
            
            # 不压缩时，图片尺寸 = 屏幕尺寸
            return {
                "success": True,
                "screenshot_path": str(screenshot_path),
                "screen_width": width,
                "screen_height": height,
                "image_width": width,
                "image_height": height,
                "message": f"📸 截图已保存: {screenshot_path}\n"
                          f"📐 屏幕尺寸: {width}x{height}\n"
                          f"⚠️ 未压缩（PIL 未安装），建议安装: pip install Pillow"
            }
        except Exception as e:
            return {"success": False, "message": f"❌ 截图失败: {e}"}
    
    def get_screen_size(self) -> Dict:
        """获取屏幕尺寸"""
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    size = ios_client.wda.window_size()
                    return {
                        "success": True,
                        "width": size[0],
                        "height": size[1],
                        "size": f"{size[0]}x{size[1]}"
                    }
            else:
                info = self.client.u2.info
                width = info.get('displayWidth', 0)
                height = info.get('displayHeight', 0)
                return {
                    "success": True,
                    "width": width,
                    "height": height,
                    "size": f"{width}x{height}"
                }
        except Exception as e:
            return {"success": False, "message": f"❌ 获取屏幕尺寸失败: {e}"}
    
    # ==================== 点击操作 ====================
    
    def click_at_coords(self, x: int, y: int, image_width: int = 0, image_height: int = 0,
                        crop_offset_x: int = 0, crop_offset_y: int = 0,
                        original_img_width: int = 0, original_img_height: int = 0) -> Dict:
        """点击坐标（核心功能，支持自动坐标转换）
        
        Args:
            x: X 坐标（来自截图分析或屏幕坐标）
            y: Y 坐标（来自截图分析或屏幕坐标）
            image_width: 压缩后图片宽度（AI 看到的图片尺寸）
            image_height: 压缩后图片高度（AI 看到的图片尺寸）
            crop_offset_x: 局部截图的 X 偏移量（局部截图时传入）
            crop_offset_y: 局部截图的 Y 偏移量（局部截图时传入）
            original_img_width: 截图原始宽度（压缩前的尺寸，用于精确转换）
            original_img_height: 截图原始高度（压缩前的尺寸，用于精确转换）
        
        坐标转换说明：
            1. 全屏压缩截图：AI 坐标 → 原图坐标（基于 image/original_img 比例）
            2. 局部裁剪截图：AI 坐标 + 偏移量 = 屏幕坐标
        """
        try:
            # 获取屏幕尺寸
            screen_width, screen_height = 0, 0
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    size = ios_client.wda.window_size()
                    screen_width, screen_height = size[0], size[1]
                else:
                    return {"success": False, "msg": "iOS未初始化"}
            else:
                info = self.client.u2.info
                screen_width = info.get('displayWidth', 0)
                screen_height = info.get('displayHeight', 0)
            
            # 🎯 坐标转换
            original_x, original_y = x, y
            converted = False
            conversion_type = ""
            
            # 情况1：局部裁剪截图 - 加上偏移量
            if crop_offset_x > 0 or crop_offset_y > 0:
                x = x + crop_offset_x
                y = y + crop_offset_y
                converted = True
                conversion_type = "crop_offset"
            # 情况2：全屏压缩截图 - 按比例转换到原图尺寸
            elif image_width > 0 and image_height > 0:
                # 优先使用 original_img_width/height（更精确）
                # 如果没传，则用 screen_width/height（兼容旧版本）
                target_width = original_img_width if original_img_width > 0 else screen_width
                target_height = original_img_height if original_img_height > 0 else screen_height
                
                if target_width > 0 and target_height > 0:
                    if image_width != target_width or image_height != target_height:
                        x = int(x * target_width / image_width)
                        y = int(y * target_height / image_height)
                        converted = True
                        conversion_type = "scale"
            
            # 执行点击
            if self._is_ios():
                ios_client = self._get_ios_client()
                ios_client.wda.click(x, y)
            else:
                self.client.u2.click(x, y)
            
            time.sleep(0.3)
            
            # 计算百分比坐标（用于跨设备兼容）
            x_percent = round(x / screen_width * 100, 1) if screen_width > 0 else 0
            y_percent = round(y / screen_height * 100, 1) if screen_height > 0 else 0
            
            # 使用标准记录格式：坐标点击用百分比作为定位方式（跨分辨率兼容）
            self._record_click('percent', f"{x_percent}%,{y_percent}%", x_percent, y_percent,
                              element_desc=f"坐标({x},{y})")
            
            # 🎯 关键步骤：检查应用是否跳转，如果跳转则自动返回目标应用
            app_check = self._check_app_switched()
            return_result = None
            
            if app_check['switched']:
                # 应用已跳转，尝试返回目标应用
                return_result = self._return_to_target_app()
            
            # 构建返回消息
            if converted:
                if conversion_type == "crop_offset":
                    msg = f"✅ 点击成功: ({x}, {y})\n" \
                          f"   🔍 局部截图坐标转换: ({original_x},{original_y}) + 偏移({crop_offset_x},{crop_offset_y}) → ({x},{y})"
                else:
                    msg = f"✅ 点击成功: ({x}, {y})\n" \
                          f"   📐 坐标已转换: ({original_x},{original_y}) → ({x},{y})\n" \
                          f"   🖼️ 图片尺寸: {image_width}x{image_height} → 屏幕: {screen_width}x{screen_height}"
            else:
                msg = f"✅ 点击成功: ({x}, {y}) [相对位置: {x_percent}%, {y_percent}%]"
            
            # 如果检测到应用跳转，添加警告和返回结果
            if app_check['switched']:
                msg += f"\n{app_check['message']}"
                if return_result:
                    if return_result['success']:
                        msg += f"\n{return_result['message']}"
                    else:
                        msg += f"\n❌ 自动返回失败: {return_result['message']}"
            
            return {
                "success": True,
                "message": msg,
                "app_check": app_check,
                "return_to_app": return_result
            }
        except Exception as e:
            return {"success": False, "message": f"❌ 点击失败: {e}"}
    
    def click_by_percent(self, x_percent: float, y_percent: float) -> Dict:
        """通过百分比坐标点击（跨设备兼容）
        
        百分比坐标原理：
        - 屏幕左上角是 (0%, 0%)，右下角是 (100%, 100%)
        - 屏幕正中央是 (50%, 50%)
        - 像素坐标 = 屏幕尺寸 × (百分比 / 100)
        
        Args:
            x_percent: X轴百分比 (0-100)，0=最左，50=中间，100=最右
            y_percent: Y轴百分比 (0-100)，0=最上，50=中间，100=最下
        
        示例：
            click_by_percent(50, 50)   # 点击屏幕正中央
            click_by_percent(10, 5)    # 点击左上角附近
            click_by_percent(85, 90)   # 点击右下角附近
        
        优势：
            - 同样的百分比在不同分辨率设备上都能点到相同相对位置
            - 录制一次，多设备回放
        """
        try:
            # 第1步：获取屏幕尺寸
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    size = ios_client.wda.window_size()
                    width, height = size[0], size[1]
                else:
                    return {"success": False, "msg": "iOS未初始化"}
            else:
                info = self.client.u2.info
                width = info.get('displayWidth', 0)
                height = info.get('displayHeight', 0)
            
            if width == 0 or height == 0:
                return {"success": False, "msg": "无法获取屏幕尺寸"}
            
            # 第2步：百分比转像素坐标
            # 公式：像素 = 屏幕尺寸 × (百分比 / 100)
            x = int(width * x_percent / 100)
            y = int(height * y_percent / 100)
            
            # 第3步：执行点击
            if self._is_ios():
                ios_client.wda.click(x, y)
            else:
                self.client.u2.click(x, y)
            
            time.sleep(0.3)
            
            # 第4步：使用标准记录格式
            self._record_click('percent', f"{x_percent}%,{y_percent}%", x_percent, y_percent,
                              element_desc=f"百分比({x_percent}%,{y_percent}%)")
            
            return {
                "success": True,
                "pixel": {"x": x, "y": y}
            }
        except Exception as e:
            return {"success": False, "message": f"❌ 百分比点击失败: {e}"}
    
    def click_by_text(self, text: str, timeout: float = 3.0, position: Optional[str] = None, 
                       verify: Optional[str] = None) -> Dict:
        """通过文本点击 - 先查 XML 树，再精准匹配
        
        Args:
            text: 元素的文本内容
            timeout: 超时时间
            position: 位置信息，当有多个相同文案时使用。支持：
                - 垂直方向: "top"/"upper"/"上", "bottom"/"lower"/"下", "middle"/"center"/"中"
                - 水平方向: "left"/"左", "right"/"右", "center"/"中"
            verify: 可选，点击后验证的文本。如果指定，会检查该文本是否出现在页面上
        """
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    elem = ios_client.wda(name=text)
                    if not elem.exists:
                        elem = ios_client.wda(label=text)
                    if elem.exists:
                        elem.click()
                        time.sleep(0.3)
                        self._record_click('text', text, element_desc=text, locator_attr='text')
                        # 验证逻辑
                        if verify:
                            return self._verify_after_click(verify, ios=True)
                        # 返回页面文本摘要，方便确认页面变化
                        page_texts = self._get_page_texts(10)
                        return {"success": True, "page_texts": page_texts}
                    # 控件树找不到，提示用视觉识别
                    return {"success": False, "fallback": "vision", "msg": f"未找到'{text}'，用截图点击"}
                else:
                    return {"success": False, "msg": "iOS未初始化"}
            else:
                # 获取屏幕尺寸用于计算百分比
                screen_width, screen_height = self.client.u2.window_size()
                
                # 🔍 先查 XML 树，找到元素及其属性
                found_elem = self._find_element_in_tree(text, position=position)
                
                if found_elem:
                    attr_type = found_elem['attr_type']
                    attr_value = found_elem['attr_value']
                    bounds = found_elem.get('bounds')
                    
                    # 计算百分比坐标作为兜底
                    x_pct, y_pct = 0, 0
                    if bounds:
                        cx = (bounds[0] + bounds[2]) // 2
                        cy = (bounds[1] + bounds[3]) // 2
                        x_pct = round(cx / screen_width * 100, 1)
                        y_pct = round(cy / screen_height * 100, 1)
                    
                    # 如果有位置参数，直接使用坐标点击
                    if position and bounds:
                        x = (bounds[0] + bounds[2]) // 2
                        y = (bounds[1] + bounds[3]) // 2
                        self.client.u2.click(x, y)
                        time.sleep(0.3)
                        self._record_click('text', attr_value, x_pct, y_pct, 
                                          element_desc=f"{text}({position})", locator_attr=attr_type)
                        # 验证逻辑
                        if verify:
                            return self._verify_after_click(verify)
                        # 返回页面文本摘要
                        page_texts = self._get_page_texts(10)
                        return {"success": True, "page_texts": page_texts}
                    
                    # 没有位置参数时，使用选择器定位
                    if attr_type == 'text':
                        elem = self.client.u2(text=attr_value)
                    elif attr_type == 'textContains':
                        elem = self.client.u2(textContains=attr_value)
                    elif attr_type == 'description':
                        elem = self.client.u2(description=attr_value)
                    elif attr_type == 'descriptionContains':
                        elem = self.client.u2(descriptionContains=attr_value)
                    else:
                        elem = None
                    
                    if elem and elem.exists(timeout=1):
                        elem.click()
                        time.sleep(0.3)
                        self._record_click('text', attr_value, x_pct, y_pct,
                                          element_desc=text, locator_attr=attr_type)
                        # 验证逻辑
                        if verify:
                            return self._verify_after_click(verify)
                        # 返回页面文本摘要
                        page_texts = self._get_page_texts(10)
                        return {"success": True, "page_texts": page_texts}
                    
                    # 选择器失败，用控件中心坐标点兜底
                    if bounds:
                        x = (bounds[0] + bounds[2]) // 2
                        y = (bounds[1] + bounds[3]) // 2
                        self.client.u2.click(x, y)
                        time.sleep(0.3)
                        self._record_click('coords', f"{x},{y}", x_pct, y_pct,
                                          element_desc=text)
                        # 验证逻辑
                        if verify:
                            return self._verify_after_click(verify)
                        # 返回页面文本摘要
                        page_texts = self._get_page_texts(10)
                        return {"success": True, "page_texts": page_texts}
                
                # 控件树找不到，提示用视觉识别
                return {"success": False, "fallback": "vision", "msg": f"未找到'{text}'，用截图点击"}
        except Exception as e:
            return {"success": False, "msg": str(e)}
    
    def _verify_after_click(self, verify_text: str, ios: bool = False, timeout: float = 2.0) -> Dict:
        """点击后验证期望文本是否出现
        
        Args:
            verify_text: 期望出现的文本
            ios: 是否是 iOS 设备
            timeout: 验证超时时间
        
        Returns:
            {"success": True, "verified": True/False, "hint": "..."}
        """
        time.sleep(0.5)  # 等待页面更新
        
        try:
            if ios:
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    exists = ios_client.wda(name=verify_text).exists or \
                             ios_client.wda(label=verify_text).exists
                else:
                    exists = False
            else:
                # Android: 检查文本或包含文本
                exists = self.client.u2(text=verify_text).exists(timeout=timeout) or \
                         self.client.u2(textContains=verify_text).exists(timeout=0.5) or \
                         self.client.u2(description=verify_text).exists(timeout=0.5)
            
            if exists:
                return {"success": True, "verified": True}
            else:
                # 验证失败，提示可以截图确认
                return {
                    "success": True,  # 点击本身成功
                    "verified": False,
                    "expect": verify_text,
                    "hint": "验证失败，可截图确认"
                }
        except Exception as e:
            return {"success": True, "verified": False, "hint": f"验证异常: {e}"}
    
    def _find_element_in_tree(self, text: str, position: Optional[str] = None, exact_match: bool = True) -> Optional[Dict]:
        """在 XML 树中查找指定文本的元素，优先返回可点击的元素
        
        Args:
            text: 要查找的文本
            position: 位置信息，用于在有多个相同文案时筛选
            exact_match: 是否精确匹配。True=优先精确匹配（用于定位元素如点击），
                        False=只进行包含匹配（用于验证元素）
        """
        try:
            xml = self.client.u2.dump_hierarchy(compressed=False)
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml)
            
            # 获取屏幕尺寸
            screen_width, screen_height = self.client.u2.window_size()
            
            # 存储所有匹配的元素（包括不可点击的）
            matched_elements = []
            
            for elem in root.iter():
                elem_text = elem.attrib.get('text', '')
                elem_desc = elem.attrib.get('content-desc', '')
                bounds_str = elem.attrib.get('bounds', '')
                clickable = elem.attrib.get('clickable', 'false').lower() == 'true'
                
                # 解析 bounds
                bounds = None
                if bounds_str:
                    import re
                    match = re.findall(r'\d+', bounds_str)
                    if len(match) == 4:
                        bounds = [int(x) for x in match]
                
                # 判断是否匹配
                is_match = False
                attr_type = None
                attr_value = None
                
                if exact_match:
                    # 精确匹配模式（用于定位元素）：优先精确匹配
                    # 精确匹配 text
                    if elem_text == text:
                        is_match = True
                        attr_type = 'text'
                        attr_value = text
                    # 精确匹配 content-desc
                    elif elem_desc == text:
                        is_match = True
                        attr_type = 'description'
                        attr_value = text
                    # 精确匹配找不到时，再尝试包含匹配（作为兜底）
                    elif text in elem_text:
                        is_match = True
                        attr_type = 'textContains'
                        attr_value = text
                    # 包含匹配 content-desc
                    elif text in elem_desc:
                        is_match = True
                        attr_type = 'descriptionContains'
                        attr_value = text
                else:
                    # 包含匹配模式（用于验证元素）：只进行包含匹配
                    # 包含匹配 text
                    if text in elem_text:
                        is_match = True
                        attr_type = 'textContains'
                        attr_value = text
                    # 包含匹配 content-desc
                    elif text in elem_desc:
                        is_match = True
                        attr_type = 'descriptionContains'
                        attr_value = text
                
                if is_match and bounds:
                    # 计算元素的中心点坐标
                    center_x = (bounds[0] + bounds[2]) / 2
                    center_y = (bounds[1] + bounds[3]) / 2
                    
                    matched_elements.append({
                        'attr_type': attr_type,
                        'attr_value': attr_value,
                        'bounds': bounds,
                        'clickable': clickable,
                        'center_x': center_x,
                        'center_y': center_y
                    })
            
            if not matched_elements:
                return None
            
            # 精确匹配模式下，优先返回精确匹配的元素（text/description），再返回包含匹配的元素
            if exact_match:
                exact_matches = [m for m in matched_elements if m['attr_type'] in ['text', 'description']]
                contains_matches = [m for m in matched_elements if m['attr_type'] in ['textContains', 'descriptionContains']]
                # 如果有精确匹配，优先使用精确匹配的结果
                if exact_matches:
                    matched_elements = exact_matches + contains_matches
                # 如果没有精确匹配，使用包含匹配的结果
                else:
                    matched_elements = contains_matches
            
            # 如果有位置信息，根据位置筛选
            if position and len(matched_elements) > 1:
                position_lower = position.lower()
                
                # 根据位置信息排序
                if position_lower in ['top', 'upper', '上', '上方']:
                    # 选择 y 坐标最小的（最上面的）
                    matched_elements = sorted(matched_elements, key=lambda x: x['center_y'])
                elif position_lower in ['bottom', 'lower', '下', '下方', '底部']:
                    # 选择 y 坐标最大的（最下面的）
                    matched_elements = sorted(matched_elements, key=lambda x: x['center_y'], reverse=True)
                elif position_lower in ['left', '左', '左侧']:
                    # 选择 x 坐标最小的（最左边的）
                    matched_elements = sorted(matched_elements, key=lambda x: x['center_x'])
                elif position_lower in ['right', '右', '右侧']:
                    # 选择 x 坐标最大的（最右边的）
                    matched_elements = sorted(matched_elements, key=lambda x: x['center_x'], reverse=True)
                elif position_lower in ['middle', 'center', '中', '中间']:
                    # 选择最接近屏幕中心的
                    screen_mid_x = screen_width / 2
                    screen_mid_y = screen_height / 2
                    matched_elements = sorted(
                        matched_elements,
                        key=lambda x: abs(x['center_x'] - screen_mid_x) + abs(x['center_y'] - screen_mid_y)
                    )
            
            # 如果有位置信息，优先返回排序后的第一个元素（最符合位置要求的）
            # 如果没有位置信息，优先返回可点击的元素
            if position and matched_elements:
                # 有位置信息时，直接返回排序后的第一个（最符合位置要求的）
                first_match = matched_elements[0]
                return {
                    'attr_type': first_match['attr_type'],
                    'attr_value': first_match['attr_value'],
                    'bounds': first_match['bounds']
                }
            
            # 没有位置信息时，优先返回可点击的元素
            # 由于前面已经排序（精确匹配在前），这里会优先返回精确匹配且可点击的元素
            for match in matched_elements:
                if match['clickable']:
                    return {
                        'attr_type': match['attr_type'],
                        'attr_value': match['attr_value'],
                        'bounds': match['bounds']
                    }
            
            # 如果没有可点击的元素，直接返回第一个匹配元素的 bounds（使用坐标点击）
            if matched_elements:
                first_match = matched_elements[0]
                return {
                    'attr_type': first_match['attr_type'],
                    'attr_value': first_match['attr_value'],
                    'bounds': first_match['bounds']
                }
            
            return None
        except Exception as e:
            import traceback
            traceback.print_exc()
            return None
    
    def click_by_id(self, resource_id: str, index: int = 0) -> Dict:
        """通过 resource-id 点击"""
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    elem = ios_client.wda(id=resource_id)
                    if not elem.exists:
                        elem = ios_client.wda(name=resource_id)
                    if elem.exists:
                        elements = elem.find_elements()
                        if index < len(elements):
                            elements[index].click()
                            time.sleep(0.3)
                            self._record_click('id', resource_id, element_desc=resource_id)
                            return {"success": True}
                        else:
                            return {"success": False, "msg": f"索引{index}超出范围(共{len(elements)}个)"}
                    return {"success": False, "fallback": "vision", "msg": f"未找到ID'{resource_id}'"}
                else:
                    return {"success": False, "msg": "iOS未初始化"}
            else:
                normalized_id = self._normalize_resource_id(resource_id)
                elem = self.client.u2(resourceId=normalized_id)
                if elem.exists(timeout=0.5):
                    count = elem.count
                    if index < count:
                        elem[index].click()
                        time.sleep(0.3)
                        # 记录时同时保留原始入参和实际使用的 id 信息
                        self._record_click('id', normalized_id, element_desc=resource_id)
                        return {"success": True}
                    else:
                        return {"success": False, "msg": f"索引{index}超出范围(共{count}个)"}
                return {
                    "success": False,
                    "fallback": "vision",
                    "msg": f"未找到ID'{resource_id}' (实际匹配: '{normalized_id}')"
                }
        except Exception as e:
            return {"success": False, "msg": str(e)}
    
    # ==================== 长按操作 ====================
    
    def long_press_at_coords(self, x: int, y: int, duration: float = 1.0,
                             image_width: int = 0, image_height: int = 0,
                             crop_offset_x: int = 0, crop_offset_y: int = 0,
                             original_img_width: int = 0, original_img_height: int = 0) -> Dict:
        """长按坐标（核心功能，支持自动坐标转换）
        
        Args:
            x: X 坐标（来自截图分析或屏幕坐标）
            y: Y 坐标（来自截图分析或屏幕坐标）
            duration: 长按持续时间（秒），默认 1.0
            image_width: 压缩后图片宽度（AI 看到的图片尺寸）
            image_height: 压缩后图片高度（AI 看到的图片尺寸）
            crop_offset_x: 局部截图的 X 偏移量（局部截图时传入）
            crop_offset_y: 局部截图的 Y 偏移量（局部截图时传入）
            original_img_width: 截图原始宽度（压缩前的尺寸，用于精确转换）
            original_img_height: 截图原始高度（压缩前的尺寸，用于精确转换）
        
        坐标转换说明：
            1. 全屏压缩截图：AI 坐标 → 原图坐标（基于 image/original_img 比例）
            2. 局部裁剪截图：AI 坐标 + 偏移量 = 屏幕坐标
        """
        try:
            # 获取屏幕尺寸
            screen_width, screen_height = 0, 0
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    size = ios_client.wda.window_size()
                    screen_width, screen_height = size[0], size[1]
                else:
                    return {"success": False, "msg": "iOS未初始化"}
            else:
                info = self.client.u2.info
                screen_width = info.get('displayWidth', 0)
                screen_height = info.get('displayHeight', 0)
            
            # 🎯 坐标转换
            original_x, original_y = x, y
            converted = False
            conversion_type = ""
            
            # 情况1：局部裁剪截图 - 加上偏移量
            if crop_offset_x > 0 or crop_offset_y > 0:
                x = x + crop_offset_x
                y = y + crop_offset_y
                converted = True
                conversion_type = "crop_offset"
            # 情况2：全屏压缩截图 - 按比例转换到原图尺寸
            elif image_width > 0 and image_height > 0:
                target_width = original_img_width if original_img_width > 0 else screen_width
                target_height = original_img_height if original_img_height > 0 else screen_height
                
                if target_width > 0 and target_height > 0:
                    if image_width != target_width or image_height != target_height:
                        x = int(x * target_width / image_width)
                        y = int(y * target_height / image_height)
                        converted = True
                        conversion_type = "scale"
            
            # 执行长按
            if self._is_ios():
                ios_client = self._get_ios_client()
                # iOS 使用 tap_hold 或 swipe 原地实现长按
                if hasattr(ios_client.wda, 'tap_hold'):
                    ios_client.wda.tap_hold(x, y, duration=duration)
                else:
                    # 兜底：用原地 swipe 模拟长按
                    ios_client.wda.swipe(x, y, x, y, duration=duration)
            else:
                self.client.u2.long_click(x, y, duration=duration)
            
            time.sleep(0.3)
            
            # 计算百分比坐标（用于跨设备兼容）
            x_percent = round(x / screen_width * 100, 1) if screen_width > 0 else 0
            y_percent = round(y / screen_height * 100, 1) if screen_height > 0 else 0
            
            # 使用标准记录格式
            self._record_long_press('percent', f"{x_percent}%,{y_percent}%", duration,
                                   x_percent, y_percent, element_desc=f"坐标({x},{y})")
            
            if converted:
                if conversion_type == "crop_offset":
                    return {"success": True}
                else:
                    return {"success": True}
            else:
                return {"success": True}
        except Exception as e:
            return {"success": False, "message": f"❌ 长按失败: {e}"}
    
    def long_press_by_percent(self, x_percent: float, y_percent: float, duration: float = 1.0) -> Dict:
        """通过百分比坐标长按（跨设备兼容）
        
        百分比坐标原理：
        - 屏幕左上角是 (0%, 0%)，右下角是 (100%, 100%)
        - 屏幕正中央是 (50%, 50%)
        - 像素坐标 = 屏幕尺寸 × (百分比 / 100)
        
        Args:
            x_percent: X轴百分比 (0-100)，0=最左，50=中间，100=最右
            y_percent: Y轴百分比 (0-100)，0=最上，50=中间，100=最下
            duration: 长按持续时间（秒），默认 1.0
        
        优势：
            - 同样的百分比在不同分辨率设备上都能点到相同相对位置
            - 录制一次，多设备回放
        """
        try:
            # 第1步：获取屏幕尺寸
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    size = ios_client.wda.window_size()
                    width, height = size[0], size[1]
                else:
                    return {"success": False, "msg": "iOS未初始化"}
            else:
                info = self.client.u2.info
                width = info.get('displayWidth', 0)
                height = info.get('displayHeight', 0)
            
            if width == 0 or height == 0:
                return {"success": False, "msg": "无法获取屏幕尺寸"}
            
            # 第2步：百分比转像素坐标
            x = int(width * x_percent / 100)
            y = int(height * y_percent / 100)
            
            # 第3步：执行长按
            if self._is_ios():
                ios_client = self._get_ios_client()
                if hasattr(ios_client.wda, 'tap_hold'):
                    ios_client.wda.tap_hold(x, y, duration=duration)
                else:
                    ios_client.wda.swipe(x, y, x, y, duration=duration)
            else:
                self.client.u2.long_click(x, y, duration=duration)
            
            time.sleep(0.3)
            
            # 第4步：使用标准记录格式
            self._record_long_press('percent', f"{x_percent}%,{y_percent}%", duration,
                                   x_percent, y_percent, element_desc=f"百分比({x_percent}%,{y_percent}%)")
            
            return {"success": True
            }
        except Exception as e:
            return {"success": False, "message": f"❌ 百分比长按失败: {e}"}
    
    def long_press_by_text(self, text: str, duration: float = 1.0) -> Dict:
        """通过文本长按
        
        Args:
            text: 元素的文本内容（精确匹配）
            duration: 长按持续时间（秒），默认 1.0
        """
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    elem = ios_client.wda(name=text)
                    if not elem.exists:
                        elem = ios_client.wda(label=text)
                    if elem.exists:
                        # iOS 元素长按
                        bounds = elem.bounds
                        x = int((bounds.x + bounds.x + bounds.width) / 2)
                        y = int((bounds.y + bounds.y + bounds.height) / 2)
                        if hasattr(ios_client.wda, 'tap_hold'):
                            ios_client.wda.tap_hold(x, y, duration=duration)
                        else:
                            ios_client.wda.swipe(x, y, x, y, duration=duration)
                        time.sleep(0.3)
                        self._record_long_press('text', text, duration, element_desc=text, locator_attr='text')
                        return {"success": True}
                    return {"success": False, "msg": f"未找到'{text}'"}
            else:
                # 获取屏幕尺寸用于计算百分比
                screen_width, screen_height = self.client.u2.window_size()
                
                # 先查 XML 树，找到元素
                found_elem = self._find_element_in_tree(text)
                
                if found_elem:
                    attr_type = found_elem['attr_type']
                    attr_value = found_elem['attr_value']
                    bounds = found_elem.get('bounds')
                    
                    # 计算百分比坐标作为兜底
                    x_pct, y_pct = 0, 0
                    if bounds:
                        cx = (bounds[0] + bounds[2]) // 2
                        cy = (bounds[1] + bounds[3]) // 2
                        x_pct = round(cx / screen_width * 100, 1)
                        y_pct = round(cy / screen_height * 100, 1)
                    
                    # 根据找到的属性类型，使用对应的选择器
                    if attr_type == 'text':
                        elem = self.client.u2(text=attr_value)
                    elif attr_type == 'textContains':
                        elem = self.client.u2(textContains=attr_value)
                    elif attr_type == 'description':
                        elem = self.client.u2(description=attr_value)
                    elif attr_type == 'descriptionContains':
                        elem = self.client.u2(descriptionContains=attr_value)
                    else:
                        elem = None
                    
                    if elem and elem.exists(timeout=1):
                        elem.long_click(duration=duration)
                        time.sleep(0.3)
                        self._record_long_press('text', attr_value, duration, x_pct, y_pct,
                                               element_desc=text, locator_attr=attr_type)
                        return {"success": True}
                    
                    # 如果选择器失败，用坐标兜底
                    if bounds:
                        x = (bounds[0] + bounds[2]) // 2
                        y = (bounds[1] + bounds[3]) // 2
                        self.client.u2.long_click(x, y, duration=duration)
                        time.sleep(0.3)
                        self._record_long_press('percent', f"{x_pct}%,{y_pct}%", duration, x_pct, y_pct,
                                               element_desc=text)
                        return {"success": True}
                
                return {"success": False, "msg": f"未找到'{text}'"}
        except Exception as e:
            return {"success": False, "message": f"❌ 长按失败: {e}"}
    
    def long_press_by_id(self, resource_id: str, duration: float = 1.0) -> Dict:
        """通过 resource-id 长按
        
        Args:
            resource_id: 元素的 resource-id
            duration: 长按持续时间（秒），默认 1.0
        """
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    elem = ios_client.wda(id=resource_id)
                    if not elem.exists:
                        elem = ios_client.wda(name=resource_id)
                    if elem.exists:
                        bounds = elem.bounds
                        x = int((bounds.x + bounds.x + bounds.width) / 2)
                        y = int((bounds.y + bounds.y + bounds.height) / 2)
                        if hasattr(ios_client.wda, 'tap_hold'):
                            ios_client.wda.tap_hold(x, y, duration=duration)
                        else:
                            ios_client.wda.swipe(x, y, x, y, duration=duration)
                        time.sleep(0.3)
                        self._record_long_press('id', resource_id, duration, element_desc=resource_id)
                        return {"success": True}
                    return {"success": False, "msg": f"未找到'{resource_id}'"}
            else:
                normalized_id = self._normalize_resource_id(resource_id)
                elem = self.client.u2(resourceId=normalized_id)
                if elem.exists(timeout=0.5):
                    elem.long_click(duration=duration)
                    time.sleep(0.3)
                    self._record_long_press('id', normalized_id, duration, element_desc=resource_id)
                    return {
                        "success": True,
                        "message": f"✅ 长按成功: {resource_id} (实际匹配: {normalized_id}) 持续 {duration}s"
                    }
                return {
                    "success": False,
                    "msg": f"未找到'{resource_id}' (实际匹配: '{normalized_id}')"
                }
        except Exception as e:
            return {"success": False, "message": f"❌ 长按失败: {e}"}
    
    # ==================== 输入操作 ====================
    
    def input_text_by_id(self, resource_id: str, text: str) -> Dict:
        """通过 resource-id 输入文本
        
        优化策略：
        1. 先用 resourceId 定位
        2. 如果只有 1 个元素 → 直接输入
        3. 如果有多个相同 ID（>5个说明 ID 不可靠）→ 改用 EditText 类型定位
        4. 多个 EditText 时选择最靠上的（搜索框通常在顶部）
        """
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    elem = ios_client.wda(id=resource_id)
                    if not elem.exists:
                        elem = ios_client.wda(name=resource_id)
                    if elem.exists:
                        elem.set_text(text)
                        time.sleep(0.3)
                        self._record_input(text, 'id', resource_id)
                        
                        # 🎯 关键步骤：检查应用是否跳转，如果跳转则自动返回目标应用
                        app_check = self._check_app_switched()
                        return_result = None
                        if app_check['switched']:
                            return_result = self._return_to_target_app()
                        
                        msg = f"✅ 输入成功: '{text}'"
                        if app_check['switched']:
                            msg += f"\n{app_check['message']}"
                            if return_result:
                                if return_result['success']:
                                    msg += f"\n{return_result['message']}"
                                else:
                                    msg += f"\n❌ 自动返回失败: {return_result['message']}"
                        
                        return {
                            "success": True,
                            "message": msg,
                            "app_check": app_check,
                            "return_to_app": return_result
                        }
                    return {"success": False, "message": f"❌ 输入框不存在: {resource_id}"}
            else:
                normalized_id = self._normalize_resource_id(resource_id)
                elements = self.client.u2(resourceId=normalized_id)
                
                # 检查是否存在
                if elements.exists(timeout=0.5):
                    count = elements.count
                    
                    # 只有 1 个元素，直接输入
                    if count == 1:
                        elements.set_text(text)
                        time.sleep(0.3)
                        self._record_input(text, 'id', normalized_id)
                        
                        # 🎯 关键步骤：检查应用是否跳转，如果跳转则自动返回目标应用
                        app_check = self._check_app_switched()
                        return_result = None
                        if app_check['switched']:
                            return_result = self._return_to_target_app()
                        
                        msg = f"✅ 输入成功: '{text}' (id: {resource_id}, 实际匹配: {normalized_id})"
                        if app_check['switched']:
                            msg += f"\n{app_check['message']}"
                            if return_result:
                                if return_result['success']:
                                    msg += f"\n{return_result['message']}"
                                else:
                                    msg += f"\n❌ 自动返回失败: {return_result['message']}"
                        
                        return {
                            "success": True,
                            "message": msg,
                            "app_check": app_check,
                            "return_to_app": return_result
                        }
                    
                    # 多个相同 ID（<=5个），尝试智能选择
                    if count <= 5:
                        for i in range(count):
                            try:
                                elem = elements[i]
                                info = elem.info
                                # 优先选择可编辑的
                                if info.get('editable') or info.get('focusable'):
                                    elem.set_text(text)
                                    time.sleep(0.3)
                                    self._record_input(text, 'id', resource_id)
                                    
                                    # 🎯 关键步骤：检查应用是否跳转，如果跳转则自动返回目标应用
                                    app_check = self._check_app_switched()
                                    return_result = None
                                    if app_check['switched']:
                                        return_result = self._return_to_target_app()
                                    
                                    msg = f"✅ 输入成功: '{text}'"
                                    if app_check['switched']:
                                        msg += f"\n{app_check['message']}"
                                        if return_result:
                                            if return_result['success']:
                                                msg += f"\n{return_result['message']}"
                                            else:
                                                msg += f"\n❌ 自动返回失败: {return_result['message']}"
                                    
                                    return {
                                        "success": True,
                                        "message": msg,
                                        "app_check": app_check,
                                        "return_to_app": return_result
                                    }
                            except:
                                continue
                        # 没找到可编辑的，用第一个
                        elements[0].set_text(text)
                        time.sleep(0.3)
                        self._record_input(text, 'id', resource_id)
                        
                        # 🎯 关键步骤：检查应用是否跳转，如果跳转则自动返回目标应用
                        app_check = self._check_app_switched()
                        return_result = None
                        if app_check['switched']:
                            return_result = self._return_to_target_app()
                        
                        msg = f"✅ 输入成功: '{text}'"
                        if app_check['switched']:
                            msg += f"\n{app_check['message']}"
                            if return_result:
                                if return_result['success']:
                                    msg += f"\n{return_result['message']}"
                                else:
                                    msg += f"\n❌ 自动返回失败: {return_result['message']}"
                        
                        return {
                            "success": True,
                            "message": msg,
                            "app_check": app_check,
                            "return_to_app": return_result
                        }
                
                # ID 不可靠（不存在或太多），改用 EditText 类型定位
                edit_texts = self.client.u2(className='android.widget.EditText')
                if edit_texts.exists(timeout=0.5):
                    et_count = edit_texts.count
                    if et_count == 1:
                        edit_texts.set_text(text)
                        time.sleep(0.3)
                        self._record_input(text, 'class', 'EditText')
                        
                        # 🎯 关键步骤：检查应用是否跳转，如果跳转则自动返回目标应用
                        app_check = self._check_app_switched()
                        return_result = None
                        if app_check['switched']:
                            return_result = self._return_to_target_app()
                        
                        msg = f"✅ 输入成功: '{text}' (通过 EditText 定位)"
                        if app_check['switched']:
                            msg += f"\n{app_check['message']}"
                            if return_result:
                                if return_result['success']:
                                    msg += f"\n{return_result['message']}"
                                else:
                                    msg += f"\n❌ 自动返回失败: {return_result['message']}"
                        
                        return {
                            "success": True,
                            "message": msg,
                            "app_check": app_check,
                            "return_to_app": return_result
                        }
                    
                    # 多个 EditText，选择最靠上的
                    best_elem = None
                    min_top = 9999
                    for i in range(et_count):
                        try:
                            elem = edit_texts[i]
                            top = elem.info.get('bounds', {}).get('top', 9999)
                            if top < min_top:
                                min_top = top
                                best_elem = elem
                        except:
                            continue
                    
                    if best_elem:
                        best_elem.set_text(text)
                        time.sleep(0.3)
                        self._record_input(text, 'class', 'EditText')
                        
                        # 🎯 关键步骤：检查应用是否跳转，如果跳转则自动返回目标应用
                        app_check = self._check_app_switched()
                        return_result = None
                        if app_check['switched']:
                            return_result = self._return_to_target_app()
                        
                        msg = f"✅ 输入成功: '{text}' (通过 EditText 定位，选择最顶部的)"
                        if app_check['switched']:
                            msg += f"\n{app_check['message']}"
                            if return_result:
                                if return_result['success']:
                                    msg += f"\n{return_result['message']}"
                                else:
                                    msg += f"\n❌ 自动返回失败: {return_result['message']}"
                        
                        return {
                            "success": True,
                            "message": msg,
                            "app_check": app_check,
                            "return_to_app": return_result
                        }
                
                return {"success": False, "message": f"❌ 输入框不存在: {resource_id}"}
                    
        except Exception as e:
            return {"success": False, "message": f"❌ 输入失败: {e}"}
    
    def input_at_coords(self, x: int, y: int, text: str) -> Dict:
        """点击坐标后输入文本（适合游戏）"""
        try:
            # 获取屏幕尺寸（用于转换百分比）
            screen_width, screen_height = 0, 0
            
            # 先点击聚焦
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    ios_client.wda.click(x, y)
                    size = ios_client.wda.window_size()
                    screen_width, screen_height = size[0], size[1]
            else:
                self.client.u2.click(x, y)
                info = self.client.u2.info
                screen_width = info.get('displayWidth', 0)
                screen_height = info.get('displayHeight', 0)
            
            time.sleep(0.3)
            
            # 输入文本
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    ios_client.wda.send_keys(text)
            else:
                self.client.u2.send_keys(text)
            
            time.sleep(0.3)
            
            # 计算百分比坐标
            x_percent = round(x / screen_width * 100, 1) if screen_width > 0 else 0
            y_percent = round(y / screen_height * 100, 1) if screen_height > 0 else 0
            
            # 使用标准记录格式
            self._record_input(text, 'percent', f"{x_percent}%,{y_percent}%", x_percent, y_percent)
            
            # 🎯 关键步骤：检查应用是否跳转，如果跳转则自动返回目标应用
            app_check = self._check_app_switched()
            return_result = None
            
            if app_check['switched']:
                # 应用已跳转，尝试返回目标应用
                return_result = self._return_to_target_app()
            
            msg = f"✅ 输入成功: ({x}, {y}) [相对位置: {x_percent}%, {y_percent}%] -> '{text}'"
            if app_check['switched']:
                msg += f"\n{app_check['message']}"
                if return_result:
                    if return_result['success']:
                        msg += f"\n{return_result['message']}"
                    else:
                        msg += f"\n❌ 自动返回失败: {return_result['message']}"
            
            return {
                "success": True,
                "message": msg,
                "app_check": app_check,
                "return_to_app": return_result
            }
        except Exception as e:
            return {"success": False, "message": f"❌ 输入失败: {e}"}
    
    # ==================== 导航操作 ====================
    
    async def swipe(self, direction: str, y: Optional[int] = None, y_percent: Optional[float] = None,
                   distance: Optional[int] = None, distance_percent: Optional[float] = None) -> Dict:
        """滑动屏幕
        
        Args:
            direction: 滑动方向 (up/down/left/right)
            y: 左右滑动时指定的高度坐标（像素）
            y_percent: 左右滑动时指定的高度百分比 (0-100)
            distance: 横向滑动时指定的滑动距离（像素），仅用于 left/right
            distance_percent: 横向滑动时指定的滑动距离百分比 (0-100)，仅用于 left/right
        """
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    size = ios_client.wda.window_size()
                    width, height = size[0], size[1]
                else:
                    return {"success": False, "msg": "iOS未初始化"}
            else:
                width, height = self.client.u2.window_size()
            
            center_x, center_y = width // 2, height // 2
            
            # 对于左右滑动，如果指定了 y 或 y_percent，使用指定的高度
            if direction in ['left', 'right']:
                if y_percent is not None:
                    if not (0 <= y_percent <= 100):
                        return {"success": False, "message": f"❌ y_percent 必须在 0-100 之间: {y_percent}"}
                    swipe_y = int(height * y_percent / 100)
                elif y is not None:
                    if not (0 <= y <= height):
                        return {"success": False, "message": f"❌ y 坐标超出屏幕范围 (0-{height}): {y}"}
                    swipe_y = y
                else:
                    swipe_y = center_y
                
                # 计算横向滑动距离
                if distance_percent is not None:
                    if not (0 <= distance_percent <= 100):
                        return {"success": False, "message": f"❌ distance_percent 必须在 0-100 之间: {distance_percent}"}
                    swipe_distance = int(width * distance_percent / 100)
                elif distance is not None:
                    if distance <= 0:
                        return {"success": False, "message": f"❌ distance 必须大于 0: {distance}"}
                    if distance > width:
                        return {"success": False, "message": f"❌ distance 不能超过屏幕宽度 ({width}): {distance}"}
                    swipe_distance = distance
                else:
                    # 默认滑动距离：屏幕宽度的 60%（从 0.8 到 0.2）
                    swipe_distance = int(width * 0.6)
                
                # 计算起始和结束位置
                if direction == 'left':
                    # 从右向左滑动：起始点在右侧，结束点在左侧
                    # 确保起始点不超出屏幕右边界
                    start_x = min(center_x + swipe_distance // 2, width - 10)
                    end_x = start_x - swipe_distance
                    # 确保结束点不超出屏幕左边界
                    if end_x < 10:
                        end_x = 10
                        start_x = min(end_x + swipe_distance, width - 10)
                else:  # right
                    # 从左向右滑动：起始点在左侧，结束点在右侧
                    # 确保起始点不超出屏幕左边界
                    start_x = max(center_x - swipe_distance // 2, 10)
                    end_x = start_x + swipe_distance
                    # 确保结束点不超出屏幕右边界
                    if end_x > width - 10:
                        end_x = width - 10
                        start_x = max(end_x - swipe_distance, 10)
                
                x1, y1, x2, y2 = start_x, swipe_y, end_x, swipe_y
            else:
                swipe_y = center_y
                # 纵向滑动保持原有逻辑
                swipe_map = {
                    'up': (center_x, int(height * 0.8), center_x, int(height * 0.2)),
                    'down': (center_x, int(height * 0.2), center_x, int(height * 0.8)),
                }
                if direction not in swipe_map:
                    return {"success": False, "message": f"❌ 不支持的方向: {direction}"}
                x1, y1, x2, y2 = swipe_map[direction]
            
            if self._is_ios():
                ios_client.wda.swipe(x1, y1, x2, y2)
            else:
                self.client.u2.swipe(x1, y1, x2, y2, duration=0.5)
            
            # 使用标准记录格式
            self._record_swipe(direction)
            
            # 🎯 关键步骤：检查应用是否跳转，如果跳转则自动返回目标应用
            app_check = self._check_app_switched()
            return_result = None
            
            if app_check['switched']:
                # 应用已跳转，尝试返回目标应用
                return_result = self._return_to_target_app()
            
            # 构建返回消息
            msg = f"✅ 滑动成功: {direction}"
            if direction in ['left', 'right']:
                msg_parts = []
                if y_percent is not None:
                    msg_parts.append(f"高度: {y_percent}% = {swipe_y}px")
                elif y is not None:
                    msg_parts.append(f"高度: {y}px")
                
                if distance_percent is not None:
                    msg_parts.append(f"距离: {distance_percent}% = {swipe_distance}px")
                elif distance is not None:
                    msg_parts.append(f"距离: {distance}px")
                else:
                    msg_parts.append(f"距离: 默认 {swipe_distance}px")
                
                if msg_parts:
                    msg += f" ({', '.join(msg_parts)})"
            
            # 如果检测到应用跳转，添加警告和返回结果
            if app_check['switched']:
                msg += f"\n{app_check['message']}"
                if return_result:
                    if return_result['success']:
                        msg += f"\n{return_result['message']}"
                    else:
                        msg += f"\n❌ 自动返回失败: {return_result['message']}"
            
            return {
                "success": True,
                "message": msg,
                "app_check": app_check,
                "return_to_app": return_result
            }
        except Exception as e:
            return {"success": False, "message": f"❌ 滑动失败: {e}"}
    
    async def press_key(self, key: str) -> Dict:
        """按键操作"""
        key_map = {
            'enter': 66, '回车': 66,
            'search': 84, '搜索': 84,
            'back': 4, '返回': 4,
            'home': 3,
        }
        
        try:
            if self._is_ios():
                ios_key_map = {'enter': 'return', 'back': 'back', 'home': 'home'}
                ios_key = ios_key_map.get(key.lower())
                if ios_key:
                    ios_client = self._get_ios_client()
                    if ios_client and hasattr(ios_client, 'wda'):
                        # iOS 使用不同的按键方式
                        if ios_key == 'return':
                            ios_client.wda.send_keys('\n')
                        elif ios_key == 'home':
                            ios_client.wda.home()
                        return {"success": True}
                return {"success": False, "msg": f"iOS不支持{key}"}
            else:
                keycode = key_map.get(key.lower())
                if keycode:
                    self.client.u2.shell(f'input keyevent {keycode}')
                    self._record_key(key)
                    return {"success": True}
                return {"success": False, "msg": f"不支持按键{key}"}
        except Exception as e:
            return {"success": False, "message": f"❌ 按键失败: {e}"}
    
    def wait(self, seconds: float) -> Dict:
        """等待指定时间"""
        time.sleep(seconds)
        # 记录等待操作
        record = {
            'action': 'wait',
            'timestamp': datetime.now().isoformat(),
            'seconds': seconds,
        }
        self.operation_history.append(record)
        return {"success": True}
    
    async def drag_progress_bar(self, direction: str = "right", distance_percent: float = 30.0, 
                                y_percent: Optional[float] = None, y: Optional[int] = None) -> Dict:
        """智能拖动进度条
        
        自动检测进度条是否可见：
        - 如果进度条已显示，直接拖动（无需先点击播放区域）
        - 如果进度条未显示，先点击播放区域显示控制栏，再拖动
        
        Args:
            direction: 拖动方向，'left'（倒退）或 'right'（前进），默认 'right'
            distance_percent: 拖动距离百分比 (0-100)，默认 30%
            y_percent: 进度条的垂直位置百分比 (0-100)，如果未指定则自动检测
            y: 进度条的垂直位置坐标（像素），如果未指定则自动检测
        """
        try:
            import xml.etree.ElementTree as ET
            import re
            
            if self._is_ios():
                return {"success": False, "message": "❌ iOS 暂不支持，请使用 mobile_swipe"}
            
            if direction not in ['left', 'right']:
                return {"success": False, "message": f"❌ 拖动方向必须是 'left' 或 'right': {direction}"}
            
            screen_width, screen_height = self.client.u2.window_size()
            
            # 获取 XML 查找进度条
            xml_string = self.client.u2.dump_hierarchy(compressed=False)
            root = ET.fromstring(xml_string)
            
            progress_bar_found = False
            progress_bar_y = None
            progress_bar_y_percent = None
            
            # 查找进度条元素（SeekBar、ProgressBar）
            for elem in root.iter():
                class_name = elem.attrib.get('class', '')
                resource_id = elem.attrib.get('resource-id', '')
                bounds_str = elem.attrib.get('bounds', '')
                
                # 检查是否是进度条
                is_progress_bar = (
                    'SeekBar' in class_name or 
                    'ProgressBar' in class_name or
                    'progress' in resource_id.lower() or
                    'seek' in resource_id.lower()
                )
                
                if is_progress_bar and bounds_str:
                    # 解析 bounds 获取进度条位置
                    match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
                    if match:
                        x1, y1, x2, y2 = map(int, match.groups())
                        center_y = (y1 + y2) // 2
                        progress_bar_y = center_y
                        progress_bar_y_percent = round(center_y / screen_height * 100, 1)
                        progress_bar_found = True
                        break
            
            # 如果未找到进度条，尝试点击播放区域显示控制栏
            if not progress_bar_found:
                # 点击屏幕中心显示控制栏
                center_x, center_y = screen_width // 2, screen_height // 2
                self.client.u2.click(center_x, center_y)
                time.sleep(0.5)
                
                # 再次查找进度条
                xml_string = self.client.u2.dump_hierarchy(compressed=False)
                root = ET.fromstring(xml_string)
                
                for elem in root.iter():
                    class_name = elem.attrib.get('class', '')
                    resource_id = elem.attrib.get('resource-id', '')
                    bounds_str = elem.attrib.get('bounds', '')
                    
                    is_progress_bar = (
                        'SeekBar' in class_name or 
                        'ProgressBar' in class_name or
                        'progress' in resource_id.lower() or
                        'seek' in resource_id.lower()
                    )
                    
                    if is_progress_bar and bounds_str:
                        match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
                        if match:
                            x1, y1, x2, y2 = map(int, match.groups())
                            center_y = (y1 + y2) // 2
                            progress_bar_y = center_y
                            progress_bar_y_percent = round(center_y / screen_height * 100, 1)
                            progress_bar_found = True
                            break
            
            # 确定使用的高度位置
            if y_percent is not None:
                swipe_y = int(screen_height * y_percent / 100)
                used_y_percent = y_percent
            elif y is not None:
                swipe_y = y
                used_y_percent = round(y / screen_height * 100, 1)
            elif progress_bar_found:
                swipe_y = progress_bar_y
                used_y_percent = progress_bar_y_percent
            else:
                # 默认使用屏幕底部附近（进度条常见位置）
                swipe_y = int(screen_height * 0.91)
                used_y_percent = 91.0
            
            # 计算滑动距离
            swipe_distance = int(screen_width * distance_percent / 100)
            
            # 计算起始和结束位置
            center_x = screen_width // 2
            if direction == 'left':
                start_x = min(center_x + swipe_distance // 2, screen_width - 10)
                end_x = start_x - swipe_distance
                if end_x < 10:
                    end_x = 10
                    start_x = min(end_x + swipe_distance, screen_width - 10)
            else:  # right
                start_x = max(center_x - swipe_distance // 2, 10)
                end_x = start_x + swipe_distance
                if end_x > screen_width - 10:
                    end_x = screen_width - 10
                    start_x = max(end_x - swipe_distance, 10)
            
            # 执行拖动
            self.client.u2.swipe(start_x, swipe_y, end_x, swipe_y, duration=0.5)
            time.sleep(0.3)
            
            # 记录操作
            self._record_swipe(direction)
            
            # 检查应用是否跳转
            app_check = self._check_app_switched()
            return_result = None
            if app_check['switched']:
                return_result = self._return_to_target_app()
            
            # 构建返回消息
            msg = f"✅ 进度条拖动成功: {direction} (高度: {used_y_percent}%, 距离: {distance_percent}%)"
            if not progress_bar_found:
                msg += "\n💡 已自动点击播放区域显示控制栏"
            else:
                msg += "\n💡 进度条已显示，直接拖动"
            
            if app_check['switched']:
                msg += f"\n{app_check['message']}"
                if return_result and return_result.get('success'):
                    msg += f"\n{return_result['message']}"
            
            return {
                "success": True,
                "message": msg,
                "progress_bar_found": progress_bar_found,
                "y_percent": used_y_percent,
                "distance_percent": distance_percent,
                "direction": direction,
                "app_check": app_check,
                "return_to_app": return_result
            }
            
        except Exception as e:
            return {"success": False, "message": f"❌ 拖动进度条失败: {e}"}
    
    # ==================== 应用管理 ====================
    
    async def launch_app(self, package_name: str) -> Dict:
        """启动应用"""
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    ios_client.wda.app_activate(package_name)
            else:
                self.client.u2.app_start(package_name)
            
            await asyncio.sleep(2)
            
            # 记录目标应用包名（用于后续监测应用跳转）
            self.target_package = package_name
            
            # 验证是否成功启动到目标应用
            current = self._get_current_package()
            if current and current != package_name:
                return {
                    "success": False,
                    "message": f"❌ 启动失败：当前应用为 {current}，期望 {package_name}"
                }
            
            self._record_operation('launch_app', package_name=package_name)
            
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": f"❌ 启动失败: {e}"}
    
    def terminate_app(self, package_name: str) -> Dict:
        """终止应用"""
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    ios_client.wda.app_terminate(package_name)
            else:
                self.client.u2.app_stop(package_name)
            return {"success": True}
        except Exception as e:
            return {"success": False, "msg": str(e)}
    
    def list_apps(self, filter_keyword: str = "") -> Dict:
        """列出已安装应用"""
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    # iOS 暂不支持列出所有应用
                    return {
                        "success": True,
                        "apps": [],
                        "count": 0,
                        "message": "💡 iOS 暂不支持列出所有应用，请直接使用 bundle_id 启动"
                    }
            else:
                apps = self.client.u2.app_list()
                if filter_keyword:
                    apps = [app for app in apps if filter_keyword.lower() in app.lower()]
                return {
                    "success": True,
                    "apps": apps[:50],  # 限制返回数量
                    "count": len(apps)
                }
        except Exception as e:
            return {"success": False, "message": f"❌ 获取应用列表失败: {e}"}
    
    # ==================== 设备管理 ====================
    
    def list_devices(self) -> Dict:
        """列出已连接设备"""
        try:
            platform = "ios" if self._is_ios() else "android"
            
            if platform == "ios":
                from .ios_device_manager_wda import IOSDeviceManagerWDA
                manager = IOSDeviceManagerWDA()
                devices = manager.list_devices()
            else:
                from .device_manager import DeviceManager
                manager = DeviceManager()
                devices = manager.list_devices()
            
            return {
                "success": True,
                "platform": platform,
                "devices": devices,
                "count": len(devices)
            }
        except Exception as e:
            return {"success": False, "message": f"❌ 获取设备列表失败: {e}"}
    
    def check_connection(self) -> Dict:
        """检查设备连接"""
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    return {"success": True, "connected": True, "platform": "ios"}
                return {"success": False, "connected": False, "message": "❌ iOS 未连接"}
            else:
                info = self.client.u2.device_info
                return {
                    "success": True,
                    "connected": True,
                    "platform": "android",
                    "device": f"{info.get('brand', '')} {info.get('model', '')}"
                }
        except Exception as e:
            return {"success": False, "connected": False, "message": f"❌ 连接检查失败: {e}"}
    
    # ==================== 辅助工具 ====================
    
    def list_elements(self) -> List[Dict]:
        """列出页面元素（已优化：过滤排版容器，保留功能控件）"""
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'list_elements'):
                    return ios_client.list_elements()
                return [{"error": "iOS 暂不支持元素列表，建议使用截图"}]
            else:
                xml_string = self.client.u2.dump_hierarchy(compressed=False)
                elements = self.client.xml_parser.parse(xml_string)
                
                # 功能控件类型（需要保留）
                FUNCTIONAL_WIDGETS = {
                    'TextView', 'Text', 'Label',  # 文本类
                    'ImageView', 'Image', 'ImageButton',  # 图片类
                    'Button', 'CheckBox', 'RadioButton', 'Switch',  # 交互类
                    'SeekBar', 'ProgressBar', 'RatingBar',  # 滑动/进度类
                    'EditText', 'TextInput',  # 输入类
                    'VideoView', 'WebView',  # 特殊功能类
                    'RecyclerView', 'ListView', 'GridView',  # 列表类
                    'ScrollView', 'NestedScrollView',  # 滚动容器（有实际功能）
                }
                
                # 容器控件类型（需要过滤，除非有业务ID）
                CONTAINER_WIDGETS = {
                    'FrameLayout', 'LinearLayout', 'RelativeLayout',
                    'ViewGroup', 'ConstraintLayout', 'CoordinatorLayout',
                    'CardView', 'View',  # 基础View也可能只是容器
                }
                
                # 装饰类控件关键词（resource_id中包含这些关键词的通常可以过滤）
                # 支持匹配如 qylt_item_short_video_shadow_one 这样的命名
                DECORATIVE_KEYWORDS = {
                    'shadow', 'divider', 'separator', 'line', 'border',
                    'background', 'bg_', '_bg', 'decorative', 'decoration',
                    '_shadow', 'shadow_', '_divider', 'divider_', '_line', 'line_'
                }
                
                # 状态栏相关关键词（这些元素对测试没有意义，直接过滤）
                STATUS_BAR_KEYWORDS = {
                    'status_bar', 'statusbar', 'notification_icon', 'notificationicons',
                    'system_icons', 'statusicons', 'battery', 'wifi_', 'wifi_combo',
                    'wifi_group', 'wifi_signal', 'wifi_in', 'wifi_out', 'signal_',
                    'clock', 'cutout', 'networkspeed', 'speed_container',
                    'carrier', 'operator', 'sim_', 'mobile_signal'
                }
                
                # 系统控件关键词（厂商系统UI元素，对测试没有意义，直接过滤）
                SYSTEM_WIDGET_KEYWORDS = {
                    'system_icon', 'systemicon', 'system_image', 'systemimage',
                    'vivo_', 'vivo_superx', 'superx', 'super_x',
                    'miui_', 'miui_system', 'huawei_', 'emui_',
                    'oppo_', 'coloros_', 'oneplus_', 'realme_',
                    'samsung_', 'oneui_', 'com.android.systemui',
                    'system_ui', 'systemui', 'navigation_bar', 'navigationbar'
                }
                
                # 系统弹窗交互文本（如果元素包含这些文本，即使 resource_id 匹配系统控件，也不过滤）
                # 这些是系统弹窗（权限请求、系统对话框等）的常见按钮文本
                SYSTEM_DIALOG_INTERACTIVE_TEXTS = {
                    '允许', '拒绝', '确定', '取消', '同意', '不同意',
                    '允许访问', '拒绝访问', '始终允许', '仅在使用时允许',
                    '确定', '取消', '是', '否', '好', '知道了',
                    'Allow', 'Deny', 'OK', 'Cancel', 'Yes', 'No',
                    'Accept', 'Reject', 'Grant', 'Deny'
                }
                
                # Token 优化：构建精简元素（只返回非空字段）
                def build_compact_element(resource_id, text, content_desc, bounds, likely_click, class_name):
                    """只返回有值的字段，节省 token"""
                    item = {}
                    if resource_id:
                        # 精简 resource_id，只保留最后一段
                        item['id'] = resource_id.split('/')[-1] if '/' in resource_id else resource_id
                    if text:
                        item['text'] = text
                    if content_desc:
                        item['desc'] = content_desc
                    if bounds:
                        item['bounds'] = bounds
                    if likely_click:
                        item['click'] = True  # 启发式判断可点击
                    # class 精简：只保留关键类型
                    if class_name in ('EditText', 'TextInput', 'Button', 'ImageButton', 'CheckBox', 'Switch'):
                        item['type'] = class_name
                    # 重要：对于 ImageView 等图片类控件，即使没有其他属性，只要有 bounds 就应该返回
                    # 因为 ImageView 可能是关闭按钮、图标等，对测试很重要
                    if not item and bounds and class_name in ('ImageView', 'Image', 'ImageButton'):
                        item['bounds'] = bounds
                        item['type'] = class_name
                    return item
                
                result = []
                for elem in elements:
                    # 获取元素属性
                    class_name = elem.get('class_name', '')
                    resource_id = elem.get('resource_id', '').strip()
                    text = elem.get('text', '').strip()
                    content_desc = elem.get('content_desc', '').strip()
                    bounds = elem.get('bounds', '')
                    clickable = elem.get('clickable', False)
                    focusable = elem.get('focusable', False)
                    scrollable = elem.get('scrollable', False)
                    enabled = elem.get('enabled', True)
                    
                    # 1. 过滤 bounds="[0,0][0,0]" 的视觉隐藏元素
                    if bounds == '[0,0][0,0]':
                        continue
                    
                    # 1.5 过滤状态栏元素（对测试没有意义）
                    if resource_id:
                        resource_id_lower = resource_id.lower()
                        if any(keyword in resource_id_lower for keyword in STATUS_BAR_KEYWORDS):
                            continue
                    
                    # 1.6 过滤系统控件（厂商系统UI元素，对测试没有意义）
                    # 例外：如果元素有明确的交互文本（系统弹窗按钮），不过滤
                    if resource_id:
                        resource_id_lower = resource_id.lower()
                        
                        # 检查是否是系统弹窗的交互按钮（有明确的交互文本）
                        is_system_dialog_button = (
                            text in SYSTEM_DIALOG_INTERACTIVE_TEXTS or
                            content_desc in SYSTEM_DIALOG_INTERACTIVE_TEXTS
                        )
                        
                        # 特殊处理：android:id/ 开头的元素
                        if 'android:id/' in resource_id_lower:
                            # android:id/button1, android:id/button2 等是系统弹窗按钮，应该保留
                            # 只过滤特定的系统UI容器元素
                            android_system_ids_to_filter = [
                                'android:id/statusbarbackground',
                                'android:id/navigationbarbackground'
                            ]
                            # 如果是系统弹窗按钮（有交互文本）或者是按钮类ID，保留
                            if (is_system_dialog_button or 
                                'button' in resource_id_lower or
                                resource_id_lower not in [id.lower() for id in android_system_ids_to_filter]):
                                # 保留，不过滤
                                pass
                            else:
                                # 过滤系统UI容器
                                continue
                        else:
                            # 非 android:id/ 开头的元素，检查是否匹配系统控件关键词
                            # 如果是系统弹窗按钮（有交互文本），不过滤
                            if not is_system_dialog_button:
                                if any(keyword in resource_id_lower for keyword in SYSTEM_WIDGET_KEYWORDS):
                                    continue
                    
                    # 2. 检查是否是功能控件（直接保留）
                    if class_name in FUNCTIONAL_WIDGETS:
                        # 使用启发式判断可点击性（替代不准确的 clickable 属性）
                        likely_click = self._is_likely_clickable(class_name, resource_id, text, content_desc, clickable, bounds)
                        item = build_compact_element(resource_id, text, content_desc, bounds, likely_click, class_name)
                        if item:
                            result.append(item)
                        continue
                    
                    # 3. 检查是否是容器控件
                    if class_name in CONTAINER_WIDGETS:
                        # 容器控件需要检查是否有业务相关的ID
                        has_business_id = self._has_business_id(resource_id)
                        if not has_business_id:
                            # 无业务ID的容器控件，检查是否有其他有意义属性
                            if not (clickable or focusable or scrollable or text or content_desc):
                                # 所有属性都是默认值，过滤掉
                                continue
                        # 有业务ID或其他有意义属性，保留
                        likely_click = self._is_likely_clickable(class_name, resource_id, text, content_desc, clickable, bounds)
                        item = build_compact_element(resource_id, text, content_desc, bounds, likely_click, class_name)
                        if item:
                            result.append(item)
                        continue
                    
                    # 4. 检查是否是装饰类控件
                    if resource_id:
                        resource_id_lower = resource_id.lower()
                        if any(keyword in resource_id_lower for keyword in DECORATIVE_KEYWORDS):
                            # 是装饰类控件，且没有交互属性，过滤掉
                            if not (clickable or focusable or text or content_desc):
                                continue
                    
                    # 5. 检查是否所有属性均为默认值
                    if not (text or content_desc or resource_id or clickable or focusable or scrollable):
                        # 所有属性都是默认值，过滤掉
                        continue
                    
                    # 6. 其他情况：有意义的元素保留
                    likely_click = self._is_likely_clickable(class_name, resource_id, text, content_desc, clickable, bounds)
                    item = build_compact_element(resource_id, text, content_desc, bounds, likely_click, class_name)
                    if item:
                        result.append(item)
                
                # Token 优化：可选限制返回元素数量（默认不限制，确保准确度）
                if TOKEN_OPTIMIZATION and MAX_ELEMENTS > 0 and len(result) > MAX_ELEMENTS:
                    # 仅在用户明确设置 MAX_ELEMENTS_RETURN 时才截断
                    truncated = result[:MAX_ELEMENTS]
                    truncated.append({
                        '_truncated': True,
                        '_total': len(result),
                        '_shown': MAX_ELEMENTS
                    })
                    return truncated
                
                return result
        except Exception as e:
            return [{"error": f"获取元素失败: {e}"}]
    
    def _get_page_texts(self, max_count: int = 15) -> List[str]:
        """获取页面关键文本列表（用于点击后快速确认页面变化）
        
        Args:
            max_count: 最多返回的文本数量
            
        Returns:
            页面上的关键文本列表（去重）
        """
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    # iOS: 获取所有 StaticText 的文本
                    elements = ios_client.wda(type='XCUIElementTypeStaticText').find_elements()
                    texts = set()
                    for elem in elements[:50]:  # 限制扫描数量
                        try:
                            name = elem.name or elem.label
                            if name and len(name) > 1 and len(name) < 50:
                                texts.add(name)
                        except:
                            pass
                    return list(texts)[:max_count]
                return []
            else:
                # Android: 快速扫描 XML 获取文本
                xml_string = self.client.u2.dump_hierarchy(compressed=True)
                import xml.etree.ElementTree as ET
                root = ET.fromstring(xml_string)
                
                texts = set()
                for elem in root.iter():
                    text = elem.get('text', '').strip()
                    desc = elem.get('content-desc', '').strip()
                    # 只收集有意义的文本（长度2-30，非纯数字）
                    for t in [text, desc]:
                        if t and 2 <= len(t) <= 30 and not t.isdigit():
                            texts.add(t)
                    if len(texts) >= max_count * 2:  # 收集足够后停止
                        break
                
                return list(texts)[:max_count]
        except Exception:
            return []
    
    def _has_business_id(self, resource_id: str) -> bool:
        """
        判断resource_id是否是业务相关的ID
        
        业务相关的ID通常包含：
        - 有意义的命名（不是自动生成的）
        - 不包含常见的自动生成模式
        """
        if not resource_id:
            return False
        
        # 自动生成的ID模式（通常可以忽略）
        auto_generated_patterns = [
            r'^android:id/',  # 系统ID
            r':id/\d+',  # 数字ID
            r':id/view_\d+',  # view_数字
            r':id/item_\d+',  # item_数字
        ]
        
        for pattern in auto_generated_patterns:
            if re.search(pattern, resource_id):
                return False
        
        # 如果resource_id有实际内容且不是自动生成的，认为是业务ID
        # 排除一些常见的系统ID
        system_ids = ['android:id/content', 'android:id/statusBarBackground']
        if resource_id in system_ids:
            return False
        
        return True
    
    def _is_likely_clickable(self, class_name: str, resource_id: str, text: str,
                             content_desc: str, clickable: bool, bounds: str) -> bool:
        """
        启发式判断元素是否可能可点击
        
        Android 的 clickable 属性经常不准确，因为：
        1. 点击事件可能设置在父容器上
        2. 使用 onTouchListener 而不是 onClick
        3. RecyclerView item 通过 ItemClickListener 处理
        
        此方法通过多种规则推断元素的真实可点击性
        """
        # 规则1：clickable=true 肯定可点击
        if clickable:
            return True
        
        # 规则2：特定类型的控件通常可点击
        TYPICALLY_CLICKABLE = {
            'Button', 'ImageButton', 'CheckBox', 'RadioButton', 'Switch',
            'ToggleButton', 'FloatingActionButton', 'Chip', 'TabView',
            'EditText', 'TextInput',  # 输入框可点击获取焦点
        }
        if class_name in TYPICALLY_CLICKABLE:
            return True
        
        # 规则3：resource_id 包含可点击关键词
        if resource_id:
            id_lower = resource_id.lower()
            CLICK_KEYWORDS = [
                'btn', 'button', 'click', 'tap', 'submit', 'confirm',
                'cancel', 'close', 'back', 'next', 'prev', 'more',
                'action', 'link', 'menu', 'tab', 'item', 'cell',
                'card', 'avatar', 'icon', 'entry', 'option', 'arrow'
            ]
            for kw in CLICK_KEYWORDS:
                if kw in id_lower:
                    return True
        
        # 规则4：content_desc 包含可点击暗示
        if content_desc:
            desc_lower = content_desc.lower()
            CLICK_HINTS = ['点击', '按钮', '关闭', '返回', '更多', 'click', 'tap', 'button', 'close']
            for hint in CLICK_HINTS:
                if hint in desc_lower:
                    return True
        
        # 规则5：有 resource_id 或 content_desc 的小图标可能可点击
        # （纯 ImageView 不加判断，误判率太高）
        if class_name in ('ImageView', 'Image') and (resource_id or content_desc) and bounds:
            match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
            if match:
                x1, y1, x2, y2 = map(int, match.groups())
                w, h = x2 - x1, y2 - y1
                # 小图标（20-100px）更可能是按钮
                if 20 <= w <= 100 and 20 <= h <= 100:
                    return True
        
        # 规则6：移除（TextView 误判率太高，只依赖上面的规则）
        # 如果有 clickable=true 或 ID/desc 中有关键词，前面的规则已经覆盖
        
        return False
    
    def find_close_button(self) -> Dict:
        """智能查找关闭按钮（不点击，只返回位置）
        
        从元素列表中找最可能的关闭按钮，返回其坐标和百分比位置。
        适用于关闭弹窗广告等场景。
        
        Returns:
            包含关闭按钮位置信息的字典，或截图让 AI 分析
        """
        try:
            import re
            
            if self._is_ios():
                return {"success": False, "msg": "iOS暂不支持"}
            
            # 获取屏幕尺寸
            screen_width = self.client.u2.info.get('displayWidth', 720)
            screen_height = self.client.u2.info.get('displayHeight', 1280)
            
            # 获取元素列表
            xml_string = self.client.u2.dump_hierarchy(compressed=False)
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_string)
            
            # 🔴 先检测是否有弹窗，避免误识别普通页面的按钮
            popup_bounds, popup_confidence = self._detect_popup_with_confidence(
                root, screen_width, screen_height
            )
            
            if popup_bounds is None or popup_confidence < 0.5:
                return {"success": True, "popup": False}
            
            # 关闭按钮特征
            close_texts = ['×', 'X', 'x', '关闭', '取消', 'close', 'Close', '跳过', '知道了', '我知道了']
            candidates = []
            
            for elem in root.iter():
                text = elem.attrib.get('text', '')
                content_desc = elem.attrib.get('content-desc', '')
                bounds_str = elem.attrib.get('bounds', '')
                class_name = elem.attrib.get('class', '')
                clickable = elem.attrib.get('clickable', 'false') == 'true'
                
                if not bounds_str:
                    continue
                
                match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
                if not match:
                    continue
                
                x1, y1, x2, y2 = map(int, match.groups())
                width = x2 - x1
                height = y2 - y1
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                
                # 计算百分比
                x_percent = round(center_x / screen_width * 100, 1)
                y_percent = round(center_y / screen_height * 100, 1)
                
                score = 0
                reason = ""
                
                # 策略1：关闭文本
                if text in close_texts:
                    score = 100
                    reason = f"文本='{text}'"
                
                # 策略2：content-desc 包含关闭关键词
                elif any(kw in content_desc.lower() for kw in ['关闭', 'close', 'dismiss', '跳过']):
                    score = 90
                    reason = f"描述='{content_desc}'"
                
                # 策略3：小尺寸的 clickable 元素（可能是 X 图标）
                elif clickable:
                    min_size = max(20, int(screen_width * 0.03))
                    max_size = max(120, int(screen_width * 0.12))
                    if min_size <= width <= max_size and min_size <= height <= max_size:
                        # 基于位置评分：角落位置加分
                        rel_x = center_x / screen_width
                        rel_y = center_y / screen_height
                        
                        # 右上角得分最高
                        if rel_x > 0.6 and rel_y < 0.5:
                            score = 70 + (rel_x - 0.6) * 50 + (0.5 - rel_y) * 50
                            reason = f"右上角小元素 {width}x{height}px"
                        # 左上角
                        elif rel_x < 0.4 and rel_y < 0.5:
                            score = 60 + (0.4 - rel_x) * 50 + (0.5 - rel_y) * 50
                            reason = f"左上角小元素 {width}x{height}px"
                        # 其他位置的小元素
                        elif 'Image' in class_name:
                            score = 50
                            reason = f"图片元素 {width}x{height}px"
                        else:
                            score = 40
                            reason = f"小型可点击元素 {width}x{height}px"
                
                if score > 0:
                    candidates.append({
                        'score': score,
                        'reason': reason,
                        'bounds': bounds_str,
                        'center_x': center_x,
                        'center_y': center_y,
                        'x_percent': x_percent,
                        'y_percent': y_percent,
                        'size': f"{width}x{height}"
                    })
            
            if not candidates:
                # 没找到，截图让 AI 分析
                screenshot_result = self.take_screenshot(description="找关闭按钮", compress=True)
                return {
                    "success": False,
                    "message": "❌ 元素树未找到关闭按钮，已截图供 AI 分析",
                    "screenshot": screenshot_result.get("screenshot_path", ""),
                    "screen_size": {"width": screen_width, "height": screen_height},
                    "image_size": {
                        "width": screenshot_result.get("image_width"),
                        "height": screenshot_result.get("image_height")
                    },
                    "original_size": {
                        "width": screenshot_result.get("original_img_width"),
                        "height": screenshot_result.get("original_img_height")
                    },
                    "tip": "请分析截图找到 X 关闭按钮，然后调用 mobile_click_by_percent(x_percent, y_percent)"
                }
            
            # 按得分排序
            candidates.sort(key=lambda x: x['score'], reverse=True)
            best = candidates[0]
            
            # Token 优化：只返回最必要的信息
            return {
                "success": True,
                "popup": True,
                "close": {"x": best['x_percent'], "y": best['y_percent']},
                "cmd": f"click_by_percent({best['x_percent']},{best['y_percent']})"
            }
            
        except Exception as e:
            return {"success": False, "msg": str(e)}
    
    def close_popup(self, popup_detected: bool = None, popup_bounds: tuple = None) -> Dict:
        """智能关闭弹窗（改进版）
        
        核心改进：先检测弹窗区域，再在弹窗范围内查找关闭按钮
        
        策略（优先级从高到低）：
        1. 检测弹窗区域（非全屏的大面积容器）
        2. 在弹窗边界内查找关闭相关的文本/描述（×、X、关闭、close 等）
        3. 在弹窗边界内查找小尺寸的 clickable 元素（优先边角位置）
        4. 如果都找不到，截图让 AI 视觉识别
        
        适配策略：
        - X 按钮可能在任意位置（上下左右都支持）
        - 使用百分比坐标记录，跨分辨率兼容
        
        Args:
            popup_detected: 可选，AI已识别到弹窗时为True，跳过弹窗检测
            popup_bounds: 可选，弹窗边界 (x1, y1, x2, y2)，如果AI已识别到弹窗区域可传入
        """
        try:
            import re
            import xml.etree.ElementTree as ET
            
            # 获取屏幕尺寸
            if self._is_ios():
                return {"success": False, "msg": "iOS暂不支持"}
            
            screen_width = self.client.u2.info.get('displayWidth', 720)
            screen_height = self.client.u2.info.get('displayHeight', 1280)
            
            # 获取原始 XML
            xml_string = self.client.u2.dump_hierarchy(compressed=False)
            
            # 关闭按钮的文本特征
            close_texts = ['×', 'X', 'x', '关闭', '取消', 'close', 'Close', 'CLOSE', '跳过', '知道了']
            close_desc_keywords = ['关闭', 'close', 'dismiss', 'cancel', '跳过']
            
            close_candidates = []
            all_clickable_elements = []  # 所有可点击元素（用于兜底策略）
            popup_confidence = 0.0
            
            # 解析 XML
            try:
                root = ET.fromstring(xml_string)
                all_elements = list(root.iter())
                
                # ===== 第一步：检测弹窗区域（如果AI未传入完整弹窗信息）=====
                if popup_bounds is None:
                    # 无论popup_detected是否传入，都需要检测bounds来定位弹窗区域
                    detected_bounds, detected_confidence = self._detect_popup_with_confidence(
                        root, screen_width, screen_height
                    )
                    popup_bounds = detected_bounds
                    popup_confidence = detected_confidence
                    
                    # 如果AI未传入popup_detected，根据检测结果判断
                    if popup_detected is None:
                        popup_detected = popup_bounds is not None and popup_confidence >= 0.6
                    # 如果AI传入了popup_detected=True，但检测不到bounds，仍然使用AI的判断
                    elif popup_detected and popup_bounds is None:
                        # AI说有问题但检测不到，可能是检测算法不够准确，信任AI的判断
                        popup_detected = True
                        popup_confidence = 0.7  # 降低置信度，因为检测不到bounds
                else:
                    # AI已传入popup_bounds，直接使用
                    if popup_detected is None:
                        # 有bounds就认为有弹窗
                        popup_detected = True
                    popup_confidence = 0.8  # AI识别到的弹窗，置信度较高
                
                # 【重要修复】如果没有检测到弹窗区域，只搜索有明确关闭特征的元素（文本、resource-id等）
                # 避免误点击普通页面的右上角图标
                
                # ===== 第二步：在弹窗范围内查找关闭按钮 =====
                for idx, elem in enumerate(all_elements):
                    text = elem.attrib.get('text', '')
                    content_desc = elem.attrib.get('content-desc', '')
                    bounds_str = elem.attrib.get('bounds', '')
                    class_name = elem.attrib.get('class', '')
                    clickable = elem.attrib.get('clickable', 'false') == 'true'
                    resource_id = elem.attrib.get('resource-id', '')
                    
                    if not bounds_str:
                        continue
                    
                    # 解析 bounds
                    match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
                    if not match:
                        continue
                    
                    x1, y1, x2, y2 = map(int, match.groups())
                    width = x2 - x1
                    height = y2 - y1
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    
                    # 计算相对位置（统一在循环开始计算，避免重复计算）
                    rel_x = center_x / screen_width
                    rel_y = center_y / screen_height
                    
                    # 收集所有可点击元素（用于兜底策略：当只有一个可点击元素时点击它）
                    if clickable:
                        all_clickable_elements.append({
                            'bounds': bounds_str,
                            'center_x': center_x,
                            'center_y': center_y,
                            'width': width,
                            'height': height,
                            'text': text,
                            'content_desc': content_desc,
                            'resource_id': resource_id,
                            'class_name': class_name
                        })
                    
                    # 如果检测到弹窗区域，检查元素是否在弹窗范围内或附近
                    in_popup = False
                    popup_edge_bonus = 0
                    is_floating_close = False  # 是否是浮动关闭按钮（在弹窗外部上方）
                    if popup_bounds:
                        px1, py1, px2, py2 = popup_bounds
                        
                        # 关闭按钮可能在弹窗外部（常见设计：X 按钮浮在弹窗右上角外侧）
                        # 扩大搜索范围：弹窗上方 200 像素，右侧 50 像素
                        margin_top = 200  # 上方扩展范围（关闭按钮常在弹窗上方）
                        margin_side = 50  # 左右扩展范围
                        margin_bottom = 30  # 下方扩展范围
                        
                        in_popup = (px1 - margin_side <= center_x <= px2 + margin_side and 
                                   py1 - margin_top <= center_y <= py2 + margin_bottom)
                        
                        # 【新增】兼容第三方广告页面：右上角的 ImageView 即使不在弹窗范围内，也可能是在弹窗上方的关闭按钮
                        # 判断条件：ImageView 位于屏幕右上角（rel_x > 0.85, rel_y < 0.15）且尺寸合适
                        is_top_right_imageview = (
                            'Image' in class_name and
                            not clickable and
                            rel_x > 0.85 and
                            rel_y < 0.15 and
                            15 <= width <= 120 and
                            15 <= height <= 120
                        )
                        
                        # 如果是右上角 ImageView，即使不在弹窗范围内，也认为是关闭按钮候选
                        if is_top_right_imageview:
                            in_popup = True
                            is_floating_close = True  # 标记为浮动关闭按钮
                        
                        # 检查是否是浮动关闭按钮（在弹窗外侧：上方或下方）
                        # 上方浮动关闭按钮（常见：右上角外侧）
                        if center_y < py1 and center_y > py1 - margin_top:
                            if center_x > (px1 + px2) / 2:  # 在弹窗右半部分上方
                                is_floating_close = True
                        # 下方浮动关闭按钮（常见：底部中间外侧）
                        elif center_y > py2 and center_y < py2 + margin_top:
                            # 下方关闭按钮通常在中间位置
                            if abs(center_x - (px1 + px2) / 2) < (px2 - px1) / 2:
                                is_floating_close = True
                        
                        if in_popup:
                            # 计算元素是否在弹窗边缘（关闭按钮通常在边缘）
                            dist_to_top = abs(center_y - py1)
                            dist_to_bottom = abs(center_y - py2)
                            dist_to_left = abs(center_x - px1)
                            dist_to_right = abs(center_x - px2)
                            min_dist = min(dist_to_top, dist_to_bottom, dist_to_left, dist_to_right)
                            
                            # 在弹窗边缘 100 像素内的元素加分
                            if min_dist < 100:
                                popup_edge_bonus = 3.0 * (1 - min_dist / 100)
                        
                        # 浮动关闭按钮（在弹窗上方外侧）给予高额加分
                        if is_floating_close:
                            popup_edge_bonus += 5.0  # 大幅加分
                        # 右上角 ImageView 额外加分（第三方广告页面常见）
                        if is_top_right_imageview:
                            popup_edge_bonus += 2.0  # 额外加分
                    elif not popup_detected:
                        # 没有检测到弹窗时，处理有明确关闭特征的元素
                        # 同时，也考虑底部中央的 clickable 小元素（可能是关闭按钮）
                        # 注意：右上角的 ImageView 只在有弹窗的情况下才识别，避免误识别正常页面的右上角图标
                        
                        # 检查是否有明确的关闭特征（文本、resource-id、content-desc）
                        has_explicit_close_feature = (
                            text in close_texts or
                            any(kw in content_desc.lower() for kw in close_desc_keywords) or
                            'close' in resource_id.lower() or
                            'dismiss' in resource_id.lower() or
                            'cancel' in resource_id.lower()
                        )
                        
                        # 【新增】底部中央的 clickable 小元素也可能是关闭按钮（常见于全屏广告、激励视频等）
                        is_bottom_center_clickable = (
                            clickable and
                            rel_y > 0.75 and  # 底部区域（屏幕下方 25%）
                            0.35 < rel_x < 0.65 and  # 中央区域（屏幕中间 30%）
                            width >= 20 and width <= 150 and  # 合理尺寸
                            height >= 20 and height <= 150
                        )
                        
                        if not has_explicit_close_feature and not is_bottom_center_clickable:
                            continue  # 没有明确关闭特征，且不是底部中央的 clickable 小元素，跳过
                        # 有明确关闭特征或底部中央 clickable 小元素时，允许处理
                        in_popup = True
                    
                    if not in_popup:
                        continue
                    
                    score = 0
                    match_type = ""
                    position = self._get_position_name(rel_x, rel_y)
                    
                    # ===== 策略1：精确匹配关闭文本（最高优先级）=====
                    if text in close_texts:
                        score = 15.0 + popup_edge_bonus
                        match_type = f"text='{text}'"
                    
                    # ===== 策略2：content-desc 包含关闭关键词 =====
                    elif any(kw in content_desc.lower() for kw in close_desc_keywords):
                        score = 12.0 + popup_edge_bonus
                        match_type = f"desc='{content_desc}'"
                    
                    # ===== 策略3：clickable 的小尺寸元素（优先于非 clickable）=====
                    elif clickable:
                        min_size = max(20, int(screen_width * 0.03))
                        max_size = max(150, int(screen_width * 0.15))  # 扩大最大尺寸，兼容更大的关闭按钮
                        if min_size <= width <= max_size and min_size <= height <= max_size:
                            # clickable 元素基础分更高
                            base_score = 8.0
                            # 浮动关闭按钮给予最高分
                            if is_floating_close:
                                base_score = 12.0
                                match_type = "floating_close"
                            # 【新增】底部中央的 clickable 小元素（可能是关闭按钮，常见于全屏广告）
                            elif rel_y > 0.75 and 0.35 < rel_x < 0.65:
                                base_score = 10.0  # 给予较高分数
                                match_type = "bottom_center_close"
                            elif 'Image' in class_name:
                                score = base_score + 2.0
                                match_type = "clickable_image"
                            else:
                                match_type = "clickable"
                            score = base_score + self._get_position_score(rel_x, rel_y) + popup_edge_bonus
                    
                    # ===== 策略4：ImageView/ImageButton 类型的小元素（非 clickable）=====
                    # 【增强】兼容第三方广告页面：右上角的 ImageView 即使 clickable="false" 也识别为关闭按钮
                    elif 'Image' in class_name:
                        min_size = max(15, int(screen_width * 0.02))
                        max_size = max(120, int(screen_width * 0.12))
                        if min_size <= width <= max_size and min_size <= height <= max_size:
                            base_score = 5.0
                            # 右上角的 ImageView 给予更高分数（第三方广告页面常见）
                            if rel_x > 0.85 and rel_y < 0.15:
                                base_score = 8.0  # 提高分数，优先识别
                                match_type = "ImageView_top_right"
                            else:
                                match_type = "ImageView"
                            score = base_score + self._get_position_score(rel_x, rel_y) + popup_edge_bonus
                    
                    # XML 顺序加分（后出现的元素在上层，更可能是弹窗内的元素）
                    if score > 0:
                        xml_order_bonus = idx / len(all_elements) * 2.0  # 最多加 2 分
                        score += xml_order_bonus
                        
                        close_candidates.append({
                            'bounds': bounds_str,
                            'center_x': center_x,
                            'center_y': center_y,
                            'width': width,
                            'height': height,
                            'score': score,
                            'position': position,
                            'match_type': match_type,
                            'text': text,
                            'content_desc': content_desc,
                            'x_percent': round(rel_x * 100, 1),
                            'y_percent': round(rel_y * 100, 1),
                            'in_popup': popup_detected
                        })
                        
            except ET.ParseError:
                pass
            
            if not close_candidates:
                # 兜底策略1：如果检测到弹窗但未找到关闭按钮，且页面元素很少（只有1个可点击元素），直接点击它
                if popup_detected and popup_bounds and len(all_clickable_elements) == 1:
                    single_element = all_clickable_elements[0]
                    self.client.u2.click(single_element['center_x'], single_element['center_y'])
                    time.sleep(0.5)
                    
                    # 检查应用是否跳转
                    app_check = self._check_app_switched()
                    return_result = None
                    if app_check['switched']:
                        return_result = self._return_to_target_app()
                    
                    # 记录操作
                    rel_x = single_element['center_x'] / screen_width
                    rel_y = single_element['center_y'] / screen_height
                    self._record_click('percent', f"{round(rel_x * 100, 1)}%,{round(rel_y * 100, 1)}%", 
                                      round(rel_x * 100, 1), round(rel_y * 100, 1),
                                      element_desc="唯一可点击元素(弹窗兜底)")
                    
                    result = {"success": True, "clicked": True, "method": "single_clickable_fallback"}
                    if app_check['switched']:
                        result["switched"] = True
                        if return_result:
                            result["returned"] = return_result['success']
                    return result
                
                # 兜底策略2：即使未检测到弹窗，如果页面只有一个可点击元素，也尝试点击它（可能是特殊类型的弹窗）
                # 这种情况通常出现在：下载浮层、特殊弹窗等，它们的 resource-id 可能不包含 dialog/popup 等关键词
                if len(all_clickable_elements) == 1:
                    single_element = all_clickable_elements[0]
                    # 检查元素是否占据较大屏幕区域（可能是弹窗）
                    element_area_ratio = (single_element['width'] * single_element['height']) / (screen_width * screen_height)
                    # 如果元素占据屏幕 20% 以上，认为是可能的弹窗
                    if element_area_ratio > 0.2:
                        self.client.u2.click(single_element['center_x'], single_element['center_y'])
                        time.sleep(0.5)
                        
                        # 检查应用是否跳转
                        app_check = self._check_app_switched()
                        return_result = None
                        if app_check['switched']:
                            return_result = self._return_to_target_app()
                        
                        # 记录操作
                        rel_x = single_element['center_x'] / screen_width
                        rel_y = single_element['center_y'] / screen_height
                        self._record_click('percent', f"{round(rel_x * 100, 1)}%,{round(rel_y * 100, 1)}%", 
                                          round(rel_x * 100, 1), round(rel_y * 100, 1),
                                          element_desc="唯一可点击元素(特殊弹窗兜底)")
                        
                        result = {"success": True, "clicked": True, "method": "single_clickable_special_popup_fallback"}
                        if app_check['switched']:
                            result["switched"] = True
                            if return_result:
                                result["returned"] = return_result['success']
                        return result
                
                # 如果没有找到关闭按钮，且不满足兜底条件，返回fallback
                if popup_detected and popup_bounds:
                    return {"success": False, "fallback": "vision", "popup": True}
                return {"success": True, "popup": False}
            
            # 按得分排序，取最可能的
            close_candidates.sort(key=lambda x: x['score'], reverse=True)
            best = close_candidates[0]
            
            # 点击
            self.client.u2.click(best['center_x'], best['center_y'])
            time.sleep(0.5)
            
            # 🎯 关键步骤：检查应用是否跳转，如果跳转说明弹窗去除失败，需要返回目标应用
            app_check = self._check_app_switched()
            return_result = None
            
            if app_check['switched']:
                # 应用已跳转，说明弹窗去除失败，尝试返回目标应用
                return_result = self._return_to_target_app()
            
            # 记录操作
            self._record_click('percent', f"{best['x_percent']}%,{best['y_percent']}%", 
                              best['x_percent'], best['y_percent'],
                              element_desc=f"关闭按钮({best['position']})")
            
            # Token 优化：精简返回值
            result = {"success": True, "clicked": True}
            if app_check['switched']:
                result["switched"] = True
                if return_result:
                    result["returned"] = return_result['success']
            
            return result
            
        except Exception as e:
            return {"success": False, "msg": str(e)}
    
    def _get_position_name(self, rel_x: float, rel_y: float) -> str:
        """根据相对坐标获取位置名称"""
        if rel_y < 0.4:
            if rel_x > 0.6:
                return "右上角"
            elif rel_x < 0.4:
                return "左上角"
            else:
                return "顶部中间"
        elif rel_y > 0.6:
            if rel_x > 0.6:
                return "右下角"
            elif rel_x < 0.4:
                return "左下角"
            else:
                return "底部中间"
        else:
            if rel_x > 0.6:
                return "右侧"
            elif rel_x < 0.4:
                return "左侧"
            else:
                return "中间"
    
    def _get_position_score(self, rel_x: float, rel_y: float) -> float:
        """根据位置计算额外得分（角落位置加分更多）"""
        # 弹窗关闭按钮常见位置得分：右上角 > 左上角 > 底部中间 > 其他角落
        if rel_y < 0.4:  # 上半部分
            if rel_x > 0.6:  # 右上角
                return 2.0 + (rel_x - 0.6) + (0.4 - rel_y)
            elif rel_x < 0.4:  # 左上角
                return 1.5 + (0.4 - rel_x) + (0.4 - rel_y)
            else:  # 顶部中间
                return 1.0
        elif rel_y > 0.6:  # 下半部分
            if 0.3 < rel_x < 0.7:  # 底部中间
                return 1.2 + (1 - abs(rel_x - 0.5) * 2)
            else:  # 底部角落
                return 0.8
        else:  # 中间区域
            return 0.5

    def _detect_popup_with_confidence(self, root, screen_width: int, screen_height: int) -> tuple:
        """严格的弹窗检测 - 使用置信度评分，避免误识别普通页面
        
        真正的弹窗特征：
        1. class 名称包含 Dialog/Popup/Alert/Modal/BottomSheet（强特征）
        2. resource-id 包含 dialog/popup/alert/modal（强特征）
        3. 有遮罩层（大面积半透明 View 在弹窗之前）
        4. 居中显示且非全屏
        5. XML 层级靠后且包含可交互元素
        
        Returns:
            (popup_bounds, confidence) 或 (None, 0)
            confidence >= 0.6 才认为是弹窗
        """
        import re
        
        screen_area = screen_width * screen_height
        
        # 收集所有元素信息
        all_elements = []
        for idx, elem in enumerate(root.iter()):
            bounds_str = elem.attrib.get('bounds', '')
            if not bounds_str:
                continue
            
            match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
            if not match:
                continue
            
            x1, y1, x2, y2 = map(int, match.groups())
            width = x2 - x1
            height = y2 - y1
            area = width * height
            
            class_name = elem.attrib.get('class', '')
            resource_id = elem.attrib.get('resource-id', '')
            clickable = elem.attrib.get('clickable', 'false') == 'true'
            
            # 检查是否是关闭按钮
            is_close_button = (
                'close' in resource_id.lower() or 
                'dismiss' in resource_id.lower() or
                'cancel' in resource_id.lower() or
                '×' in elem.attrib.get('text', '') or
                'X' in elem.attrib.get('text', '')
            )
            
            all_elements.append({
                'idx': idx,
                'bounds': (x1, y1, x2, y2),
                'width': width,
                'height': height,
                'area': area,
                'area_ratio': area / screen_area if screen_area > 0 else 0,
                'class': class_name,
                'resource_id': resource_id,
                'clickable': clickable,
                'center_x': (x1 + x2) // 2,
                'center_y': (y1 + y2) // 2,
                'is_close_button': is_close_button,
            })
        
        if not all_elements:
            return None, 0
        
        # 弹窗检测关键词
        dialog_class_keywords = ['Dialog', 'Popup', 'Alert', 'Modal', 'BottomSheet', 'PopupWindow']
        dialog_id_keywords = ['dialog', 'popup', 'alert', 'modal', 'bottom_sheet', 'overlay', 'mask']
        # 广告弹窗关键词（全屏广告、激励视频等）
        ad_popup_keywords = ['ad_close', 'ad_button', 'full_screen', 'interstitial', 'reward', 'close_icon', 'close_btn']
        
        popup_candidates = []
        has_mask_layer = False
        mask_idx = -1
        
        for elem in all_elements:
            x1, y1, x2, y2 = elem['bounds']
            class_name = elem['class']
            resource_id = elem['resource_id']
            area_ratio = elem['area_ratio']
            
            # 检测遮罩层（大面积、几乎全屏、通常是 FrameLayout/View）
            if area_ratio > 0.85 and elem['width'] >= screen_width * 0.95:
                # 可能是遮罩层，记录位置
                if 'FrameLayout' in class_name or 'View' in class_name:
                    has_mask_layer = True
                    mask_idx = elem['idx']
            
            # 先检查是否有强弹窗特征（用于后续判断）
            has_strong_popup_feature = (
                any(kw in class_name for kw in dialog_class_keywords) or
                any(kw in resource_id.lower() for kw in dialog_id_keywords) or
                any(kw in resource_id.lower() for kw in ad_popup_keywords)  # 广告弹窗关键词
            )
            
            # 检查是否有子元素是关闭按钮（作为弹窗特征）
            has_close_button_child = False
            elem_bounds = elem['bounds']
            for other_elem in all_elements:
                if other_elem['idx'] == elem['idx']:
                    continue
                if other_elem['is_close_button']:
                    # 检查关闭按钮是否在这个元素范围内
                    ox1, oy1, ox2, oy2 = other_elem['bounds']
                    ex1, ey1, ex2, ey2 = elem_bounds
                    if ex1 <= ox1 and ey1 <= oy1 and ex2 >= ox2 and ey2 >= oy2:
                        has_close_button_child = True
                        break
            
            # 检查是否有右上角的 ImageView 关闭按钮（全屏广告页常见）
            has_top_right_close = False
            if area_ratio > 0.9:  # 全屏元素才检查
                for other_elem in all_elements:
                    if other_elem['idx'] == elem['idx']:
                        continue
                    # 检查是否是右上角的 ImageView
                    ox1, oy1, ox2, oy2 = other_elem['bounds']
                    o_center_x = other_elem['center_x']
                    o_center_y = other_elem['center_y']
                    o_width = other_elem['width']
                    o_height = other_elem['height']
                    o_class = other_elem['class']
                    
                    rel_x = o_center_x / screen_width
                    rel_y = o_center_y / screen_height
                    
                    # 右上角的 ImageView（即使 clickable="false"）
                    if ('Image' in o_class and
                        rel_x > 0.85 and rel_y < 0.15 and
                        15 <= o_width <= 120 and 15 <= o_height <= 120):
                        # 检查是否在当前元素范围内或附近
                        if (ex1 <= ox1 and ey1 <= oy1 and ex2 >= ox2 and ey2 >= oy2) or \
                           (abs(ex2 - ox1) < 50 and abs(ey1 - oy2) < 50):  # 在元素右上角附近
                            has_top_right_close = True
                            break
            
            # 【特殊处理】全屏广告页：如果面积 > 90% 但有关闭按钮或广告特征，也识别为弹窗
            is_fullscreen_ad = (
                area_ratio > 0.9 and
                (
                    # 有关闭按钮作为子元素
                    has_close_button_child or
                    # 有右上角的 ImageView 关闭按钮
                    has_top_right_close or
                    # 有广告相关的强特征
                    any(kw in resource_id.lower() for kw in ad_popup_keywords)
                )
            )
            
            # 如果不是全屏广告页，跳过全屏元素
            if area_ratio > 0.9 and not is_fullscreen_ad:
                continue
            
            # 跳过太小的元素
            if area_ratio < 0.05:
                continue
            
            # 跳过状态栏区域
            if y1 < 50:
                continue
            
            # 【非弹窗特征】如果元素包含底部导航栏（底部tab），则不是弹窗
            # 底部导航栏通常在屏幕底部，高度约100-200像素
            if y2 > screen_height * 0.85:
                # 检查是否包含tab相关的resource-id或class
                if 'tab' in resource_id.lower() or 'Tab' in class_name or 'navigation' in resource_id.lower():
                    continue  # 跳过底部导航栏
            
            # 【非弹窗特征】如果元素包含顶部搜索栏，则不是弹窗
            if y1 < screen_height * 0.15:
                if 'search' in resource_id.lower() or 'Search' in class_name:
                    continue  # 跳过顶部搜索栏
            
            # 【非弹窗特征】如果元素包含明显的页面内容特征，则不是弹窗
            # 检查是否包含视频播放器、内容列表等页面元素
            page_content_keywords = ['video', 'player', 'recycler', 'list', 'scroll', 'viewpager', 'fragment']
            if any(kw in resource_id.lower() or kw in class_name.lower() for kw in page_content_keywords):
                # 如果面积很大且没有强弹窗特征，则不是弹窗
                if area_ratio > 0.6 and not has_strong_popup_feature:
                    continue
            
            # 【非弹窗特征】如果元素面积过大（接近全屏），即使居中也不应该是弹窗
            # 真正的弹窗通常不会超过屏幕的60%
            # 对于面积 > 0.6 的元素，如果没有强特征，直接跳过（避免误判首页内容区域）
            if area_ratio > 0.6 and not has_strong_popup_feature:
                continue  # 跳过大面积非弹窗元素（接近全屏的内容区域，如首页视频播放区域）
            
            # 对于面积 > 0.7 的元素，即使有强特征也要更严格
            if area_ratio > 0.7:
                # 需要非常强的特征才认为是弹窗
                if not has_strong_popup_feature:
                    continue
            
            confidence = 0.0
            
            # 【强特征】class 名称包含弹窗关键词 (+0.5)
            if any(kw in class_name for kw in dialog_class_keywords):
                confidence += 0.5
            
            # 【强特征】resource-id 包含弹窗关键词 (+0.4)
            if any(kw in resource_id.lower() for kw in dialog_id_keywords):
                confidence += 0.4
            
            # 【强特征】resource-id 包含广告弹窗关键词 (+0.4)
            if any(kw in resource_id.lower() for kw in ad_popup_keywords):
                confidence += 0.4
            
            # 【强特征】包含关闭按钮作为子元素 (+0.3)
            if has_close_button_child:
                confidence += 0.3
            
            # 【强特征】全屏广告页且有右上角关闭按钮 (+0.4)
            if is_fullscreen_ad and has_top_right_close:
                confidence += 0.4
            
            # 【中等特征】居中显示 (+0.2)
            # 但如果没有强特征，降低权重
            center_x = elem['center_x']
            center_y = elem['center_y']
            is_centered_x = abs(center_x - screen_width / 2) < screen_width * 0.15
            is_centered_y = abs(center_y - screen_height / 2) < screen_height * 0.25
            
            has_strong_feature = (
                any(kw in class_name for kw in dialog_class_keywords) or
                any(kw in resource_id.lower() for kw in dialog_id_keywords) or
                any(kw in resource_id.lower() for kw in ad_popup_keywords) or
                has_close_button_child or
                (is_fullscreen_ad and has_top_right_close)  # 全屏广告页且有右上角关闭按钮
            )
            
            if is_centered_x and is_centered_y:
                if has_strong_feature:
                    confidence += 0.2
                else:
                    confidence += 0.1  # 没有强特征时降低权重
            elif is_centered_x:
                if has_strong_feature:
                    confidence += 0.1
                else:
                    confidence += 0.05  # 没有强特征时降低权重
            
            # 【中等特征】非全屏但有一定大小 (+0.15)
            # 但如果没有强特征，降低权重
            if 0.15 < area_ratio < 0.75:
                if has_strong_feature:
                    confidence += 0.15
                else:
                    confidence += 0.08  # 没有强特征时降低权重
            
            # 【弱特征】XML 顺序靠后（在视图层级上层）(+0.1)
            if elem['idx'] > len(all_elements) * 0.5:
                confidence += 0.1
            
            # 【弱特征】有遮罩层且在遮罩层之后 (+0.15)
            if has_mask_layer and elem['idx'] > mask_idx:
                confidence += 0.15
            
            # 只有达到阈值才加入候选
            if confidence >= 0.3:
                popup_candidates.append({
                    'bounds': elem['bounds'],
                    'confidence': confidence,
                    'class': class_name,
                    'resource_id': resource_id,
                    'idx': elem['idx']
                })
        
        if not popup_candidates:
            return None, 0
        
        # 选择置信度最高的
        popup_candidates.sort(key=lambda x: (x['confidence'], x['idx']), reverse=True)
        best = popup_candidates[0]
        
        # 更严格的阈值：只有置信度 >= 0.7 才返回弹窗
        # 如果没有强特征（class或resource-id包含弹窗关键词），需要更高的置信度
        has_strong_feature = (
            any(kw in best['class'] for kw in dialog_class_keywords) or
            any(kw in best['resource_id'].lower() for kw in dialog_id_keywords) or
            any(kw in best['resource_id'].lower() for kw in ad_popup_keywords)
        )
        
        if has_strong_feature:
            # 有强特征时，阈值0.7
            threshold = 0.7
        else:
            # 没有强特征时，阈值0.85（更严格）
            threshold = 0.85
        
        if best['confidence'] >= threshold:
            return best['bounds'], best['confidence']
        
        return None, best['confidence']
    
    def start_toast_watch(self) -> Dict:
        """开始监听 Toast（仅 Android）
        
        ⚠️ 必须在执行操作之前调用！
        
        正确流程：
        1. 调用 mobile_start_toast_watch() 开始监听
        2. 执行操作（如点击提交按钮）
        3. 调用 mobile_get_toast() 获取 Toast 内容
        
        Returns:
            监听状态
        """
        if self._is_ios():
            return {
                "success": False,
                "message": "❌ iOS 不支持 Toast 检测，Toast 是 Android 特有功能"
            }
        
        try:
            # 清除缓存并开始监听
            self.client.u2.toast.reset()
            return {
                "success": True,
                "message": "✅ Toast 监听已开启，请立即执行操作，然后调用 mobile_get_toast 获取结果"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"❌ 开启 Toast 监听失败: {e}"
            }
    
    def get_toast(self, timeout: float = 5.0, reset_first: bool = False) -> Dict:
        """获取 Toast 消息（仅 Android）
        
        Toast 是 Android 系统级的短暂提示消息，常用于显示操作结果。
        
        ⚠️ 推荐用法（两步走）：
        1. 先调用 mobile_start_toast_watch() 开始监听
        2. 执行操作（如点击提交按钮）
        3. 调用 mobile_get_toast() 获取 Toast
        
        或者设置 reset_first=True，会自动 reset 后等待（适合操作已自动触发的场景）
        
        Args:
            timeout: 等待 Toast 出现的超时时间（秒），默认 5 秒
            reset_first: 是否先 reset（清除旧缓存），默认 False
        
        Returns:
            包含 Toast 消息的字典
        """
        if self._is_ios():
            return {
                "success": False,
                "message": "❌ iOS 不支持 Toast 检测，Toast 是 Android 特有功能"
            }
        
        try:
            if reset_first:
                # 清除旧缓存，适合等待即将出现的 Toast
                self.client.u2.toast.reset()
            
            # 等待并获取 Toast 消息
            toast_message = self.client.u2.toast.get_message(
                wait_timeout=timeout,
                default=None
            )
            
            if toast_message:
                return {
                    "success": True,
                    "toast_found": True,
                    "message": toast_message,
                    "tip": "Toast 消息获取成功"
                }
            else:
                return {
                    "success": True,
                    "toast_found": False,
                    "message": None,
                    "tip": f"在 {timeout} 秒内未检测到 Toast。提示：先调用 mobile_start_toast_watch，再执行操作，最后调用此工具"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"❌ 获取 Toast 失败: {e}"
            }
    
    def assert_toast(self, expected_text: str, timeout: float = 5.0, contains: bool = True) -> Dict:
        """断言 Toast 消息（仅 Android）
        
        等待 Toast 出现并验证内容是否符合预期。
        
        ⚠️ 推荐用法：先调用 mobile_start_toast_watch，再执行操作，最后调用此工具
        
        Args:
            expected_text: 期望的 Toast 文本
            timeout: 等待超时时间（秒）
            contains: True 表示包含匹配，False 表示精确匹配
        
        Returns:
            断言结果
        """
        if self._is_ios():
            return {
                "success": False,
                "passed": False,
                "message": "❌ iOS 不支持 Toast 检测"
            }
        
        try:
            # 获取 Toast（不 reset，假设之前已经调用过 start_toast_watch）
            toast_message = self.client.u2.toast.get_message(
                wait_timeout=timeout,
                default=None
            )
            
            if toast_message is None:
                return {
                    "success": True,
                    "passed": False,
                    "expected": expected_text,
                    "actual": None,
                    "message": f"❌ 断言失败：未检测到 Toast 消息"
                }
            
            # 匹配检查
            if contains:
                passed = expected_text in toast_message
                match_type = "包含"
            else:
                passed = expected_text == toast_message
                match_type = "精确"
            
            if passed:
                return {
                    "success": True,
                    "passed": True,
                    "expected": expected_text,
                    "actual": toast_message,
                    "match_type": match_type,
                    "message": f"✅ Toast 断言通过：'{toast_message}'"
                }
            else:
                return {
                    "success": True,
                    "passed": False,
                    "expected": expected_text,
                    "actual": toast_message,
                    "match_type": match_type,
                    "message": f"❌ Toast 断言失败：期望 '{expected_text}'，实际 '{toast_message}'"
                }
        except Exception as e:
            return {
                "success": False,
                "passed": False,
                "message": f"❌ Toast 断言异常: {e}"
            }
    
    def assert_text(self, text: str) -> Dict:
        """检查页面是否包含文本（支持精确匹配和包含匹配）"""
        try:
            exists = False
            match_type = ""
            
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    # 先尝试精确匹配
                    if ios_client.wda(name=text).exists or ios_client.wda(label=text).exists:
                        exists = True
                        match_type = "精确匹配"
                    # 再尝试包含匹配
                    elif ios_client.wda(nameContains=text).exists or ios_client.wda(labelContains=text).exists:
                        exists = True
                        match_type = "包含匹配"
            else:
                # Android: 先尝试精确匹配
                if self.client.u2(text=text).exists():
                    exists = True
                    match_type = "精确匹配"
                # 再尝试包含匹配
                elif self.client.u2(textContains=text).exists():
                    exists = True
                    match_type = "包含匹配"
            
            if exists:
                message = f"✅ 文本'{text}' 存在（{match_type}）"
            else:
                message = f"❌ 文本'{text}' 不存在"
            
            return {
                "success": True,
                "found": exists,
                "text": text,
                "match_type": match_type if exists else None,
                "message": message
            }
        except Exception as e:
            return {"success": False, "message": f"❌ 断言失败: {e}"}
    
    # ==================== 脚本生成 ====================
    
    def get_operation_history(self, limit: Optional[int] = None) -> Dict:
        """获取操作历史"""
        history = self.operation_history
        if limit:
            history = history[-limit:]
        return {
            "success": True,
            "count": len(history),
            "total": len(self.operation_history),
            "operations": history
        }
    
    def clear_operation_history(self) -> Dict:
        """清空操作历史"""
        count = len(self.operation_history)
        self.operation_history = []
        return {"success": True, "message": f"✅ 已清空 {count} 条记录"}
    
    def generate_test_script(self, test_name: str, package_name: str, filename: str) -> Dict:
        """生成 pytest 测试脚本（带智能等待、广告处理和跨设备兼容）
        
        优化：
        1. 坐标点击自动转换为百分比定位（跨分辨率兼容）
        2. 优先使用 ID/文本定位（最稳定）
        3. 百分比定位作为坐标的替代方案
        """
        if not self.operation_history:
            return {"success": False, "message": "❌ 没有操作历史，请先执行一些操作"}
        
        # 生成脚本
        safe_name = re.sub(r'[^\w\s-]', '', test_name).strip().replace(' ', '_')
        # 确保 safe_name 不为空，否则使用默认名称
        if not safe_name:
            safe_name = 'generated_case'
        
        # 提前处理文件名，确保文档字符串中的文件名正确
        if not filename.endswith('.py'):
            filename = f"{filename}.py"
        if not filename.startswith('test_'):
            filename = f"test_{filename}"
        
        script_lines = [
            "#!/usr/bin/env python3",
            "# -*- coding: utf-8 -*-",
            f'"""',
            f"测试用例: {test_name}",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "定位策略（按优先级）：",
            "1. 文本定位 - 最稳定，跨设备兼容",
            "2. ID 定位 - 稳定，跨设备兼容",
            "3. 百分比定位 - 跨分辨率兼容（坐标自动转换）",
            "",
            "运行方式：",
            f"  pytest {filename} -v        # 使用 pytest 运行",
            f"  python {filename}           # 直接运行",
            f'"""',
            "import time",
            "import pytest",
            "import uiautomator2 as u2",
            "",
            f'PACKAGE_NAME = "{package_name}"',
            "",
            "# === 配置（根据 App 情况调整）===",
            "LAUNCH_WAIT = 3        # 启动后等待时间（秒）",
            "CLOSE_AD_ON_LAUNCH = True  # 是否尝试关闭启动广告",
            "AD_CLOSE_KEYWORDS = ['关闭', '跳过', 'Skip', 'Close', '×', 'X', '我知道了', '稍后再说']",
            "",
            "",
            "def smart_wait(d, seconds=1):",
            '    """等待页面稳定"""',
            "    time.sleep(seconds)",
            "",
            "",
            "def close_ad_if_exists(d, quick=False):",
            '    """尝试关闭广告弹窗（quick=True 时只检查常见的）"""',
            "    keywords = AD_CLOSE_KEYWORDS[:3] if quick else AD_CLOSE_KEYWORDS",
            "    for keyword in keywords:",
            "        elem = d(textContains=keyword)",
            "        if elem.exists(timeout=0.3):  # 缩短超时",
            "            try:",
            "                elem.click()",
            "                print(f'  📢 关闭广告: {keyword}')",
            "                time.sleep(0.3)",
            "                return True",
            "            except:",
            "                pass",
            "    return False",
            "",
            "",
            "def safe_click(d, selector, timeout=3):",
            '    """安全点击（带等待）"""',
            "    try:",
            "        if selector.exists(timeout=timeout):",
            "            selector.click()",
            "            return True",
            "        return False",
            "    except Exception as e:",
            "        print(f'  ⚠️ 点击失败: {e}')",
            "        return False",
            "",
            "",
            "def click_by_percent(d, x_percent, y_percent):",
            '    """',
            '    百分比点击（跨分辨率兼容）',
            '    ',
            '    原理：屏幕左上角 (0%, 0%)，右下角 (100%, 100%)',
            '    优势：同样的百分比在不同分辨率设备上都能点到相同相对位置',
            '    """',
            "    info = d.info",
            "    width = info.get('displayWidth', 0)",
            "    height = info.get('displayHeight', 0)",
            "    x = int(width * x_percent / 100)",
            "    y = int(height * y_percent / 100)",
            "    d.click(x, y)",
            "    return True",
            "",
            "",
            "def long_press_by_percent(d, x_percent, y_percent, duration=1.0):",
            '    """',
            '    百分比长按（跨分辨率兼容）',
            '    ',
            '    原理：屏幕左上角 (0%, 0%)，右下角 (100%, 100%)',
            '    优势：同样的百分比在不同分辨率设备上都能长按到相同相对位置',
            '    """',
            "    info = d.info",
            "    width = info.get('displayWidth', 0)",
            "    height = info.get('displayHeight', 0)",
            "    x = int(width * x_percent / 100)",
            "    y = int(height * y_percent / 100)",
            "    d.long_click(x, y, duration=duration)",
            "    return True",
            "",
            "",
            "def swipe_direction(d, direction):",
            '    """',
            '    通用滑动方法（兼容所有 uiautomator2 版本）',
            '    ',
            '    Args:',
            '        d: uiautomator2 设备对象',
            '        direction: 滑动方向 (up/down/left/right)',
            '    """',
            "    info = d.info",
            "    width = info.get('displayWidth', 0)",
            "    height = info.get('displayHeight', 0)",
            "    cx, cy = width // 2, height // 2",
            "    ",
            "    if direction == 'up':",
            "        d.swipe(cx, int(height * 0.8), cx, int(height * 0.3))",
            "    elif direction == 'down':",
            "        d.swipe(cx, int(height * 0.3), cx, int(height * 0.8))",
            "    elif direction == 'left':",
            "        d.swipe(int(width * 0.8), cy, int(width * 0.2), cy)",
            "    elif direction == 'right':",
            "        d.swipe(int(width * 0.2), cy, int(width * 0.8), cy)",
            "    return True",
            "",
            "",
            "# ========== pytest fixture ==========",
            "@pytest.fixture(scope='function')",
            "def device():",
            '    """pytest fixture: 连接设备并启动应用"""',
            "    d = u2.connect()",
            "    d.implicitly_wait(10)",
            "    d.app_start(PACKAGE_NAME)",
            "    time.sleep(LAUNCH_WAIT)",
            "    if CLOSE_AD_ON_LAUNCH:",
            "        close_ad_if_exists(d)",
            "    yield d",
            "    # 测试结束后可选择关闭应用",
            "    # d.app_stop(PACKAGE_NAME)",
            "",
            "",
            f"def test_{safe_name}(device):",
            '    """测试用例主函数"""',
            "    d = device",
            "    ",
        ]
        
        # 生成操作代码（使用标准记录格式，逻辑更简洁）
        step_num = 0
        for op in self.operation_history:
            action = op.get('action')
            
            # 跳过 launch_app（脚本头部已经有 app_start）
            if action == 'launch_app':
                continue
            
            step_num += 1
            
            if action == 'click':
                # 新格式：使用 locator_type 和 locator_value
                locator_type = op.get('locator_type', '')
                locator_value = op.get('locator_value', '')
                locator_attr = op.get('locator_attr', 'text')
                element_desc = op.get('element_desc', '')
                x_pct = op.get('x_percent', 0)
                y_pct = op.get('y_percent', 0)
                
                # 转义单引号
                value_escaped = locator_value.replace("'", "\\'") if locator_value else ''
                
                if locator_type == 'text':
                    # 文本定位（最稳定）
                    script_lines.append(f"    # 步骤{step_num}: 点击 '{element_desc}' (文本定位)")
                    if locator_attr == 'description':
                        script_lines.append(f"    safe_click(d, d(description='{value_escaped}'))")
                    elif locator_attr == 'descriptionContains':
                        script_lines.append(f"    safe_click(d, d(descriptionContains='{value_escaped}'))")
                    elif locator_attr == 'textContains':
                        script_lines.append(f"    safe_click(d, d(textContains='{value_escaped}'))")
                    else:
                        script_lines.append(f"    safe_click(d, d(text='{value_escaped}'))")
                elif locator_type == 'id':
                    # ID 定位（稳定）
                    script_lines.append(f"    # 步骤{step_num}: 点击 '{element_desc}' (ID定位)")
                    script_lines.append(f"    safe_click(d, d(resourceId='{value_escaped}'))")
                elif locator_type == 'percent':
                    # 百分比定位（跨分辨率兼容）
                    script_lines.append(f"    # 步骤{step_num}: 点击 '{element_desc}' (百分比定位)")
                    script_lines.append(f"    click_by_percent(d, {x_pct}, {y_pct})")
                else:
                    # 兼容旧格式
                    ref = op.get('ref', '')
                    if ref:
                        ref_escaped = ref.replace("'", "\\'")
                        script_lines.append(f"    # 步骤{step_num}: 点击 '{ref}'")
                        script_lines.append(f"    safe_click(d, d(text='{ref_escaped}'))")
                    else:
                        continue
                
                script_lines.append("    time.sleep(0.5)")
                script_lines.append("    ")
            
            elif action == 'input':
                text = op.get('text', '')
                locator_type = op.get('locator_type', '')
                locator_value = op.get('locator_value', '')
                x_pct = op.get('x_percent', 0)
                y_pct = op.get('y_percent', 0)
                
                text_escaped = text.replace("'", "\\'")
                value_escaped = locator_value.replace("'", "\\'") if locator_value else ''
                
                if locator_type == 'id':
                    script_lines.append(f"    # 步骤{step_num}: 输入 '{text}' (ID定位)")
                    script_lines.append(f"    d(resourceId='{value_escaped}').set_text('{text_escaped}')")
                elif locator_type == 'class':
                    script_lines.append(f"    # 步骤{step_num}: 输入 '{text}' (类名定位)")
                    script_lines.append(f"    d(className='android.widget.EditText').set_text('{text_escaped}')")
                elif x_pct > 0 and y_pct > 0:
                    script_lines.append(f"    # 步骤{step_num}: 点击后输入 '{text}'")
                    script_lines.append(f"    click_by_percent(d, {x_pct}, {y_pct})")
                    script_lines.append("    time.sleep(0.3)")
                    script_lines.append(f"    d.send_keys('{text_escaped}')")
                else:
                    # 兼容旧格式
                    ref = op.get('ref', '')
                    if ref:
                        script_lines.append(f"    # 步骤{step_num}: 输入 '{text}'")
                        script_lines.append(f"    d(resourceId='{ref}').set_text('{text_escaped}')")
                    else:
                        continue
                
                script_lines.append("    time.sleep(0.5)")
                script_lines.append("    ")
            
            elif action == 'long_press':
                locator_type = op.get('locator_type', '')
                locator_value = op.get('locator_value', '')
                locator_attr = op.get('locator_attr', 'text')
                element_desc = op.get('element_desc', '')
                duration = op.get('duration', 1.0)
                x_pct = op.get('x_percent', 0)
                y_pct = op.get('y_percent', 0)
                
                value_escaped = locator_value.replace("'", "\\'") if locator_value else ''
                
                if locator_type == 'text':
                    script_lines.append(f"    # 步骤{step_num}: 长按 '{element_desc}'")
                    if locator_attr == 'description':
                        script_lines.append(f"    d(description='{value_escaped}').long_click(duration={duration})")
                    else:
                        script_lines.append(f"    d(text='{value_escaped}').long_click(duration={duration})")
                elif locator_type == 'id':
                    script_lines.append(f"    # 步骤{step_num}: 长按 '{element_desc}'")
                    script_lines.append(f"    d(resourceId='{value_escaped}').long_click(duration={duration})")
                elif locator_type == 'percent':
                    script_lines.append(f"    # 步骤{step_num}: 长按 '{element_desc}'")
                    script_lines.append(f"    long_press_by_percent(d, {x_pct}, {y_pct}, duration={duration})")
                else:
                    # 兼容旧格式
                    ref = op.get('ref', '')
                    if ref:
                        ref_escaped = ref.replace("'", "\\'")
                        script_lines.append(f"    # 步骤{step_num}: 长按 '{ref}'")
                        script_lines.append(f"    d(text='{ref_escaped}').long_click(duration={duration})")
                    else:
                        continue
                
                script_lines.append("    time.sleep(0.5)")
                script_lines.append("    ")
            
            elif action == 'swipe':
                direction = op.get('direction', 'up')
                script_lines.append(f"    # 步骤{step_num}: 滑动 {direction}")
                script_lines.append(f"    swipe_direction(d, '{direction}')")
                script_lines.append("    time.sleep(0.5)")
                script_lines.append("    ")
            
            elif action == 'press_key':
                key = op.get('key', 'enter')
                script_lines.append(f"    # 步骤{step_num}: 按键 {key}")
                script_lines.append(f"    d.press('{key}')")
                script_lines.append("    time.sleep(0.5)")
                script_lines.append("    ")
            
            elif action == 'wait':
                seconds = op.get('seconds', 1)
                script_lines.append(f"    # 步骤{step_num}: 等待 {seconds} 秒")
                script_lines.append(f"    time.sleep({seconds})")
                script_lines.append("    ")
        
        script_lines.extend([
            "    print('✅ 测试完成')",
            "",
            "",
            "# ========== 直接运行入口 ==========",
            "if __name__ == '__main__':",
            "    # 直接运行时，手动创建设备连接",
            "    _d = u2.connect()",
            "    _d.implicitly_wait(10)",
            "    _d.app_start(PACKAGE_NAME)",
            "    time.sleep(LAUNCH_WAIT)",
            "    if CLOSE_AD_ON_LAUNCH:",
            "        close_ad_if_exists(_d)",
            f"    test_{safe_name}(_d)",
        ])
        
        script = '\n'.join(script_lines)
        
        # 保存文件
        output_dir = Path("tests")
        output_dir.mkdir(exist_ok=True)
        
        file_path = output_dir / filename
        file_path.write_text(script, encoding='utf-8')
        
        return {
            "success": True,
            "file_path": str(file_path),
            "message": f"✅ 脚本已生成: {file_path}\n💡 运行方式: pytest {file_path} -v 或 python {file_path}",
            "operations_count": len(self.operation_history),
            "preview": script[:500] + "..."
        }

    # ========== 模板匹配功能 ==========
    
    def template_match_close(self, screenshot_path: Optional[str] = None, threshold: float = 0.75) -> Dict:
        """使用模板匹配查找关闭按钮
        
        基于 OpenCV 模板匹配，从预设的X号模板库中查找匹配项。
        比 AI 视觉识别更精准、更快速。
        
        Args:
            screenshot_path: 截图路径（可选，不提供则自动截图）
            threshold: 匹配阈值 0-1，越高越严格，默认0.75
            
        Returns:
            匹配结果，包含坐标和点击命令
        """
        try:
            from .template_matcher import TemplateMatcher
            
            # 如果没有提供截图，先截图
            if screenshot_path is None:
                screenshot_result = self.take_screenshot(description="模板匹配", compress=False)
                screenshot_path = screenshot_result.get("screenshot_path")
                if not screenshot_path:
                    return {"success": False, "error": "截图失败"}
            
            matcher = TemplateMatcher()
            result = matcher.find_close_buttons(screenshot_path, threshold)
            
            return result
            
        except ImportError:
            return {
                "success": False,
                "error": "需要安装 opencv-python: pip install opencv-python"
            }
        except Exception as e:
            return {"success": False, "error": f"模板匹配失败: {e}"}
    
    def template_click_close(self, threshold: float = 0.75) -> Dict:
        """模板匹配并点击关闭按钮（一步到位）
        
        截图 -> 模板匹配 -> 点击最佳匹配位置
        
        Args:
            threshold: 匹配阈值 0-1
            
        Returns:
            操作结果
        """
        try:
            # 先截图并匹配
            match_result = self.template_match_close(threshold=threshold)
            
            if not match_result.get("success"):
                return match_result
            
            # 获取最佳匹配的百分比坐标
            best = match_result.get("best_match", {})
            x_percent = best.get("percent", {}).get("x")
            y_percent = best.get("percent", {}).get("y")
            
            if x_percent is None or y_percent is None:
                return {"success": False, "error": "无法获取匹配坐标"}
            
            # 点击
            click_result = self.click_by_percent(x_percent, y_percent)
            
            return {
                "success": True,
                "message": f"✅ 模板匹配并点击成功",
                "matched_template": best.get("template"),
                "confidence": best.get("confidence"),
                "clicked_position": f"({x_percent}%, {y_percent}%)",
                "click_result": click_result
            }
            
        except Exception as e:
            return {"success": False, "error": f"模板点击失败: {e}"}
    
    def template_add(self, screenshot_path: str, x: int, y: int, 
                     width: int, height: int, template_name: str) -> Dict:
        """从截图中裁剪并添加新模板
        
        当遇到新样式的X号时，用此方法添加到模板库。
        
        Args:
            screenshot_path: 截图路径
            x, y: 裁剪区域左上角坐标
            width, height: 裁剪区域大小
            template_name: 模板名称（如 x_circle_gray）
            
        Returns:
            结果
        """
        try:
            from .template_matcher import TemplateMatcher
            
            matcher = TemplateMatcher()
            return matcher.crop_and_add_template(
                screenshot_path, x, y, width, height, template_name
            )
        except ImportError:
            return {"success": False, "error": "需要安装 opencv-python"}
        except Exception as e:
            return {"success": False, "error": f"添加模板失败: {e}"}
    
    def template_list(self) -> Dict:
        """列出所有关闭按钮模板"""
        try:
            from .template_matcher import TemplateMatcher
            
            matcher = TemplateMatcher()
            return matcher.list_templates()
        except ImportError:
            return {"success": False, "error": "需要安装 opencv-python"}
        except Exception as e:
            return {"success": False, "error": f"列出模板失败: {e}"}
    
    def template_delete(self, template_name: str) -> Dict:
        """删除指定模板"""
        try:
            from .template_matcher import TemplateMatcher
            
            matcher = TemplateMatcher()
            return matcher.delete_template(template_name)
        except ImportError:
            return {"success": False, "error": "需要安装 opencv-python"}
        except Exception as e:
            return {"success": False, "error": f"删除模板失败: {e}"}
    
    def close_ad_popup(self, auto_learn: bool = True) -> Dict:
        """智能关闭广告弹窗（专用于广告场景）
        
        按优先级尝试：
        1. 控件树查找关闭按钮（最可靠）
        2. 模板匹配（需要积累模板库）
        3. 返回视觉信息供 AI 分析（如果前两步失败）
        
        自动学习：
        - 点击成功后，检查这个 X 是否已在模板库
        - 如果是新样式，自动裁剪并添加到模板库
        
        Args:
            auto_learn: 是否自动学习新模板（点击成功后检查并保存）
            
        Returns:
            结果字典
        """
        import time
        import re
        
        result = {
            "success": False,
            "method": None,
            "message": "",
            "learned_template": None
        }
        
        if self._is_ios():
            return {"success": False, "error": "iOS 暂不支持此功能"}
        
        try:
            import xml.etree.ElementTree as ET
            
            # ========== 第0步：先检测是否有弹窗 ==========
            xml_string = self.client.u2.dump_hierarchy(compressed=False)
            root = ET.fromstring(xml_string)
            
            screen_width = self.client.u2.info.get('displayWidth', 1440)
            screen_height = self.client.u2.info.get('displayHeight', 3200)
            
            popup_bounds, popup_confidence = self._detect_popup_with_confidence(
                root, screen_width, screen_height
            )
            
            # 如果没有检测到弹窗，直接返回"无弹窗"
            if popup_bounds is None or popup_confidence < 0.5:
                result["success"] = True
                result["method"] = None
                result["message"] = "ℹ️ 当前页面未检测到弹窗，无需关闭"
                result["popup_detected"] = False
                result["popup_confidence"] = popup_confidence
                return result
            
            # ========== 第1步：控件树查找关闭按钮 ==========
            
            # 关闭按钮的常见特征
            close_keywords = ['关闭', '跳过', '×', 'X', 'x', 'close', 'skip', '取消']
            close_content_desc = ['关闭', '跳过', 'close', 'skip', 'dismiss']
            
            close_candidates = []
            
            for elem in root.iter():
                text = elem.attrib.get('text', '').strip()
                content_desc = elem.attrib.get('content-desc', '').strip()
                clickable = elem.attrib.get('clickable', 'false') == 'true'
                bounds_str = elem.attrib.get('bounds', '')
                resource_id = elem.attrib.get('resource-id', '')
                
                if not bounds_str:
                    continue
                
                match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
                if not match:
                    continue
                
                x1, y1, x2, y2 = map(int, match.groups())
                width = x2 - x1
                height = y2 - y1
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                
                score = 0
                reason = ""
                
                # 文本匹配
                for kw in close_keywords:
                    if kw in text:
                        score += 10
                        reason = f"文本含'{kw}'"
                        break
                
                # content-desc 匹配
                for kw in close_content_desc:
                    if kw.lower() in content_desc.lower():
                        score += 8
                        reason = f"描述含'{kw}'"
                        break
                
                # 小尺寸可点击元素（可能是 X 按钮）
                if clickable and 30 < width < 200 and 30 < height < 200:
                    screen_width = self.client.u2.info.get('displayWidth', 1440)
                    screen_height = self.client.u2.info.get('displayHeight', 3200)
                    
                    # 在屏幕右半边上半部分，很可能是 X
                    if cx > screen_width * 0.6 and cy < screen_height * 0.5:
                        score += 5
                        reason = reason or "右上角小按钮"
                    # 在屏幕上半部分的小按钮，也可能是 X
                    elif cy < screen_height * 0.4:
                        score += 2
                        reason = reason or "上部小按钮"
                
                # 只要是可点击的小按钮都考虑（即使没有文本）
                if score > 0 or (clickable and 30 < width < 150 and 30 < height < 150):
                    if not reason and clickable:
                        reason = "可点击小按钮"
                        score = max(score, 1)  # 确保有分数
                    close_candidates.append({
                        'score': score,
                        'reason': reason,
                        'bounds': (x1, y1, x2, y2),
                        'center': (cx, cy),
                        'resource_id': resource_id,
                        'text': text
                    })
            
            # 按分数排序
            close_candidates.sort(key=lambda x: x['score'], reverse=True)
            
            if close_candidates:
                best = close_candidates[0]
                cx, cy = best['center']
                bounds = best['bounds']
                
                # 点击（click_at_coords 内部已包含应用状态检查和自动返回）
                click_result = self.click_at_coords(cx, cy)
                time.sleep(0.5)
                
                # 🎯 再次检查应用状态（确保弹窗去除没有导致应用跳转）
                app_check = self._check_app_switched()
                return_result = None
                
                if app_check['switched']:
                    # 应用已跳转，说明弹窗去除失败，尝试返回目标应用
                    return_result = self._return_to_target_app()
                
                result["success"] = True
                result["method"] = "控件树"
                msg = f"✅ 通过控件树找到关闭按钮并点击\n" \
                      f"   位置: ({cx}, {cy})\n" \
                      f"   原因: {best['reason']}"
                
                if app_check['switched']:
                    msg += f"\n⚠️ 应用已跳转，说明弹窗去除失败"
                    if return_result:
                        if return_result['success']:
                            msg += f"\n{return_result['message']}"
                        else:
                            msg += f"\n❌ 自动返回失败: {return_result['message']}"
                
                result["message"] = msg
                result["app_check"] = app_check
                result["return_to_app"] = return_result
                result["tip"] = "💡 建议调用 mobile_screenshot_with_som 确认弹窗是否已关闭"
                
                return result
            
            # ========== 第2步：模板匹配（自动执行，不需要 AI 介入）==========
            screenshot_path = None
            try:
                from .template_matcher import TemplateMatcher
                
                # 截图用于模板匹配
                screenshot_result = self.take_screenshot(description="模板匹配", compress=False)
                screenshot_path = screenshot_result.get("screenshot_path")
                
                if screenshot_path:
                    matcher = TemplateMatcher()
                    match_result = matcher.find_close_buttons(screenshot_path, threshold=0.75)
                    
                    # 直接使用最佳匹配（已按置信度排序）
                    if match_result.get("success") and match_result.get("best_match"):
                        best = match_result["best_match"]
                        x_pct = best["percent"]["x"]
                        y_pct = best["percent"]["y"]
                        
                        # 点击
                        click_result = self.click_by_percent(x_pct, y_pct)
                        time.sleep(0.5)
                        
                        app_check = self._check_app_switched()
                        return_result = None
                        
                        if app_check['switched']:
                            return_result = self._return_to_target_app()
                        
                        result["success"] = True
                        result["method"] = "模板匹配"
                        msg = f"✅ 通过模板匹配找到关闭按钮并点击\n" \
                              f"   模板: {best.get('template', 'unknown')}\n" \
                              f"   置信度: {best.get('confidence', 'N/A')}%\n" \
                              f"   位置: ({x_pct:.1f}%, {y_pct:.1f}%)"
                        
                        if app_check['switched']:
                            msg += f"\n⚠️ 应用已跳转"
                            if return_result:
                                msg += f"\n{return_result['message']}"
                        
                        result["message"] = msg
                        result["app_check"] = app_check
                        result["return_to_app"] = return_result
                        return result
                    
            except ImportError:
                pass  # OpenCV 未安装，跳过模板匹配
            except Exception:
                pass  # 模板匹配失败，继续下一步
            
            # ========== 第3步：控件树和模板匹配都失败，提示 AI 使用视觉识别 ==========
            result["success"] = False
            result["fallback"] = "vision"
            result["method"] = None
            result["popup_detected"] = True
            result["message"] = "⚠️ 控件树和模板匹配都未找到关闭按钮，请调用 mobile_screenshot_with_som 截图后用 click_by_som 点击"
            
            return result
            
        except Exception as e:
            return {"success": False, "error": f"关闭弹窗失败: {e}"}
    
    def _detect_popup_region(self, root) -> tuple:
        """从控件树中检测弹窗区域
        
        Args:
            root: 控件树根元素
            
        Returns:
            弹窗边界 (x1, y1, x2, y2) 或 None
        """
        import re
        
        screen_width = self.client.u2.info.get('displayWidth', 1440)
        screen_height = self.client.u2.info.get('displayHeight', 3200)
        
        popup_candidates = []
        
        for elem in root.iter():
            bounds_str = elem.attrib.get('bounds', '')
            if not bounds_str:
                continue
            
            match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
            if not match:
                continue
            
            x1, y1, x2, y2 = map(int, match.groups())
            width = x2 - x1
            height = y2 - y1
            
            # 弹窗特征：
            # 1. 不是全屏
            # 2. 在屏幕中央
            # 3. 有一定大小
            is_fullscreen = (width >= screen_width * 0.95 and height >= screen_height * 0.9)
            is_centered = (x1 > screen_width * 0.05 and x2 < screen_width * 0.95)
            is_reasonable_size = (width > 200 and height > 200 and 
                                  width < screen_width * 0.95 and 
                                  height < screen_height * 0.8)
            
            if not is_fullscreen and is_centered and is_reasonable_size:
                # 计算"弹窗感"分数
                area = width * height
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                center_dist = abs(center_x - screen_width/2) + abs(center_y - screen_height/2)
                
                score = area / 1000 - center_dist / 10
                popup_candidates.append({
                    'bounds': (x1, y1, x2, y2),
                    'score': score
                })
        
        if popup_candidates:
            # 返回分数最高的弹窗
            popup_candidates.sort(key=lambda x: x['score'], reverse=True)
            return popup_candidates[0]['bounds']
        
        return None

    def _auto_learn_template(self, screenshot_path: str, bounds: tuple, threshold: float = 0.6) -> str:
        """自动学习：检查 X 按钮是否已在模板库，不在就添加
        
        Args:
            screenshot_path: 截图路径
            bounds: X 按钮的边界 (x1, y1, x2, y2)
            threshold: 判断是否已存在的阈值（高于此值认为已存在）
            
        Returns:
            新模板名称，如果是新模板的话；已存在或失败返回 None
        """
        try:
            from .template_matcher import TemplateMatcher
            from PIL import Image
            import time
            
            x1, y1, x2, y2 = bounds
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            width = x2 - x1
            height = y2 - y1
            
            # 扩展一点边界，确保裁剪完整
            padding = max(10, int(max(width, height) * 0.2))
            
            # 打开截图
            img = Image.open(screenshot_path)
            
            # 裁剪 X 按钮区域
            crop_x1 = max(0, x1 - padding)
            crop_y1 = max(0, y1 - padding)
            crop_x2 = min(img.width, x2 + padding)
            crop_y2 = min(img.height, y2 + padding)
            
            cropped = img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            
            # 保存临时文件用于匹配检查
            temp_path = self.screenshot_dir / "temp_new_x.png"
            cropped.save(str(temp_path))
            
            # 检查是否已在模板库中（用模板匹配检测相似度）
            matcher = TemplateMatcher()
            
            import cv2
            new_img = cv2.imread(str(temp_path), cv2.IMREAD_GRAYSCALE)
            if new_img is None:
                return None
            
            is_new = True
            for template_file in matcher.template_dir.glob("*.png"):
                template = cv2.imread(str(template_file), cv2.IMREAD_GRAYSCALE)
                if template is None:
                    continue
                
                # 将两个图都调整到合适大小，然后用小模板在大图中搜索
                # 这样比较更接近实际匹配场景
                
                # 新图作为搜索区域（稍大一点）
                new_resized = cv2.resize(new_img, (100, 100))
                # 模板调整到较小尺寸
                template_resized = cv2.resize(template, (60, 60))
                
                # 在新图中搜索模板
                result = cv2.matchTemplate(new_resized, template_resized, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                
                if max_val >= threshold:
                    is_new = False
                    break
            
            # 清理临时文件
            if temp_path.exists():
                temp_path.unlink()
            
            if is_new:
                # 生成唯一模板名
                timestamp = time.strftime("%m%d_%H%M%S")
                template_name = f"auto_x_{timestamp}.png"
                template_path = matcher.template_dir / template_name
                
                # 保存新模板
                cropped.save(str(template_path))
                
                return template_name
            else:
                return None  # 已存在类似模板
                
        except Exception as e:
            return None  # 学习失败，不影响主流程
    
    def template_add_by_percent(self, x_percent: float, y_percent: float, 
                                 size: int, template_name: str) -> Dict:
        """通过百分比坐标添加模板（更方便！）
        
        自动截图 → 根据百分比位置裁剪 → 保存为模板
        
        Args:
            x_percent: X号中心的水平百分比 (0-100)
            y_percent: X号中心的垂直百分比 (0-100)
            size: 裁剪区域大小（正方形边长，像素）
            template_name: 模板名称
            
        Returns:
            结果
        """
        try:
            from .template_matcher import TemplateMatcher
            from PIL import Image
            
            # 先截图（不带 SoM 标注的干净截图）
            screenshot_result = self.take_screenshot(description="添加模板", compress=False)
            screenshot_path = screenshot_result.get("screenshot_path")
            
            if not screenshot_path:
                return {"success": False, "error": "截图失败"}
            
            # 读取截图获取尺寸
            img = Image.open(screenshot_path)
            img_w, img_h = img.size
            
            # 计算中心点像素坐标
            cx = int(img_w * x_percent / 100)
            cy = int(img_h * y_percent / 100)
            
            # 计算裁剪区域
            half = size // 2
            x1 = max(0, cx - half)
            y1 = max(0, cy - half)
            x2 = min(img_w, cx + half)
            y2 = min(img_h, cy + half)
            
            # 裁剪并保存
            cropped = img.crop((x1, y1, x2, y2))
            
            matcher = TemplateMatcher()
            output_path = matcher.template_dir / f"{template_name}.png"
            cropped.save(str(output_path))
            
            return {
                "success": True,
                "message": f"✅ 模板已保存: {template_name}",
                "template_path": str(output_path),
                "center_percent": f"({x_percent}%, {y_percent}%)",
                "center_pixel": f"({cx}, {cy})",
                "crop_region": f"({x1},{y1}) - ({x2},{y2})",
                "size": f"{cropped.size[0]}x{cropped.size[1]}"
            }
            
        except ImportError as e:
            return {"success": False, "error": f"需要安装依赖: {e}"}
        except Exception as e:
            return {"success": False, "error": f"添加模板失败: {e}"}
    
    def open_new_chat(self, message: str = "继续执行飞书用例") -> Dict:
        """打开 Cursor 新会话并发送消息
        
        用于飞书用例批量执行时，自动分批继续。
        
        Args:
            message: 发送到新会话的消息，默认"继续执行飞书用例"
        
        Returns:
            执行结果
        
        依赖:
            pip install pyautogui pyperclip pygetwindow (macOS/Windows)
        """
        import sys
        import platform
        
        try:
            import pyautogui
            import pyperclip
        except ImportError:
            return {
                "success": False,
                "error": "缺少依赖，请执行: pip install pyautogui pyperclip pygetwindow"
            }
        
        try:
            system = platform.system()
            
            # 1. 激活 Cursor 窗口
            if system == "Darwin":  # macOS
                import subprocess
                # 使用 osascript 激活 Cursor
                script = '''
                tell application "Cursor"
                    activate
                end tell
                '''
                subprocess.run(["osascript", "-e", script], check=True)
                time.sleep(0.3)
                
                # 2. 快捷键打开新会话 (Cmd+T)
                pyautogui.hotkey('command', 't')
                
            elif system == "Windows":
                try:
                    import pygetwindow as gw
                    cursor_windows = gw.getWindowsWithTitle('Cursor')
                    if cursor_windows:
                        cursor_windows[0].activate()
                        time.sleep(0.3)
                except:
                    pass  # 如果激活失败，继续尝试发送快捷键
                
                # 2. 快捷键打开新会话 (Ctrl+T)
                pyautogui.hotkey('ctrl', 't')
                
            else:  # Linux
                # 2. 快捷键打开新会话 (Ctrl+T)
                pyautogui.hotkey('ctrl', 't')
            
            time.sleep(0.5)  # 等待新会话打开
            
            # 3. 复制消息到剪贴板并粘贴
            pyperclip.copy(message)
            time.sleep(0.1)
            
            if system == "Darwin":
                pyautogui.hotkey('command', 'v')
            else:
                pyautogui.hotkey('ctrl', 'v')
            
            time.sleep(0.2)
            
            # 4. 按 Enter 发送
            pyautogui.press('enter')
            
            return {
                "success": True,
                "message": f"✅ 已打开新会话并发送: {message}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"打开新会话失败: {e}"
            }

