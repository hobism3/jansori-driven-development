"""Single-instance guard for the persistent Capsule store (U1 reopen 2026-09-09).

Why this exists: the store persists to one JSON file, written through on every commit
via an atomic temp+replace (persistence.atomic_write). If two server processes hold the
same data file, their os.replace calls race and one intermittently fails with WinError 5
("access denied") on Windows, which used to surface as a transient SERVER_ERROR and a
partial commit. Preventing a second process from binding the same file at startup removes
that failure mode at the source.

Mechanism: acquire an OS-level advisory lock on a sidecar `<data_file>.lock` and hold the
handle open for the whole process lifetime. The OS releases the lock automatically when the
process exits (even on crash), so there is no stale-lock problem — no PID liveness probing,
no manual cleanup on the happy path. The PID is written into the lock file purely as a
human-readable hint for whoever is diagnosing a conflict.

Platform:
- Windows: msvcrt.locking(LK_NBLCK) on the first byte (non-blocking exclusive).
- POSIX:   fcntl.flock(LOCK_EX | LOCK_NB).

Only the persistent server entry point (main()) acquires the lock; in-memory runs
(:memory:) and the test harness never touch it.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

try:  # POSIX
    import fcntl  # type: ignore
except ImportError:  # pragma: no cover - Windows
    fcntl = None  # type: ignore

try:  # Windows
    import msvcrt  # type: ignore
except ImportError:  # pragma: no cover - POSIX
    msvcrt = None  # type: ignore


class InstanceLockError(RuntimeError):
    """Raised when the data file is already locked by another running instance."""


class InstanceLock:
    """Holds an OS advisory lock on `<data_file>.lock` for the process lifetime.

    Keep a reference alive for as long as the server should stay single-instance; the lock
    is released when close() is called or the process (and thus the open handle) exits.
    """

    def __init__(self, lock_path: Path) -> None:
        self._lock_path = lock_path
        self._fh = None  # type: ignore[var-annotated]

    def acquire(self) -> "InstanceLock":
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        # Open for read/write, creating if absent; do NOT truncate an existing lock file
        # before we know we own it (another instance may be mid-write of its PID hint).
        fh = open(self._lock_path, "a+", encoding="utf-8")
        try:
            _os_lock(fh)
        except OSError as exc:
            fh.close()
            raise InstanceLockError(
                f"another instance already holds {self._lock_path.name} "
                f"(a server is likely already running against this data file)"
            ) from exc
        # We own the lock: record our PID as a diagnostic hint.
        self._fh = fh
        try:
            fh.seek(0)
            fh.truncate()
            fh.write(str(os.getpid()))
            fh.flush()
        except OSError:
            pass  # PID hint is best-effort; the lock itself is what matters.
        return self

    def close(self) -> None:
        if self._fh is not None:
            try:
                _os_unlock(self._fh)
            finally:
                self._fh.close()
                self._fh = None

    def __enter__(self) -> "InstanceLock":
        return self.acquire()

    def __exit__(self, *exc) -> None:
        self.close()


def _os_lock(fh) -> None:
    if msvcrt is not None:
        # Lock the first byte, non-blocking; raises OSError if already locked. msvcrt locks
        # `nbytes` from the CURRENT position, so seek(0) first to lock a fixed region every
        # time regardless of how much PID text the file already holds (locking past EOF is OK).
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
    elif fcntl is not None:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    else:  # pragma: no cover - no locking primitive available
        raise OSError("no OS file-locking primitive available on this platform")


def _os_unlock(fh) -> None:
    try:
        if msvcrt is not None:
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        elif fcntl is not None:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass  # releasing is best-effort; process exit releases it anyway.


def acquire_for(data_file: Optional[str | Path]) -> Optional[InstanceLock]:
    """Acquire the single-instance lock for `data_file`, or None if persistence is off.

    Raises InstanceLockError if another process already holds the lock.
    """
    if not data_file:
        return None
    lock_path = Path(str(data_file) + ".lock")
    return InstanceLock(lock_path).acquire()
