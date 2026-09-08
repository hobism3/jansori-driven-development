# U1 Code Summary — Domain Layer

> 코드: `server/domain/`. 기술 중립 도메인 핵심. 테스트: `tests/unit/u1/test_domain.py`(전부 통과).

## 파일
| 파일 | 내용 |
|---|---|
| `models.py` | Capsule(집합체 루트, frozen dataclass — copy-on-write), Version(불변 스냅샷 I-01), Correction(target/seq/request_id, Q3/I-05/I-13), Asset, Session(진행 플래그 분리 I-10), IndexEntry. `PROTECTED_FIELDS` 고정집합(Q9/I-14). |
| `refs.py` | `assert_depth_one` — depth-1 검사(I-15), 손자/자기참조 거부 + 위반 경로·권고. 등록·refs 변경 공통. |
| `limits.py` | `Limits`(max_content_length=10,000 L, normalization_threshold=3), 환경변수 override. |
| `errors.py` | `ErrorCode` enum + `DomainError` 계층(구조화 오류 D-03). SERVER_ERROR↔SKILL_ABSENT 별개(I-07). |

## 불변식 반영
- **I-01**: Capsule frozen; `with_new_content()`는 version+1의 새 객체 반환, 과거 스냅샷 불변.
- **I-15**: `assert_depth_one`가 자식의 자식 존재 시 `DepthLimit`.
- **I-14/Q9**: `PROTECTED_FIELDS = (skill_id, name, refs_children, protected_fields)`.
- **D-03**: 8개 오류 코드 + VALIDATION/NEEDS_CONFIRMATION.

## 설계 노트
- version = 단조 증가 정수(Q1=A). body = 단일 문자열(Q2=A), corrections는 별도 tuple로 보관.
- Capsule은 불변 → 저장소가 포인터를 원자 스왑(I-12는 store 담당).
