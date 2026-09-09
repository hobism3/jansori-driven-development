"""U1 persistence (JSON snapshot) — reopen 2026-09-09.

Verifies: write-through on every commit, reload into a fresh store preserves latest
capsules + immutable version history, atomic write, and fail-safe on missing/corrupt
files. In-memory default (data_file=None) writes nothing.
"""
from __future__ import annotations

import json

import pytest

from server.app.routes import Container
from server.store import persistence


def _register_and_nag(c: Container, skill_id="sk", n=2):
    c.skills.register({"skill_id": skill_id, "name": "N", "description": "d",
                       "body": "base", "refs_children": []}, request_id="r0")
    v = 1
    for i in range(1, n + 1):
        v = c.nags.apply_nag(skill_id, correction_text=f"rule{i}", base_version=v,
                             request_id=f"n{i}")["new_version"]
    return v


def test_roundtrip_reload_preserves_state(tmp_path):
    f = tmp_path / "data.json"
    c1 = Container.build(data_file=str(f))
    v = _register_and_nag(c1, n=2)
    assert v == 3 and f.exists()

    # brand-new store from the same file -> same latest + history + corrections.
    c2 = Container.build(data_file=str(f))
    got = c2.skills.get_capsule("sk")
    assert got["version"] == 3
    assert len(got["corrections"]) == 2
    assert len(c2.store.history("sk")) == 3  # v1 register + 2 nags (immutable, I-01)
    assert c2.store.history("sk")[0].number == 1


def test_further_writes_after_reload_persist(tmp_path):
    f = tmp_path / "data.json"
    _register_and_nag(Container.build(data_file=str(f)), n=1)  # v2
    c2 = Container.build(data_file=str(f))
    c2.nags.apply_nag("sk", correction_text="more", base_version=2, request_id="n2")  # v3
    c3 = Container.build(data_file=str(f))
    assert c3.store.get_latest("sk").version == 3


def test_missing_file_starts_empty(tmp_path):
    c = Container.build(data_file=str(tmp_path / "nope.json"))
    assert c.store.all_capsules() == []


def test_corrupt_file_starts_empty_no_crash(tmp_path):
    f = tmp_path / "data.json"
    f.write_text("{ this is not valid json", encoding="utf-8")
    c = Container.build(data_file=str(f))  # must not raise
    assert c.store.all_capsules() == []


def test_atomic_write_is_valid_json(tmp_path):
    f = tmp_path / "data.json"
    c = Container.build(data_file=str(f))
    _register_and_nag(c, n=1)
    raw = json.loads(f.read_text(encoding="utf-8"))
    assert raw["snapshot_version"] == persistence.SNAPSHOT_VERSION
    assert raw["capsules"][0]["skill_id"] == "sk"


def test_in_memory_default_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    c = Container.build()  # data_file=None
    _register_and_nag(c, n=1)
    assert list(tmp_path.iterdir()) == []  # no snapshot file created


# ----- persist-first commit atomicity (U1 reopen 2026-09-09) --------------------
# Regression for the partial-commit bug: a disk-write failure (e.g. WinError 5 when the
# snapshot is locked by another process) must NOT advance in-memory state ahead of disk.

def test_persist_failure_leaves_memory_and_disk_at_prior_version(tmp_path, monkeypatch):
    f = tmp_path / "data.json"
    c = Container.build(data_file=str(f))
    _register_and_nag(c, n=2)  # v3 on disk + memory

    # Inject a disk-write failure on the NEXT commit (simulates os.replace WinError 5).
    def boom(*_a, **_k):
        raise OSError("simulated WinError 5: access denied")

    monkeypatch.setattr(persistence, "atomic_write", boom)
    with pytest.raises(OSError):
        c.nags.apply_nag("sk", correction_text="willfail", base_version=3, request_id="nfail")

    # In-memory state did NOT run ahead of disk.
    assert c.store.get_latest("sk").version == 3
    assert len(c.store.history("sk")) == 3
    # Disk is still the clean prior version.
    assert Container.build(data_file=str(f)).store.get_latest("sk").version == 3


def test_retry_after_persist_failure_commits_cleanly(tmp_path, monkeypatch):
    f = tmp_path / "data.json"
    c = Container.build(data_file=str(f))
    _register_and_nag(c, n=2)  # v3

    calls = {"n": 0}
    real = persistence.atomic_write

    def fail_once(path, state):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("simulated WinError 5: access denied")
        return real(path, state)

    monkeypatch.setattr(persistence, "atomic_write", fail_once)

    # First attempt fails at the disk write; nothing recorded (not even the request_id).
    with pytest.raises(OSError):
        c.nags.apply_nag("sk", correction_text="rule3", base_version=3, request_id="nfail")

    # A genuine retry (same request_id, same base_version) now succeeds — no stale replay,
    # no PRESERVATION_FAILED, because the failed attempt left no trace.
    res = c.nags.apply_nag("sk", correction_text="rule3", base_version=3, request_id="nfail")
    assert res["new_version"] == 4
    assert Container.build(data_file=str(f)).store.get_latest("sk").version == 4
