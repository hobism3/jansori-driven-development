# 이전 입력 묶음의 명세 정렬 이력

아래는 기존 입력 묶음에 있던 **예제 자료의 명세 정렬 이력**이다.
이번 `(3).zip` 보강 내역은 `../SAMPLE-IMPROVEMENTS.md`에 따로 기록했다.
현재 SPEC.md는 별도 첨부 `SPEC (2)(1).md`를 byte 그대로 치환한 문서이며, docs/spec-reference.md는 `(3).zip`에서 유지했다.

| 이전 예제의 전제 | 이번 반영 | 새 근거 |
|---|---|---|
| 옛 SPEC §18, AI-DLC 고정 버전/Stage/3 Unit 인용 | 삭제. 팀 워크플로우와 새 §8 결정 순서 사용 | SPEC §8 |
| reference JSON/API를 사실상 고정 응답으로 사용 | 모든 사례를 동작/기대값으로 표현. schema/header/status는 팀이 확정 | SPEC §0·§8, reference 서두 |
| Capsule 내부 compaction_pending | seed 내용에서 제거. 별도 상태 사례로 관리 | I-01/I-10, §4B |
| compaction은 같은 version에 덮어쓰기 | 성공 시 새 version, 과거 내용 보존 | I-01, §4B |
| 소비자 폴링 상한 뒤 미정리본 사용 | 현재 body+corrections로 즉시 소비. 정리 완료 대기 없음 | I-10 |
| 긴 렌더링은 오래된 corrections부터 생략 | 등록/nag/PATCH 입구에서 거부·기존 지침 보존·분리 안내 | I-09, §4B |
| 잔소리는 매번 대상 확인 1회 필수 | 명확한 대상/공유 요청은 반영, 추론/추가 확인 필요한 요청만 확인 | §3, I-13 |
| 승인 플래그만으로 보호 변경 반영 | 승인 + 최신성, 오래된 변경안은 최신 내용을 덮지 못함 | I-04/I-14 |
| 24시간/60초/10,000자/특정 token/HTTP 코드 고정 | 새 §8 미정 항목으로 유지 | §8 |
| body의 경로/이메일 문자열 무조건 거부 | 실제 저장 경로와 내용 검사를 구분, 자동 수집·스크립트 경계 포함 | §5 |
| B와 다른 C 한 번의 결과만 비교 | 동일 C 초기 파일/요청을 C0/C1/C2 세 상태로 비교 | §7 |
| 정리 영상은 별도 선택 사항 | 승인된 제외가 아니면 실제 compaction+세 상태 유지 | §7·§10 |
| C++ 영상·시간만 주요 결과 | ready boolean/일반 frame_count 상태 과제 추가, 기존 규칙 보존도 비교 | §7 예시와 이번 golden 선택 |
| 설명 자료는 선택적인 후속 작업 | README·영상·HTML/PPT·5분 이해도 확인을 초기 계획에 포함 | §10~§12 |
| demo-prepare/demo-check 추가 타깃을 요구 | 새 필수로 강제하지 않음. 복사/빌드 예시와 결과 조건 제공 | §9·§12 |

## 유지한 것

부모 C-model 개발 / 자식 리팩토링·Code Rule 분류, B/C의 서로 다른 영상 업무,
독립적 시험 자료, 원본 NR/Local Contrast 영상 연산, 입력 PPM, 기존 수치 golden, Top/child 정책 보조 사례.
이번 보강에서는 원래의 수치 사례는 유지하면서 W-37~42와 상태 관측을 추가했다.
실제 회사 규정이나 제품 레지스터 사양은 추가로 만들어 넣지 않았다.

## 실제 CPP 변경

`C/local_contrast.cpp`의 영상 연산은 유지하고 LocalContrastModel의 미완성 관리 API를 추가했다.
`C/local_contrast_model.hpp`, `C/session_probe.cpp`, `C/TASK.md`를 추가했다.
기존 private m_parameters를 유지하고 ready/frame_count 실제 구현은 C가 작성한다.
정답 접두사나 최적화 해법은 C의 공개 파일에 넣지 않았다.
공통 WORKLOAD-SPEC에서 free function의 무상태성과 새 객체 상태 과제를 분리했다.

## 충돌 처리 원칙

이전 초기 입력 ZIP의 문서와 새 묶음을 섞지 않는다. 제품 명세는 최신 두 첨부 문서가 기준이다.
spec-reference의 cmodel-naming 예시를 확정 도메인 분류로 바꾸지 않았다.
새 §8이 의도적으로 열어 둔 빈칸에 예전 명세의 계약을 조용히 복원하지 않는다.
