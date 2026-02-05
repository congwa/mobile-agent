"""
Forwarder module so that `from mobile_mcp.core.mobile_client import MobileClient`
works when running from source.
"""

from pathlib import Path
import importlib.util
import sys


# 项目根目录：.../mobile_mcp
_PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _load_impl():
    """
    Load the real `core.mobile_client` module and return its MobileClient.

    We avoid importing it as `core.mobile_client` to prevent Python from
    treating it as part of the `core` package (which would break its
    relative imports like `from ..utils ...`).
    """
    impl_path = _PROJECT_ROOT / "core" / "mobile_client.py"
    spec = importlib.util.spec_from_file_location(
        "mobile_mcp._impl_core_mobile_client", impl_path
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.MobileClient


MobileClient = _load_impl()

__all__ = ["MobileClient"]


