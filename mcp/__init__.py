"""
Mobile MCP Server Package
"""
# 延迟导入，避免与系统的 mcp 包冲突
def __getattr__(name):
    if name == 'MobileMCPServer':
        from .mcp_server import MobileMCPServer
        return MobileMCPServer
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['MobileMCPServer']


