"""NagService (CMP-03) — apply_nag, resolve_target, check_threshold, protected-change.

Stories: US-07 (nag + version), US-08 (target resolution), US-09 (protected change),
US-10 (threshold/idempotency/atomic).
Invariants: I-01, I-04, I-05, I-09, I-13, I-14.
"""
from __future__ import annotations

import uuid
from typing import Optional

from ..domain.errors import (
    DepthLimit,
    NeedsConfirmation,
    OverLength,
    ProtectedChangeDenied,
    SkillAbsent,
    ValidationError,
)
from ..domain.limits import LIMITS, Limits
from ..domain.models import PROTECTED_FIELDS, Capsule, Correction
from ..domain.refs import assert_depth_one
from ..store.capsule_store import CapsuleStore
from .session_service import SessionService


class NagService:
    def __init__(
        self,
        store: CapsuleStore,
        sessions: SessionService,
        limits: Limits = LIMITS,
    ) -> None:
        self._store = store
        self._sessions = sessions
        self._limits = limits

    # ----- helpers -----------------------------------------------------------
    def _assert_len(self, text: str, what: str) -> None:
        if len(text) > self._limits.max_content_length:
            raise OverLength(
                f"{what} exceeds max content length; content preserved, change refused.",
                detail={"what": what, "length": len(text), "limit": self._limits.max_content_length},
            )

    def _normalize_due(self, corrections_count: int) -> bool:
        # Q7=A: fires at threshold; latched (>=) so it stays due while normalization is
        # pending and additional nags keep accumulating (I-10). Cleared when corrections
        # are emptied on a successful normalization commit.
        return corrections_count >= self._limits.normalization_threshold

    @staticmethod
    def _assert_request_skill(prior, skill_id: str, request_id: str) -> None:
        """M2: a request_id is bound to the skill it first operated on; reusing it against
        a different skill is a client error, not a foreign-capsule replay."""
        if prior.skill_id != skill_id:
            raise ValidationError(
                "request_id was already used for a different skill_id.",
                detail={"request_id": request_id, "bound_skill_id": prior.skill_id, "requested_skill_id": skill_id},
            )

    # ----- resolve_target (I-13) ---------------------------------------------
    def resolve_target(self, hint: Optional[str], session_id: str) -> str:
        """Resolve nag target within the active session scope (Q5=A, I-13).

        Matches on EXACT skill_id within the active scope (parent + loaded children).
        Unique match -> that skill_id. Zero or multiple (or no hint) -> NEEDS_CONFIRMATION.
        No default parent auto-attribution, no loose substring matching (that could yield a
        wrong "unique" match). Name-based selection is a client (U2) concern using the
        index; the server resolves against ids it actually recorded as loaded (I-02).
        """
        scope = self._sessions.active_scope_ids(session_id)
        if hint is None or hint.strip() == "":
            raise NeedsConfirmation(
                "No target hint provided; caller must confirm the target.",
                detail={"candidates": scope},
            )
        matches = [sid for sid in scope if sid == hint]
        if len(matches) == 1:
            return matches[0]
        raise NeedsConfirmation(
            "Target is ambiguous or not in active scope; caller must confirm.",
            detail={"hint": hint, "candidates": scope, "matches": matches},
        )

    # ----- check_threshold ---------------------------------------------------
    def check_threshold(self, skill_id: str) -> bool:
        capsule = self._store.get_latest(skill_id)
        if capsule is None:
            raise SkillAbsent("skill not found.", detail={"skill_id": skill_id})
        return self._normalize_due(len(capsule.corrections))

    # ----- apply_nag (US-07/US-10) -------------------------------------------
    def apply_nag(
        self,
        skill_id: str,
        correction_text: str,
        base_version: int,
        request_id: str,
    ) -> dict:
        """Accumulate a correction, bump immutable version (I-01), idempotent (I-05).

        `skill_id` is the already-resolved target (the path id). Length checked per
        correction (I-09). Stale base_version rejected (I-04). Returns normalize_due.
        """
        # idempotent replay short-circuit (I-05/M1): return the EXACT prior capsule.
        prior = self._store.get_request(request_id)
        if prior is not None:
            self._assert_request_skill(prior, skill_id, request_id)  # M2
            return {
                "capsule": prior.public_dict(),
                "new_version": prior.version,
                "normalize_due": self._normalize_due(len(prior.corrections)),
                "idempotent_replay": True,
            }

        capsule = self._store.get_latest(skill_id)
        if capsule is None:
            raise SkillAbsent("skill not found.", detail={"skill_id": skill_id})

        self._assert_len(correction_text, "correction")

        correction = Correction(
            id=str(uuid.uuid4()),
            target=skill_id,
            instruction_text=correction_text,
            request_id=request_id,
            seq=len(capsule.corrections) + 1,
        )
        new_capsule = capsule.with_new_content(corrections=capsule.corrections + (correction,))
        # atomic commit with stale check (I-04/I-12)
        stored = self._store.commit(
            new_capsule, request_id=request_id, origin="nag", expected_base_version=base_version
        )
        return {
            "capsule": stored.public_dict(),
            "new_version": stored.version,
            "normalize_due": self._normalize_due(len(stored.corrections)),
            "idempotent_replay": False,
        }

    # ----- protected-change (US-09, I-14) ------------------------------------
    def apply_protected_change(
        self,
        skill_id: str,
        field: str,
        new_value,
        base_version: int,
        approval_flag: bool,
        request_id: str,
    ) -> dict:
        """Change a protected field; requires approval + freshness (I-14/I-04)."""
        if field not in PROTECTED_FIELDS:
            raise ValidationError(
                f"'{field}' is not a protected field; use the nag path for body/corrections.",
                detail={"field": field, "protected_fields": list(PROTECTED_FIELDS)},
            )
        if not approval_flag:
            raise ProtectedChangeDenied(
                "Protected-field change requires an approval flag.",
                detail={"field": field},
            )

        # idempotent replay (I-05/M1): return the exact prior capsule
        prior = self._store.get_request(request_id)
        if prior is not None:
            self._assert_request_skill(prior, skill_id, request_id)  # M2
            return {"capsule": prior.public_dict(), "new_version": prior.version, "idempotent_replay": True}

        capsule = self._store.get_latest(skill_id)
        if capsule is None:
            raise SkillAbsent("skill not found.", detail={"skill_id": skill_id})

        kwargs = {}
        if field == "name":
            kwargs["name"] = str(new_value)
        elif field == "refs_children":
            children = tuple(new_value or [])
            # depth-1 re-check on refs change (I-15), BOTH directions:
            # (downward) proposed children must not already have their own children
            def resolve(child_id: str):
                child = self._store.get_latest(child_id)
                return list(child.refs_children) if child else None
            assert_depth_one(skill_id, children, resolve)
            # (upward) this capsule must not already be a child of another capsule — otherwise
            # giving it children creates a grandchild via the reverse path (B1 fix, I-15/D-06).
            if children and self._store.is_referenced_as_child(skill_id):
                raise DepthLimit(
                    "Capsule is already referenced as a child; it cannot gain its own "
                    "children (would create a depth-2 grandchild).",
                    detail={"skill_id": skill_id, "proposed_children": list(children),
                            "recommendation": "Detach this capsule from its parent first, or flatten."},
                )
            kwargs["refs_children"] = children
        elif field == "protected_fields":
            kwargs["protected_fields"] = tuple(new_value or [])
        elif field == "skill_id":
            # skill_id is the identity key; renaming would fork identity — refuse in v1.
            raise ProtectedChangeDenied(
                "skill_id is immutable in v1.", detail={"field": field}
            )

        new_capsule = capsule.with_new_content(**kwargs)
        stored = self._store.commit(
            new_capsule, request_id=request_id, origin="protected_change",
            expected_base_version=base_version,
        )
        return {"capsule": stored.public_dict(), "new_version": stored.version, "idempotent_replay": False}
