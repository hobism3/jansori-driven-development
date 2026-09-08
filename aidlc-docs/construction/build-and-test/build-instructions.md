# Build Instructions

## Prerequisites
- **Build Tool**: Python + `pip` (PEP 517 editable install via setuptools). Optional GNU `make`.
- **Dependencies** (declared in `pyproject.toml`):
  - Runtime: `fastapi>=0.110,<1.0`, `uvicorn>=0.29,<1.0`, `pydantic>=2.6,<3.0`
  - Dev/test extra `[dev]`: `pytest>=8.0`, `httpx>=0.27`, `hypothesis>=6.100`
- **Environment Variables** (all optional; safe defaults):
  - `JANSORI_HOST` (default `127.0.0.1`, **loopback only** — non-loopback refused, SPEC 5)
  - `JANSORI_PORT` (default `8765`)
  - `JANSORI_URL` (client target; default `http://127.0.0.1:8765`)
  - `JANSORI_MAX_CONTENT_LENGTH` (default `10000`), `JANSORI_NORMALIZE_THRESHOLD` (default `3`)
  - `JANSORI_HYPOTHESIS_PROFILE` (`dev`|`ci`), `JANSORI_HYPOTHESIS_MAX_EXAMPLES`
- **System Requirements**: **Python 3.10–3.11** (`requires-python = ">=3.10,<3.12"`). Windows (win32) primary; portable elsewhere. No database/disk (in-memory store).

## Build Steps

### 1. Install Dependencies
```bash
make install
# equivalent:
python -m pip install -e ".[dev]"
```

### 2. Configure Environment
No configuration required for defaults. To override (example):
```bash
export JANSORI_PORT=8799
export JANSORI_NORMALIZE_THRESHOLD=3
```

### 3. Build All Units
This is a pure-Python project — there is no compile step. "Build" = the editable install
above, which makes the `server` package importable and installs test deps. The client
(`plugin/scripts/jansori_client.py`) and subagent (`plugin/agents/capsule-normalizer.md`)
are stdlib-only and require no build.

### 4. Verify Build Success
- **Expected Output**: `pip` reports `Successfully installed jansori-server-0.1.0` (+ deps).
- **Build Artifacts**: none packaged; importable `server.*` package + `tests/`, `scripts/seed.py`, `Makefile`.
- **Smoke check**:
  ```bash
  python -c "import server.app.main, fastapi, uvicorn, hypothesis; print('ok')"
  ```

## Troubleshooting

### Build Fails with Dependency Errors
- **Cause**: offline index / incompatible Python (3.12+ or <3.10).
- **Solution**: use Python 3.10 or 3.11; ensure network access to PyPI; retry `make install`.

### `make` not found (Windows)
- **Cause**: GNU Make not installed.
- **Solution**: run the underlying commands directly (each `Makefile` recipe lists them),
  e.g. `python -m server.app.main`, `python -m pytest tests -q`.

### Server refuses to start
- **Cause**: `JANSORI_HOST` set to a non-loopback address (SPEC 5 guard raises ValidationError).
- **Solution**: unset it or set `127.0.0.1` / `localhost` / `::1`.
