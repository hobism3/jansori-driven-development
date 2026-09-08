# U1 Code Generation 계획 (Part 1 — Planning)

> 단위: **U1 — Server & Store & Contracts**. 이 계획이 Code Generation의 **단일 진실원**.
> 근거: `functional-design/domain-entities.md`·`business-logic-model.md`·`business-rules.md`, `contract-decisions.md`(D-01..D-07), `unit-of-work.md`.
> ⚠️ "정상화(normalize)" = SPEC "compaction" ≠ Claude Code context compaction.

## 프로젝트 컨텍스트
- **워크스페이스 루트**: `C:\Users\WoongbumHwang\Desktop\20260908_jansori` (애플리케이션 코드는 루트, 문서는 aidlc-docs/만).
- **유형**: Greenfield 다중 단위(monorepo, 단위별 최상위 디렉터리). U1 = `server/`.
- **스택**: Python 3.10–3.11(Req Q7=B), 경량 프레임워크 FastAPI(Req Q10=B) — **loopback-only 바인딩 필수**. 인메모리·재시작 비영속(Q9).
- **의존 방향**: `app → services → domain/store`, `security` 횡단.
- **U1 인터페이스(계약)**: `GET /skills/index`, `GET /skills/{id}`, `POST /skills/register`, `POST /skills/{id}/load`, `POST /skills/{id}/nag`, `POST /skills/{id}/protected-change`, `POST /skills/{id}/normalize`.
- **다른 단위 의존**: 없음(U1은 클라이언트 무의존). U2/U3/U4가 U1에 loopback HTTP로 의존.

## 스토리 커버리지 (U1)
- **주(primary)**: US-03(refs depth-1 확장), US-06(중복 등록 차단), US-07(잔소리·version), US-08(대상 판정), US-09(보호 변경), US-10(임계·멱등·원자), US-14(서버 실패≠중복), US-15(§5 보안).
- **관여(participating)**: US-01(인덱스), US-02(로드), US-04, US-05, US-11(정상화 커밋 검증), US-12, US-13(구조화 오류), US-16(PBT 대상), US-17.

## 코드 위치 (모두 워크스페이스 루트; aidlc-docs 금지)
```
server/
├── app/            # HTTP 어댑터(FastAPI 라우팅·검증·오류 매핑, loopback bind)
│   ├── main.py         # 앱 생성 + loopback 바인딩(assert_loopback) 진입점
│   ├── routes.py       # 7개 엔드포인트 → 서비스 위임(얇게)
│   ├── schemas.py      # 요청/응답 pydantic 모델 (RegisterInput 등)
│   └── errors.py       # 구조화 오류 매핑(D-03 코드 → HTTP)
├── services/
│   ├── skill_service.py         # register/load/build_index/expand_refs (CMP-02)
│   ├── nag_service.py           # apply_nag/resolve_target/check_threshold/protected-change (CMP-03)
│   ├── normalization_service.py # commit_normalization/validate_preservation (CMP-04)
│   └── session_service.py       # get_or_create/set_active_scope/set_progress_flag (CMP-05)
├── domain/
│   ├── models.py       # Capsule/Version/Correction/Asset/Session/IndexEntry (dataclass/pydantic)
│   ├── refs.py         # RefsGraph depth-1 검사(I-15)
│   ├── errors.py       # DomainError 계층 + 오류 코드 enum(D-03)
│   └── limits.py       # L=10000, threshold=3 (설정 가능)
├── store/
│   └── capsule_store.py # in-memory, skill_id 락 + copy-on-write 포인터 스왑, RequestLog(I-12/I-05)
├── security/
│   └── guard.py        # assert_loopback/contain_path/guard_script (§5)
└── __init__.py
tests/unit/u1/          # U1 단위 테스트(계약·불변식 스모크; 전면 PBT는 U4)
```
> `make run/verify/seed`·`Makefile`·PBT 하네스는 **U4** 단위에서 생성(여기서 만들지 않음).
> 문서 요약: `aidlc-docs/construction/U1-server-store-contracts/code/`(마크다운만).

---

## 실행 단계 (Part 2에서 [x], 순서대로)

- [x] **Step 1 — 프로젝트 구조 셋업 (greenfield)**: `server/` 및 하위 패키지 디렉터리·`__init__.py`, `pyproject.toml`/의존성 선언(FastAPI/uvicorn/pydantic, Python 3.10–3.11 명시), `.gitignore`. *(인프라 최소 — 배포 아님)*
- [x] **Step 2 — Domain 모델 생성** (`server/domain/models.py`, `limits.py`, `errors.py`, `refs.py`): Capsule/Version/Correction/Asset/Session/IndexEntry, 오류 코드 enum(STALE_BASE_VERSION/OVER_LENGTH/PROTECTED_CHANGE_DENIED/SKILL_ABSENT/SERVER_ERROR/DEPTH_LIMIT/DUPLICATE_REGISTRATION), L/threshold, RefsGraph depth-1 검사(I-15). *(US-03/06/09/10)*
- [x] **Step 3 — Domain 단위 테스트** (`tests/unit/u1/test_domain.py`): version 불변(I-01), depth-1 경계(I-15), 길이 규칙(I-09), Correction 구조/seq(I-05/I-13 데이터).
- [x] **Step 4 — Domain 요약** (`aidlc-docs/construction/U1-server-store-contracts/code/domain-summary.md`).
- [x] **Step 5 — Repository(Store) 생성** (`server/store/capsule_store.py`): in-memory 저장, `get_latest/append_version_atomic/record_request/exists`, skill_id 락 + copy-on-write 포인터 스왑, 전역 RequestLog. *(US-10/US-14, I-12/I-05/I-06)*
- [x] **Step 6 — Store 단위 테스트** (`tests/unit/u1/test_store.py`): 원자성(I-12), 멱등 재수신 직전결과 반환(I-05), 중복 exists(I-06), stale 거부(I-04).
- [x] **Step 7 — Store 요약** (`.../code/store-summary.md`).
- [x] **Step 8 — Security 생성** (`server/security/guard.py`): `assert_loopback/contain_path/guard_script`, 무수집 원칙. *(US-15, §5)*
- [x] **Step 9 — Security 단위 테스트** (`tests/unit/u1/test_security.py`): 비루프백 거부, path-traversal 거부, 스크립트 비자동실행 notice.
- [x] **Step 10 — Business Logic(Services) 생성**:
    - `skill_service.py` — register(중복 차단·depth-1·유사 경고 없음/서버 LLM 미사용), load+expand_refs(depth-1·로드 기록), build_index (US-01/02/03/06/14, I-02/03/06/15)
    - `nag_service.py` — apply_nag(불변 version·멱등·임계), resolve_target(유일매칭/NEEDS_CONFIRMATION), check_threshold, protected-change (US-07/08/09/10, I-01/04/05/09/13/14)
    - `normalization_service.py` — commit_normalization(stale/보존/원자/corrections 비움), validate_preservation(구조적) (US-11, I-04/11/12)
    - `session_service.py` — get_or_create/set_active_scope/set_progress_flag (D-01, I-02/10)
- [x] **Step 11 — Services 단위 테스트** (`tests/unit/u1/test_services.py`): 각 BL 흐름 핵심 경로 + 오류 경로(NEEDS_CONFIRMATION, PROTECTED_CHANGE_DENIED, STALE, OVER_LENGTH, normalize_due 발화).
- [x] **Step 12 — Services 요약** (`.../code/services-summary.md`).
- [x] **Step 13 — API Layer 생성** (`server/app/`): main.py(loopback 바인딩·assert_loopback), routes.py(7 엔드포인트 위임), schemas.py(요청/응답), errors.py(D-03 구조화 오류 매핑 + SERVER_ERROR↔SKILL_ABSENT 구분 I-07). *(US-01/02/07/09/11/13)*
- [x] **Step 14 — API 단위 테스트** (`tests/unit/u1/test_api.py`): 엔드포인트 라우팅·검증, 구조화 오류 형태, loopback 강제, request_id 필수.
- [x] **Step 15 — API 요약** (`.../code/api-summary.md`).
- [x] **Step 16 — 문서 생성**: `aidlc-docs/construction/U1-server-store-contracts/code/README-u1.md`(엔드포인트 계약 요약·실행 방법 개요), 계약표(D-01..D-07 → 엔드포인트). *(루트 README 전체는 U4)*
- [x] **Step 17 — 배포 아티팩트**: 최소 — `server/` 실행 진입점 확인(`python -m server.app.main` 또는 uvicorn 커맨드 문서화). *(Makefile·seed·verify는 U4)*

> **테스트 실행은 Build & Test 단계**에서 수행(여기서는 생성만). 전면 PBT(PBT-01..10)는 U4.

## 검증·불변식 매핑 (생성물 기준)
| 불변식/요건 | 구현 위치 |
|---|---|
| I-01 불변 version | domain/models.py Version, store append(+1) |
| I-02 로드 기록 | session_service.set_active_scope |
| I-03 depth-1 확장 | skill_service.expand_refs |
| I-04 stale | store/nag/normalization base_version 검사 |
| I-05 멱등 | store.record_request(전역) |
| I-06 중복 차단 | skill_service.register + store.exists |
| I-07 SERVER≠ABSENT | app/errors.py, skill_service |
| I-09 과길이 보존 | domain/limits + 각 서비스 입구 검사 |
| I-10 진행상태≠콘텐츠 | session_service.set_progress_flag |
| I-11 보존 | normalization_service.validate_preservation |
| I-12 원자성 | store.append_version_atomic |
| I-13 대상 판정 | nag_service.resolve_target |
| I-14 보호 | nag_service protected-change + domain 고정집합 |
| I-15 depth-1 | domain/refs.py (register·refs 변경) |
| §5 보안 | security/guard.py + app 바인딩 |
| D-03 상한·오류 | domain/limits + app/errors |

## 총 규모
- **17단계**, 애플리케이션 파일 ~18개(server/) + 단위 테스트 5개 + 코드 요약 5개(aidlc-docs). 
- 스토리 US-01..US-17 중 U1 주/관여 전부 커버(위 표).

---

## 승인 (Part 2 진입 전)
- [x] 사용자 계획 승인 → Part 2(코드 생성) 시작 (2026-09-08T07:15:00Z)

## 생성 완료 (Part 2, 2026-09-08T07:45:00Z)
- 애플리케이션 코드: `server/` (domain 4 + store 1 + security 1 + services 4 + app 4 + __init__ 6) + `pyproject.toml` + `.gitignore`.
- 단위 테스트: `tests/unit/u1/` (test_domain/store/security/services/api) — **43 passed** (`python -m pytest tests/unit/u1 -q`).
- 코드 요약: `aidlc-docs/construction/U1-server-store-contracts/code/` (domain/store/services/api-summary + README-u1).
- 스토리 구현: US-01/02/03/06/07/08/09/10/14/15(주) + US-11/13(관여 커밋 검증/구조화 오류) [x]. US-04/05는 U2, US-12/16/17은 U4.
