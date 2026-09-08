# U2 Code Summary — Common Client (`plugin/scripts/jansori_client.py`)

CMP-11 공통 액션 경로. 표준 라이브러리 urllib만 사용(Windows 무의존, Q2).

- **표준화 출력**: 모든 액션이 stdout에 단일 JSON `{ok,status,data}` 또는 `{ok:false,status,code,message,detail?}`.
- **오류 분류(I-07/BR-08)**: HTTPError는 서버 봉투의 `code` 사용; 연결거부/타임아웃은 `status:0, code:SERVER_ERROR`(부재 아님); 비구조화 404는 SKILL_ABSENT.
- **request_id(I-05/D-08)**: `--request-id` 재사용 시 그대로 전송(멱등 재시도). 미지정 시 UUID 생성. skill 바인딩은 서버가 강제.
- **nag/protected-change**: base_version 미지정 시 `GET /skills/{id}`로 latest version 읽고 write(read-then-write, I-04 대비).
- **loopback 강제(BR-11.1)**: `JANSORI_URL` host가 loopback이 아니면 `ValueError`.
- **UTF-8**: main에서 stdout/stderr를 UTF-8로 강제(Windows cp949 크래시 방지).
- **비목표**: 상태·병합·정상화·불변식 검증(U1/U3).

테스트: `tests/unit/u2/test_jansori_client.py`(9 케이스). 오류 분류·타임아웃·nag read-then-write·request_id 재시도·loopback 거부.
