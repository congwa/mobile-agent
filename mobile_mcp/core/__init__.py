"""
Compatibility shim for `mobile_mcp.core` when running from source.

This package forwards symbol-level imports (e.g. `mobile_mcp.core.MobileClient`)
to the real implementations under the top-level `core` package, but does NOT
import `core` as a package to avoid relative-import issues.
"""

from pathlib import Path
import sys


_PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Re-export key symbols explicitly
from core.mobile_client import MobileClient  # noqa: F401
from core.device_manager import DeviceManager  # noqa: F401

__all__ = ["MobileClient", "DeviceManager"]


