"""U1 store unit tests: atomicity/idempotency (I-12/I-05), duplicate (I-06), stale (I-04)."""
from __future__ import annotations

import threading

import pytest

from server.domain.errors import DuplicateRegistration, StaleBaseVersion, ValidationError
from server.domain.models import Capsule
from server.store.capsule_store import CapsuleStore


def cap(skill_id="s1", version=1, body="b") -> Capsule:
    return Capsule(skill_id=skill_id, name=skill_id, description="", body=body, version=version)


def test_replay_returns_exact_prior_result_not_current_latest():
    # M1: replaying request rA after an intervening write rB must return rA's version, not latest.
    store = CapsuleStore()
    store.register(cap(version=1, body="v1"), "r1")
    c2 = store.get_latest("s1").with_new_content(body="v2")
    store.commit(c2, "rA", "nag", expected_base_version=1)   # -> v2
    c3 = store.get_latest("s1").with_new_content(body="v3")
    store.commit(c3, "rB", "nag", expected_base_version=2)   # -> v3
    # replay rA: new_capsule arg is irrelevant; must return the exact v2 capsule
    replay = store.commit(store.get_latest("s1").with_new_content(body="ignored"),
                          "rA", "nag", expected_base_version=99)
    assert replay.version == 2
    assert replay.body == "v2"
    # and latest is still v3 (no extra write)
    assert store.get_latest("s1").version == 3


def test_cross_skill_request_id_is_rejected():
    # M2: a request_id bound to skill 'a' cannot be reused for skill 'b'.
    store = CapsuleStore()
    store.register(cap(skill_id="a", body="A"), "R")
    with pytest.raises(ValidationError):
        store.register(cap(skill_id="b", body="B"), "R")
    # 'b' was NOT registered
    assert not store.exists("b")


def test_is_referenced_as_child():
    store = CapsuleStore()
    store.register(Capsule(skill_id="c", name="c", description="", body="b", version=1), "r1")
    store.register(
        Capsule(skill_id="p", name="p", description="", body="b", version=1, refs_children=("c",)),
        "r2",
    )
    assert store.is_referenced_as_child("c") is True
    assert store.is_referenced_as_child("p") is False


def test_register_then_get_latest():
    store = CapsuleStore()
    store.register(cap(), "r1")
    assert store.exists("s1")
    assert store.get_latest("s1").version == 1


def test_duplicate_registration_blocked():
    store = CapsuleStore()
    store.register(cap(), "r1")
    with pytest.raises(DuplicateRegistration):
        store.register(cap(body="other"), "r2")


def test_idempotent_register_returns_prior_without_change():
    store = CapsuleStore()
    store.register(cap(body="first"), "r1")
    # same request_id replay -> no new state, returns prior
    result = store.register(cap(body="second"), "r1")
    assert result.body == "first"
    assert store.get_latest("s1").body == "first"


def test_commit_stale_base_version_rejected():
    store = CapsuleStore()
    store.register(cap(version=1), "r1")
    current = store.get_latest("s1")
    new = current.with_new_content(body="v2")
    # expected_base_version mismatched -> stale
    with pytest.raises(StaleBaseVersion):
        store.commit(new, request_id="r2", origin="nag", expected_base_version=99)
    # state unchanged
    assert store.get_latest("s1").version == 1


def test_commit_happy_path_bumps_and_records_history():
    store = CapsuleStore()
    store.register(cap(version=1), "r1")
    new = store.get_latest("s1").with_new_content(body="v2")
    store.commit(new, request_id="r2", origin="nag", expected_base_version=1)
    assert store.get_latest("s1").version == 2
    assert len(store.history("s1")) == 2


def test_idempotent_commit_replay():
    store = CapsuleStore()
    store.register(cap(version=1), "r1")
    new = store.get_latest("s1").with_new_content(body="v2")
    store.commit(new, request_id="r2", origin="nag", expected_base_version=1)
    # replay same request_id -> returns prior, no extra version
    store.commit(new, request_id="r2", origin="nag", expected_base_version=1)
    assert store.get_latest("s1").version == 2


def test_concurrent_register_only_one_wins():
    store = CapsuleStore()
    errors: list[Exception] = []
    ok: list[bool] = []

    def worker(rid: str):
        try:
            store.register(cap(body=rid), rid)
            ok.append(True)
        except DuplicateRegistration as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(f"r{i}",)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(ok) == 1
    assert len(errors) == 7
