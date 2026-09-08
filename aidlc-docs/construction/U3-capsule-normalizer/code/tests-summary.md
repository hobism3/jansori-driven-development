# U3 Code Summary — Tests

**디렉터리**: `tests/unit/u3/` (conftest.py로 `plugin/scripts` + repo root를 sys.path에 추가).

## test_normalize_client.py (클라이언트 계약, monkeypatch urllib)
- 요청 형태: POST `/skills/{id}/normalize` body에 `merged_correction_ids` 선언 포함.
- 오류 분류: STALE_BASE_VERSION / PRESERVATION_FAILED(422) / OVER_LENGTH / SERVER_ERROR(status 0, I-07).
- request_id: 시도마다 새 uuid(BR-U3-09) / `--request-id` 지정 시 동일 재사용(I-05).
- CLI 검증: `--merged-id` 필수, body 소스(`--new-body`|`--new-body-stdin`) 필수.

## test_agent_definition.py (정의 파일 구조 계약 — 런타임 행동 아님)
- 파일 존재; frontmatter 유효 YAML(pyyaml, importorskip); `name==capsule-normalizer`; `tools==Bash`(최소).
- 본문 필수 요소: 용어 구분(context compaction), 격리(트랜스크립트 미접근), merged-id 선언, normalize 계약, STALE 처리, 재시작·재병합 상한(각 3), 무변경·정직성(F-04), 비차단(I-10), 번들 클라이언트 사용(`${CLAUDE_PLUGIN_ROOT}`).

## test_normalize_integration.py (실기동 U1 서버, uvicorn 스레드 + 임의 loopback 포트)
- (a) 축약 body + 전체 id → **커밋 성공**·corrections 비워짐·body 교체·version+1.
- (b) stale base_version → **STALE_BASE_VERSION**.
- (c) 미지의 correction id → **PRESERVATION_FAILED(422)**.
- (d) new_body > L(10000) → **OVER_LENGTH**.
- (e) 부분 선언 → 선언된 것만 제거·나머지 이월.
- (f) Issue 3: stale 포기 후 콘텐츠 무변경 확인 → fresh base·새 attempt id로 재시도 성공(bounded·I-11-safe).

## 실행 결과 (정직 기록)
- `python -m pytest tests/unit/u3 -q` → **20 passed**.
- `python -m pytest tests -q` → **95 passed** (U1 57 + U2 18 + U3 20). Python 3.12.7.
- 3.10/3.11 실행은 미수행 → U4 잔여(코드는 `from __future__ import annotations` + `X|None`로 3.10 호환 작성, 미검증).
