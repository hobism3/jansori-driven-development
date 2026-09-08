"""NormalizationService (CMP-04) — commit_normalization, validate_preservation.

SPEC term: "compaction". This is Capsule Normalization (server-side Capsule content),
UNRELATED to Claude Code context compaction. The server performs NO LLM merge — the
capsule-normalizer subagent (U3) produces new_body; the server validates + atomically
commits.

Stories: US-11. Invariants: I-04, I-11, I-12.
"""
from __future__ import annotations

from ..domain.errors import OverLength, PreservationFailed, SkillAbsent, ValidationError
from ..domain.limits import LIMITS, Limits
from ..domain.models import Capsule
from ..store.capsule_store import CapsuleStore


class NormalizationService:
    def __init__(self, store: CapsuleStore, limits: Limits = LIMITS) -> None:
        self._store = store
        self._limits = limits

    def validate_preservation(
        self, old: Capsule, new_body: str, merged_correction_ids: "list[str] | tuple[str, ...]"
    ) -> bool:
        """Structural preservation check (I-11). No semantic/LLM judgment.

        REDESIGN (2026-09-08, U1 reopen): the subagent may condense/paraphrase the
        corrections during Capsule Normalization (SPEC compaction), so we NO LONGER
        require each correction's instruction_text to survive as a verbatim substring.
        Instead we validate the merge DECLARATION structurally:

        (1) length <= L,
        (2) merged_correction_ids is non-empty and a subset of the corrections present
            at base (no unknown/foreign ids),
        refs/assets set-equality is guaranteed structurally because normalization only
        changes `body` (refs_children/assets are carried over unchanged on commit).

        Merge QUALITY (each declared correction actually reflected in new_body) is the
        subagent's responsibility; the server has no LLM and does not judge semantic
        reflection.
        """
        if len(new_body) > self._limits.max_content_length:
            return False
        declared = set(merged_correction_ids or ())
        if not declared:
            return False
        base_ids = {c.id for c in old.corrections}
        return declared.issubset(base_ids)

    def commit_normalization(
        self,
        skill_id: str,
        base_version: int,
        new_body: str,
        request_id: str,
        merged_correction_ids: "list[str] | tuple[str, ...]",
    ) -> dict:
        """Validate + atomically commit a normalized body (I-04/I-11/I-12).

        On success: body <- new_body, version + 1, ONLY the declared merged corrections
        are removed (later-arrived corrections are carried forward), refs/assets preserved,
        request logged. STALE_BASE_VERSION => caller (subagent) restarts from latest (I-04).
        PreservationFailed => no change (I-11).
        """
        # idempotent replay (I-05/M1): return the exact prior capsule
        prior = self._store.get_request(request_id)
        if prior is not None:
            if prior.skill_id != skill_id:  # M2
                raise ValidationError(
                    "request_id was already used for a different skill_id.",
                    detail={"request_id": request_id, "bound_skill_id": prior.skill_id,
                            "requested_skill_id": skill_id},
                )
            return {"capsule": prior.public_dict(), "new_version": prior.version, "idempotent_replay": True}

        capsule = self._store.get_latest(skill_id)
        if capsule is None:
            raise SkillAbsent("skill not found.", detail={"skill_id": skill_id})

        if len(new_body) > self._limits.max_content_length:
            raise OverLength(
                "normalized body exceeds max content length; commit refused.",
                detail={"length": len(new_body), "limit": self._limits.max_content_length},
            )
        if not self.validate_preservation(capsule, new_body, merged_correction_ids):
            raise PreservationFailed(
                "normalized body failed preservation check (declared merged ids / length / refs / assets).",
                detail={"skill_id": skill_id, "base_version": base_version},
            )

        # remove ONLY the declared merged corrections; carry any later-arrived ones forward.
        merged = set(merged_correction_ids)
        remaining = tuple(c for c in capsule.corrections if c.id not in merged)
        new_capsule = capsule.with_new_content(body=new_body, corrections=remaining)
        stored = self._store.commit(
            new_capsule, request_id=request_id, origin="normalize",
            expected_base_version=base_version,
        )
        return {"capsule": stored.public_dict(), "new_version": stored.version, "idempotent_replay": False}
