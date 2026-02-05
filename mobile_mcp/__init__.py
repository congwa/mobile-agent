"""
Compatibility shim for the `mobile_mcp` package when running from source.

This allows imports like:

- `import mobile_mcp`
- `from mobile_mcp.core.mobile_client import MobileClient`

to work even if the project has not been installed into site-packages.
"""

from pathlib import Path
import sys


_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Ensure the project root (which contains `core`, `utils`, `mcp_tools`, etc.)
# is on sys.path so that our shim submodules can import them.
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

