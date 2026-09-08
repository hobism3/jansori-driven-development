# U3 Domain Entities — Capsule Normalizer Subagent (서브에이전트 관점 뷰)

> U1 도메인(Capsule/Version/Correction/RefsGraph/…)의 **재정의가 아님**. U3가 실행 중 다루는 개념적 작업 엔티티(주로 인메모리·수명 = 1회 정상화)를 정의한다. 영속 상태·원자성은 U1 소유.
> ⚠️ 정상화 = SPEC compaction ≠ Claude Code context compaction.

## E1 — CapsuleSnapshot (읽기 전용, GET 결과)
서버 `GET /skills/{id}` 응답을 서브에이전트가 취한 스냅샷. **유일한 콘텐츠 입력**(격리 BR-U3-01).
| 필드 | 설명 |
|---|---|
| skill_id | 대상 skill 식별자 |
| base_version | 이 스냅샷의 version (제출 시 base_version으로 사용, I-04) |
| body | 현재 본문 |
| corrections[] | 누적 교정(seq 순): {id, instruction_text, seq} — 병합 대상(BR-U3-04) |
| refs_children[] | depth-1 자식 참조 집합(병합 시 body에서 삭제 금지) |
| assets[] | 자산 참조 집합(삭제 금지) |

- 트랜스크립트·프롬프트·작업 소스는 **포함되지 않으며 요청하지도 않음**(§5).

## E2 — MergePlan (작업용, 휘발성)
병합 1회 시도의 산출 초안.
| 필드 | 설명 |
|---|---|
| new_body | 병합 결과 본문(BR-U3-05 보존 규약 충족 목표) |
| merged_correction_ids[] | 이번에 병합한 correction id 목록 — **U1 제출·검증·정리의 계약 필드**(재설계 2026-09-08) |
| attempt | 병합 재시도 카운터 (<= MAX_MERGE=3, BR-U3-07) |
| self_gate_ok | 제출 전 셀프 보존 점검 통과 여부(BR-U3-06) |

## E3 — NormalizationSubmission (POST 페이로드)
서버 `POST /skills/{id}/normalize` 로 보내는 값. **U1 현행 계약과 정확히 일치**(재설계 2026-09-08 반영).
| 필드 | 설명 |
|---|---|
| skill_id | 대상 (URL path 파라미터) |
| base_version | E1.base_version (stale 판정 기준, I-04) — body |
| new_body | E2.new_body (축약·의역 가능) — body |
| merged_correction_ids[] | 병합 선언 id 목록(비어있지 않음, ⊆ base) — body. **U1 검증·정리 기준(BR-U3-05)** |
| request_id | attempt_id (시도마다 새로, BR-U3-09) — body |

## E4 — NormalizationOutcome (POST 결과 분기)
| 값 | 의미 | U3 반응 |
|---|---|---|
| COMMITTED{new_version} | 커밋 성공 | 종료(콜백 없음) |
| STALE_BASE_VERSION | 그 사이 version 상승 | 재시작(BR-U3-08, <=3) |
| OVER_LENGTH | new_body 과길이 | 재병합(BR-U3-07) |
| PRESERVATION_FAILED | U1 보존 검증 실패 | 재병합(BR-U3-07) |
| SERVER_ERROR / 네트워크 | 서버 장애 | 동일 id 제한 재전송 → 초과 시 포기 |
| SKILL_ABSENT | (GET 단계) skill 없음 | 포기(무변경) |

## E5 — AttemptLog (진단/증거, F-04)
| 필드 | 설명 |
|---|---|
| skill_id, base_version | 대상·기준 |
| stage | GET / MERGE / SELF_GATE / SUBMIT / RESTART |
| outcome | E4 값 또는 self-gate FAIL |
| merge_attempts, restarts | 카운터 |
| final | COMMITTED 또는 ABANDONED(무변경, 사유) |

- 미완을 완료로 표기하지 않음(BR-U3-10). 실기동 증거는 U4 `make verify`/transcript.

## 관계 (텍스트)
```
LAUNCH(skill_id)
   -> E1 CapsuleSnapshot (GET)
   -> E2 MergePlan (E1.body + E1.corrections, 보존 규약)
   -> E3 NormalizationSubmission (POST)
   -> E4 NormalizationOutcome
        COMMITTED  -> 종료
        STALE      -> E1 재취득(<=3)
        OVER/PRESERVATION -> E2 재생성(<=3)
   (전 과정 E5 AttemptLog 기록)
```

- **영속 엔티티는 없음**: E1~E5는 정상화 1회 수명. Capsule/Version/Correction의 실제 상태·원자 커밋은 U1 소유(단일 진실원).
