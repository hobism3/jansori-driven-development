# U4 — Build/Verify/Seed + PBT Harness — Code Generation Plan (Part 1)

> **Single source of truth for U4 Code Generation.** Part 2 executes these steps in order, marking each `[x]` immediately on completion.
>근거: `unit-of-work.md` §U4 (CMP-13 Build/Verify/Seed Harness, CMP-14 PBT Harness), `unit-of-work-story-map.md` (주 US-12/US-16/US-17), U1 functional-design (invariants I-01..I-15), PBT rules PBT-01..PBT-10 (**full mode, all blocking**), `aidlc-state.md` Approved Decisions.
> ⚠️ 용어: "정상화(normalize)" = SPEC "compaction" ≠ Claude Code context compaction.

---

## 1. Unit Context

- **Unit**: U4 — Build/Verify/Seed + PBT Harness (LAST unit; order U1→U2→U3→U4, U1/U2/U3 CLOSED).
- **Components**: CMP-13 Build/Verify/Seed Harness, CMP-14 PBT Harness.
- **Stories** (from story-map):
  - **US-16** (주) — Property-based tests PBT-01..10 over U1 domain/store.
  - **US-17** (주) — Evidence honesty (F-04) + `make verify` **real in-test server boot/teardown** contract (fake Store NOT accepted).
  - **US-12** (주) — 3-state C0/C1/C2 propagation evidence.
  - 관여: — (none; U4 has no participating-only stories).
- **Dependencies**: U4 → U1 (exercises server over loopback HTTP + in-process for PBT), U4 → U2/U3 (test-time boot/contract; demo transcript inputs). No production code depends on U4.
- **Team deliverables**: `README.md`, `make run/verify/seed`, golden/demo-scenario/demo-transcript **inputs**, comprehension-check execution+record.
- **User deliverables (team NEVER marks done)**: demo video, explanation HTML **or** PPT. We supply explanation content + demo script + golden/scenario/transcript inputs only.

### SPEC / State guardrails carried in
- Do NOT fill workload TODOs or edit golden / C-original.
- Distinguish sample functional checks from real Plugin propagation evidence (transcripts).
- Compaction threshold = single value **3** everywhere (configurable, default 3); do not weaken invariants.
- Python **3.10–3.11**; Windows (win32) primary, keep portable where feasible.
- Persistence: in-memory only — `make run` starts empty, `make seed` populates each run.
- §5 security (loopback-only bind, temp-dir containment, no script auto-exec, no auto-collection) remains mandatory regardless of Security extension = OFF.
- Honesty: do NOT record tests/consent/demos/transcripts not actually performed.

---

## 2. Contract facts confirmed from current code (inputs to this plan)

- **Server start**: `uvicorn server.app.main:app`, or `python -m server.app.main`; host `JANSORI_HOST` (default `127.0.0.1`), port `JANSORI_PORT` (default `8765`). Non-loopback host → `ValidationError` (defense-in-depth in `main()` + lifespan).
- **Client**: `plugin/scripts/jansori_client.py` (stdlib urllib), base URL env `JANSORI_URL` (default `http://127.0.0.1:8765`). Exposes `act_index/act_get/act_load/act_resolve_target/act_nag/act_register/act_protected_change/act_normalize`; returns `{ok,status,data}` or `{ok:False,status,code,message,detail?}`.
- **Endpoints & statuses**: GET `/health`; GET `/skills/index?session_id?`; GET `/skills/resolve-target?hint?&session_id`; GET `/skills/{id}`; POST `/skills/register`; POST `/skills/{id}/load`; POST `/skills/{id}/nag`; POST `/skills/{id}/protected-change`; POST `/skills/{id}/normalize`. Errors → STALE_BASE_VERSION 409, OVER_LENGTH 413, PROTECTED_CHANGE_DENIED 403, SKILL_ABSENT 404, SERVER_ERROR 500, DEPTH_LIMIT 409, DUPLICATE_REGISTRATION 409, PRESERVATION_FAILED 422, NEEDS_CONFIRMATION 409, VALIDATION_ERROR 400.
- **Domain (PBT targets)** `server/domain/models.py`: Capsule (frozen; `version`, `corrections`, `refs_children`, `assets`, `protected_fields`, copy-on-write `with_new_content`), Version (frozen, immutable I-01), Correction (frozen; `id/target/instruction_text/request_id/seq`), Asset, Session, IndexEntry; `PROTECTED_FIELDS=("skill_id","name","refs_children","protected_fields")`. Limits: `max_content_length=10_000` (env `JANSORI_MAX_CONTENT_LENGTH`), `normalization_threshold=3` (env `JANSORI_NORMALIZE_THRESHOLD`).
- **Stateful component**: `server/store/capsule_store.py` (atomic commit/register, idempotency log by `request_id`, version history, reverse-ref lookup) → primary PBT-06 target with dict reference model.
- **Normalization preservation (I-11, current contract)**: `validate_preservation` = `len(new_body) ≤ L` AND `merged_correction_ids` non-empty ⊆ base corrections; `commit_normalization` removes ONLY declared ids, carries undeclared forward. (NOT verbatim-substring — reflects U1 reopen redesign.)
- **Seed files** `fixtures/seed/*.json` (3): fields `skill_id/version/name/description/keywords[]/body/refs[]/assets[]/corrections[]/created_at`. ⚠️ Mapping gap vs API: `refs`→`refs_children`; `keywords` has no API field (drop); `created_at` ISO string (server uses float, drop); `corrections`/`version` not accepted by `register` → **replay corrections as `nag` calls** to reconstruct state. `cmodel-development` refs `["cmodel-refactoring","cmodel-code-rule"]` → register leaves first (depth-1). Korean UTF-8.
- **Golden/acceptance** `fixtures/acceptance/`: `three-state-golden.json` (C0/C1/C2, threshold 3 — US-12 oracle), `development-cases.json` (DEV-01..46 invariant↔case map; DEV-27 three-state, DEV-34 loopback, DEV-38 generic seed, DEV-43..46 depth-1), `demo-cases.json` (status NOT_RUN), `lifecycle-golden.json`, `workload-golden.json`. **Read-only; do not edit.**
- **Test harness precedent**: live-server uvicorn-thread fixture is duplicated inline in `tests/unit/u2/test_hooks_integration.py` and `tests/unit/u3/test_normalize_integration.py` → U4 **centralizes** it in `tests/conftest.py`.
- **pyproject.toml**: `requires-python >=3.10,<3.12`; dev extra already includes `hypothesis>=6.100`, `pytest>=8.0`, `httpx>=0.27`. `[tool.pytest.ini_options] testpaths=["tests"]`. No markers/hypothesis profile yet.

---

## 3. PBT-01 Testable Properties (documented here — FD was SKIPPED for U4)

> PBT-01 normally lives in Functional Design; U4 FD was skipped (user-approved), so per-component testable properties are documented **in this plan** (the U4 design artifact) and grounded on U1 FD which already lists I-01..I-15 as PBT properties. This keeps PBT-01 compliant.

| Component / target | Property | Category | Rule |
|---|---|---|---|
| Capsule `public_dict()` ↔ reconstruct | serialize→parse yields structurally equal capsule content | Round-trip | PBT-02 |
| register → GET `/skills/{id}` | registered content round-trips through HTTP + store | Round-trip | PBT-02 |
| `with_new_content` / commit | any content change ⇒ `version` strictly increases by 1; old Version snapshots immutable (I-01) | Invariant | PBT-03 |
| commit / nag | `len(body) ≤ L` always holds post-commit; OVER_LENGTH rejected, prior state preserved (I-09) | Invariant / Range | PBT-03 |
| `commit` stale guard | commit with `base_version != current` rejected STALE, state unchanged (I-04) | Invariant | PBT-03 |
| `validate_preservation` (I-11) | declared ⊆ base ids & length ≤ L ⇒ accept; undeclared carried forward; empty/unknown ids ⇒ PRESERVATION_FAILED | Invariant | PBT-03 |
| idempotency log (I-05) | `f(f(x))=f(x)`: replaying same `request_id` returns exact prior result, no new version/state change | Idempotence | PBT-04 |
| CapsuleStore command sequences | store state matches dict reference model after each command (register/nag/protected-change/normalize/load) | Stateful / Oracle | PBT-06 |
| index build / three-state versioning | service output equals simple reference model (correction count, version, normalize_due at ≥3) vs `three-state-golden.json` | Oracle | PBT-05 |
| refs depth-1 (I-15) | no valid register/refs-change produces depth>1 in either direction | Invariant | PBT-03 |

Components with **no PBT properties**: Makefile / `make run` (build glue), demo-transcript inputs (require real Claude Code runtime) → marked **N/A** with rationale in the compliance summary. Round-trip encoding/decoding beyond capsule JSON: N/A (no other codecs). PBT-10: golden/example tests pin business-critical scenarios alongside PBT.

---

## 4. Target file layout (application code at workspace ROOT; docs in aidlc-docs/ only)

```text
<ROOT>/
├── Makefile                         # NEW — install / run / seed / verify / test / pbt
├── README.md                        # NEW — team deliverable (overview, requirements, targets, invariants, F-04 honesty, demo howto)
├── pyproject.toml                   # MODIFY — pytest markers (pbt, verify, golden) + hypothesis profile note
├── scripts/
│   └── seed.py                      # NEW — generic seed loader (no hardcoded IDs; reads fixtures/seed/*.json; depth-1 order; replay corrections via nag)
└── tests/
    ├── conftest.py                  # NEW — centralized live-server fixture (uvicorn thread, ephemeral loopback port) + hypothesis profile/seed logging
    ├── pbt/
    │   ├── __init__.py
    │   ├── generators.py            # NEW — Hypothesis strategies (skill_id, body≤L, correction_text, assets, refs, register/nag params)
    │   ├── test_roundtrip.py        # PBT-02
    │   ├── test_invariants.py       # PBT-03 (I-01/I-04/I-09/I-11/I-15, range)
    │   ├── test_idempotency.py      # PBT-04 (I-05)
    │   ├── test_oracle.py           # PBT-05 (reference model / three-state)
    │   └── test_stateful.py         # PBT-06 (RuleBasedStateMachine vs dict model over CapsuleStore)
    ├── golden/
    │   ├── __init__.py
    │   ├── test_core_paths.py       # example-based: register→load→nag×3→normalize_due→normalize; refs depth-1; dup block; loopback (PBT-10)
    │   └── test_three_state.py      # US-12 C0/C1/C2 vs fixtures/acceptance/three-state-golden.json
    └── verify/
        ├── __init__.py
        └── test_verify_contract.py  # US-17 — REAL in-test server boot/teardown; full API contract over HTTP; fake store rejected
```

Doc summaries (markdown only): `aidlc-docs/construction/U4-build-verify-seed-pbt/code/`.

---

## 5. Generation Steps (Part 2 executes in this order)

- [x] **Step 1 — pyproject.toml pytest/PBT config** *(MODIFY)*
  Add `[tool.pytest.ini_options]` markers `pbt`, `golden`, `verify` (registered to avoid warnings); keep `testpaths=["tests"]`. Document Hypothesis usage. Confirm `hypothesis` in dev extra (already present). No runtime dep change. (PBT-09 framework already selected = Hypothesis.)

- [x] **Step 2 — tests/conftest.py (centralized harness)** *(NEW)*
  Move the duplicated uvicorn-thread live-server harness into a shared fixture: `_free_port()`, `_ServerThread`, `live_url` (sets `JANSORI_URL`, pins `127.0.0.1`, polls `server.started`). Add `in_process_client` fixture returning FastAPI `TestClient(create_app(Container.build()))` with a fresh empty store. Register a Hypothesis profile (`settings.register_profile`) with a reasonable `max_examples` and **`print_blob=True`/seed logging on failure** (PBT-08). Do NOT yet refactor u2/u3 inline copies (out of scope; note as optional follow-up to avoid touching CLOSED units).

- [x] **Step 3 — tests/pbt/generators.py** *(NEW)* — PBT-07
  Domain-specific Hypothesis strategies: `skill_ids()` (slug-like, non-empty), `bodies(max_len=L)` (bounded incl. Unicode + empty + boundary L), `correction_texts()` (non-empty), `assets()` (`{name,path,is_script,summary}`), `refs_children()` (lists of valid ids), `register_payloads()`, `nag_payloads()`. Centralized/reusable. Include boundary values (empty collections, length exactly L, length L+1 for rejection tests). No bare `st.integers()`/`st.text()` for domain fields.

- [x] **Step 4 — tests/pbt/test_roundtrip.py** *(NEW)* — PBT-02
  (a) Capsule `public_dict()` → reconstruct structural equality on content fields. (b) register (generated payload) → GET `/skills/{id}` returns equal name/description/body/refs_children/assets (via in-process client). Generated inputs, not hardcoded.

- [x] **Step 5 — tests/pbt/test_invariants.py** *(NEW)* — PBT-03
  Properties over generated command sequences / inputs: I-01 (content change ⇒ version+1, prior Version snapshot unchanged & immutable), I-04 (stale base_version ⇒ STALE_BASE_VERSION, state unchanged), I-09 (over-length body ⇒ OVER_LENGTH, prior state preserved; post-commit `len(body)≤L` always), I-11 (`validate_preservation`: declared⊆base & ≤L accept, undeclared carried forward, empty/unknown ⇒ PRESERVATION_FAILED), I-15 (depth-1 both directions — generated refs never yield depth>1 after valid ops; violating attempt ⇒ DEPTH_LIMIT). Test general rules, not example duplicates.

- [x] **Step 6 — tests/pbt/test_idempotency.py** *(NEW)* — PBT-04
  Generate an operation then replay with the SAME `request_id`; assert exact-result replay (same version, same capsule, `idempotent_replay=True`) and no observable state change; distinct `request_id` bound to different skill ⇒ VALIDATION_ERROR (M2). `f(f(x))=f(x)` on nag/register/normalize/protected-change.

- [x] **Step 7 — tests/pbt/test_oracle.py** *(NEW)* — PBT-05
  Reference model: pure-Python recompute of `version`, `corrections_count`, `normalize_due (count ≥ threshold=3)` from a command sequence; assert service/store output equals model. Cross-check the three-state expectations shape against `fixtures/acceptance/three-state-golden.json` (read-only) at the count/version level. (If judged not a genuine oracle, document rationale — but reference model is genuine here.)

- [x] **Step 8 — tests/pbt/test_stateful.py** *(NEW)* — PBT-06
  `RuleBasedStateMachine` (Hypothesis stateful) driving CapsuleStore/services with a dict reference model (`skill_id → {version, corrections[], refs_children, body}` + version-history). Rules: register, nag, protected-change (approved/denied), normalize, load, get. Invariants checked **after each step**: version monotonic, immutable history, idempotency log consistency, depth-1, normalize_due latch. Include empty sequences.
  **Load-semantics invariants (gap-closure DEV-05/DEV-08/DEV-37)**: a parent load always delivers the LATEST child version even when the parent's own version is unchanged; child nags are independent of parent version; a load recorded at v(n) is NOT retroactively invalidated/flagged when a later v(n+1) commits. Assert these as model-vs-store equivalences within the state machine.

- [x] **Step 9 — tests/golden/test_core_paths.py** *(NEW)* — PBT-10 (example-based)
  Concrete pinned scenarios (in-process client): register→load (DEV-02); nag×3 flips `normalize_due` at 3, 2 does not (DEV-13); normalize with declared merged ids condenses body & carries forward; refs parent load expands depth-1 children (I-03/I-15, DEV-02); duplicate registration ⇒ DUPLICATE_REGISTRATION (I-06, DEV-09); non-loopback host ⇒ ValidationError (§5/DEV-34). Explicit expected values.
  **Gap-closure additions (from golden audit):**
  - **Bad-refs matrix (DEV-03/DEV-44)**: missing-id ref, self-ref, duplicate ref in one register; and a refs-**change** (not just register) that would turn a with-children capsule into a child ⇒ each rejected with the correct code (SKILL_ABSENT / VALIDATION_ERROR / DEPTH_LIMIT as applicable).
  - **DEV-46 ALLOW boundary (positive)**: assert the *permitted* one-level cases SUCCEED — register A referencing new leaf B (depth-1) OK; change A.refs→[C] (C a leaf) OK. Guards against an over-strict impl that wrongly rejects valid depth-1 (u1 only tests rejections today).
  - **DEV-28 content vs progress-state separation**: toggling `normalize_due`/`normalize_in_progress` (session/progress flags) leaves capsule `version` and content (body/corrections) unchanged — assert version + content hash stable across a flag toggle.

- [x] **Step 10 — tests/golden/test_three_state.py** *(NEW)* — US-12 / DEV-27
  **Replay the golden `events` array VERBATIM** (all 6 steps, in order) from `three-state-golden.json`, then assert **field-by-field** the C0/C1/C2 per-state `versions` map (`cmodel-development`/`cmodel-refactoring`/`cmodel-code-rule`), `code_corrections_count`, and `normalize_due` at the **server-state level** (threshold 3). Explicitly label the C++-propagation member-name fields (`expected_ready_member`, `expected_frame_count_member`, `preserve_existing_member`) and `observations_status:"NOT_RUN"` as **transcript-only / out-of-scope** (require real Claude Code runtime; F-04 honesty). NOT a live plugin-propagation transcript.
  **DEV-14 full normalize (gap-closure)**: pin the terminal merge — merge ALL corrections ⇒ `corrections` empty AND `assets`/`refs_children` intact AND prior version v(n-1) fully preserved (immutable) AND commit atomic (version bumps exactly once). Explicit expected values.

- [x] **Step 11 — tests/verify/test_verify_contract.py** *(NEW)* — US-17 / DEV-34
  Uses `live_url` (REAL uvicorn boot on ephemeral loopback port, torn down after). Full contract sweep over HTTP via `jansori_client`: health, register, index, load+refs, nag×3 → normalize_due, normalize (condense+declare), protected-change (approved/denied 403), stale (409), over-length (413), unknown-id preservation (422), duplicate (409), resolve-target (needs-confirmation 409). Asserts the server actually served (not a fake/TestClient stub) — `make verify` binds `make verify` to this suite. Include an explicit assertion that a non-loopback bind is refused.
  **Approval×stale combination (gap-closure DEV-29/DEV-32)**: an `approval_flag=True` protected-change with a STALE `base_version` is still rejected by the stale guard (approval does not bypass I-04); and an approve→network-retry with the same `request_id` is counted exactly once (idempotent, no double version bump).

- [x] **Step 12 — scripts/seed.py** *(NEW)* — DEV-38 generic seed
  Generic loader: glob `fixtures/seed/*.json` (no hardcoded IDs), parse, topologically order by `refs` (leaves/children first so parents register with resolvable depth-1 refs), map `refs`→`refs_children`, drop `keywords/version/created_at`, pass `assets` through; register via `jansori_client.act_register` against a running server (`JANSORI_URL`); then **replay `corrections[]` in `seq` order as `act_nag`** to reconstruct version/correction state. Idempotent per run via per-item `request_id`. Prints a summary; honest about what it seeded. No auto-exec of scripts (§5).

- [x] **Step 13 — Makefile** *(NEW)*
  Targets: `install` (`pip install -e .[dev]`), `run` (`python -m server.app.main` — empty state), `seed` (`python scripts/seed.py` — assumes server running), `verify` (`pytest tests/verify -q` — real boot/teardown; fake store not accepted), `pbt` (`pytest tests/pbt -q`), `test` (`pytest tests -q`). Portability note in README for Windows (GNU Make via git/choco, or run the underlying commands directly). No hardcoded skill IDs anywhere.

- [x] **Step 14 — README.md (root)** *(NEW — team deliverable)*
  Overview; requirements (Python 3.10–3.11; Claude Code v2.1.263 recorded, confirm before demo); install/run/seed/verify/test targets + Windows note; architecture (server/plugin/agents/tests/fixtures); invariants I-01..I-15 + §5 security summary; **F-04 evidence-honesty section** (what is verified by tests vs what requires a real Claude Code demo transcript — the latter marked NOT_RUN, owned inputs only); demo howto pointing at demo-cases/scenario inputs; note demo video + HTML/PPT are **user deliverables** (team supplies content/inputs only, never marked done).

- [x] **Step 15 — Run full test suite** *(execution + honest reporting)*
  Run `pytest tests -q` (Python available = 3.12 in this env; note 3.10/3.11 target — flag as residual if not runnable here). Log Hypothesis seed/profile (PBT-08). Report ACTUAL pass/fail counts (existing 95 + new U4). Do NOT claim demo/transcript/real-CC runtime results not performed.

- [x] **Step 16 — Code doc summaries** *(NEW, markdown only)*
  Under `aidlc-docs/construction/U4-build-verify-seed-pbt/code/`: `README-u4.md` (unit overview + residual/UNVERIFIED checklist honestly), `makefile-seed-summary.md`, `pbt-summary.md` (per-rule mapping), `verify-golden-summary.md`. Include **PBT Compliance** table (PBT-01..10 compliant/N/A) and F-04 honesty notes.
  **DEV→test traceability matrix (gap-closure, mandatory)**: a `golden-coverage-matrix.md` mapping every `development-cases.json` case **DEV-01..DEV-46 → covering test id** (existing-u1 or new-U4) **OR** an explicit out-of-scope rationale (U2/U3 CLOSED-unit concern / transcript-only / C++ evaluator / F-04-deferred). This makes "full golden coverage" auditable (also satisfies DEV-39/F-04 honesty). No DEV case may be left unclassified.

---

## 6. Story traceability

| Story | Steps |
|---|---|
| US-16 (PBT-01..10) | 1,2,3,4,5,6,7,8 (+10 PBT-10 complement) |
| US-17 (make verify real-boot + F-04 honesty) | 2,11,13,14,16 |
| US-12 (3-state C0/C1/C2 evidence) | 10 (state-level) + 14/16 (transcript inputs + honesty) |
| DEV-38 generic seed | 12,13 |
| §5 security (loopback/no auto-exec) | 9,11,12,14 |

---

## 7. PBT compliance intent (to be finalized in Step 16)

| Rule | Plan coverage |
|---|---|
| PBT-01 Property identification | §3 table (documented in this plan since FD skipped) |
| PBT-02 Round-trip | Step 4 |
| PBT-03 Invariants | Step 5 |
| PBT-04 Idempotency | Step 6 |
| PBT-05 Oracle | Step 7 |
| PBT-06 Stateful | Step 8 |
| PBT-07 Generator quality | Step 3 (centralized domain generators) |
| PBT-08 Shrinking/reproducibility | Step 2 (profile+seed logging), Step 15 |
| PBT-09 Framework | Hypothesis (already in pyproject dev extra), Step 1 |
| PBT-10 Complementary | Steps 9,10 (example/golden) alongside PBT |

No rule anticipated non-compliant. N/A candidates (with rationale): none among PBT-02..08 (all have genuine targets); build-glue/demo-transcript components marked N/A under PBT-01.

---

## 8. Explicit scope boundaries (honesty / F-04)

- We do **NOT** run a real Claude Code plugin/subagent propagation session; US-12 live transcript + demo video + HTML/PPT remain user deliverables / NOT_RUN. Tests reproduce three-state at server-state level only.
- We do **NOT** edit `fixtures/**` golden or workload files.
- We do **NOT** refactor CLOSED units U1/U2/U3 code (u2/u3 inline harness copies left as-is; centralization is additive in tests/conftest.py).
- 3.10/3.11 execution: target per Requirements; if only 3.12 is available in this environment, report actual run version and flag 3.10/3.11 as residual.

## 9. Golden-audit outcome (subagent, 2026-09-08) — gap closures folded in

A golden-coverage audit (all 5 acceptance/golden fixtures enumerated vs plan) returned **GAPS FOUND**; the following are now closed in the steps above:
- DEV-03/DEV-44 bad-refs matrix (missing/self/dup + refs-change) → Step 9
- DEV-46 **ALLOW** boundary positive case (permitted depth-1 register+change succeeds) → Step 9
- DEV-28 content vs progress-state separation → Step 9
- DEV-14 full-merge retention/atomicity → Step 10
- DEV-27 three-state: replay `events` verbatim + field-by-field assert; member-name fields labeled transcript-only → Step 10
- DEV-05/DEV-08/DEV-37 load semantics (latest child, independence, no retro-flag) → Step 8
- DEV-29/DEV-32 approval×stale + approve-retry idempotency → Step 11
- DEV→test traceability matrix (`golden-coverage-matrix.md`) → Step 16
- Correctly confirmed **out-of-scope**: workload-golden (C++ numeric W-01..42), lifecycle-golden (evaluator-only C++ probe), demo-cases DEMO-* (`actual_plugin_transcript`, NOT_RUN user deliverables), three-state member-name fields, and transcript/artifact_review DEV cases (DEV-18/39/40/41/42) — per SPEC guardrails (don't fill workload TODOs; sample checks ≠ propagation evidence; F-04).

### ✅ Contract discrepancy RESOLVED (DEV-11) — 2026-09-08 (user-decided: Option A)
`development-cases.json` DEV-11 lists protected-change candidates as **`name / description / keywords / assets / refs`**, but the implemented (U1 CLOSED, approved) `PROTECTED_FIELDS = {skill_id, name, refs_children, protected_fields}` — i.e. `description/keywords/assets` are NOT protected in code.
**Decision (user-approved):** implemented `PROTECTED_FIELDS` is **authoritative** (U1 contract approved & CLOSED); U1 NOT reopened. U4 tests target `{skill_id, name, refs_children, protected_fields}`; DEV-11 recorded as a superseded/looser doc note in `golden-coverage-matrix.md` (Step 16). Step 9/11 protected-change cases assert this set: changing a protected field without `approval_flag` ⇒ PROTECTED_CHANGE_DENIED 403; with approval ⇒ succeeds; non-protected fields (description/keywords/assets) follow normal (non-protected) change path.
```

