# U1 Persistence (JSON snapshot) — reopen 2026-09-09

Small brownfield addition to CMP-07 Capsule Store: optional, **persist-by-default** JSON
snapshot so a running server survives restarts. AI-DLC: U1 reopen only (reverse-eng /
user-stories / units / NFR / infra all SKIP; no new components).

## Decisions
- **D-P1 (persist-by-default)** — the running server persists to a JSON file. Env
  `JANSORI_DATA_FILE` default `jansori-data.json` (cwd); opt out to in-memory with
  `:memory:` (or empty). **Supersedes the original Q9 (in-memory only) — user-authorized.**
- **D-P2 (trigger)** — write-through on every store commit. All writes
  (register / nag / protected-change / normalize) funnel through
  `CapsuleStore._commit_locked`; the persist hook lives there, so it fires on every skill
  create/update. Reads never persist.
- **D-P3 (scope)** — latest capsules + immutable version history (I-01). The idempotency
  request-log is NOT persisted (a restart is a fresh session).
- **D-P4 (atomicity)** — serialize full state → temp file → `os.replace`, under the store
  lock, so a crash mid-write never yields a torn snapshot (I-12 preserved).
- **D-P5 (load / fail-safe)** — on startup load the file if present; missing OR corrupt →
  empty store + no crash.

## Isolation guard (why the 144 tests stay green)
Persist-by-default applies **only to the server entrypoint `main()`**, which resolves the
env and builds a persistent `Container`. `Container.build(data_file=None)` and
`create_app()` keep the **in-memory** default, so unit tests, the `TestClient`, and the
`live_url` fixture never touch the filesystem.

## Files
- `server/store/persistence.py` (NEW) — (de)serialize Capsule/Version/Correction/Asset,
  `dump_state`, `load_state` (fail-safe), `atomic_write` (temp + `os.replace`).
- `server/store/capsule_store.py` — `__init__(data_file=None)` hydrates from file;
  `_commit_locked` writes the snapshot when a data file is set.
- `server/app/routes.py` — `Container.build(data_file=None)`.
- `server/app/main.py` — `configured_data_file()` (default `jansori-data.json`, `:memory:`
  opt-out); `main()` builds a persistent app and logs the mode.
- `tests/unit/u1/test_persistence.py` (NEW) — 6 tests: reload round-trip, further-writes,
  missing→empty, corrupt→empty, atomic JSON valid, in-memory writes nothing.
- `.gitignore` — ignores `jansori-data.json`. `README.md` — run/env updated.

## Verification (actual)
- `python -m pytest tests -q` → **144 passed** (prior 138 + 6 persistence), Python 3.12.7.
- End-to-end: boot (persist) → `make seed` (3 skills) → nag cmodel-refactoring→v2 → kill →
  reboot same file → **3 skills + cmodel-refactoring v2 + correction survived** (snapshot 5740 B).

## Notes / honesty
- Every commit does a full-state file write under the lock (opt-in-scale IO; negligible at
  demo size; the in-memory default path is unaffected). A future optimization could write
  incrementally, but that is out of scope for this simple change.
- 3.10/3.11 execution still a standing residual (env here is 3.12.7).
