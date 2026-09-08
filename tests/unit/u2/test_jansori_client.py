"""Unit tests for the U2 common client (BR-04/07/08, D-03/D-08, I-07).

We monkeypatch urllib to simulate the U1 server so we can assert error CLASSIFICATION
(SERVER_ERROR vs SKILL_ABSENT never conflated), request shaping, and loopback enforcement
without a live server. (Live round-trip is covered in test_hooks_integration.py.)
"""
import io
import json
import urllib.error

import jansori_client as jc
import pytest


class _FakeResp:
    def __init__(self, status, body):
        self.status = status
        self._body = body.encode("utf-8") if isinstance(body, str) else body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _patch_urlopen(monkeypatch, handler):
    """handler(req, timeout) -> _FakeResp or raises urllib error."""
    captured = {}

    def fake(req, timeout=None):
        captured["req"] = req
        captured["timeout"] = timeout
        return handler(req, timeout)

    monkeypatch.setattr(jc.urllib.request, "urlopen", fake)
    return captured


def test_index_success(monkeypatch):
    _patch_urlopen(monkeypatch, lambda req, t: _FakeResp(200, json.dumps({"entries": [{"skill_id": "a", "name": "A", "description": "d"}]})))
    r = jc.act_index("s1", 2000)
    assert r["ok"] is True
    assert r["data"]["entries"][0]["skill_id"] == "a"


def test_skill_absent_maps_to_absent_not_server_error(monkeypatch):
    def h(req, t):
        raise urllib.error.HTTPError(req.full_url, 404, "nf", {}, io.BytesIO(json.dumps({"error": {"code": "SKILL_ABSENT", "message": "gone"}}).encode()))
    _patch_urlopen(monkeypatch, h)
    r = jc.act_get("missing", 2000)
    assert r["ok"] is False
    assert r["code"] == "SKILL_ABSENT"  # I-07: NOT SERVER_ERROR


def test_connection_refused_is_server_error_not_absent(monkeypatch):
    def h(req, t):
        raise urllib.error.URLError("connection refused")
    _patch_urlopen(monkeypatch, h)
    r = jc.act_index("s1", 500)
    assert r["ok"] is False
    assert r["code"] == "SERVER_ERROR"  # I-07: outage, not absence
    assert r["status"] == 0


def test_timeout_is_server_error(monkeypatch):
    def h(req, t):
        raise TimeoutError("timed out")
    _patch_urlopen(monkeypatch, h)
    r = jc.act_load("x", "s1", 100)
    assert r["ok"] is False and r["code"] == "SERVER_ERROR"


def test_needs_confirmation_passthrough(monkeypatch):
    def h(req, t):
        raise urllib.error.HTTPError(req.full_url, 409, "conf", {}, io.BytesIO(json.dumps({"error": {"code": "NEEDS_CONFIRMATION", "message": "ambiguous", "detail": {"candidates": ["a", "b"]}}}).encode()))
    _patch_urlopen(monkeypatch, h)
    r = jc.act_resolve_target("?", "s1", 2000)
    assert r["ok"] is False and r["code"] == "NEEDS_CONFIRMATION"
    assert r["detail"]["candidates"] == ["a", "b"]


def test_nag_reads_base_version_then_posts(monkeypatch):
    calls = []

    def h(req, t):
        calls.append((req.method, req.full_url))
        if req.method == "GET":
            return _FakeResp(200, json.dumps({"skill_id": "s", "version": 7}))
        # POST nag: echo the sent body so we can assert base_version was filled in
        body = json.loads(req.data.decode())
        assert body["base_version"] == 7
        assert body["request_id"] == "rid-1"
        return _FakeResp(200, json.dumps({"version": 8, "normalize_due": False}))

    _patch_urlopen(monkeypatch, h)
    r = jc.act_nag("s", "no emojis", "rid-1", base_version=None, timeout_ms=2000)
    assert r["ok"] is True and r["data"]["version"] == 8
    assert calls[0][0] == "GET" and calls[1][0] == "POST"  # read-then-write


def test_request_id_reused_on_retry_is_caller_controlled(monkeypatch):
    sent = []

    def h(req, t):
        sent.append(json.loads(req.data.decode())["request_id"])
        return _FakeResp(200, json.dumps({"version": 2}))

    _patch_urlopen(monkeypatch, h)
    jc.act_nag("s", "x", "same-rid", base_version=1, timeout_ms=2000)
    jc.act_nag("s", "x", "same-rid", base_version=1, timeout_ms=2000)
    assert sent == ["same-rid", "same-rid"]  # client transmits the SAME id (I-05 retry)


def test_non_loopback_url_refused(monkeypatch):
    monkeypatch.setenv("JANSORI_URL", "http://10.0.0.5:8765")
    with pytest.raises(ValueError):
        jc.request("GET", "/skills/index")  # BR-11.1


def test_env_defaults():
    assert jc.default_timeout_ms() >= 1
    assert jc.base_url().startswith("http://127.0.0.1")
