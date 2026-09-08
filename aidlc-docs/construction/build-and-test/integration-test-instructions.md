# Integration Test Instructions

## Purpose
Verify interactions **between units** over the real loopback HTTP boundary: the U2 plugin
client and the U3 subagent client both talk to the U1 server; the U4 `verify` suite exercises
the full SPEC-8 contract against a genuinely running server. No fake/stub Store is accepted.

## Test Scenarios

### Scenario 1: U2 plugin client → U1 server (`tests/unit/u2/test_hooks_integration.py`)
- **Description**: UserPromptSubmit/Stop hooks + bundled client hit a live server (index injection, fail-open).
- **Setup**: uvicorn server on an ephemeral 127.0.0.1 port (centralized `live_url` fixture, `tests/conftest.py`).
- **Expected**: hooks succeed; server-down path fails open (I-07/I-08) without blocking.

### Scenario 2: U3 capsule-normalizer client → U1 server (`tests/unit/u3/test_normalize_integration.py`)
- **Description**: normalize contract over HTTP — condensed body commit / STALE / PRESERVATION_FAILED (422) / OVER_LENGTH / partial-merge carry-forward.
- **Expected**: all six behaviors hold end to end.

### Scenario 3: U4 full contract → U1 server (`tests/verify/test_verify_contract.py`, US-17)
- **Description**: health, register/index/load+refs, nag×3→normalize_due→normalize, full error matrix (409/413/403/404/422), protected-change (denied/approved), DEV-29/32 (approval×stale + approve-retry idempotency), client non-loopback refusal (§5).
- **Expected**: **7 passed** against a real server.

### Scenario 4: U4 generic seed → U1 server (`scripts/seed.py`, DEV-38)
- **Description**: populate a running server from `fixtures/seed/*.json` (leaves-first, refs→refs_children, correction replay).
- **Expected**: all seed capsules registered; Korean UTF-8 preserved; re-seed idempotent.

## Setup Integration Test Environment

### 1. Start Required Services
The pytest fixtures start/stop the server automatically (uvicorn background thread). For the
manual seed scenario, start it yourself:
```bash
JANSORI_PORT=8799 python -m server.app.main   # terminal 1
```

### 2. Configure Service Endpoints
```bash
export JANSORI_URL=http://127.0.0.1:8799       # terminal 2 (seed / client)
```

## Run Integration Tests

### 1. Execute Integration Suite
```bash
python -m pytest tests/verify tests/unit/u2/test_hooks_integration.py tests/unit/u3/test_normalize_integration.py -q
```
Manual seed check:
```bash
python scripts/seed.py
python plugin/scripts/jansori_client.py index
```

### 2. Verify Service Interactions
- **Expected**: verify suite **7 passed**; integration tests within u2/u3 pass; seed registers all fixtures and re-seed is idempotent.
- **Logs**: pytest stdout; uvicorn logs at `log_level="warning"`.

### 3. Cleanup
The fixtures set `should_exit` and join the server thread automatically. For the manual server, stop it with Ctrl-C (in-memory store discarded).

## Out of scope (F-04 — real Claude Code runtime, NOT run here)
Claude Code actually launching the hooks/`load` Skill/`capsule-normalizer` subagent, LLM merge
quality, and real C++ three-state propagation transcripts require a live Claude Code session and
remain **NOT_RUN** user-deliverable evidence (see `fixtures/acceptance/demo-cases.json`).
