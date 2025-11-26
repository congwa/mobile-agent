#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
移动端SmartLocator适配器 - 复用现有SmartLocator逻辑

策略：
1. Level 1: 规则匹配（免费，85%）
2. Level 2: 缓存查询（免费，5%）
3. Level 3: XML深度分析（免费，5%）
4. Level 4: 视觉识别（付费，4%）
5. Level 5: 文本AI分析（付费，1%）
"""
import hashlib
import time
from typing import Dict, Optional
# 复用现有的SmartLocator（通过导入，不修改原代码）
import sys
from pathlib import Path as PathLib

# 添加browser_mcp路径以便导入
# mobile_mcp现在在backend/mobile_mcp，browser_mcp在backend/mind-ui/browser_mcp
current_file = PathLib(__file__)
# 从 backend/mobile_mcp/core/locator/mobile_smart_locator.py
# 到 backend/mind-ui/browser_mcp
# 路径: backend/mobile_mcp/core/locator -> backend/mind-ui
mind_ui_path = current_file.parent.parent.parent.parent / 'mind-ui'
if mind_ui_path.exists():
    sys.path.insert(0, str(mind_ui_path))

try:
    from browser_mcp.core.locator.smart_locator import SmartLocator
    SMART_LOCATOR_AVAILABLE = True
except ImportError:
    SMART_LOCATOR_AVAILABLE = False
    print("⚠️  无法导入SmartLocator，将使用简化版本", file=sys.stderr)


class MobileSmartLocator:
    """
    移动端SmartLocator适配器
    
    复用现有SmartLocator逻辑，适配移动端格式
    """
    
    def __init__(self, mobile_client):
        """
        初始化移动端SmartLocator
        
        Args:
            mobile_client: MobileClient实例
        """
        self.mobile_client = mobile_client
        
        # 缓存
        self._cache: Dict[str, Dict] = {}
        self._cache_ttl = 300  # 5分钟
        
        # 统计
        self.stats = {
            'total': 0,
            'rule_hits': 0,
            'cache_hits': 0,
            'quick_match_hits': 0,
            'xml_analysis': 0,
            'vision_calls': 0,
            'ai_calls': 0,
            'xml_read_count': 0,  # XML读取次数
            'total_time': 0.0,  # 总耗时（毫秒）
        }
        
        # 性能监控
        self.performance_logs = []  # 详细性能日志
        
        # 如果可用，复用现有SmartLocator
        if SMART_LOCATOR_AVAILABLE:
            # 创建适配器，让SmartLocator可以调用mobile_client的方法
            self.smart_locator = SmartLocator(self._create_adapter())
        else:
            self.smart_locator = None
    
    def _create_adapter(self):
        """创建适配器，让SmartLocator可以调用mobile_client的方法"""
        class Adapter:
            def __init__(self, mobile_client):
                self.mobile_client = mobile_client
            
            async def snapshot(self):
                # 返回格式化的字符串，SmartLocator的规则匹配器会调用extract_snapshot_content
                # extract_snapshot_content会处理字符串类型
                snapshot_str = await self.mobile_client.snapshot()
                
                # 包装成类似MCP CallToolResult的格式，以便兼容
                class SnapshotResult:
                    def __init__(self, text):
                        self.content = [type('Content', (), {'text': text})()]
                
                return SnapshotResult(snapshot_str)
        
        return Adapter(self.mobile_client)
    
    async def locate(self, query: str, wait_for_popup: bool = True, max_wait: float = 3.0) -> Optional[Dict]:
        """
        智能定位元素
        
        Args:
            query: 自然语言查询
            wait_for_popup: 是否等待弹窗出现（默认True，适用于弹窗场景）
            max_wait: 最大等待时间（秒，默认3秒）
            
        Returns:
            定位结果 或 None
        """
        import time
        start_time = time.time()
        
        self.stats['total'] += 1
        
        print(f"\n🔍 MobileSmartLocator 定位: {query}", file=sys.stderr)
        
        # Level 1: 缓存查询（最快）
        cache_start = time.time()
        cache_result = await self._try_cache(query)
        cache_time = (time.time() - cache_start) * 1000
        
        if cache_result:
            self.stats['cache_hits'] += 1
            elapsed_time = (time.time() - start_time) * 1000
            self.stats['total_time'] += elapsed_time
            print(f"  ✅ 缓存命中！耗时: {elapsed_time:.2f}ms", file=sys.stderr)
            self._log_performance(query, 'cache', elapsed_time, 0)
            return cache_result
        
        # 🎯 弹窗场景：如果启用等待，先等待一段时间让弹窗出现
        if wait_for_popup:
            import asyncio
            await asyncio.sleep(0.5)  # 先等待0.5秒，让弹窗有时间出现
        
        # ⚡ 优化：一次定位只读一次XML（避免重复读取，节省400-1000ms）
        print(f"  📱 读取页面XML...", file=sys.stderr)
        
        # 分步计时：XML读取
        xml_read_start = time.time()
        xml_string = self.mobile_client.u2.dump_hierarchy()
        xml_read_time = (time.time() - xml_read_start) * 1000
        print(f"     ⏱️  XML读取: {xml_read_time:.2f}ms", file=sys.stderr)
        
        # 分步计时：XML解析
        xml_parse_start = time.time()
        elements = self.mobile_client.xml_parser.parse(xml_string)
        xml_parse_time = (time.time() - xml_parse_start) * 1000
        print(f"     ⏱️  XML解析: {xml_parse_time:.2f}ms (共{len(elements)}个元素)", file=sys.stderr)
        
        xml_time = xml_read_time + xml_parse_time
        self.stats['xml_read_count'] += 1
        print(f"  ✅ XML处理完成，总耗时: {xml_time:.2f}ms (读取: {xml_read_time:.0f}ms + 解析: {xml_parse_time:.0f}ms)", file=sys.stderr)
        
        # Level 1.5: 快速预匹配（针对容易歧义的查询）
        # 例如："点击 输入邮箱" - 包含"输入"但不是输入操作，而是页签
        quick_result = await self._try_quick_match(elements, query)
        if quick_result:
            self.stats['quick_match_hits'] += 1
            elapsed_time = (time.time() - start_time) * 1000
            self.stats['total_time'] += elapsed_time
            print(f"  ✅ 快速预匹配成功！总耗时: {elapsed_time:.2f}ms (XML: {xml_time:.2f}ms)", file=sys.stderr)
            await self._cache_result(query, quick_result)
            self._log_performance(query, 'quick_match', elapsed_time, 1, xml_time)
            return quick_result
        
        # Level 2: 规则匹配（如果SmartLocator可用）
        if self.smart_locator:
            rule_result = await self._try_rule_match(elements, query)
            if rule_result:
                self.stats['rule_hits'] += 1
                elapsed_time = (time.time() - start_time) * 1000
                self.stats['total_time'] += elapsed_time
                print(f"  ✅ 规则匹配成功！总耗时: {elapsed_time:.2f}ms (XML: {xml_time:.2f}ms)", file=sys.stderr)
                await self._cache_result(query, rule_result)
                self._log_performance(query, 'rule_match', elapsed_time, 1, xml_time)
                return rule_result
        
        # Level 3: XML深度分析（免费，快速）
        xml_result, candidates = await self._try_xml_analysis(elements, query)
        if xml_result:
            self.stats['xml_analysis'] += 1
            elapsed_time = (time.time() - start_time) * 1000
            self.stats['total_time'] += elapsed_time
            print(f"  ✅ XML分析成功: {xml_result.get('element', '')} 总耗时: {elapsed_time:.2f}ms (XML: {xml_time:.2f}ms)", file=sys.stderr)
            await self._cache_result(query, xml_result)
            self._log_performance(query, 'xml_analysis', elapsed_time, 1, xml_time)
            return xml_result
        
        # Level 3.5: 位置分析（免费，快速）⭐ 新增
        position_result = await self._try_position_analysis(elements, query)
        if position_result:
            self.stats['position_analysis'] = self.stats.get('position_analysis', 0) + 1
            elapsed_time = (time.time() - start_time) * 1000
            self.stats['total_time'] += elapsed_time
            print(f"  ✅ 位置分析成功！总耗时: {elapsed_time:.2f}ms (XML: {xml_time:.2f}ms)", file=sys.stderr)
            await self._cache_result(query, position_result)
            self._log_performance(query, 'position_analysis', elapsed_time, 1, xml_time)
            return position_result
        
        # 🎯 架构优化：检测弹窗/覆盖层场景
        # 如果XML元素很少（<50个），可能是弹窗/覆盖层，优先使用视觉识别
        is_popup_scenario = len(elements) < 50 and not candidates
        
        # Level 3.6: AI智能兜底（分析候选元素）
        # 前提：有候选元素（说明XML中有相关元素，只是不确定选哪个）
        if candidates:
            print(f"  📋 Level 3.6: AI智能兜底 (有{len(candidates)}个候选元素)...", file=sys.stderr)
            ai_result = await self._try_ai_candidates(query, candidates, elements)
            if ai_result:
                self.stats['ai_calls'] += 1
                elapsed_time = (time.time() - start_time) * 1000
                self.stats['total_time'] += elapsed_time
                print(f"  ✅ AI智能兜底成功！总耗时: {elapsed_time:.2f}ms (XML: {xml_time:.2f}ms)", file=sys.stderr)
                await self._cache_result(query, ai_result)
                self._log_performance(query, 'ai_smart_fallback', elapsed_time, 1, xml_time)
                return ai_result
        
        # 🎯 架构优化：弹窗场景优先使用视觉识别
        # 如果XML元素很少且没有候选，说明可能是弹窗/覆盖层，视觉识别更有效
        if is_popup_scenario:
            print(f"  🎯 检测到弹窗场景（XML元素少: {len(elements)}个），优先使用视觉识别...", file=sys.stderr)
            vision_result = await self._try_vision(query)
            if vision_result:
                self.stats['vision_calls'] += 1
                elapsed_time = (time.time() - start_time) * 1000
                self.stats['total_time'] += elapsed_time
                print(f"  ✅ 视觉识别成功！总耗时: {elapsed_time:.2f}ms", file=sys.stderr)
                await self._cache_result(query, vision_result)
                self._log_performance(query, 'vision', elapsed_time, 1, xml_time)
                return vision_result
        
        # Level 4: 文本AI分析（需要AI配置）
        # 场景：XML中有元素但无法匹配（需要AI理解语义）
        print(f"  ⚠️  XML分析失败，尝试AI分析...", file=sys.stderr)
        ai_result = await self._try_ai_analysis(query, elements)
        if ai_result:
            self.stats['ai_calls'] += 1
            elapsed_time = (time.time() - start_time) * 1000
            self.stats['total_time'] += elapsed_time
            print(f"  ✅ AI分析成功！总耗时: {elapsed_time:.2f}ms", file=sys.stderr)
            await self._cache_result(query, ai_result)
            self._log_performance(query, 'ai_analysis', elapsed_time, 1, xml_time)  # 传入已解析的elements，不重复读XML
            return ai_result
        
        # Level 5: 视觉识别（最后兜底，多模态）
        # 场景：所有方法都失败，视觉识别是最后手段
        vision_result = None
        if not is_popup_scenario:  # 如果之前已经尝试过视觉识别，不再重复
            print(f"  ⚠️  AI分析也失败，尝试视觉识别（最后兜底）...", file=sys.stderr)
            vision_result = await self._try_vision(query)
            if vision_result:
                self.stats['vision_calls'] += 1
                elapsed_time = (time.time() - start_time) * 1000
                self.stats['total_time'] += elapsed_time
                print(f"  ✅ 视觉识别成功！总耗时: {elapsed_time:.2f}ms", file=sys.stderr)
                await self._cache_result(query, vision_result)
                self._log_performance(query, 'vision', elapsed_time, 1, xml_time)
                return vision_result
        
        # 🎯 最后兜底：使用Cursor AI视觉识别（截图分析）
        # 类似@browser的行为：当所有定位方法都失败时，自动截图并请求Cursor AI分析
        # ⚠️ 如果查询包含位置信息（如"右上角"），且位置分析已失败，直接返回None，不等待Cursor AI
        position_keywords = ['右上角', '左上角', '右下角', '左下角', '顶部', '底部', '左侧', '右侧']
        has_position_keyword = any(kw in query for kw in position_keywords)
        
        if has_position_keyword:
            elapsed_time = (time.time() - start_time) * 1000
            print(f"  ❌ 所有定位方法都失败（包含位置关键词，不使用Cursor AI），总耗时: {elapsed_time:.2f}ms", file=sys.stderr)
            return None
        try:
            from .cursor_vision_helper import CursorVisionHelper
            cursor_helper = CursorVisionHelper(self.mobile_client)
            # 🎯 直接截图并创建请求文件，不等待（让Cursor AI主动分析）
            # 智能选择截图区域
            region = cursor_helper._smart_region_selection(query)
            screenshot_path = await cursor_helper.take_screenshot(query, region=region)
            
            # 创建请求文件
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            request_id = f"{timestamp}_{hash(query) % 10000}"
            request_file = cursor_helper.request_dir / f"request_{request_id}.json"
            
            request_data = {
                "request_id": request_id,
                "screenshot_path": screenshot_path,
                "element_desc": query,
                "region": region,
                "timestamp": timestamp,
                "status": "pending"
            }
            
            with open(request_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(request_data, f, ensure_ascii=False, indent=2)
            
            print(f"  📸 已截图并创建分析请求 (request_id: {request_id})", file=sys.stderr)
            
            # 🎯 返回特殊标记，让MCP服务器知道需要Cursor AI分析
            # 返回一个包含请求信息的字典，而不是None
            return {
                'element': query,
                'ref': f"cursor_vision_request_{request_id}",
                'confidence': 0,
                'method': 'cursor_vision_pending',
                'screenshot_path': screenshot_path,
                'request_id': request_id,
                'status': 'pending_analysis'
            }
        except Exception as e:
            print(f"  ⚠️  Cursor视觉识别失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        
        elapsed_time = (time.time() - start_time) * 1000
        print(f"  ❌ 所有定位方法都失败（包括Cursor视觉识别），总耗时: {elapsed_time:.2f}ms", file=sys.stderr)
        return None
    
    async def _try_cache(self, query: str) -> Optional[Dict]:
        """尝试从缓存获取"""
        cache_key = self._get_cache_key(query)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached['timestamp'] < self._cache_ttl:
                return cached['result']
            else:
                # 缓存过期
                del self._cache[cache_key]
        return None
    
    async def _try_quick_match(self, elements: list, query: str) -> Optional[Dict]:
        """
        快速预匹配（针对容易歧义的查询）
        
        场景：
        1. "输入邮箱" - 包含"输入"但实际是页签，不是输入操作
        2. "输入XXX"但不是"输入框" - 可能是页签/按钮，不是输入操作
        3. "登陆" → "登录" - 同义词替换
        4. "点击XX按钮" → "XX" - 去除无意义词
        5. resource-id直接匹配
        
        策略：
        - 完全匹配优先（准确性第一）
        - 去除无意义词再匹配
        - 同义词自动替换
        """
        import time
        start_time = time.time()
        
        query_lower = query.lower().strip()
        
        # ⚡ 优化1: 同义词替换
        if "登陆" in query_lower:
            query_lower = query_lower.replace("登陆", "登录")
            print(f"  ⚡ 同义词替换: '登陆' → '登录'", file=sys.stderr)
        
        # ⚡ 优化2: resource-id快速匹配（如果query包含:id/或com.开头）
        if ":id/" in query or query.startswith("com."):
            print(f"  ⚡ 检测到resource-id格式，直接匹配", file=sys.stderr)
            for elem in elements:
                if elem.get('resource_id') == query:
                    print(f"     ✅ resource-id完全匹配: {query}", file=sys.stderr)
                    return {
                        'element': query,
                        'ref': query,
                        'confidence': 100,
                        'method': 'quick_match_resource_id'
                    }
        
        # ⚡ 优化3: 去除无意义词，提取关键词
        query_clean = query_lower
        removed_words = []
        if "点击" in query_clean:
            query_clean = query_clean.replace("点击", "").strip()
            removed_words.append("点击")
        if "按钮" in query_clean and "输入框" not in query_clean:
            query_clean = query_clean.replace("按钮", "").strip()
            removed_words.append("按钮")
        
        if removed_words:
            print(f"  ⚡ 去除无意义词: {', '.join(removed_words)} → '{query_clean}'", file=sys.stderr)
        
        # 判断是否可能被误判为输入操作
        has_input_keyword = "输入" in query_lower
        is_not_input_box = "输入框" not in query_lower
        
        # 如果包含"输入"但不是"输入框"，可能是页签/按钮（如"输入邮箱"页签）
        # 或者去除了无意义词后，都应该在clickable元素中优先查找
        if (has_input_keyword and is_not_input_box) or removed_words:
            if has_input_keyword and is_not_input_box:
                print(f"  ⚡ 快速预匹配: 检测到'输入'但不是'输入框'，先查找clickable元素", file=sys.stderr)
            
            # 在clickable元素中查找
            filter_start = time.time()
            clickable_elements = [e for e in elements if e.get('clickable', False)]
            filter_time = (time.time() - filter_start) * 1000
            print(f"     ⏱️  预过滤: {filter_time:.2f}ms (从{len(elements)}个筛选到{len(clickable_elements)}个clickable)", file=sys.stderr)
            
            # ⚡ 优化4: 完全匹配优先（最重要！）
            match_start = time.time()
            for elem in clickable_elements:
                text = elem.get('text', '').lower()
                content_desc = elem.get('content_desc', '').lower()
                # 清理content_desc（去除换行符和额外文本）
                content_desc_clean = content_desc.split('\n')[0].strip() if content_desc else ''
                content_desc_clean_lower = content_desc_clean.lower()
                
                # 完全匹配优先（使用清理后的query）
                if query_clean == content_desc_clean_lower or query_clean == text:
                    # 找到完全匹配！
                    match_time = (time.time() - match_start) * 1000
                    ref = elem.get('resource_id') or content_desc_clean or text
                    element_desc = content_desc_clean or text or query
                    
                    total_time = (time.time() - start_time) * 1000
                    print(f"     ✅ 完全匹配(清理后): {element_desc}", file=sys.stderr)
                    print(f"     ⏱️  匹配耗时: {match_time:.2f}ms | 快速预匹配总耗时: {total_time:.2f}ms", file=sys.stderr)
                    
                    return {
                        'element': element_desc,
                        'ref': ref,
                        'confidence': 95,
                        'method': 'quick_match'
                    }
                
                # 原始query也试试完全匹配
                if query_lower == content_desc_clean_lower or query_lower == text:
                    match_time = (time.time() - match_start) * 1000
                    ref = elem.get('resource_id') or content_desc_clean or text
                    element_desc = content_desc_clean or text or query
                    
                    total_time = (time.time() - start_time) * 1000
                    print(f"     ✅ 完全匹配(原始): {element_desc}", file=sys.stderr)
                    print(f"     ⏱️  匹配耗时: {match_time:.2f}ms | 快速预匹配总耗时: {total_time:.2f}ms", file=sys.stderr)
                    
                    return {
                        'element': element_desc,
                        'ref': ref,
                        'confidence': 95,
                        'method': 'quick_match'
                    }
            
            # 完全匹配失败，再尝试包含匹配（降级）
            match_time = (time.time() - match_start) * 1000
            print(f"     ⏱️  完全匹配遍历: {match_time:.2f}ms (未找到)", file=sys.stderr)
            
            contain_start = time.time()
            for elem in clickable_elements:
                text = elem.get('text', '').lower()
                content_desc = elem.get('content_desc', '').lower()
                content_desc_clean = content_desc.split('\n')[0].strip() if content_desc else ''
                content_desc_clean_lower = content_desc_clean.lower()
                
                # 包含匹配（使用清理后的query）
                if query_clean in content_desc_clean_lower or query_clean in text:
                    contain_time = (time.time() - contain_start) * 1000
                    ref = elem.get('resource_id') or content_desc_clean or text
                    element_desc = content_desc_clean or text or query
                    
                    total_time = (time.time() - start_time) * 1000
                    print(f"     ✅ 包含匹配: {element_desc}", file=sys.stderr)
                    print(f"     ⏱️  包含匹配耗时: {contain_time:.2f}ms | 快速预匹配总耗时: {total_time:.2f}ms", file=sys.stderr)
                    
                    return {
                        'element': element_desc,
                        'ref': ref,
                        'confidence': 85,
                        'method': 'quick_match'
                    }
        
        total_time = (time.time() - start_time) * 1000
        if total_time > 5:  # 只有超过5ms才打印
            print(f"     ⏱️  快速预匹配: {total_time:.2f}ms (未匹配)", file=sys.stderr)
        return None
    
    async def _try_rule_match(self, elements: list, query: str) -> Optional[Dict]:
        """
        尝试规则匹配（复用SmartLocator）
        
        Args:
            elements: 已解析的元素列表（用于转换结果时复用）
            query: 查询文本
        """
        if not self.smart_locator:
            return None
        
        # ⚡ 同义词替换（规则匹配阶段）
        query_processed = query
        if "登陆" in query:
            query_processed = query.replace("登陆", "登录")
            print(f"  ⚡ 同义词替换（规则匹配）: '登陆' → '登录'", file=sys.stderr)
        
        # 定义AI函数（用于降级，但这里先不调用）
        async def ai_func(client, q: str):
            return None  # 规则匹配阶段不调用AI
        
        # 调用SmartLocator，跳过AI
        result = await self.smart_locator.locate(query_processed, ai_func=ai_func, skip_ai=True)
        
        if result:
            # 转换结果为移动端格式（传入elements避免重复读取XML）
            return self._convert_result(result, query, elements)
        
        return None
    
    async def _try_xml_analysis(self, elements: list, query: str):
        """
        XML深度分析
        
        Args:
            elements: 已解析的元素列表（复用，避免重复读取XML）
            query: 查询文本
            
        Returns:
            (result, candidates): result为定位结果，candidates为候选元素列表（用于AI兜底）
        """
        import time
        start_time = time.time()
        
        print(f"  📋 Level 3: XML深度分析...", file=sys.stderr)
        
        # 🎯 优化：只在调试模式下打印XML结构预览
        # 通过环境变量 MOBILE_MCP_DEBUG=1 开启
        import os
        debug_mode = os.getenv('MOBILE_MCP_DEBUG', '0') == '1'
        
        if debug_mode:
            # 打印XML结构（调试用）
            print(f"  📄 XML结构预览（共{len(elements)}个元素）:", file=sys.stderr)
            print(f"  {'─' * 60}", file=sys.stderr)
            
            # 只打印前20个有意义的元素（避免输出过多）
            meaningful_elements = [
                e for e in elements 
                if e.get('text') or e.get('content_desc') or e.get('resource_id') or e.get('clickable')
            ][:20]
            
            for i, elem in enumerate(meaningful_elements, 1):
                text = elem.get('text', '')
                desc = elem.get('content_desc', '')
                resource_id = elem.get('resource_id', '')
                class_name = elem.get('class_name', '')
                clickable = elem.get('clickable', False)
                focusable = elem.get('focusable', False)
                
                # 格式化输出
                parts = []
                if text:
                    parts.append(f"text='{text[:30]}'")
                if desc:
                    desc_clean = desc.split('\n')[0][:30]
                    parts.append(f"desc='{desc_clean}'")
                if resource_id:
                    parts.append(f"id='{resource_id[:30]}'")
                if class_name:
                    parts.append(f"class={class_name}")
                if clickable:
                    parts.append("[clickable]")
                if focusable:
                    parts.append("[focusable]")
                
                print(f"  {i:2d}. {' | '.join(parts) if parts else 'empty element'}", file=sys.stderr)
            
            if len(meaningful_elements) < len([e for e in elements if e.get('text') or e.get('content_desc')]):
                print(f"  ... (还有更多元素，共{len(elements)}个)", file=sys.stderr)
            print(f"  {'─' * 60}", file=sys.stderr)
        
        # 文本匹配
        query_lower = query.lower().strip()
        
        # ⚡ 同义词处理：登陆 -> 登录
        if "登陆" in query_lower:
            query_lower = query_lower.replace("登陆", "登录")
            print(f"  ⚡ 同义词替换: '登陆' → '登录'", file=sys.stderr)
        
        matched = []
        
        # 提取关键词（去除"输入框"、"按钮"等后缀）
        query_keywords = query_lower
        if "输入框" in query:
            query_keywords = query_lower.replace("输入框", "").strip()
        elif "按钮" in query:
            query_keywords = query_lower.replace("按钮", "").strip()
        elif "页签" in query or "标签" in query:
            query_keywords = query_lower.replace("页签", "").replace("标签", "").strip()
        elif "图标" in query:
            query_keywords = query_lower.replace("图标", "").strip()
        
        # 判断查询类型：输入框 vs 页签/按钮 vs 图标
        is_input_query = "输入框" in query or "输入" in query
        is_tab_query = "页签" in query or "标签" in query or ("点击" in query and "输入" not in query)
        is_icon_query = "图标" in query or ("搜索" in query and "图标" in query) or ("右上角" in query and "图标" in query)
        
        # 🚀 性能优化策略（准确性优先 + 速度优化）
        
        # 步骤1: 根据查询类型预过滤元素（大幅减少遍历范围，提速50%+）
        filter_start = time.time()
        candidate_elements = []
        
        if is_input_query and "输入框" in query:
            # 查询输入框：只看EditText类型（准确性优先）
            candidate_elements = [e for e in elements if e.get('class_name', '').lower() in ['edittext', 'textfield']]
            filter_time = (time.time() - filter_start) * 1000
            if len(candidate_elements) < len(elements):
                print(f"  🎯 输入框查询优化: 从{len(elements)}个元素缩减到{len(candidate_elements)}个EditText (⏱️ {filter_time:.2f}ms)", file=sys.stderr)
            
            # 特殊处理：如果查询输入框，直接匹配所有EditText（包括空的）
            # 这样可以匹配到空输入框，后续通过评分选择最佳
            match_start = time.time()  # 定义match_start
            matched = candidate_elements
            match_time = (time.time() - match_start) * 1000
            print(f"  ✅ 找到 {len(matched)} 个EditText元素（包括空输入框） (⏱️ {match_time:.2f}ms)", file=sys.stderr)
            
        elif is_icon_query:
            # 🎯 图标查询优化：优先从顶部区域筛选
            # 1. 先筛选可点击的图标元素（Image/ImageView类型，或者无文本的可点击元素）
            icon_elements = []
            for e in elements:
                if not e.get('clickable', False):
                    continue
                
                class_name = e.get('class_name', '').lower()
                text = e.get('text', '')
                content_desc = e.get('content_desc', '')
                
                # 图标特征：Image类型，或者无文本的可点击元素（可能是图标）
                is_image_type = ('image' in class_name or class_name in ['imageview', 'imagebutton'])
                is_icon_like = not text and not content_desc  # 无文本描述，可能是图标
                
                if is_image_type or is_icon_like:
                    icon_elements.append(e)
            
            # 2. 如果查询包含"右上角"、"顶部"等位置描述，优先筛选顶部区域元素
            if "右上角" in query or "顶部" in query or "上角" in query:
                # 解析bounds，筛选Y坐标较小的元素（顶部区域）
                screen_height = 2400  # 默认屏幕高度，可以从设备获取
                top_threshold = screen_height * 0.3  # 顶部30%区域
                
                top_icon_elements = []
                for elem in icon_elements:
                    bounds = elem.get('bounds', '')
                    import re
                    match = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                    if match:
                        y1 = int(match.group(2))
                        if y1 < top_threshold:
                            top_icon_elements.append(elem)
                
                if top_icon_elements:
                    candidate_elements = top_icon_elements
                else:
                    candidate_elements = icon_elements
            else:
                candidate_elements = icon_elements
            
            filter_time = (time.time() - filter_start) * 1000
            if "右上角" in query or "顶部" in query or "上角" in query:
                print(f"  🎯 图标查询优化（顶部区域）: 从{len(elements)}个元素缩减到{len(candidate_elements)}个顶部图标元素 (⏱️ {filter_time:.2f}ms)", file=sys.stderr)
            else:
                print(f"  🎯 图标查询优化: 从{len(elements)}个元素缩减到{len(candidate_elements)}个图标元素 (⏱️ {filter_time:.2f}ms)", file=sys.stderr)
            
            # 步骤2: 遍历候选元素进行文本匹配
            match_start = time.time()
            matched = []
            for element in candidate_elements:
                text = element.get('text', '').lower()
                content_desc = element.get('content_desc', '').lower()
                content_desc_clean = content_desc.split('\n')[0].strip() if content_desc else ''
                content_desc_clean_lower = content_desc_clean.lower()
                bounds = element.get('bounds', '')
                
                # 图标匹配：优先匹配description，也匹配text
                text_matched = (query_lower == content_desc_clean_lower or  # 完全匹配desc
                               query_lower == text or  # 完全匹配text
                               query_lower in content_desc_clean_lower or  # 包含匹配desc
                               query_lower in text or  # 包含匹配text
                               query_keywords in content_desc_clean_lower or  # 关键词匹配desc
                               query_keywords in text)  # 关键词匹配text
                
                # 🎯 特殊处理：如果图标没有文本描述，根据位置匹配
                if not text_matched and not text and not content_desc:
                    # 无文本图标，根据位置描述匹配
                    import re
                    match = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                    if match:
                        x1, y1, x2, y2 = map(int, match.groups())
                        center_x = (x1 + x2) // 2
                        center_y = (y1 + y2) // 2
                        screen_width = 1080
                        screen_height = 2400
                        
                        # 右上角判断：X坐标在右侧70%以上，Y坐标在顶部30%以内
                        is_top_right = center_x > screen_width * 0.7 and center_y < screen_height * 0.3
                        # 顶部判断：Y坐标在顶部30%以内
                        is_top = center_y < screen_height * 0.3
                        # 右侧判断：X坐标在右侧70%以上
                        is_right = center_x > screen_width * 0.7
                        
                        # 根据查询中的位置关键词匹配
                        if ("右上角" in query or "上角" in query) and is_top_right:
                            matched.append(element)
                            print(f"  ✅ 位置匹配（右上角）: bounds={bounds}, center=({center_x}, {center_y})", file=sys.stderr)
                        elif "顶部" in query and is_top:
                            matched.append(element)
                            print(f"  ✅ 位置匹配（顶部）: bounds={bounds}, center=({center_x}, {center_y})", file=sys.stderr)
                        elif "右侧" in query or "右边" in query and is_right:
                            matched.append(element)
                            print(f"  ✅ 位置匹配（右侧）: bounds={bounds}, center=({center_x}, {center_y})", file=sys.stderr)
                
                if text_matched:
                    matched.append(element)
            
        elif is_tab_query or ("点击" in query and "输入框" not in query):
            # 查询页签/按钮：只看可点击元素
            clickable_elements = [e for e in elements if e.get('clickable', False)]
            filter_time = (time.time() - filter_start) * 1000
            if len(clickable_elements) < len(elements):
                candidate_elements = clickable_elements
                print(f"  🎯 点击查询优化: 从{len(elements)}个元素缩减到{len(candidate_elements)}个可点击元素 (⏱️ {filter_time:.2f}ms)", file=sys.stderr)
            else:
                candidate_elements = elements
                print(f"  ⏱️  预过滤: {filter_time:.2f}ms (无缩减)", file=sys.stderr)
            
            # 步骤2: 遍历候选元素进行文本匹配
            match_start = time.time()
            matched = []
            for element in candidate_elements:
                text = element.get('text', '').lower()
                content_desc = element.get('content_desc', '').lower()
                content_desc_clean = content_desc.split('\n')[0].strip() if content_desc else ''
                content_desc_clean_lower = content_desc_clean.lower()
                
                # 匹配条件（简化判断提高速度）
                if (query_lower == content_desc_clean_lower or  # 完全匹配desc
                    query_lower == text or  # 完全匹配text
                    query_lower in content_desc_clean_lower or  # 包含匹配desc
                    query_lower in text or  # 包含匹配text
                    query_keywords in content_desc_clean_lower or  # 关键词匹配desc
                    query_keywords in text):  # 关键词匹配text
                    matched.append(element)
        else:
            # 其他查询：使用全部元素进行文本匹配
            candidate_elements = elements
            match_start = time.time()  # 定义match_start
            matched = []
            for element in candidate_elements:
                text = element.get('text', '').lower()
                content_desc = element.get('content_desc', '').lower()
                class_name = element.get('class_name', '').lower()
                
                # 跳过无意义的容器元素
                if class_name in ['framelayout', 'linearlayout', 'relativelayout'] and not text and not content_desc:
                    continue
                
                content_desc_clean = content_desc.split('\n')[0].strip() if content_desc else ''
                content_desc_clean_lower = content_desc_clean.lower()
                
                # 匹配条件
                if (query_lower == content_desc_clean_lower or
                    query_lower == text or
                    query_lower in content_desc_clean_lower or
                    query_lower in text or
                    query_keywords in content_desc_clean_lower or
                    query_keywords in text):
                    matched.append(element)
        
        if matched:
            match_time = (time.time() - match_start) * 1000
            print(f"  ✅ 找到 {len(matched)} 个匹配元素 (⏱️ 文本匹配: {match_time:.2f}ms)", file=sys.stderr)
            print(f"  {'─' * 60}", file=sys.stderr)
            
            # 显示所有匹配元素（不限制数量，让用户看到完整情况）
            for i, elem in enumerate(matched, 1):
                text = elem.get('text', '')
                desc = elem.get('content_desc', '')
                resource_id = elem.get('resource_id', '')
                class_name = elem.get('class_name', '')
                clickable = elem.get('clickable', False)
                focusable = elem.get('focusable', False)
                bounds = elem.get('bounds', '')
                
                # 计算匹配分数（用于显示）
                score = 0
                content_desc_clean_lower = desc.split('\n')[0].strip().lower() if desc else ''
                text_lower = text.lower()
                
                if query_lower == content_desc_clean_lower:
                    score += 100
                elif query_lower in content_desc_clean_lower:
                    score += 50
                elif query_keywords in content_desc_clean_lower:
                    score += 48
                
                if query_lower == text_lower:
                    score += 80
                elif query_lower in text_lower:
                    score += 40
                
                if clickable:
                    score += 20
                if focusable:
                    score += 5
                if resource_id:
                    score += 5
                
                # 格式化显示
                parts = []
                if text:
                    parts.append(f"text='{text}'")
                if desc:
                    desc_clean = desc.split('\n')[0]
                    parts.append(f"desc='{desc_clean}'")
                if resource_id:
                    parts.append(f"id='{resource_id}'")
                if class_name:
                    parts.append(f"class={class_name}")
                if clickable:
                    parts.append("[clickable]")
                if focusable:
                    parts.append("[focusable]")
                if bounds:
                    parts.append(f"bounds={bounds}")
                
                # 计算最终分数（在评分循环中会重新计算，这里只是显示）
                print(f"    [{i:3d}] 分数={score:3d} | {' | '.join(parts) if parts else 'empty element'}", file=sys.stderr)
            
            print(f"  {'─' * 60}", file=sys.stderr)
            
            # 🎯 Phase 1优化：位置索引定位（仅针对输入框查询）
            # 如果是输入框查询，且所有匹配的元素都是EditText且没有任何标识
            # 则使用位置索引（关键词）来区分
            if is_input_query and "输入框" in query and matched:
                # 检查是否所有匹配元素都是EditText且没有text/content_desc/resource_id
                all_empty_edittext = all(
                    e.get('class_name', '').lower() in ['edittext', 'textfield'] and
                    not e.get('text') and
                    not e.get('content_desc') and
                    not e.get('resource_id')
                    for e in matched
                )
                
                if all_empty_edittext and len(matched) > 1:
                    # 所有输入框都没有标识，使用位置索引
                    print(f"  🎯 检测到{len(matched)}个无标识EditText，使用位置索引定位", file=sys.stderr)
                    
                    # 按Y坐标排序
                    import re
                    def get_y_coord(elem):
                        bounds = elem.get('bounds', '')
                        match = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                        return int(match.group(2)) if match else 9999
                    
                    sorted_edittexts = sorted(matched, key=get_y_coord)
                    
                    # 根据关键词选择
                    target_elem = None
                    # 🎯 支持"第一个"、"第二个"、"第三个"等描述
                    if any(kw in query for kw in ['第一个', '第1个', '1个', '首个']):
                        target_elem = sorted_edittexts[0] if len(sorted_edittexts) > 0 else None
                        if target_elem:
                            print(f"     → 关键词'第一个' → 第1个EditText (Y={get_y_coord(target_elem)})", file=sys.stderr)
                    elif any(kw in query for kw in ['第二个', '第2个', '2个']):
                        target_elem = sorted_edittexts[1] if len(sorted_edittexts) > 1 else None
                        if target_elem:
                            print(f"     → 关键词'第二个' → 第2个EditText (Y={get_y_coord(target_elem)})", file=sys.stderr)
                    elif any(kw in query for kw in ['第三个', '第3个', '3个']):
                        target_elem = sorted_edittexts[2] if len(sorted_edittexts) > 2 else None
                        if target_elem:
                            print(f"     → 关键词'第三个' → 第3个EditText (Y={get_y_coord(target_elem)})", file=sys.stderr)
                    # 原有的关键词匹配
                    elif any(kw in query for kw in ['邮箱', '账号', '用户名', '手机号', '电话']):
                        target_elem = sorted_edittexts[0]
                        print(f"     → 关键词'邮箱/账号' → 第1个EditText (Y={get_y_coord(target_elem)})", file=sys.stderr)
                    elif '验证码' in query:
                        target_elem = sorted_edittexts[1] if len(sorted_edittexts) > 1 else sorted_edittexts[0]
                        print(f"     → 关键词'验证码' → 第2个EditText (Y={get_y_coord(target_elem)})", file=sys.stderr)
                    elif '密码' in query:
                        target_elem = sorted_edittexts[1] if len(sorted_edittexts) > 1 else sorted_edittexts[0]
                        print(f"     → 关键词'密码' → 第2个EditText (Y={get_y_coord(target_elem)})", file=sys.stderr)
                    
                    if target_elem:
                        # 直接返回，使用bounds或class_name[index]作为ref
                        ref = target_elem.get('bounds', '')
                        if not ref:
                            index = sorted_edittexts.index(target_elem)
                            ref = f"EditText[{index}]"
                        
                        print(f"  🎯 位置索引定位成功:", file=sys.stderr)
                        print(f"     元素: {query}", file=sys.stderr)
                        print(f"     ref: '{ref}'", file=sys.stderr)
                        print(f"     置信度: 90%", file=sys.stderr)
                        
                        result = {
                            'element': query,
                            'ref': ref,
                            'confidence': 90,
                            'method': 'position_index'
                        }
                        return (result, [])  # 成功找到，不需要AI兜底
            
            # 🔍 检测超大容器元素（H5页面的容器）
            # 如果是超大容器，使用bounds坐标点击（点击容器底部中心，提交按钮通常在那里）
            filtered_matched = []
            large_container = None
            
            for elem in matched:
                bounds = elem.get('bounds', '')
                if bounds:
                    import re
                    match = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                    if match:
                        x1, y1, x2, y2 = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
                        width = x2 - x1
                        height = y2 - y1
                        # 如果宽度超过屏幕宽度的90%，很可能是H5容器元素
                        if width > 1080 * 0.9:  # 假设屏幕宽度1080
                            print(f"  ⚠️  检测到超大H5容器: width={width}, height={height}", file=sys.stderr)
                            print(f"      bounds={bounds}", file=sys.stderr)
                            # 保存这个容器，如果没有其他元素，就点击容器底部中心
                            large_container = elem
                            continue
                filtered_matched.append(elem)
            
            # 如果过滤后没有元素了，使用超大容器的bounds坐标点击
            if not filtered_matched and large_container:
                print(f"  🎯 使用H5容器bounds坐标定位（点击底部中心）", file=sys.stderr)
                bounds = large_container.get('bounds', '')
                match = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                if match:
                    x1, y1, x2, y2 = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
                    # 计算底部中心点（Y坐标在容器的95%位置，提交按钮通常在最底部）
                    center_x = (x1 + x2) // 2
                    bottom_y = int(y1 + (y2 - y1) * 0.95)  # 95%位置（接近底部）
                    
                    # 构造一个新的bounds，指向底部中心区域
                    # 创建一个小的点击区域（50x50像素）
                    click_bounds = f"[{center_x-25},{bottom_y-25}][{center_x+25},{bottom_y+25}]"
                    
                    print(f"      点击位置: ({center_x}, {bottom_y})", file=sys.stderr)
                    print(f"      点击bounds: {click_bounds}", file=sys.stderr)
                    
                    # 直接返回结果，使用bounds作为ref
                    result = {
                        'element': query,
                        'ref': click_bounds,  # 使用计算后的点击区域
                        'confidence': 85,
                        'method': 'h5_container_bounds'
                    }
                    return (result, [])
            
            # 如果过滤后没有元素也没有容器，使用原始列表
            if not filtered_matched:
                print(f"  ⚠️  过滤后无元素，使用原始列表", file=sys.stderr)
                filtered_matched = matched
            elif len(filtered_matched) < len(matched):
                print(f"  ✅ 过滤后剩余 {len(filtered_matched)} 个元素（原{len(matched)}个）", file=sys.stderr)
            
            # 为每个匹配元素计算详细分数
            score_start = time.time()
            scored_elements = []
            
            for element in filtered_matched:
                score = 0
                score_details = []  # 记录加分详情（用于调试）
                content_desc = element.get('content_desc', '')
                content_desc_lower = content_desc.lower()
                # 清理content_desc（去除换行符和额外文本）
                content_desc_clean = content_desc.split('\n')[0].strip() if content_desc else ''
                content_desc_clean_lower = content_desc_clean.lower()
                text = element.get('text', '').lower()
                class_name = element.get('class_name', '').lower()
                
                # 元素类型判断
                is_textbox = class_name in ['edittext', 'textfield']
                is_button = element.get('clickable', False) and not is_textbox
                is_tab = element.get('clickable', False) and ('标签' in content_desc or '标签' in text)
                
                # ===== 类型匹配加分（最重要） =====
                # 如果查询包含"输入框"，EditText类型应该获得大幅加分
                # 注意：只有当查询明确包含"输入框"时才加分，避免"输入邮箱"页签被误判
                if is_input_query and "输入框" in query and is_textbox:
                    score += 200  # 输入框查询匹配到EditText，大幅加分
                    score_details.append("类型匹配EditText+200")
                    
                    # 额外加分：优先匹配空的输入框（没有text或text是占位符的）
                    # 检查text是否为空或只是占位符（如"请输入"、"•••"等）
                    is_empty_or_placeholder = (
                        not text or 
                        text.strip() == '' or
                        text.strip() == '•••••••••••••••' or  # 密码占位符
                        '请输入' in text or
                        '请填写' in text
                    )
                    
                    if is_empty_or_placeholder:
                        score += 100  # 空输入框大幅优先
                        score_details.append("空输入框+100")
                    else:
                        score -= 50  # 已有文本的输入框大幅降分（避免匹配到已填写的输入框）
                        score_details.append(f"已有文本({text})-50")
                
                # 如果查询包含"按钮"，可点击的按钮应该获得加分
                if "按钮" in query and is_button:
                    score += 150  # 按钮查询匹配到按钮元素
                    score_details.append("类型匹配Button+150")
                
                # 如果查询包含"页签"或"标签"，页签元素应该获得加分
                if is_tab_query and is_tab:
                    score += 150  # 页签查询匹配到页签元素
                    score_details.append("类型匹配Tab+150")
                
                # ===== 文本匹配评分 =====
                # 优先匹配清理后的content_desc（完全匹配优先）
                if query_lower == content_desc_clean_lower:
                    score += 150  # 完全匹配清理后的description（大幅加分）
                    score_details.append("完全匹配desc+150")
                elif query_lower == content_desc_lower:
                    score += 140  # 完全匹配原始description（可能包含换行）
                    score_details.append("完全匹配原始desc+140")
                elif query_lower in content_desc_clean_lower:
                    # 如果元素描述比查询长（如"游戏登录"包含"登录"），大幅降分
                    if len(content_desc_clean_lower) > len(query_lower):
                        score += 5  # 包含匹配但描述更长，大幅降分（避免匹配到"游戏登录"）
                        score_details.append(f"包含匹配desc但更长({content_desc_clean_lower}包含{query_lower})+5")
                    else:
                        score += 30  # 包含匹配清理后的description（降分，避免部分匹配）
                        score_details.append("包含匹配desc+30")
                elif query_lower in content_desc_lower:
                    # 如果元素描述比查询长，大幅降分
                    if len(content_desc_lower) > len(query_lower):
                        score += 3  # 包含匹配但描述更长，大幅降分
                        score_details.append(f"包含匹配原始desc但更长({content_desc_lower}包含{query_lower})+3")
                    else:
                        score += 25  # 包含匹配原始description（降分）
                        score_details.append("包含匹配原始desc+25")
                
                # 完全匹配text优先于部分匹配（重要）
                if query_lower == text:
                    score += 80  # 完全匹配text
                    score_details.append("完全匹配text+80")
                elif query_lower in text:
                    # 如果元素文本比查询长（如"游戏登录"包含"登录"），大幅降分
                    if len(text) > len(query_lower):
                        score += 5  # 包含匹配但文本更长，大幅降分（避免匹配到"游戏登录"）
                        score_details.append(f"包含匹配text但更长({text}包含{query_lower})+5")
                    else:
                        score += 20  # 包含匹配text（降分，避免部分匹配）
                        score_details.append("包含匹配text+20")
                elif text and query_lower in text:  # 反向匹配（text包含查询）
                    score -= 30  # 如果text包含查询但不是完全匹配，大幅降分（避免匹配到已有文本）
                    score_details.append("反向匹配text-30")
                
                # 关键词匹配
                if query_keywords == content_desc_clean_lower:
                    score += 95
                    score_details.append("关键词完全匹配+95")
                elif query_keywords in content_desc_clean_lower:
                    score += 48
                    score_details.append("关键词包含匹配+48")
                
                # 文本匹配已在上面处理，这里不需要重复
                
                # ===== 元素属性加分 =====
                # 优先选择可交互的元素
                if element.get('clickable'):
                    score += 20  # 可点击元素
                    score_details.append("clickable+20")
                if element.get('focusable'):
                    score += 10  # 可聚焦元素（输入框通常是focusable）
                    score_details.append("focusable+10")
                
                # 优先选择有resource-id的元素
                if element.get('resource_id'):
                    score += 5
                    score_details.append("resource-id+5")
                
                # 页签特征：可点击+有文本/描述
                if is_tab and (text or content_desc):
                    score += 15
                    score_details.append("Tab特征+15")
                
                # ===== 位置加分（输入框通常在页面上方，按顺序） =====
                if is_input_query and is_textbox:
                    bounds = element.get('bounds', '')
                    if bounds:
                        # 解析bounds，Y坐标小的在上方
                        import re
                        match = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                        if match:
                            y1 = int(match.group(2))
                            # Y坐标越小（越靠上），分数越高（最多+50分）
                            # 假设屏幕高度2356，Y坐标在200-800之间是输入框常见位置
                            if 200 <= y1 <= 800:
                                # 对于"邮箱输入框"，优先Y坐标更小的（第一个）
                                # 对于"密码输入框"，优先Y坐标稍大的（第二个）
                                if "邮箱" in query:
                                    # 邮箱输入框应该在第一个（Y坐标更小）
                                    position_bonus = max(0, 50 - (y1 - 200) // 10)
                                    score += position_bonus
                                    score_details.append(f"位置Y={y1}(邮箱优先)+{position_bonus}")
                                elif "密码" in query:
                                    # 密码输入框应该在第二个（Y坐标稍大）
                                    # 如果Y坐标在400-700之间，给予加分
                                    if 400 <= y1 <= 700:
                                        position_bonus = max(0, 50 - abs(y1 - 550) // 10)
                                        score += position_bonus
                                        score_details.append(f"位置Y={y1}(密码优先)+{position_bonus}")
                                    else:
                                        score -= 20  # 位置不对，降分
                                        score_details.append(f"位置Y={y1}(密码位置不对)-20")
                                else:
                                    # 其他输入框，Y坐标越小越好
                                    position_bonus = max(0, 30 - (y1 - 200) // 20)
                                    score += position_bonus
                                    score_details.append(f"位置Y={y1}+{position_bonus}")
                
                # 保存分数和详情
                scored_elements.append((element, score, score_details))
            
            # 按分数排序，选择最佳匹配
            scored_elements.sort(key=lambda x: x[1], reverse=True)
            score_time = (time.time() - score_start) * 1000
            
            # 显示前5个的详细评分
            print(f"  📊 评分详情（前5个） (⏱️ 评分: {score_time:.2f}ms):", file=sys.stderr)
            for i, (elem, score, details) in enumerate(scored_elements[:5], 1):
                text = elem.get('text', '')
                desc = elem.get('content_desc', '')
                class_name = elem.get('class_name', '')
                desc_clean = desc.split('\n')[0] if desc else ''
                print(f"    [{i}] 分数={score:3d}: {desc_clean or text or class_name}", file=sys.stderr)
                if details:
                    print(f"        详情: {' | '.join(details[:3])}", file=sys.stderr)  # 只显示前3个加分项
            
            # 选择最佳匹配
            best = scored_elements[0][0] if scored_elements else None
            best_score = scored_elements[0][1] if scored_elements else 0
                
                # 已经在上面排序了，这里不需要再比较
            
            if best:
                # 确定ref（优先resource-id，其次content_desc，最后text）
                ref = best.get('resource_id')
                if not ref:
                    # 如果description匹配，使用清理后的description定位（去除换行符）
                    content_desc = best.get('content_desc', '')
                    if content_desc:
                        # 清理content_desc（去除换行符和额外文本）
                        content_desc_clean = content_desc.split('\n')[0].strip()
                        content_desc_lower = content_desc.lower()
                        content_desc_clean_lower = content_desc_clean.lower()
                        
                        # 如果查询匹配清理后的description，使用清理后的值
                        if query_lower in content_desc_clean_lower or query_keywords in content_desc_clean_lower:
                            ref = content_desc_clean  # 使用清理后的description
                        elif query_lower in content_desc_lower:
                            ref = content_desc_clean  # 即使匹配原始，也使用清理后的
                        else:
                            ref = content_desc_clean  # 默认使用清理后的
                    elif best.get('text'):
                        # 使用text定位（页签通常用text）
                        ref = best.get('text', '')
                    else:
                        ref = best.get('content_desc', '')
                
                # 确保ref不为空
                if not ref:
                    # 如果还是没有ref，尝试使用bounds或class_name+索引
                    bounds = best.get('bounds', '')
                    class_name = best.get('class_name', '')
                    
                    if bounds:
                        # 使用bounds作为ref（格式：[x1,y1][x2,y2]）
                        ref = bounds
                        print(f"  ⚠️  使用bounds作为ref: {bounds}", file=sys.stderr)
                    elif class_name:
                        # 使用class_name+索引（作为最后手段）
                        # 查找同类元素的索引
                        same_class_elements = [e for e in elements if e.get('class_name') == class_name]
                        index = same_class_elements.index(best) if best in same_class_elements else 0
                        ref = f"{class_name}[{index}]"
                        print(f"  ⚠️  使用class_name+索引作为ref: {ref}", file=sys.stderr)
                    else:
                        print(f"  ⚠️  找到匹配元素但无法确定ref: {best}", file=sys.stderr)
                        # 无法确定ref但有匹配元素，返回候选元素供AI分析
                        candidates = matched[:5] if matched else []
                        return (None, candidates)
                
                # 返回清理后的element描述
                element_desc = best.get('content_desc', '') or best.get('text', '')
                if element_desc and '\n' in element_desc:
                    element_desc = element_desc.split('\n')[0].strip()
                
                # 如果没有描述，使用查询文本或class_name
                if not element_desc:
                    if query:
                        # 使用查询文本作为描述
                        element_desc = query
                    else:
                        element_desc = best.get('class_name', 'element')
                
                total_time = (time.time() - start_time) * 1000
                print(f"  🎯 选择最佳匹配:", file=sys.stderr)
                print(f"     元素: {element_desc}", file=sys.stderr)
                print(f"     ref: '{ref}'", file=sys.stderr)
                print(f"     评分: {best_score}", file=sys.stderr)
                print(f"     置信度: {min(95, 70 + best_score // 2)}%", file=sys.stderr)
                print(f"  ⏱️  XML深度分析总耗时: {total_time:.2f}ms", file=sys.stderr)
                
                result = {
                    'element': element_desc,
                    'ref': ref,
                    'confidence': min(95, 70 + best_score // 2),
                    'method': 'xml_analysis'
                }
                return (result, [])  # 成功找到，不需要AI兜底
        
        # XML分析失败，但返回候选元素供AI分析
        candidates = matched[:5] if matched else []  # 最多返回5个候选
        return (None, candidates)
    
    async def _try_position_analysis(self, elements: list, query: str) -> Optional[Dict]:
        """
        位置分析（Level 3.5）⭐ 新增
        
        通过XML中的bounds信息定位无标识元素（如底部导航栏图标）
        
        适用场景：
        - "底部导航栏第X个图标"
        - "顶部第X个图标"
        - "右下角的按钮"
        
        Args:
            elements: 已解析的元素列表
            query: 查询文本
        
        Returns:
            定位结果 或 None
        """
        import time
        start_time = time.time()
        
        # 检测是否是位置查询
        position_keywords = [
            '底部导航', '底部第', '底部图标',
            '顶部导航', '顶部第', '顶部图标',
            '右下角', '左下角', '右上角', '左上角',
            '悬浮按钮', '悬浮', '加号', 'fab',
            '第1个', '第2个', '第3个', '第4个', '第5个',
            '第一个', '第二个', '第三个', '第四个', '第五个',
            '最下面', '最上面', '最左边', '最右边',
            '帖子', '按钮', '图标',  # 支持通用的第N个描述
        ]
        
        is_position_query = any(kw in query for kw in position_keywords)
        
        if not is_position_query:
            return None
        
        print(f"  📍 Level 3.5: 位置分析...", file=sys.stderr)
        
        try:
            from .position_analyzer import PositionAnalyzer
            
            # 获取屏幕尺寸（从第一个元素推测，或使用默认值）
            screen_width = 1080
            screen_height = 2400
            
            # 尝试从元素中获取屏幕尺寸
            for elem in elements:
                bounds = elem.get('bounds', '')
                if bounds:
                    import re
                    match = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                    if match:
                        x2, y2 = int(match.group(3)), int(match.group(4))
                        screen_width = max(screen_width, x2)
                        screen_height = max(screen_height, y2)
            
            analyzer = PositionAnalyzer(screen_width, screen_height)
            
            # 根据查询类型选择分析方法（优先级：位置 > 序号）
            result = None
            if '悬浮' in query or '加号' in query or 'fab' in query.lower():
                result = analyzer.analyze_floating_button(elements, query)
            elif '右上角' in query or '上角' in query:
                # 🎯 新增：右上角位置分析
                print(f"  🎯 检测到'右上角'查询，调用 analyze_corner_position", file=sys.stderr)
                result = analyzer.analyze_corner_position(elements, query, corner='top_right')
            elif '左上角' in query:
                result = analyzer.analyze_corner_position(elements, query, corner='top_left')
            elif '右下角' in query:
                result = analyzer.analyze_corner_position(elements, query, corner='bottom_right')
            elif '左下角' in query:
                result = analyzer.analyze_corner_position(elements, query, corner='bottom_left')
            elif ('底部' in query and ('导航' in query or '图标' in query)) or ('底部' in query and any(kw in query for kw in ['第一个', '第二个', '第三个', '第四个', '第五个', '第1个', '第2个', '第3个', '第4个', '第5个'])):
                # 🎯 修复：优先匹配"底部第X个图标"这种描述
                print(f"  🎯 检测到'底部第X个'查询，调用 analyze_bottom_navigation", file=sys.stderr)
                result = analyzer.analyze_bottom_navigation(elements, query)
            elif ('顶部' in query and ('导航' in query or '图标' in query)) or ('顶部' in query and any(kw in query for kw in ['第一个', '第二个', '第三个', '第四个', '第五个', '第1个', '第2个', '第3个', '第4个', '第5个'])):
                # 🎯 修复：优先匹配"顶部第X个图标"这种描述
                print(f"  🎯 检测到'顶部第X个'查询，调用 analyze_top_navigation", file=sys.stderr)
                result = analyzer.analyze_top_navigation(elements, query)
            elif any(kw in query for kw in ['第一个', '第二个', '第三个', '第四个', '第五个', '第1个', '第2个', '第3个', '第4个', '第5个']):
                # 通用的"第N个"定位（没有位置限定）
                print(f"  🎯 检测到'第N个'查询，调用 analyze_nth_element", file=sys.stderr)
                result = analyzer.analyze_nth_element(elements, query)
            else:
                # 其他位置查询（暂不支持）
                print(f"  ⚠️  未匹配到任何位置分析方法", file=sys.stderr)
                result = None
            
            if result:
                elapsed = (time.time() - start_time) * 1000
                print(f"     ⏱️  位置分析耗时: {elapsed:.2f}ms", file=sys.stderr)
                return result
            
        except ImportError:
            print(f"     ⚠️  位置分析器未安装", file=sys.stderr)
        except Exception as e:
            print(f"     ⚠️  位置分析失败: {e}", file=sys.stderr)
        
        return None
    
    async def _try_ai_candidates(self, query: str, candidates: list, all_elements: list) -> Optional[Dict]:
        """
        AI智能兜底 - 分析候选元素
        
        Args:
            query: 用户查询
            candidates: 候选元素列表
            all_elements: 所有元素（用于构建上下文）
        """
        if not candidates:
            return None
        
        try:
            from ..ai.ai_analyzer import ai_analyzer
            
            # 构建上下文信息
            context = f"页面共有{len(all_elements)}个元素，已筛选出{len(candidates)}个候选"
            
            # 调用AI分析
            result = await ai_analyzer.analyze_candidates(query, candidates, context)
            return result
            
        except ImportError:
            print(f"  ⚠️  AI分析器未配置", file=sys.stderr)
            return None
        except Exception as e:
            print(f"  ⚠️  AI智能兜底失败: {e}", file=sys.stderr)
            return None
    
    async def _try_vision(self, query: str) -> Optional[Dict]:
        """尝试视觉识别（多模态）"""
        print(f"  👁️  Level 4: 尝试视觉识别...", file=sys.stderr)
        try:
            from ...vision.vision_locator import MobileVisionLocator
            
            vision_locator = MobileVisionLocator(self.mobile_client)
            result = await vision_locator.locate_element_by_vision(query)
            
            if result and result.get('found'):
                # 视觉识别返回的是坐标点，直接用于点击
                x = result.get('x', 0)
                y = result.get('y', 0)
                confidence = result.get('confidence', 80)
                print(f"  ✅ 视觉识别成功: 坐标({x}, {y}), 置信度{confidence}%", file=sys.stderr)
                return {
                    'element': query,
                    'ref': f"vision_coord_{x}_{y}",  # 特殊标记，表示是坐标定位
                    'confidence': confidence,
                    'method': 'vision',
                    'x': x,
                    'y': y,
                }
            else:
                reason = result.get('reason', 'unknown') if result else 'result is None'
                print(f"  ❌ 视觉识别未找到元素: {reason}", file=sys.stderr)
        except ImportError:
            print("  ⚠️  视觉识别模块未安装（需要安装dashscope: pip install dashscope）", file=sys.stderr)
        except Exception as e:
            print(f"  ❌ 视觉识别异常: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        
        return None
    
    async def _try_ai_analysis(self, query: str, elements: list = None) -> Optional[Dict]:
        """尝试文本AI分析（最后手段）- 使用AI分析移动端XML结构"""
        print(f"  🤖 Level 4: 尝试AI分析...", file=sys.stderr)
        
        try:
            # 加载根目录的.env配置
            from pathlib import Path
            import os
            from dotenv import load_dotenv
            
            # 查找根目录的.env文件（从mobile_mcp向上查找）
            current_dir = Path(__file__).parent
            root_dir = current_dir.parent.parent.parent  # backend/mobile_mcp -> backend -> douzi-ai
            env_file = root_dir / '.env'
            
            if env_file.exists():
                load_dotenv(env_file)
                print(f"  ✅ 已加载.env配置: {env_file}", file=sys.stderr)
            else:
                # 尝试从当前目录向上查找
                for parent in current_dir.parents:
                    env_file = parent / '.env'
                    if env_file.exists():
                        load_dotenv(env_file)
                        print(f"  ✅ 已加载.env配置: {env_file}", file=sys.stderr)
                        break
            
            # 获取页面快照（格式化的XML结构）
            snapshot = await self.mobile_client.snapshot()
            
            # 获取AI配置
            try:
                mind_ui_path = PathLib(__file__).parent.parent.parent.parent / 'mind-ui'
                if str(mind_ui_path) not in sys.path:
                    sys.path.insert(0, str(mind_ui_path))
                
                from browser_mcp.core.ai.api.api_client import optimize_with_ai_auto
                from browser_mcp.core.ai.config.config import get_ai_config
                
                # 检查AI配置是否可用
                ai_config = get_ai_config()
                if ai_config.default_provider == "manual" or ai_config.is_manual_mode():
                    print(f"  ⚠️  AI配置为手动模式，跳过AI分析", file=sys.stderr)
                    return None
                
                print(f"  🤖 使用AI分析 (Provider: {ai_config.default_provider}, Model: {ai_config.default_model})", file=sys.stderr)
                
                # 创建适配器，让AI可以分析移动端页面
                class MobileAdapter:
                    async def snapshot(self):
                        class SnapshotResult:
                            def __init__(self, text):
                                self.content = [type('Content', (), {'text': text})()]
                        return SnapshotResult(snapshot)
                
                adapter = MobileAdapter()
                
                # 调用AI分析
                result = await optimize_with_ai_auto(adapter, query)
                
                if result:
                    print(f"  ✅ AI分析成功: {result.get('element', '')} (置信度: {result.get('confidence', 0)}%)", file=sys.stderr)
                    # 转换结果为移动端格式，传入elements避免重复读取XML
                    converted = self._convert_result(result, query, elements)
                    if converted and converted.get('ref'):
                        return converted
                    else:
                        print(f"  ⚠️  AI分析结果转换失败（无法在移动端XML中找到对应元素）", file=sys.stderr)
                        return None
                else:
                    print(f"  ❌ AI分析未找到元素", file=sys.stderr)
                    return None
                    
            except ImportError as e:
                print(f"  ⚠️  无法导入AI模块: {e}", file=sys.stderr)
                return None
            except Exception as e:
                print(f"  ⚠️  AI分析失败: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                return None
                
        except ImportError:
            print(f"  ⚠️  未安装python-dotenv，无法加载.env配置", file=sys.stderr)
            return None
        except Exception as e:
            print(f"  ⚠️  AI分析异常: {e}", file=sys.stderr)
            return None
    
    def _convert_result(self, result: Dict, query: str = "", elements: list = None) -> Dict:
        """
        转换结果为移动端格式
        
        SmartLocator返回的ref可能是：
        1. CSS选择器（如 "button.login-btn"）- 需要重新定位
        2. resource-id（如 "com.app:id/login"）- 直接使用
        3. text（如 "登录"）- 直接使用
        4. bounds（如 "[100,200][300,400]"）- 直接使用
        
        Args:
            result: SmartLocator返回的结果
            query: 查询文本
            elements: 已解析的元素列表（可选，避免重复读取XML）
        """
        ref = result.get('ref', '')
        element = result.get('element', '')
        
        print(f"  🔄 转换AI结果: ref='{ref}', element='{element}', query='{query}'", file=sys.stderr)
        
        # 🎯 优化：检测 XPath 格式（AI 常返回这种格式）
        is_xpath = ref.startswith('//') or ref.startswith('//*[@')
        if is_xpath:
            print(f"  ⚠️  检测到XPath格式，需要重新定位: {ref}", file=sys.stderr)
        
        # 如果ref是CSS选择器、HTML标签或XPath格式，需要重新定位
        # 这种情况下，使用query或element文本重新在XML中查找
        html_tags = ['input', 'button', 'textbox', 'submit', 'textarea', 'select', 'a', 'div', 'span']
        if is_xpath or '.' in ref or '#' in ref or ref.startswith('button') or ref.startswith('textbox') or ref.lower() in html_tags:
            print(f"  🔍 检测到HTML标签/CSS选择器，重新定位...", file=sys.stderr)
            # CSS选择器格式，需要重新定位
            # 使用query或element文本在XML中查找
            
            # ⚡ 优化：如果传入了elements，直接使用；否则才读取XML
            if elements is None:
                xml_string = self.mobile_client.u2.dump_hierarchy()
                elements = self.mobile_client.xml_parser.parse(xml_string)
            
            # 优先使用query，其次使用element
            search_text = (query or element).lower()
            
            # 🔍 只在可点击元素中查找
            clickable_elements = [e for e in elements if e.get('clickable') or e.get('class_name') in ['Button', 'ImageButton', 'EditText']]
            print(f"  🔍 在{len(clickable_elements)}个可点击元素中查找 '{search_text}'", file=sys.stderr)
            
            for elem in clickable_elements:
                elem_text = elem.get('text', '').lower()
                elem_desc = elem.get('content_desc', '').lower()
                elem_resource_id = elem.get('resource_id', '').lower()
                
                # 精确匹配（text或description完全包含查询文本）
                # 🎯 改进：支持模糊匹配（忽略空格、括号等）
                search_text_normalized = search_text.replace(' ', '').replace('(', '').replace(')', '').replace('（', '').replace('）', '')
                elem_text_normalized = elem_text.replace(' ', '').replace('(', '').replace(')', '').replace('（', '').replace('）', '')
                elem_desc_normalized = elem_desc.replace(' ', '').replace('(', '').replace(')', '').replace('（', '').replace('）', '')
                
                if search_text and (
                    (elem_text and search_text in elem_text) or 
                    (elem_desc and search_text in elem_desc) or
                    (elem_text_normalized and search_text_normalized in elem_text_normalized) or
                    (elem_desc_normalized and search_text_normalized in elem_desc_normalized)
                ):
                    # 找到匹配，优先使用text/description（更可靠），其次使用resource-id
                    new_ref = elem.get('text') or elem.get('content_desc') or elem.get('resource_id', '')
                    if new_ref:
                        print(f"  ✅ 找到匹配元素: {new_ref}", file=sys.stderr)
                        result['ref'] = new_ref
                        result['method'] = 'rule_match_converted'
                        return result
            
            # 如果找不到，尝试使用element文本（去除"按钮"等后缀）
            if element:
                element_clean = element.replace('按钮', '').replace('输入框', '').strip().lower()
                print(f"  🔍 尝试使用清洗后的element: '{element_clean}'", file=sys.stderr)
                for elem in elements:
                    elem_text = elem.get('text', '').lower()
                    elem_desc = elem.get('content_desc', '').lower()
                    if element_clean in elem_text or elem_text in element_clean or element_clean in elem_desc or elem_desc in element_clean:
                        new_ref = elem.get('resource_id') or elem.get('text') or elem.get('content_desc', '')
                        if new_ref:
                            print(f"  ✅ 找到匹配元素: {new_ref}", file=sys.stderr)
                            result['ref'] = new_ref
                            result['method'] = 'rule_match_converted'
                            return result
            
            print(f"  ❌ 转换失败，未找到匹配元素", file=sys.stderr)
            return None  # 转换失败返回None，而不是返回原result
        
        # 其他格式（resource-id、text、bounds）直接返回
        return result
    
    def _get_cache_key(self, query: str) -> str:
        """生成缓存key"""
        # 使用页面结构hash + 查询文本
        snapshot_hash = hashlib.md5(
            str(self.mobile_client._snapshot_cache or '').encode()
        ).hexdigest()[:8]
        
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        
        return f"{snapshot_hash}_{query_hash}"
    
    async def _cache_result(self, query: str, result: Dict):
        """缓存定位结果"""
        cache_key = self._get_cache_key(query)
        self._cache[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }
    
    def _log_performance(self, query: str, method: str, total_time: float, xml_count: int, xml_time: float = 0):
        """
        记录性能日志
        
        Args:
            query: 查询文本
            method: 匹配方法
            total_time: 总耗时（毫秒）
            xml_count: XML读取次数
            xml_time: XML读取耗时（毫秒）
        """
        self.performance_logs.append({
            'query': query,
            'method': method,
            'total_time': total_time,
            'xml_count': xml_count,
            'xml_time': xml_time,
        })
    
    def print_performance_report(self):
        """打印性能报告"""
        print("\n" + "=" * 80, file=sys.stderr)
        print("📊 性能监控报告", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        
        print(f"\n📈 总体统计:", file=sys.stderr)
        print(f"  总定位次数: {self.stats['total']}", file=sys.stderr)
        print(f"  总耗时: {self.stats['total_time']:.2f}ms", file=sys.stderr)
        print(f"  平均耗时: {self.stats['total_time'] / max(1, self.stats['total']):.2f}ms", file=sys.stderr)
        print(f"  XML总读取次数: {self.stats['xml_read_count']}", file=sys.stderr)
        
        print(f"\n🎯 匹配方式分布:", file=sys.stderr)
        print(f"  缓存命中: {self.stats['cache_hits']} ({self.stats['cache_hits']/max(1, self.stats['total'])*100:.1f}%)", file=sys.stderr)
        print(f"  快速预匹配: {self.stats['quick_match_hits']} ({self.stats['quick_match_hits']/max(1, self.stats['total'])*100:.1f}%)", file=sys.stderr)
        print(f"  规则匹配: {self.stats['rule_hits']} ({self.stats['rule_hits']/max(1, self.stats['total'])*100:.1f}%)", file=sys.stderr)
        print(f"  XML深度分析: {self.stats['xml_analysis']} ({self.stats['xml_analysis']/max(1, self.stats['total'])*100:.1f}%)", file=sys.stderr)
        print(f"  位置分析: {self.stats.get('position_analysis', 0)} ({self.stats.get('position_analysis', 0)/max(1, self.stats['total'])*100:.1f}%) ⭐", file=sys.stderr)
        print(f"  视觉识别: {self.stats['vision_calls']} ({self.stats['vision_calls']/max(1, self.stats['total'])*100:.1f}%)", file=sys.stderr)
        print(f"  AI分析: {self.stats['ai_calls']} ({self.stats['ai_calls']/max(1, self.stats['total'])*100:.1f}%)", file=sys.stderr)
        
        if self.performance_logs:
            print(f"\n📋 详细性能日志:", file=sys.stderr)
            print(f"{'序号':<6}{'查询':<25}{'方法':<15}{'总耗时(ms)':<12}{'XML次数':<10}{'XML耗时(ms)':<12}", file=sys.stderr)
            print("-" * 80, file=sys.stderr)
            for i, log in enumerate(self.performance_logs, 1):
                query_short = log['query'][:22] + '...' if len(log['query']) > 22 else log['query']
                print(f"{i:<6}{query_short:<25}{log['method']:<15}{log['total_time']:<12.2f}{log['xml_count']:<10}{log['xml_time']:<12.2f}", file=sys.stderr)
        
        print("\n" + "=" * 80, file=sys.stderr)

