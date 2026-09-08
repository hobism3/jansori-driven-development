"""SkillService (CMP-02) — register, load + expand_refs, build_index.

Stories: US-01 (index), US-02 (load), US-03 (depth-1 expansion), US-06/US-14
(duplicate block / server-failure != duplicate).
Invariants: I-02, I-03, I-06, I-09, I-15.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from ..domain.errors import OverLength, SkillAbsent
from ..domain.limits import LIMITS, Limits
from ..domain.models import Asset, Capsule, IndexEntry
from ..domain.refs import assert_depth_one
from ..security import guard
from ..store.capsule_store import CapsuleStore
from .session_service import SessionService


class SkillService:
    def __init__(
        self,
        store: CapsuleStore,
        sessions: SessionService,
        limits: Limits = LIMITS,
        temp_dir: Optional[Path] = None,
    ) -> None:
        self._store = store
        self._sessions = sessions
        self._limits = limits
        self._temp_dir = temp_dir  # resolved lazily to avoid mkdir at import time

    # ----- helpers -----------------------------------------------------------
    def _assert_len(self, text: str, what: str) -> None:
        if len(text) > self._limits.max_content_length:
            raise OverLength(
                f"{what} exceeds max content length; content preserved, change refused.",
                detail={"what": what, "length": len(text), "limit": self._limits.max_content_length},
            )

    @staticmethod
    def _rendered(body: str, correction_texts: list[str]) -> str:
        """Composite render of a node = body + its corrections (as shown on load)."""
        if not correction_texts:
            return body
        return body + "\n" + "\n".join(correction_texts)

    def _assert_rendered_len(self, body: str, correction_texts: list[str], what: str) -> None:
        """I-09 / Q6=A: the composite render of a node (body + corrections) must be <= L."""
        rendered = self._rendered(body, correction_texts)
        if len(rendered) > self._limits.max_content_length:
            raise OverLength(
                f"{what} composite render exceeds max content length; change refused, "
                f"consider splitting/detaching children.",
                detail={
                    "what": what,
                    "rendered_length": len(rendered),
                    "limit": self._limits.max_content_length,
                },
            )

    def _temp_base(self) -> Path:
        if self._temp_dir is not None:
            return self._temp_dir
        return guard.default_temp_dir()

    def _validate_assets(self, assets: list[dict]) -> tuple[tuple[Asset, ...], list[dict]]:
        """Contain paths (SPEC 5) and collect script notices (never auto-execute)."""
        base = self._temp_base()
        built: list[Asset] = []
        notices: list[dict] = []
        for a in assets or []:
            name = a["name"]
            contained = guard.contain_path(base, a.get("path", name))
            is_script = bool(a.get("is_script", False))
            notice = guard.guard_script(name, is_script, a.get("summary", ""))
            if notice is not None:
                notices.append({"name": notice.name, "summary": notice.summary})
            built.append(Asset(name=name, path=str(contained), is_script=is_script))
        return tuple(built), notices

    def _child_refs_resolver(self):
        def resolve(child_id: str):
            child = self._store.get_latest(child_id)
            return list(child.refs_children) if child else None
        return resolve

    # ----- API ---------------------------------------------------------------
    def register(self, payload: dict, request_id: str) -> dict:
        """Register a new capsule (v1). US-06/US-14, I-06/I-09/I-15.

        Note: "similar re-search" is a CLIENT (U2) concern via build_index; the server
        blocks ONLY exact skill_id duplicates and never runs an LLM (Q4=A).
        """
        skill_id = payload["skill_id"]
        body = payload.get("body", "")
        refs_children = tuple(payload.get("refs_children", []) or [])

        # 1) security: contain asset paths, script notices
        assets, notices = self._validate_assets(payload.get("assets", []))
        # 2) length
        self._assert_len(body, "body")
        # 3) depth-1 (I-15): reject if any proposed child already has children
        assert_depth_one(skill_id, refs_children, self._child_refs_resolver())
        # 4) build v1 + atomic register. Idempotent replay (same request_id) and exact
        #    skill_id duplicate (I-06) are both resolved atomically inside store.register:
        #    a replay returns the prior capsule; a genuine duplicate raises. (No pre-exists
        #    check here — that would wrongly raise DUPLICATE on a legitimate replay.)
        capsule = Capsule(
            skill_id=skill_id,
            name=payload.get("name", skill_id),
            description=payload.get("description", ""),
            body=body,
            version=1,
            corrections=(),
            refs_children=refs_children,
            assets=assets,
        )
        stored = self._store.register(capsule, request_id)
        return {"capsule": stored.public_dict(), "script_notices": notices}

    def expand_refs(self, skill_id: str) -> dict:
        """Expand depth-1 direct children body+corrections (I-03, D-06)."""
        parent = self._store.get_latest(skill_id)
        if parent is None:
            raise SkillAbsent("skill not found.", detail={"skill_id": skill_id})
        children: list[dict] = []
        for child_id in parent.refs_children:
            child = self._store.get_latest(child_id)
            if child is None:
                # v1: missing child excluded from expansion + flagged (content integrity first).
                # (Documented deviation from BL-2: absent child is skipped, not an error.)
                children.append({"skill_id": child_id, "absent": True})
                continue
            child_corrections = [c.instruction_text for c in child.corrections]
            # I-09/Q6=A: check the child's COMPOSITE render (body + corrections), not body alone.
            self._assert_rendered_len(child.body, child_corrections, f"child ({child_id})")
            children.append(
                {
                    "skill_id": child.skill_id,
                    "version": child.version,
                    "name": child.name,
                    "body": child.body,
                    "corrections": child_corrections,
                    "absent": False,
                }
            )
        return {"parent_id": skill_id, "children": children}

    def load(self, skill_id: str, session_id: str) -> dict:
        """Load parent + expand depth-1 children, record active scope (I-02/I-03)."""
        parent = self._store.get_latest(skill_id)
        if parent is None:
            raise SkillAbsent("skill not found.", detail={"skill_id": skill_id})

        # I-09/Q6=A: parent composite render (body + corrections) must be <= L.
        parent_corrections = [c.instruction_text for c in parent.corrections]
        self._assert_rendered_len(parent.body, parent_corrections, "parent")
        expanded = self.expand_refs(skill_id)  # per-child composite length checked inside

        # record active scope with actually-loaded versions (I-02)
        child_scope = [
            {"skill_id": c["skill_id"], "version": c.get("version", 0)}
            for c in expanded["children"]
            if not c.get("absent")
        ]
        self._sessions.set_active_scope(
            session_id,
            parent={"skill_id": parent.skill_id, "version": parent.version},
            children=child_scope,
        )
        return {
            "parent": {
                "skill_id": parent.skill_id,
                "version": parent.version,
                "name": parent.name,
                "description": parent.description,
                "body": parent.body,
                "corrections": [c.instruction_text for c in parent.corrections],
            },
            "children": expanded["children"],
        }

    def build_index(self) -> list[dict]:
        """Name/description index for hook injection (US-01). No body, no LLM."""
        entries: list[IndexEntry] = [c.to_index_entry() for c in self._store.all_capsules()]
        return [{"skill_id": e.skill_id, "name": e.name, "description": e.description} for e in entries]

    def get_capsule(self, skill_id: str) -> dict:
        """GET /skills/{id} — full capsule JSON (used by capsule-normalizer subagent)."""
        capsule = self._store.get_latest(skill_id)
        if capsule is None:
            raise SkillAbsent("skill not found.", detail={"skill_id": skill_id})
        return capsule.public_dict()

    @staticmethod
    def new_request_id() -> str:
        return str(uuid.uuid4())
