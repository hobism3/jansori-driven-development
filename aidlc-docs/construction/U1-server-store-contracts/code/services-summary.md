# U1 Code Summary — Services Layer

> 코드: `server/services/`. 비즈니스 규칙. 테스트: `tests/unit/u1/test_services.py`(전부 통과).

## SkillService (CMP-02) — US-01/02/03/06/14
- `register`: assets 경로 격리(§5)·길이(I-09)·depth-1(I-15)·중복(I-06) 검사 후 v1 원자 등록. **유사 재검색은 클라이언트(U2) build_index 몫, 서버 LLM 없음(Q4=A)**.
- `load` + `expand_refs`: depth-1 직속 자식 body+corrections 확장(I-03), 활성 범위·version 세션 기록(I-02). 부재 자식은 확장 제외+플래그. **길이 검사는 각 노드의 합성 렌더(body + corrections) 기준**(I-09/Q6=A, M4 수정 — corrections 제외한 body-only 검사 아님).
- `build_index`: 이름/설명만(LLM 없음). `get_capsule`: 서브에이전트 GET용 전체 JSON.

## NagService (CMP-03) — US-07/08/09/10
- `apply_nag`: 멱등 replay(I-05) → 대상 존재 → 길이(I-09) → Correction 누적 + version+1(I-01) → 원자 커밋(stale I-04) → `normalize_due` 반환.
- `resolve_target`: 활성 세션 범위 **정확 skill_id 유일 매칭**(Q5=A). 0/다중/부분일치 → `NEEDS_CONFIRMATION`(느슨한 부분문자열 매칭 제거 — 잘못된 유일매칭 방지; 이름 기반 선택은 U2 몫, I-13). **HTTP 노출**: `GET /skills/resolve-target?hint=&session_id=`(US-08).
- `check_threshold`: corrections ≥ 임계(3) → normalize_due. **래치(≥) 해석**: 임계 도달 시 발화하고 커밋 전까지 유지(추가 nag 누적 중에도, I-10). 정상화 커밋으로 corrections 비워지면 해제.
- `apply_protected_change`: 보호필드 여부 확인 → approval 플래그(I-14) → stale(I-04) → refs면 depth-1 **양방향** 재검사(하향 `assert_depth_one` + **상향 `is_referenced_as_child`** — 이미 자식인 Capsule이 자식을 갖는 손자 생성 차단, B1 수정, I-15) → 원자 커밋. skill_id는 v1에서 불변.

## NormalizationService (CMP-04, SPEC compaction) — US-11
- `validate_preservation` (**재설계 2026-09-08 U1 재오픈**, 서버 LLM 없음): 길이 ≤ L + `merged_correction_ids` 비어있지 않음 AND ⊆ base corrections id 집합. refs/assets는 정상화가 body만 바꾸므로 구조적 보존. **폐기: 각 correction의 verbatim 정규화-부분문자열 추적** → 서브에이전트가 축약·의역 가능(병합 품질은 서브에이전트 책임).
- `commit_normalization(skill_id, base_version, new_body, request_id, merged_correction_ids)`: 멱등 → 존재 → 길이 → 보존검증(실패 시 PRESERVATION_FAILED[422], 무변경 I-11) → body 교체·version+1·**선언된 merged_correction_ids만 제거(나머지 이월)**·원자 커밋(I-12). base 불일치 시 STALE → 서브에이전트 재시작(I-04).
- ⚠️ 대화 트랜스크립트 미접근. context compaction과 무관.

## SessionService (CMP-05) — D-01
- `get_or_create_session` / `set_active_scope`(I-02) / `set_progress_flag`(콘텐츠 분리 I-10) / `active_scope_ids`(resolve_target용).
