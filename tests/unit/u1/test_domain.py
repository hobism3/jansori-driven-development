"""U1 domain unit tests: version immutability (I-01), depth-1 (I-15), Correction (I-05/I-13)."""
from __future__ import annotations

import pytest

from server.domain.errors import DepthLimit
from server.domain.models import PROTECTED_FIELDS, Capsule, Correction
from server.domain.refs import assert_depth_one


def make_capsule(**kw) -> Capsule:
    base = dict(skill_id="s1", name="S1", description="d", body="body", version=1)
    base.update(kw)
    return Capsule(**base)


def test_version_bump_on_content_change_is_plus_one():
    c1 = make_capsule(version=1)
    c2 = c1.with_new_content(body="new body")
    assert c2.version == 2
    # original unchanged (frozen dataclass -> immutable snapshot, I-01)
    assert c1.version == 1
    assert c1.body == "body"


def test_snapshot_version_preserves_body():
    c = make_capsule(body="frozen")
    snap = c.snapshot_version(request_id="r1", origin="register")
    c2 = c.with_new_content(body="changed")
    # snapshot of old version still holds old body (I-01)
    assert snap.body_snapshot == "frozen"
    assert c2.body == "changed"


def test_protected_fields_default_fixed_set():
    c = make_capsule()
    assert c.protected_fields == PROTECTED_FIELDS
    assert set(PROTECTED_FIELDS) == {"skill_id", "name", "refs_children", "protected_fields"}


def test_correction_carries_target_seq_request_id():
    corr = Correction(id="c1", target="s1", instruction_text="be terse", request_id="r1", seq=1)
    assert corr.target == "s1"
    assert corr.seq == 1
    assert corr.request_id == "r1"


def test_depth_one_allows_children_without_grandchildren():
    # child s2 has no children -> allowed
    assert_depth_one("parent", ["s2"], get_child_refs=lambda cid: [])


def test_depth_one_rejects_grandchild():
    # child s2 already has a child g1 -> linking under parent creates a grandchild
    with pytest.raises(DepthLimit) as ei:
        assert_depth_one("parent", ["s2"], get_child_refs=lambda cid: ["g1"] if cid == "s2" else [])
    assert "violations" in ei.value.detail


def test_depth_one_rejects_self_reference():
    with pytest.raises(DepthLimit):
        assert_depth_one("parent", ["parent"], get_child_refs=lambda cid: [])
