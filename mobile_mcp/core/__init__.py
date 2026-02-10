"""
Compatibility shim for `mobile_mcp.core` when running from source.

This package forwards symbol-level imports (e.g. `mobile_mcp.core.MobileClient`)
to the real implementations under the top-level `core` package, but does NOT
import `core` as a package to avoid relative-import issues.

Strategy: rewrite __path__ of this package (and the parent `mobile_mcp` +
sibling `mobile_mcp.utils`) so that Python's standard import machinery
resolves every relative import against the real source directories.
"""

import sys
import types
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_CORE_DIR = _PROJECT_ROOT / "core"
_UTILS_DIR = _PROJECT_ROOT / "utils"

# ── 1. 让 mobile_mcp 的 __path__ 包含项目根，使 from ..utils 可解析 ──
import mobile_mcp as _top
if str(_PROJECT_ROOT) not in _top.__path__:
    _top.__path__.insert(0, str(_PROJECT_ROOT))

# ── 2. 注册 mobile_mcp.utils 包（指向项目根下的 utils/）──
if "mobile_mcp.utils" not in sys.modules:
    _utils_pkg = types.ModuleType("mobile_mcp.utils")
    _utils_pkg.__path__ = [str(_UTILS_DIR)]
    _utils_pkg.__package__ = "mobile_mcp.utils"
    sys.modules["mobile_mcp.utils"] = _utils_pkg

# ── 3. 让当前包（mobile_mcp.core）的 __path__ 指向真正的 core/ 目录 ──
__path__ = [str(_CORE_DIR)]
__package__ = "mobile_mcp.core"

# ── 4. 延迟导出（避免在 __init__ 中触发整个导入链，使用者按需 import）──
__all__ = ["MobileClient", "DeviceManager"]


def __getattr__(name: str):
    """按需导入，避免 __init__.py 加载时就触发全部依赖"""
    if name == "MobileClient":
        from mobile_mcp.core.mobile_client import MobileClient
        return MobileClient
    if name == "DeviceManager":
        from mobile_mcp.core.device_manager import DeviceManager
        return DeviceManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


