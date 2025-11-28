#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mobile MCP Server - 简化版（向后兼容代理）

这个文件现在只是一个代理，自动设置为简化模式并调用主 MCP Server。
保留此文件是为了向后兼容使用简化版配置的用户。

建议：新用户直接使用 mcp_server.py 并通过环境变量 MOBILE_MCP_MODE 控制模式。
"""

import os
import sys

# 设置为简化模式
os.environ["MOBILE_MCP_MODE"] = "simple"

# 导入并运行主 MCP Server
from .mcp_server import main

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
