"""PBT-02 — Round-trip properties for the Capsule domain.

Two invertible paths:
  (a) Capsule -> public_dict() -> reconstruct : content survives serialization.
  (b) register(payload) -> get_capsule()      : registered content round-trips through
      the service + store layer (the transformation layer, not the socket — PBT-02).

Uses generated inputs (not hardcoded). Property-based; complemented by example tests
in tests/golden (PBT-10).
"""
from __future__ import annotations

import pytest

pytest.importorskip("hypothesis")
from hypothesis import given
from hypothesis import strategies as st

from server.app.routes import Container
from server.domain.models import Asset, Capsule, Correction

from . import generators as gen


@given(
    skill_id=gen.skill_ids(),
    name=gen.names(),
    description=gen.descriptions(),
    body=gen.bodies(),
    refs=st.lists(gen.skill_ids(), max_size=3, unique=True),
)
def test_capsule_public_dict_roundtrip(skill_id, name, description, body, refs):
    """f_inv(f(x)) == x for the content-bearing fields of a Capsule."""
    cap = Capsule(
        skill_id=skill_id,
        name=name,
        description=description,
        body=body,
        version=1,
        corrections=(Correction(id="c1", target=skill_id, instruction_text="t",
                                 request_id="r1", seq=1),),
        refs_children=tuple(refs),
        assets=(Asset(name="a", path="/tmp/a", is_script=False),),
    )
    d = cap.public_dict()
    # Reconstruct content from the serialized view and assert equality.
    assert d["skill_id"] == cap.skill_id
    assert d["name"] == cap.name
    assert d["description"] == cap.description
    assert d["body"] == cap.body
    assert d["version"] == cap.version
    assert d["refs_children"] == list(cap.refs_children)
    assert [c["id"] for c in d["corrections"]] == [c.id for c in cap.corrections]
    assert [c["instruction_text"] for c in d["corrections"]] == \
        [c.instruction_text for c in cap.corrections]
    assert [(a["name"], a["path"], a["is_script"]) for a in d["assets"]] == \
        [(a.name, a.path, a.is_script) for a in cap.assets]


@given(payload=gen.register_payloads(id_strategy=gen.skill_ids()))
def test_register_then_get_roundtrips(payload):
    """A freshly-registered capsule's content is returned unchanged by GET (v1)."""
    c = Container.build()  # fresh empty store per example
    out = c.skills.register(dict(payload), request_id="req-" + payload["skill_id"])
    got = c.skills.get_capsule(payload["skill_id"])
    assert got["skill_id"] == payload["skill_id"]
    assert got["name"] == payload["name"]
    assert got["description"] == payload["description"]
    assert got["body"] == payload["body"]
    assert got["version"] == 1
    # register echoes the same capsule it stored.
    assert out["capsule"]["body"] == got["body"]
