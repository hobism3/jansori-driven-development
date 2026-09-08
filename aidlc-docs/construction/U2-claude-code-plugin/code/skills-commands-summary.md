# U2 Code Summary — Skill & Commands (`plugin/skills/`, `plugin/commands/`)

CMP-10 / CMP-11. 모두 공통 클라이언트(`scripts/jansori_client.py`)를 호출(BR-04 수렴).

## skills/load/SKILL.md (US-02/03/04/11)
- 인덱스에서 skill 선택 → `jansori_client.py load` → 서버가 depth-1 자식 확장·version 기록(BR-05), 응답을 컨텍스트에 반영.
- 결과 분기: ok→적용 / SKILL_ABSENT→부재 안내(≠장애) / SERVER_ERROR→fail-open 계속 / OVER_LENGTH·DEPTH_LIMIT→서버 메시지.
- normalize_due=true → 백그라운드 capsule-normalizer(U3) 기동, 비차단(I-10).

## commands/nag.md (US-07/08/10/11)
- resolve-target(이름→id 매핑은 인덱스로) → 409 NEEDS_CONFIRMATION 시 사용자 확인(I-13) → nag(request_id, base_version은 클라이언트가 읽음) → STALE_BASE_VERSION 재시도(동일 request_id) → normalize_due 트리거. 성공은 ok:true에서만 보고(증거 정직성).

## commands/save.md (US-06/09/14)
- 유사 재검색 안내(중복이면 nag 권유) → register(request_id 재사용으로 재시도 시 중복 방지, I-06/I-05) → DUPLICATE_REGISTRATION→nag 전환 / OVER_LENGTH·DEPTH_LIMIT→가이드 / SERVER_ERROR→fail-open.
- 보호필드(I-14): `--approve`는 사용자 명시 승인 시에만 전달, 인간 동의 증거로 기록 안 함(서버가 강제).

실제 CC 런타임에서의 Skill/command 인식·서브에이전트 기동은 U4 실기동 검증(README-u2 잔여 체크리스트).
