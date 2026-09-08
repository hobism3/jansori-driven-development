"""Make the plugin's bundled client importable and expose the repo root for U3 tests.

U3 (capsule-normalizer) reuses the U2 common client (plugin/scripts/jansori_client.py)
for its server calls (Q7=A), so unit tests import it directly. The live integration test
also needs the U1 server package, so the repo root is on sys.path too.
"""
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
for _p in (_ROOT, os.path.join(_ROOT, "plugin", "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
