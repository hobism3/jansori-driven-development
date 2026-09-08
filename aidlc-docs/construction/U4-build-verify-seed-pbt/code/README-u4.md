# U4 — Build/Verify/Seed + PBT Harness — Code Summary

**Unit**: U4 (last). Components CMP-13 (Build/Verify/Seed) + CMP-14 (PBT). Stories US-12/US-16/US-17.
**Status**: Code Generation Part 2 complete. **138 passed** (existing 95 + U4 43) on Python 3.12.7.

## Generated / modified artifacts (application code at repo root)

| Path | Kind | Purpose |
|---|---|---|
| `pyproject.toml` | MODIFY | registered pytest markers `pbt/golden/verify` (Hypothesis already in dev extra) |
| `tests/conftest.py` | NEW | centralized live-server harness (`live_url`, `LiveServer`, `free_loopback_port`), in-process `client`/`container`, Hypothesis profiles + seed logging (PBT-08) |
| `tests/pbt/generators.py` | NEW | domain Hypothesis strategies (PBT-07) |
| `tests/pbt/test_roundtrip.py` | NEW | PBT-02 |
| `tests/pbt/test_invariants.py` | NEW | PBT-03 (I-01/04/09/11/15) |
| `tests/pbt/test_idempotency.py` | NEW | PBT-04 (I-05/M2/I-06) |
| `tests/pbt/test_oracle.py` | NEW | PBT-05 (reference model + threshold cross-check) |
| `tests/pbt/test_stateful.py` | NEW | PBT-06 (RuleBasedStateMachine vs dict model) + load-semantics (DEV-05/08/37) |
| `tests/golden/test_core_paths.py` | NEW | example/golden (DEV-02/09/13/34/03/44/46/28, protected-change) |
| `tests/golden/test_three_state.py` | NEW | US-12/DEV-27 (events replayed verbatim, field-by-field) + DEV-14 |
| `tests/verify/test_verify_contract.py` | NEW | US-17 real-server contract + DEV-29/32 |
| `scripts/seed.py` | NEW | generic DEV-38 seed loader (leaves-first, refs→refs_children, correction replay) |
| `Makefile` | NEW | `install/run/seed/verify/pbt/test` |
| `README.md` | NEW | team deliverable |

## Verified (this environment)
- `pytest tests -q` → **138 passed** (Python 3.12.7).
- `make seed` smoke: registers 3 seed capsules leaves-first, Korean UTF-8 preserved, **re-seed idempotent** (stable request_ids → replay, no DUPLICATE_REGISTRATION).
- `make verify` suite boots a **real uvicorn server** on an ephemeral loopback port and drives the full contract over HTTP (not a stub).

## Residual / UNVERIFIED (honest, F-04) — NOT marked done
- **Python 3.10/3.11**: target per Requirements Q7; only **3.12.7** was available here. Re-run `make test` on 3.10/3.11 before sign-off.
- **`make` on Windows**: GNU Make not assumed present; recipes documented to run directly. `make` invocation itself not exercised here (equivalent `python -m pytest ...` commands were).
- **Real Claude Code runtime** (US-12 propagation transcript, subagent launch on `normalize_due`, LLM merge quality, plugin discovery on Windows) — require a live session; remain **NOT_RUN** user-deliverable evidence.
- **Demo video + explanation HTML/PPT** — user deliverables; team supplies inputs/content only.

## PBT compliance (full mode, all blocking)
| Rule | Status | Where |
|---|---|---|
| PBT-01 property identification | Compliant | plan §3 (FD skipped → documented in plan); this summary |
| PBT-02 round-trip | Compliant | test_roundtrip.py |
| PBT-03 invariants | Compliant | test_invariants.py |
| PBT-04 idempotency | Compliant | test_idempotency.py |
| PBT-05 oracle | Compliant | test_oracle.py |
| PBT-06 stateful | Compliant | test_stateful.py |
| PBT-07 generator quality | Compliant | generators.py (domain strategies, boundary values, centralized) |
| PBT-08 shrinking/reproducibility | Compliant | conftest.py profiles + print_blob + report header |
| PBT-09 framework | Compliant | Hypothesis (pyproject dev extra) |
| PBT-10 complementary | Compliant | tests/golden example tests alongside PBT |

No non-compliant (blocking) PBT findings. N/A: none among PBT-02..08 (all have genuine targets); build-glue (Makefile) and demo-transcript components carry no PBT properties (PBT-01 N/A rationale).
