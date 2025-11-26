#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一的日志管理器

用于规范MCP Server的日志输出，避免直接使用print导致的JSON解析错误
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# 创建logger
logger = logging.getLogger('mobile_mcp')

# 默认配置标志
_configured = False


def configure_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    enable_console: bool = True,
    enable_emoji: bool = True
):
    """
    配置日志系统
    
    Args:
        level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        log_file: 日志文件路径（可选）
        enable_console: 是否输出到控制台（默认True）
        enable_emoji: 是否启用emoji（默认True）
    """
    global _configured
    if _configured:
        return
    
    logger.setLevel(level)
    
    # 创建格式化器
    if enable_emoji:
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # 控制台处理器（输出到stderr，避免与MCP协议混淆）
    if enable_console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # 文件处理器
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    _configured = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    获取logger实例
    
    Args:
        name: logger名称（可选）
    
    Returns:
        logger实例
    """
    if not _configured:
        configure_logging()
    
    if name:
        return logging.getLogger(f'mobile_mcp.{name}')
    return logger


# 便捷函数
def debug(msg: str, *args, **kwargs):
    """Debug级别日志"""
    logger.debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs):
    """Info级别日志"""
    logger.info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    """Warning级别日志"""
    logger.warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    """Error级别日志"""
    logger.error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs):
    """Critical级别日志"""
    logger.critical(msg, *args, **kwargs)


# 兼容旧代码的print替代函数
def log_print(msg: str, level: str = 'info'):
    """
    替代print的函数，自动使用logging系统
    
    Args:
        msg: 消息内容
        level: 日志级别（debug, info, warning, error, critical）
    """
    level_map = {
        'debug': logger.debug,
        'info': logger.info,
        'warning': logger.warning,
        'error': logger.error,
        'critical': logger.critical
    }
    
    log_func = level_map.get(level.lower(), logger.info)
    log_func(msg)


# 初始化默认配置
if not _configured:
    configure_logging(
        level=logging.INFO,
        enable_console=True,
        enable_emoji=True
    )

