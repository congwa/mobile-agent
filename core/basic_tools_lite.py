#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精简版基础工具 - 纯 MCP，依赖 Cursor 视觉能力

特点：
- 不需要 AI 密钥
- 核心功能精简
- 保留 pytest 脚本生成
- 支持操作历史记录
"""

import asyncio
import time
import re
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


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
        """记录操作到历史"""
        record = {
            'action': action,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        self.operation_history.append(record)
    
    
    
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
                    return {"success": False, "message": "❌ iOS 客户端未初始化"}
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
                
                return {
                    "success": True,
                    "screenshot_path": str(final_path),
                    "screen_width": screen_width,
                    "screen_height": screen_height,
                    "image_width": img.width,
                    "image_height": img.height,
                    "crop_offset_x": crop_offset_x,
                    "crop_offset_y": crop_offset_y,
                    "file_size": f"{cropped_size/1024:.1f}KB",
                    "message": f"🔍 局部截图已保存: {final_path}\n"
                              f"📐 裁剪区域: ({crop_offset_x}, {crop_offset_y}) 起，{img.width}x{img.height} 像素\n"
                              f"📦 文件大小: {cropped_size/1024:.0f}KB\n"
                              f"🎯 【坐标换算】AI 返回坐标 (x, y) 后：\n"
                              f"   实际屏幕坐标 = ({crop_offset_x} + x, {crop_offset_y} + y)\n"
                              f"   或直接调用 mobile_click_at_coords(x, y, crop_offset_x={crop_offset_x}, crop_offset_y={crop_offset_y})"
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
                
                return {
                    "success": True,
                    "screenshot_path": str(final_path),
                    "screen_width": screen_width,
                    "screen_height": screen_height,
                    "original_img_width": original_img_width,    # 截图原始宽度
                    "original_img_height": original_img_height,  # 截图原始高度
                    "image_width": image_width,                  # 压缩后宽度（AI 看到的）
                    "image_height": image_height,                # 压缩后高度（AI 看到的）
                    "original_size": f"{original_size/1024:.1f}KB",
                    "compressed_size": f"{compressed_size/1024:.1f}KB",
                    "saved_percent": f"{saved_percent:.0f}%",
                    "message": f"📸 截图已保存: {final_path}\n"
                              f"📐 原始尺寸: {original_img_width}x{original_img_height} → 压缩后: {image_width}x{image_height}\n"
                              f"📦 已压缩: {original_size/1024:.0f}KB → {compressed_size/1024:.0f}KB (省 {saved_percent:.0f}%)\n"
                              f"⚠️ 【坐标转换】AI 返回坐标后，请传入：\n"
                              f"   image_width={image_width}, image_height={image_height},\n"
                              f"   original_img_width={original_img_width}, original_img_height={original_img_height}"
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
                
                # 不压缩时，用截图实际尺寸（可能和 screen_width 不同）
                return {
                    "success": True,
                    "screenshot_path": str(final_path),
                    "screen_width": screen_width,
                    "screen_height": screen_height,
                    "original_img_width": img.width,   # 截图实际尺寸
                    "original_img_height": img.height,
                    "image_width": img.width,          # 未压缩，和原图一样
                    "image_height": img.height,
                    "file_size": f"{original_size/1024:.1f}KB",
                    "message": f"📸 截图已保存: {final_path}\n"
                              f"📐 截图尺寸: {img.width}x{img.height}\n"
                              f"📦 文件大小: {original_size/1024:.0f}KB（未压缩）\n"
                              f"💡 未压缩，坐标可直接使用"
                }
        except ImportError:
            # 如果没有 PIL，回退到原始方式（不压缩）
            return self._take_screenshot_no_compress(description)
        except Exception as e:
            return {"success": False, "message": f"❌ 截图失败: {e}"}
    
    def take_screenshot_with_grid(self, grid_size: int = 100, show_popup_hints: bool = True) -> Dict:
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
                    return {"success": False, "message": "❌ iOS 客户端未初始化"}
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
            
            # 第3步：检测弹窗并标注
            popup_info = None
            close_positions = []
            
            if show_popup_hints and not self._is_ios():
                try:
                    import xml.etree.ElementTree as ET
                    xml_string = self.client.u2.dump_hierarchy()
                    root = ET.fromstring(xml_string)
                    
                    # 检测弹窗区域
                    popup_bounds = None
                    for elem in root.iter():
                        bounds_str = elem.attrib.get('bounds', '')
                        class_name = elem.attrib.get('class', '')
                        
                        if not bounds_str:
                            continue
                        
                        match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
                        if not match:
                            continue
                        
                        x1, y1, x2, y2 = map(int, match.groups())
                        width = x2 - x1
                        height = y2 - y1
                        area = width * height
                        screen_area = screen_width * screen_height
                        
                        is_container = any(kw in class_name for kw in ['Layout', 'View', 'Dialog', 'Card'])
                        area_ratio = area / screen_area if screen_area > 0 else 0
                        is_not_fullscreen = (width < screen_width * 0.98 or height < screen_height * 0.98)
                        is_reasonable_size = 0.08 < area_ratio < 0.85
                        
                        if is_container and is_not_fullscreen and is_reasonable_size and y1 > 50:
                            if popup_bounds is None or area > (popup_bounds[2] - popup_bounds[0]) * (popup_bounds[3] - popup_bounds[1]):
                                popup_bounds = (x1, y1, x2, y2)
                    
                    if popup_bounds:
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
                "screen_width": screen_width,
                "screen_height": screen_height,
                "image_width": img_width,
                "image_height": img_height,
                "grid_size": grid_size,
                "message": f"📸 网格截图已保存: {final_path}\n"
                          f"📐 尺寸: {img_width}x{img_height}\n"
                          f"📏 网格间距: {grid_size}px"
            }
            
            if popup_info:
                result["popup_detected"] = True
                result["popup_bounds"] = popup_info["bounds"]
                result["close_button_hints"] = close_positions
                result["message"] += f"\n🎯 检测到弹窗: {popup_info['bounds']}"
                result["message"] += f"\n💡 可能的关闭按钮位置（绿色圆圈标注）："
                for pos in close_positions:
                    result["message"] += f"\n   {pos['priority']}. {pos['name']}: ({pos['x']}, {pos['y']})"
            else:
                result["popup_detected"] = False
            
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
                    return {"success": False, "message": "❌ iOS 客户端未初始化"}
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
                    xml_string = self.client.u2.dump_hierarchy()
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
                    'desc': elem['desc']
                })
            
            # 第3.5步：检测弹窗区域（用于标注）
            popup_bounds = None
            
            if not self._is_ios():
                try:
                    # 检测弹窗区域
                    for elem in root.iter():
                        bounds_str = elem.attrib.get('bounds', '')
                        class_name = elem.attrib.get('class', '')
                        
                        if not bounds_str:
                            continue
                        
                        match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
                        if not match:
                            continue
                        
                        px1, py1, px2, py2 = map(int, match.groups())
                        p_width = px2 - px1
                        p_height = py2 - py1
                        p_area = p_width * p_height
                        screen_area = screen_width * screen_height
                        
                        is_container = any(kw in class_name for kw in ['Layout', 'View', 'Dialog', 'Card', 'Frame'])
                        area_ratio = p_area / screen_area if screen_area > 0 else 0
                        is_not_fullscreen = (p_width < screen_width * 0.99 or p_height < screen_height * 0.95)
                        # 放宽面积范围：5% - 95%
                        is_reasonable_size = 0.05 < area_ratio < 0.95
                        
                        if is_container and is_not_fullscreen and is_reasonable_size and py1 > 30:
                            if popup_bounds is None or p_area > (popup_bounds[2] - popup_bounds[0]) * (popup_bounds[3] - popup_bounds[1]):
                                popup_bounds = (px1, py1, px2, py2)
                    
                    # 如果检测到弹窗，标注弹窗边界（不再猜测X按钮位置）
                    if popup_bounds:
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
            
            # 构建元素列表文字
            elements_text = "\n".join([
                f"  [{e['index']}] {e['desc']} → ({e['center'][0]}, {e['center'][1]})"
                for e in som_elements[:15]  # 只显示前15个
            ])
            if len(som_elements) > 15:
                elements_text += f"\n  ... 还有 {len(som_elements) - 15} 个元素"
            
            # 构建弹窗提示文字
            hints_text = ""
            if popup_bounds:
                hints_text = f"\n🎯 检测到弹窗区域（蓝色边框）\n"
                hints_text += f"   如需关闭弹窗，请观察图片中的 X 按钮位置\n"
                hints_text += f"   然后使用 mobile_click_by_percent(x%, y%) 点击"
            
            return {
                "success": True,
                "screenshot_path": str(final_path),
                "screen_width": screen_width,
                "screen_height": screen_height,
                "image_width": img_width,
                "image_height": img_height,
                "element_count": len(som_elements),
                "elements": som_elements,
                "popup_detected": popup_bounds is not None,
                "popup_bounds": f"[{popup_bounds[0]},{popup_bounds[1]}][{popup_bounds[2]},{popup_bounds[3]}]" if popup_bounds else None,
                "message": f"📸 SoM 截图已保存: {final_path}\n"
                          f"🏷️ 已标注 {len(som_elements)} 个可点击元素\n"
                          f"📋 元素列表：\n{elements_text}{hints_text}\n\n"
                          f"💡 使用方法：\n"
                          f"   - 点击标注元素：mobile_click_by_som(编号)\n"
                          f"   - 点击任意位置：mobile_click_by_percent(x%, y%)"
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
            else:
                self.client.u2.click(cx, cy)
            
            time.sleep(0.3)
            
            return {
                "success": True,
                "message": f"✅ 已点击 [{index}] {target['desc']} → ({cx}, {cy})\n💡 建议：再次截图确认操作是否成功",
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
                    return {"success": False, "message": "❌ iOS 客户端未初始化"}
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
                    return {"success": False, "message": "❌ iOS 客户端未初始化"}
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
            
            # 记录操作（包含屏幕尺寸和百分比，便于脚本生成时转换）
            self._record_operation(
                'click', 
                x=x, 
                y=y, 
                x_percent=x_percent,
                y_percent=y_percent,
                screen_width=screen_width,
                screen_height=screen_height,
                ref=f"coords_{x}_{y}"
            )
            
            if converted:
                if conversion_type == "crop_offset":
                    return {
                        "success": True,
                        "message": f"✅ 点击成功: ({x}, {y})\n"
                                  f"   🔍 局部截图坐标转换: ({original_x},{original_y}) + 偏移({crop_offset_x},{crop_offset_y}) → ({x},{y})"
                    }
                else:
                    return {
                        "success": True,
                        "message": f"✅ 点击成功: ({x}, {y})\n"
                                  f"   📐 坐标已转换: ({original_x},{original_y}) → ({x},{y})\n"
                                  f"   🖼️ 图片尺寸: {image_width}x{image_height} → 屏幕: {screen_width}x{screen_height}"
                    }
            else:
                return {
                    "success": True,
                    "message": f"✅ 点击成功: ({x}, {y}) [相对位置: {x_percent}%, {y_percent}%]"
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
                    return {"success": False, "message": "❌ iOS 客户端未初始化"}
            else:
                info = self.client.u2.info
                width = info.get('displayWidth', 0)
                height = info.get('displayHeight', 0)
            
            if width == 0 or height == 0:
                return {"success": False, "message": "❌ 无法获取屏幕尺寸"}
            
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
            
            # 第4步：记录操作（同时记录百分比和像素）
            self._record_operation(
                'click',
                x=x,
                y=y,
                x_percent=x_percent,
                y_percent=y_percent,
                screen_width=width,
                screen_height=height,
                ref=f"percent_{x_percent}_{y_percent}"
            )
            
            return {
                "success": True,
                "message": f"✅ 百分比点击成功: ({x_percent}%, {y_percent}%) → 像素({x}, {y})",
                "screen_size": {"width": width, "height": height},
                "percent": {"x": x_percent, "y": y_percent},
                "pixel": {"x": x, "y": y}
            }
        except Exception as e:
            return {"success": False, "message": f"❌ 百分比点击失败: {e}"}
    
    def click_by_text(self, text: str, timeout: float = 3.0) -> Dict:
        """通过文本点击 - 先查 XML 树，再精准匹配"""
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
                        self._record_operation('click', element=text, ref=text)
                        return {"success": True, "message": f"✅ 点击成功: '{text}'"}
                    return {"success": False, "message": f"❌ 文本不存在: {text}"}
            else:
                # 🔍 先查 XML 树，找到元素及其属性
                found_elem = self._find_element_in_tree(text)
                
                if found_elem:
                    attr_type = found_elem['attr_type']
                    attr_value = found_elem['attr_value']
                    bounds = found_elem.get('bounds')
                    
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
                        elem.click()
                        time.sleep(0.3)
                        self._record_operation('click', element=text, ref=f"{attr_type}:{attr_value}")
                        return {"success": True, "message": f"✅ 点击成功({attr_type}): '{text}'"}
                    
                    # 如果选择器失败，用坐标兜底
                    if bounds:
                        x = (bounds[0] + bounds[2]) // 2
                        y = (bounds[1] + bounds[3]) // 2
                        self.client.u2.click(x, y)
                        time.sleep(0.3)
                        self._record_operation('click', element=text, x=x, y=y, ref=f"coords:{x},{y}")
                        return {"success": True, "message": f"✅ 点击成功(坐标兜底): '{text}' @ ({x},{y})"}
                
                return {"success": False, "message": f"❌ 文本不存在: {text}"}
        except Exception as e:
            return {"success": False, "message": f"❌ 点击失败: {e}"}
    
    def _find_element_in_tree(self, text: str) -> Optional[Dict]:
        """在 XML 树中查找包含指定文本的元素"""
        try:
            xml = self.client.u2.dump_hierarchy()
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml)
            
            for elem in root.iter():
                elem_text = elem.attrib.get('text', '')
                elem_desc = elem.attrib.get('content-desc', '')
                bounds_str = elem.attrib.get('bounds', '')
                
                # 解析 bounds
                bounds = None
                if bounds_str:
                    import re
                    match = re.findall(r'\d+', bounds_str)
                    if len(match) == 4:
                        bounds = [int(x) for x in match]
                
                # 精确匹配 text
                if elem_text == text:
                    return {'attr_type': 'text', 'attr_value': text, 'bounds': bounds}
                
                # 精确匹配 content-desc
                if elem_desc == text:
                    return {'attr_type': 'description', 'attr_value': text, 'bounds': bounds}
                
                # 模糊匹配 text
                if text in elem_text:
                    return {'attr_type': 'textContains', 'attr_value': text, 'bounds': bounds}
                
                # 模糊匹配 content-desc
                if text in elem_desc:
                    return {'attr_type': 'descriptionContains', 'attr_value': text, 'bounds': bounds}
            
            return None
        except Exception:
            return None
    
    def click_by_id(self, resource_id: str) -> Dict:
        """通过 resource-id 点击"""
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    elem = ios_client.wda(id=resource_id)
                    if not elem.exists:
                        elem = ios_client.wda(name=resource_id)
                    if elem.exists:
                        elem.click()
                        time.sleep(0.3)
                        self._record_operation('click', element=resource_id, ref=resource_id)
                        return {"success": True, "message": f"✅ 点击成功: {resource_id}"}
                    return {"success": False, "message": f"❌ 元素不存在: {resource_id}"}
            else:
                elem = self.client.u2(resourceId=resource_id)
                if elem.exists(timeout=0.5):
                    elem.click()
                    time.sleep(0.3)
                    self._record_operation('click', element=resource_id, ref=resource_id)
                    return {"success": True, "message": f"✅ 点击成功: {resource_id}"}
                return {"success": False, "message": f"❌ 元素不存在: {resource_id}"}
        except Exception as e:
            return {"success": False, "message": f"❌ 点击失败: {e}"}
    
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
                    return {"success": False, "message": "❌ iOS 客户端未初始化"}
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
            
            # 记录操作
            self._record_operation(
                'long_press', 
                x=x, 
                y=y, 
                x_percent=x_percent,
                y_percent=y_percent,
                duration=duration,
                screen_width=screen_width,
                screen_height=screen_height,
                ref=f"coords_{x}_{y}"
            )
            
            if converted:
                if conversion_type == "crop_offset":
                    return {
                        "success": True,
                        "message": f"✅ 长按成功: ({x}, {y}) 持续 {duration}s\n"
                                  f"   🔍 局部截图坐标转换: ({original_x},{original_y}) + 偏移({crop_offset_x},{crop_offset_y}) → ({x},{y})"
                    }
                else:
                    return {
                        "success": True,
                        "message": f"✅ 长按成功: ({x}, {y}) 持续 {duration}s\n"
                                  f"   📐 坐标已转换: ({original_x},{original_y}) → ({x},{y})\n"
                                  f"   🖼️ 图片尺寸: {image_width}x{image_height} → 屏幕: {screen_width}x{screen_height}"
                    }
            else:
                return {
                    "success": True,
                    "message": f"✅ 长按成功: ({x}, {y}) 持续 {duration}s [相对位置: {x_percent}%, {y_percent}%]"
                }
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
                    return {"success": False, "message": "❌ iOS 客户端未初始化"}
            else:
                info = self.client.u2.info
                width = info.get('displayWidth', 0)
                height = info.get('displayHeight', 0)
            
            if width == 0 or height == 0:
                return {"success": False, "message": "❌ 无法获取屏幕尺寸"}
            
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
            
            # 第4步：记录操作
            self._record_operation(
                'long_press',
                x=x,
                y=y,
                x_percent=x_percent,
                y_percent=y_percent,
                duration=duration,
                screen_width=width,
                screen_height=height,
                ref=f"percent_{x_percent}_{y_percent}"
            )
            
            return {
                "success": True,
                "message": f"✅ 百分比长按成功: ({x_percent}%, {y_percent}%) → 像素({x}, {y}) 持续 {duration}s",
                "screen_size": {"width": width, "height": height},
                "percent": {"x": x_percent, "y": y_percent},
                "pixel": {"x": x, "y": y},
                "duration": duration
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
                        self._record_operation('long_press', element=text, duration=duration, ref=text)
                        return {"success": True, "message": f"✅ 长按成功: '{text}' 持续 {duration}s"}
                    return {"success": False, "message": f"❌ 文本不存在: {text}"}
            else:
                # 先查 XML 树，找到元素
                found_elem = self._find_element_in_tree(text)
                
                if found_elem:
                    attr_type = found_elem['attr_type']
                    attr_value = found_elem['attr_value']
                    bounds = found_elem.get('bounds')
                    
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
                        self._record_operation('long_press', element=text, duration=duration, ref=f"{attr_type}:{attr_value}")
                        return {"success": True, "message": f"✅ 长按成功({attr_type}): '{text}' 持续 {duration}s"}
                    
                    # 如果选择器失败，用坐标兜底
                    if bounds:
                        x = (bounds[0] + bounds[2]) // 2
                        y = (bounds[1] + bounds[3]) // 2
                        self.client.u2.long_click(x, y, duration=duration)
                        time.sleep(0.3)
                        self._record_operation('long_press', element=text, x=x, y=y, duration=duration, ref=f"coords:{x},{y}")
                        return {"success": True, "message": f"✅ 长按成功(坐标兜底): '{text}' @ ({x},{y}) 持续 {duration}s"}
                
                return {"success": False, "message": f"❌ 文本不存在: {text}"}
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
                        self._record_operation('long_press', element=resource_id, duration=duration, ref=resource_id)
                        return {"success": True, "message": f"✅ 长按成功: {resource_id} 持续 {duration}s"}
                    return {"success": False, "message": f"❌ 元素不存在: {resource_id}"}
            else:
                elem = self.client.u2(resourceId=resource_id)
                if elem.exists(timeout=0.5):
                    elem.long_click(duration=duration)
                    time.sleep(0.3)
                    self._record_operation('long_press', element=resource_id, duration=duration, ref=resource_id)
                    return {"success": True, "message": f"✅ 长按成功: {resource_id} 持续 {duration}s"}
                return {"success": False, "message": f"❌ 元素不存在: {resource_id}"}
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
                        self._record_operation('input', element=resource_id, ref=resource_id, text=text)
                        return {"success": True, "message": f"✅ 输入成功: '{text}'"}
                    return {"success": False, "message": f"❌ 输入框不存在: {resource_id}"}
            else:
                elements = self.client.u2(resourceId=resource_id)
                
                # 检查是否存在
                if elements.exists(timeout=0.5):
                    count = elements.count
                    
                    # 只有 1 个元素，直接输入
                    if count == 1:
                        elements.set_text(text)
                        time.sleep(0.3)
                        self._record_operation('input', element=resource_id, ref=resource_id, text=text)
                        return {"success": True, "message": f"✅ 输入成功: '{text}'"}
                    
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
                                    self._record_operation('input', element=resource_id, ref=resource_id, text=text)
                                    return {"success": True, "message": f"✅ 输入成功: '{text}'"}
                            except:
                                continue
                        # 没找到可编辑的，用第一个
                        elements[0].set_text(text)
                        time.sleep(0.3)
                        self._record_operation('input', element=resource_id, ref=resource_id, text=text)
                        return {"success": True, "message": f"✅ 输入成功: '{text}'"}
                
                # ID 不可靠（不存在或太多），改用 EditText 类型定位
                edit_texts = self.client.u2(className='android.widget.EditText')
                if edit_texts.exists(timeout=0.5):
                    et_count = edit_texts.count
                    if et_count == 1:
                        edit_texts.set_text(text)
                        time.sleep(0.3)
                        self._record_operation('input', element='EditText', ref='EditText', text=text)
                        return {"success": True, "message": f"✅ 输入成功: '{text}' (通过 EditText 定位)"}
                    
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
                        self._record_operation('input', element='EditText', ref='EditText', text=text)
                        return {"success": True, "message": f"✅ 输入成功: '{text}' (通过 EditText 定位，选择最顶部的)"}
                
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
            
            self._record_operation(
                'input', 
                x=x, 
                y=y, 
                x_percent=x_percent,
                y_percent=y_percent,
                ref=f"coords_{x}_{y}", 
                text=text
            )
            
            return {"success": True, "message": f"✅ 输入成功: ({x}, {y}) [相对位置: {x_percent}%, {y_percent}%] -> '{text}'"}
        except Exception as e:
            return {"success": False, "message": f"❌ 输入失败: {e}"}
    
    # ==================== 导航操作 ====================
    
    async def swipe(self, direction: str, y: Optional[int] = None, y_percent: Optional[float] = None) -> Dict:
        """滑动屏幕
        
        Args:
            direction: 滑动方向 (up/down/left/right)
            y: 左右滑动时指定的高度坐标（像素）
            y_percent: 左右滑动时指定的高度百分比 (0-100)
        """
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    size = ios_client.wda.window_size()
                    width, height = size[0], size[1]
                else:
                    return {"success": False, "message": "❌ iOS 客户端未初始化"}
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
            else:
                swipe_y = center_y
            
            swipe_map = {
                'up': (center_x, int(height * 0.8), center_x, int(height * 0.2)),
                'down': (center_x, int(height * 0.2), center_x, int(height * 0.8)),
                'left': (int(width * 0.8), swipe_y, int(width * 0.2), swipe_y),
                'right': (int(width * 0.2), swipe_y, int(width * 0.8), swipe_y),
            }
            
            if direction not in swipe_map:
                return {"success": False, "message": f"❌ 不支持的方向: {direction}"}
            
            x1, y1, x2, y2 = swipe_map[direction]
            
            if self._is_ios():
                ios_client.wda.swipe(x1, y1, x2, y2)
            else:
                self.client.u2.swipe(x1, y1, x2, y2, duration=0.5)
            
            # 记录操作信息
            record_info = {'direction': direction}
            if y is not None:
                record_info['y'] = y
            if y_percent is not None:
                record_info['y_percent'] = y_percent
            self._record_operation('swipe', **record_info)
            
            # 构建返回消息
            msg = f"✅ 滑动成功: {direction}"
            if direction in ['left', 'right']:
                if y_percent is not None:
                    msg += f" (高度: {y_percent}% = {swipe_y}px)"
                elif y is not None:
                    msg += f" (高度: {y}px)"
            
            return {"success": True, "message": msg}
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
                        return {"success": True, "message": f"✅ 按键成功: {key}"}
                return {"success": False, "message": f"❌ iOS 不支持: {key}"}
            else:
                keycode = key_map.get(key.lower())
                if keycode:
                    self.client.u2.shell(f'input keyevent {keycode}')
                    self._record_operation('press_key', key=key)
                    return {"success": True, "message": f"✅ 按键成功: {key}"}
                return {"success": False, "message": f"❌ 不支持的按键: {key}"}
        except Exception as e:
            return {"success": False, "message": f"❌ 按键失败: {e}"}
    
    def wait(self, seconds: float) -> Dict:
        """等待指定时间"""
        time.sleep(seconds)
        return {"success": True, "message": f"✅ 已等待 {seconds} 秒"}
    
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
            
            self._record_operation('launch_app', package_name=package_name)
            
            return {
                "success": True,
                "message": f"✅ 已启动: {package_name}\n💡 建议等待 2-3 秒让页面加载"
            }
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
            return {"success": True, "message": f"✅ 已终止: {package_name}"}
        except Exception as e:
            return {"success": False, "message": f"❌ 终止失败: {e}"}
    
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
        """列出页面元素"""
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'list_elements'):
                    return ios_client.list_elements()
                return [{"error": "iOS 暂不支持元素列表，建议使用截图"}]
            else:
                xml_string = self.client.u2.dump_hierarchy()
                elements = self.client.xml_parser.parse(xml_string)
                
                result = []
                for elem in elements:
                    if elem.get('clickable') or elem.get('focusable'):
                        result.append({
                            'resource_id': elem.get('resource_id', ''),
                            'text': elem.get('text', ''),
                            'content_desc': elem.get('content_desc', ''),
                            'bounds': elem.get('bounds', ''),
                            'clickable': elem.get('clickable', False)
                        })
                return result
        except Exception as e:
            return [{"error": f"获取元素失败: {e}"}]
    
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
                return {"success": False, "message": "iOS 暂不支持，请使用截图+坐标点击"}
            
            # 获取屏幕尺寸
            screen_width = self.client.u2.info.get('displayWidth', 720)
            screen_height = self.client.u2.info.get('displayHeight', 1280)
            
            # 获取元素列表
            xml_string = self.client.u2.dump_hierarchy()
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_string)
            
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
            
            return {
                "success": True,
                "message": f"✅ 找到可能的关闭按钮",
                "best_candidate": {
                    "reason": best['reason'],
                    "center": {"x": best['center_x'], "y": best['center_y']},
                    "percent": {"x": best['x_percent'], "y": best['y_percent']},
                    "bounds": best['bounds'],
                    "size": best['size'],
                    "score": best['score']
                },
                "click_command": f"mobile_click_by_percent({best['x_percent']}, {best['y_percent']})",
                "other_candidates": [
                    {"reason": c['reason'], "percent": f"({c['x_percent']}%, {c['y_percent']}%)", "score": c['score']}
                    for c in candidates[1:4]
                ] if len(candidates) > 1 else [],
                "screen_size": {"width": screen_width, "height": screen_height}
            }
            
        except Exception as e:
            return {"success": False, "message": f"❌ 查找关闭按钮失败: {e}"}
    
    def close_popup(self) -> Dict:
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
        """
        try:
            import re
            import xml.etree.ElementTree as ET
            
            # 获取屏幕尺寸
            if self._is_ios():
                return {"success": False, "message": "iOS 暂不支持，请使用截图+坐标点击"}
            
            screen_width = self.client.u2.info.get('displayWidth', 720)
            screen_height = self.client.u2.info.get('displayHeight', 1280)
            
            # 获取原始 XML
            xml_string = self.client.u2.dump_hierarchy()
            
            # 关闭按钮的文本特征
            close_texts = ['×', 'X', 'x', '关闭', '取消', 'close', 'Close', 'CLOSE', '跳过', '知道了']
            close_desc_keywords = ['关闭', 'close', 'dismiss', 'cancel', '跳过']
            
            close_candidates = []
            popup_bounds = None  # 弹窗区域
            
            # 解析 XML
            try:
                root = ET.fromstring(xml_string)
                all_elements = list(root.iter())
                
                # ===== 第一步：检测弹窗区域 =====
                # 弹窗特征：非全屏、面积较大、通常在屏幕中央的容器
                popup_containers = []
                for idx, elem in enumerate(all_elements):
                    bounds_str = elem.attrib.get('bounds', '')
                    class_name = elem.attrib.get('class', '')
                    
                    if not bounds_str:
                        continue
                    
                    match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
                    if not match:
                        continue
                    
                    x1, y1, x2, y2 = map(int, match.groups())
                    width = x2 - x1
                    height = y2 - y1
                    area = width * height
                    screen_area = screen_width * screen_height
                    
                    # 弹窗容器特征：
                    # 1. 面积在屏幕的 10%-90% 之间（非全屏）
                    # 2. 宽度或高度不等于屏幕尺寸
                    # 3. 是容器类型（Layout/View/Dialog）
                    is_container = any(kw in class_name for kw in ['Layout', 'View', 'Dialog', 'Card', 'Container'])
                    area_ratio = area / screen_area
                    is_not_fullscreen = (width < screen_width * 0.98 or height < screen_height * 0.98)
                    is_reasonable_size = 0.08 < area_ratio < 0.9
                    
                    # 排除状态栏区域（y1 通常很小）
                    is_below_statusbar = y1 > 50
                    
                    if is_container and is_not_fullscreen and is_reasonable_size and is_below_statusbar:
                        popup_containers.append({
                            'bounds': (x1, y1, x2, y2),
                            'bounds_str': bounds_str,
                            'area': area,
                            'area_ratio': area_ratio,
                            'idx': idx,  # 元素在 XML 中的顺序（越后越上层）
                            'class': class_name
                        })
                
                # 选择最可能的弹窗容器（优先选择：XML 顺序靠后 + 面积适中）
                if popup_containers:
                    # 按 XML 顺序倒序（后出现的在上层），然后按面积适中程度排序
                    popup_containers.sort(key=lambda x: (x['idx'], -abs(x['area_ratio'] - 0.3)), reverse=True)
                    popup_bounds = popup_containers[0]['bounds']
                
                # ===== 第二步：在弹窗范围内查找关闭按钮 =====
                for idx, elem in enumerate(all_elements):
                    text = elem.attrib.get('text', '')
                    content_desc = elem.attrib.get('content-desc', '')
                    bounds_str = elem.attrib.get('bounds', '')
                    class_name = elem.attrib.get('class', '')
                    clickable = elem.attrib.get('clickable', 'false') == 'true'
                    
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
                    
                    # 如果检测到弹窗区域，检查元素是否在弹窗范围内或附近
                    in_popup = True
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
                    
                    if not in_popup:
                        continue
                    
                    # 相对位置（0-1）
                    rel_x = center_x / screen_width
                    rel_y = center_y / screen_height
                    
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
                        max_size = max(120, int(screen_width * 0.15))
                        if min_size <= width <= max_size and min_size <= height <= max_size:
                            # clickable 元素基础分更高
                            base_score = 8.0
                            # 浮动关闭按钮给予最高分
                            if is_floating_close:
                                base_score = 12.0
                                match_type = "floating_close"
                            elif 'Image' in class_name:
                                score = base_score + 2.0
                                match_type = "clickable_image"
                            else:
                                match_type = "clickable"
                            score = base_score + self._get_position_score(rel_x, rel_y) + popup_edge_bonus
                    
                    # ===== 策略4：ImageView/ImageButton 类型的小元素（非 clickable）=====
                    elif 'Image' in class_name:
                        min_size = max(15, int(screen_width * 0.02))
                        max_size = max(120, int(screen_width * 0.12))
                        if min_size <= width <= max_size and min_size <= height <= max_size:
                            score = 5.0 + self._get_position_score(rel_x, rel_y) + popup_edge_bonus
                            match_type = "ImageView"
                    
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
                            'in_popup': popup_bounds is not None
                        })
                        
            except ET.ParseError:
                pass
            
            if not close_candidates:
                # 如果检测到弹窗区域，先尝试点击常见的关闭按钮位置
                if popup_bounds:
                    px1, py1, px2, py2 = popup_bounds
                    popup_width = px2 - px1
                    popup_height = py2 - py1
                    
                    # 【优化】X按钮有三种常见位置：
                    # 1. 弹窗内靠近顶部边界（内嵌X按钮）- 最常见
                    # 2. 弹窗边界上方（浮动X按钮）
                    # 3. 弹窗正下方（底部关闭按钮）
                    offset_x = max(60, int(popup_width * 0.07))   # 宽度7%
                    offset_y_above = max(35, int(popup_height * 0.025))  # 高度2.5%，在边界之上
                    offset_y_near = max(45, int(popup_height * 0.03))    # 高度3%，紧贴顶边界内侧
                    
                    try_positions = [
                        # 【最高优先级】弹窗内紧贴顶部边界
                        (px2 - offset_x, py1 + offset_y_near, "弹窗右上角"),
                        # 弹窗边界上方（浮动X按钮）
                        (px2 - offset_x, py1 - offset_y_above, "弹窗右上浮"),
                        # 弹窗正下方中间（底部关闭按钮）
                        ((px1 + px2) // 2, py2 + max(50, int(popup_height * 0.04)), "弹窗下方中间"),
                        # 弹窗正上方中间
                        ((px1 + px2) // 2, py1 - 40, "弹窗正上方"),
                    ]
                    
                    for try_x, try_y, position_name in try_positions:
                        if 0 <= try_x <= screen_width and 0 <= try_y <= screen_height:
                            self.client.u2.click(try_x, try_y)
                            time.sleep(0.3)
                    
                    # 尝试后截图，让 AI 判断是否成功
                    screenshot_result = self.take_screenshot("尝试关闭后")
                    return {
                        "success": True,
                        "message": f"✅ 已尝试点击常见关闭按钮位置",
                        "tried_positions": [p[2] for p in try_positions],
                        "screenshot": screenshot_result.get("screenshot_path", ""),
                        "tip": "请查看截图确认弹窗是否已关闭。如果还在，可手动分析截图找到关闭按钮位置。"
                    }
                
                # 没有检测到弹窗区域，截图让 AI 分析
                screenshot_result = self.take_screenshot(description="页面截图", compress=True)
                
                return {
                    "success": False,
                    "message": "❌ 未检测到弹窗区域，已截图供 AI 分析",
                    "action_required": "请查看截图找到关闭按钮，调用 mobile_click_at_coords 点击",
                    "screenshot": screenshot_result.get("screenshot_path", ""),
                    "screen_size": {"width": screen_width, "height": screen_height},
                    "image_size": {
                        "width": screenshot_result.get("image_width", screen_width),
                        "height": screenshot_result.get("image_height", screen_height)
                    },
                    "original_size": {
                        "width": screenshot_result.get("original_img_width", screen_width),
                        "height": screenshot_result.get("original_img_height", screen_height)
                    },
                    "search_areas": ["弹窗右上角", "弹窗正上方", "弹窗下方中间", "屏幕右上角"],
                    "time_warning": "⚠️ 截图分析期间弹窗可能自动消失。如果是定时弹窗，建议等待其自动消失。"
                }
            
            # 按得分排序，取最可能的
            close_candidates.sort(key=lambda x: x['score'], reverse=True)
            best = close_candidates[0]
            
            # 点击
            self.client.u2.click(best['center_x'], best['center_y'])
            time.sleep(0.5)
            
            # 点击后截图，让 AI 判断是否成功
            screenshot_result = self.take_screenshot("关闭弹窗后")
            
            # 记录操作（使用百分比，跨设备兼容）
            self._record_operation(
                'click',
                x=best['center_x'],
                y=best['center_y'],
                x_percent=best['x_percent'],
                y_percent=best['y_percent'],
                screen_width=screen_width,
                screen_height=screen_height,
                ref=f"close_popup_{best['position']}"
            )
            
            # 返回候选按钮列表，让 AI 看截图判断
            # 如果弹窗还在，AI 可以选择点击其他候选按钮
            return {
                "success": True,
                "message": f"✅ 已点击关闭按钮 ({best['position']}): ({best['center_x']}, {best['center_y']})",
                "clicked": {
                    "position": best['position'],
                    "match_type": best['match_type'],
                    "coords": (best['center_x'], best['center_y']),
                    "percent": (best['x_percent'], best['y_percent'])
                },
                "screenshot": screenshot_result.get("screenshot_path", ""),
                "popup_detected": popup_bounds is not None,
                "popup_bounds": f"[{popup_bounds[0]},{popup_bounds[1]}][{popup_bounds[2]},{popup_bounds[3]}]" if popup_bounds else None,
                "other_candidates": [
                    {
                        "position": c['position'], 
                        "type": c['match_type'], 
                        "coords": (c['center_x'], c['center_y']),
                        "percent": (c['x_percent'], c['y_percent'])
                    }
                    for c in close_candidates[1:4]  # 返回其他3个候选，AI 可以选择
                ],
                "tip": "请查看截图判断弹窗是否已关闭。如果弹窗还在，可以尝试点击 other_candidates 中的其他位置；如果误点跳转了，请按返回键"
            }
            
        except Exception as e:
            return {"success": False, "message": f"❌ 关闭弹窗失败: {e}"}
    
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
    
    def assert_text(self, text: str) -> Dict:
        """检查页面是否包含文本"""
        try:
            if self._is_ios():
                ios_client = self._get_ios_client()
                if ios_client and hasattr(ios_client, 'wda'):
                    exists = ios_client.wda(name=text).exists or ios_client.wda(label=text).exists
                else:
                    exists = False
            else:
                exists = self.client.u2(text=text).exists()
            
            return {
                "success": True,
                "found": exists,
                "text": text,
                "message": f"✅ 文本'{text}' {'存在' if exists else '不存在'}"
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
        
        script_lines = [
            "#!/usr/bin/env python3",
            "# -*- coding: utf-8 -*-",
            f'"""',
            f"测试用例: {test_name}",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "定位策略（按优先级）：",
            "1. ID 定位 - 最稳定，跨设备兼容",
            "2. 文本定位 - 稳定，跨设备兼容",
            "3. 百分比定位 - 跨分辨率兼容（坐标自动转换）",
            f'"""',
            "import time",
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
            "def test_main():",
            "    # 连接设备",
            "    d = u2.connect()",
            "    d.implicitly_wait(10)  # 设置全局等待",
            "    ",
            "    # 启动应用",
            f"    d.app_start(PACKAGE_NAME)",
            "    time.sleep(LAUNCH_WAIT)  # 等待启动（可调整）",
            "    ",
            "    # 尝试关闭启动广告（可选，根据 App 情况调整）",
            "    if CLOSE_AD_ON_LAUNCH:",
            "        close_ad_if_exists(d)",
            "    ",
        ]
        
        # 生成操作代码（跳过启动应用相关操作，因为脚本头部已处理）
        step_num = 0
        for op in self.operation_history:
            action = op.get('action')
            
            # 跳过 launch_app（脚本头部已经有 app_start）
            if action == 'launch_app':
                continue
            
            step_num += 1
            
            if action == 'click':
                ref = op.get('ref', '')
                element = op.get('element', '')
                has_coords = 'x' in op and 'y' in op
                has_percent = 'x_percent' in op and 'y_percent' in op
                
                # 判断 ref 是否为坐标格式（coords_ 或 coords:）
                is_coords_ref = ref.startswith('coords_') or ref.startswith('coords:')
                is_percent_ref = ref.startswith('percent_')
                
                # 优先级：ID > 文本 > 百分比 > 坐标（兜底）
                if ref and (':id/' in ref or ref.startswith('com.')):
                    # 1️⃣ 使用 resource-id（最稳定）
                    script_lines.append(f"    # 步骤{step_num}: 点击元素 (ID定位，最稳定)")
                    script_lines.append(f"    safe_click(d, d(resourceId='{ref}'))")
                elif ref and not is_coords_ref and not is_percent_ref and ':' not in ref:
                    # 2️⃣ 使用文本（稳定）- 排除 "text:xxx" 等带冒号的格式
                    script_lines.append(f"    # 步骤{step_num}: 点击文本 '{ref}' (文本定位)")
                    script_lines.append(f"    safe_click(d, d(text='{ref}'))")
                elif ref and ':' in ref and not is_coords_ref and not is_percent_ref:
                    # 2️⃣-b 使用文本（Android 的 text:xxx 或 description:xxx 格式）
                    # 提取冒号后面的实际文本值
                    actual_text = ref.split(':', 1)[1] if ':' in ref else ref
                    script_lines.append(f"    # 步骤{step_num}: 点击文本 '{actual_text}' (文本定位)")
                    script_lines.append(f"    safe_click(d, d(text='{actual_text}'))")
                elif has_percent:
                    # 3️⃣ 使用百分比（跨分辨率兼容）
                    x_pct = op['x_percent']
                    y_pct = op['y_percent']
                    desc = f" ({element})" if element else ""
                    script_lines.append(f"    # 步骤{step_num}: 点击位置{desc} (百分比定位，跨分辨率兼容)")
                    script_lines.append(f"    click_by_percent(d, {x_pct}, {y_pct})  # 原坐标: ({op.get('x', '?')}, {op.get('y', '?')})")
                elif has_coords:
                    # 4️⃣ 坐标兜底（不推荐，仅用于无法获取百分比的情况）
                    desc = f" ({element})" if element else ""
                    script_lines.append(f"    # 步骤{step_num}: 点击坐标{desc} (⚠️ 坐标定位，可能不兼容其他分辨率)")
                    script_lines.append(f"    d.click({op['x']}, {op['y']})")
                else:
                    continue  # 无效操作，跳过
                    
                script_lines.append("    time.sleep(0.5)  # 等待响应")
                script_lines.append("    ")
            
            elif action == 'input':
                text = op.get('text', '')
                ref = op.get('ref', '')
                has_coords = 'x' in op and 'y' in op
                has_percent = 'x_percent' in op and 'y_percent' in op
                
                # 判断 ref 是否为坐标格式
                is_coords_ref = ref.startswith('coords_') or ref.startswith('coords:')
                
                # 优先使用 ID，其次百分比，最后坐标
                if ref and not is_coords_ref and (':id/' in ref or ref.startswith('com.')):
                    # 完整格式的 resource-id
                    script_lines.append(f"    # 步骤{step_num}: 输入文本 '{text}' (ID定位)")
                    script_lines.append(f"    d(resourceId='{ref}').set_text('{text}')")
                elif ref and not is_coords_ref and not has_coords:
                    # 简短格式的 resource-id（不包含 com. 或 :id/）
                    script_lines.append(f"    # 步骤{step_num}: 输入文本 '{text}' (ID定位)")
                    script_lines.append(f"    d(resourceId='{ref}').set_text('{text}')")
                elif has_percent:
                    x_pct = op['x_percent']
                    y_pct = op['y_percent']
                    script_lines.append(f"    # 步骤{step_num}: 点击后输入 (百分比定位)")
                    script_lines.append(f"    click_by_percent(d, {x_pct}, {y_pct})")
                    script_lines.append(f"    time.sleep(0.3)")
                    script_lines.append(f"    d.send_keys('{text}')")
                elif has_coords:
                    script_lines.append(f"    # 步骤{step_num}: 点击坐标后输入 (⚠️ 可能不兼容其他分辨率)")
                    script_lines.append(f"    d.click({op['x']}, {op['y']})")
                    script_lines.append(f"    time.sleep(0.3)")
                    script_lines.append(f"    d.send_keys('{text}')")
                else:
                    # 兜底：无法识别的格式，跳过
                    continue
                script_lines.append("    time.sleep(0.5)")
                script_lines.append("    ")
            
            elif action == 'long_press':
                ref = op.get('ref', '')
                element = op.get('element', '')
                duration = op.get('duration', 1.0)
                has_coords = 'x' in op and 'y' in op
                has_percent = 'x_percent' in op and 'y_percent' in op
                
                # 判断 ref 是否为坐标格式
                is_coords_ref = ref.startswith('coords_') or ref.startswith('coords:')
                is_percent_ref = ref.startswith('percent_')
                
                # 优先级：ID > 文本 > 百分比 > 坐标
                if ref and (':id/' in ref or ref.startswith('com.')):
                    # 使用 resource-id
                    script_lines.append(f"    # 步骤{step_num}: 长按元素 (ID定位，最稳定)")
                    script_lines.append(f"    d(resourceId='{ref}').long_click(duration={duration})")
                elif ref and not is_coords_ref and not is_percent_ref and ':' not in ref:
                    # 使用文本
                    script_lines.append(f"    # 步骤{step_num}: 长按文本 '{ref}' (文本定位)")
                    script_lines.append(f"    d(text='{ref}').long_click(duration={duration})")
                elif ref and ':' in ref and not is_coords_ref and not is_percent_ref:
                    actual_text = ref.split(':', 1)[1] if ':' in ref else ref
                    script_lines.append(f"    # 步骤{step_num}: 长按文本 '{actual_text}' (文本定位)")
                    script_lines.append(f"    d(text='{actual_text}').long_click(duration={duration})")
                elif has_percent:
                    # 使用百分比
                    x_pct = op['x_percent']
                    y_pct = op['y_percent']
                    desc = f" ({element})" if element else ""
                    script_lines.append(f"    # 步骤{step_num}: 长按位置{desc} (百分比定位，跨分辨率兼容)")
                    script_lines.append(f"    long_press_by_percent(d, {x_pct}, {y_pct}, duration={duration})  # 原坐标: ({op.get('x', '?')}, {op.get('y', '?')})")
                elif has_coords:
                    # 坐标兜底
                    desc = f" ({element})" if element else ""
                    script_lines.append(f"    # 步骤{step_num}: 长按坐标{desc} (⚠️ 坐标定位，可能不兼容其他分辨率)")
                    script_lines.append(f"    d.long_click({op['x']}, {op['y']}, duration={duration})")
                else:
                    continue
                    
                script_lines.append("    time.sleep(0.5)  # 等待响应")
                script_lines.append("    ")
            
            elif action == 'swipe':
                direction = op.get('direction', 'up')
                script_lines.append(f"    # 步骤{step_num}: 滑动 {direction}")
                script_lines.append(f"    d.swipe_ext('{direction}')")
                script_lines.append("    time.sleep(0.5)")
                script_lines.append("    ")
            
            elif action == 'press_key':
                key = op.get('key', 'enter')
                script_lines.append(f"    # 步骤{step_num}: 按键 {key}")
                script_lines.append(f"    d.press('{key}')")
                script_lines.append("    time.sleep(0.5)")
                script_lines.append("    ")
        
        script_lines.extend([
            "    print('✅ 测试完成')",
            "",
            "",
            "if __name__ == '__main__':",
            "    test_main()",
        ])
        
        script = '\n'.join(script_lines)
        
        # 保存文件
        output_dir = Path("tests")
        output_dir.mkdir(exist_ok=True)
        
        if not filename.endswith('.py'):
            filename = f"{filename}.py"
        
        file_path = output_dir / filename
        file_path.write_text(script, encoding='utf-8')
        
        return {
            "success": True,
            "file_path": str(file_path),
            "message": f"✅ 脚本已生成: {file_path}",
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
            
            # ========== 第1步：控件树查找关闭按钮 ==========
            xml_string = self.client.u2.dump_hierarchy()
            root = ET.fromstring(xml_string)
            
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
                
                # 点击前截图（用于自动学习）
                pre_screenshot = None
                if auto_learn:
                    pre_result = self.take_screenshot(description="关闭前", compress=False)
                    pre_screenshot = pre_result.get("screenshot_path")
                
                # 点击
                self.click_at_coords(cx, cy)
                time.sleep(0.5)
                
                result["success"] = True
                result["method"] = "控件树"
                result["message"] = f"✅ 通过控件树找到关闭按钮并点击\n" \
                                   f"   位置: ({cx}, {cy})\n" \
                                   f"   原因: {best['reason']}"
                
                # 自动学习：检查这个 X 是否已在模板库，不在就添加
                if auto_learn and pre_screenshot:
                    learn_result = self._auto_learn_template(pre_screenshot, bounds)
                    if learn_result:
                        result["learned_template"] = learn_result
                        result["message"] += f"\n📚 自动学习: {learn_result}"
                
                return result
            
            # ========== 第2步：模板匹配 ==========
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
                        self.click_by_percent(x_pct, y_pct)
                        time.sleep(0.5)
                        
                        result["success"] = True
                        result["method"] = "模板匹配"
                        result["message"] = f"✅ 通过模板匹配找到关闭按钮并点击\n" \
                                           f"   模板: {best.get('template', 'unknown')}\n" \
                                           f"   置信度: {best.get('confidence', 'N/A')}%\n" \
                                           f"   位置: ({x_pct:.1f}%, {y_pct:.1f}%)"
                        return result
                    
            except ImportError:
                pass  # OpenCV 未安装，跳过模板匹配
            except Exception:
                pass  # 模板匹配失败，继续下一步
            
            # ========== 第3步：返回截图供 AI 分析 ==========
            if not screenshot_path:
                screenshot_result = self.take_screenshot(description="需要AI分析", compress=True)
            
            result["success"] = False
            result["method"] = None
            result["message"] = "❌ 控件树和模板匹配都未找到关闭按钮\n" \
                               "📸 已截图，请 AI 分析图片中的 X 按钮位置\n" \
                               "💡 找到后使用 mobile_click_by_percent(x%, y%) 点击"
            result["screenshot"] = screenshot_result if not screenshot_path else {"screenshot_path": screenshot_path}
            result["need_ai_analysis"] = True
            
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

