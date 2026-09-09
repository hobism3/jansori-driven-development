# Jansori — persistent, self-correcting skills for Claude Code

Jansori ("잔소리" = gentle nagging) lets a Claude Code user turn repeated corrections into
**durable, versioned skill capsules**. A local loopback server owns the capsules; a Claude
Code plugin injects a skill index and routes save/nag/load actions; an isolated subagent
periodically **normalizes** (SPEC term: *compaction*) accumulated corrections into a
condensed capsule body.

> **Terminology:** *Capsule Normalization* (this product's `normalize`) = SPEC **compaction**
> (merging corrections into a new capsule content version). It is **unrelated** to Claude
> Code's context/transcript compaction.

## Requirements

- **Python 3.10–3.11** (`requires-python = ">=3.10,<3.12"`). *Note: development in this
  workspace ran on the locally available interpreter; confirm 3.10/3.11 before the demo.*
- **Claude Code v2.1.263** recorded at design time (≥ required v2.1.163). Confirm the actual
  installed version before demoing.
- Windows (win32) is the primary target; the server is kept portable where feasible.

## Install & run

```bash
make install     # pip install -e ".[dev]"  (fastapi, uvicorn, pydantic + pytest, hypothesis, httpx)
make run         # start loopback server on 127.0.0.1:8765 (persists to ./jansori-data.json)
make seed        # in another shell: populate the RUNNING server from fixtures/seed/*.json
```

`make run` **persists** the store to a JSON snapshot (default `./jansori-data.json`), written
through on every skill create/update and reloaded on restart (U1 reopen 2026-09-09; supersedes
the original in-memory-only Q9). To run purely in-memory (e.g. a throwaway session), set
`JANSORI_DATA_FILE=:memory:`. `make seed` is **generic** (no hardcoded ids): it registers every `fixtures/seed/*.json`
capsule (leaves first for depth-1 refs) and replays any declared corrections as nags.

Environment overrides: `JANSORI_HOST` (default `127.0.0.1`, **loopback only**),
`JANSORI_PORT` (default `8765`), `JANSORI_URL` (client target), `JANSORI_MAX_CONTENT_LENGTH`
(default `10000`), `JANSORI_NORMALIZE_THRESHOLD` (default `3`),
`JANSORI_DATA_FILE` (default `jansori-data.json`; `:memory:` = no persistence).

If GNU Make is unavailable on Windows, run the recipe commands directly (see `Makefile`),
e.g. `python -m server.app.main`.

## Testing

```bash
make test        # full suite: unit (u1..u3) + pbt + golden + verify
make pbt         # property-based tests only (Hypothesis, PBT-01..10)
make verify      # real-server contract suite (boots & tears down a real uvicorn server)
```

- **`make verify` boots a genuine server** on an ephemeral loopback port and drives it over
  HTTP — a fake/in-memory Store stub is **not** accepted (US-17).
- **Reproducing a property failure (PBT-08):** on failure Hypothesis prints an
  `@reproduce_failure` blob and the seed; replay with `pytest --hypothesis-seed=<seed>`.
  Choose a profile with `JANSORI_HYPOTHESIS_PROFILE=ci|dev`.

## Architecture

```text
server/    U1  loopback FastAPI Capsule server (single source of truth for SPEC-8 contracts)
plugin/    U2  Claude Code plugin (UserPromptSubmit/Stop hooks, load Skill, /jansori:* commands)
plugin/agents/ U3  capsule-normalizer subagent (isolated; GETs capsule JSON, submits normalize)
tests/     U4  pbt/ (Hypothesis) · golden/ (examples) · verify/ (real-server contract)
fixtures/      provided inputs (seed / acceptance-golden / C++ workloads) — requirements, not product source
Makefile   U4  run / seed / verify / pbt / test
```

## Invariants & security (enforced by U1, verified by U4)

I-01 immutable versions · I-02 load record · I-03 depth-1 child expansion · I-04 stale reject ·
I-05 idempotency (request_id) · I-06 duplicate-registration block · I-07 failure≠absence ·
I-08 hook fail-open · I-09 over-length reject+preserve · I-10 non-blocking normalize ·
I-11 preservation (declared merged ids + length) · I-12 atomic writes · I-13 nag target
resolution · I-14 protected-field approval · I-15 storage depth-1 (both directions).

**§5 security (mandatory regardless of extension config):** loopback-only bind
(127.0.0.1/::1), temp-dir path containment, scripts never auto-executed, and no collection of
task source / prompts / conversation transcripts.

## Evidence honesty (F-04)

What the automated suite proves vs what requires a human/runtime demo is stated explicitly:

- **Verified by tests here:** the Capsule server contract, all listed invariants, the
  Capsule versioning/correction **state** that underlies three-state (C0/C1/C2) propagation
  (`tests/golden/test_three_state.py`, asserted field-by-field against
  `fixtures/acceptance/three-state-golden.json`).
- **NOT verified here (require a real Claude Code session; marked NOT_RUN):** the plugin/
  subagent actually launching at runtime, LLM merge *quality*, and real C++ code propagation
  (the golden's `expected_ready_member` etc. and `demo-cases.json` transcripts). These are
  produced in a live demo.
- **User deliverables (the team supplies inputs/content only, never marks them "done"):** the
  **demo video** and the **explanation HTML or PPT**. See `fixtures/acceptance/demo-cases.json`
  (all `NOT_RUN`) and the demo/scenario/transcript inputs.

A full DEV-01..46 acceptance-case → test / out-of-scope map is in
`aidlc-docs/construction/U4-build-verify-seed-pbt/code/golden-coverage-matrix.md`.
