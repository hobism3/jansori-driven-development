"""PBT-04 — Idempotency properties (I-05, M1/M2).

`f(f(x)) == f(x)` keyed by request_id, verified as observable-state equivalence:
  - replaying a write with the SAME request_id returns the EXACT prior result and
    changes nothing (version, corrections, body all stable);
  - a request_id bound to one skill, reused against another, is a client error
    (VALIDATION_ERROR), not a silent foreign-capsule replay (M2).
"""
from __future__ import annotations

import pytest

pytest.importorskip("hypothesis")
from hypothesis import given
from hypothesis import strategies as st

from server.app.routes import Container
from server.domain.errors import DuplicateRegistration, ValidationError

from . import generators as gen


def _fresh(skill_id="sk"):
    c = Container.build()
    c.skills.register({"skill_id": skill_id, "name": "n", "description": "d",
                       "body": "base", "refs_children": []}, request_id="r0")
    return c


@given(text=gen.correction_texts(), extra=st.integers(min_value=0, max_value=5))
def test_nag_replay_is_exact_and_stateless(text, extra):
    c = _fresh()
    first = c.nags.apply_nag("sk", correction_text=text, base_version=1, request_id="n1")
    assert first["idempotent_replay"] is False
    v_after = first["new_version"]
    corr_after = len(first["capsule"]["corrections"])

    # replay same request_id (even with a DIFFERENT base_version) -> exact prior result.
    replay = c.nags.apply_nag("sk", correction_text="totally different",
                              base_version=1 + extra, request_id="n1")
    assert replay["idempotent_replay"] is True
    assert replay["new_version"] == v_after
    assert len(replay["capsule"]["corrections"]) == corr_after
    # observable store state unchanged by the replay (f(f(x)) == f(x))
    latest = c.store.get_latest("sk")
    assert latest.version == v_after
    assert len(latest.corrections) == corr_after


@given(text=gen.correction_texts())
def test_request_id_bound_to_skill_cross_use_rejected(text):
    c = _fresh("sk-a")
    c.skills.register({"skill_id": "sk-b", "body": "b", "refs_children": []}, request_id="rb")
    c.nags.apply_nag("sk-a", correction_text=text, base_version=1, request_id="shared")
    # reuse "shared" against a different skill -> M2 client error
    with pytest.raises(ValidationError):
        c.nags.apply_nag("sk-b", correction_text=text, base_version=1, request_id="shared")


@given(payload=gen.register_payloads(id_strategy=gen.skill_ids()))
def test_register_idempotent_replay_vs_duplicate(payload):
    c = Container.build()
    sid = payload["skill_id"]
    first = c.skills.register(dict(payload), request_id="reg1")
    # same request_id -> idempotent replay: exact same capsule, still one registration.
    replay = c.skills.register(dict(payload), request_id="reg1")
    assert replay["capsule"]["version"] == first["capsule"]["version"] == 1
    # DIFFERENT request_id, same skill_id -> genuine duplicate rejected (I-06).
    with pytest.raises(DuplicateRegistration):
        c.skills.register(dict(payload), request_id="reg2")
    assert c.store.get_latest(sid).version == 1
