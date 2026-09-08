# AI-DLC 초기 전달용 입력 — 샘플 검증 보강판

**서비스 완제품이 아니라, 개발 시작 전에 주는 명세·시험 데이터·시연 원본 코드입니다.**
이번 패키지는 사용자의 최신 `(3).zip`을 바탕으로 샘플의 검증 빈틈을 보완했습니다.
ZIP 내부의 이전 SPEC은 사용하지 않고, 별도 첨부 `SPEC (2)(1).md`를 `SPEC.md`로 byte 그대로 치환했습니다.
`docs/spec-reference.md`는 최신 ZIP의 내용을 유지했습니다. 옛 패키지와 섞지 말고 이 묶음으로 교체하세요.
변경 내용과 원문 안의 I-15 교차참조 주의사항은 `SAMPLE-IMPROVEMENTS.md`에 있습니다.

## 1. 개발 시작 시 한 번 전달

1. 이 폴더의 내용을 해커톤 프로젝트 루트에 둡니다.
2. 팀이 준비한 AI-DLC가 활성화된 Claude Code를 프로젝트 루트에서 엽니다.
3. **`prompts/START-AI-DLC-SHORT.txt`를 최초 사용자 메시지로 입력합니다.** 전체 지시를 직접 붙여 넣으려면 `prompts/START-AI-DLC.txt`를 사용합니다. 둘을 연속 입력할 필요는 없습니다.
4. 이후에는 정상 워크플로우의 질문과 사람 승인에 응답합니다. 중간에 별도 mock/adapter를 주입하지 않습니다.

새 SPEC에는 AI-DLC 버전·Stage 개수·Unit 개수가 고정되어 있지 않습니다.
이 패키지도 과거 문서의 버전 고정이나 Stage 계획을 새 명세의 요구라고 가져오지 않습니다.
팀이 설치한 워크플로우를 사용하며, 설치 명령이나 존재하지 않는 전용 slash 명령을 가정하지 않습니다.

## 2. 처음부터 함께 줄 자료

| 파일 | 역할 |
|---|---|
| `SPEC.md` | 제품 의도·I-01~15·채택 기준선·R-01~14·F-01~07·필수 제출물 |
| `docs/spec-reference.md` | 자료 형식 예시. 확정 스키마/API가 아님 |
| `docs/initial-requirements-addendum.md` | 제공 자료의 경계와 팀이 검토할 예제 업무 선택 |
| `docs/contract-decisions.md` | SPEC §8에서 확정할 항목과 검증 연결 |
| `docs/development-test-plan.md` | 시험 사례를 처음부터 구현·검증 계획에 넣는 방법 |
| `fixtures/acceptance/development-cases.json` | 46개 입력·이벤트·기대 결과 사례. 서비스 테스트 구현은 아님 |
| `docs/golden-data.md`, `fixtures/seed/` | 부모 C-model 개발 / 자식 리팩토링·Code Rule의 예제 규칙 |
| `docs/demo-scenario.md`, `prompts/demo/` | 개발 완료 후 A 증거 + B 교정 + C 세 상태 실제 실행 대본 |
| `fixtures/workloads/` | 기존 영상 CPP, C의 미완성 상태 기능, 입력 PPM, 중립적 기능 명세 |
| `fixtures/acceptance/*golden.json` | 평가자 전용 수치·상태·멤버명 기대값. C 환경에는 제외 |
| `docs/explanation-brief.md` | SPEC §12 설명용 HTML/PPT·영상·이해도 확인의 제작 입력 |
| `docs/demo-transcript.md` | 실제 실행 뒤 채울 빈 전사 양식. 현재 NOT RUN |
| `docs/sample-verification.md`, `tools/verify_sample.py` | 샘플 입력·후보의 고정 평가기. 제품 `make verify`와 별개 |
| `SAMPLE-IMPROVEMENTS.md` | 이번 보완 범위, 보존한 원본, 원문 교차참조 주의사항 |

## 3. 개발과 시연을 혼동하지 않기

**개발 Claude Code**는 전체 자료를 보고 Jansori와 실제 구현에 연결된 테스트를 만듭니다.
제공된 workload CPP를 서비스 코드로 취급하거나 개발 중 최적화 정답으로 바꾸지 않습니다.
**시연 Claude Code**는 완성된 Plugin을 켠 별도 B/C 작업 공간에서 그 복사본만 수정합니다.
C는 개발 대화나 B의 대화를 이어받지 않습니다. C0/C1/C2끼리도 각각 새 세션입니다.

이 패키지에는 server/, plugin/, mock Store, HTTP 어댑터, 최적화 정답, Makefile,
완성된 AI-DLC Stage 결과물이나 승인 기록이 없습니다.
C++ runner·session_probe와 Python `tools/verify_sample.py`는 사전 제작 업무를 검사하는 도구이며 Jansori 구현이 아닙니다.
후보의 반환 이미지·비기본 파라미터 Reset·객체 간 상태 독립성을 고정 평가기로 확인합니다.
private 멤버명/실제 Capsule Read/전파 성공은 여전히 코드 검토와 실제 전사로 따로 판정합니다.

## 4. 개발 완료 후 사용하는 명령

팀이 SPEC §12에 따라 **구현한 프로젝트**에서 실행합니다.
이 초기 입력 패키지에 아래 Make 타깃이 구현되어 있다는 뜻이 아닙니다.

```bash
# 터미널 1: 실제 제품 서버
make run
# 터미널 2: 실제 구현 검증, 그리고 영상 시연용 데이터 등록
make verify
make seed
```

make verify는 실제 서버를 테스트 안에서 기동·종료하고 자격증명 없이 기계적 계약을 검사해야 합니다.
make seed는 특정 ID를 하드코딩하지 않는 범용 등록입니다. 승인된 자동화 축소는 수동 절차로 대체합니다.
API·설정·Plugin 활성화 명령은 §8 설계 결과를 완성된 프로젝트 README에 기록해야 합니다.
초기 문서가 미정 endpoint나 포트를 대신 확정하지 않습니다.

과거 제안한 `make demo-prepare/demo-check`를 이번 새 SPEC의 필수 명령으로 강제하지 않았습니다.
작업 폴더 준비·업무 검증의 결과 조건은 유지하며, 실제 자동화 명령은 팀 설계에서 정합니다.
지금도 사용할 수 있는 파일 복사·CPP 빌드 명령은 `docs/demo-scenario.md`에 있습니다.

## 5. 실제 시연 순서

```
A: 관련 스킬 없는 정상 서버에서 완료 → 제안 → 실제 동의 → 재검색 → 생성 (별도 증거)

영상용 깨끗한 seed와 시험 compaction 임계값 3:
C0: 새 세션 + C 원본 + C-START 요청 / 교정 전
B : 새 세션 + NR 원본 → Ref 잔소리 1회 → Code 잔소리 1·2
C1: 새 세션 + 같은 C 원본 + 같은 C-START 요청 / 교정 후·정리 전
B : Code 잔소리 3(앞선 규칙 재명시) → 실제 백그라운드 compaction
C2: 새 세션 + 같은 C 원본 + 같은 C-START 요청 / 정리 후
```

구체적인 순서·복사 허용 목록·파일 경로·관측값은 **`docs/demo-scenario.md`**를 그대로 사용하세요.
B와 C를 서로 비교하는 것만으로는 부족합니다. 동일 C 입력을 세 상태에서 비교하는 것이 추가되었습니다.

## 6. 무엇이 달라지는지 화면에 보이는 항목

| C 작업 | 교정 전 C0 기대 | 교정 후 C1 기대 | 정리 후 C2 기대 |
|---|---|---|---|
| 새 private boolean ready 멤버 | m_ready | is_ready | is_ready 유지 |
| 새 일반 frame_count 멤버 | m_frame_count | m_frame_count 유지 | m_frame_count 유지 |
| 기존 파라미터 멤버 | m_parameters 유지 | 유지 | 유지 |
| 상태 기능과 영상 출력 | 공개 기능 계약 충족 | 같은 계약 충족 | 같은 계약 충족 |

위 멤버명은 **평가자 전용 기대값**입니다. C의 공개 TASK에는 논리 이름과 동작만 있고 접두사 정답은 없습니다.
멤버명 자체가 맞았다고 전파 성공은 아닙니다. 실제 자식 Read·version·교정·작업 결과를 함께 기록합니다.
이미지·실측 시간 비교도 유지하되 속도 배율을 미리 정하거나 제품 서버 성능 최적화 요구로 확대하지 않습니다.

## 7. 지금 확인된 것 / 확인되지 않은 것

`PREPARATION-CHECKS.json`은 이번 패키지의 실제 샘플 검사 결과입니다. 정상 영상 42건·오류 5건을 검사하며,
C는 free DoProcess뿐 아니라 DoRun의 반환 영상도 같은 기대값과 비교합니다. 상태 관측은 24단계입니다.
`EVALUATOR-REGRESSION-CHECKS.json`은 임시 오류 후보를 새 검사기가 걸러냈는지 확인한 기록입니다.
정답 후보 소스나 최적화 구현은 패키지에 넣지 않았습니다.
C의 상태 기능은 시연 에이전트가 작성할 과제여서 현재 starter는 그 기능 검증을 만족하지 않습니다.
실제 서비스·Plugin·A/B/C 전사·설명 이해도 확인은 **NOT RUN**입니다.
문서를 만들었다는 사실을 서비스 검증이나 사람 승인으로 바꾸지 않습니다.
