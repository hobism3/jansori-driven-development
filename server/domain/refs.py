"""RefsGraph — depth-1 storage relationship enforcement (I-15, D-06).

I-15: storage relationship depth <= 1. A registration or refs change that would
create a grandchild is rejected with DEPTH_LIMIT and NO state change. This is NOT
substituted by "ignore stored grandchild on read" — the relationship itself is
refused. Checked on BOTH new registration AND refs change.
"""
from __future__ import annotations

from typing import Callable, Iterable, Optional

from .errors import DepthLimit


def assert_depth_one(
    parent_id: str,
    child_ids: Iterable[str],
    get_child_refs: Callable[[str], Optional[list[str]]],
) -> None:
    """Raise DepthLimit if any proposed child already has children (would be a grandparent).

    Args:
        parent_id: the capsule that will hold `child_ids` as refs_children.
        child_ids: proposed direct children (depth-1).
        get_child_refs: resolver returning a child's own refs_children, or None if absent.

    A child that itself declares refs_children means linking it under `parent_id`
    creates a grandchild -> DEPTH_LIMIT.
    """
    violating: list[dict] = []
    for child_id in child_ids:
        if child_id == parent_id:
            violating.append({"child": child_id, "reason": "self-reference"})
            continue
        grandchildren = get_child_refs(child_id)
        if grandchildren:
            violating.append(
                {
                    "child": child_id,
                    "path": f"{parent_id} -> {child_id} -> {list(grandchildren)}",
                    "grandchildren": list(grandchildren),
                }
            )
    if violating:
        raise DepthLimit(
            "Storage relationship would exceed depth-1 (grandchild not allowed).",
            detail={
                "violations": violating,
                "recommendation": "Detach the offending child's own children or flatten the hierarchy.",
            },
        )


# NOTE: the "upward" depth-1 case — a capsule that is ALREADY a child gaining its own
# children (e.g. via protected-change refs_children) — is enforced in NagService using
# CapsuleStore.is_referenced_as_child(), because it requires a reverse lookup over stored
# capsules that this pure-function module deliberately does not own.
