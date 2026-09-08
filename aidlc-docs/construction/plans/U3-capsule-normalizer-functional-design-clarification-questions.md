# U3 Functional Design — Clarification (Q2=C vs CLOSED U1 계약 충돌)

`[Answer]:` 태그에 문자로 답해 주세요. 이 한 건만 해소되면 나머지(Q1·Q3~Q11=A)로 U3 산출물 생성에 바로 들어갑니다.

## 감지된 충돌
**Q2=C**("병합 correction id 목록을 메타데이터로 제출 + 본문 자연 통합, U1은 id 선언·길이·집합만 검증")는 이미 **CLOSED된 U1**의 실제 구현과 어긋납니다.

- U1 `server/services/normalization_service.py`:
  - `commit_normalization(skill_id, base_version, new_body, request_id)` — **`merged_correction_ids` 파라미터 없음**.
  - `validate_preservation` (line 40–47): **각 correction의 `instruction_text`가 `new_body`에 정규화 부분문자열로 존재**해야 통과. (공백 축약·소문자화 후 substring 검사)
- 즉 U1은 지금 "본문에 지시 문구가 실제로 남아 있어야" 통과시키며, id 선언 방식은 지원하지 않습니다.
- Q2=C의 "본문 자연 통합(문구 앵커 없음)"은 이 substring 검사를 통과하지 못해 `PRESERVATION_FAILED`가 납니다.

참고: U1의 이 방식은 원래 Q2 보기 중 **A**("앵커/정규화 규약으로 본문 추적")에 해당합니다. U1 Functional Design 승인(Q8=A) 시 채택된 규약입니다.

## Clarification Question 1
이 충돌을 어떻게 해소할까요?

A) **U1 유지 · U3를 U1 현행 규약(부분문자열 보존)에 맞춤** — 서브에이전트가 병합 시 각 correction의 지시 문구를 `new_body`에 (정규화 기준) 보존하도록 병합. U1 코드/계약 변경 없음. 실질적으로 Q2를 **A**로 확정. (권장 · CLOSED 유닛 불변, 검증 결정성 유지)

B) **U1을 다시 열어 Q2=C 채택** — `POST /skills/{id}/normalize`에 `merged_correction_ids` 추가, `validate_preservation`를 "선언된 id가 base corrections와 일치 + 길이/집합(refs·assets) 보존"으로 교체, U1 코드·테스트·contract-decisions 수정 후 회귀 테스트 재실행. (CLOSED U1 재작업 + 재승인 필요; 병합 문구 자유도↑, 검증 엄격도↓)

C) **하이브리드** — U3가 `merged_correction_ids`를 메타데이터로 함께 보내되(문서·증거용), 본문에는 여전히 U1의 부분문자열 규약을 만족시키도록 지시 문구를 보존. U1 검증 로직은 현행 유지(메타데이터는 참고용). (U1 검증 로직 무변경, 필드만 선택 추가 가능)

X) Other (아래 [Answer]: 태그 뒤에 설명)

[Answer]: A
