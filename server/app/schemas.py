"""Request/response schemas (pydantic v2).

SPEC 5 no-collection: NONE of these carry task source, prompts, or conversation
transcripts. Only capsule content, correction text, and control fields are accepted.
`request_id` is REQUIRED on all writes for idempotency (I-05, Q10=A).
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class AssetIn(BaseModel):
    name: str
    path: str
    is_script: bool = False
    summary: str = ""


class RegisterInput(BaseModel):
    skill_id: str = Field(min_length=1)
    name: str = ""
    description: str = ""
    body: str = ""
    refs_children: list[str] = Field(default_factory=list)
    assets: list[AssetIn] = Field(default_factory=list)
    request_id: str = Field(min_length=1)


class LoadInput(BaseModel):
    session_id: str = Field(min_length=1)


class NagInput(BaseModel):
    correction_text: str = Field(min_length=1)
    base_version: int = Field(ge=0)
    request_id: str = Field(min_length=1)


class ProtectedChangeInput(BaseModel):
    field: str = Field(min_length=1)
    new_value: Any = None
    base_version: int = Field(ge=0)
    approval_flag: bool = False
    request_id: str = Field(min_length=1)


class NormalizeInput(BaseModel):
    base_version: int = Field(ge=0)
    new_body: str
    request_id: str = Field(min_length=1)
    # ids of the corrections the subagent merged into new_body (declaration).
    # U1-reopen redesign: preservation is validated by this declaration + length,
    # NOT by verbatim-substring survival — so the subagent may condense/paraphrase.
    merged_correction_ids: list[str] = Field(min_length=1)
