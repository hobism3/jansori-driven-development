# Requirements — Jansori Plugin

> Source of truth: root `SPEC.md`. `docs/spec-reference.md` is format examples only, not a fixed contract.
> This document turns SPEC.md + the input package into confirmed requirements + a verification plan. It does NOT reopen adopted §4B baselines or weaken invariants I-01..I-15.

## 1. Intent Analysis

- **User request**: Build the Jansori Plugin — a Claude Code plugin + local Python server that lets a user's "nag" (correction) accumulate on a skill Capsule, produce a **new version of the same `skill_id`**, and propagate that correction into the **next user's real work** in a fresh session, while preserving existing rules/features. Compare three states (C0 pre-correction / C1 post-correction pre-compaction / C2 post-compaction).
- **Request type**: New Project (greenfield product).
- **Scope estimate**: Multiple components / system-wide (plugin hooks + load Skill + save/nag paths + local server + storage + refs expansion + compaction subagent + build/test + submissions).
- **Complexity estimate**: Complex (hard invariants I-01..I-15, security boundary §5, evidence-honesty rules F-03..F-07, multi-session propagation proof).
- **Core proposition** (must be proven, not just stored/injected): one person's nag → same `skill_id` new version → next fresh session's **actual changed code output**, with existing instructions preserved.

## 2. What is NOT reverse-engineered / what fixtures are

The repo's C++ workloads (`fixtures/workloads/`), seed JSON (`fixtures/seed/`), acceptance/golden JSON, and `tools/verify_sample.py` are **provided inputs** (requirements + evaluator tooling), NOT an existing Jansori product. We do not fill workload TODOs, edit golden, or optimize workload originals during development. Sample functional checks (fixed runner/probe/`verify_sample.py`) are kept distinct from real Plugin propagation evidence (transcripts).

## 3. Adopted Baselines Carried In (SPEC §4B — NOT reopened)

| Area | Adopted baseline (in force) |
|---|---|
| Data/state | Capsule JSON single source of truth; consumer does not keep parent SKILL.md as a local copy; progress state managed separately from content |
| Selection | Claude selects from index name/description; **no LLM call inside hooks** |
| Hook roles | UserPromptSubmit injects index; Stop gives save-suggestion notice; hooks do not converse or store directly |
| Call paths | `load` provided as a model-callable Skill; `/jansori:save`, `/jansori:nag`, and clear natural-language requests use a common processing path |
| Version/corrections | first version = v1; corrections accumulate oldest→newest; latest explicit correction for a condition wins; if unclear, confirm first |
| Protected fields | name·description·keywords·assets·refs changes require an approval flag + freshness check |
| Over-length | render-length check at register/nag/PATCH entry; on exceed → preserve existing content, reject change, advise child split (NOT truncate-oldest, NOT defer-to-next-nag) |
| refs / active scope | reference depth 1; new work = new session; one session activates one parent + its direct children; children are also correctable |
| compaction | trigger by corrections count (**adjusted to 3 everywhere per Q5**); background in a separate subagent; on success write new version + new body and clear corrections |

## 4. Functional Requirements (SPEC §6 R-01..R-14 + linked invariants + acceptance cases)

Each requirement lists: verification mode (auto = `make verify` mechanical contract; transcript = real run vs pre-set expectation), the invariants it carries, and the DEV acceptance cases it must satisfy (from `fixtures/acceptance/development-cases.json`, all treated as draft-to-confirm under §8).

| R | Requirement | Verify | Invariants | Acceptance cases |
|---|---|---|---|---|
| R-01 | Inject skill index at task start (UserPromptSubmit hook) | auto | I-08 | DEV-01, DEV-21 |
| R-02 | Claude selects & loads a skill from the index | transcript | — | DEV-01, DEV-25, DEV-36 |
| R-03 | On parent load, expand refs children as body+corrections | auto | I-02, I-03, I-15 | DEV-02, DEV-03, DEV-08, DEV-43..46 |
| R-04 | Loaded skill is reflected in task execution | transcript | — | DEV-18, DEV-25, DEV-27 |
| R-05 | After task completion, suggest saving (Stop notice only) | transcript | — | DEV-05*, DEV-19, DEV-26 |
| R-06 | Re-search similar skills before new registration | auto (perform) / transcript (judgment) | I-06, I-07 | DEV-10, DEV-22, DEV-26 |
| R-07 | Apply nag to correct target, bump version | auto | I-01, I-03, I-13 | DEV-04, DEV-05, DEV-07 |
| R-08 | Nag target correctly判定 as parent vs child | transcript | I-13 | DEV-08, DEV-25 |
| R-09 | Threshold judgment + base_version-based apply/reject | auto | I-04, I-05, I-09, I-12 | DEV-06, DEV-07, DEV-13, DEV-15, DEV-23, DEV-29..32 |
| R-10 | Subagent compaction does not lose existing valid instructions | transcript | I-10, I-11, I-12 | DEV-14, DEV-16, DEV-17, DEV-18, DEV-28 |
| R-11 | Protected-field changes not applied without approval flag | auto | I-14 | DEV-11, DEV-12, DEV-24, DEV-33, DEV-35 |
| R-12 | Server failure does not block user work | auto | I-07, I-08 | DEV-21 |
| R-13 | Server failure does not cause duplicate registration | auto | I-06, I-07 | DEV-22 |
| R-14 | Updated skill is delivered to the next user | auto + transcript | I-01, I-02, I-03 | DEV-27 (three-state), DEV-37, DEV-38 |

Cross-cutting mandatory conditions attached to the above (SPEC §6 note): §4A invariants, §5 security boundary, and retry handling are conditions of acceptance for the related requirements — not separate padded R-IDs.

### Invariant → requirement/case coverage (I-01..I-15)
- I-01 immutable content version → R-07 / DEV-04.
- I-02 latest confirmed on read + record loaded parent/child IDs & versions → R-14 / DEV-08, DEV-37.
- I-03 parent AND child reflect body+corrections → R-03 / DEV-02.
- I-04 stale change-proposal/compaction result cannot overwrite latest → R-09 / DEV-29.
- I-05 retry does not duplicate correction/version → R-09 / DEV-06.
- I-06 block duplicate new registration of same skill_id → R-13 / DEV-09.
- I-07 distinguish server failure from skill-absent → R-12/R-13 / DEV-22.
- I-08 hook wait bounded; failure never blocks user work → R-01/R-12 / DEV-21.
- I-09 never drop valid instructions due to length (no truncate-oldest, no defer) → R-09 / DEV-23.
- I-10 consumer proceeds immediately during compaction (no poll/wait; progress state ≠ content) → R-10 / DEV-16.
- I-11 compaction preserves valid instructions + assets/refs; on failure content unchanged → R-10 / DEV-14, DEV-17.
- I-12 writes (new version + latest pointer + retry record) are atomic (applies to in-memory too) → R-09 / DEV-30.
- I-13 apply correction to correct target + share-intent; infer → confirm first → R-07/R-08 / DEV-25.
- I-14 protected changes need approval (flag check ≠ human-consent evidence) → R-11 / DEV-11.
- **I-15 parent/child depth = max 1, both on new registration AND refs change, on the STORED relation (not a read-time grandchild omission)** → R-03 / DEV-03, DEV-43, DEV-44, DEV-45, DEV-46(allow-boundary). Do not substitute "ignore stored grandchild on read."

## 5. Non-Functional Requirements

### 5.1 Security (SPEC §5 — MANDATORY product requirement; enforced even though Security extension = OFF; §11 F-02)
- Bind to `127.0.0.1` or `::1` only; never expose to the LAN. (DEV-34)
- assets/refs actual file write paths must be contained within the designated temp dir (path-traversal safe). (DEV-24)
- Included scripts are never auto-executed; summarize and require explicit user consent. (DEV-24)
- Server does not auto-collect/store task source code or prompt text; distinguish from user-included Capsule content. (DEV-35)
- Secret-pattern scanning is auxiliary only; do not conflate path checks with body/script content checks. (DEV-33)
- Capsule is advisory; current user request + execution permission take precedence; disclose residual indirect-prompt-injection risk.

### 5.2 Reliability / limits (SPEC §4A I-07/I-08/I-11/I-12; §8 D-03/D-04/D-07)
- Hook connect/response has an upper bound; server slowness/failure must not block user input (fail-open). Concrete cap value decided in §8 D-03 (not fixed to 60s).
- Render + index size limit `L`; over-length rejected at entry preserving content (I-09). Concrete value decided in §8 D-03 (not fixed to 10,000).
- Writes atomic across new version + latest pointer + retry record, including under concurrent nag + background compaction, on the in-memory store (I-12). Compaction failure/abort leaves content unchanged (I-11).

### 5.3 Property-Based Testing (extension ENABLED, full — PBT-01..PBT-10)
- **Framework (PBT-09):** Python → **Hypothesis**, added to project deps; supports custom generators, shrinking, seeded reproducibility.
- **Round-trip (PBT-02):** Capsule JSON serialize/deserialize; rendered-injection text build (structured → text) where losslessly invertible or documented lossy.
- **Invariants (PBT-03):** version monotonic increase on content change; corrections order preserved oldest→newest; refs depth ≤ 1 always; over-length always rejected preserving prior content; compaction preserves the union of valid instructions + assets/refs.
- **Idempotency (PBT-04):** same `request_id` retry ⇒ no new version/correction (I-05); protected-change without approval ⇒ no state change (I-14).
- **Oracle (PBT-05):** compaction merge vs a simplified reference merge model (equivalence of effective ruleset). Note: the C++ workload arithmetic oracle belongs to `verify_sample.py` (evaluator tooling), not our product tests.
- **Stateful (PBT-06):** the Capsule store + session/progress state as a stateful system vs a simplified model — random command sequences (register / load / nag / protected-change / compaction / retry) asserting invariants after each step (I-01..I-14).
- **Generators (PBT-07):** domain generators for Capsule, correction, refs graph (depth-constrained), request_id, base_version — not raw primitives.
- **Shrinking/repro (PBT-08):** shrinking enabled; seed logged on failure; PBT in CI with seed logging.
- **Complementary (PBT-10):** each business-critical path (three-state propagation, I-15 rejection, compaction preservation) also has an example-based test pinning expected values from golden.

### 5.4 Environment & implementation (SPEC §2; Q6..Q10)
- OS: Windows (win32) primary, keep portable where feasible.
- Python 3.10–3.11 server; lightweight framework (FastAPI/Flask) acceptable, loopback-only bind.
- Claude Code installed **v2.1.263** (≥ v2.1.163); README records actual version.
- **In-memory store**, no restart persistence; `make run` starts empty, `make seed` (generic, reads `fixtures/seed/*.json`, no hardcoded IDs — DEV-38) populates each run.
- Compaction threshold = **3** everywhere (configurable, default 3).

## 6. SPEC §8 Open Items — decision order (to be resolved at contract-decisions / Application Design gate; Q11=A)

Resolve in order **D-01 common session state → D-02 action/API mapping → D-03 errors/limits**, then D-04 data/write atomicity, D-05 plugin execution, D-06 refs expansion, D-07 compaction execution. `spec-reference` values (`X-Request-Id`, error names, 60s, 10,000, 24h, `compaction_token`) are examples only and are NOT adopted as fixed; we choose and document our own, grounded in SPEC. §4B is not reopened; I-15 is not an open choice (only its rejection response format is open). These map to `docs/contract-decisions.md` D-01..D-07.

## 7. Deliverables (SPEC §12) & ownership

| Deliverable | Owner | Notes |
|---|---|---|
| README entry point | Team | problem → core loop → install/run/verify → scope → unimplemented/limits → evidence locations; records Claude Code v2.1.263 |
| `make run` / `make verify` / generic `make seed` | Team | `make verify` starts/stops the REAL server in-test and checks mechanical contracts without credentials; a fake Store passing ≠ verification |
| Demo video | **User** | We supply demo script (`docs/demo-scenario.md`) + explanation content |
| HTML **or** PPT explanation | **User** | We supply explanation content (`docs/explanation-brief.md`) |
| Comprehension-check record | Team runs/records | 5-min check with a participant who did not hear the explanation; recorded in `docs/demo-transcript.md` after actual run (currently NOT RUN) |
| Domain/execution evidence | Team | `docs/golden-data.md`, `docs/demo-scenario.md`, `docs/demo-transcript.md`; expected/actual, commands, versions, fail/unverified distinctions |

Video and HTML/PPT are user-authored but remain required (not reductions); we never mark them complete. All transcript/consent/comprehension items are recorded only after real execution.

## 8. Verification Approach & Evidence Honesty (SPEC §7, §11)

- `make verify` = automatic mechanical contract checks against a real spun-up server.
- Transcript items proven by real A/B/C runs vs pre-set expectations in golden/demo docs (expected+actual = evidence; a transcript without both is just a log).
- Three-state proof: C0 (pre-correction) / C1 (post-correction, pre-compaction) / C2 (post-compaction), same clean original workload + same request; record actually-loaded versions each run. C environment excludes golden/script/B-edits/evaluator/reports.
- Candidate functional checks use evaluator-held fixed runner/probe/API headers (incl. DoRun returned image, non-default Reset, object independence) — kept separate from propagation evidence. `EXPECTED_INCOMPLETE` in sample checks is the original task state; do not edit C-original or golden to satisfy it.
- New `skill_id` cloning must NOT substitute for correction propagation on the same `skill_id`.
- Distinguish: unverified / failed / unimplemented / approved-exclusion. Do not record tests/consent/demos not actually performed (F-04).
- **§11 F-01 note:** SPEC §4A defines I-15 but §11 F-01's parenthetical lists only I-01..I-14. Per SAMPLE-IMPROVEMENTS.md this wording is a known discrepancy; checks apply I-15 regardless. A §9 wording fix to F-01 will be proposed with the spec-change record.

## 9. Approved decisions this stage (from clarifying answers)
- Extensions: Security OFF (but §5/F-02 stay mandatory), Resiliency OFF (I-07/08/11/12 stay), PBT ON full.
- Full v1 scope; user authors video + HTML/PPT; comprehension check proceeds.
- Threshold = 3 (approved §9 adjustment of §4B).
- Windows primary; Python 3.10–3.11; framework OK loopback-only; in-memory (no restart persistence); Claude Code v2.1.263.
- §8 contracts proposed by team, user approves at contract-decisions gate.

## 10. Key requirements summary
Build a local loopback-only Python server + Claude Code plugin implementing the correction-propagation loop with hard invariants I-01..I-15 (esp. I-15 depth-1 on stored relations both directions, and I-03 parent+child correction delivery), compaction as the differentiator (threshold 3, subagent, preserve-or-no-change), protected-field approval, atomic in-memory writes, idempotent retries, and §5 security boundary — proven by `make verify` (mechanical) + real three-state C0/C1/C2 transcripts (propagation) with strict evidence honesty. Detailed §8 API/schema/error/limit contracts are proposed next and approved before code.
