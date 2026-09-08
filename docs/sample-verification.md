# 샘플 입력·후보 검사 — 제품 검증과 분리

이 도구는 제공된 C++ 샘플과 그 후보를 검사한다. Jansori 서버·Hook·Skill·AI-DLC를 실행하지 않는다.
제품의 `make verify`를 대체하지 않으며 새 제품 API나 Make 타깃을 요구하지 않는다.
필요 환경은 **Python 3.10 이상, C++17 컴파일러**다. Python 외부 패키지는 필요하지 않다.
컴파일/실행은 임시 디렉터리에서 수행하고 원본 소스와 golden은 변경하지 않는다.
후보 코드를 실제로 실행하므로 내용을 검토한 신뢰할 수 있는 샘플만 사용한다. 보안 샌드박스는 아니다.

## 1. 지금 받은 입력 확인

이 패키지 루트에서 실행한다. `c++` 대신 설치된 `g++` 또는 `clang++`를 지정할 수 있다.
여러 컴파일러를 비교하려면 `--compiler`를 반복한다. 존재하지 않는 컴파일러는 성공으로 건너뛰지 않는다.

```bash
python3 tools/verify_sample.py --mode integrity --report ../jansori-evaluation/integrity.json
python3 tools/verify_sample.py --mode starter --compiler c++ \
  --report ../jansori-evaluation/starter.json
# 두 컴파일러가 모두 설치된 환경에서:
python3 tools/verify_sample.py --mode starter --compiler g++ --compiler clang++ \
  --report ../jansori-evaluation/starter-two-compilers.json
```

`integrity`는 manifest hash, fixture JSON, 사례 ID/R/I 참조, seed 깊이, 수치 golden과 공개 연산식을 확인한다.
R/I 참조가 모두 존재하는 것과 실제 제품이 그 요구사항을 만족하는 것은 다르다.
`starter`는 B/C 영상 계산과 오류 계약, 정책 보조 코드, 분리 작업물 복사·알려진 정답 문자열 검사를 수행한다.
C 상태 기능은 미완성이므로 `EXPECTED_INCOMPLETE`가 정상적인 **입력 준비 판정**이다.
무조건적인 실패 무시는 아니다. 원본의 실제 관측이 미완성 starter의 예상 상태/영상과도 다르면 검사 실패다.
이를 없애려고 개발 단계에서 C 원본의 TODO를 채우지 않는다.

## 2. 실제 C0/C1/C2 후보 확인

평가자는 시연 전에 이 ZIP의 원본을 개발·C 작업 폴더와 분리해 보관한다.
C 세션이 끝난 뒤 보존한 후보를 평가한다. 후보의 `src/`에는 수정된 cpp와 hpp를 함께 둔다.
추가 C++ 번역 단위와 로컬 헤더도 `src/` 아래에 두면 수집한다. 외부 라이브러리가 필요한 빌드는
이 샘플 평가기 범위를 벗어나므로 별도 빌드 근거를 남긴다. 성공으로 처리하지 않는다.

```bash
# 평가자 보관본 루트에서. 후보 경로는 이 패키지 밖의 별도 작업 폴더다.
python3 tools/verify_sample.py --mode candidate \
  --candidate /absolute/path/to/c0 --workload C --compiler c++ \
  --report ../jansori-evaluation/c0.json
# c1, c2도 같은 명령/컴파일러로 각각 실행한다.

# B 후보도 같은 도구로 수치 계약을 확인할 수 있다.
python3 tools/verify_sample.py --mode candidate \
  --candidate /absolute/path/to/b --workload B --compiler c++ \
  --report ../jansori-evaluation/b.json
```

평가에는 **보관본의** `common/cmodel.hpp`, `common/runner.cpp`, `C/session_probe.cpp`, 수치/상태 golden을 사용한다.
후보의 클래스 헤더·구현은 함께 검사하되, 후보가 수정한 runner/probe는 빌드 입력에서 제외한다.
`src/` 안에서 `cmodel.hpp`를 별도로 정의해 공통 API를 가리는 구성은 거부한다.
원본 공통 API와 직접 호환되지 않는 후보는 수용 계약/빌드 문제로 기록한다.
보고서에는 사용한 고정 평가기와 후보 소스의 SHA-256, 명령·컴파일 결과, 기대/실제 불일치가 포함된다.

`tools/`, golden, 평가 보고서, 이 문서는 C에게 전달하지 않는다.
평가 후 피드백을 받은 수정 실행은 최초 무힌트 실행과 구분한다. 파일 복사만으로 세션 격리를 증명하지 않는다.

## 3. 이번에 강화한 판정

| 검사 | 기대 |
|---|---|
| 수치 입력 42건, 오류 5건 | B DoProcess, C DoProcess와 DoRun 각각 동일 계약 |
| W-37~42 | 256의 배수가 아닌 Gain. 음수 나눗셈을 0 방향으로 절삭 |
| C DoRun 반환값 | 상태뿐 아니라 크기와 모든 픽셀도 올바름 |
| C 공개 관측 24단계 | 성공/실패 전이, 비기본 파라미터 Reset 전후, 두 객체 교차 실행/Reset |
| 전체 640×360 영상 | 고정 기본 파라미터에서 원본 출력과 byte 동일 |
| 평가기 독립성 | 후보가 바꾼 관측기 대신 평가자 고정 사본 사용 |

수치 검사는 공개 연산식을 별도로 계산해 golden 자체도 확인한다. 이는 평가자 전용 직접 계산이며
C에게 전달할 최적화 C++ 해법이나 완성된 상태 구현이 아니다.

## 4. 종료 코드·보고서 해석

| 종료 코드 | 의미 |
|---|---|
| 0 | 선택한 검사 범위에서 통과. starter는 의도된 미완성 상태의 입력 적합성만 확인 |
| 1 | 실행 관측과 기대값 불일치 등 기능/검사 실패 |
| 2 | 파일/환경/컴파일/실행/JSON/무결성 오류 또는 명령 사용 오류 |

`PASS_INPUT_CHECKS_ONLY`: 제공 입력 검사 성공. 제품/실제 C 결과 성공이 아니다.
`PASS_FUNCTIONAL_CHECKS_ONLY`: 지정한 후보의 기능 검사 성공. 전파 성공이 아니다.

다음은 이 도구로 판정하지 않는다: private 멤버의 실제 선언과 규칙 적용, Capsule 선택/Read,
부모·자식 실제 version, 잔소리 대상/공유 의도, 실제 compaction 의미 보존, 속도 개선,
사람 승인·설명 이해도. `docs/demo-transcript.md`에 코드 검토와 실제 세션 증거를 별도로 연결한다.

## 5. 검출력 확인 기록

`EVALUATOR-REGRESSION-CHECKS.json`은 임시 검사용 정상 대조군과 의도적인 오류 후보를 사용해
평가기의 통과/실패 구분을 확인한 기록이다. 실제 Claude 결과나 제품 기능 검증이 아니다.
오류는 빈 DoRun 반환, Reset 파라미터 변경, 객체 간 공유 상태, 음수 내림 나눗셈이다.
임시 대조군/오류 후보의 C++ 소스는 이 패키지나 C 환경에 포함하지 않았다.
이 기록과 별개로 위 명령으로 입력 및 실제 후보의 검사를 재실행할 수 있다.
