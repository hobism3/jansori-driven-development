"""Unit tests for the client `normalize` action added for U3 (BR-U3-05/09/11).

Monkeypatch urllib to simulate the U1 server so we can assert request shaping (path +
merged_correction_ids declaration), per-attempt request_id, and error CLASSIFICATION
(STALE / PRESERVATION_FAILED / OVER_LENGTH) without a live server. Live round-trip is in
test_normalize_integration.py.
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


def _patch(monkeypatch, handler):
    def fake(req, timeout=None):
        return handler(req, timeout)

    monkeypatch.setattr(jc.urllib.request, "urlopen", fake)


def test_normalize_posts_declaration_and_body(monkeypatch):
    captured = {}

    def h(req, t):
        captured["method"] = req.method
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode())
        return _FakeResp(200, json.dumps({"capsule": {"corrections": []}, "new_version": 5}))

    _patch(monkeypatch, h)
    r = jc.act_normalize("sk", base_version=4, new_body="condensed",
                         merged_correction_ids=["c1", "c2"], request_id="norm-1", timeout_ms=2000)
    assert r["ok"] is True and r["data"]["new_version"] == 5
    assert captured["method"] == "POST"
    assert captured["url"].endswith("/skills/sk/normalize")
    assert captured["body"] == {
        "base_version": 4, "new_body": "condensed",
        "request_id": "norm-1", "merged_correction_ids": ["c1", "c2"],
    }


def test_normalize_stale_classified(monkeypatch):
    def h(req, t):
        raise urllib.error.HTTPError(
            req.full_url, 409, "stale", {},
            io.BytesIO(json.dumps({"error": {"code": "STALE_BASE_VERSION", "message": "stale"}}).encode()))

    _patch(monkeypatch, h)
    r = jc.act_normalize("sk", 1, "x", ["c1"], "n1", 2000)
    assert r["ok"] is False and r["code"] == "STALE_BASE_VERSION"


def test_normalize_preservation_failed_classified(monkeypatch):
    def h(req, t):
        raise urllib.error.HTTPError(
            req.full_url, 422, "unproc", {},
            io.BytesIO(json.dumps({"error": {"code": "PRESERVATION_FAILED", "message": "bad ids"}}).encode()))

    _patch(monkeypatch, h)
    r = jc.act_normalize("sk", 4, "x", ["does-not-exist"], "n1", 2000)
    assert r["ok"] is False and r["code"] == "PRESERVATION_FAILED"


def test_normalize_over_length_classified(monkeypatch):
    def h(req, t):
        raise urllib.error.HTTPError(
            req.full_url, 422, "unproc", {},
            io.BytesIO(json.dumps({"error": {"code": "OVER_LENGTH", "message": "too long"}}).encode()))

    _patch(monkeypatch, h)
    r = jc.act_normalize("sk", 4, "x" * 99999, ["c1"], "n1", 2000)
    assert r["ok"] is False and r["code"] == "OVER_LENGTH"


def test_normalize_server_down_is_server_error_not_absent(monkeypatch):
    def h(req, t):
        raise urllib.error.URLError("connection refused")

    _patch(monkeypatch, h)
    r = jc.act_normalize("sk", 4, "x", ["c1"], "n1", 500)
    assert r["ok"] is False and r["code"] == "SERVER_ERROR" and r["status"] == 0  # I-07


def test_dispatch_generates_fresh_request_id_per_attempt(monkeypatch):
    """BR-U3-09: without --request-id, each invocation (attempt) gets a new uuid."""
    sent = []

    def h(req, t):
        sent.append(json.loads(req.data.decode())["request_id"])
        return _FakeResp(200, json.dumps({"capsule": {"corrections": []}, "new_version": 2}))

    _patch(monkeypatch, h)
    parser = jc._build_parser()
    for _ in range(2):
        args = parser.parse_args(["normalize", "--id", "sk", "--base-version", "1",
                                  "--new-body", "b", "--merged-id", "c1"])
        jc.dispatch(args)
    assert len(sent) == 2 and sent[0] != sent[1]  # distinct attempts -> distinct ids


def test_dispatch_reuses_request_id_when_supplied(monkeypatch):
    """Same-attempt network resend reuses the SAME id (I-05 idempotent replay)."""
    sent = []

    def h(req, t):
        sent.append(json.loads(req.data.decode())["request_id"])
        return _FakeResp(200, json.dumps({"capsule": {"corrections": []}, "new_version": 2}))

    _patch(monkeypatch, h)
    parser = jc._build_parser()
    for _ in range(2):
        args = parser.parse_args(["--request-id", "same", "normalize", "--id", "sk",
                                  "--base-version", "1", "--new-body", "b", "--merged-id", "c1"])
        jc.dispatch(args)
    assert sent == ["same", "same"]


def test_cli_requires_merged_id_and_a_body_source():
    parser = jc._build_parser()
    with pytest.raises(SystemExit):  # missing --merged-id
        parser.parse_args(["normalize", "--id", "sk", "--base-version", "1", "--new-body", "b"])
    with pytest.raises(SystemExit):  # missing body source (neither --new-body nor --new-body-stdin)
        parser.parse_args(["normalize", "--id", "sk", "--base-version", "1", "--merged-id", "c1"])
