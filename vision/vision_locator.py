#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
移动端视觉定位器 - 多模态AI支持

功能：
1. 截图
2. 图片压缩
3. 多模态AI分析（通义千问VL / GPT-4V）
4. 返回元素坐标
"""
import base64
import hashlib
import asyncio
from typing import Dict, Optional
import tempfile

try:
    import dashscope
    from dashscope import MultiModalConversation
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class MobileVisionLocator:
    """
    移动端视觉定位器
    
    使用多模态AI模型进行视觉元素定位
    """
    
    def __init__(self, mobile_client, api_key: Optional[str] = None):
        """
        初始化视觉定位器
        
        Args:
            mobile_client: MobileClient实例
            api_key: 通义千问API Key（可选，从环境变量读取）
        """
        self.mobile_client = mobile_client
        
        # API配置
        self.api_key = api_key or self._get_api_key()
        if self.api_key and DASHSCOPE_AVAILABLE:
            dashscope.api_key = self.api_key
        
        # 缓存
        self._cache: Dict[str, Dict] = {}
        
        # 统计
        self.stats = {
            'total_calls': 0,
            'cache_hits': 0,
            'api_calls': 0,
        }
    
    def _get_api_key(self) -> Optional[str]:
        """从环境变量获取API Key"""
        import os
        from pathlib import Path
        from dotenv import load_dotenv
        
        # 尝试加载.env文件（从mobile_mcp向上查找）
        current_dir = Path(__file__).parent
        root_dir = current_dir.parent.parent.parent  # vision -> mobile_mcp -> backend -> douzi-ai
        env_file = root_dir / '.env'
        
        if env_file.exists():
            load_dotenv(env_file)
            print(f"  ✅ 已加载.env文件: {env_file}")
        
        # 🎯 支持多种API Key名称（兼容性）
        api_key = (
            os.environ.get('DASHSCOPE_API_KEY') or 
            os.environ.get('QWEN_API_KEY') or  # 通义千问API Key
            os.environ.get('ALIBABA_CLOUD_API_KEY') or
            os.environ.get('DASHSCOPE_KEY')
        )
        
        if api_key:
            # 安全提示：不打印 API Key 相关信息，避免日志泄露
            print(f"  ✅ 已读取视觉识别API配置")
        else:
            print(f"  ⚠️  未找到视觉识别API Key，请配置环境变量: DASHSCOPE_API_KEY")
        
        return api_key
    
    def _get_vision_model(self) -> str:
        """获取视觉识别模型（支持环境变量配置）"""
        import os
        # 支持环境变量配置，默认使用 qwen-vl-plus
        return os.environ.get('VISION_MODEL', 'qwen-vl-plus')
    
    async def locate_element_by_vision(self, element_description: str, region: Optional[Dict] = None) -> Dict:
        """
        通过视觉识别定位元素
        
        Args:
            element_description: 元素描述（自然语言）
            region: 截图区域 {"x": 0, "y": 0, "width": 1080, "height": 2400}，None则智能选择区域
            
        Returns:
            定位结果（包含绝对坐标）
        """
        self.stats['total_calls'] += 1
        
        # 检查缓存
        cache_key = self._get_cache_key(element_description)
        if cache_key in self._cache:
            self.stats['cache_hits'] += 1
            return self._cache[cache_key]
        
        # 智能选择区域（如果未指定）
        if region is None:
            region = self._smart_region_selection(element_description)
        
        # 截图（支持区域截图）
        screenshot_path, region_offset = await self._take_screenshot(region)
        
        # 压缩图片
        if PIL_AVAILABLE:
            screenshot_path = self._compress_image(screenshot_path)
        
        # 调用多模态AI（返回相对于截图的坐标）
        result = await self._call_vision_api(screenshot_path, element_description)
        
        # 坐标转换：截图相对坐标 → 屏幕绝对坐标
        if result.get('found') and region_offset:
            result['x'] = result.get('x', 0) + region_offset['x']
            result['y'] = result.get('y', 0) + region_offset['y']
            result['region_offset'] = region_offset  # 记录偏移量（调试用）
        
        # 缓存结果
        self._cache[cache_key] = result
        
        return result
    
    def _smart_region_selection(self, description: str) -> Optional[Dict]:
        """
        智能选择截图区域（减少图片大小，提高识别精度）
        
        根据元素描述推断应该截哪个区域：
        - "底部导航栏" → 只截底部区域
        - "顶部标题栏" → 只截顶部区域
        - "登录按钮" → 截中间区域
        """
        # 获取屏幕尺寸
        screen_info = self.mobile_client.u2.info
        screen_width = screen_info.get('displayWidth', 1080)
        screen_height = screen_info.get('displayHeight', 2400)
        
        description_lower = description.lower()
        
        # 底部区域（底部导航栏、底部按钮等）
        if any(keyword in description_lower for keyword in ['底部', 'bottom', '导航栏', 'tab', '底部导航']):
            return {
                'x': 0,
                'y': int(screen_height * 0.8),  # 底部20%
                'width': screen_width,
                'height': int(screen_height * 0.2)
            }
        
        # 顶部区域（标题栏、顶部导航等）
        if any(keyword in description_lower for keyword in ['顶部', 'top', '标题', 'header', '导航栏']):
            return {
                'x': 0,
                'y': 0,
                'width': screen_width,
                'height': int(screen_height * 0.2)  # 顶部20%
            }
        
        # 中间区域（登录按钮、表单等）
        if any(keyword in description_lower for keyword in ['登录', 'login', '按钮', 'button', '表单', 'form']):
            return {
                'x': 0,
                'y': int(screen_height * 0.3),
                'width': screen_width,
                'height': int(screen_height * 0.4)  # 中间40%
            }
        
        # 默认全屏
        return None
    
    async def _take_screenshot(self, region: Optional[Dict] = None) -> tuple:
        """
        截图（支持区域截图）
        
        Args:
            region: 截图区域 {"x": 0, "y": 0, "width": 1080, "height": 2400}，None则全屏
            
        Returns:
            (截图路径, 区域偏移量) - 偏移量用于坐标转换
        """
        # 创建临时文件
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        # 获取屏幕尺寸
        screen_info = self.mobile_client.u2.info
        screen_width = screen_info.get('displayWidth', 1080)
        screen_height = screen_info.get('displayHeight', 2400)
        
        # 区域偏移量（用于坐标转换）
        region_offset = {'x': 0, 'y': 0}
        
        if region:
            # 区域截图：先截全屏，再裁剪
            full_screenshot_path = temp_path.replace('.png', '_full.png')
            self.mobile_client.u2.screenshot(full_screenshot_path)
            
            # 裁剪区域
            if PIL_AVAILABLE:
                img = Image.open(full_screenshot_path)
                x = region.get('x', 0)
                y = region.get('y', 0)
                width = region.get('width', screen_width)
                height = region.get('height', screen_height)
                
                # 确保不越界
                x = max(0, min(x, screen_width))
                y = max(0, min(y, screen_height))
                width = min(width, screen_width - x)
                height = min(height, screen_height - y)
                
                # 裁剪
                cropped = img.crop((x, y, x + width, y + height))
                cropped.save(temp_path)
                
                # 记录偏移量
                region_offset = {'x': x, 'y': y}
            else:
                # PIL不可用时，使用全屏截图
                import shutil
                shutil.copy2(full_screenshot_path, temp_path)
        else:
            # 全屏截图
            self.mobile_client.u2.screenshot(temp_path)
        
        return temp_path, region_offset
    
    def _compress_image(self, image_path: str, max_size: tuple = (1920, 1080), quality: int = 80) -> str:
        """
        压缩图片
        
        Args:
            image_path: 图片路径
            max_size: 最大尺寸
            quality: JPEG质量（1-100）
            
        Returns:
            压缩后的图片路径
        """
        if not PIL_AVAILABLE:
            return image_path
        
        try:
            img = Image.open(image_path)
            
            # 调整尺寸
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # 转换为JPEG（更小）
            if image_path.endswith('.png'):
                jpeg_path = image_path.replace('.png', '_compressed.jpg')
                img.convert('RGB').save(jpeg_path, 'JPEG', quality=quality)
                return jpeg_path
            
            return image_path
        except Exception as e:
            print(f"  ⚠️  图片压缩失败: {e}")
            return image_path
    
    async def _call_vision_api(self, image_path: str, description: str) -> Dict:
        """调用多模态AI API"""
        if not DASHSCOPE_AVAILABLE:
            return {
                'found': False,
                'reason': 'dashscope未安装，请运行: pip install dashscope'
            }
        
        # 🎯 改进：如果初始化时没读取到API Key，再次尝试读取
        if not self.api_key:
            print(f"  ⚠️  视觉识别API Key未配置，尝试重新读取.env...")
            self.api_key = self._get_api_key()
            if self.api_key:
                dashscope.api_key = self.api_key
                print(f"  ✅ 已从.env读取API Key")
            else:
                # 打印调试信息
                import os
                from pathlib import Path
                current_dir = Path(__file__).parent
                root_dir = current_dir.parent.parent.parent
                env_file = root_dir / '.env'
                print(f"  ⚠️  .env文件路径: {env_file}")
                print(f"  ⚠️  .env文件存在: {env_file.exists()}")
                if env_file.exists():
                    print(f"  ⚠️  请检查.env文件中是否有DASHSCOPE_API_KEY")
                return {
                    'found': False,
                    'reason': '未配置API Key，请检查.env文件中的DASHSCOPE_API_KEY'
                }
        
        self.stats['api_calls'] += 1
        
        try:
            # 读取图片
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode()
            
            # 构建prompt（明确说明坐标是相对于截图的）
            prompt = f"""请在这张移动端App截图中找到以下元素：{description}

重要：请返回元素在截图中的相对坐标（x, y），不是屏幕绝对坐标。
格式为JSON：
{{
    "found": true/false,
    "x": 元素中心X坐标（相对于截图左上角，0-截图宽度）,
    "y": 元素中心Y坐标（相对于截图左上角，0-截图高度）,
    "confidence": 置信度(0-100),
    "reason": "定位原因"
}}"""
            
            # 获取模型配置（支持环境变量）
            vision_model = self._get_vision_model()
            
            # 调用API（使用线程池避免阻塞）
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: MultiModalConversation.call(
                    model=vision_model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"image": f"data:image/png;base64,{image_data}"},
                                {"text": prompt}
                            ]
                        }
                    ]
                )
            )
            
            # 解析结果
            if result.status_code == 200:
                # 🎯 修复：兼容不同的响应格式
                try:
                    # 尝试获取响应文本（可能是对象或字典）
                    content = result.output.choices[0].message.content[0]
                    if isinstance(content, dict):
                        response_text = content.get('text', '') or str(content)
                    else:
                        response_text = content.text if hasattr(content, 'text') else str(content)
                    
                    # 提取JSON
                    import json
                    import re
                    json_match = re.search(r'\{[^{}]*"found"[^{}]*\}', response_text, re.DOTALL)
                    if json_match:
                        result_data = json.loads(json_match.group(0))
                        return result_data
                    else:
                        # 如果没找到JSON，尝试直接解析整个响应
                        try:
                            result_data = json.loads(response_text)
                            if 'found' in result_data:
                                return result_data
                        except:
                            pass
                        
                        return {
                            'found': False,
                            'reason': f'无法解析AI响应: {response_text[:200]}'
                        }
                except Exception as e:
                    return {
                        'found': False,
                        'reason': f'解析响应失败: {e}, 响应类型: {type(result.output.choices[0].message.content[0])}'
                    }
            
            return {
                'found': False,
                'reason': f'API调用失败: status_code={result.status_code}, message={getattr(result, "message", "unknown")}'
            }
            
        except Exception as e:
            return {
                'found': False,
                'reason': f'视觉识别异常: {e}'
            }
    
    def _get_cache_key(self, description: str) -> str:
        """生成缓存key"""
        # 使用描述文本hash
        return hashlib.md5(description.encode()).hexdigest()[:16]

