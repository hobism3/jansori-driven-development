# Build and Test Summary

## Build Status
- **Build Tool**: Python + pip editable install (`pip install -e ".[dev]"`); no compile step (pure Python).
- **Build Status**: Success (importable `server.*`; smoke `import server.app.main` ok).
- **Build Artifacts**: none packaged — importable server package + `tests/`, `scripts/seed.py`, `Makefile`, `plugin/`, `README.md`.
- **Build Time**: n/a (install only).
- **Environment note**: executed on **Python 3.12.7** (locally available). Target is **3.10–3.11** — re-run on 3.10/3.11 before sign-off (residual).

## Test Execution Summary

### Unit Tests (`tests/unit`) — 95 passed
| Suite | Result |
|---|---|
| U1 `tests/unit/u1` | 57 passed |
| U2 `tests/unit/u2` | 18 passed |
| U3 `tests/unit/u3` | 20 passed |
- **Status**: **Pass** (0 failures).

### Property-Based Tests (`tests/pbt`, Hypothesis) — 15 passed
- PBT-02 round-trip, PBT-03 invariants (I-01/04/09/11/15), PBT-04 idempotency (I-05),
  PBT-05 oracle, PBT-06 stateful + load-semantics. Generators PBT-07; shrinking/seed PBT-08.
- **Status**: **Pass**.

### Integration / Contract Tests — included above + `tests/verify` (7 passed)
- `tests/verify/test_verify_contract.py` drives a **real uvicorn server** (US-17); U2/U3 live-server integration tests pass; `scripts/seed.py` smoke-verified (leaves-first, Korean UTF-8, idempotent re-seed).
- **Status**: **Pass**.

### Golden / Example Tests (`tests/golden`) — 21 passed
- Core paths + DEV-02/09/13/34/03/44/46/28, protected-change (DEV-11 resolved), three-state C0/C1/C2 (US-12/DEV-27) field-by-field + DEV-14.
- **Status**: **Pass**.

### Performance Tests
- Load/stress/scalability: **N/A** (local single-user, in-memory; NFR SKIPPED). Hook fail-open budget (I-08, 2000ms) and non-blocking normalization (I-10) verified functionally.

### Security Tests (§5 boundary — mandatory even with Security extension OFF)
- Loopback-only bind (server + client guards), temp-dir path containment, scripts never auto-executed, no collection of prompts/transcripts — covered by U1 security unit tests + golden loopback tests + verify client non-loopback refusal.
- **Status**: **Pass**.

## Overall Totals
- **Full suite** `python -m pytest tests -q` → **138 passed, 0 failed** (unit 95 + pbt 15 + golden 21 + verify 7), Python 3.12.7.

## Overall Status
- **Build**: Success
- **All Tests**: **Pass** (138/138)
- **Ready for Operations**: Yes (with residuals below tracked honestly)

## Residual / UNVERIFIED (F-04 — NOT marked complete)
- Python **3.10/3.11** run (only 3.12.7 available in this environment).
- `make` invocation on Windows (GNU Make not assumed; equivalent `python -m ...` commands run).
- **Real Claude Code runtime** evidence: plugin/subagent launch, LLM merge quality, live C0/C1/C2 code-propagation transcript — **NOT_RUN** (user-deliverable demo).
- **Demo video** + **explanation HTML/PPT** — user deliverables; team supplies inputs/content only.

## Next Steps
All automated build+test gates pass → ready to proceed to the **Operations** phase (placeholder
in this workflow). Before the demo: confirm the 3.10/3.11 run, Claude Code v2.1.263, and capture
the live propagation transcript for the user-owned demo artifacts.
