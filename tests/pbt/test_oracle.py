"""PBT-05 — Oracle / model-based testing.

A pure-Python reference model recomputes (version, corrections_count, normalize_due)
from a command sequence, independently of the real service/store. We assert the system
under test agrees with the oracle for every generated sequence.

The oracle mirrors the documented rules: nag => +1 correction & version+1; a full
normalize => corrections emptied & version+1; normalize_due latches at corrections
count >= threshold (3). It is genuinely independent of the implementation (it does not
call the store), so an implementation regression in version/threshold accounting would
be caught.
"""
from __future__ import annotations

import pytest

pytest.importorskip("hypothesis")
from hypothesis import given
from hypothesis import strategies as st

from server.app.routes import Container
from server.domain.limits import LIMITS

from . import generators as gen

THRESHOLD = LIMITS.normalization_threshold


class Model:
    """Reference state for one skill."""

    def __init__(self) -> None:
        self.version = 1
        self.corrections = 0

    def nag(self) -> None:
        self.corrections += 1
        self.version += 1

    def normalize_all(self) -> None:
        self.corrections = 0
        self.version += 1

    @property
    def normalize_due(self) -> bool:
        return self.corrections >= THRESHOLD


# command = ("nag", text) | ("normalize",)
_commands = st.lists(
    st.one_of(
        st.tuples(st.just("nag"), gen.correction_texts()),
        st.tuples(st.just("normalize")),
    ),
    min_size=0,
    max_size=12,
)


@given(cmds=_commands)
def test_service_matches_reference_model(cmds):
    c = _fresh()
    model = Model()
    seq = 0
    for cmd in cmds:
        if cmd[0] == "nag":
            seq += 1
            r = c.nags.apply_nag("sk", correction_text=cmd[1],
                                 base_version=model.version, request_id=f"n{seq}")
            model.nag()
            assert r["new_version"] == model.version
            assert len(r["capsule"]["corrections"]) == model.corrections
            assert r["normalize_due"] == model.normalize_due
        else:  # normalize all current corrections
            latest = c.store.get_latest("sk")
            ids = [x.id for x in latest.corrections]
            if not ids:
                continue  # normalize requires >=1 declared id (skip empty)
            seq += 1
            r = c.normalization.commit_normalization(
                "sk", base_version=model.version, new_body="condensed",
                request_id=f"z{seq}", merged_correction_ids=ids)
            model.normalize_all()
            assert r["new_version"] == model.version
            assert len(r["capsule"]["corrections"]) == 0 == model.corrections


def _fresh():
    c = Container.build()
    c.skills.register({"skill_id": "sk", "name": "n", "description": "d",
                       "body": "base", "refs_children": []}, request_id="r0")
    return c


def test_three_state_golden_threshold_matches_impl():
    """Cross-check: the golden's declared threshold equals the implemented threshold."""
    import json
    import os

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    with open(os.path.join(root, "fixtures", "acceptance", "three-state-golden.json"),
              encoding="utf-8") as fh:
        golden = json.load(fh)
    assert golden["threshold"] == THRESHOLD
