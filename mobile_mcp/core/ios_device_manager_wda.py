"""
Forwarder module so that `from mobile_mcp.core.ios_device_manager_wda import IOSDeviceManagerWDA`
works when running from source.
"""

from pathlib import Path
import sys


_PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from core.ios_device_manager_wda import *  # noqa: F401,F403

