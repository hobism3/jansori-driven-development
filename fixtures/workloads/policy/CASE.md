# 작은 개발용 정책 업무 입력

서비스 구현이 아니다. 원래 제시된 Top/child 규칙을 적용할 작은 코드다.
원본 출력: top_accepted=false, nr_before=100, nr_after=100, rgbp=264.

수정 요청/기대값(테스트 데이터):
- 사용자 정의 함수명은 대문자로 시작하는 CamelCase. main/고정 외부 API는 예외.
- GetAttribute 키 합집합은 nr.enable, frame.bit_depth, nr.strength, nr.edge_threshold, rgbp.gain_q8.
- Top에 nr.strength=0, nr.edge_threshold=0을 추가하고 해당 이름으로 SetAttribute가 전달되어야 한다.
- nr.strength=64일 때 top_accepted=true, nr_before=100, nr_after=164. RGBP 결과는 264 유지.
- NoiseReduction은 공통 CModelBase를 public 상속하고 InitInputBuffer를 protected override로 구현하며 PrepareInputBuffer를 재사용한다. 클래스 자체를 protected 상속하라는 뜻이 아니다.
- 해당 규칙의 저장/전파는 실제 Plugin 전사로 검증한다. 정수 결과만으로 전파 성공을 판정하지 않는다.

이 입력에 대한 최적화/정답 소스는 제공하지 않는다. 서비스 개발 중에는 원본을 보존하고, 정책 업무를 실제 테스트할 때 복사본을 수정한다.
핵심 B/C 영상 대본의 필수 장면은 아니며 초기 User Stories의 보조 사례다. 추가 nag로 실행하면 당시 실제 version 증가를 기록한다.

## 평가자 전용
이 파일은 기대값과 잔소리 내용이 있으므로 C의 clean 작업 공간에 복사하지 않는다.
최신 SPEC §7의 세 상태 비교는 C/의 동일 원본·동일 요청을 사용한다. 이 보조 사례로 대체하지 않는다.
