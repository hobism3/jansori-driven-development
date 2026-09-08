"""Capsule Normalization INTEGRATION tests — real U1 server over a real loopback socket.

Runs the actual U1 FastAPI app in a uvicorn background thread on an ephemeral 127.0.0.1
port and drives it through the bundled client (the same code path the U3 subagent uses).
This proves the full HTTP round-trip of the redesigned normalize contract:
commit-with-condensed-body / STALE / PRESERVATION_FAILED / OVER_LENGTH / partial-merge.

NOT covered here (host-runtime facts, U4 residual, F-04): Claude Code actually LAUNCHING the
capsule-normalizer subagent on `normalize_due`, and the model's merge QUALITY. See README-u3.
"""
import os
import socket
import sys
import threading
import time

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

uvicorn = pytest.importorskip("uvicorn")
import jansori_client as jc  # noqa: E402  (path set by conftest)
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


@pytest.fixture()
def live_url(monkeypatch):
    port = _free_port()
    with _ServerThread(create_app(), port):
        url = f"http://127.0.0.1:{port}"
        monkeypatch.setenv("JANSORI_URL", url)
        yield url


def _register_with_three_nags(skill_id="sk"):
    assert jc.act_register(skill_id, "r1", name="N", description="d", body="base rules",
                           refs_children=[], timeout_ms=5000)["ok"]
    v = 1
    for i in range(1, 4):
        r = jc.act_nag(skill_id, f"rule{i}", f"n{i}", base_version=v, timeout_ms=5000)
        assert r["ok"], r
        v = r["data"]["new_version"]
    got = jc.act_get(skill_id, 5000)
    assert got["ok"], got
    corr_ids = [c["id"] for c in got["data"]["corrections"]]
    assert len(corr_ids) == 3
    return v, corr_ids


def test_commit_with_condensed_body_succeeds(live_url):
    v, corr_ids = _register_with_three_nags()
    r = jc.act_normalize("sk", base_version=v, new_body="condensed guidance",
                         merged_correction_ids=corr_ids, request_id="norm1", timeout_ms=5000)
    assert r["ok"], r
    assert r["data"]["capsule"]["corrections"] == []
    assert r["data"]["capsule"]["body"] == "condensed guidance"
    assert r["data"]["new_version"] == v + 1


def test_stale_base_version(live_url):
    v, corr_ids = _register_with_three_nags()
    # submit against a stale base_version (v-1) -> STALE
    r = jc.act_normalize("sk", base_version=v - 1, new_body="condensed",
                         merged_correction_ids=corr_ids, request_id="norm1", timeout_ms=5000)
    assert r["ok"] is False and r["code"] == "STALE_BASE_VERSION"


def test_unknown_correction_id_preservation_failed(live_url):
    v, _ = _register_with_three_nags()
    r = jc.act_normalize("sk", base_version=v, new_body="condensed",
                         merged_correction_ids=["does-not-exist"], request_id="norm1", timeout_ms=5000)
    assert r["ok"] is False and r["code"] == "PRESERVATION_FAILED"  # HTTP 422


def test_over_length_rejected(live_url):
    v, corr_ids = _register_with_three_nags()
    r = jc.act_normalize("sk", base_version=v, new_body="x" * 10001,
                         merged_correction_ids=corr_ids, request_id="norm1", timeout_ms=5000)
    assert r["ok"] is False and r["code"] == "OVER_LENGTH"


def test_partial_merge_carries_forward_undeclared(live_url):
    v, corr_ids = _register_with_three_nags()
    keep = corr_ids[-1]
    r = jc.act_normalize("sk", base_version=v, new_body="two merged",
                         merged_correction_ids=corr_ids[:-1], request_id="norm1", timeout_ms=5000)
    assert r["ok"], r
    remaining = [c["id"] for c in r["data"]["capsule"]["corrections"]]
    assert remaining == [keep]


def test_repeated_abandonment_is_expected_safe(live_url):
    """Issue 3: after a failed submit (e.g. stale), the content is unchanged and a retry
    can succeed against the fresh base. Bounded, I-11-safe — abandonment is not corruption."""
    v, corr_ids = _register_with_three_nags()
    stale = jc.act_normalize("sk", base_version=v - 1, new_body="c",
                             merged_correction_ids=corr_ids, request_id="a1", timeout_ms=5000)
    assert stale["ok"] is False and stale["code"] == "STALE_BASE_VERSION"
    # content unchanged: latest still has the 3 corrections and version v
    got = jc.act_get("sk", 5000)
    assert got["data"]["version"] == v and len(got["data"]["corrections"]) == 3
    # retry against fresh base with a NEW attempt id succeeds
    ok = jc.act_normalize("sk", base_version=v, new_body="c",
                          merged_correction_ids=corr_ids, request_id="a2", timeout_ms=5000)
    assert ok["ok"] and ok["data"]["capsule"]["corrections"] == []
