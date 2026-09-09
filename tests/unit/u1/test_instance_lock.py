"""U1 single-instance lock (reopen 2026-09-09).

Verifies that a second acquirer of the same data file's lock is rejected (so two servers
can never race os.replace on one snapshot), that releasing lets a later acquire succeed,
and that persistence-off (:memory: / None) skips locking entirely.
"""
from __future__ import annotations

import pytest

from server.store import instance_lock


def test_second_acquire_is_rejected(tmp_path):
    f = tmp_path / "data.json"
    lock1 = instance_lock.acquire_for(str(f))
    assert lock1 is not None
    try:
        with pytest.raises(instance_lock.InstanceLockError):
            instance_lock.acquire_for(str(f))
    finally:
        lock1.close()


def test_reacquire_after_release_succeeds(tmp_path):
    f = tmp_path / "data.json"
    lock1 = instance_lock.acquire_for(str(f))
    lock1.close()
    lock2 = instance_lock.acquire_for(str(f))
    assert lock2 is not None
    lock2.close()


def test_context_manager_releases(tmp_path):
    f = tmp_path / "data.json"
    lock_path = __import__("pathlib").Path(str(f) + ".lock")
    with instance_lock.InstanceLock(lock_path):
        with pytest.raises(instance_lock.InstanceLockError):
            instance_lock.acquire_for(str(f))
    # released on exit -> acquirable again
    again = instance_lock.acquire_for(str(f))
    assert again is not None
    again.close()


def test_no_data_file_skips_locking():
    assert instance_lock.acquire_for(None) is None
    assert instance_lock.acquire_for("") is None
