# Golden Coverage Matrix — DEV-01..46 → test / out-of-scope

Auditable mapping of every `fixtures/acceptance/development-cases.json` case to a covering
test (existing U1 unit test or new U4 test) OR an explicit out-of-scope rationale. Produced
to close the "no DEV→test traceability" gap from the golden audit (also serves DEV-39/F-04
evidence honesty). Modes in the source: `automatic`, `automatic+transcript`, `transcript`,
`artifact_review`.

| DEV | Coverage | Where |
|---|---|---|
| DEV-01 | OUT-OF-SCOPE (U2 hook/session concern; CLOSED unit) | u2 hook tests |
| DEV-02 | COVERED | golden `test_load_expands_depth1_child`; u1 load tests |
| DEV-03 | COVERED | golden `test_refs_self_reference_rejected`, `test_refs_grandchild_rejected_on_register`, `test_missing_and_duplicate_refs_are_tolerated` |
| DEV-04 | COVERED | pbt `test_i01_version_increments_by_one_and_history_immutable`; u1 version tests |
| DEV-05 | COVERED | pbt/stateful `test_load_delivers_latest_child_even_if_parent_unchanged` |
| DEV-06 | COVERED | pbt `test_nag_replay_is_exact_and_stateless`; u1 idempotency test |
| DEV-07 | COVERED | pbt `test_i04_stale_base_version_rejected_no_change`; u1 stale test |
| DEV-08 | COVERED | pbt/stateful `test_load_delivers_latest_child_even_if_parent_unchanged` |
| DEV-09 | COVERED | golden `test_duplicate_registration_blocked`; pbt `test_register_idempotent_replay_vs_duplicate` |
| DEV-10 | OUT-OF-SCOPE (U2 client-path / index re-search) | u2 client tests |
| DEV-11 | COVERED (resolved: implemented PROTECTED_FIELDS authoritative) | golden `test_protected_change_field_set` — see note below |
| DEV-12 | OUT-OF-SCOPE (U2 nag routing) | u2 command tests |
| DEV-13 | COVERED | golden `test_normalize_due_latches_at_three`; three_state |
| DEV-14 | COVERED | golden `test_dev14_full_merge_retention_and_atomicity` |
| DEV-15 | COVERED | verify `test_nag_threshold_then_normalize` (normalize commit path) |
| DEV-16 | COVERED (over-length preserve) | pbt `test_i09_length_boundary_on_register`; u1 over-length |
| DEV-17 | COVERED (server-error≠absence) | u1 api error tests; verify `test_error_contract_matrix` |
| DEV-18 | OUT-OF-SCOPE (transcript mode; real CC runtime) | demo transcript (F-04, NOT_RUN) |
| DEV-19..22 | OUT-OF-SCOPE (U2 hook/session/NL — CLOSED unit) | u2 tests |
| DEV-23 | COVERED (over-length rejected+preserved) | pbt `test_i09_...`; u1 over-length |
| DEV-24 | COVERED (temp-dir containment) | u1 `test_contain_path*` |
| DEV-25 | OUT-OF-SCOPE (U2 NL common path) | u2 tests |
| DEV-26 | OUT-OF-SCOPE (U2 stop-notice) | u2 tests |
| DEV-27 | COVERED (server-state level; propagation = transcript) | golden `test_three_state_server_level_reproduction` |
| DEV-28 | COVERED | golden `test_progress_flag_toggle_does_not_change_capsule` |
| DEV-29 | COVERED | verify `test_dev29_dev32_approval_stale_and_retry_idempotent` |
| DEV-30 | COVERED (atomicity) | u1 `test_concurrent_register_only_one_wins`; pbt/stateful invariants |
| DEV-31 | COVERED (cross-skill request_id) | pbt `test_request_id_bound_to_skill_cross_use_rejected`; u1 M2 test |
| DEV-32 | COVERED | verify `test_dev29_dev32_approval_stale_and_retry_idempotent` |
| DEV-33 | COVERED (scripts not auto-executed) | u1 `test_guard_script` |
| DEV-34 | COVERED (loopback-only) | golden `test_loopback_hosts_*`; verify `test_client_refuses_non_loopback_url`; u1 loopback |
| DEV-35 | COVERED (index name/description only) | verify `test_register_index_load_refs`; u1 index test |
| DEV-36 | OUT-OF-SCOPE (U2 fail-open hook budget) | u2 hook tests |
| DEV-37 | COVERED | pbt/stateful `test_earlier_load_not_retro_invalidated_by_later_commit` |
| DEV-38 | COVERED (generic seed) | `scripts/seed.py` + live smoke (README-u4) |
| DEV-39 | OUT-OF-SCOPE (artifact_review; this matrix IS the honesty artifact) | this file / README F-04 |
| DEV-40 | OUT-OF-SCOPE (transcript mode) | demo transcript (NOT_RUN) |
| DEV-41 | OUT-OF-SCOPE (artifact_review; human) | user deliverable |
| DEV-42 | OUT-OF-SCOPE (evaluator numeric C++ contract) | workload-golden (evaluator tooling) |
| DEV-43 | COVERED (upward depth-1) | u1 `test_protected_change_refs_upward_depth_limit` |
| DEV-44 | COVERED | golden `test_refs_change_making_with_children_capsule_a_child_rejected` |
| DEV-45 | COVERED (register grandchild refused) | u1 `test_depth_limit_on_register`; golden `test_refs_grandchild_rejected_on_register` |
| DEV-46 | COVERED (ALLOW boundary positive) | golden `test_allow_depth1_register_and_refs_change_succeed` |

## DEV-11 note (contract discrepancy, resolved)
`development-cases.json` DEV-11 lists protected-change candidates as
`name/description/keywords/assets/refs`. The implemented, U1-approved (CLOSED) contract is
`PROTECTED_FIELDS = {skill_id, name, refs_children, protected_fields}`. **Resolution (user
decision 2026-09-08, Option A):** implemented set is authoritative; U1 not reopened; the
DEV-11 list is treated as a superseded/looser doc note. `description/keywords/assets` follow
the normal (non-protected) change path (a protected-change on `description` returns
VALIDATION_ERROR).

## Out-of-scope fixtures (whole-file, per SPEC guardrails)
- `fixtures/acceptance/workload-golden.json` (W-01..42 + 5 invalid): C++ image-arithmetic numeric contract — evaluator tooling, not product service tests. (Don't fill workload TODOs; sample checks ≠ propagation evidence.)
- `fixtures/acceptance/lifecycle-golden.json` (24 steps): evaluator-only C++ session-probe public behavior.
- `fixtures/acceptance/demo-cases.json` (DEMO-*, `actual_plugin_transcript`, NOT_RUN): user-deliverable demo transcripts.
- three-state member-name fields (`expected_ready_member`, `expected_frame_count_member`, `preserve_existing_member`) and `observations_status`: real C++ code-propagation, transcript-only.
