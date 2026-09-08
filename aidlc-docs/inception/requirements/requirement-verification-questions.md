# Requirements Clarification Questions — Jansori Plugin

Please answer each question by filling in the letter after the `[Answer]:` tag. If none fit, choose the "Other" option and describe after the tag. Let me know when you're done.

**Scope note (read first):** The detailed SPEC §8 contracts (session-state storage, request/response schemas, error names, limit numbers, write atomicity, refs/compaction mechanics) are **not** asked here as raw schema choices. Per your START prompt, our team proposes those concrete contracts during Application Design, grounded in SPEC + `docs/spec-reference.md` *examples* (which are format samples, not fixed contracts), and you approve them at the contract-decisions gate. These questions cover only decisions where your input changes **what** we build. Adopted §4B baselines and invariants I-01..I-15 are **not** reopened.

---

## Section A — Extension Opt-Ins (required)

## Question 1: Security Extensions
Should security extension rules be enforced for this project?

A) Yes — enforce all SECURITY rules as blocking constraints (recommended; SPEC §5 defines a real security boundary — loopback-only bind, path containment, no auto-exec of scripts, no auto-collection)

B) No — skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 2: Resiliency Extensions
Should the resiliency baseline (AWS Well-Architected Reliability directional best practices) be applied?

A) Yes — apply the resiliency baseline as directional design-time guidance

B) No — skip it (recommended here: this is a single-instance local demo server explicitly excluding availability/scaling optimization per SPEC §10; SPEC §4A already fixes the specific fault-handling invariants I-07/I-08/I-11/I-12 we must meet)

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 3: Property-Based Testing Extension
Should property-based testing (PBT) rules be enforced?

A) Yes — enforce all PBT rules as blocking constraints (recommended; the domain has real algorithmic/state logic — versioning, corrections ordering, refs depth-1, compaction merge, idempotent retries — that benefit from property tests)

B) Partial — PBT only for pure functions and serialization round-trips

C) No — skip all PBT rules

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Section B — Scope & Reduction

## Question 4: v1 scope
Should we build the full v1 correction-propagation loop with no reductions right now?

A) Full scope — local Python server + Claude Code plugin (hooks + load Skill + save/nag paths) + refs depth-1 expansion + compaction (subagent) + assets + generic `make seed` + README + demo video + HTML/PPT + comprehension check (recommended)

B) Pre-approve a reduction now — I'll name it; reductions follow SPEC §10 order (make seed automation → assets → refs → compaction) and require the §9/§10 approval + invariant/R-ID updates

X) Other (please describe after [Answer]: tag below)

[Answer]: X, local Python server + Claude Code plugin (hooks + load Skill + save/nag paths) + refs depth-1 expansion + compaction (subagent) + assets + generic `make seed` + README 까지는 맞으나, 그 후의 데모 비디오나, HTML 은 내가 직접 만들거야. comprehension check 진행해

## Question 5: Compaction threshold
Confirm the correction-count threshold that triggers compaction.

A) Configurable; production default 10, demo/tests use 3 (recommended — matches golden/demo fixtures)

B) Different values (describe after [Answer]:)

X) Other (please describe after [Answer]: tag below)

[Answer]: B, 데모와 통일하여 모두 3으로 진행

---

## Section C — Execution Environment (SPEC §2 & §8 "실행 환경")

## Question 6: Development / demo OS
Where will the server run and the A/B/C demo be recorded?

A) This Windows machine (win32) is primary; keep the server portable where feasible

B) macOS or Linux is primary

C) Cross-platform — must run on Windows and a Unix-like OS

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 7: Python version for the product server
(Note: the C++ workload build and `tools/verify_sample.py` are separate sample tooling; this is about the Jansori server.)

A) Python 3.12+

B) Python 3.10–3.11

C) Team picks/installs a suitable 3.10+ version

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 8: Installed Claude Code version
SPEC §2 requires minimum v2.1.163 and that the README records the actual installed version.

A) I'll provide the exact installed version now (write it after [Answer]:)

B) Assume ≥ v2.1.163 for design; I'll confirm and record the actual version before the demo

X) Other (please describe after [Answer]: tag below)

[Answer]: A, v2.1.263 이야.

## Question 9: Persistence across restart
Must Capsules and session/progress state survive a server restart?

A) Yes — persist Capsule JSON (and durable state) to disk under the server data dir (recommended; supports seed + reproducible demo)

B) No — in-memory only is acceptable for the demo

X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Section D — Implementation Preferences

## Question 10: Python server implementation
Any preference for how the local server is built?

A) Standard library only (`http.server`) — minimal dependencies, easiest to review/run

B) A lightweight framework (FastAPI / Flask) is acceptable

C) Team decides during Application Design based on the API contract

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 11: §8 contract review checkpoint
How do you want to handle the detailed §8 contracts (session state → action/API mapping → errors/limits, then data/atomicity, plugin execution, refs, compaction)?

A) We propose concrete contracts (grounded in SPEC + examples, documented as our decisions — not copied from `spec-reference` as fixed) and you approve them at the contract-decisions / Application Design gate before code (recommended)

B) You will specify some of them now (describe after [Answer]:)

X) Other (please describe after [Answer]: tag below)

[Answer]: A
