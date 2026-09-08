# U1 — Server & Store & Contracts (실행·계약 요약)

> 루트 전체 README·`make run/verify/seed`는 **U4** 담당. 본 문서는 U1 코드의 실행 개요·계약 매핑.
> ⚠️ `/normalize` = 캡슐 정상화(SPEC compaction). Claude Code context compaction과 **무관**.

## 스택 / 실행
- Python 3.10–3.11 대상(로컬 검증은 3.12 가능), FastAPI + uvicorn, pydantic v2. 인메모리·재시작 비영속.
- 의존성: `pip install -e .[dev]` (또는 `pip install fastapi uvicorn pydantic pytest httpx hypothesis`).
- 기동(loopback-only):
  ```bash
  python -m server.app.main
  # 또는
  uvicorn server.app.main:app --host 127.0.0.1 --port 8765
  ```
  `assert_loopback`가 비루프백 host 기동을 거부(§5). host/port는 `JANSORI_HOST`/`JANSORI_PORT`.
- 설정: `JANSORI_MAX_CONTENT_LENGTH`(기본 10,000), `JANSORI_NORMALIZE_THRESHOLD`(기본 3), `JANSORI_TEMP_DIR`.

## 테스트 (생성됨, 실행은 Build & Test/U4)
```bash
python -m pytest tests/unit/u1 -q     # 43 passed
```

## §8 계약 매핑 (D-01..D-07 → 구현)
| 계약 | 엔드포인트/구현 |
|---|---|
| D-01 세션 상태 | `services/session_service.py`(active scope + progress flags) |
| D-02 동작/API | `app/routes.py` 7 엔드포인트 |
| D-03 오류·상한 | `app/errors.py` + `domain/limits.py`(L=10,000·threshold=3·request_id) |
| D-04 원자성 | `store/capsule_store.py`(락 + 포인터 스왑 + request 기록) |
| D-05 플러그인 실행 | U2(클라이언트) — 서버는 정상 응답/normalize_due 플래그만 |
| D-06 refs/파일 | `services/skill_service.expand_refs` + `domain/refs.py`(depth-1) + `security/guard.contain_path` |
| D-07 정상화 | `services/normalization_service.py`(검증+원자 커밋); 병합은 U3 서브에이전트 |

## 불변식 커버리지 (I-01..I-15, §5)
전부 코드에 반영 — 상세는 domain/store/services/api-summary.md 및 `functional-design/business-rules.md`. 단위 테스트로 스모크 검증(전면 PBT는 U4 PBT-01..10).

## 경계 (U1이 하지 않는 것)
- Makefile·`make run/verify/seed`·시드 데이터 → U4.
- Claude Code 플러그인/훅/Skill/커맨드 → U2.
- capsule-normalizer 서브에이전트(body 병합) → U3. U1은 제출된 new_body를 **구조적으로만** 검증.
