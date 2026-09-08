# Build/Seed Summary (CMP-13)

## Makefile targets
| Target | Command | Notes |
|---|---|---|
| `install` | `pip install -e ".[dev]"` | server + pytest/hypothesis/httpx |
| `run` | `python -m server.app.main` | EMPTY in-memory store, loopback 127.0.0.1:8765 (Q9) |
| `seed` | `python scripts/seed.py` | populate a RUNNING server (generic, DEV-38) |
| `verify` | `pytest tests/verify -q` | real-server boot/teardown contract (US-17) |
| `pbt` | `pytest tests/pbt -q` | Hypothesis PBT |
| `test` | `pytest tests -q` | full suite |

`PY ?= python` override; Windows note documents running recipes directly if GNU Make absent.

## scripts/seed.py (generic — DEV-38)
- Globs `fixtures/seed/*.json` (no hardcoded ids / count).
- **Field mapping**: `refs`→`refs_children`; `keywords`/`version`/`created_at` dropped (no API
  field; server owns version/time); `assets` passed through; registers via loopback HTTP
  (`jansori_client.request`, includes assets).
- **Ordering**: leaves first (`order_by_refs`) so parents reference resolvable depth-1 children;
  cycle-safe (leftovers appended).
- **Corrections replay**: register creates v1 with no corrections, so declared `corrections[]`
  are re-applied as `nag` calls in order (generic text extraction: str / `instruction_text` /
  `text`).
- **Idempotent within a server lifetime**: stable request_ids (`seed-<id>`, `seed-<id>-nag-<seq>`)
  → re-running `make seed` replays instead of raising DUPLICATE_REGISTRATION.
- **§5**: loopback-only; asset scripts are NEVER executed (server returns notices).

## Smoke-verified (README-u4)
Live server on an ephemeral port: 3 seed capsules registered leaves-first, Korean UTF-8
preserved, re-seed idempotent.
