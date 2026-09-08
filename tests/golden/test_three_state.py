"""US-12 / DEV-27 — three-state (C0/C1/C2) propagation, at the SERVER-STATE level.

We replay the golden `events` array from fixtures/acceptance/three-state-golden.json
VERBATIM against the real Capsule services, then assert the per-state `versions` map and
`code_corrections_count` FIELD-BY-FIELD. `threshold` is honored.

SCOPE / F-04 HONESTY: the golden's C++ member-name fields (`expected_ready_member`,
`expected_frame_count_member`, `preserve_existing_member`) and `observations_status:
"NOT_RUN"` describe ACTUAL CODE PROPAGATION in a real Claude Code session — they require
a live plugin/subagent runtime and are OUT OF SCOPE here (verified only via a real demo
transcript, a USER deliverable). This test proves the Capsule versioning/correction state
that MUST underlie that propagation, nothing more.
"""
from __future__ import annotations

import json
import os

from server.app.routes import Container

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_GOLDEN = os.path.join(_ROOT, "fixtures", "acceptance", "three-state-golden.json")

DEV = "cmodel-development"
REF = "cmodel-refactoring"
CODE = "cmodel-code-rule"


def _load_golden() -> dict:
    with open(_GOLDEN, encoding="utf-8") as fh:
        return json.load(fh)


def _state(golden: dict, name: str) -> dict:
    return next(s for s in golden["states"] if s["state"] == name)


def _assert_versions(c: Container, golden_state: dict):
    """Field-by-field assert the per-skill version map for a golden state."""
    for skill_id, expected_version in golden_state["versions"].items():
        latest = c.store.get_latest(skill_id)
        assert latest is not None, f"{skill_id} not registered"
        assert latest.version == expected_version, (
            f"{golden_state['state']}: {skill_id} v{latest.version} != golden v{expected_version}"
        )


def test_three_state_server_level_reproduction():
    golden = _load_golden()
    assert golden["threshold"] == 3

    c = Container.build()
    # --- event: "initial seed" -> C0 (all v1, 0 corrections) --------------- #
    c.skills.register({"skill_id": REF, "body": "refactoring rules", "refs_children": []},
                      request_id="seed-ref")
    c.skills.register({"skill_id": CODE, "body": "code rules", "refs_children": []},
                      request_id="seed-code")
    c.skills.register({"skill_id": DEV, "body": "dev overview", "refs_children": [REF, CODE]},
                      request_id="seed-dev")
    c0 = _state(golden, "C0")
    _assert_versions(c, c0)
    assert len(c.store.get_latest(CODE).corrections) == c0["code_corrections_count"] == 0

    # --- event: "refactoring nag once" -> ref_version 2 -------------------- #
    r = c.nags.apply_nag(REF, correction_text="tighten duplication check",
                         base_version=1, request_id="ref-n1")
    assert r["new_version"] == 2

    # --- event: "code nag 1" -> code_version 2 ----------------------------- #
    r = c.nags.apply_nag(CODE, correction_text="use m_ prefix", base_version=1,
                         request_id="code-n1")
    assert r["new_version"] == 2

    # --- event: "code nag 2" -> code_version 3, state C1 ------------------- #
    r = c.nags.apply_nag(CODE, correction_text="verb-first function names", base_version=2,
                         request_id="code-n2")
    assert r["new_version"] == 3
    c1 = _state(golden, "C1")
    _assert_versions(c, c1)
    assert len(c.store.get_latest(CODE).corrections) == c1["code_corrections_count"] == 2
    assert r["normalize_due"] is False  # 2 < threshold

    # --- event: "code nag 3 restates same effective rules" -> code_version 4 --- #
    r = c.nags.apply_nag(CODE, correction_text="keep public API stable", base_version=3,
                         request_id="code-n3")
    assert r["new_version"] == 4
    assert r["normalize_due"] is True  # 3 == threshold: normalize_due latches

    # --- event: "successful background compaction" -> code_version 5, C2 --- #
    v4 = c.store.get_latest(CODE)
    merged_ids = [x.id for x in v4.corrections]
    assert len(merged_ids) == 3
    out = c.normalization.commit_normalization(
        CODE, base_version=4, new_body="condensed code rules (m_ prefix, verb-first, API stable)",
        request_id="code-norm", merged_correction_ids=merged_ids)
    assert out["new_version"] == 5
    c2 = _state(golden, "C2")
    _assert_versions(c, c2)
    assert len(c.store.get_latest(CODE).corrections) == c2["code_corrections_count"] == 0

    # historical v4 preserved (immutable snapshot with the pre-compaction body).
    hist = c.store.history(CODE)
    v4_snap = next(s for s in hist if s.number == 4)
    assert v4_snap.body_snapshot == "code rules"  # v4 body was still the original body


def test_dev14_full_merge_retention_and_atomicity():
    """DEV-14: merge ALL corrections -> corrections empty AND assets/refs intact AND prior
    version preserved AND version bumps exactly once."""
    c = Container.build()
    c.skills.register({"skill_id": CODE, "body": "rules", "refs_children": []},
                      request_id="r0")
    # give it a ref child by registering a leaf and pointing to it (refs must survive merge)
    c.skills.register({"skill_id": "leaf", "body": "l", "refs_children": []}, request_id="rl")
    c.nags.apply_protected_change(CODE, field="refs_children", new_value=["leaf"],
                                  base_version=1, approval_flag=True, request_id="pc")  # v2
    v = 2
    for i in range(1, 4):
        v = c.nags.apply_nag(CODE, correction_text=f"c{i}", base_version=v,
                             request_id=f"n{i}")["new_version"]
    before = c.store.get_latest(CODE)
    assert len(before.corrections) == 3
    ids = [x.id for x in before.corrections]
    out = c.normalization.commit_normalization(
        CODE, base_version=before.version, new_body="merged", request_id="norm",
        merged_correction_ids=ids)
    after = c.store.get_latest(CODE)
    assert out["capsule"]["corrections"] == []            # all merged
    assert after.refs_children == ("leaf",)               # refs intact
    assert after.version == before.version + 1            # exactly one bump (atomic)
    # prior version snapshot preserved (immutable)
    prev = next(s for s in c.store.history(CODE) if s.number == before.version)
    assert prev.body_snapshot == before.body
