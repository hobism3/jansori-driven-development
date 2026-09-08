"""U1 API unit tests: endpoint routing, structured errors, request_id required."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from server.app.main import create_app
from server.app.routes import Container


@pytest.fixture
def client():
    # fresh container per test (empty in-memory store, Q9)
    return TestClient(create_app(Container.build()))


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_register_load_index_flow(client):
    r = client.post("/skills/register", json={
        "skill_id": "s1", "name": "S1", "description": "d", "body": "do X",
        "refs_children": [], "assets": [], "request_id": "r1",
    })
    assert r.status_code == 200, r.text
    assert r.json()["capsule"]["version"] == 1

    idx = client.get("/skills/index").json()["entries"]
    assert any(e["skill_id"] == "s1" for e in idx)

    loaded = client.post("/skills/s1/load", json={"session_id": "sess"}).json()
    assert loaded["parent"]["skill_id"] == "s1"


def test_get_absent_skill_is_404_skill_absent(client):
    r = client.get("/skills/nope")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "SKILL_ABSENT"


def test_duplicate_registration_conflict(client):
    payload = {"skill_id": "d1", "body": "b", "request_id": "r1"}
    assert client.post("/skills/register", json=payload).status_code == 200
    r = client.post("/skills/register", json={**payload, "request_id": "r2"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "DUPLICATE_REGISTRATION"


def test_request_id_required_on_write(client):
    # missing request_id -> pydantic validation (422)
    r = client.post("/skills/register", json={"skill_id": "x", "body": "b"})
    assert r.status_code == 422


def test_nag_then_stale(client):
    client.post("/skills/register", json={"skill_id": "s2", "body": "b", "request_id": "r1"})
    ok = client.post("/skills/s2/nag", json={"correction_text": "be terse", "base_version": 1, "request_id": "n1"})
    assert ok.status_code == 200
    assert ok.json()["new_version"] == 2
    stale = client.post("/skills/s2/nag", json={"correction_text": "x", "base_version": 1, "request_id": "n2"})
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "STALE_BASE_VERSION"


def test_normalize_endpoint(client):
    client.post("/skills/register", json={"skill_id": "s3", "body": "base", "request_id": "r1"})
    v = 1
    for i in range(1, 4):
        resp = client.post("/skills/s3/nag", json={"correction_text": f"rule{i}", "base_version": v, "request_id": f"n{i}"})
        v = resp.json()["new_version"]
    assert resp.json()["normalize_due"] is True
    corr_ids = [c["id"] for c in client.get("/skills/s3").json()["corrections"]]
    # U1-reopen redesign: a CONDENSED/paraphrased body (NOT verbatim) is now accepted;
    # preservation is validated by the merged-id declaration + length, not substring survival.
    merged = "condensed guidance"
    norm = client.post(
        "/skills/s3/normalize",
        json={"base_version": v, "new_body": merged, "request_id": "norm1",
              "merged_correction_ids": corr_ids},
    )
    assert norm.status_code == 200, norm.text
    assert norm.json()["capsule"]["corrections"] == []
    assert norm.json()["capsule"]["body"] == "condensed guidance"


def test_normalize_rejects_unknown_correction_id(client):
    # redesign: declaring a correction id that isn't present at base -> PRESERVATION_FAILED.
    client.post("/skills/register", json={"skill_id": "s3b", "body": "base", "request_id": "r1"})
    v = 1
    for i in range(1, 4):
        resp = client.post("/skills/s3b/nag", json={"correction_text": f"rule{i}", "base_version": v, "request_id": f"n{i}"})
        v = resp.json()["new_version"]
    bad = client.post(
        "/skills/s3b/normalize",
        json={"base_version": v, "new_body": "x", "request_id": "norm1",
              "merged_correction_ids": ["does-not-exist"]},
    )
    assert bad.status_code == 422, bad.text
    assert bad.json()["error"]["code"] == "PRESERVATION_FAILED"


def test_protected_change_denied_without_approval(client):
    client.post("/skills/register", json={"skill_id": "s4", "body": "b", "request_id": "r1"})
    r = client.post("/skills/s4/protected-change", json={
        "field": "name", "new_value": "New", "base_version": 1,
        "approval_flag": False, "request_id": "p1",
    })
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "PROTECTED_CHANGE_DENIED"


def test_resolve_target_endpoint(client):
    # load parent+child into a session, then resolve
    client.post("/skills/register", json={"skill_id": "c", "body": "b", "request_id": "r0"})
    client.post("/skills/register", json={"skill_id": "p", "body": "b", "refs_children": ["c"], "request_id": "r1"})
    client.post("/skills/p/load", json={"session_id": "sess"})
    ok = client.get("/skills/resolve-target", params={"hint": "p", "session_id": "sess"})
    assert ok.status_code == 200
    assert ok.json()["target"] == "p"
    ambiguous = client.get("/skills/resolve-target", params={"hint": "zzz", "session_id": "sess"})
    assert ambiguous.status_code == 409
    assert ambiguous.json()["error"]["code"] == "NEEDS_CONFIRMATION"


def test_protected_change_refs_upward_depth_limit_api(client):
    # B1 over HTTP: N is a child of P; giving N children must be refused.
    for sid in ("x", "n"):
        client.post("/skills/register", json={"skill_id": sid, "body": "b", "request_id": f"r-{sid}"})
    client.post("/skills/register", json={"skill_id": "pp", "body": "b", "refs_children": ["n"], "request_id": "r-pp"})
    r = client.post("/skills/n/protected-change", json={
        "field": "refs_children", "new_value": ["x"], "base_version": 1,
        "approval_flag": True, "request_id": "pc1",
    })
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "DEPTH_LIMIT"


def test_cross_skill_request_id_rejected_api(client):
    client.post("/skills/register", json={"skill_id": "a", "body": "b", "request_id": "R"})
    r = client.post("/skills/register", json={"skill_id": "b", "body": "b", "request_id": "R"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_depth_limit_on_register(client):
    # child with its own child
    client.post("/skills/register", json={"skill_id": "gc", "body": "b", "request_id": "r0"})
    client.post("/skills/register", json={"skill_id": "child", "body": "b", "refs_children": ["gc"], "request_id": "r1"})
    # linking child (which has gc) under parent -> grandchild -> DEPTH_LIMIT
    r = client.post("/skills/register", json={"skill_id": "parent", "body": "b", "refs_children": ["child"], "request_id": "r2"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "DEPTH_LIMIT"
