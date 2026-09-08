# Unit Test Execution

## Run Unit Tests

### 1. Execute All Unit Tests
```bash
python -m pytest tests/unit -q
```
Or per unit:
```bash
python -m pytest tests/unit/u1 -q   # server/store/services/security (U1)
python -m pytest tests/unit/u2 -q   # plugin hooks + client (U2; incl. live-server integration)
python -m pytest tests/unit/u3 -q   # capsule-normalizer client + agent def + integration (U3)
```

### 2. Review Test Results
- **Expected** (actual, Python 3.12.7 in dev env — target 3.10/3.11):
  - `tests/unit/u1` → **57 passed**
  - `tests/unit/u2` → **18 passed**
  - `tests/unit/u3` → **20 passed**
  - Unit total → **95 passed, 0 failures**
- **Coverage**: no coverage gate configured; unit tests exercise every service, the store,
  the security guard, hooks, the client, and the subagent definition. Property-based tests
  (see below) add broad input-space coverage.
- **Test Report Location**: stdout (pytest). Add `--junitxml=report.xml` for CI artifacts.

### 3. Property-Based Tests (Hypothesis) — PBT-08 seed logging
```bash
python -m pytest tests/pbt -q                       # profile from JANSORI_HYPOTHESIS_PROFILE (default dev)
JANSORI_HYPOTHESIS_PROFILE=ci python -m pytest tests/pbt -q
python -m pytest tests/pbt --hypothesis-seed=<seed> # replay a specific run
```
- **Expected**: `tests/pbt` → **15 passed**.
- On failure, Hypothesis prints an `@reproduce_failure` blob **and** the seed (the run header
  from `tests/conftest.py` reminds how to replay). Add the shrunk example to `tests/golden`
  as a permanent regression (PBT-10).
- **CI**: run PBT every build; log the seed (default) or pin `--hypothesis-seed`. Investigate
  flaky failures — do not silently retry (PBT-08).

### 4. Fix Failing Tests
1. Review pytest output (and the Hypothesis reproduce blob for PBT).
2. Identify the failing case; for PBT, replay with `--hypothesis-seed=<seed>`.
3. Fix the code; rerun until green.
