#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
位置分析器 - 通过XML的bounds信息定位无标识元素

核心思路：
1. 底部导航栏图标虽然没有text/desc/id，但有bounds坐标
2. 通过分析bounds的位置（Y坐标、X坐标）来定位
3. 完全免费，速度快（50-100ms）

适用场景：
✓ 底部导航栏图标（Y坐标在底部，X坐标均匀分布）
✓ 顶部导航栏图标（Y坐标在顶部）
✓ 悬浮按钮（固定位置）
✓ 网格布局的图标（如九宫格）
"""
import sys
import re
from typing import List, Dict, Optional, Tuple


class PositionAnalyzer:
    """位置分析器"""
    
    def __init__(self, screen_width: int = 1080, screen_height: int = 2400):
        """
        初始化位置分析器
        
        Args:
            screen_width: 屏幕宽度（默认1080）
            screen_height: 屏幕高度（默认2400）
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # 定义区域（可根据实际屏幕调整）
        self.regions = {
            'top': (0, int(screen_height * 0.1)),      # 顶部区域：0-10%
            'bottom': (int(screen_height * 0.85), screen_height),  # 底部区域：85-100%
            'left': (0, int(screen_width * 0.2)),      # 左侧区域：0-20%
            'right': (int(screen_width * 0.8), screen_width),  # 右侧区域：80-100%
        }
    
    def analyze_nth_element(self, elements: List[Dict], query: str) -> Optional[Dict]:
        """
        分析"第N个"元素（通用方法）
        
        支持的描述：
        - "第一个帖子"、"第二个帖子"、"第三个帖子"
        - "第1个按钮"、"第2个图标"
        - "第一个可点击元素"
        
        Args:
            elements: 所有元素列表
            query: 查询文本
        
        Returns:
            匹配的元素信息
        """
        # 提取序号
        index = self._extract_index(query)
        if index is None:
            return None
        
        print(f"  📍 位置分析：第{index}个元素", file=sys.stderr)
        
        # 提取关键词（帖子、按钮、图标等）
        keywords = []
        if '帖子' in query or '帖' in query:
            keywords = ['帖子', '帖']
        elif '按钮' in query:
            keywords = ['按钮', 'button']
        elif '图标' in query:
            keywords = ['图标', 'icon', 'image']
        elif '文本' in query or '文字' in query:
            keywords = ['文本', 'text']
        
        # 1. 筛选候选元素
        candidates = []
        
        # 如果有关键词，先按关键词筛选
        if keywords:
            for elem in elements:
                # 跳过系统栏元素
                if self._is_system_ui(elem):
                    continue
                
                # 检查class_name是否包含关键词
                class_name = elem.get('class_name', '').lower()
                text = elem.get('text', '').lower()
                desc = elem.get('content_desc', '').lower()
                
                # 帖子通常是可点击的、有一定大小的容器
                if '帖' in keywords:
                    if elem.get('clickable', False) or elem.get('long_clickable', False):
                        bounds = self._get_bounds(elem)
                        if bounds:
                            x1, y1, x2, y2 = bounds
                            width = x2 - x1
                            height = y2 - y1
                            center_y = (y1 + y2) // 2
                            center_x = (x1 + x2) // 2
                            
                            # 帖子卡片特征：
                            # 1. 宽度较大（至少屏幕宽度的50%，优先选择接近屏幕宽度的）
                            # 2. 高度在150-800px之间
                            # 3. 位于屏幕中间区域（Y坐标在200-2000之间，避开状态栏和底部导航栏）
                            # 4. 不是异常小的元素（避免选择帖子内部的图标、按钮等）
                            # 5. 过滤掉小的ImageView（通常是标签、图标，不是帖子卡片）
                            is_reasonable_width = (self.screen_width * 0.5 <= width <= self.screen_width * 1.1)
                            is_reasonable_height = (150 <= height <= 800)
                            is_middle_area = (200 <= center_y <= 2000)
                            is_not_too_small = (width * height > 50000)  # 面积至少50000像素
                            is_not_small_imageview = not (class_name.lower() == 'imageview' and width < 400 and height < 300)
                            
                            if is_reasonable_width and is_reasonable_height and is_middle_area and is_not_too_small and is_not_small_imageview:
                                candidates.append(elem)
                            else:
                                # 调试信息（只在详细模式下打印）
                                pass
                # 按钮
                elif '按钮' in keywords or 'button' in keywords:
                    if elem.get('clickable', False) or 'button' in class_name:
                        candidates.append(elem)
                # 图标
                elif '图标' in keywords or 'icon' in keywords or 'image' in keywords:
                    if 'image' in class_name or elem.get('clickable', False):
                        candidates.append(elem)
                # 文本
                elif '文本' in keywords or 'text' in keywords:
                    if 'text' in class_name and (text or desc):
                        candidates.append(elem)
        else:
            # 没有关键词，默认选择所有可点击元素
            for elem in elements:
                if self._is_system_ui(elem):
                    continue
                if elem.get('clickable', False) or elem.get('long_clickable', False):
                    candidates.append(elem)
        
        print(f"     → 找到 {len(candidates)} 个候选元素", file=sys.stderr)
        
        if not candidates:
            return None
        
        # 2. 按Y坐标（从上到下）排序
        sorted_candidates = sorted(candidates, key=lambda e: self._get_center_y(e))
        
        # 3. 选择第N个
        if index > len(sorted_candidates):
            print(f"     ❌ 只有 {len(sorted_candidates)} 个元素，无法选择第 {index} 个", file=sys.stderr)
            return None
        
        selected = sorted_candidates[index - 1]  # 转换为0-based索引
        center_x, center_y = self._get_center(selected)
        bounds = selected.get('bounds', '')
        
        print(f"     ✅ 选择第{index}个元素:", file=sys.stderr)
        print(f"        class: {selected.get('class_name', 'Unknown')}", file=sys.stderr)
        print(f"        text: {selected.get('text', '')}", file=sys.stderr)
        print(f"        desc: {selected.get('content_desc', '')}", file=sys.stderr)
        print(f"        中心点: ({center_x}, {center_y})", file=sys.stderr)
        print(f"        bounds: {bounds}", file=sys.stderr)
        
        # 返回结果
        return {
            'element': query,
            'ref': bounds,  # 使用bounds作为ref
            'confidence': 90,
            'method': 'position_analysis_nth',
            'x': center_x,
            'y': center_y,
        }
    
    def analyze_floating_button(self, elements: List[Dict], query: str) -> Optional[Dict]:
        """
        分析悬浮按钮（FloatingActionButton）
        
        特征：
        - 通常在右下角或底部中间
        - 大小接近正方形（100-300px）
        - Y坐标在1700-2100之间
        - 可点击
        - 通常没有text/desc
        
        Args:
            elements: 所有元素列表
            query: 查询文本（如"最下面悬浮按钮"、"右下角加号"）
        
        Returns:
            匹配的元素信息
        """
        print(f"  📍 位置分析：悬浮按钮", file=sys.stderr)
        
        # 1. 筛选候选元素
        candidates = []
        for elem in elements:
            if not elem.get('clickable', False):
                continue
            
            bounds = self._get_bounds(elem)
            if not bounds:
                continue
            
            x1, y1, x2, y2 = bounds
            width = x2 - x1
            height = y2 - y1
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            
            # 悬浮按钮特征：
            # 1. Y坐标在1700-2100之间（底部但不是最底部）
            # 2. 大小在100-300之间
            # 3. 接近正方形（宽高比0.7-1.3）
            if 1700 < center_y < 2100:
                if 100 < width < 300 and 100 < height < 300:
                    ratio = width / height if height > 0 else 0
                    if 0.7 < ratio < 1.3:
                        candidates.append({
                            'elem': elem,
                            'center': (center_x, center_y),
                            'size': (width, height),
                            'bounds': elem.get('bounds', ''),
                        })
        
        print(f"     → 找到 {len(candidates)} 个悬浮按钮候选", file=sys.stderr)
        
        if not candidates:
            return None
        
        # 2. 打印候选元素
        print(f"     📋 悬浮按钮候选元素:", file=sys.stderr)
        for i, cand in enumerate(candidates, 1):
            print(f"       [{i}] 中心点{cand['center']}, 大小{cand['size']}, bounds={cand['bounds']}", file=sys.stderr)
        
        # 3. 根据查询选择
        if "最下面" in query or "最下方" in query:
            # 选择Y坐标最大的（最下面的）
            selected = max(candidates, key=lambda c: c['center'][1])
            print(f"     ✅ 选择最下面的悬浮按钮: 中心点{selected['center']}", file=sys.stderr)
        elif "右下角" in query or "右下" in query:
            # 选择右下角的（X最大，Y最大）
            selected = max(candidates, key=lambda c: (c['center'][0] + c['center'][1]))
            print(f"     ✅ 选择右下角的悬浮按钮: 中心点{selected['center']}", file=sys.stderr)
        else:
            # 默认选择最下面的
            selected = max(candidates, key=lambda c: c['center'][1])
            print(f"     ✅ 默认选择最下面的悬浮按钮: 中心点{selected['center']}", file=sys.stderr)
        
        return {
            'element': query,
            'ref': selected['bounds'],
            'confidence': 95,
            'method': 'position_analysis_fab',
            'x': selected['center'][0],
            'y': selected['center'][1],
        }
    
    def analyze_bottom_navigation(self, elements: List[Dict], query: str) -> Optional[Dict]:
        """
        分析底部导航栏
        
        Args:
            elements: 所有元素列表
            query: 查询文本（如"底部导航栏第3个图标"）
        
        Returns:
            匹配的元素信息
        """
        print(f"  📍 位置分析：底部导航栏", file=sys.stderr)
        
        # 1. 筛选底部区域的元素
        bottom_elements = self._filter_by_region(elements, 'bottom')
        print(f"     → 底部区域元素: {len(bottom_elements)}个", file=sys.stderr)
        
        # 2. 筛选可点击的元素（导航栏图标通常是clickable）
        clickable_bottom = [e for e in bottom_elements if e.get('clickable', False)]
        print(f"     → 可点击元素: {len(clickable_bottom)}个", file=sys.stderr)
        
        if not clickable_bottom:
            print(f"     ❌ 底部没有可点击元素", file=sys.stderr)
            return None
        
        # 2.5. 过滤掉异常宽的元素（如全屏宽度的View）
        # 导航栏图标通常宽度在 50-300 之间
        filtered_elements = []
        for elem in clickable_bottom:
            bounds = self._get_bounds(elem)
            if bounds:
                x1, y1, x2, y2 = bounds
                width = x2 - x1
                # 过滤掉宽度 > 500 或 < 50 的元素
                if 50 <= width <= 500:
                    filtered_elements.append(elem)
        
        if filtered_elements:
            print(f"     → 过滤后元素: {len(filtered_elements)}个（过滤掉{len(clickable_bottom) - len(filtered_elements)}个异常宽度元素）", file=sys.stderr)
            clickable_bottom = filtered_elements
        
        # 3. 按X坐标排序（从左到右）
        sorted_elements = sorted(clickable_bottom, key=lambda e: self._get_center_x(e))
        
        # 4. 打印所有候选元素
        print(f"     📋 底部导航栏候选元素（从左到右）:", file=sys.stderr)
        for i, elem in enumerate(sorted_elements, 1):
            bounds = elem.get('bounds', '')
            center_x, center_y = self._get_center(elem)
            class_name = elem.get('class_name', '')
            text = elem.get('text', '')
            desc = elem.get('content_desc', '')
            
            info = f"class={class_name}"
            if text:
                info += f", text='{text}'"
            if desc:
                info += f", desc='{desc[:20]}'"
            
            print(f"       [{i}] 中心点({center_x}, {center_y}) | bounds={bounds} | {info}", file=sys.stderr)
        
        # 5. 根据查询提取索引
        index = self._extract_index(query)
        
        if index is None:
            # 没有明确索引，尝试关键词匹配
            print(f"     ⚠️  查询中没有明确索引，尝试关键词匹配...", file=sys.stderr)
            return self._match_by_keyword(sorted_elements, query)
        
        if index < 1 or index > len(sorted_elements):
            print(f"     ❌ 索引超出范围: {index}（共{len(sorted_elements)}个元素）", file=sys.stderr)
            return None
        
        # 6. 返回对应索引的元素
        selected = sorted_elements[index - 1]
        bounds = selected.get('bounds', '')
        center_x, center_y = self._get_center(selected)
        
        print(f"     ✅ 选择第{index}个元素:", file=sys.stderr)
        print(f"        中心点: ({center_x}, {center_y})", file=sys.stderr)
        print(f"        bounds: {bounds}", file=sys.stderr)
        
        return {
            'element': query,
            'ref': bounds,  # 使用bounds作为ref
            'confidence': 95,
            'method': 'position_analysis',
            'x': center_x,
            'y': center_y,
        }
    
    def analyze_corner_position(self, elements: List[Dict], query: str, corner: str = 'top_right') -> Optional[Dict]:
        """
        分析角落位置（右上角、左上角、右下角、左下角）
        
        Args:
            elements: 所有元素列表
            query: 查询文本（如"右上角搜索图标"）
            corner: 角落位置（'top_right', 'top_left', 'bottom_right', 'bottom_left'）
        
        Returns:
            匹配的元素信息
        """
        print(f"  📍 位置分析：{corner}角落", file=sys.stderr)
        
        # 定义角落区域（屏幕的10%区域）
        corner_threshold = 0.1  # 10%
        
        # 根据角落类型定义筛选条件
        if corner == 'top_right':
            # 右上角：X坐标在右侧10%，Y坐标在顶部10%
            x_min = self.screen_width * (1 - corner_threshold)
            y_max = self.screen_height * corner_threshold
        elif corner == 'top_left':
            # 左上角：X坐标在左侧10%，Y坐标在顶部10%
            x_max = self.screen_width * corner_threshold
            y_max = self.screen_height * corner_threshold
        elif corner == 'bottom_right':
            # 右下角：X坐标在右侧10%，Y坐标在底部10%
            x_min = self.screen_width * (1 - corner_threshold)
            y_min = self.screen_height * (1 - corner_threshold)
        elif corner == 'bottom_left':
            # 左下角：X坐标在左侧10%，Y坐标在底部10%
            x_max = self.screen_width * corner_threshold
            y_min = self.screen_height * (1 - corner_threshold)
        else:
            return None
        
        # 1. 筛选候选元素（可点击的图标元素）
        candidates = []
        for elem in elements:
            if not elem.get('clickable', False):
                continue
            
            # 如果是图标查询，优先选择Image/ImageView类型
            if '图标' in query:
                class_name = elem.get('class_name', '').lower()
                if 'image' not in class_name and class_name not in ['imageview', 'imagebutton']:
                    continue
            
            bounds = self._get_bounds(elem)
            if not bounds:
                continue
            
            x1, y1, x2, y2 = bounds
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            
            # 检查是否在角落区域
            in_corner = False
            if corner == 'top_right':
                in_corner = center_x >= x_min and center_y <= y_max
            elif corner == 'top_left':
                in_corner = center_x <= x_max and center_y <= y_max
            elif corner == 'bottom_right':
                in_corner = center_x >= x_min and center_y >= y_min
            elif corner == 'bottom_left':
                in_corner = center_x <= x_max and center_y >= y_min
            
            if in_corner:
                candidates.append({
                    'elem': elem,
                    'center': (center_x, center_y),
                    'bounds': elem.get('bounds', ''),
                })
        
        print(f"     → 找到 {len(candidates)} 个{corner}角落候选元素", file=sys.stderr)
        
        if not candidates:
            return None
        
        # 2. 如果有多个候选，选择最接近角落的（距离角落最近）
        if len(candidates) > 1:
            # 计算每个候选到角落的距离
            for cand in candidates:
                center_x, center_y = cand['center']
                if corner == 'top_right':
                    # 距离右上角的距离（越小越好）
                    distance = (self.screen_width - center_x) + center_y
                elif corner == 'top_left':
                    distance = center_x + center_y
                elif corner == 'bottom_right':
                    distance = (self.screen_width - center_x) + (self.screen_height - center_y)
                elif corner == 'bottom_left':
                    distance = center_x + (self.screen_height - center_y)
                else:
                    distance = 0
                cand['distance'] = distance
            
            # 选择距离最小的
            selected = min(candidates, key=lambda c: c['distance'])
        else:
            selected = candidates[0]
        
        center_x, center_y = selected['center']
        bounds = selected['bounds']
        
        print(f"     ✅ 选择{corner}角落元素:", file=sys.stderr)
        print(f"        中心点: ({center_x}, {center_y})", file=sys.stderr)
        print(f"        bounds: {bounds}", file=sys.stderr)
        
        return {
            'element': query,
            'ref': bounds,
            'confidence': 95,
            'method': 'position_analysis_corner',
            'x': center_x,
            'y': center_y,
        }
    
    def analyze_top_navigation(self, elements: List[Dict], query: str) -> Optional[Dict]:
        """
        分析顶部导航栏
        
        Args:
            elements: 所有元素列表
            query: 查询文本（如"顶部第2个图标"）
        
        Returns:
            匹配的元素信息
        """
        print(f"  📍 位置分析：顶部导航栏", file=sys.stderr)
        
        # 1. 筛选顶部区域的元素
        top_elements = self._filter_by_region(elements, 'top')
        print(f"     → 顶部区域元素: {len(top_elements)}个", file=sys.stderr)
        
        # 2. 筛选可点击的元素
        clickable_top = [e for e in top_elements if e.get('clickable', False)]
        print(f"     → 可点击元素: {len(clickable_top)}个", file=sys.stderr)
        
        if not clickable_top:
            print(f"     ❌ 顶部没有可点击元素", file=sys.stderr)
            return None
        
        # 3. 按X坐标排序（从左到右）
        sorted_elements = sorted(clickable_top, key=lambda e: self._get_center_x(e))
        
        # 4. 根据查询提取索引
        index = self._extract_index(query)
        
        if index is None or index < 1 or index > len(sorted_elements):
            print(f"     ❌ 无法确定索引", file=sys.stderr)
            return None
        
        # 5. 返回对应索引的元素
        selected = sorted_elements[index - 1]
        bounds = selected.get('bounds', '')
        center_x, center_y = self._get_center(selected)
        
        print(f"     ✅ 选择第{index}个元素: 中心点({center_x}, {center_y})", file=sys.stderr)
        
        return {
            'element': query,
            'ref': bounds,
            'confidence': 95,
            'method': 'position_analysis',
            'x': center_x,
            'y': center_y,
        }
    
    def analyze_grid_layout(self, elements: List[Dict], query: str, rows: int = 3, cols: int = 3) -> Optional[Dict]:
        """
        分析网格布局（如九宫格）
        
        Args:
            elements: 所有元素列表
            query: 查询文本（如"第2行第3列的图标"）
            rows: 行数
            cols: 列数
        
        Returns:
            匹配的元素信息
        """
        print(f"  📍 位置分析：网格布局 ({rows}x{cols})", file=sys.stderr)
        
        # 1. 筛选可点击的元素
        clickable = [e for e in elements if e.get('clickable', False)]
        
        # 2. 按Y坐标分组（行）
        rows_groups = self._group_by_y(clickable, rows)
        
        # 3. 每行按X坐标排序（列）
        grid = []
        for row in rows_groups:
            sorted_row = sorted(row, key=lambda e: self._get_center_x(e))
            grid.append(sorted_row)
        
        # 4. 提取行列索引
        row_idx, col_idx = self._extract_grid_index(query)
        
        if row_idx is None or col_idx is None:
            print(f"     ❌ 无法解析网格索引", file=sys.stderr)
            return None
        
        if row_idx >= len(grid) or col_idx >= len(grid[row_idx]):
            print(f"     ❌ 索引超出范围", file=sys.stderr)
            return None
        
        # 5. 返回对应位置的元素
        selected = grid[row_idx][col_idx]
        bounds = selected.get('bounds', '')
        center_x, center_y = self._get_center(selected)
        
        print(f"     ✅ 选择第{row_idx+1}行第{col_idx+1}列: 中心点({center_x}, {center_y})", file=sys.stderr)
        
        return {
            'element': query,
            'ref': bounds,
            'confidence': 90,
            'method': 'position_analysis',
            'x': center_x,
            'y': center_y,
        }
    
    # ========================================
    # 辅助方法
    # ========================================
    
    def _filter_by_region(self, elements: List[Dict], region: str) -> List[Dict]:
        """
        按区域筛选元素
        
        Args:
            elements: 所有元素
            region: 区域名称（'top', 'bottom', 'left', 'right'）
        
        Returns:
            筛选后的元素列表
        """
        if region not in self.regions:
            return elements
        
        region_range = self.regions[region]
        filtered = []
        
        for elem in elements:
            bounds = elem.get('bounds', '')
            if not bounds:
                continue
            
            center_x, center_y = self._get_center(elem)
            
            if region in ['top', 'bottom']:
                # 按Y坐标筛选
                if region_range[0] <= center_y <= region_range[1]:
                    filtered.append(elem)
            elif region in ['left', 'right']:
                # 按X坐标筛选
                if region_range[0] <= center_x <= region_range[1]:
                    filtered.append(elem)
        
        return filtered
    
    def _get_bounds(self, element: Dict) -> Optional[Tuple[int, int, int, int]]:
        """
        解析bounds字符串
        
        Args:
            element: 元素信息
        
        Returns:
            (x1, y1, x2, y2) 或 None
        """
        bounds = element.get('bounds', '')
        if not bounds:
            return None
        
        # bounds格式: "[x1,y1][x2,y2]"
        match = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
        if match:
            x1, y1, x2, y2 = map(int, match.groups())
            return (x1, y1, x2, y2)
        
        return None
    
    def _get_center(self, element: Dict) -> Tuple[int, int]:
        """
        获取元素中心点坐标
        
        Args:
            element: 元素信息
        
        Returns:
            (center_x, center_y)
        """
        bounds = self._get_bounds(element)
        if bounds:
            x1, y1, x2, y2 = bounds
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            return (center_x, center_y)
        
        return (0, 0)
    
    def _get_center_x(self, element: Dict) -> int:
        """获取元素中心点X坐标"""
        return self._get_center(element)[0]
    
    def _get_center_y(self, element: Dict) -> int:
        """获取元素中心点Y坐标"""
        return self._get_center(element)[1]
    
    def _is_system_ui(self, elem: Dict) -> bool:
        """
        判断是否是系统UI元素（状态栏、导航栏等）
        
        Args:
            elem: 元素字典
        
        Returns:
            True if system UI, False otherwise
        """
        resource_id = elem.get('resource_id', '')
        class_name = elem.get('class_name', '')
        
        # 系统UI的resource-id通常以这些开头
        system_prefixes = [
            'com.android.systemui',
            'android:id/statusBarBackground',
            'android:id/navigationBarBackground',
        ]
        
        return any(resource_id.startswith(prefix) for prefix in system_prefixes)
    
    def _extract_index(self, query: str) -> Optional[int]:
        """
        从查询中提取索引
        
        Args:
            query: 查询文本（支持"第一个"、"第1个"等）
        
        Returns:
            索引（1-based）或 None
        """
        # 中文数字映射
        chinese_numbers = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
            '1': 1, '2': 2, '3': 3, '4': 4, '5': 5,
            '6': 6, '7': 7, '8': 8, '9': 9, '0': 10,
        }
        
        # 匹配"第X个"、"第X项"、"第X列"等（支持中文数字）
        patterns = [
            r'第([一二三四五六七八九十\d]+)个',
            r'第([一二三四五六七八九十\d]+)项',
            r'第([一二三四五六七八九十\d]+)列',
            r'([一二三四五六七八九十\d]+)号',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                num_str = match.group(1)
                # 尝试转换为数字
                if num_str.isdigit():
                    return int(num_str)
                elif num_str in chinese_numbers:
                    return chinese_numbers[num_str]
        
        return None
    
    def _extract_grid_index(self, query: str) -> Tuple[Optional[int], Optional[int]]:
        """
        从查询中提取网格索引
        
        Args:
            query: 查询文本（如"第2行第3列"）
        
        Returns:
            (row_index, col_index) 或 (None, None)
        """
        # 匹配"第X行第Y列"
        match = re.search(r'第(\d+)行第(\d+)列', query)
        if match:
            row = int(match.group(1)) - 1  # 转换为0-based
            col = int(match.group(2)) - 1
            return (row, col)
        
        return (None, None)
    
    def _group_by_y(self, elements: List[Dict], num_groups: int) -> List[List[Dict]]:
        """
        按Y坐标分组
        
        Args:
            elements: 元素列表
            num_groups: 分组数量
        
        Returns:
            分组后的元素列表
        """
        # 按Y坐标排序
        sorted_elements = sorted(elements, key=lambda e: self._get_center_y(e))
        
        # 平均分组
        group_size = len(sorted_elements) // num_groups
        groups = []
        
        for i in range(num_groups):
            start = i * group_size
            end = start + group_size if i < num_groups - 1 else len(sorted_elements)
            groups.append(sorted_elements[start:end])
        
        return groups
    
    def _match_by_keyword(self, elements: List[Dict], query: str) -> Optional[Dict]:
        """
        通过关键词匹配元素
        
        Args:
            elements: 候选元素列表（已排序）
            query: 查询文本
        
        Returns:
            匹配的元素信息
        """
        # 关键词映射（可扩展）
        keyword_map = {
            '首页': 0,
            'home': 0,
            '发现': 1,
            'discover': 1,
            '社区': 2,
            'community': 2,
            '我的': 3,
            'profile': 3,
            '个人': 3,
        }
        
        query_lower = query.lower()
        
        for keyword, index in keyword_map.items():
            if keyword in query_lower:
                if index < len(elements):
                    selected = elements[index]
                    bounds = selected.get('bounds', '')
                    center_x, center_y = self._get_center(selected)
                    
                    print(f"     ✅ 关键词匹配: '{keyword}' → 第{index+1}个元素", file=sys.stderr)
                    print(f"        中心点: ({center_x}, {center_y})", file=sys.stderr)
                    
                    return {
                        'element': query,
                        'ref': bounds,
                        'confidence': 90,
                        'method': 'position_analysis_keyword',
                        'x': center_x,
                        'y': center_y,
                    }
        
        print(f"     ❌ 未找到匹配的关键词", file=sys.stderr)
        return None

