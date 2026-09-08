"""Structured domain errors (D-03).

Error envelope (D-03):
    { "error": { "code": <CODE>, "message": "...", "detail"?: {...} } }

I-07: SERVER_ERROR (server failure) and SKILL_ABSENT (skill missing, server OK) are
distinct codes so callers (U2) never mistake an outage for absence.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional


class ErrorCode(str, Enum):
    STALE_BASE_VERSION = "STALE_BASE_VERSION"
    OVER_LENGTH = "OVER_LENGTH"
    PROTECTED_CHANGE_DENIED = "PROTECTED_CHANGE_DENIED"
    SKILL_ABSENT = "SKILL_ABSENT"
    SERVER_ERROR = "SERVER_ERROR"
    DEPTH_LIMIT = "DEPTH_LIMIT"
    DUPLICATE_REGISTRATION = "DUPLICATE_REGISTRATION"
    PRESERVATION_FAILED = "PRESERVATION_FAILED"
    NEEDS_CONFIRMATION = "NEEDS_CONFIRMATION"
    VALIDATION_ERROR = "VALIDATION_ERROR"


class DomainError(Exception):
    """Base class carrying a structured error code + optional detail."""

    code: ErrorCode = ErrorCode.SERVER_ERROR

    def __init__(self, message: str, detail: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail or {}

    def to_envelope(self) -> dict[str, Any]:
        env: dict[str, Any] = {"code": self.code.value, "message": self.message}
        if self.detail:
            env["detail"] = self.detail
        return {"error": env}


class StaleBaseVersion(DomainError):
    code = ErrorCode.STALE_BASE_VERSION


class OverLength(DomainError):
    code = ErrorCode.OVER_LENGTH


class ProtectedChangeDenied(DomainError):
    code = ErrorCode.PROTECTED_CHANGE_DENIED


class SkillAbsent(DomainError):
    code = ErrorCode.SKILL_ABSENT


class ServerError(DomainError):
    code = ErrorCode.SERVER_ERROR


class DepthLimit(DomainError):
    code = ErrorCode.DEPTH_LIMIT


class DuplicateRegistration(DomainError):
    code = ErrorCode.DUPLICATE_REGISTRATION


class PreservationFailed(DomainError):
    code = ErrorCode.PRESERVATION_FAILED


class NeedsConfirmation(DomainError):
    code = ErrorCode.NEEDS_CONFIRMATION


class ValidationError(DomainError):
    code = ErrorCode.VALIDATION_ERROR
