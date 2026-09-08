# U3 Code Summary — Client `normalize` Action (additive to U2 shared client)

**파일**: `plugin/scripts/jansori_client.py` (순수 추가 — 기존 index/get/load/resolve-target/nag/register/protected-change 시그니처·동작 불변; Q7=A 공통 클라이언트 재사용).

- **`act_normalize(skill_id, base_version, new_body, merged_correction_ids, request_id, timeout_ms)`**
  → `POST /skills/{id}/normalize` body `{base_version, new_body, request_id, merged_correction_ids}`.
  loopback-only(`_assert_loopback`), 구조화 오류 파싱(STALE_BASE_VERSION / PRESERVATION_FAILED[422] / OVER_LENGTH / SKILL_ABSENT / SERVER_ERROR[status 0], I-07 비혼용).
- **CLI `normalize`**: `--id`, `--base-version`, `--merged-id`(append, 1+ required), body 소스 **상호배타 필수** `--new-body` | `--new-body-stdin`(대용량/멀티라인 stdin, Issue 2).
- **dispatch**: `rid = --request-id or uuid4()` — 시도별 새 id(BR-U3-09), 재전송 시 caller가 동일 id 재사용(I-05). stdin body는 `sys.stdin.read()`.
- UTF-8 stdio(`_force_utf8_stdio`)·loopback 가드 재사용 — U3에 그대로 적용(한국어 body 안전).

**계약 정합**: U1 재설계된 `NormalizeInput`(base_version, new_body, request_id, merged_correction_ids) 및 `validate_preservation`(id 선언 검증)와 일치. 서버가 선언된 corrections만 제거.
