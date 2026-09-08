"""In-memory Capsule store (CMP-07).

Responsibilities:
- Single source of truth for Capsules (latest pointer + immutable version history).
- Atomic writes via per-skill lock + copy-on-write pointer swap (I-12, D-04).
- GLOBAL idempotency log keyed by request_id (I-05, Q10=A) — serialized by a global
  request lock so the same request_id cannot commit twice even across different skills.
- Duplicate detection by exact skill_id (I-06, Q4=A).
- Reverse reference lookup (is_referenced_as_child) for depth-1 enforcement (I-15).

Persistence: in-memory only; empty on start, not persisted across restarts (Q9).

Locking discipline (to avoid deadlock, locks are ALWAYS acquired in this order):
    skill lock (per skill_id)  ->  request lock (global)
`commit`/`register` perform the idempotency replay check, stale check, pointer swap,
version-history append, and request-log record as ONE atomic unit while holding BOTH
locks, so a concurrent nag + background normalization (same skill) and any same
request_id across skills can never observe a partial or duplicated write (I-05/I-12).
"""
from __future__ import annotations

import threading
from typing import Optional

from ..domain.errors import DuplicateRegistration, StaleBaseVersion, ValidationError
from ..domain.models import Capsule, Version


class CapsuleStore:
    def __init__(self) -> None:
        self._capsules: dict[str, Capsule] = {}          # skill_id -> latest confirmed Capsule
        self._history: dict[str, list[Version]] = {}     # skill_id -> immutable version snapshots (I-01)
        # request_id -> the exact Capsule that request produced (for precise replay, M1/I-05)
        self._request_log: dict[str, Capsule] = {}
        self._skill_locks: dict[str, threading.RLock] = {}
        self._registry_lock = threading.RLock()          # guards lock creation + capsule-map scans
        self._request_lock = threading.Lock()            # global: serializes request_id reserve/record

    # ----- lock management ---------------------------------------------------
    def _lock_for(self, skill_id: str) -> threading.RLock:
        with self._registry_lock:
            lock = self._skill_locks.get(skill_id)
            if lock is None:
                lock = threading.RLock()
                self._skill_locks[skill_id] = lock
            return lock

    # ----- reads -------------------------------------------------------------
    def get_latest(self, skill_id: str) -> Optional[Capsule]:
        """Return latest confirmed Capsule (I-02) or None if absent."""
        return self._capsules.get(skill_id)

    def exists(self, skill_id: str) -> bool:
        """Duplicate-registration decision (I-06)."""
        return skill_id in self._capsules

    def get_request(self, request_id: str) -> Optional[Capsule]:
        """Return the EXACT Capsule an already-processed request produced, else None (I-05).

        The result is the specific capsule that request committed (not merely the current
        latest), so replay is faithful even after intervening writes (M1).
        """
        with self._request_lock:
            return self._request_log.get(request_id)

    def is_referenced_as_child(self, skill_id: str, exclude_parent: Optional[str] = None) -> bool:
        """True if any capsule lists `skill_id` in its refs_children (reverse lookup, I-15)."""
        with self._registry_lock:
            for cap in self._capsules.values():
                if exclude_parent is not None and cap.skill_id == exclude_parent:
                    continue
                if skill_id in cap.refs_children:
                    return True
        return False

    def history(self, skill_id: str) -> list[Version]:
        return list(self._history.get(skill_id, []))

    def all_capsules(self) -> list[Capsule]:
        return list(self._capsules.values())

    # ----- writes ------------------------------------------------------------
    def register(self, capsule: Capsule, request_id: str) -> Capsule:
        """Atomically register a brand-new capsule (version already == 1).

        Idempotent on request_id (I-05); the exact-skill_id duplicate is re-checked under
        the lock (I-06/I-12) so a racing register of the same id cannot both succeed.
        """
        with self._lock_for(capsule.skill_id), self._request_lock:
            replay = self._replay_or_none(request_id, capsule.skill_id)
            if replay is not None:
                return replay
            if capsule.skill_id in self._capsules:
                raise DuplicateRegistration(
                    "skill_id already registered.",
                    detail={"skill_id": capsule.skill_id},
                )
            self._commit_locked(capsule, request_id, origin="register")
            return capsule

    def commit(
        self,
        new_capsule: Capsule,
        request_id: str,
        origin: str,
        expected_base_version: int,
    ) -> Capsule:
        """Atomically swap the latest pointer to `new_capsule` after a stale check.

        - Idempotent replay on request_id returns the exact prior result (I-05/M1).
        - StaleBaseVersion raised (and NO change) if current.version != expected_base_version (I-04).
        - Version snapshot appended to immutable history (I-01); request logged (I-05).
        All under skill lock + global request lock (I-12/Q10=A).
        """
        with self._lock_for(new_capsule.skill_id), self._request_lock:
            replay = self._replay_or_none(request_id, new_capsule.skill_id)
            if replay is not None:
                return replay

            current = self._capsules.get(new_capsule.skill_id)
            current_version = current.version if current is not None else 0
            if current_version != expected_base_version:
                raise StaleBaseVersion(
                    "base_version does not match current latest version.",
                    detail={"expected": expected_base_version, "current": current_version},
                )
            self._commit_locked(new_capsule, request_id, origin=origin)
            return new_capsule

    # ----- internals (must hold BOTH skill lock and request lock) ------------
    def _replay_or_none(self, request_id: str, skill_id: str) -> Optional[Capsule]:
        prior = self._request_log.get(request_id)
        if prior is None:
            return None
        # M2: a request_id is bound to the skill it first operated on. Reusing it against a
        # different skill is a client error, NOT a silent no-op returning a foreign capsule.
        if prior.skill_id != skill_id:
            raise ValidationError(
                "request_id was already used for a different skill_id.",
                detail={"request_id": request_id, "bound_skill_id": prior.skill_id, "requested_skill_id": skill_id},
            )
        # M1: return the exact capsule this request produced.
        return prior

    def _commit_locked(self, capsule: Capsule, request_id: str, origin: str) -> None:
        # 1) build immutable snapshot for the new version (I-01)
        snapshot = capsule.snapshot_version(request_id=request_id, origin=origin)
        # 2) atomic pointer swap
        self._capsules[capsule.skill_id] = capsule
        # 3) append version history
        self._history.setdefault(capsule.skill_id, []).append(snapshot)
        # 4) record idempotency with the EXACT produced capsule (same atomic unit, I-05/I-12/M1)
        self._request_log[request_id] = capsule
