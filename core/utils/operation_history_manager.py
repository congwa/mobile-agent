#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
操作历史管理器 - 文件持久化

功能：
1. 自动保存操作历史到文件
2. 从文件加载操作历史
3. 管理操作历史的增删改查
"""
import sys
import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


class OperationHistoryManager:
    """
    操作历史管理器 - 文件持久化
    
    文件格式：JSON Lines（每行一个操作记录）
    文件位置：~/.mobile_mcp/operation_history.jsonl
    """
    
    def __init__(self, history_file: Optional[str] = None):
        """
        初始化操作历史管理器
        
        Args:
            history_file: 历史文件路径，默认使用 ~/.mobile_mcp/operation_history.jsonl
        """
        if history_file is None:
            # 默认使用用户目录下的 .mobile_mcp 目录
            home_dir = Path.home()
            mobile_mcp_dir = home_dir / ".mobile_mcp"
            mobile_mcp_dir.mkdir(exist_ok=True)
            self.history_file = mobile_mcp_dir / "operation_history.jsonl"
        else:
            self.history_file = Path(history_file)
        
        # 确保目录存在
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 内存缓存
        self._cache: List[Dict] = []
        self._cache_loaded = False
    
    def append(self, operation: Dict):
        """
        追加操作记录到文件
        
        Args:
            operation: 操作记录字典
        """
        # 添加时间戳
        if 'timestamp' not in operation:
            operation['timestamp'] = datetime.now().isoformat()
        
        # 追加到文件（JSON Lines格式）
        try:
            with open(self.history_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(operation, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"⚠️  保存操作历史失败: {e}", file=os.sys.stderr)
        
        # 更新缓存
        self._cache.append(operation)
    
    def load(self, limit: Optional[int] = None) -> List[Dict]:
        """
        从文件加载操作历史
        
        Args:
            limit: 限制加载的记录数，None表示加载全部
        
        Returns:
            操作历史列表
        """
        if not self.history_file.exists():
            return []
        
        operations = []
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if limit:
                    lines = lines[-limit:]  # 只加载最后N条
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        operation = json.loads(line)
                        operations.append(operation)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"⚠️  加载操作历史失败: {e}", file=os.sys.stderr)
        
        # 更新缓存
        self._cache = operations
        self._cache_loaded = True
        return operations
    
    def get_all(self) -> List[Dict]:
        """
        获取所有操作历史（优先使用缓存）
        
        Returns:
            操作历史列表
        """
        if not self._cache_loaded:
            return self.load()
        return self._cache.copy()
    
    def get_successful(self) -> List[Dict]:
        """
        获取成功的操作历史
        
        Returns:
            成功的操作历史列表
        """
        all_ops = self.get_all()
        return [op for op in all_ops if op.get('success', False)]
    
    def clear(self):
        """
        清除所有操作历史
        """
        try:
            if self.history_file.exists():
                self.history_file.unlink()
            self._cache = []
            self._cache_loaded = True
        except Exception as e:
            print(f"⚠️  清除操作历史失败: {e}", file=os.sys.stderr)
    
    def get_statistics(self) -> Dict:
        """
        获取操作历史统计信息
        
        Returns:
            统计信息字典
        """
        all_ops = self.get_all()
        successful_ops = self.get_successful()
        
        return {
            'total_operations': len(all_ops),
            'successful_operations': len(successful_ops),
            'failed_operations': len(all_ops) - len(successful_ops),
            'success_rate': f"{len(successful_ops)/len(all_ops)*100:.1f}%" if all_ops else "0%",
            'history_file': str(self.history_file)
        }

