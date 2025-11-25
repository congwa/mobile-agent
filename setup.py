#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mobile MCP Enhanced - Python包发布配置

安装：
    pip install -e .

发布到PyPI：
    python setup.py sdist bdist_wheel
    twine upload dist/*
"""
from setuptools import setup, find_packages
from pathlib import Path

# 读取README
readme_file = Path(__file__).parent / "README.md"
if not readme_file.exists():
    readme_file = Path(__file__).parent / "README_COMBINED.md"
long_description = readme_file.read_text(encoding='utf-8') if readme_file.exists() else ""

# 读取requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file, 'r', encoding='utf-8') as f:
        requirements = [
            line.strip() 
            for line in f 
            if line.strip() and not line.startswith('#')
        ]

setup(
    name="mobile-mcp-ai",
    version="1.0.1",
    description="移动端自动化测试框架 - 支持Android和iOS，集成AI增强功能",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="douzi",
    author_email="1492994674@qq.com",
    url="https://github.com/test111ddff-hash/mobile-mcp-ai",
    packages=["mobile_mcp"] + [f"mobile_mcp.{pkg}" for pkg in find_packages(where=".", exclude=["tests", "examples", "docs"])],
    package_dir={"mobile_mcp": "."},
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "ios": [
            "Appium-Python-Client>=3.0.0",
        ],
        "h5": [
            "Appium-Python-Client>=3.0.0",
            "selenium>=4.0.0",
        ],
        "ai": [
            "anthropic>=0.18.0",  # Claude
            "openai>=1.0.0",  # OpenAI
            "google-generativeai>=0.3.0",  # Gemini
        ],
        "all": [
            "Appium-Python-Client>=3.0.0",
            "selenium>=4.0.0",
            "anthropic>=0.18.0",
            "openai>=1.0.0",
            "google-generativeai>=0.3.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "mobile-mcp=mobile_mcp.mcp.mcp_server:main",
        ],
    },
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
    keywords="mobile automation testing android ios mcp ai",
    project_urls={
        "Documentation": "https://github.com/test111ddff-hash/mobile-mcp-ai",
        "Source": "https://github.com/test111ddff-hash/mobile-mcp-ai",
        "Tracker": "https://github.com/test111ddff-hash/mobile-mcp-ai/issues",
    },
  )

