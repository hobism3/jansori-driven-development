"""Example-based golden / regression tests for core Capsule paths (PBT-10 complement).

These pin CONCRETE expected values for business-critical scenarios (the general rules
are covered by tests/pbt). Case ids reference fixtures/acceptance/development-cases.json.

Covered here: DEV-02 (load+expand), DEV-13 (threshold 2 vs 3), DEV-09 (duplicate),
DEV-34 (loopback), DEV-03/DEV-44 (refs matrix), DEV-46 (ALLOW boundary), DEV-28
(content vs progress-state), and protected-change per the resolved DEV-11 field set.
"""
from __future__ import annotations

import pytest

from server.app.routes import Container
from server.domain.errors import (
    DepthLimit,
    DuplicateRegistration,
    ProtectedChangeDenied,
    ValidationError,
)
from server.domain.models import PROTECTED_FIELDS
from server.security.guard import assert_loopback


def _c():
    return Container.build()


# ----- DEV-02 : register -> load expands depth-1 child body + corrections ---- #
def test_load_expands_depth1_child():
    c = _c()
    c.skills.register({"skill_id": "child", "body": "child body", "refs_children": []},
                      request_id="rc")
    c.skills.register({"skill_id": "parent", "body": "parent body", "refs_children": ["child"]},
                      request_id="rp")
    c.nags.apply_nag("child", correction_text="child rule", base_version=1, request_id="n1")
    loaded = c.skills.load("parent", session_id="s1")
    assert loaded["parent"]["body"] == "parent body"
    child = next(x for x in loaded["children"] if x["skill_id"] == "child")
    assert child["absent"] is False
    assert "child rule" in child["corrections"]


# ----- DEV-13 : normalize_due at exactly threshold (3), not at 2 ------------- #
def test_normalize_due_latches_at_three():
    c = _c()
    c.skills.register({"skill_id": "sk", "body": "b", "refs_children": []}, request_id="r0")
    r1 = c.nags.apply_nag("sk", correction_text="a", base_version=1, request_id="n1")
    r2 = c.nags.apply_nag("sk", correction_text="b", base_version=2, request_id="n2")
    assert r1["normalize_due"] is False
    assert r2["normalize_due"] is False  # 2 corrections < 3
    r3 = c.nags.apply_nag("sk", correction_text="c", base_version=3, request_id="n3")
    assert r3["normalize_due"] is True   # 3 corrections == threshold


# ----- normalize condenses body and carries forward undeclared corrections --- #
def test_normalize_condense_and_carry_forward():
    c = _c()
    c.skills.register({"skill_id": "sk", "body": "b", "refs_children": []}, request_id="r0")
    v = 1
    for i in range(1, 4):
        v = c.nags.apply_nag("sk", correction_text=f"rule{i}", base_version=v,
                             request_id=f"n{i}")["new_version"]
    latest = c.store.get_latest("sk")
    ids = [x.id for x in latest.corrections]
    out = c.normalization.commit_normalization(
        "sk", base_version=v, new_body="condensed guidance",
        request_id="z1", merged_correction_ids=ids[:-1])  # merge first two, keep last
    assert out["capsule"]["body"] == "condensed guidance"
    remaining = [x["id"] for x in out["capsule"]["corrections"]]
    assert remaining == [ids[-1]]


# ----- DEV-09 : duplicate registration blocked ------------------------------ #
def test_duplicate_registration_blocked():
    c = _c()
    c.skills.register({"skill_id": "sk", "body": "b", "refs_children": []}, request_id="r0")
    with pytest.raises(DuplicateRegistration):
        c.skills.register({"skill_id": "sk", "body": "b2", "refs_children": []}, request_id="r1")


# ----- DEV-34 : loopback-only bind ------------------------------------------ #
@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost", "127.5.0.2"])
def test_loopback_hosts_accepted(host):
    assert_loopback(host)  # no raise


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.10", "example.com", ""])
def test_non_loopback_hosts_refused(host):
    with pytest.raises(ValidationError):
        assert_loopback(host)


# ----- DEV-03 / DEV-44 : refs matrix ---------------------------------------- #
def test_refs_self_reference_rejected():
    c = _c()
    with pytest.raises(DepthLimit):
        c.skills.register({"skill_id": "p", "body": "b", "refs_children": ["p"]}, request_id="r0")
    assert c.store.get_latest("p") is None


def test_refs_grandchild_rejected_on_register():
    c = _c()
    c.skills.register({"skill_id": "g", "body": "leaf", "refs_children": []}, request_id="rg")
    c.skills.register({"skill_id": "child", "body": "c", "refs_children": ["g"]}, request_id="rc")
    with pytest.raises(DepthLimit):  # parent -> child -> g would be depth-2
        c.skills.register({"skill_id": "p", "body": "p", "refs_children": ["child"]},
                          request_id="rp")


def test_refs_change_making_with_children_capsule_a_child_rejected():
    """DEV-44: X has children; making X a child of Y via refs-change is refused."""
    c = _c()
    c.skills.register({"skill_id": "leaf", "body": "l", "refs_children": []}, request_id="rl")
    c.skills.register({"skill_id": "x", "body": "x", "refs_children": ["leaf"]}, request_id="rx")
    c.skills.register({"skill_id": "y", "body": "y", "refs_children": []}, request_id="ry")
    with pytest.raises(DepthLimit):
        c.nags.apply_protected_change("y", field="refs_children", new_value=["x"],
                                      base_version=1, approval_flag=True, request_id="pc1")


def test_missing_and_duplicate_refs_are_tolerated():
    """Documented behavior: a missing child is not an error at register (flagged absent on
    load); duplicate refs are accepted. (Contrast with self/grandchild which ARE refused.)"""
    c = _c()
    c.skills.register({"skill_id": "child", "body": "c", "refs_children": []}, request_id="rc")
    # missing ref tolerated at register:
    c.skills.register({"skill_id": "p1", "body": "b", "refs_children": ["ghost"]},
                      request_id="rp1")
    loaded = c.skills.load("p1", session_id="s")
    ghost = next(x for x in loaded["children"] if x["skill_id"] == "ghost")
    assert ghost["absent"] is True
    # duplicate ref tolerated:
    c.skills.register({"skill_id": "p2", "body": "b", "refs_children": ["child", "child"]},
                      request_id="rp2")
    assert c.store.get_latest("p2").refs_children == ("child", "child")


# ----- DEV-46 : ALLOW boundary (permitted depth-1 must SUCCEED) ------------- #
def test_allow_depth1_register_and_refs_change_succeed():
    c = _c()
    c.skills.register({"skill_id": "b", "body": "leaf", "refs_children": []}, request_id="rb")
    # register A referencing existing leaf B (depth-1) -> OK
    out = c.skills.register({"skill_id": "a", "body": "a", "refs_children": ["b"]},
                            request_id="ra")
    assert out["capsule"]["refs_children"] == ["b"]
    # change A.refs -> [c] (c a leaf) via protected-change -> OK
    c.skills.register({"skill_id": "c", "body": "leaf2", "refs_children": []}, request_id="rc")
    changed = c.nags.apply_protected_change("a", field="refs_children", new_value=["c"],
                                            base_version=1, approval_flag=True, request_id="pc")
    assert changed["capsule"]["refs_children"] == ["c"]
    assert changed["new_version"] == 2


# ----- DEV-28 : content vs progress-state separation ------------------------ #
def test_progress_flag_toggle_does_not_change_capsule():
    c = _c()
    c.skills.register({"skill_id": "sk", "body": "body", "refs_children": []}, request_id="r0")
    before = c.store.get_latest("sk")
    c.sessions.set_progress_flag("s1", "sk", "normalize_due", True)
    c.sessions.set_progress_flag("s1", "sk", "normalize_in_progress", True)
    after = c.store.get_latest("sk")
    assert after.version == before.version
    assert after.body == before.body
    assert after.corrections == before.corrections


# ----- protected-change per resolved DEV-11 field set ----------------------- #
def test_protected_change_field_set():
    # the authoritative set (DEV-11 resolved: implemented PROTECTED_FIELDS)
    assert set(PROTECTED_FIELDS) == {"skill_id", "name", "refs_children", "protected_fields"}
    c = _c()
    c.skills.register({"skill_id": "sk", "name": "old", "body": "b", "refs_children": []},
                      request_id="r0")
    # protected field without approval -> denied
    with pytest.raises(ProtectedChangeDenied):
        c.nags.apply_protected_change("sk", field="name", new_value="new",
                                      base_version=1, approval_flag=False, request_id="p1")
    # protected field with approval -> succeeds, version+1
    out = c.nags.apply_protected_change("sk", field="name", new_value="new",
                                        base_version=1, approval_flag=True, request_id="p2")
    assert out["capsule"]["name"] == "new" and out["new_version"] == 2
    # non-protected field (description) is NOT a protected-change -> VALIDATION_ERROR
    with pytest.raises(ValidationError):
        c.nags.apply_protected_change("sk", field="description", new_value="x",
                                      base_version=2, approval_flag=True, request_id="p3")
