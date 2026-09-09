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

## Bug fix — persist-first commit + single-instance lock (reopen 2026-09-09, second pass)

**Root cause (confirmed against source):** `_commit_locked` mutated the in-memory maps
(pointer swap / history / request-log) *before* the disk write, with **no rollback**. When
`persistence.atomic_write`'s `os.replace` failed (WinError 5 — the snapshot was held by a
second server process), in-memory ran ahead to v_n+1 while disk stayed at v_n. Retries then
saw a state that diverged from disk → `PRESERVATION_FAILED` cascade and 500s on full-capsule
serialization. Trigger: **two server processes shared one `jansori-data.json`**.

- **D-P6 (persist-first)** — `_commit_locked` now writes a **prospective** snapshot (built
  from shallow copies, live maps untouched) and confirms it durable **before** any in-memory
  change. A failed write raises with in-memory unchanged, so disk and memory never diverge and
  a retry cleanly re-commits from the true prior version. In-memory-only stores skip the write.
- **D-P7 (single-instance lock)** — `server/store/instance_lock.py` (NEW): `main()` acquires
  an OS advisory lock on `<data_file>.lock` (Windows `msvcrt.locking` / POSIX `fcntl.flock`,
  non-blocking) held for the process lifetime and auto-released on exit (no stale locks). A
  second server against the same file refuses to start with a clear message. `:memory:` and
  tests skip locking. Removes the shared-file race at the source.

**Files changed:** `server/store/capsule_store.py` (persist-first `_commit_locked` + docstring),
`server/store/instance_lock.py` (NEW), `server/app/main.py` (acquire lock in `main()` when
persisting). **Tests:** `tests/unit/u1/test_persistence.py` +2 (persist-failure leaves
memory/disk at prior version; retry-after-failure commits cleanly),
`tests/unit/u1/test_instance_lock.py` (NEW, 4).

**Verification (actual):** `python -m pytest tests -q` → **150 passed** (prior 144 + 6),
Python 3.12.7.

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
