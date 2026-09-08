"""US-17 — `make verify` contract suite against a REAL running server.

Every test here drives a genuine uvicorn server bound to an ephemeral 127.0.0.1 port
(the `live_url` fixture in tests/conftest.py) through the bundled `jansori_client`
over real HTTP. A fake/in-memory Store stub is NOT accepted — this proves the actual
app serves the SPEC-8 contract end to end.

Terminology: normalize = Capsule Normalization (SPEC compaction), NOT context compaction.
"""
from __future__ import annotations

import pytest

pytest.importorskip("uvicorn")
import jansori_client as jc  # noqa: E402 (path via conftest)

T = 5000


def _seed_parent_child():
    assert jc.act_register("child", "rc", name="Child", description="d", body="child body",
                           refs_children=[], timeout_ms=T)["ok"]
    assert jc.act_register("parent", "rp", name="Parent", description="d", body="parent body",
                           refs_children=["child"], timeout_ms=T)["ok"]


def test_health_served_by_real_server(live_url):
    r = jc.request("GET", "/health", timeout_ms=T)
    assert r["ok"] and r["data"]["status"] == "ok"


def test_register_index_load_refs(live_url):
    _seed_parent_child()
    idx = jc.act_index(None, T)
    assert idx["ok"]
    ids = {e["skill_id"] for e in idx["data"]["entries"]}
    assert {"child", "parent"} <= ids
    loaded = jc.act_load("parent", "sess", T)
    assert loaded["ok"]
    child = next(x for x in loaded["data"]["children"] if x["skill_id"] == "child")
    assert child["absent"] is False


def test_nag_threshold_then_normalize(live_url):
    jc.act_register("sk", "r0", name="S", description="d", body="base", refs_children=[],
                    timeout_ms=T)
    v, due = 1, False
    ids = []
    for i in range(1, 4):
        r = jc.act_nag("sk", f"rule{i}", f"n{i}", base_version=v, timeout_ms=T)
        assert r["ok"], r
        v, due = r["data"]["new_version"], r["data"]["normalize_due"]
    assert due is True  # normalize_due latched at 3
    got = jc.act_get("sk", T)
    ids = [c["id"] for c in got["data"]["corrections"]]
    out = jc.act_normalize("sk", base_version=v, new_body="condensed",
                           merged_correction_ids=ids, request_id="z1", timeout_ms=T)
    assert out["ok"] and out["data"]["capsule"]["corrections"] == []


def test_error_contract_matrix(live_url):
    jc.act_register("sk", "r0", name="S", description="d", body="base", refs_children=[],
                    timeout_ms=T)
    # stale (409)
    stale = jc.act_nag("sk", "x", "ns", base_version=0, timeout_ms=T)
    assert stale["ok"] is False and stale["code"] == "STALE_BASE_VERSION" and stale["status"] == 409
    # over-length (413)
    over = jc.act_nag("sk", "y" * 10001, "no", base_version=1, timeout_ms=T)
    assert over["ok"] is False and over["code"] == "OVER_LENGTH" and over["status"] == 413
    # unknown skill get -> SKILL_ABSENT (404)
    absent = jc.act_get("nope", T)
    assert absent["ok"] is False and absent["code"] == "SKILL_ABSENT" and absent["status"] == 404
    # duplicate registration (409)
    dup = jc.act_register("sk", "rdup", name="S", description="d", body="b2",
                          refs_children=[], timeout_ms=T)
    assert dup["ok"] is False and dup["code"] == "DUPLICATE_REGISTRATION"
    # preservation failed (422): unknown merged id
    v = jc.act_get("sk", T)["data"]["version"]
    pf = jc.act_normalize("sk", base_version=v, new_body="c",
                          merged_correction_ids=["ghost"], request_id="zpf", timeout_ms=T)
    assert pf["ok"] is False and pf["code"] == "PRESERVATION_FAILED" and pf["status"] == 422
    # resolve-target with no scope -> NEEDS_CONFIRMATION (409)
    rt = jc.act_resolve_target(None, "empty-session", T)
    assert rt["ok"] is False and rt["code"] == "NEEDS_CONFIRMATION"


def test_protected_change_over_http(live_url):
    jc.act_register("sk", "r0", name="old", description="d", body="b", refs_children=[],
                    timeout_ms=T)
    # denied without approval (403)
    denied = jc.act_protected_change("sk", "name", "new", "p1", approval_flag=False,
                                     base_version=1, timeout_ms=T)
    assert denied["ok"] is False and denied["code"] == "PROTECTED_CHANGE_DENIED" and denied["status"] == 403
    # approved succeeds
    ok = jc.act_protected_change("sk", "name", "new", "p2", approval_flag=True,
                                 base_version=1, timeout_ms=T)
    assert ok["ok"] and ok["data"]["capsule"]["name"] == "new"


def test_dev29_dev32_approval_stale_and_retry_idempotent(live_url):
    """DEV-29: approval does NOT bypass the stale guard. DEV-32: approve->retry with the
    same request_id is counted exactly once."""
    jc.act_register("sk", "r0", name="old", description="d", body="b", refs_children=[],
                    timeout_ms=T)
    # approved but STALE base_version -> still rejected (I-04 not bypassed by approval)
    stale = jc.act_protected_change("sk", "name", "new", "pc-stale", approval_flag=True,
                                    base_version=0, timeout_ms=T)
    assert stale["ok"] is False and stale["code"] == "STALE_BASE_VERSION"
    # approve -> commit at correct base
    first = jc.act_protected_change("sk", "name", "new", "pc-retry", approval_flag=True,
                                    base_version=1, timeout_ms=T)
    assert first["ok"] and first["data"]["new_version"] == 2
    # retry with SAME request_id (network-retry) -> idempotent replay, no double bump
    retry = jc.act_protected_change("sk", "name", "new", "pc-retry", approval_flag=True,
                                    base_version=1, timeout_ms=T)
    assert retry["ok"] and retry["data"]["idempotent_replay"] is True
    assert retry["data"]["new_version"] == 2
    assert jc.act_get("sk", T)["data"]["version"] == 2  # exactly one commit


def test_client_refuses_non_loopback_url(live_url, monkeypatch):
    """SPEC 5 client-side defense: the bundled client refuses a non-loopback JANSORI_URL."""
    monkeypatch.setenv("JANSORI_URL", "http://192.168.1.50:8765")
    with pytest.raises(ValueError):
        jc.act_index(None, T)
