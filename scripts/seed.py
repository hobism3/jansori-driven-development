#!/usr/bin/env python3
"""Generic Capsule seed loader (U4 · CMP-13 · DEV-38).

Populates a RUNNING Jansori server (in-memory; `make run` starts empty) from every
`fixtures/seed/*.json` file. GENERIC — no hardcoded skill ids, no hardcoded count:
it globs whatever seed files exist and maps their fields to the register contract.

Seed file shape (see fixtures/seed/*.json):
    skill_id, name, description, body, refs[], assets[], corrections[], keywords[], version, created_at
Mapping to the API:
    refs                 -> refs_children          (register)
    keywords/version/created_at -> dropped         (no API field; server owns version/time)
    assets               -> assets[]               (passed through)
    corrections[]        -> replayed as nag calls  (register creates v1 with no corrections,
                                                     so declared corrections are re-applied)

Ordering: leaves (no refs) are registered first so parents reference resolvable children
(depth-1). Idempotent within one server lifetime via stable per-item request_ids, so
re-running `make seed` against an already-seeded server replays rather than errors.

Talks to the server over loopback HTTP only, reusing the bundled client. NEVER executes
asset scripts (SPEC 5); script assets surface as notices from the server.
"""
from __future__ import annotations

import glob
import json
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _p in (_ROOT, os.path.join(_ROOT, "plugin", "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import jansori_client as jc  # noqa: E402

SEED_DIR = os.path.join(_ROOT, "fixtures", "seed")
TIMEOUT_MS = 5000


def load_seed_files(seed_dir: str = SEED_DIR) -> list[dict]:
    files = sorted(glob.glob(os.path.join(seed_dir, "*.json")))
    records = []
    for path in files:
        with open(path, encoding="utf-8") as fh:
            records.append(json.load(fh))
    return records


def order_by_refs(records: list[dict]) -> list[dict]:
    """Leaves first, then capsules whose refs are already scheduled (stable, cycle-safe)."""
    remaining = list(records)
    scheduled: list[dict] = []
    scheduled_ids: set[str] = set()
    # deterministic: repeatedly take records whose refs are all already scheduled.
    progress = True
    while remaining and progress:
        progress = False
        for rec in list(remaining):
            refs = rec.get("refs", []) or []
            if all(r in scheduled_ids or r not in {x["skill_id"] for x in records} for r in refs):
                scheduled.append(rec)
                scheduled_ids.add(rec["skill_id"])
                remaining.remove(rec)
                progress = True
    scheduled.extend(remaining)  # any cycle leftovers appended as-is
    return scheduled


def _correction_text(item) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return item.get("instruction_text") or item.get("text") or json.dumps(item, ensure_ascii=False)
    return str(item)


def register_record(rec: dict) -> dict:
    sid = rec["skill_id"]
    body = {
        "skill_id": sid,
        "name": rec.get("name", sid),
        "description": rec.get("description", ""),
        "body": rec.get("body", ""),
        "refs_children": rec.get("refs", []) or [],
        "assets": rec.get("assets", []) or [],
        "request_id": f"seed-{sid}",
    }
    return jc.request("POST", "/skills/register", body=body, timeout_ms=TIMEOUT_MS)


def replay_corrections(rec: dict) -> list[dict]:
    sid = rec["skill_id"]
    results = []
    # start from the current server version so re-seeding stays consistent.
    got = jc.act_get(sid, TIMEOUT_MS)
    version = int(got["data"]["version"]) if got.get("ok") else 1
    for seq, item in enumerate(rec.get("corrections", []) or [], start=1):
        r = jc.act_nag(sid, _correction_text(item), request_id=f"seed-{sid}-nag-{seq}",
                       base_version=version, timeout_ms=TIMEOUT_MS)
        results.append(r)
        if r.get("ok"):
            version = r["data"]["new_version"]
    return results


def seed(seed_dir: str = SEED_DIR) -> int:
    records = load_seed_files(seed_dir)
    if not records:
        print(f"[seed] no seed files found in {seed_dir}")
        return 0
    ordered = order_by_refs(records)
    ok_count = 0
    for rec in ordered:
        reg = register_record(rec)
        status = "ok" if reg.get("ok") else f"{reg.get('code')}"
        print(f"[seed] register {rec['skill_id']:<22} -> {status}")
        if reg.get("ok"):
            ok_count += 1
            notices = reg["data"].get("script_notices") or []
            for n in notices:
                print(f"[seed]   script notice (NOT executed): {n.get('name')}")
        for cr in replay_corrections(rec):
            tag = "ok" if cr.get("ok") else cr.get("code")
            print(f"[seed]   nag {rec['skill_id']} -> {tag}")
    print(f"[seed] done: {ok_count}/{len(records)} capsules registered.")
    return 0


def main() -> int:
    return seed()


if __name__ == "__main__":
    raise SystemExit(main())
