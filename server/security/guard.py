"""SecurityGuard (CMP-06) — SPEC 5 boundary (US-15).

- assert_loopback: server binds only to loopback (127.0.0.1 / ::1).
- contain_path: asset/refs file writes are contained inside a designated temp dir
  (path-traversal blocked).
- guard_script: scripts are never auto-executed; a summary notice requires explicit consent.
- No-collection: the server never collects/stores task source, prompts, or conversation
  transcripts (enforced by never accepting/persisting such fields — see schemas/models).
"""
from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass
from pathlib import Path

from ..domain.errors import ValidationError

_LOOPBACK_HOSTNAMES = {"localhost"}


def assert_loopback(host: str) -> None:
    """Raise ValidationError unless `host` is a loopback address/hostname.

    Accepts 127.0.0.0/8, ::1, and 'localhost'. Any routable interface is refused so
    the server is never exposed beyond the local machine (SPEC 5).
    """
    normalized = (host or "").strip().strip("[]")
    if normalized in _LOOPBACK_HOSTNAMES:
        return
    try:
        ip = ipaddress.ip_address(normalized)
    except ValueError as exc:
        raise ValidationError(
            f"Bind host '{host}' is not a recognized loopback address.",
            detail={"host": host},
        ) from exc
    if not ip.is_loopback:
        raise ValidationError(
            f"Refusing to bind non-loopback host '{host}' (SPEC 5 loopback-only).",
            detail={"host": host},
        )


def contain_path(base_tmp: Path, target: str) -> Path:
    """Return the resolved absolute path IFF it stays inside base_tmp; else raise.

    Blocks path-traversal (e.g. '../') and absolute escapes (SPEC 5).
    """
    base = Path(base_tmp).resolve()
    candidate = (base / target).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise ValidationError(
            "Asset path escapes the designated temp directory (path-traversal blocked).",
            detail={"base": str(base), "target": target},
        ) from exc
    return candidate


@dataclass(frozen=True)
class ScriptNotice:
    """Result of guard_script: a script asset was detected; NOT executed."""

    name: str
    summary: str
    requires_consent: bool = True


def guard_script(name: str, is_script: bool, summary: str = "") -> ScriptNotice | None:
    """Return a ScriptNotice for script assets (never auto-execute). None otherwise."""
    if not is_script:
        return None
    return ScriptNotice(
        name=name,
        summary=summary or f"Script asset '{name}' detected. It will NOT be executed automatically.",
        requires_consent=True,
    )


def default_temp_dir() -> Path:
    """Designated temp base for asset containment (configurable via JANSORI_TEMP_DIR)."""
    raw = os.environ.get("JANSORI_TEMP_DIR")
    base = Path(raw) if raw else Path(os.environ.get("TEMP", ".")) / "jansori"
    base.mkdir(parents=True, exist_ok=True)
    return base.resolve()
