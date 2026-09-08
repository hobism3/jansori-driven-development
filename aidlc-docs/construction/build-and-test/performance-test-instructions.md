# Performance Test Instructions

## Applicability — mostly N/A (with one real budget)
Jansori is a **local, single-user, loopback-only** tool with an **in-memory** store. NFR
Requirements/Design were SKIPPED (user-approved) — there are no throughput/concurrent-user/
scalability targets to load- or stress-test. Full load/stress testing is therefore **N/A**.

The ONE latency-adjacent requirement is the **hook time budget (I-08, fail-open)**: the
UserPromptSubmit hook must not block the user — it uses a bounded client timeout
(`JANSORI_HOOK_TIMEOUT_MS`, default **2000ms**) and fails open if the server is slow/down.

## What to check instead of load tests

### 1. Hook fail-open budget (I-08)
- **Requirement**: a slow/unreachable server must NOT stall prompt submission; the hook
  returns within its timeout and proceeds without the index.
- **How**: covered functionally by the U2 fail-open hook tests (server-down path). To sanity-
  check latency manually:
  ```bash
  JANSORI_HOOK_TIMEOUT_MS=2000 JANSORI_URL=http://127.0.0.1:9  \
    python plugin/scripts/jansori_client.py index    # unreachable -> returns promptly, ok:false SERVER_ERROR
  ```
- **Expected**: returns within ~2s with `{"ok": false, "code": "SERVER_ERROR"}` (never hangs).

### 2. Non-blocking normalization (I-10)
- **Requirement**: capsule normalization runs in a background subagent and never blocks the
  consumer path. Verified structurally (subagent is isolated; server `normalize` is a normal
  request, `normalize_due` is a response flag, not a callback).

## Load/Stress/Scalability
**N/A** for v1 (local single-user, in-memory). If future deployment introduces multi-user or
networked operation, revisit with an NFR Requirements pass first, then add k6/locust scripts
targeting the endpoints in `build-instructions.md`.
