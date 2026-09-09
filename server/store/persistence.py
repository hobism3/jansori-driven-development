"""JSON-snapshot persistence for the Capsule store (optional, default-on for `make run`).

Design (U1 reopen, 2026-09-09; supersedes Q9 in-memory-only, user-authorized):
- The running server persists the whole store state to a single JSON file, written
  through on every commit (register/nag/protected-change/normalize). Reads never write.
- Scope: latest capsules + immutable version history (I-01). The idempotency
  request-log is NOT persisted (a restart is a fresh session).
- Atomicity: serialize the full state, write a temp file, then os.replace (atomic on
  Windows/POSIX) so a crash mid-write never leaves a torn snapshot (I-12 preserved).
- Load: on startup, a missing OR corrupt file yields an empty store (fail-safe, no crash).

Serialization reuses Capsule.public_dict() (already a full, round-trippable view);
deserialization rebuilds the frozen domain objects here so server/domain/models.py
stays untouched.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Optional

from ..domain.models import Asset, Capsule, Correction, Version

SNAPSHOT_VERSION = 1


def _correction_from_dict(d: dict) -> Correction:
    return Correction(
        id=d["id"], target=d["target"], instruction_text=d["instruction_text"],
        request_id=d["request_id"], seq=d["seq"], created_at=d["created_at"],
    )


def capsule_from_dict(d: dict) -> Capsule:
    return Capsule(
        skill_id=d["skill_id"], name=d["name"], description=d["description"],
        body=d["body"], version=d["version"],
        corrections=tuple(_correction_from_dict(c) for c in d.get("corrections", [])),
        refs_children=tuple(d.get("refs_children", [])),
        assets=tuple(Asset(name=a["name"], path=a["path"], is_script=a.get("is_script", False))
                     for a in d.get("assets", [])),
        protected_fields=tuple(d.get("protected_fields", [])),
        created_at=d["created_at"], updated_at=d["updated_at"],
    )


def _version_to_dict(v: Version) -> dict:
    return {"number": v.number, "body_snapshot": v.body_snapshot,
            "request_id": v.request_id, "origin": v.origin, "created_at": v.created_at}


def _version_from_dict(d: dict) -> Version:
    return Version(number=d["number"], body_snapshot=d["body_snapshot"],
                   request_id=d["request_id"], origin=d["origin"], created_at=d["created_at"])


def dump_state(capsules: dict[str, Capsule], history: dict[str, list[Version]]) -> dict:
    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "capsules": [c.public_dict() for c in capsules.values()],
        "history": {sid: [_version_to_dict(v) for v in vers] for sid, vers in history.items()},
    }


def atomic_write(path: Path, state: dict) -> None:
    """Write `state` as JSON to `path` atomically (temp file in the same dir + os.replace)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)  # atomic
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load_state(path: Optional[str | Path]) -> tuple[dict[str, Capsule], dict[str, list[Version]]]:
    """Load (capsules, history) from the snapshot. Missing/corrupt/invalid -> empty (fail-safe)."""
    if not path:
        return {}, {}
    p = Path(path)
    if not p.exists():
        return {}, {}
    try:
        with open(p, encoding="utf-8") as f:
            raw = json.load(f)
        capsules = {c["skill_id"]: capsule_from_dict(c) for c in raw.get("capsules", [])}
        history = {sid: [_version_from_dict(v) for v in vers]
                   for sid, vers in raw.get("history", {}).items()}
        return capsules, history
    except (ValueError, KeyError, OSError, TypeError):
        # Corrupt or schema-mismatched snapshot: start empty rather than crash the server.
        return {}, {}
