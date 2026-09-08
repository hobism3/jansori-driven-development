"""SessionService (CMP-05) — server-side session records (D-01).

The server-side session is the single source of truth for active scope and progress
flags. I-02: records the actual loaded parent/children ids+versions. I-10: progress
flags are stored separately from content, so flag toggles never change capsule bytes.
In-memory, not persisted (Q9).
"""
from __future__ import annotations

import threading
from typing import Optional

from ..domain.models import Session


class SessionService:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.RLock()

    def get_or_create_session(self, session_id: str) -> Session:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                session = Session(session_id=session_id)
                self._sessions[session_id] = session
            return session

    def set_active_scope(
        self,
        session_id: str,
        parent: dict,               # {"skill_id": str, "version": int}
        children: list[dict],       # [{"skill_id","version"}]
    ) -> None:
        """Record the actually-loaded parent/children ids+versions (I-02)."""
        with self._lock:
            session = self.get_or_create_session(session_id)
            session.active_parent = {"skill_id": parent["skill_id"], "version": parent["version"]}
            session.active_children = [
                {"skill_id": c["skill_id"], "version": c["version"]} for c in children
            ]

    def set_progress_flag(self, session_id: str, skill_id: str, flag: str, value: bool) -> None:
        """Update a progress flag (content-separate, I-10)."""
        with self._lock:
            session = self.get_or_create_session(session_id)
            session.set_flag(skill_id, flag, value)

    def active_scope_ids(self, session_id: str) -> list[str]:
        """skill_ids in the active scope (parent + children) — for resolve_target (I-13)."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return []
            ids: list[str] = []
            if session.active_parent:
                ids.append(session.active_parent["skill_id"])
            ids.extend(c["skill_id"] for c in session.active_children)
            return ids

    def get_session(self, session_id: str) -> Optional[Session]:
        with self._lock:
            session = self._sessions.get(session_id)
            return session.copy() if session else None
