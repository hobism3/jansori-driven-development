"""Hook INTEGRATION tests — real U1 server over a real loopback socket (I-08 measured).

This closes the gap unit tests can't: the UserPromptSubmit hook subprocess makes a REAL HTTP
call to a REAL running U1 app and we assert (a) real index injection, (b) fail-open when the
server is stopped, (c) fail-open within the timeout budget against a HANGING socket.

Still NOT covered here (host-runtime facts, verified live at U4): Claude Code actually firing
the hook and injecting `additionalContext` into the model. See README-u2 residual checklist.
"""
import json
import os
import socket
import subprocess
import sys
import threading
import time

import httpx
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
HOOK_UPS = os.path.join(ROOT, "plugin", "hooks", "user_prompt_submit.py")

uvicorn = pytest.importorskip("uvicorn")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from server.app.main import create_app  # noqa: E402


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    return port


class _ServerThread:
    def __init__(self, app, port):
        self._config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        self._server = uvicorn.Server(self._config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)

    def __enter__(self):
        self._thread.start()
        for _ in range(100):
            if self._server.started:
                break
            time.sleep(0.05)
        assert self._server.started, "uvicorn did not start"
        return self

    def __exit__(self, *a):
        self._server.should_exit = True
        self._thread.join(timeout=5)


def _run_hook(url, timeout_ms=2000, session_id="s1"):
    env = dict(os.environ)
    env["JANSORI_URL"] = url
    env["JANSORI_HOOK_TIMEOUT_MS"] = str(timeout_ms)
    return subprocess.run([sys.executable, HOOK_UPS],
                          input=json.dumps({"session_id": session_id, "prompt": "hi"}),
                          capture_output=True, text=True, encoding="utf-8", env=env, timeout=30)


def test_hook_injects_real_index_from_live_server():
    port = _free_port()
    url = f"http://127.0.0.1:{port}"
    with _ServerThread(create_app(), port):
        # register a skill so the index is non-empty
        r = httpx.post(f"{url}/skills/register",
                       json={"skill_id": "fmt", "name": "Formatter", "description": "code style",
                             "body": "no trailing whitespace", "refs_children": [], "request_id": "reg-1"},
                       timeout=5)
        assert r.status_code == 200, r.text
        p = _run_hook(url)
        assert p.returncode == 0
        out = json.loads(p.stdout)  # must be valid JSON with our shape
        ctx = out["hookSpecificOutput"]["additionalContext"]
        assert "/jansori:nag" in ctx           # preamble injected (auto-detect)
        assert "Formatter" in ctx and "fmt" in ctx  # REAL server index injected


def test_hook_failopen_when_server_stopped():
    port = _free_port()
    url = f"http://127.0.0.1:{port}"
    with _ServerThread(create_app(), port):
        pass  # server stops on exit
    p = _run_hook(url, timeout_ms=800)
    assert p.returncode == 0
    assert p.stdout.strip() == ""              # no injection, no block (I-08)


def test_hook_failopen_within_budget_on_hanging_socket():
    # A socket that accepts connections (via backlog) but NEVER responds -> read times out.
    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lsock.bind(("127.0.0.1", 0))
    lsock.listen(1)
    port = lsock.getsockname()[1]
    try:
        budget_ms = 800
        start = time.monotonic()
        p = _run_hook(f"http://127.0.0.1:{port}", timeout_ms=budget_ms)
        elapsed = time.monotonic() - start
        assert p.returncode == 0
        assert p.stdout.strip() == ""          # fail-open on hang (I-08)
        # returned near the budget, not hanging for the full 30s subprocess timeout
        assert elapsed < 10, f"hook did not fail-open promptly: {elapsed:.1f}s"
    finally:
        lsock.close()
