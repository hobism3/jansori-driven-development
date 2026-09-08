"""PBT-06 — Stateful property testing of the Capsule store/services.

A Hypothesis RuleBasedStateMachine drives register/nag/normalize/get against the real
Container (store + services) while a simplified dict reference model mirrors expected
state. Invariants are checked AFTER EVERY command (not just at the end):

  - store version == model version for every known skill (monotonic; +1 per write);
  - corrections count matches the model;
  - version history length == current version (every version has one immutable snapshot);
  - normalize_due latch == (corrections >= threshold).

Also includes deterministic load-semantics invariants (DEV-05/DEV-08/DEV-37): parent
load always delivers the LATEST child; child nags are independent of the parent version;
a load recorded at v(n) is not retro-invalidated when v(n+1) later commits.
"""
from __future__ import annotations

import pytest

pytest.importorskip("hypothesis")
from hypothesis import settings
from hypothesis.stateful import Bundle, RuleBasedStateMachine, invariant, rule
from hypothesis import strategies as st

from server.app.routes import Container
from server.domain.limits import LIMITS

THRESHOLD = LIMITS.normalization_threshold


class CapsuleStateMachine(RuleBasedStateMachine):
    skills = Bundle("skills")

    def __init__(self) -> None:
        super().__init__()
        self.c = Container.build()
        self.model: dict[str, dict] = {}
        self._n = 0

    def _rid(self) -> str:
        self._n += 1
        return f"req-{self._n}"

    @rule(target=skills, suffix=st.integers(min_value=0, max_value=999), body=st.text(max_size=50))
    def register(self, suffix, body):
        sid = f"s{suffix}"
        if sid in self.model:
            return sid  # already registered; reuse the id (no duplicate write)
        self.c.skills.register({"skill_id": sid, "name": "n", "description": "d",
                                "body": body, "refs_children": []}, request_id=self._rid())
        self.model[sid] = {"version": 1, "corr": [], "body": body}
        return sid

    @rule(sid=skills, text=st.text(min_size=1, max_size=40))
    def nag(self, sid, text):
        m = self.model[sid]
        r = self.c.nags.apply_nag(sid, correction_text=text,
                                  base_version=m["version"], request_id=self._rid())
        m["version"] = r["new_version"]
        m["corr"].append(r["capsule"]["corrections"][-1]["id"])

    @rule(sid=skills)
    def normalize(self, sid):
        m = self.model[sid]
        if not m["corr"]:
            return
        r = self.c.normalization.commit_normalization(
            sid, base_version=m["version"], new_body="condensed",
            request_id=self._rid(), merged_correction_ids=list(m["corr"]))
        m["version"] = r["new_version"]
        m["corr"] = []

    @rule(sid=skills)
    def get_matches_model(self, sid):
        got = self.c.skills.get_capsule(sid)
        m = self.model[sid]
        assert got["version"] == m["version"]
        assert len(got["corrections"]) == len(m["corr"])

    @invariant()
    def store_matches_model(self):
        for sid, m in self.model.items():
            latest = self.c.store.get_latest(sid)
            assert latest is not None
            assert latest.version == m["version"]
            assert len(latest.corrections) == len(m["corr"])
            # every version has exactly one immutable history snapshot (I-01)
            assert len(self.c.store.history(sid)) == m["version"]
            # normalize_due latch
            assert self.c.nags.check_threshold(sid) == (len(m["corr"]) >= THRESHOLD)


TestCapsuleStateMachine = CapsuleStateMachine.TestCase
TestCapsuleStateMachine.settings = settings(max_examples=25, stateful_step_count=20, deadline=None)


# ----- deterministic load-semantics invariants (DEV-05 / DEV-08 / DEV-37) --- #
def _c_with_parent_child():
    c = Container.build()
    c.skills.register({"skill_id": "child", "body": "cbody", "refs_children": []},
                      request_id="rc")
    c.skills.register({"skill_id": "parent", "body": "pbody", "refs_children": ["child"]},
                      request_id="rp")
    return c


def test_load_delivers_latest_child_even_if_parent_unchanged():
    """DEV-05/DEV-08: nag the child; parent version stays 1 but load returns the child's
    newest corrections."""
    c = _c_with_parent_child()
    c.nags.apply_nag("child", correction_text="child-rule", base_version=1, request_id="n1")
    loaded = c.skills.load("parent", session_id="sess")
    assert loaded["parent"]["version"] == 1  # parent unchanged
    child = next(x for x in loaded["children"] if x["skill_id"] == "child")
    assert child["version"] == 2  # latest child delivered
    assert "child-rule" in child["corrections"]


def test_earlier_load_not_retro_invalidated_by_later_commit():
    """DEV-37: a load recorded at v(n) remains valid history; a later v(n+1) commit does
    not mutate the earlier immutable snapshot."""
    c = _c_with_parent_child()
    c.skills.load("parent", session_id="sess")            # records scope at child v1
    hist_before = c.store.history("child")
    c.nags.apply_nag("child", correction_text="x", base_version=1, request_id="n2")  # -> v2
    hist_after = c.store.history("child")
    assert hist_before[0].number == 1 and hist_before[0].body_snapshot == "cbody"
    assert hist_after[0].number == 1 and hist_after[0].body_snapshot == "cbody"  # unchanged
    assert len(hist_after) == 2
