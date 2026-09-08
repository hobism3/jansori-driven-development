# 공개 기능 계약 — C-model 영상 업무

이 문서는 공개 기능 명세다. 사용자 잔소리나 스킬 규칙이 아니다.
실제 ISP/IP, SystemC 타이밍 또는 제품 NR 화질 알고리즘을 구현하지 않는다.
세대 이름 2025/vanguard와 2026/whistler는 사용자가 제공한 스토리의 라벨이다.

## 인터페이스

C++17, `cmodel::Image DoProcess(const Image&, const Parameters&)`.
RGB8 interleaved 3채널. 이미지 폭/높이 1~4096, 버퍼 길이 폭×높이×3.
R 0~64, StrengthQ8 0~256, GainQ8 0~1024. 유효하지 않은 값은 std::invalid_argument.
출력 크기는 입력과 동일하다. free function DoProcess는 프레임 간 상태를 공유하지 않는다.
LocalContrastModel의 객체별 관리 상태는 별도의 TASK.md 계약을 따른다.

## 평균

픽셀마다 중심 주변 (2R+1)×(2R+1)의 해당 채널 값을 합산한다.
경계 밖 좌표는 가장 가까운 유효 좌표로 제한하여 경계 픽셀을 반복한다(replicate).
평균 M은 총합을 면적으로 정수 나눗셈한 값이다. 중간 반올림은 없다.

## B / Noise Reduction

`Y = (X*(256-StrengthQ8) + M*StrengthQ8 + 128) / 256`.

## C / Local Contrast

`Y = ClampToByte(X + ((X-M)*GainQ8)/256)`.
X-M은 부호 있는 정수이며 음수 나눗셈은 C++ 정수처럼 0 방향으로 절삭한다.
ClampToByte는 0~255 범위로 자른다.

## 기본 실행

업무 공간에 common/, src/, input.ppm이 있을 때:

```bash
# B
c++ -std=c++17 -O2 -Icommon common/runner.cpp src/noise_reduction.cpp -o workload
./workload input.ppm output.ppm

# C는 -Isrc를 추가하고 src/local_contrast.cpp를 사용한다.
```

runner.cpp는 입출력만 수행한다. 실행 시간이 출력되지 않는다고 미완성 서비스가 있는 것이 아니다.
입력 PPM은 숫자로 만든 합성 패턴이다. 제품의 촬영 데이터나 실제 화질 성능을 뜻하지 않는다.
