# U1 Code Summary — Store Layer

> 코드: `server/store/capsule_store.py`. 인메모리 저장·원자 커밋·멱등. 테스트: `tests/unit/u1/test_store.py`(전부 통과).

## CapsuleStore
| 메서드 | 역할 | 불변식 |
|---|---|---|
| `get_latest(skill_id)` | 최신 확정 Capsule 또는 None | I-02 |
| `exists(skill_id)` | 중복 등록 판정 | I-06 |
| `get_request(request_id)` | 기처리 요청이 **만든 정확한 Capsule** 반환(현재 latest 아님) | I-05 |
| `is_referenced_as_child(skill_id)` | 역방향 참조 조회(어떤 Capsule이 이 skill을 자식으로 두는가) | I-15 상향 |
| `register(capsule, request_id)` | 신규 등록(락 내 중복 재검사) | I-06/I-12 |
| `commit(new_capsule, request_id, origin, expected_base_version)` | stale 검사 → 포인터 스왑 → history append → request 기록(1 원자단위) | I-04/I-05/I-12 |
| `history(skill_id)` | 불변 version 스냅샷 목록 | I-01 |

## 원자성·동시성 (I-12/D-04) — 검토 반영
- **락 순서 고정**: `skill_id별 RLock` → **전역 `_request_lock`**(항상 이 순서로 획득, 데드락 없음).
- `commit`/`register`는 **replay(I-05) → stale(I-04) → 스왑 → history → request 기록**을 두 락(스킬+전역요청) 구간에서 수행 → 동시 nag + 백그라운드 정상화, 그리고 **교차 skill 동일 request_id**에도 부분/중복 저장 없음(전역 멱등 진짜 보장, M3 수정).
- **멱등(Q10=A, M1/M2 수정)**: request_log가 **그 요청이 만든 Capsule 자체**를 보관 → 재수신 시 개입 쓰기가 있어도 **그 요청의 정확한 결과** 반환(현재 latest 아님). request_id는 **최초 사용한 skill에 바인딩** → 다른 skill에 재사용 시 `VALIDATION_ERROR`(남의 Capsule 반환·조용한 누락 방지).
- **동시 등록 테스트**: 8스레드 동시 register → 정확히 1건 성공, 7건 DUPLICATE_REGISTRATION.
- **역참조(I-15 상향)**: `is_referenced_as_child`로 "이미 자식인 Capsule이 자식을 갖는" protected-change 경로 차단(NagService에서 호출).

## 지속성
- 인메모리, 재시작 비영속(Q9). `make run`은 빈 상태(시드는 U4).
