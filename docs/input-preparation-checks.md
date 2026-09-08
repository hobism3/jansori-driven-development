# 사전 입력 자료 확인 결과 — 이번 보강판

이 기록은 명세 복사본·fixture·샘플 검사기를 확인한 것이다.
실제 Jansori 서비스의 `make verify`나 실제 Plugin 시연을 수행한 기록이 아니다.
재실행 명령과 검사 한계는 `sample-verification.md`에 있다.

## 실제 확인한 범위

| 대상 | 결과 |
|---|---|
| SPEC.md | 별도 첨부 SPEC (2)(1).md와 byte/hash 동일. ZIP 내부 SPEC은 미사용 |
| docs/spec-reference.md | 사용자의 최신 (3).zip 파일과 byte/hash 동일 |
| 개발 수용 사례 46개 | JSON/ID 중복/참조 범위 확인. R-01~14와 I-01~15 참조 포함 |
| seed 세 개 | 초기 v1·빈 corrections·runtime 상태 없음·직접 자식 깊이 1단계 |
| 수치 golden | 기존 W-01~36/오류 5건 보존, W-37~42 추가. 공개 연산식과 독립 대조 |
| B의 NR | GCC/Clang 각각 정상 42건·오류 5건, 전체 640×360 실행 |
| C의 영상 계약 | GCC/Clang 각각 DoProcess와 DoRun에 정상 42건·오류 5건씩, 전체 영상 실행 |
| GCC/Clang 전체 영상 | B/C 각각 출력 byte 동일 |
| C 상태 starter | 고정 probe 24단계 실행. 목표와 다른 16개 관측은 의도된 미완성 상태와 일치 |
| 정책 보조 입력 | 두 컴파일러에서 top_accepted=false / 100→100 / RGBP 264 |
| C 작업물 준비 | 허용 목록으로 C0/C1/C2 복사, 상대경로별 hash 동일, 알려진 접두사 정답 문자열 없음 |
| 평가기 검출력 | GCC 임시 정상 대조군 통과, 기존 검사에서 놓치던 오류 4종은 새 검사에서 모두 실패 |
| 평가기 고정 | 임시 정상 후보의 runner/probe가 컴파일 불가능해도 평가자 보관 도구로 정상 검사 |

## C 상태 과제는 완료하지 않음

원본 IsReady는 false, GetFrameCount는 0을 반환하고 Reset은 빈 구현이다.
새 관측에서도 모든 상태가 초기값으로 남아 목표 상태와 16개 사건에서 다르다.
이는 C가 실제로 구현할 과제를 남긴 것이다. 영상 계산 정상과 상태 기능 미완성을 구분한다.
입력 검사기의 `PASS_INPUT_CHECKS_ONLY`/`EXPECTED_INCOMPLETE`를 C 후보의 완료로 표시하지 않는다.

## 기록의 출처와 한계

`../PREPARATION-CHECKS.json`: 이번 원본 입력의 실제 컴파일·명령·관측·hash 기록.
`../EVALUATOR-REGRESSION-CHECKS.json`: 합성 정상/오류 후보를 이용한 평가기 구분 능력 확인.
정상·오류 후보의 C++ 소스는 패키지에 포함하지 않았으며 실제 Claude 작업물로 취급하지 않는다.
`../SOURCE-PROVENANCE.json`: 제공 ZIP, 별도 명세, 보존한 파일의 출처와 hash.
`../INPUT-MANIFEST.json`: 자기 자신을 제외한 배포 파일의 최종 SHA-256.

정답 문자열 검사는 알려진 정확한 문자열에 한정되며 OS 샌드박스·실제 세션 격리 증명이 아니다.
기능 검사 성공은 private 선언 적합성, 실제 Capsule Read, 교정의 인과 효과, 속도 개선을 증명하지 않는다.

## 수행하지 않은 것

실제 제품 서버/Hook/Skill, A 생성, B nag, C0/C1/C2 실제 세션, compaction,
사람의 AI-DLC 승인, 영상/설명물 제작 및 이해도 확인은 **NOT RUN**이다.
서비스 미구현과 입력 준비 검사를 구분하며, 전사 양식은 실제 수행 전의 NOT RUN 상태를 유지한다.
