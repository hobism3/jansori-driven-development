"""Domain-specific Hypothesis strategies for the Jansori Capsule domain (PBT-07).

Poor generators (bare `st.text()` for a body, unbounded ints for a version) miss real
bugs. These strategies respect the U1 domain constraints:

- skill_id: non-empty slug (schema requires min_length=1); a bounded alphabet so the
  same ids recur across a run (realistic for register/nag/refs targeting).
- body / correction_text: bounded, may include Unicode + empty, with boundary lengths
  around the content limit L (I-09).
- refs_children: lists of skill_ids (depth-1 semantics enforced by the store, not here).
- register payloads / nag texts: structurally valid request bodies.

Reusable across tests/pbt/* (PBT-07 centralization).
"""
from __future__ import annotations

from hypothesis import strategies as st

from server.domain.limits import LIMITS

L = LIMITS.max_content_length

# A small, recurring id alphabet so generated sequences actually collide on ids
# (register the same skill, nag an existing skill, reference a real child).
_ID_ALPHABET = "abcdefghijklmnopqrstuvwxyz-_0123456789"


def skill_ids(max_size: int = 12):
    """Non-empty slug-like ids (schema: min_length=1)."""
    return st.text(alphabet=_ID_ALPHABET, min_size=1, max_size=max_size)


def small_skill_ids():
    """A tiny id space so sequences reuse ids (collisions/duplicates are interesting)."""
    return st.sampled_from(["sk-a", "sk-b", "sk-c", "sk-d"])


def names():
    # includes Unicode (Korean capsule names are real) and empty (schema default "").
    return st.text(min_size=0, max_size=40)


def descriptions():
    return st.text(min_size=0, max_size=120)


def bodies(max_size: int = 200):
    """Bounded body text incl. empty + Unicode; well under L for combinable sequences."""
    return st.text(min_size=0, max_size=max_size)


def boundary_bodies():
    """Bodies at/around the content limit L (I-09 boundary): L-1, L, L+1."""
    return st.sampled_from([("x" * (L - 1), True), ("x" * L, True), ("x" * (L + 1), False)])


def correction_texts(max_size: int = 120):
    """Non-empty correction text (schema: min_length=1)."""
    return st.text(min_size=1, max_size=max_size)


def refs_children(ids=None, max_size: int = 3):
    ids = small_skill_ids() if ids is None else ids
    return st.lists(ids, max_size=max_size, unique=True)


def register_payloads(id_strategy=None):
    """A structurally valid /skills/register body (request_id added by the test)."""
    id_strategy = small_skill_ids() if id_strategy is None else id_strategy
    return st.builds(
        lambda sid, nm, ds, bd: {
            "skill_id": sid,
            "name": nm,
            "description": ds,
            "body": bd,
            "refs_children": [],
        },
        id_strategy,
        names(),
        descriptions(),
        bodies(),
    )
