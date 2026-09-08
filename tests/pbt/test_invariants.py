"""PBT-03 — Invariant properties over the Capsule domain.

Covers the documented U1 invariants as general rules (not example duplicates):
  I-01  content change => version + 1; prior Version snapshots immutable.
  I-04  stale base_version => STALE, no state change.
  I-09  over-length => OVER_LENGTH, prior content preserved; post-commit len(body) <= L.
  I-11  preservation: declared ⊆ base & len<=L accept; empty/unknown => PRESERVATION_FAILED.
  I-15  depth-1 both directions; a would-be grandchild is refused with DEPTH_LIMIT.
"""
from __future__ import annotations

import pytest

pytest.importorskip("hypothesis")
from hypothesis import given, settings
from hypothesis import strategies as st

from server.app.routes import Container
from server.domain.errors import DepthLimit, OverLength, PreservationFailed, StaleBaseVersion
from server.domain.limits import LIMITS
from server.domain.models import Capsule, Correction

from . import generators as gen

L = LIMITS.max_content_length


def _fresh_with_capsule(skill_id="sk", body="base"):
    c = Container.build()
    c.skills.register({"skill_id": skill_id, "name": "n", "description": "d",
                       "body": body, "refs_children": []}, request_id="r0")
    return c


# ----- I-01 : monotonic version + immutable history ------------------------- #
@given(texts=st.lists(gen.correction_texts(), min_size=1, max_size=6))
def test_i01_version_increments_by_one_and_history_immutable(texts):
    c = _fresh_with_capsule()
    version = 1
    seen_snapshots = []
    for i, text in enumerate(texts):
        r = c.nags.apply_nag("sk", correction_text=text, base_version=version,
                             request_id=f"n{i}")
        assert r["new_version"] == version + 1  # I-01: exactly +1 per content change
        version = r["new_version"]
        hist = c.store.history("sk")
        # history grows by one immutable snapshot each commit; earlier entries unchanged.
        for j, prev in enumerate(seen_snapshots):
            assert hist[j].number == prev.number
            assert hist[j].body_snapshot == prev.body_snapshot
        seen_snapshots = list(hist)


# ----- I-04 : stale base rejected, no state change -------------------------- #
@given(good=gen.correction_texts(), stale_delta=st.integers(min_value=1, max_value=3))
def test_i04_stale_base_version_rejected_no_change(good, stale_delta):
    c = _fresh_with_capsule()
    c.nags.apply_nag("sk", correction_text=good, base_version=1, request_id="n1")
    latest_before = c.store.get_latest("sk")
    with pytest.raises(StaleBaseVersion):
        c.nags.apply_nag("sk", correction_text="x",
                         base_version=latest_before.version - stale_delta, request_id="n2")
    latest_after = c.store.get_latest("sk")
    assert latest_after.version == latest_before.version
    assert latest_after.body == latest_before.body
    assert len(latest_after.corrections) == len(latest_before.corrections)


# ----- I-09 : over-length rejected + preserved; post-commit len <= L --------- #
@given(pair=gen.boundary_bodies())
def test_i09_length_boundary_on_register(pair):
    body, should_pass = pair
    c = Container.build()
    if should_pass:
        out = c.skills.register({"skill_id": "sk", "body": body, "refs_children": []},
                                request_id="r0")
        assert len(out["capsule"]["body"]) <= L
    else:
        with pytest.raises(OverLength):
            c.skills.register({"skill_id": "sk", "body": body, "refs_children": []},
                              request_id="r0")
        assert c.store.get_latest("sk") is None  # preserved: nothing registered


# ----- I-11 : preservation declaration rules -------------------------------- #
@given(
    n=st.integers(min_value=1, max_value=5),
    body=gen.bodies(),
)
def test_i11_preservation_declaration(n, body):
    corrections = tuple(
        Correction(id=f"c{i}", target="sk", instruction_text=f"t{i}", request_id=f"r{i}", seq=i)
        for i in range(1, n + 1)
    )
    cap = Capsule(skill_id="sk", name="n", description="d", body="b", version=1,
                  corrections=corrections)
    svc = Container.build().normalization
    all_ids = [c.id for c in corrections]
    # declared non-empty subset & length ok -> accept
    if len(body) <= L:
        assert svc.validate_preservation(cap, body, all_ids) is True
        assert svc.validate_preservation(cap, body, all_ids[:1]) is True
    # empty declaration -> reject
    assert svc.validate_preservation(cap, body, []) is False
    # unknown id -> reject
    assert svc.validate_preservation(cap, body, ["does-not-exist"]) is False


# ----- I-15 : depth-1 refused (grandchild) ---------------------------------- #
@given(g=gen.skill_ids(), child=gen.skill_ids(), parent=gen.skill_ids())
@settings(max_examples=40)
def test_i15_depth_one_grandchild_refused(g, child, parent):
    # need three distinct ids
    if len({g, child, parent}) < 3:
        return
    c = Container.build()
    c.skills.register({"skill_id": g, "body": "leaf", "refs_children": []}, request_id="rg")
    # child references g -> child now HAS children (depth-1 OK for child itself)
    c.skills.register({"skill_id": child, "body": "c", "refs_children": [g]}, request_id="rc")
    # registering parent -> [child] would create parent->child->g (depth-2): refused, no state.
    with pytest.raises(DepthLimit):
        c.skills.register({"skill_id": parent, "body": "p", "refs_children": [child]},
                          request_id="rp")
    assert c.store.get_latest(parent) is None
