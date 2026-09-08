"""Domain entities (technology-neutral core).

Entities: Capsule (aggregate root), Version, Correction, Asset, Session, IndexEntry.
See aidlc-docs/construction/U1-server-store-contracts/functional-design/domain-entities.md.

Invariants touched here:
- I-01: a Version's body_snapshot is immutable; content change => version + 1.
- I-14: PROTECTED_FIELDS is a fixed set (Q9=A).
- I-05: Correction carries request_id + seq for idempotency/ordering.
"""
from __future__ import annotations

import copy
import time
from dataclasses import dataclass, field, replace
from typing import Optional

# I-14 / Q9=A: fixed set of protected fields (changing these requires protected-change).
PROTECTED_FIELDS: tuple[str, ...] = ("skill_id", "name", "refs_children", "protected_fields")


def _now() -> float:
    return time.time()


@dataclass(frozen=True)
class Asset:
    """Attached asset metadata. File writes are temp-dir contained (SPEC 5)."""

    name: str
    path: str
    is_script: bool = False

    def key(self) -> str:
        return self.name


@dataclass(frozen=True)
class Correction:
    """A single, not-yet-merged nag (Q3=A)."""

    id: str
    target: str          # skill_id (parent or loaded child) — I-13
    instruction_text: str
    request_id: str      # idempotency key — I-05
    seq: int             # accumulation order (1..)
    created_at: float = field(default_factory=_now)


@dataclass(frozen=True)
class Version:
    """Immutable content snapshot (I-01)."""

    number: int          # monotonic integer (Q1=A)
    body_snapshot: str
    request_id: str
    origin: str          # register | nag | normalize | protected_change
    created_at: float = field(default_factory=_now)


@dataclass(frozen=True)
class Capsule:
    """Aggregate root — single source of truth for one skill.

    Immutable dataclass: all mutations produce a NEW Capsule (copy-on-write),
    which the store swaps in atomically (I-12). Never mutate in place.
    """

    skill_id: str
    name: str
    description: str
    body: str
    version: int
    corrections: tuple[Correction, ...] = ()
    refs_children: tuple[str, ...] = ()
    assets: tuple[Asset, ...] = ()
    protected_fields: tuple[str, ...] = PROTECTED_FIELDS
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    # ----- derived / helpers -------------------------------------------------
    def next_version_number(self) -> int:
        return self.version + 1

    def with_new_content(
        self,
        *,
        body: Optional[str] = None,
        description: Optional[str] = None,
        corrections: Optional[tuple[Correction, ...]] = None,
        refs_children: Optional[tuple[str, ...]] = None,
        name: Optional[str] = None,
        assets: Optional[tuple[Asset, ...]] = None,
        protected_fields: Optional[tuple[str, ...]] = None,
    ) -> "Capsule":
        """Return a new Capsule with version+1 (content change, I-01)."""
        return replace(
            self,
            body=self.body if body is None else body,
            description=self.description if description is None else description,
            name=self.name if name is None else name,
            corrections=self.corrections if corrections is None else corrections,
            refs_children=self.refs_children if refs_children is None else refs_children,
            assets=self.assets if assets is None else assets,
            protected_fields=self.protected_fields if protected_fields is None else protected_fields,
            version=self.next_version_number(),
            updated_at=_now(),
        )

    def snapshot_version(self, request_id: str, origin: str) -> Version:
        return Version(
            number=self.version,
            body_snapshot=self.body,
            request_id=request_id,
            origin=origin,
        )

    def to_index_entry(self) -> "IndexEntry":
        return IndexEntry(skill_id=self.skill_id, name=self.name, description=self.description)

    def public_dict(self) -> dict:
        """Serialization-friendly view (used by API layer / subagent GET)."""
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "body": self.body,
            "version": self.version,
            "corrections": [
                {
                    "id": c.id,
                    "target": c.target,
                    "instruction_text": c.instruction_text,
                    "request_id": c.request_id,
                    "seq": c.seq,
                    "created_at": c.created_at,
                }
                for c in self.corrections
            ],
            "refs_children": list(self.refs_children),
            "assets": [{"name": a.name, "path": a.path, "is_script": a.is_script} for a in self.assets],
            "protected_fields": list(self.protected_fields),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class IndexEntry:
    """Name/description only — for hook injection (I: no body, no LLM)."""

    skill_id: str
    name: str
    description: str


@dataclass
class Session:
    """Server-side session record (D-01). Mutable; guarded by SessionService.

    I-10: progress_flags are separate from content — toggling them never changes
    any Capsule content bytes.
    """

    session_id: str
    active_parent: Optional[dict] = None          # {"skill_id": str, "version": int}
    active_children: list[dict] = field(default_factory=list)  # [{"skill_id","version"}]
    progress_flags: dict[str, dict[str, bool]] = field(default_factory=dict)  # skill_id -> {flag: bool}

    def set_flag(self, skill_id: str, flag: str, value: bool) -> None:
        self.progress_flags.setdefault(skill_id, {})[flag] = value

    def get_flag(self, skill_id: str, flag: str) -> bool:
        return self.progress_flags.get(skill_id, {}).get(flag, False)

    def copy(self) -> "Session":
        return Session(
            session_id=self.session_id,
            active_parent=copy.deepcopy(self.active_parent),
            active_children=copy.deepcopy(self.active_children),
            progress_flags=copy.deepcopy(self.progress_flags),
        )
