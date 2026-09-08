# 실제 서비스 시연 — 같은 C 원본으로 교정 전/후/정리 후 비교

**상태: 계획·발화 예시, 실제 실행 전사 아님.** 개발 시작 때 이 대본을 전달한다.
개발 완료 후 실제 Plugin·로컬 단일 서버로 수행한다. 실제 관측은 demo-transcript.md에 남긴다.
형식 예시나 사전 expected JSON을 보여주는 것만으로 서버/사용자 실행을 대체하지 않는다.

## 0. 핵심 구조

B의 NR 업무와 C의 Local Contrast 업무는 다르다. 그러나 C0/C1/C2끼리는
**같은 원본 코드·같은 기능 요청·같은 입력**을 사용한다. 이것이 SPEC §7의 세 상태 비교다.

```
A 경로: 정상 빈 인덱스 → 업무 완료 → 제안 → 실제 수락 → 재검색 → 생성/등록

별도 깨끗한 영상용 데이터:
C0(교정 전) → B 교정들 → C1(교정 후·정리 전) → B 재명시 nag/정리 → C2(정리 후)
```

A/B/C는 계정/인증 역할이 아니라 분리된 실제 세션 이름이다.
전사 실행 전체를 영상에 길게 넣을 필요는 없지만 필수 증거의 위치를 안내한다.
세 상태는 촬영 결과에 불리하다고 임의로 생략하지 않는다. compaction이 승인된 제외일 때만
관련 요구/I/F/수용 기준을 함께 갱신하고 세 번째 상태도 승인된 제외로 표시한다.

## 1. 개발 완료 뒤 운영자가 준비하는 것

실제 프로젝트 README에서 설치·서버 데이터 위치·임계값 설정·Plugin 활성화 절차를 확인한다.
이들은 SPEC §8에서 정할 것이므로 아직 존재하지 않는 환경 변수나 slash 명령을 여기서 발명하지 않는다.
make run/verify/seed는 팀의 실제 구현 산출물이다. 이 초기 입력 ZIP에서 바로 실행되는 타깃이 아니다.

```bash
# 실제 완성된 프로젝트: 터미널 1
make run
# 별도 터미널
make verify
```

A는 관련 스킬이 없는 정상 서버 상태에서 별도로 검증한다. 연결 장애를 '관련 스킬 없음'으로 쓰지 않는다.
A 검증 후 영상 비교용으로 깨끗한 별도 데이터 디렉터리를 사용하는 재현 절차를 README대로 수행한다.
한 번에 로컬 서버 한 인스턴스만 운영한다. 삭제/초기화 API를 새로 만드는 요구가 아니다.
이미 같은 ID가 있으면 무단 덮어쓰지 않는다. 실제 데이터 준비 과정을 기록한다.

영상 비교용 데이터에는 다음을 수행한다.

```bash
make seed
```

시험 임계값은 **3**으로 설정하고 실제 적용값을 기록한다. 기본값 10을 제품에서 바꾸라는 뜻은 아니다.
seed는 초기 세 v1만 등록하고 v2/v3/v5 정답 상태를 직접 넣지 않는다.

## 2. 지금 제공된 파일로 작업 공간 분리 — 복사 명령

B/C 에이전트는 전체 개발 저장소에서 시작하지 않는다. 아래 일반 shell 명령은 서버 구현 없이도 실행 가능하다.
기존 출력 폴더가 있으면 중단한다. 셸 변수 ROOT는 이 초기 자료가 들어 있는 프로젝트 루트다.

```bash
set -eu
ROOT="$PWD"
DEMO_ROOT="$(dirname "$ROOT")/jansori-demo-spec-run"
test ! -e "$DEMO_ROOT" || { echo "이미 있는 폴더입니다. 새 출력 경로를 선택하세요."; exit 1; }
mkdir -p "$DEMO_ROOT/b/src" "$DEMO_ROOT/b/common"
cp "$ROOT/fixtures/workloads/B/noise_reduction.cpp" "$DEMO_ROOT/b/src/"
cp "$ROOT/fixtures/workloads/B/input.ppm" "$DEMO_ROOT/b/input.ppm"
for FILE in WORKLOAD-SPEC.md cmodel.hpp runner.cpp; do
  cp "$ROOT/fixtures/workloads/common/$FILE" "$DEMO_ROOT/b/common/"
done
for RUN in c0 c1 c2; do
  mkdir -p "$DEMO_ROOT/$RUN/src" "$DEMO_ROOT/$RUN/common"
  cp "$ROOT/fixtures/workloads/C/local_contrast.cpp" "$DEMO_ROOT/$RUN/src/"
  cp "$ROOT/fixtures/workloads/C/local_contrast_model.hpp" "$DEMO_ROOT/$RUN/src/"
  cp "$ROOT/fixtures/workloads/C/session_probe.cpp" "$DEMO_ROOT/$RUN/src/"
  cp "$ROOT/fixtures/workloads/C/TASK.md" "$DEMO_ROOT/$RUN/TASK.md"
  cp "$ROOT/fixtures/workloads/C/input.ppm" "$DEMO_ROOT/$RUN/input.ppm"
  for FILE in WORKLOAD-SPEC.md cmodel.hpp runner.cpp; do
    cp "$ROOT/fixtures/workloads/common/$FILE" "$DEMO_ROOT/$RUN/common/"
  done
done
```

허용 파일은 자기 CPP/헤더/중립 기능 명세/관측 runner/이미지뿐이다.
평가자는 시연 전에 이 패키지의 원본과 `INPUT-MANIFEST.json`을 C가 읽을 수 없는 위치에 보관한다.
`tools/`·golden·평가 보고서는 C에게 복사하지 않는다. 평가자 보관본을 고정 도구로 사용한다.
**금지:** SPEC/spec-reference, golden JSON/문서, 이 대본, 교정 프롬프트, B 수정본, 다른 C 결과.
논리 이름 ready/frame_count와 public API는 기능 명세에 있어도 되지만 m_ready/is_ready 정답은 없어야 한다.

파일 복사는 보안 샌드박스가 아니다. 에이전트의 읽기 범위도 해당 폴더로 제한하고,
부모 개발 폴더의 안내 파일·기존 대화·기억에 답이 섞이지 않았는지 확인한다.
B/C 각 세션을 열기 전에 normalized 상대경로별 파일 hash를 기록한다.
C0/C1/C2의 초기 파일·요청 hash가 다르면 비교를 시작하지 않는다.

## 3. A의 실제 생성 증거 — seed로 대체하지 않음

A는 별도 새 대화에서 원본 B NR와 common/·이미지 복사본을 사용한다. B가 수정한 소스가 아니다.
관련 스킬이 없는 정상 서버 상태에서 `prompts/demo/A-START.txt`를 운영자가 입력한다.

> 이 C-model 영상 코드를 실행하고 입력·출력과 잘못된 입력 처리 여부를 확인해 줘.
> 다른 개발자가 반복할 수 있는 빌드와 실행 절차도 정리해 줘.

관측: 정상 인덱스 → Claude의 관련 스킬 판단 → 실제 업무 완료 → 저장 제안.
제안이 있을 때 사람이 실제로 수락하거나 거절한다. 둘의 기대 분기를 개발 테스트에 포함한다.
수락 시 재검색과 생성·등록을 기록한다. Generator/파일 경로는 실제 §8 설계 결과를 따른다.
제안이 없는데 있었던 것처럼 쓰거나, 운영자가 먼저 저장을 강요한 것을 자동 제안 성공으로 표시하지 않는다.
아직 미완료인데 응답이 끝났다는 이유만으로 등록하면 실패다.

영상은 seed 기반으로 짧게 시작해도 된다. 단, A 증거 위치를 영상/README에서 안내한다.
A에서 만들어진 Capsule을 seed fixture 내용과 동일하다고 가정하지 않는다.

## 4. C0 — 교정 전 대조 실행

작업 폴더 `c0/`, 실제 Plugin을 활성화한 **새 대화**.
다음 한 파일을 그대로 입력한다. 이후 C1/C2에도 **동일한 파일**을 사용한다.

**입력: `prompts/demo/C-START.txt`**

> 이 Local Contrast C-model의 TASK.md에 적힌 준비 상태와 처리 횟수 기능을 구현하고
> 공통 개발 규칙에 맞게 코드를 정리해 줘. 작업 결과를 남겨줘.

이 발화에 접두사·시간 측정·정답 구현을 덧붙이지 않는다.
실제 모델이 부모 Skill을 호출하고 해당 자식 내용을 읽는지 기록한다.
기대 로드 상태는 Top1/Ref1/Code1이다. 실제 내용/버전을 기록하고, 맞추려고 결과를 고치지 않는다.
평가자 기대는 m_ready / m_frame_count / 기존 m_parameters 보존과 상태 기능·영상 계약 충족이다.

C0 결과를 보존하되 C1/C2 폴더에 복사하지 않는다.
C0가 새 스킬 저장을 제안하면 운영자는 저장하지 않겠다고 응답하고 실제 응답을 기록해
본 비교의 서버 상태에 추가 내용 변경이 생기지 않게 한다. 새 규칙을 알려주는 힌트는 주지 않는다.
승인하지 않은 저장이 발생하면 비교의 사전 조건 위반으로 기록한다.

## 5. B — 원본 NR 확인 후 교정 저장

작업 폴더 `b/`, 별도 실제 Plugin 대화. `prompts/demo/B-START.txt` 입력.

> 이 Noise Reduction C-model을 공통 개발 규칙에 맞게 정리하려고 해.
> 관련 스킬을 확인하고 기존 코드의 동작과 출력 이미지를 보여줘.
> 이 단계에서는 소스코드를 수정하지 마.

기존 영상 연산은 정상이다. Claude의 고의 실패가 아니라 사전 준비한 반복 계산 코드다.

### 5-1. 리팩토링 교정

기존 결과를 본 직후 **`prompts/demo/B-NAG-REFACTORING.txt`**를 입력한다.
내용: 중복 합산 검토, 출력·경계·반올림 유지, 입출력 제외 반복 실측, 실제 보고.
대상 cmodel-refactoring과 공유 의도가 명시된 요청이다. 명확하면 공통 nag 경로로 반영한다.
추가 추론/확인이 실제로 필요하면 질문에 응답한다. 매번 별도 확인을 성공 필수로 강제하지 않는다.

예상: Ref v1→v2. 부모/Code 내용 불변. 현재 NR 코드도 실제로 수정·검증하는지 본다.

### 5-2. Code 교정 1

**`prompts/demo/B-NAG-CODE-1.txt`** 입력.
내용: private boolean만 is_, 일반 m_ 유지, 고정 공개 API 유지.
예상: Code v1→v2. Ref v2/부모 v1은 바뀌지 않는다.
B 코드에 새 boolean이 없어도 공유 규칙 저장 요청은 명시되어 있다.
불필요한 멤버를 억지로 추가해 현재 코드의 적용 사례를 만들 필요는 없다.

### 5-3. Code 교정 2

**`prompts/demo/B-NAG-CODE-2.txt`** 입력.
내용: 직접 작성 함수는 동사 시작·첫 글자 대문자 CamelCase, main/고정 API 예외.
예상: Code v2→v3, corrections 2건. 현재 NR의 함수명에도 적용한다.
임계값은 3이므로 아직 정리를 시작하지 않는 것이 이 대본의 전제다.
여기서 세 번째 Code nag를 보내기 전에 C1을 실행한다.

## 6. C1 — 교정 후, 정리 전 대조 실행

작업 폴더 `c1/`, C0/B와 다른 **새 대화**.
C0와 동일한 `prompts/demo/C-START.txt`만 입력한다.
기대 실제 로드 상태: Top1/Ref2/Code3. 부모는 v1이어도 최신 자식 version을 받는다.

평가자 기대: is_ready / m_frame_count / m_parameters 보존, 함수 규칙과 고정 API 예외 적용,
상태·영상 계약 충족. C의 프롬프트나 폴더에서 잔소리를 전달하지 않는다.
실제 자식 파일에 body+corrections가 있고 모델이 읽었음을 기록한다.

C1의 자체 처리 시간 보고와 평가자의 독립 측정을 구분한다.
운영자가 나중에 시간을 쟀다는 사실만으로 Claude가 시간 보고 지침을 적용했다고 쓰지 않는다.
C1에서 추가 스킬 저장은 수락하지 않으며, 실제 요청/거절을 기록한다.

## 7. B의 세 번째 교정과 실제 compaction

이전 B 대화에서 **`prompts/demo/B-NAG-CODE-3.txt`**를 입력한다.
앞의 boolean 예외·일반 멤버·함수/고정 API 규칙을 **의미 변경 없이 재명시하는 새 잔소리 한 건**이다.
이후 Code v4, 교정 3건에서 실제 별도 서브에이전트 정리를 시작한다.
내용 version에는 pending을 끼워 넣지 않고 진행 상태를 별도로 관리한다.
성공하면 Code v5에 정리 본문/빈 corrections를 기록하고 v4 전체 내용을 보존한다.

사전 v5 본문을 seed로 넣거나 운영자가 직접 정리 결과로 PATCH한 것은 실제 정리 증거가 아니다.
실제 서브에이전트 입력·결과와 base_version 기반 반영을 기록한다.
정리 중 새 교정/오래된 결과 충돌은 DEV-15에서 자동으로 검증하며 결과를 따로 안내한다.

### C1을 v3에서 실행한 이유

빠른 정리를 억지로 멈춰 v4를 소비하게 하지 않기 위해 임계값 도달 전의 v3에서 C1을 실행한다.
그 다음 세 번째 교정은 새 유효 규칙을 추가하지 않는다. 실제 텍스트의 의미가 같았는지 전사에서 확인한다.
정확한 직전/직후 v4→v5 내용 경계는 DEV-14 자동 검증에서도 확인한다.
이 구조는 소비자에게 대기·폴링·재조회 기능을 추가하는 것이 아니다.
정리가 끝나지 않은 때 시작한 일반 소비자는 현재 body+corrections로 즉시 일한다(I-10).
C2는 운영자가 실제 정리 성공을 관측한 **이후 새로 시작하는 독립 실험 세션**이다.

정리가 실패하면 C2 성공으로 넘어가지 않는다. 실패·미검증 상태를 남긴다.
기능 축소는 SPEC §10의 실제 승인과 관련 기준 갱신 없이는 할 수 없다.

## 8. C2 — 정리 후 대조 실행

작업 폴더 `c2/`, 앞의 모든 대화와 다른 **새 대화**.
C0/C1과 동일한 `prompts/demo/C-START.txt`만 입력한다.
기대 로드: Top1/Ref2/Code5. 교정 배열은 비어 있지만 지침이 본문에 보존되어야 한다.

평가자 기대: is_ready / m_frame_count / m_parameters 및 기능 계약은 C1과 동일하다.
Code v4가 과거본으로 남아 있고 실제 로드가 v5였다는 근거를 함께 제시한다.
C0/C1/C2에서 실제 로드한 번호가 다르면 그 번호와 원인을 기록한다.
원하는 version 숫자로 보이도록 기록을 손으로 바꾸지 않는다.

## 9. 후보를 실행하는 현재 제공 명령

각 C 작업 폴더 안에서 다음 명령을 실행할 수 있다. 최적화 해법을 제공하는 명령이 아니다.

```bash
c++ -std=c++17 -O2 -Icommon -Isrc common/runner.cpp src/local_contrast.cpp -o workload
./workload input.ppm output.ppm
c++ -std=c++17 -O2 -Icommon -Isrc src/session_probe.cpp src/local_contrast.cpp -o session-probe
./session-probe
```

B는 common/runner.cpp와 src/noise_reduction.cpp를 같은 방식으로 빌드한다.
위 명령은 후보 작업 중 관측용이다. 최종 판정에는 후보 폴더의 runner/probe를 신뢰하지 않는다.
**세션을 종료하고 후보를 보존한 뒤 평가자 환경의 고정 패키지에서** 다음을 실행한다.

```bash
# 평가자 보관본 루트. 보고서는 C 폴더 밖에 저장한다.
python3 tools/verify_sample.py --mode candidate --candidate /absolute/path/to/c0 \
  --workload C --compiler c++ --report ../jansori-evaluation/c0.json
# c1/c2도 같은 방식으로 검사한다. B는 --workload B와 b 폴더를 사용한다.
```

도구는 후보 src를 임시 폴더에 복사하고 평가자 고정 runner/probe/API 헤더로 빌드한다.
42개 정상·5개 오류 입력에 대해 DoProcess와 DoRun을 검사하고, DoRun의 크기/모든 픽셀도 비교한다.
24개 관측으로 비기본 파라미터의 Reset 보존과 두 객체의 독립성까지 확인한다.
640×360 원본 영상 출력과도 별도로 비교한다. 정확한 사용법·한계는 `docs/sample-verification.md`를 따른다.
private 멤버 이름은 실제 클래스 소스/선언을 확인한다. 주석에 정답 단어만 있다고 통과시키지 않는다.
후보는 CPP뿐 아니라 수정된 local_contrast_model.hpp도 포함해 hash를 남긴다.
고정 평가기 hash·실행 명령·JSON 보고서·기대/실제 불일치도 전사에 연결한다.
검사 보고서를 받아 정답을 수정한 재실행은 최초 무힌트 결과와 구분한다.

영상 시간은 같은 호스트·컴파일러·옵션·입력·파라미터로 측정한다.
DoProcess 등 동등한 처리 범위를 반복 측정하고, 파일 읽기/쓰기·빌드·hash를 제외한다.
함수 내부 할당의 포함 여부와 원시 표본/중앙값/변동을 기록한다.
`time ./workload`는 파일 입출력을 포함하므로 위 처리 시간의 대체 증거로 쓰지 않는다.
현재 runner는 시간 비교 도구가 아니다. 팀의 실제 검증 도구/모델의 측정 코드를 검토해 사용한다.
출력이 다르거나 속도가 개선되지 않으면 그대로 보고한다. 사전 배율은 없다.

## 10. 영상·설명 화면의 순서

1. 문제: 여러 조직의 C-model 규칙이 통일되지 않아 같은 피드백이 반복된다.
2. B의 실제 잔소리 원문과 대상 자식·저장 version을 보여준다.
3. C0/C1/C2의 같은 기능 요청과 private 멤버 선언을 나란히 보여준다.
4. is_ready만 바뀌고 m_frame_count와 m_parameters는 유지되는 것을 보여준다.
5. 입력/출력 이미지·다른 픽셀 수·실측 시간, 실제 자식 Read·정리 증거 위치를 연결한다.

상태 표의 기대값과 실제값을 구분한다. 참고 예시 코드를 실제 Claude 결과처럼 편집하지 않는다.
설명용 HTML 또는 PPT를 최소 하나 제작한다. 제품 웹 UI 구현과는 별개다.
프로젝트 설명을 듣지 않은 참가자가 자료를 보고 5분 안에 핵심을 설명 가능한지 실제 관찰하고
시간·응답·혼동점을 demo-transcript에 남긴다. 자동 생성한 대답은 증거가 아니다.

## 11. 개입/실패 기록

- 명시적 /load로 복구한 경우 자율 선택 성공과 구분한다.
- C에게 교정을 다시 알려줬다면 무힌트 전파 비교가 아니라 개입 실행이다.
- C0/C1/C2 입력 파일이나 요청이 다르면 통제 비교 요건을 충족하지 않는다.
- 실제 로드와 작업 적용이 없으면 golden과 우연히 같은 결과라도 전파 성공으로 하지 않는다.
- reference 구현, 최적화 정답, 가짜 대화·동의·이해도 확인을 만들지 않는다.
- A·C2·설명물 등 빠진 범위를 README에서 미검증/실패/미구현/승인된 제외로 구분한다.
