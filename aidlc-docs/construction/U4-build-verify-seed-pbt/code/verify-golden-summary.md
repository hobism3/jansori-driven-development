# Verify & Golden Summary

## tests/conftest.py — centralized harness
- `LiveServer` + `free_loopback_port` + `live_url` fixture: a **real** uvicorn server on an
  ephemeral 127.0.0.1 port, torn down after each test. Centralizes the harness previously
  duplicated inline in `tests/unit/u2/test_hooks_integration.py` and
  `tests/unit/u3/test_normalize_integration.py` (those CLOSED-unit copies left untouched).
- `container`/`client`: fast in-process FastAPI `TestClient` over a fresh empty store.
- Hypothesis profiles + report header (PBT-08).

## tests/verify/test_verify_contract.py (US-17) — REAL server
Every test drives a genuine socket server through the bundled client over HTTP; a fake Store
is not accepted. Covers: health, register/index/load+refs, nag×3→normalize_due→normalize,
error matrix (STALE 409 / OVER_LENGTH 413 / SKILL_ABSENT 404 / DUPLICATE 409 /
PRESERVATION_FAILED 422 / NEEDS_CONFIRMATION 409), protected-change (denied 403 / approved),
DEV-29/32 (approval does not bypass stale; approve→retry idempotent), and client-side
non-loopback refusal (§5).

## tests/golden/ (example-based, PBT-10 complement)
- `test_core_paths.py`: DEV-02/09/13/34/03/44/46/28 + protected-change field set (resolved
  DEV-11). Includes the ALLOW-boundary positive case (permitted depth-1 must SUCCEED) and the
  documented tolerated cases (missing/duplicate refs).
- `test_three_state.py`: US-12/DEV-27 — replays the golden `events` array verbatim and asserts
  the C0/C1/C2 `versions` map + `code_corrections_count` field-by-field at the server-state
  level; DEV-14 full-merge retention/atomicity. C++ member-name fields + `observations_status`
  explicitly labeled transcript-only / out-of-scope (F-04).

## Result
`pytest tests -q` → **138 passed** (Python 3.12.7). See README-u4 residual list for
3.10/3.11 and real-CC-runtime items that remain UNVERIFIED (F-04).
