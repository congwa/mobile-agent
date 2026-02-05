"""
Forwarder module so that `from mobile_mcp.core.basic_tools_lite import BasicMobileToolsLite`
works when running from source.
"""

from pathlib import Path
import sys


_PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from core.basic_tools_lite import *  # noqa: F401,F403

