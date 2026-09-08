# Components — Jansori Plugin

> 고수준 컴포넌트 식별·책임·인터페이스. 상세 비즈니스 로직은 Functional Design(per-unit)에서.
> 단위 매핑(Q9=A, 4단위): U1 Server & Store & Contracts / U2 Claude Code Plugin / U3 Capsule Normalizer Subagent (SPEC: compaction) / U4 Build·Verify·Seed + PBT.
> ⚠️ 용어: 본 제품 "캡슐 정상화(Capsule Normalization)" = SPEC의 "compaction". Claude Code의 context compaction과 무관(contract-decisions.md 용어 구분 절 참조).
> 아키텍처 스타일(Q10=A): Layered — 어댑터 얇게, 규칙은 서비스/도메인. "복잡성 최소" 지침: 각 컴포넌트 내부를 얇게 유지.

## 컴포넌트 개요

| ID | 컴포넌트 | 단위 | 목적 |
|---|---|---|---|
| CMP-01 | HTTP Adapter | U1 | loopback-only 요청 수신·검증·역직렬화, 서비스 위임, 구조화 오류 직렬화 |
| CMP-02 | Skill Service | U1 | 등록·로드·refs 확장 오케스트레이션 |
| CMP-03 | Nag Service | U1 | 잔소리 적용·version 상승·대상 판정·임계값 판정 |
| CMP-04 | Normalization Service (SPEC: compaction) | U1 | 정상화 커밋 검증(base_version·보존·길이)·원자 커밋. context compaction과 무관 |
| CMP-05 | Session Service | U1 | 세션별 활성 parent/children·version·진행 상태 관리(콘텐츠와 분리) |
| CMP-06 | Security Guard | U1 | loopback 바인딩, temp-dir 경로 격리, 스크립트 비자동실행, 소스·프롬프트 무수집 |
| CMP-07 | Capsule Store (in-memory) | U1 | Capsule/version/corrections/refs/assets 단일 진실원, skill_id 락+원자 포인터 스왑 |
| CMP-08 | Domain Model | U1 | Capsule, Version, Correction, RefsGraph, ProtectedFields, RequestLog |
| CMP-09 | Plugin Hooks | U2 | UserPromptSubmit(인덱스 주입, fail-open), Stop(저장 제안 notice) |
| CMP-10 | Load Skill | U2 | 모델 호출 가능 Skill — 인덱스 기반 선택·로드 |
| CMP-11 | Command/NL Common Path | U2 | `/jansori:save`·`/jansori:nag`·자연어 → 공통 서버 액션 경로 |
| CMP-12 | Capsule Normalizer Subagent (SPEC: compaction) | U3 | `normalize_due` 시 격리 백그라운드에서 서버 Capsule 병합 → `/normalize` 제출. context compaction과 무관 |
| CMP-13 | Build/Verify/Seed Harness | U4 | `make run`/`make verify`/제네릭 `make seed` |
| CMP-14 | PBT Harness | U4 | Hypothesis 제너레이터·stateful·oracle·shrinking + golden 예제 테스트 |

## 컴포넌트별 책임·인터페이스

### CMP-01 HTTP Adapter (U1)
- **책임**: 라우팅, 스키마 검증, `session_id`/`request_id` 추출, 서비스 위임, 오류 코드 매핑. **loopback-only bind(127.0.0.1/::1)**.
- **인터페이스**: `GET /skills/index`, `GET /skills/{id}`, `POST /skills/register`, `POST /skills/{id}/load`, `POST /skills/{id}/nag`, `POST /skills/{id}/protected-change`, `POST /skills/{id}/normalize`.

### CMP-02 Skill Service (U1)
- **책임**: 등록 전 유사 재검색(I-06), 로드 시 활성 범위 구성 + refs 직속 자식 확장(I-03, depth-1), I-02 로드 기록.
- **인터페이스**: `register()`, `load()`, `build_index()`, `expand_refs()`.

### CMP-03 Nag Service (U1)
- **책임**: 대상 parent/child 판정(I-13, 모호 시 확인), correction 누적(oldest→newest), 불변 version 상승(I-01), 임계값(3) 판정 → `normalize_due`.
- **인터페이스**: `apply_nag()`, `resolve_target()`, `check_threshold()`.

### CMP-04 Normalization Service (SPEC: compaction) (U1)
- **책임**: `/normalize` 제출 검증 — base_version 최신성(I-04), 보존(assets/refs·유효 지시, I-11), 길이 L(I-09); 통과 시 원자 커밋(새 version+포인터+corrections 비움, I-12). Claude Code context compaction과 무관.
- **인터페이스**: `commit_normalization()`, `validate_preservation()`.

### CMP-05 Session Service (U1)
- **책임**: `session_id`별 활성 parent/children·version, 진행 상태 플래그(`normalize_due`/`normalize_in_progress`) — **콘텐츠와 분리(I-10)**.
- **인터페이스**: `get_or_create_session()`, `set_active_scope()`, `set_progress_flag()`.

### CMP-06 Security Guard (U1)
- **책임**: 바인딩 loopback 강제, assets/refs 쓰기 경로 temp-dir 격리(path-traversal 차단), 스크립트 비자동실행, 소스·프롬프트 무수집, secret-pattern 보조 스캔(경로 검사와 혼동 금지).
- **인터페이스**: `assert_loopback()`, `contain_path()`, `guard_script()`.

### CMP-07 Capsule Store (U1)
- **책임**: 인메모리 저장, skill_id 단위 락 + 원자적 포인터 스왑(copy-on-write, I-12), request_id 멱등 기록(I-05), 중복 등록 차단(I-06).
- **인터페이스**: `get_latest()`, `append_version_atomic()`, `record_request()`, `exists()`.

### CMP-08 Domain Model (U1)
- **책임**: Capsule/Version/Correction/RefsGraph(depth-1 제약 I-15)/ProtectedFields(승인 플래그 I-14)/RequestLog 불변식 캡슐화.

### CMP-09 Plugin Hooks (U2)
- **책임**: UserPromptSubmit → `GET /skills/index` 주입(2000ms 상한 fail-open, LLM 호출 없음, I-08); Stop → 저장 제안 notice only.

### CMP-10 Load Skill (U2)
- **책임**: 주입된 인덱스의 이름/설명으로 선택·`load` 호출. 판단은 transcript 검증.

### CMP-11 Command/NL Common Path (U2)
- **책임**: `/jansori:save`·`/jansori:nag`·자연어 요청을 동일 서버 액션 경로로 수렴.

### CMP-12 Capsule Normalizer Subagent (SPEC: compaction) (U3)
> ⚠️ 우리 캡슐 정상화 전용. Claude Code context compaction(트랜스크립트 요약)과 무관하며 트랜스크립트를 읽거나 요약하지 않음.
- **책임**: (메인 모델이 `normalize_due` 관측 후 기동) 격리 백그라운드에서 **서버 GET으로 Capsule만** 취득 → body+corrections 병합(보존, I-11) → `POST /skills/{id}/normalize` 제출. stale면 최신 base로 재시작. 소비자 비차단(I-10).
- **구현 형태**: Claude Code 서브에이전트 정의(도구: Bash/WebFetch로 loopback 호출; 대화 컨텍스트 미참조). 훅이 아니라 모델이 기동. 부모 세션 종료 시 중단(커밋 전이면 무변경, 안전). 상시 분리 실행 미채택(v1 범위 밖).

### CMP-13 Build/Verify/Seed Harness (U4)
- **책임**: `make run`(빈 상태 기동), 제네릭 `make seed`(하드코딩 ID 없음, `fixtures/seed/*.json`, DEV-38), `make verify`(실제 서버 in-test 기동/종료, 기계 계약 검사).

### CMP-14 PBT Harness (U4)
- **책임**: Hypothesis 도메인 제너레이터(Capsule/correction/refs graph/request_id/base_version), 불변식·멱등·stateful·oracle 속성(PBT-01..08), 핵심 경로 golden 예제 병행(PBT-10).
