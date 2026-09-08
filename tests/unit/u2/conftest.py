"""Make the U2 plugin's bundled scripts/hooks importable in-process for unit tests.

(The plugin dirs are not Python packages — Claude Code invokes them as scripts — so we add
them to sys.path for the import-based tests. Subprocess tests exercise the real entry points.)
"""
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
for _p in (os.path.join(_ROOT, "plugin", "scripts"), os.path.join(_ROOT, "plugin", "hooks")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
