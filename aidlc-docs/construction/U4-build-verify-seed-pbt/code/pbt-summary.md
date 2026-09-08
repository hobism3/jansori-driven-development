# PBT Harness Summary (CMP-14)

Framework: **Hypothesis** (PBT-09), already declared in `pyproject.toml` dev extra.
Profiles + reproducibility configured in `tests/conftest.py` (PBT-08): `dev`/`ci`,
`print_blob=True`, `deadline=None`; `pytest_report_header` surfaces the active profile and
how to replay a failure (`pytest --hypothesis-seed=<seed>`).

## Files & rule mapping
- `tests/pbt/generators.py` — **PBT-07** domain strategies: `skill_ids`, `small_skill_ids`
  (collision-friendly), `names`/`descriptions` (Unicode + empty), `bodies` (bounded),
  `boundary_bodies` (L-1/L/L+1), `correction_texts` (non-empty), `refs_children`,
  `register_payloads`. Centralized/reusable; boundary values included.
- `test_roundtrip.py` — **PBT-02**: Capsule `public_dict()` content round-trip; register→GET.
- `test_invariants.py` — **PBT-03**: I-01 (version+1 & immutable history), I-04 (stale reject,
  no change), I-09 (length boundary + preserve), I-11 (preservation declaration), I-15
  (grandchild refused).
- `test_idempotency.py` — **PBT-04**: exact replay by request_id (f(f(x))=f(x)); M2 cross-skill
  reuse rejected; register replay vs duplicate.
- `test_oracle.py` — **PBT-05**: pure reference `Model` for version/corrections/normalize_due
  compared against the real services over generated command sequences; golden threshold
  cross-check.
- `test_stateful.py` — **PBT-06**: `RuleBasedStateMachine` (register/nag/normalize/get) vs a
  dict reference model, invariants checked after every step (version==model, history length==
  version, normalize_due latch); plus deterministic load-semantics (DEV-05/08/37).

## Complementary strategy (PBT-10)
Business-critical paths are ALSO pinned with example-based tests in `tests/golden/` and
`tests/verify/` (concrete expected values), so PBT is never the sole coverage for a critical
path. When a PBT fails, add the shrunk `@reproduce_failure` example as a permanent golden test.
