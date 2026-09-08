"""Shared U4 test fixtures — centralized live-server harness + Hypothesis config.

This root `tests/conftest.py` is loaded by every test package (u1..u3 unit tests keep
their own path-setup conftests; those remain untouched — U4 does not refactor CLOSED
units). It provides:

- sys.path setup so `server.*` and the bundled `jansori_client` import from anywhere
  under tests/ (pbt/, golden/, verify/).
- `live_url`   : a REAL uvicorn server bound to an ephemeral 127.0.0.1 port, torn down
  after the test. Used by tests/verify (make verify) — a fake Store is NOT accepted.
- `container` / `client` : an in-process FastAPI TestClient with a fresh empty store
  (fast; for golden/pbt that don't need a socket).
- Hypothesis profiles + seed/reproducibility logging (PBT-08).

Terminology: "normalize" = Capsule Normalization (SPEC "compaction"), NOT Claude Code
context compaction.
"""
from __future__ import annotations

import os
import socket
import sys
import threading
import time

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _p in (_ROOT, os.path.join(_ROOT, "plugin", "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# --------------------------------------------------------------------------- #
# Hypothesis profiles (PBT-08: shrinking on, seed logged / reproducible).
# --------------------------------------------------------------------------- #
try:
    from hypothesis import settings, HealthCheck

    # "dev": rich exploration locally. "ci": more examples, deterministic-friendly.
    settings.register_profile(
        "dev",
        max_examples=int(os.environ.get("JANSORI_HYPOTHESIS_MAX_EXAMPLES", "50")),
        print_blob=True,  # print an @reproduce_failure blob on failure (PBT-08 reproducibility)
        deadline=None,    # stateful/live tests can exceed the default per-example deadline
        suppress_health_check=[HealthCheck.too_slow],
    )
    settings.register_profile(
        "ci",
        max_examples=int(os.environ.get("JANSORI_HYPOTHESIS_MAX_EXAMPLES", "150")),
        print_blob=True,
        deadline=None,
        derandomize=os.environ.get("JANSORI_HYPOTHESIS_DERANDOMIZE", "0") == "1",
        suppress_health_check=[HealthCheck.too_slow],
    )
    settings.load_profile(os.environ.get("JANSORI_HYPOTHESIS_PROFILE", "dev"))
    _HYPOTHESIS = True
except Exception:  # hypothesis not installed → pbt tests will importorskip
    _HYPOTHESIS = False


def pytest_report_header(config):
    """PBT-08: surface the active profile + how to reproduce failures, every run."""
    profile = os.environ.get("JANSORI_HYPOTHESIS_PROFILE", "dev")
    if not _HYPOTHESIS:
        return "hypothesis: NOT INSTALLED (pbt tests skipped)"
    return (
        f"hypothesis profile={profile} print_blob=True "
        "(on failure a @reproduce_failure blob + seed are printed; "
        "replay with `pytest --hypothesis-seed=<seed>`)"
    )


# --------------------------------------------------------------------------- #
# Real loopback server harness (US-17 / make verify).
# --------------------------------------------------------------------------- #
def free_loopback_port() -> int:
    """Reserve an ephemeral 127.0.0.1 port (bind-to-0)."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class LiveServer:
    """Runs the real U1 FastAPI app in a uvicorn background thread on loopback.

    Centralizes the harness previously duplicated inline in
    tests/unit/u2/test_hooks_integration.py and tests/unit/u3/test_normalize_integration.py.
    Binds ONLY to 127.0.0.1 (SPEC 5); a non-loopback host would be refused by the app.
    """

    def __init__(self, app, port: int) -> None:
        import uvicorn

        self.port = port
        self.url = f"http://127.0.0.1:{port}"
        self._config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        self._server = uvicorn.Server(self._config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)

    def __enter__(self) -> "LiveServer":
        self._thread.start()
        for _ in range(200):  # up to ~10s
            if self._server.started:
                break
            time.sleep(0.05)
        assert self._server.started, "uvicorn did not start"
        return self

    def __exit__(self, *exc) -> None:
        self._server.should_exit = True
        self._thread.join(timeout=5)


@pytest.fixture()
def live_url(monkeypatch):
    """A real, freshly-started, empty U1 server on an ephemeral loopback port.

    Sets JANSORI_URL so the bundled jansori_client targets this instance. This is a
    genuine socket server — proves `make verify` runs the real app, not a fake Store.
    """
    pytest.importorskip("uvicorn")
    from server.app.main import create_app

    port = free_loopback_port()
    with LiveServer(create_app(), port) as srv:
        monkeypatch.setenv("JANSORI_URL", srv.url)
        yield srv.url


@pytest.fixture()
def container():
    """A fresh in-process Container (empty store) for fast golden/pbt tests."""
    from server.app.routes import Container

    return Container.build()


@pytest.fixture()
def client(container):
    """In-process FastAPI TestClient over a fresh empty store."""
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    from server.app.main import create_app

    return TestClient(create_app(container))
