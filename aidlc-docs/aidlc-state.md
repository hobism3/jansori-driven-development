# AI-DLC State Tracking

## Project Information
- **Project Type**: Greenfield (Jansori product) — see Workspace State note
- **Start Date**: 2026-09-08T00:00:00Z
- **Current Stage**: CONSTRUCTION — **U1 persistence bug fix DONE 2026-09-09 (2nd pass)**: persist-first commit + single-instance lock. `_commit_locked` now writes disk BEFORE in-memory (rollback-free atomicity, fixes partial-commit/PRESERVATION_FAILED cascade); NEW `server/store/instance_lock.py` prevents two processes sharing one data file (root trigger: PIDs 1996+9576 shared `jansori-data.json`). **150 passed** (144 + 6). See code/persistence-summary.md §"Bug fix". *(1st pass: JSON snapshot persist-by-default, supersedes Q9, 144 passed.)* Prior AI-DLC workflow complete (U1/U2/U3/U4 + Build and Test 2026-09-08).

## Workspace State
- **Existing Code**: Yes, but NOT product code. Sample fixtures (C++ workloads, seed/acceptance/golden JSON) + Python sample-evaluator tooling + AI-DLC rule details + SPEC/reference docs.
- **Jansori Product Code Present**: No (no server/, plugin/, Store, HTTP adapter, or Makefile).
- **Reverse Engineering Needed**: No. Per README-START-HERE.md §3 and START-AI-DLC.txt, pre-made CPP/sample evaluators do NOT imply an existing Jansori implementation. Fixtures are treated as requirements/verification inputs, not product source to reverse-engineer or optimize.
- **Programming Languages (fixtures/tools)**: C++ (workloads), Python (sample evaluator)
- **Target Product Stack**: TBD in NFR Requirements — SPEC §2 mandates Claude Code Plugin + local Python server
- **Workspace Root**: C:\Users\WoongbumHwang\Desktop\20260908_jansori

## Code Location Rules
- **Application Code**: Workspace root (NEVER in aidlc-docs/)
- **Documentation**: aidlc-docs/ only
- **Structure patterns**: See code-generation.md Critical Rules

## Guardrails Carried From SPEC / START Prompt (do not violate without §9/§10 approval)
- Do NOT fill workload TODOs or edit golden/C-original during development.
- Distinguish sample functional checks (fixed runner/probe/verify_sample.py) from real Plugin propagation evidence (transcripts).
- Preserve §4A invariants I-01..I-15 and adopted §4B baseline; do not reopen §4B or import old fixed Stage/Unit/version plans.
- I-15: max reference depth 1 applies to BOTH new registration and refs changes; do not substitute "ignore stored grandchild on read."
- §8 decision order: common session state → action/API mapping → errors/limits, then data/write atomicity, plugin execution, refs, compaction.
- Do NOT record tests/consent/demos/understanding-checks that were not actually performed. This turn's message is NOT blanket approval.

## Stage Progress
### 🔵 INCEPTION PHASE
- [x] Workspace Detection
- [ ] Reverse Engineering — N/A (greenfield product)
- [x] Requirements Analysis (APPROVED 2026-09-08T02:00:00Z)
- [x] User Stories (APPROVED 2026-09-08T03:00:00Z — personas.md 3인 + stories.md US-01..US-17)
- [x] Workflow Planning (APPROVED 2026-09-08T03:15:00Z — execution-plan.md)
- [x] Application Design — APPROVED 2026-09-08T05:00:00Z (components/component-methods/services/component-dependency/application-design + contract-decisions D-01..D-07; Q7=B refined; terminology non-conflation guaranteed)
- [x] Units Generation — APPROVED 2026-09-08T06:00:00Z (unit-of-work.md + unit-of-work-dependency.md + unit-of-work-story-map.md; Q1..Q6=A; 4 units U1→U2→U3→U4, single-repo per-unit dirs)

### 🟢 CONSTRUCTION PHASE (per-unit loop)

**Current unit: U3 — Capsule Normalizer Subagent** (order U1→U2→U3→U4; U1, U2 complete)

#### U1 — Server & Store & Contracts
- [x] Functional Design — APPROVED 2026-09-08T07:00:00Z (Q1..Q10=A; domain-entities.md + business-logic-model.md + business-rules.md; Capsule schema, versioning/normalization/refs logic, I-01..I-15 as PBT properties, §5 folded in)
- [ ] NFR Requirements — SKIP (user-approved; see phase-level note)
- [ ] NFR Design — SKIP (user-approved)
- [ ] Infrastructure Design — SKIP (user-approved; local loopback + in-memory)
- [x] Code Generation — APPROVED 2026-09-08T09:00:00Z (server/ 21 modules incl. resolve-target endpoint + tests/unit/u1 5 files + code summaries + D-01..D-08; U1-owned invariants I-01..I-15 + §5 implemented and smoke-verified; full PBT + 3.10/3.11 run deferred to U4)
  - **REOPENED 2026-09-08T13:00:00Z → RE-APPROVED & re-CLOSED 2026-09-08T13:10:00Z (user-approved)** — normalization preservation redesign: verbatim-substring → **id-declaration + structural** (schemas.NormalizeInput +merged_correction_ids; validate_preservation/commit_normalization rewritten; dead _normalize_text/re removed; routes pass field). Enables real compaction (condense/paraphrase); server no longer judges per-correction reflection (subagent responsibility). Tests updated (condense passes / unknown-id 422 / partial-merge carry-forward / over-length / stale). **Full regression 75 passed.**

**U1 post-generation review (3 subagents, 2026-09-08T08:15:00Z):** BLOCKER B1 (I-15 upward via protected-change), MAJOR M1/M2/M3 (idempotency: exact-result replay + skill-bound request_id + global request lock), MAJOR M4 (composite render length), MAJOR loopback bypass on uvicorn path, MINOR resolve_target loose match / dead code / state duplicate — **ALL FIXED + regression tests added (43→54)**. See audit.md.

### 🟢 CONSTRUCTION PHASE — remaining units & final stage
- [x] U2 — Claude Code Plugin (per-unit loop: Functional Design → Code Generation) — CLOSED 2026-09-08T11:30:00Z
  - [x] Functional Design — APPROVED 2026-09-08T10:12:00Z (business-logic-model 6 흐름 + business-rules BR-01..BR-11 + domain-entities; Q1..Q12=A; **자연어 잔소리 항상 자동 판별** 결정 반영 — UserPromptSubmit 행동 프리앰블 BR-02.3/02.4)
  - [ ] NFR Requirements / NFR Design / Infrastructure Design — SKIP (client-side plugin, loopback HTTP only; consistent with U1 phase-level skip)
  - [x] Code Generation — APPROVED 2026-09-08T11:30:00Z (plugin/ 8 files: plugin.json, scripts/jansori_client.py, hooks/{user_prompt_submit,stop_notice}.py+hooks.json, skills/load/SKILL.md, commands/{nag,save}.md; tests/unit/u2 3 files [**U2 18 / total 72 passed**]; code summaries + README-u2. US-01/02/04/05/13 + participating implemented. Windows cp949 encoding bug found via live-server integration test & fixed. CC-runtime wiring = U4 residual checklist, unverified/F-04)
- [~] U3 — Capsule Normalizer Subagent (per-unit loop) — IN PROGRESS
  - [x] Functional Design — APPROVED 2026-09-08T12:15:00Z. Q1..Q11=A (Q2=C→A after clarification: keep CLOSED U1 substring-preservation contract, U3 conforms). business-logic-model (NL-1..8) + business-rules (BR-U3-01..11) + domain-entities (E1..5). Primary US-11 / participating US-12,US-17. Grounds on U1 BL-5/BL-6/BL-7. **U1 unchanged.**
  - [ ] NFR Requirements / NFR Design / Infrastructure Design — SKIP (Q11=A; client-side subagent, loopback HTTP only; consistent with U1/U2 phase-level skip)
  - [x] Code Generation Part 1 (Planning) — APPROVED 2026-09-08T13:20:00Z (updated for merged_correction_ids + Issue2 stdin + Issue3 note)
  - [x] Code Generation Part 2 — APPROVED & CLOSED 2026-09-08T13:45:00Z (user "승인"). plugin/agents/capsule-normalizer.md (subagent def) + plugin/scripts/jansori_client.py normalize action (additive) + tests/unit/u3 3 files [**U3 20 / total 95 passed**] + code summaries + README-u3 (U4 residual UNVERIFIED). US-11 primary implemented to contract+live-HTTP level. Runtime wiring (CC launch, LLM merge quality, isolation enforcement, 3.10/3.11, Windows install) = U4 residual/F-04.
- [~] U4 — Build/Verify/Seed + PBT Harness (per-unit loop, LAST unit) — IN PROGRESS
  - [ ] Functional Design — SKIP (user-approved 2026-09-08T13:50:00Z; no new business logic/domain models; PBT properties = U1 invariants I-01..I-15 already defined; U4 is build/verify/seed + test harness)
  - [ ] NFR Requirements / NFR Design / Infrastructure Design — SKIP (user-approved; dev/test harness, loopback only; consistent with U1/U2/U3)
  - [x] Code Generation Part 1 (Planning) — APPROVED 2026-09-08T14:40:00Z (plan finalized after golden-coverage audit: 8 gap-closures + DEV→test traceability matrix + DEV-11 resolved Option A). Plan: plans/U4-build-verify-seed-pbt-code-generation-plan.md (16 steps)
  - [x] Code Generation Part 2 — APPROVED & U4 CLOSED 2026-09-08T15:15:00Z (user "승인"). All 16 steps [x]. NEW: pyproject markers; tests/conftest.py (centralized live-server harness + Hypothesis profiles/seed logging PBT-08); tests/pbt/{generators,roundtrip PBT-02,invariants PBT-03,idempotency PBT-04,oracle PBT-05,stateful PBT-06+load-semantics}; tests/golden/{core_paths,three_state US-12/DEV-27+DEV-14}; tests/verify/test_verify_contract (US-17 real-server + DEV-29/32); scripts/seed.py (generic DEV-38, smoke-verified idempotent); Makefile; README.md; 5 code summaries + golden-coverage-matrix.md (DEV-01..46 mapped). **pytest tests -q → 138 passed (Python 3.12.7)**. US-12/US-16/US-17 primary implemented to server-state/contract level. RESIDUAL/UNVERIFIED (F-04, NOT done): 3.10/3.11 run; make-on-Windows; real CC runtime propagation transcript; demo video + HTML/PPT (user deliverables).
- [x] Build and Test — APPROVED & COMPLETE 2026-09-08T15:35:00Z (user "승인"). Generated build-and-test/{build-instructions,unit-test-instructions,integration-test-instructions,performance-test-instructions,build-and-test-summary}.md. **Full suite 138 passed** (unit 95 + pbt 15 + golden 21 + verify 7, Python 3.12.7). Perf load/stress N/A (local single-user); §5 security covered. Residual (F-04): 3.10/3.11 run, make-on-Windows, real CC runtime transcript, demo video+HTML/PPT (user deliverables).

### 🟡 OPERATIONS PHASE
- [~] Operations (placeholder — no deployment/monitoring stages defined in this workflow; construction complete)

## Extension Configuration

| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis (Q1=B) |
| Resiliency Baseline | No | Requirements Analysis (Q2=B) |
| Property-Based Testing | Yes (full) | Requirements Analysis (Q3=A) |

**IMPORTANT — extension vs SPEC:** Security Baseline extension being OFF does NOT relax SPEC §5 or §11 F-02. SPEC §5 security boundary (loopback-only bind 127.0.0.1/::1, temp-dir path containment, no script auto-exec, no auto-collection of task source/prompts) remains a MANDATORY product requirement enforced via requirements/design/tests, not via the extension. Resiliency invariants I-07/I-08/I-11/I-12 likewise remain mandatory per §4A.

## Approved Decisions & Deviations (Requirements Analysis)
- **Scope (Q4=X):** Full v1 loop — local Python server + Claude Code plugin (hooks + load Skill + save/nag) + refs depth-1 + compaction (subagent) + assets + generic `make seed` + README + comprehension check. **Demo video and HTML/PPT are authored by the USER**; we supply explanation content, demo script, golden/scenario/transcript inputs. These deliverables are NOT dropped (still required per §12/§10); ownership shifts. We never mark them complete on our side.
- **Compaction threshold (Q5=B):** Single value **3** everywhere (demo-aligned). Approved §9 adjustment of §4B baseline ("default 10 / test 3"). Implement configurable, default 3. Does not weaken any invariant.
- **OS (Q6=A):** Windows (win32) primary; keep server portable where feasible.
- **Python (Q7=B):** 3.10–3.11 for the Jansori server.
- **Claude Code version (Q8=A):** Installed **v2.1.263** (≥ required v2.1.163). Record in README; confirm actual before demo.
- **Persistence (Q9=B):** In-memory only; no restart persistence. `make run` starts empty, `make seed` populates each run. I-12 atomicity still applies to in-memory multi-field updates.
- **Server impl (Q10=B):** Lightweight framework (FastAPI/Flask) acceptable; must still bind loopback-only.
- **§8 contracts (Q11=A):** Our team proposes concrete contracts (grounded in SPEC + examples, documented as our decisions — not copied from spec-reference as fixed); user approves at contract-decisions / Application Design gate before code.

## Terminology Guardrail (2026-09-08)
- **"캡슐 정상화 (Capsule Normalization)" = SPEC/requirements의 "compaction"** (corrections를 병합해 새 Capsule 콘텐츠 버전 생성). **Claude Code의 context compaction(대화 트랜스크립트 자동 요약)과 절대 혼용 금지.**
- 런타임 식별자는 `normalize` 계열: `POST /skills/{id}/normalize`, `GET /skills/{id}`, 플래그 `normalize_due`/`normalize_in_progress`, 서브에이전트 `capsule-normalizer`, 서비스 `NormalizationService`. "compaction"은 설계문서 SPEC 추적 별칭으로만.
- capsule-normalizer 서브에이전트는 서버 GET으로 Capsule JSON만 처리; 대화 트랜스크립트 미접근(§5/§8 격리). 보장 상세: `application-design/contract-decisions.md` 용어 구분 절.

## Working Preferences
- Question files (질문지) from now on are written in **Korean** (per user instruction 2026-09-08).
