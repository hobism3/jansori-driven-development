"""Map DomainError -> HTTP response with the D-03 structured envelope.

I-07: SERVER_ERROR and SKILL_ABSENT map to distinct statuses/codes so callers never
conflate an outage with absence.
"""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from ..domain.errors import DomainError, ErrorCode

_STATUS_BY_CODE: dict[ErrorCode, int] = {
    ErrorCode.STALE_BASE_VERSION: 409,
    ErrorCode.OVER_LENGTH: 413,
    ErrorCode.PROTECTED_CHANGE_DENIED: 403,
    ErrorCode.SKILL_ABSENT: 404,
    ErrorCode.SERVER_ERROR: 500,
    ErrorCode.DEPTH_LIMIT: 409,
    ErrorCode.DUPLICATE_REGISTRATION: 409,
    ErrorCode.PRESERVATION_FAILED: 422,
    ErrorCode.NEEDS_CONFIRMATION: 409,
    ErrorCode.VALIDATION_ERROR: 400,
}


def http_status_for(code: ErrorCode) -> int:
    return _STATUS_BY_CODE.get(code, 500)


async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=http_status_for(exc.code), content=exc.to_envelope())


async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    # Any unexpected failure is SERVER_ERROR (I-07) — never SKILL_ABSENT.
    return JSONResponse(
        status_code=500,
        content={"error": {"code": ErrorCode.SERVER_ERROR.value, "message": "internal server error"}},
    )
