"""
OpenCV 模板匹配器 - 用于精确识别广告弹窗X号
核心优势：
1. 收集常见X号样式建立模板库
2. 多尺度匹配解决分辨率差异
3. 返回精确坐标，点击准确率高
"""

import os
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class TemplateMatcher:
    """OpenCV 模板匹配器"""
    
    def __init__(self, template_dir: Optional[str] = None):
        """
        初始化模板匹配器
        
        Args:
            template_dir: 模板目录路径，默认为 templates/close_buttons/
        """
        if template_dir is None:
            # 默认模板目录
            base_dir = Path(__file__).parent.parent
            self.template_dir = base_dir / "templates" / "close_buttons"
        else:
            self.template_dir = Path(template_dir)
        
        # 确保目录存在
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        # 多尺度匹配的缩放范围
        self.scales = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5, 1.8, 2.0]
        
        # 匹配阈值（越高越严格）
        self.match_threshold = 0.75
        
        # 缓存加载的模板
        self._template_cache: Dict[str, np.ndarray] = {}
    
    def load_templates(self) -> List[Tuple[str, np.ndarray]]:
        """
        加载所有模板图片
        
        Returns:
            List of (template_name, template_image) tuples
        """
        templates = []
        
        if not self.template_dir.exists():
            return templates
        
        # 支持的图片格式
        extensions = ['.png', '.jpg', '.jpeg', '.bmp']
        
        for file in self.template_dir.iterdir():
            if file.suffix.lower() in extensions:
                template_name = file.stem
                
                # 使用缓存
                if template_name in self._template_cache:
                    templates.append((template_name, self._template_cache[template_name]))
                    continue
                
                # 读取模板（支持透明通道）
                template = cv2.imread(str(file), cv2.IMREAD_UNCHANGED)
                if template is not None:
                    self._template_cache[template_name] = template
                    templates.append((template_name, template))
        
        return templates
    
    def match_single_template(
        self, 
        screenshot: np.ndarray, 
        template: np.ndarray,
        threshold: Optional[float] = None
    ) -> List[Dict]:
        """
        单模板多尺度匹配
        
        Args:
            screenshot: 截图 (BGR格式)
            template: 模板图片
            threshold: 匹配阈值
            
        Returns:
            匹配结果列表
        """
        if threshold is None:
            threshold = self.match_threshold
        
        results = []
        
        # 转灰度图
        if len(screenshot.shape) == 3:
            gray_screen = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        else:
            gray_screen = screenshot
        
        # 处理模板（可能有透明通道）
        # 注意：不使用 mask，因为 TM_CCOEFF_NORMED + mask 可能返回 INF
        if len(template.shape) == 3:
            if template.shape[2] == 4:  # BGRA
                template_gray = cv2.cvtColor(template[:, :, :3], cv2.COLOR_BGR2GRAY)
            else:  # BGR
                template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        else:
            template_gray = template
        
        template_h, template_w = template_gray.shape[:2]
        
        # 多尺度匹配
        for scale in self.scales:
            # 缩放模板
            new_w = int(template_w * scale)
            new_h = int(template_h * scale)
            
            # 跳过太小或太大的模板
            if new_w < 10 or new_h < 10:
                continue
            if new_w > gray_screen.shape[1] or new_h > gray_screen.shape[0]:
                continue
            
            resized_template = cv2.resize(template_gray, (new_w, new_h))
            
            # 模板匹配
            try:
                result = cv2.matchTemplate(
                    gray_screen, resized_template, 
                    cv2.TM_CCOEFF_NORMED
                )
            except cv2.error:
                continue
            
            # 跳过包含 INF/NAN 的结果
            if np.isinf(result).any() or np.isnan(result).any():
                continue
            
            # 找所有超过阈值的匹配点
            locations = np.where(result >= threshold)
            
            for pt in zip(*locations[::-1]):  # (x, y)
                confidence = float(result[pt[1], pt[0]])
                center_x = int(pt[0] + new_w // 2)
                center_y = int(pt[1] + new_h // 2)
                
                results.append({
                    'x': center_x,
                    'y': center_y,
                    'width': int(new_w),
                    'height': int(new_h),
                    'scale': float(scale),
                    'confidence': confidence,
                    'top_left': (int(pt[0]), int(pt[1])),
                    'bottom_right': (int(pt[0] + new_w), int(pt[1] + new_h))
                })
        
        # 非极大值抑制（去除重叠的检测框）
        results = self._non_max_suppression(results)
        
        return results
    
    def _non_max_suppression(self, results: List[Dict], overlap_thresh: float = 0.3) -> List[Dict]:
        """
        非极大值抑制，去除重叠的检测框
        """
        if len(results) == 0:
            return []
        
        # 按置信度排序
        results = sorted(results, key=lambda x: x['confidence'], reverse=True)
        
        kept = []
        for result in results:
            is_duplicate = False
            for kept_result in kept:
                # 计算中心点距离
                dx = abs(result['x'] - kept_result['x'])
                dy = abs(result['y'] - kept_result['y'])
                
                # 如果中心点距离小于框的一半大小，认为是重复
                avg_size = (result['width'] + result['height'] + 
                           kept_result['width'] + kept_result['height']) / 4
                
                if dx < avg_size * overlap_thresh and dy < avg_size * overlap_thresh:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                kept.append(result)
        
        return kept
    
    def find_close_buttons(
        self, 
        screenshot_path: str,
        threshold: Optional[float] = None
    ) -> Dict:
        """
        在截图中查找所有关闭按钮
        
        Args:
            screenshot_path: 截图路径
            threshold: 匹配阈值 (0-1)
            
        Returns:
            匹配结果
        """
        # 读取截图
        screenshot = cv2.imread(screenshot_path)
        if screenshot is None:
            return {
                "success": False,
                "error": f"无法读取截图: {screenshot_path}"
            }
        
        img_height, img_width = screenshot.shape[:2]
        
        # 加载模板
        templates = self.load_templates()
        if not templates:
            return {
                "success": False,
                "error": "没有找到模板图片，请在 templates/close_buttons/ 目录添加X号模板",
                "template_dir": str(self.template_dir),
                "tip": "添加常见X号截图到模板目录，命名如 x_circle.png, x_white.png 等"
            }
        
        all_matches = []
        
        for template_name, template in templates:
            matches = self.match_single_template(screenshot, template, threshold)
            for match in matches:
                match['template'] = template_name
                all_matches.append(match)
        
        # 按置信度排序
        all_matches = sorted(all_matches, key=lambda x: x['confidence'], reverse=True)
        
        # 再次 NMS 去除不同模板的重复检测
        all_matches = self._non_max_suppression(all_matches)
        
        if not all_matches:
            return {
                "success": False,
                "message": "未找到匹配的关闭按钮",
                "templates_used": [t[0] for t in templates],
                "threshold": threshold or self.match_threshold,
                "tip": "可能需要添加新的X号模板，或降低匹配阈值"
            }
        
        # 计算百分比坐标
        for match in all_matches:
            match['x_percent'] = round(match['x'] / img_width * 100, 1)
            match['y_percent'] = round(match['y'] / img_height * 100, 1)
        
        best = all_matches[0]
        
        return {
            "success": True,
            "message": f"✅ 找到 {len(all_matches)} 个关闭按钮",
            "best_match": {
                "template": best['template'],
                "center": {"x": int(best['x']), "y": int(best['y'])},
                "percent": {"x": float(best['x_percent']), "y": float(best['y_percent'])},
                "size": f"{best['width']}x{best['height']}",
                "confidence": float(round(best['confidence'] * 100, 1))
            },
            "click_command": f"mobile_click_by_percent({best['x_percent']}, {best['y_percent']})",
            "all_matches": [
                {
                    "template": m['template'],
                    "percent": f"({m['x_percent']}%, {m['y_percent']}%)",
                    "confidence": f"{m['confidence']*100:.1f}%"
                }
                for m in all_matches[:5]  # 最多返回5个
            ],
            "image_size": {"width": img_width, "height": img_height}
        }
    
    def add_template(self, image_path: str, template_name: str) -> Dict:
        """
        添加新模板到模板库
        
        Args:
            image_path: 图片路径（可以是截图的一部分）
            template_name: 模板名称
            
        Returns:
            结果
        """
        # 读取图片
        img = cv2.imread(image_path)
        if img is None:
            return {"success": False, "error": f"无法读取图片: {image_path}"}
        
        # 保存到模板目录
        output_path = self.template_dir / f"{template_name}.png"
        cv2.imwrite(str(output_path), img)
        
        # 清除缓存
        self._template_cache.clear()
        
        return {
            "success": True,
            "message": f"✅ 模板已保存: {output_path}",
            "template_name": template_name
        }
    
    def crop_and_add_template(
        self, 
        screenshot_path: str, 
        x: int, y: int, 
        width: int, height: int,
        template_name: str
    ) -> Dict:
        """
        从截图中裁剪区域并添加为模板
        
        Args:
            screenshot_path: 截图路径
            x, y: 左上角坐标
            width, height: 裁剪尺寸
            template_name: 模板名称
            
        Returns:
            结果
        """
        img = cv2.imread(screenshot_path)
        if img is None:
            return {"success": False, "error": f"无法读取截图: {screenshot_path}"}
        
        # 裁剪
        cropped = img[y:y+height, x:x+width]
        
        if cropped.size == 0:
            return {"success": False, "error": "裁剪区域无效"}
        
        # 保存
        output_path = self.template_dir / f"{template_name}.png"
        cv2.imwrite(str(output_path), cropped)
        
        # 清除缓存
        self._template_cache.clear()
        
        return {
            "success": True,
            "message": f"✅ 模板已保存: {output_path}",
            "template_name": template_name,
            "size": f"{width}x{height}"
        }
    
    def list_templates(self) -> Dict:
        """列出所有模板"""
        templates = self.load_templates()
        
        if not templates:
            return {
                "success": True,
                "templates": [],
                "message": "模板库为空",
                "template_dir": str(self.template_dir)
            }
        
        template_info = []
        for name, img in templates:
            h, w = img.shape[:2]
            template_info.append({
                "name": name,
                "size": f"{w}x{h}",
                "path": str(self.template_dir / f"{name}.png")
            })
        
        return {
            "success": True,
            "templates": template_info,
            "count": len(template_info),
            "template_dir": str(self.template_dir)
        }
    
    def delete_template(self, template_name: str) -> Dict:
        """删除模板"""
        # 查找模板文件
        for ext in ['.png', '.jpg', '.jpeg', '.bmp']:
            path = self.template_dir / f"{template_name}{ext}"
            if path.exists():
                path.unlink()
                self._template_cache.pop(template_name, None)
                return {
                    "success": True,
                    "message": f"✅ 已删除模板: {template_name}"
                }
        
        return {
            "success": False,
            "error": f"模板不存在: {template_name}"
        }


# 便捷函数
def match_close_button(screenshot_path: str, threshold: float = 0.75) -> Dict:
    """
    快速匹配关闭按钮
    
    用法：
        from core.template_matcher import match_close_button
        result = match_close_button("screenshot.png")
        if result["success"]:
            print(result["click_command"])
    """
    matcher = TemplateMatcher()
    return matcher.find_close_buttons(screenshot_path, threshold)

