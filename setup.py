#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mobile MCP AI - 移动端自动化测试框架
支持Android和iOS，集成AI增强功能
"""

from setuptools import setup, find_packages
from pathlib import Path

# 读取 README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# 读取 requirements
requirements = []
requirements_file = this_directory / "requirements.txt"
if requirements_file.exists():
    with open(requirements_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # 跳过空行和注释
            if line and not line.startswith('#'):
                requirements.append(line)

setup(
    name="mobile-mcp-ai",
    version="2.3.1",  # 修复截图压缩兼容性问题（Pillow 版本 + RGBA 处理）
    author="douzi",
    author_email="1492994674@qq.com",
    description="移动端自动化 MCP Server - 支持 Android/iOS，AI 功能可选（基础工具不需要 AI）",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/test111ddff-hash/mobile-mcp-ai",
    project_urls={
        "Documentation": "https://github.com/test111ddff-hash/mobile-mcp-ai",
        "Source": "https://github.com/test111ddff-hash/mobile-mcp-ai",
        "Tracker": "https://github.com/test111ddff-hash/mobile-mcp-ai/issues",
    },
    # 明确列出所有包，确保在 mobile_mcp 命名空间下
    packages=[
        'mobile_mcp',
        'mobile_mcp.core',
        'mobile_mcp.core.utils',
        'mobile_mcp.mcp_tools',
        'mobile_mcp.utils',
    ],
    # 将 mobile_mcp 映射到当前目录
    package_dir={'mobile_mcp': '.'},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=[
        # 核心依赖（基础工具必需）
        "uiautomator2>=2.16.0",
        "adbutils>=1.2.0",
        "Pillow>=10.0.0",
        "mcp>=0.9.0",
        "python-dotenv>=1.0.0",  # 用于读取 .env 配置
    ],
    extras_require={
        # AI 功能（可选）- 智能工具需要
        'ai': [
            'dashscope>=1.10.0',  # 通义千问（推荐）
            'openai>=1.0.0',      # OpenAI
            'anthropic>=0.3.0',   # Claude
        ],
        # 测试相关（可选）
        'test': [
            'pytest>=8.0.0',
            'pytest-asyncio>=0.21.0',
            'allure-pytest>=2.13.0',
        ],
        # 开发工具（可选）
        'dev': [
            'pytest>=8.0.0',
            'pytest-asyncio>=0.21.0',
            'twine>=4.0.0',
            'build>=0.10.0',
        ],
        # iOS 支持（可选）
        'ios': [
            'Appium-Python-Client>=3.0.0',
        ],
        # H5 支持（可选）
        'h5': [
            'Appium-Python-Client>=3.0.0',
            'selenium>=4.0.0',
        ],
        # 完整安装（包含所有功能）
        'all': [
            'dashscope>=1.10.0',
            'openai>=1.0.0',
            'anthropic>=0.3.0',
            'Appium-Python-Client>=3.0.0',
            'selenium>=4.0.0',
            'pytest>=8.0.0',
            'pytest-asyncio>=0.21.0',
            'allure-pytest>=2.13.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'mobile-mcp=mobile_mcp.mcp_tools.mcp_server:main',
        ],
    },
    keywords=[
        "mobile",
        "automation",
        "testing",
        "android",
        "ios",
        "mcp",
        "ai",
        "pytest",
        "cursor",
    ],
    include_package_data=True,
    zip_safe=False,
)


