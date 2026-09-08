# 예제 도메인 규칙과 세 상태 기대값

상태: **팀 검토용 예제 데이터**. 실제 사내 정책이나 실제 IP 사양이라고 주장하지 않는다.
제품 기준은 SPEC.md. 형식 예시는 spec-reference.md. 이 문서는 실제 시연에서 쓸 규칙을 제안한다.

## Capsule 분류와 초기 데이터

```
cmodel-development   C-model 개발
├── cmodel-refactoring   리팩토링
└── cmodel-code-rule     Code Rule
```

부모는 대상 명세와 적용 범위를 확인하고 필요한 자식을 읽도록 안내한다.
자식은 독립적인 교정 대상이며 NR/RGBP/BYRP는 규칙의 분류가 아니라 업무 대상이다.
자동 상속/모순 탐지 엔진을 추가하지 않는다. 새 세션은 부모 하나와 직접 자식만 활성화한다.
seed 세 개는 v1, corrections와 assets는 비어 있다. schema/생성 시각 필드는 최종 §8 계약으로 매핑한다.
고정 created_at은 예제 표시이며 실제 사용자 활동 시각이 아니다. 진행 상태를 내용 JSON에 넣지 않았다.

## 교정 전 유지할 규칙

Code Rule 초기 본문에는 직접 작성하는 클래스의 모든 private 데이터 멤버가 m_ 접두사를 쓴다고 명시한다.
정해진 논리 이름에 접두사를 붙이고 불필요한 접미사를 추가하지 않는다.
함수는 동작을 나타내는 동사로 시작하며, 공개/외부 고정 API는 이름을 유지한다.
제공된 기능·오류 계약과 실제 제품 사양을 추정하지 않는 원칙도 유지한다.

이 규칙 덕분에 C0의 private boolean ready는 m_ready, 일반 frame_count는 m_frame_count가 기대값이다.
C의 초기 코드에는 아직 ready/frame_count 데이터 멤버가 없고 m_parameters만 있다.
기존 m_parameters가 있다는 것이 새 boolean의 is_ 예외를 알려주지는 않는다.

## B가 실제로 입력할 교정

| 사건 | 대상 | 효과 | 예상 버전 |
|---|---|---|---|
| Ref 교정 | cmodel-refactoring | 영상 결과 유지, 중복 합산 검토, 실제 시간 비교 | Ref 1→2 |
| Code 교정 1 | cmodel-code-rule | private boolean만 is_ 예외, 일반 m_ 유지 | Code 1→2 |
| Code 교정 2 | cmodel-code-rule | 동사 시작 + 첫 글자 대문자 CamelCase, 고정 API/main 예외 | Code 2→3 |
| C1 비교 실행 | 쓰기 없음 | 교정 2건이라 시험 임계값 3 미만 | Code3/Ref2 |
| Code 교정 3 | cmodel-code-rule | 앞의 두 규칙을 의미 변경 없이 재명시한 새 사용자 잔소리 1건 | Code 3→4 |
| 정리 성공 | cmodel-code-rule | 유효 본문 통합, corrections 비움, 과거 v4 보존 | Code 4→5 |

원문은 prompts/demo/B-NAG-*.txt다. 잔소리 요청은 서로 다른 실제 사용자 이벤트다.
네트워크 재시도로 같은 이벤트를 중복 append하지 않는다.
Code 교정 3은 생략하거나 내용을 바꾸지 않는다. 이 교정이 새 유효 조건을 추가하면 C1/C2 의미 비교가 달라진다.
내용이 동일한 의도를 재강조하는 새 요청과 같은 request_id 재전송은 다르다. 의미 중복 완전 차단은 범위 밖이다.

## C0/C1/C2 — 같은 기능, 같은 요청, 같은 초기 코드

| 항목 | C0: 교정 전 | C1: 교정 후·정리 전 | C2: 정리 후 |
|---|---|---|---|
| 부모 | v1 | v1 | v1 |
| 리팩토링 | v1 | v2 | v2 |
| Code Rule | v1 | v3 | v5 |
| Code corrections 개수 | 0 | 2 | 0 |
| 새 private bool ready | m_ready | is_ready | is_ready |
| 새 private 일반 frame_count | m_frame_count | m_frame_count | m_frame_count |
| 기존 private 파라미터 | m_parameters 보존 | 보존 | 보존 |
| 공개 상태 기능 | lifecycle-golden 충족 | 동일 | 동일 |
| 영상 출력 | workload-golden 충족 | 동일 | 동일 |

숫자는 깨끗한 v1 시작 + 표의 내용 변경만 있었을 때다.
추가 nag/metadata 변경/중복 시연을 했다면 실제 version을 기록하고 사건표를 갱신한다.
원하는 숫자를 맞추려고 과거본을 수정하거나 최신 포인터를 임의로 되돌리지 않는다.
단순 진행 상태 변화만으로 content version이 바뀌어서는 안 된다.

## 평가자 자료와 공개 업무 명세

평가자 전용: 이 문서, SPEC/reference, prompts의 교정, three-state-golden, lifecycle-golden, workload-golden.
C에게 줄 것: 자기 CPP/헤더/session_probe, common 코드·수치 기능 명세, 입력 PPM, 중립적인 TASK.
TASK는 logical ready/frame_count와 상태 동작만 설명한다. m_ready/is_ready/m_frame_count 정답은 포함하지 않는다.
공개 API IsReady/GetFrameCount는 기능 계약이며 private 멤버 이름의 정답이 아니다.

C의 full frame 이미지는 소스 산출물 보존과 눈에 띄는 결과 제시에 사용한다.
다른 픽셀 0, 코드에서 교정된 멤버, 일반 멤버 보존, 실제 로드 내용이 함께 증거가 된다.
시간은 같은 조건에서 측정하되 특정 배율을 약속하지 않는다. 서버 성능 최적화와 구별한다.

## 기존 Top/child 요구의 보조 사례

policy/legacy_policy.cpp와 CASE.md를 유지했다. 누락 GetAttribute 등록·SetAttribute 전달,
protected virtual 초기화/base 재사용·함수명을 확인하는 작은 업무다.
CASE.md는 답을 포함하므로 C의 clean 환경에 넣지 않는다.
이 보조 사례를 시행하면 당시 실제 추가 교정/버전을 기록한다. 핵심 세 상태 비교를 대체하지 않는다.
