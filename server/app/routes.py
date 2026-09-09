"""Route wiring (CMP-01) — thin adapter delegating to services.

Endpoints (D-02):
  GET  /skills/index
  GET  /skills/{id}
  POST /skills/register
  POST /skills/{id}/load
  POST /skills/{id}/nag
  POST /skills/{id}/protected-change
  POST /skills/{id}/normalize
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, FastAPI

from ..services.normalization_service import NormalizationService
from ..services.nag_service import NagService
from ..services.session_service import SessionService
from ..services.skill_service import SkillService
from ..store.capsule_store import CapsuleStore
from .schemas import (
    LoadInput,
    NagInput,
    NormalizeInput,
    ProtectedChangeInput,
    RegisterInput,
)


@dataclass
class Container:
    store: CapsuleStore
    sessions: SessionService
    skills: SkillService
    nags: NagService
    normalization: NormalizationService

    @classmethod
    def build(cls, data_file: "str | None" = None) -> "Container":
        # data_file=None => in-memory (test / TestClient / module-app default, keeps tests
        # isolated). The server entrypoint (main()) resolves the env and passes a path so a
        # running instance persists across restarts (U1 reopen 2026-09-09).
        store = CapsuleStore(data_file=data_file)
        sessions = SessionService()
        return cls(
            store=store,
            sessions=sessions,
            skills=SkillService(store, sessions),
            nags=NagService(store, sessions),
            normalization=NormalizationService(store),
        )


def register_routes(app: FastAPI, container: Container) -> None:
    router = APIRouter()

    @router.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @router.get("/skills/index")
    def get_index(session_id: str | None = None) -> dict:
        # session_id accepted for parity with hook injection; index is name/description only.
        return {"entries": container.skills.build_index()}

    @router.get("/skills/resolve-target")
    def resolve_target(hint: str | None = None, session_id: str = "") -> dict:
        # Surfaces I-13 (US-08) over HTTP: resolve a nag target within the active session
        # scope. Unique match -> {"target": id}; ambiguous/none -> NEEDS_CONFIRMATION (409).
        return {"target": container.nags.resolve_target(hint, session_id)}

    @router.get("/skills/{skill_id}")
    def get_skill(skill_id: str) -> dict:
        return container.skills.get_capsule(skill_id)

    @router.post("/skills/register")
    def register(payload: RegisterInput) -> dict:
        return container.skills.register(
            payload.model_dump(exclude={"request_id"}), request_id=payload.request_id
        )

    @router.post("/skills/{skill_id}/load")
    def load(skill_id: str, payload: LoadInput) -> dict:
        return container.skills.load(skill_id, payload.session_id)

    @router.post("/skills/{skill_id}/nag")
    def nag(skill_id: str, payload: NagInput) -> dict:
        return container.nags.apply_nag(
            skill_id,
            correction_text=payload.correction_text,
            base_version=payload.base_version,
            request_id=payload.request_id,
        )

    @router.post("/skills/{skill_id}/protected-change")
    def protected_change(skill_id: str, payload: ProtectedChangeInput) -> dict:
        return container.nags.apply_protected_change(
            skill_id,
            field=payload.field,
            new_value=payload.new_value,
            base_version=payload.base_version,
            approval_flag=payload.approval_flag,
            request_id=payload.request_id,
        )

    @router.post("/skills/{skill_id}/normalize")
    def normalize(skill_id: str, payload: NormalizeInput) -> dict:
        # "normalize" = Capsule Normalization (SPEC compaction) — NOT context compaction.
        return container.normalization.commit_normalization(
            skill_id,
            base_version=payload.base_version,
            new_body=payload.new_body,
            request_id=payload.request_id,
            merged_correction_ids=payload.merged_correction_ids,
        )

    app.include_router(router)
