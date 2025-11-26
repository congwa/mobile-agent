#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI分析器 - 智能兜底，分析候选元素
"""
import sys
import json
from typing import Dict, List, Optional
from .ai_config import ai_config


class AIAnalyzer:
    """AI分析器 - 用于智能兜底"""
    
    def __init__(self):
        """初始化AI分析器"""
        self.config = ai_config
    
    async def analyze_candidates(self, query: str, candidates: List[Dict], context: str = "") -> Optional[Dict]:
        """
        分析候选元素，选择最佳匹配
        
        Args:
            query: 用户查询
            candidates: 候选元素列表
            context: 上下文信息（可选）
        
        Returns:
            最佳匹配的元素信息
        """
        if not self.config.is_configured():
            print("  ⚠️  AI未配置，跳过AI分析", file=sys.stderr)
            return None
        
        if not candidates:
            print("  ⚠️  没有候选元素，跳过AI分析", file=sys.stderr)
            return None
        
        try:
            import httpx
            
            # 构建提示词
            prompt = self._build_prompt(query, candidates, context)
            
            print(f"  🤖 调用AI分析（模型: {self.config.model}）...", file=sys.stderr)
            
            # 调用通义千问API
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self.config.api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.config.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "你是一个专业的移动端UI元素分析助手。请根据用户查询和候选元素，选择最匹配的元素，并返回JSON格式的结果。"
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.1,  # 低温度，更确定性
                        "response_format": {"type": "json_object"}  # 强制返回JSON
                    }
                )
            
            if response.status_code != 200:
                print(f"  ❌ AI调用失败: HTTP {response.status_code}", file=sys.stderr)
                print(f"     {response.text}", file=sys.stderr)
                return None
            
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            
            # 解析AI返回的JSON
            ai_result = json.loads(ai_response)
            
            if not ai_result.get('selected_index'):
                print(f"  ⚠️  AI未能选择元素", file=sys.stderr)
                return None
            
            selected_index = ai_result['selected_index'] - 1  # 转换为0-based索引
            
            if selected_index < 0 or selected_index >= len(candidates):
                print(f"  ⚠️  AI返回的索引无效: {selected_index + 1}", file=sys.stderr)
                return None
            
            selected = candidates[selected_index]
            confidence = ai_result.get('confidence', 85)
            reason = ai_result.get('reason', '未提供原因')
            
            print(f"  ✅ AI选择: 候选{selected_index + 1}/{len(candidates)}", file=sys.stderr)
            print(f"     元素: {selected.get('text') or selected.get('content_desc') or selected.get('class_name')}", file=sys.stderr)
            print(f"     置信度: {confidence}%", file=sys.stderr)
            print(f"     理由: {reason}", file=sys.stderr)
            
            return {
                'element': selected.get('text') or selected.get('content_desc') or query,
                'ref': self._get_ref(selected),
                'confidence': confidence,
                'method': 'ai_analysis',
                'reason': reason
            }
            
        except Exception as e:
            print(f"  ❌ AI分析异常: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return None
    
    def _build_prompt(self, query: str, candidates: List[Dict], context: str) -> str:
        """构建AI提示词"""
        # 格式化候选元素
        candidates_text = []
        for i, elem in enumerate(candidates, 1):
            text = elem.get('text', '')
            desc = elem.get('content_desc', '')
            resource_id = elem.get('resource_id', '')
            class_name = elem.get('class_name', '')
            bounds = elem.get('bounds', '')
            clickable = elem.get('clickable', False)
            focusable = elem.get('focusable', False)
            
            # 计算位置
            position = "未知"
            if bounds:
                try:
                    # bounds格式: "[x1,y1][x2,y2]"
                    coords = bounds.replace('[', '').replace(']', ',').split(',')
                    y1 = int(coords[1])
                    if y1 < 400:
                        position = "顶部"
                    elif y1 < 800:
                        position = "中部"
                    else:
                        position = "底部"
                except:
                    pass
            
            parts = [f"候选{i}:"]
            if text:
                parts.append(f"文本=\"{text[:50]}\"")
            if desc:
                parts.append(f"描述=\"{desc[:50]}\"")
            if resource_id:
                parts.append(f"ID={resource_id}")
            parts.append(f"类型={class_name}")
            parts.append(f"位置={position}")
            if clickable:
                parts.append("可点击")
            if focusable:
                parts.append("可聚焦")
            
            candidates_text.append(" | ".join(parts))
        
        prompt = f"""
用户查询: "{query}"

页面上有以下候选元素:
{chr(10).join(candidates_text)}

{f"上下文信息: {context}" if context else ""}

请分析哪个元素最匹配用户查询，并返回JSON格式:
{{
    "selected_index": <1到{len(candidates)}的数字>,
    "confidence": <置信度0-100>,
    "reason": "<选择理由>"
}}

分析要点:
1. 优先匹配文本/描述的语义
2. 考虑元素类型是否合理（如输入框应该是EditText）
3. 考虑元素位置（如"顶部按钮"、"底部输入框"）
4. 考虑用户意图（如"点击"需要可点击元素）
"""
        return prompt
    
    def _get_ref(self, element: Dict) -> str:
        """获取元素引用"""
        # 优先级: resource_id > content_desc > text > bounds
        return (
            element.get('resource_id') or
            element.get('content_desc') or
            element.get('text') or
            element.get('bounds', '')
        )


# 全局实例
ai_analyzer = AIAnalyzer()

