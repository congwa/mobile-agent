#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI配置模块 - 从根目录.env读取配置
支持通义千问API
"""
import os
from pathlib import Path
from typing import Optional


class AIConfig:
    """AI配置类"""
    
    def __init__(self):
        """初始化配置"""
        self._load_env()
    
    def _load_env(self):
        """从根目录.env加载配置"""
        # 查找根目录.env文件
        # 当前路径: backend/mobile_mcp/core/ai/ai_config.py
        # 项目根目录: douzi-ai/
        current_file = Path(__file__)
        # 向上5层: ai/ -> core/ -> mobile_mcp/ -> backend/ -> douzi-ai/
        project_root = current_file.parent.parent.parent.parent.parent
        env_file = project_root / '.env'
        
        # 如果项目根目录没有，尝试backend目录
        if not env_file.exists():
            backend_root = current_file.parent.parent.parent.parent
            env_file = backend_root / '.env'
        
        if not env_file.exists():
            print(f"⚠️  未找到.env文件: {env_file}")
            return
        
        # 读取.env文件
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # 解析键值对
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    
                    # 设置环境变量（如果尚未设置）
                    if key not in os.environ:
                        os.environ[key] = value
    
    @property
    def api_key(self) -> Optional[str]:
        """获取API密钥"""
        # 优先级：QWEN_API_KEY > OPENAI_API_KEY
        return (
            os.getenv('QWEN_API_KEY') or 
            os.getenv('DASHSCOPE_API_KEY') or
            os.getenv('OPENAI_API_KEY')
        )
    
    @property
    def api_base(self) -> Optional[str]:
        """获取API基础URL"""
        return (
            os.getenv('QWEN_API_BASE') or 
            os.getenv('OPENAI_API_BASE') or
            'https://dashscope.aliyuncs.com/compatible-mode/v1'  # 通义千问默认地址
        )
    
    @property
    def model(self) -> str:
        """获取模型名称"""
        return (
            os.getenv('QWEN_MODEL') or 
            os.getenv('OPENAI_MODEL') or
            'qwen-plus'  # 通义千问默认模型
        )
    
    @property
    def timeout(self) -> int:
        """获取超时时间（秒）"""
        return int(os.getenv('AI_TIMEOUT', '30'))
    
    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.api_key)
    
    def __repr__(self):
        """字符串表示（安全：不显示 API Key 信息）"""
        return (
            f"AIConfig(\n"
            f"  api_base={self.api_base}\n"
            f"  model={self.model}\n"
            f"  api_key_configured={'✅ Yes' if self.api_key else '❌ No'}\n"
            f"  timeout={self.timeout}s\n"
            f")"
        )


# 全局配置实例
ai_config = AIConfig()


if __name__ == '__main__':
    # 测试配置
    print("=" * 60)
    print("AI配置测试")
    print("=" * 60)
    print(ai_config)
    print()
    print(f"是否已配置: {ai_config.is_configured()}")

