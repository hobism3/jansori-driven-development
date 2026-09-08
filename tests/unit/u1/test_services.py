"""U1 service unit tests: register/load/expand, nag/threshold/resolve, normalization, protected."""
from __future__ import annotations

import pytest

from server.domain.errors import (
    DepthLimit,
    DuplicateRegistration,
    NeedsConfirmation,
    OverLength,
    PreservationFailed,
    ProtectedChangeDenied,
    SkillAbsent,
    StaleBaseVersion,
    ValidationError,
)
from server.domain.limits import Limits
from server.services.nag_service import NagService
from server.services.normalization_service import NormalizationService
from server.services.session_service import SessionService
from server.services.skill_service import SkillService
from server.store.capsule_store import CapsuleStore


@pytest.fixture
def wired(tmp_path):
    store = CapsuleStore()
    sessions = SessionService()
    limits = Limits(max_content_length=100, normalization_threshold=3)
    skills = SkillService(store, sessions, limits=limits, temp_dir=tmp_path)
    nags = NagService(store, sessions, limits=limits)
    norm = NormalizationService(store, limits=limits)
    return store, sessions, skills, nags, norm


def register_parent(skills, skill_id="parent", body="do X", children=None, request_id=None):
    return skills.register(
        {
            "skill_id": skill_id,
            "name": skill_id,
            "description": "desc",
            "body": body,
            "refs_children": children or [],
            "assets": [],
        },
        request_id=request_id or f"reg-{skill_id}",
    )


# ----- SkillService ---------------------------------------------------------
def test_register_and_index(wired):
    _, _, skills, _, _ = wired
    register_parent(skills)
    idx = skills.build_index()
    assert any(e["skill_id"] == "parent" for e in idx)
    # index has no body
    assert "body" not in idx[0]


def test_register_duplicate_blocked(wired):
    # true duplicate = same skill_id, DIFFERENT request_id (same request_id is idempotent replay)
    _, _, skills, _, _ = wired
    register_parent(skills, request_id="reg-1")
    with pytest.raises(DuplicateRegistration):
        register_parent(skills, request_id="reg-2")


def test_register_same_request_id_is_idempotent_replay(wired):
    _, _, skills, _, _ = wired
    first = register_parent(skills, body="first", request_id="same")
    second = register_parent(skills, body="second", request_id="same")  # replay
    assert second["capsule"]["body"] == "first"


def test_register_over_length(wired):
    _, _, skills, _, _ = wired
    with pytest.raises(OverLength):
        register_parent(skills, body="x" * 500)


def test_load_expands_depth1_children_and_records_scope(wired):
    store, sessions, skills, _, _ = wired
    register_parent(skills, skill_id="child", body="child body")
    register_parent(skills, skill_id="parent", body="parent body", children=["child"])
    result = skills.load("parent", session_id="sess1")
    assert result["parent"]["skill_id"] == "parent"
    assert result["children"][0]["skill_id"] == "child"
    assert result["children"][0]["body"] == "child body"
    # scope recorded (I-02)
    assert "parent" in sessions.active_scope_ids("sess1")
    assert "child" in sessions.active_scope_ids("sess1")


def test_load_absent_skill(wired):
    _, _, skills, _, _ = wired
    with pytest.raises(SkillAbsent):
        skills.load("nope", session_id="s")


# ----- NagService -----------------------------------------------------------
def test_apply_nag_bumps_version_and_idempotent(wired):
    _, _, skills, nags, _ = wired
    register_parent(skills)
    r1 = nags.apply_nag("parent", "be terse", base_version=1, request_id="n1")
    assert r1["new_version"] == 2
    # idempotent replay -> no extra bump
    r2 = nags.apply_nag("parent", "be terse", base_version=1, request_id="n1")
    assert r2["idempotent_replay"] is True
    assert r2["new_version"] == 2


def test_apply_nag_stale_rejected(wired):
    _, _, skills, nags, _ = wired
    register_parent(skills)
    with pytest.raises(StaleBaseVersion):
        nags.apply_nag("parent", "x", base_version=99, request_id="n1")


def test_apply_nag_over_length(wired):
    _, _, skills, nags, _ = wired
    register_parent(skills)
    with pytest.raises(OverLength):
        nags.apply_nag("parent", "y" * 500, base_version=1, request_id="n1")


def test_threshold_normalize_due_at_three(wired):
    _, _, skills, nags, _ = wired
    register_parent(skills)
    v = 1
    for i in range(1, 4):
        r = nags.apply_nag("parent", f"c{i}", base_version=v, request_id=f"n{i}")
        v = r["new_version"]
    assert r["normalize_due"] is True
    assert nags.check_threshold("parent") is True


def test_resolve_target_unique_and_ambiguous(wired):
    _, sessions, skills, nags, _ = wired
    register_parent(skills, skill_id="child", body="c")
    register_parent(skills, skill_id="parent", body="p", children=["child"])
    skills.load("parent", session_id="s1")
    assert nags.resolve_target("parent", "s1") == "parent"
    with pytest.raises(NeedsConfirmation):
        nags.resolve_target("", "s1")           # no hint
    with pytest.raises(NeedsConfirmation):
        nags.resolve_target("unknown", "s1")    # not in scope


# ----- protected-change -----------------------------------------------------
def test_protected_change_requires_approval(wired):
    _, _, skills, nags, _ = wired
    register_parent(skills)
    with pytest.raises(ProtectedChangeDenied):
        nags.apply_protected_change(
            "parent", field="name", new_value="New", base_version=1,
            approval_flag=False, request_id="p1",
        )
    ok = nags.apply_protected_change(
        "parent", field="name", new_value="New", base_version=1,
        approval_flag=True, request_id="p2",
    )
    assert ok["capsule"]["name"] == "New"


def test_protected_change_non_protected_field_rejected(wired):
    _, _, skills, nags, _ = wired
    register_parent(skills)
    with pytest.raises(Exception):
        nags.apply_protected_change(
            "parent", field="body", new_value="x", base_version=1,
            approval_flag=True, request_id="p3",
        )


# ----- NormalizationService -------------------------------------------------
def test_normalization_commit_condenses_and_clears_declared(wired):
    # U1-reopen redesign: preservation is validated by the merged-id declaration + length,
    # NOT by verbatim-substring survival, so a CONDENSED body is accepted.
    _, _, skills, nags, norm = wired
    register_parent(skills, body="base instructions")
    v = 1
    for i in range(1, 4):
        r = nags.apply_nag("parent", f"rule{i}", base_version=v, request_id=f"n{i}")
        v = r["new_version"]
    corr_ids = [c["id"] for c in skills.get_capsule("parent")["corrections"]]
    merged = "condensed"  # shorter, paraphrased — would FAIL the old substring rule
    result = norm.commit_normalization(
        "parent", base_version=v, new_body=merged, request_id="norm1", merged_correction_ids=corr_ids
    )
    assert result["capsule"]["corrections"] == []
    assert result["capsule"]["body"] == "condensed"
    assert result["new_version"] == v + 1


def test_normalization_partial_merge_carries_forward_undeclared(wired):
    # declaring a SUBSET removes only those corrections; undeclared ones survive.
    _, _, skills, nags, norm = wired
    register_parent(skills, body="base")
    v = 1
    for i in range(1, 4):
        r = nags.apply_nag("parent", f"rule{i}", base_version=v, request_id=f"n{i}")
        v = r["new_version"]
    corr = skills.get_capsule("parent")["corrections"]
    keep_id = corr[-1]["id"]
    merged_ids = [c["id"] for c in corr[:-1]]  # merge only the first two
    result = norm.commit_normalization(
        "parent", base_version=v, new_body="two merged", request_id="norm1", merged_correction_ids=merged_ids
    )
    remaining_ids = [c["id"] for c in result["capsule"]["corrections"]]
    assert remaining_ids == [keep_id]


def test_normalization_preservation_failure_unknown_id(wired):
    # redesign: declaring an id not present at base -> preservation fails (no change, I-11).
    _, _, skills, nags, norm = wired
    register_parent(skills, body="base")
    r = nags.apply_nag("parent", "keep this rule", base_version=1, request_id="n1")
    with pytest.raises(PreservationFailed):
        norm.commit_normalization(
            "parent", base_version=r["new_version"], new_body="anything",
            request_id="norm1", merged_correction_ids=["does-not-exist"],
        )


def test_normalization_over_length_still_rejected(wired):
    # length invariant unchanged: new_body over L -> OverLength (no change, I-09/I-11).
    _, _, skills, nags, norm = wired
    register_parent(skills, body="base")
    v = 1
    for i in range(1, 4):
        r = nags.apply_nag("parent", f"rule{i}", base_version=v, request_id=f"n{i}")
        v = r["new_version"]
    corr_ids = [c["id"] for c in skills.get_capsule("parent")["corrections"]]
    with pytest.raises(OverLength):
        norm.commit_normalization(
            "parent", base_version=v, new_body="x" * 101, request_id="norm1",
            merged_correction_ids=corr_ids,
        )


def test_load_composite_length_includes_corrections(wired):
    # M4: load must reject when parent composite render (body + corrections) exceeds L (=100).
    _, _, skills, nags, _ = wired
    register_parent(skills, skill_id="p", body="x" * 60)  # body alone under 100
    v = 1
    for i in range(1, 4):
        r = nags.apply_nag("p", "y" * 20, base_version=v, request_id=f"n{i}")
        v = r["new_version"]
    # composite = 60 + 3*20 + newlines > 100
    with pytest.raises(OverLength):
        skills.load("p", session_id="s")


def test_resolve_target_no_false_substring_match(wired):
    # m1: 'alph' must NOT uniquely resolve to 'alpha' when 'alphabet' is also in scope.
    _, sessions, skills, nags, _ = wired
    register_parent(skills, skill_id="alpha", body="a")
    register_parent(skills, skill_id="alphabet", body="b")
    sessions.set_active_scope(
        "s", {"skill_id": "alpha", "version": 1}, [{"skill_id": "alphabet", "version": 1}]
    )
    with pytest.raises(NeedsConfirmation):
        nags.resolve_target("alph", "s")          # loose substring -> now refused
    assert nags.resolve_target("alpha", "s") == "alpha"  # exact still works


def test_protected_change_refs_upward_depth_limit(wired):
    # B1: giving an already-child capsule its own children must be refused (I-15 upward).
    _, _, skills, nags, _ = wired
    register_parent(skills, skill_id="X", body="x")
    register_parent(skills, skill_id="N", body="n")
    register_parent(skills, skill_id="P", body="p", children=["N"])  # P -> N
    with pytest.raises(DepthLimit):
        nags.apply_protected_change(
            "N", field="refs_children", new_value=["X"], base_version=1,
            approval_flag=True, request_id="pc1",
        )
    # N did not gain children (no state change)
    assert skills.get_capsule("N")["refs_children"] == []


def test_cross_skill_request_id_rejected_at_service(wired):
    # M2 at the service layer (apply_nag).
    _, _, skills, nags, _ = wired
    register_parent(skills, skill_id="a", body="a")
    register_parent(skills, skill_id="b", body="b")
    nags.apply_nag("a", "corr", base_version=1, request_id="shared")
    with pytest.raises(ValidationError):
        nags.apply_nag("b", "corr", base_version=1, request_id="shared")


def test_normalization_stale_restart_signal(wired):
    _, _, skills, nags, norm = wired
    register_parent(skills, body="base")
    nags.apply_nag("parent", "rule1", base_version=1, request_id="n1")
    corr_ids = [c["id"] for c in skills.get_capsule("parent")["corrections"]]
    # subagent computed against base_version=1 but latest is now 2 -> stale
    with pytest.raises(StaleBaseVersion):
        norm.commit_normalization(
            "parent", base_version=1, new_body="base rule1", request_id="norm1",
            merged_correction_ids=corr_ids,
        )
