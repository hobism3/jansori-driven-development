# Local Contrast 모델 업무

영상 계산은 이미 구현되어 있다. LocalContrastModel의 생명주기 상태 기능은 아직 미완성이다.
이 파일은 기능 계약이며 특정 코딩 규칙이나 멤버 이름의 정답을 제공하지 않는다.

## 요청할 기능

LocalContrastModel 객체에 준비 상태를 나타내는 bool private 멤버와 처리 횟수를 나타내는
비boolean 정수 private 멤버를 추가한다. 두 멤버의 논리 이름은 각각 ready, frame_count다.
실제 구현상의 이름은 현재 적용되는 개발 규칙에 따라 정한다.

생성 직후와 Reset 직후에는 준비되지 않은 상태이며 처리 횟수는 0이다.
DoRun이 정상 반환할 때만 준비 상태를 참으로 바꾸고 횟수를 1 증가시킨다.
잘못된 입력 등으로 DoRun이 실패하면 직전 상태와 횟수를 유지한다.
객체마다 상태는 독립적이다. Reset은 처리 파라미터를 바꾸지 않는다.
public IsReady, GetFrameCount, DoRun, Reset 인터페이스는 유지한다.

기존 영상 연산과 입력 검증 계약은 common/WORKLOAD-SPEC.md를 따른다.
공개 free function DoProcess는 상태를 공유하지 않는 영상 연산으로 유지한다.
클래스 내부는 필요에 따라 구현하되 시연 자료나 외부 정답을 가져오지 않는다.

## 실행

작업 폴더의 common/, src/, input.ppm 배치를 기준으로 한다.

```bash
c++ -std=c++17 -O2 -Icommon -Isrc common/runner.cpp src/local_contrast.cpp -o workload
./workload input.ppm output.ppm
c++ -std=c++17 -O2 -Icommon -Isrc src/session_probe.cpp src/local_contrast.cpp -o session-probe
./session-probe
```

session-probe는 반환 영상, 상태/횟수, 비기본 파라미터의 Reset 전후, 객체 두 개의 교차 실행을 관측한다.
관측 프로그램의 종료 코드 0이 기능 정답 판정을 의미하지는 않는다. 최종 판정에는 평가자 보관 관측기를 쓴다. 초기 코드도 실행되지만 상태 기능이 미완성이므로
처리 후 상태와 횟수가 바뀌지 않는다. 정상 영상 출력과 미완성 상태 기능을 구분한다.
