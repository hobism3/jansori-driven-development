# Unit of Work — Jansori Plugin

> 근거: `application-design/*`, `stories.md`, `requirements.md`, `plans/unit-of-work-plan.md`(Q1..Q6 전부 A). 유형: **Greenfield 다중 단위**.
> 결정: 4단위(Q1=A), 구현 순서 U1→U2→U3→U4(Q2=A), 단일 저장소·단위별 최상위 디렉터리(Q3=A), contract-first + 실기동 `make verify`(Q4=A), 주/관여 스토리 매핑(Q5=A), 단위 문서에 소유권 명시(Q6=A).
> ⚠️ 용어: 본 제품 "캡슐 정상화(Capsule Normalization)" = SPEC의 "compaction". Claude Code context compaction(대화 트랜스크립트 요약)과 **무관**.

## 용어 정의
- **Service(독립 배포 컴포넌트)**: U1 로컬 서버(단일 프로세스). U2 플러그인·U3 서브에이전트는 Claude Code 런타임에 로드되는 클라이언트측 산출물, U4는 개발/검증 하네스.
- **Module(서비스 내 논리 그룹)**: U1 내부의 adapter/services/domain/store/security 계층.
- **Unit of Work(계획 단위)**: per-unit 루프(Functional Design→Code Generation)를 돌리는 개발 단위.

---

## 단위 정의·책임

### U1 — Server & Store & Contracts
- **책임**: loopback-only Python 서버. §8 계약(D-01..D-07)의 단일 진실원. Capsule/version/corrections/refs/assets 인메모리 저장(단일 진실원), 등록·로드·refs 확장·잔소리·보호변경·정상화 검증/원자 커밋·세션 상태·보안 경계.
- **컴포넌트**: CMP-01 HTTP Adapter, CMP-02 SkillService, CMP-03 NagService, CMP-04 NormalizationService, CMP-05 SessionService, CMP-06 SecurityGuard, CMP-07 Capsule Store, CMP-08 Domain Model.
- **엔드포인트**: `GET /skills/index`, `GET /skills/{id}`, `POST /skills/register`, `POST /skills/{id}/load`, `POST /skills/{id}/nag`, `POST /skills/{id}/protected-change`, `POST /skills/{id}/normalize`.
- **핵심 불변식**: I-01(불변 version), I-02(로드 기록), I-03(parent+child 교정 전달), I-04(stale 거부), I-05(멱등), I-06(중복 등록 차단), I-07(실패≠부재), I-09(과길이 거부·보존), I-11(정상화 보존/무변경 커밋측), I-12(원자성), I-13(대상 판정), I-14(보호 필드 승인), I-15(refs depth-1), §5 보안.
- **팀 산출물**. **사용자 산출물 없음.**

### U2 — Claude Code Plugin
- **책임**: 클라이언트측 통합. UserPromptSubmit 훅(인덱스 주입, 2000ms fail-open, LLM 없음), Stop 훅(저장 제안 notice only), load Skill(인덱스 기반 선택·로드), `/jansori:save`·`/jansori:nag`·자연어 공통 액션 경로. 서버와는 loopback HTTP만.
- **컴포넌트**: CMP-09 Plugin Hooks, CMP-10 Load Skill, CMP-11 Command/NL Common Path.
- **핵심 불변식/요건**: I-08(fail-open), I-02/I-03(로드·확장 트리거), Stop=notice only.
- **팀 산출물**. **사용자 산출물 없음.**

### U3 — Capsule Normalizer Subagent (SPEC: compaction)
- **책임**: 메인 모델이 `normalize_due` 관측 시 기동하는 격리 백그라운드 서브에이전트. **서버 GET으로 Capsule JSON만** 취득 → body+corrections 병합(유효 지시·assets/refs 보존) → `POST /skills/{id}/normalize` 제출. stale이면 최신 base로 재시작. 소비자 비차단.
- **컴포넌트**: CMP-12 Capsule Normalizer Subagent.
- **⚠️ 격리**: 대화 트랜스크립트를 읽거나 요약하지 않음(§5/§8). Claude Code context compaction과 무관.
- **핵심 불변식**: I-10(비차단), I-11(보존/무변경). 커밋 검증·원자성은 U1이 담당.
- **팀 산출물**. **사용자 산출물 없음.**

### U4 — Build/Verify/Seed + PBT Harness
- **책임**: `make run`(빈 상태 기동), 제네릭 `make seed`(하드코딩 ID 없음, `fixtures/seed/*.json`, DEV-38), `make verify`(**실제 서버 in-test 기동/종료** 기계 계약 — 가짜 Store 통과 불인정). Hypothesis PBT(제너레이터·불변식·멱등·stateful·oracle·shrinking, PBT-01..10) + 핵심 경로 golden 예제. 3상태 C0/C1/C2 전파 transcript 지시·증거 정직성 표기(F-04).
- **컴포넌트**: CMP-13 Build/Verify/Seed Harness, CMP-14 PBT Harness.
- **핵심 요건**: PBT-01..10, `make verify` 실기동 계약, F-04 증거 정직성.
- **팀 산출물**: README, `make run/verify/seed`, golden/데모-시나리오/데모-트랜스크립트 입력, 이해도 점검 실행·기록.
- **사용자 산출물(팀이 완료로 표기하지 않음)**: 데모 비디오, 설명용 HTML **또는** PPT. 팀은 설명 콘텐츠·데모 스크립트·golden/scenario/transcript 입력만 제공.

---

## Greenfield 코드 조직화 전략 (Q3=A · 단일 저장소·단위별 최상위 디렉터리)

> 애플리케이션 코드는 **워크스페이스 루트**에만. 문서는 `aidlc-docs/`에만(CLAUDE.md 규칙). 실제 파일 트리는 Code Generation에서 확정.

```text
<WORKSPACE-ROOT>/
├── server/                 # U1 — loopback Python 서버
│   ├── app/                #   HTTP Adapter(라우팅·검증·오류 매핑, loopback bind)
│   ├── services/           #   SkillService / NagService / NormalizationService / SessionService
│   ├── domain/             #   Capsule / Version / Correction / RefsGraph / ProtectedFields / RequestLog
│   ├── store/              #   in-memory Capsule Store (락 + 원자 포인터 스왑)
│   └── security/           #   SecurityGuard (loopback / temp-dir 격리 / 스크립트 / 무수집)
├── plugin/                 # U2 — Claude Code 플러그인 (.claude-plugin 규약)
│   ├── hooks/              #   UserPromptSubmit / Stop
│   ├── skills/             #   load Skill
│   └── commands/           #   /jansori:save, /jansori:nag + 공통 액션 경로
├── agents/                 # U3 — capsule-normalizer 서브에이전트 정의
├── tests/                  # U4 — pbt/ (Hypothesis), golden/ (예제), verify/ (실기동 계약)
├── fixtures/               # 제공 입력(요구·평가): seed/ golden/ workloads/  ※역공학·수정 대상 아님
├── Makefile                # U4 — run / verify / seed
└── README.md               # U4 — 팀 산출물
```

- **의존 방향**: `app → services → domain/store`(단방향, Layered). `security`는 횡단(서비스가 명시 호출).
- **클라이언트↔서버**: `plugin/`·`agents/` → `server/`는 **loopback HTTP만**. 서버는 클라이언트를 역호출하지 않음(`normalize_due`는 응답 플래그).
- **Python**: 3.10–3.11(Requirements Q7=B), 경량 프레임워크(FastAPI/Flask, Requirements Q10=B) 허용하되 loopback-only 바인딩 필수. (출처: Requirements Analysis 질문셋 = aidlc-state.md Approved Decisions; App Design/Units 질문셋의 Q7/Q10과 별개)

---

## 검증 (Step: 단위 경계·의존성)
- **순환 의존 없음**: 전체 엣지 = {U2→U1, U3→U1(HTTP), U4→U1·U4→U2(테스트 시 기동/계약 검사), U2→U3(런타임 모델 트리거, 코드 의존 아님)}. 위상 정렬 U1→U3→U2→U4 성립. U1은 클라이언트 무의존. → 비순환.
- **모든 스토리 배정 확인**: US-01..US-17 전부 하나 이상 단위에 배정(아래 story-map 참조). 미배정 없음.
- **경계 근거**: U1(서버 상태·계약), U2(클라이언트 통합), U3(격리 정상화 실행), U4(빌드·검증) — 배포/실행 형태와 격리 경계가 서로 달라 단위 분리 타당.
