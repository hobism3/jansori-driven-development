# Application Design 계획 (Part 1) — Jansori Plugin

> 근거: `requirements/requirements.md`, `user-stories/stories.md`, `execution-plan.md`. SPEC.md 최종 진실원.
> 이 단계는 **컴포넌트/메서드/서비스/의존성** 고수준 설계 + **§8 D-01..D-07 계약 결정 게이트**(Q11=A: 팀 제안 → 사용자 승인)를 함께 수행합니다.
> 상세 비즈니스 로직은 이후 Functional Design(per-unit)에서. NFR 패턴(loopback·temp-dir 격리·원자적 쓰기·fail-open·PBT)도 Functional Design에 흡수(사용자 승인 스킵).
> **주의**: `spec-reference`의 값(X-Request-Id, 60s, 10000, 24h, compaction_token)은 예시일 뿐 고정 채택 아님. 아래는 SPEC 근거 팀 제안이며 사용자가 승인/수정합니다.

---

## 실행 계획 (체크박스)

### 준비
- [x] requirements.md / stories.md / personas.md 컨텍스트 로드 (완료)
- [x] 핵심 역량·기능 영역 식별 및 설계 범위 확정

### 질문 게이트 (아래 [Answer]: 태그 작성 필요)
- [x] 사용자가 모든 질문의 [Answer]: 태그 작성
- [x] 답변 분석(모호/모순/누락) 및 필요 시 후속 질문 — 블로킹 모호성 없음; Q4=L 10,000 해석, Q7=B↔Q1 재조정, Q9 복잡성지침 반영

### 필수 설계 아티팩트 생성 (Part 2, 승인 후)
- [x] `application-design/components.md` — 컴포넌트 정의·책임·인터페이스
- [x] `application-design/component-methods.md` — 메서드 시그니처·입출력(상세 규칙은 Functional Design)
- [x] `application-design/services.md` — 서비스 정의·오케스트레이션 패턴
- [x] `application-design/component-dependency.md` — 의존성 매트릭스·통신 패턴·데이터 흐름
- [x] `application-design/application-design.md` — 위 문서 통합본
- [x] `application-design/contract-decisions.md` — §8 D-01..D-07 확정 계약(루트 docs/contract-decisions.md 템플릿은 원형 유지; 제품 반영은 Code Generation)
- [x] 설계 완전성·일관성 검증

---

## 질문 (§8 계약 결정 + 컴포넌트/서비스 설계)

각 질문은 팀 권장안(A)을 먼저 제시합니다. 모두 권장안이면 각 [Answer]:에 `A`만 적으셔도 됩니다.

### Question 1 — 서버 API 스타일 (§8 D-02: action/API 매핑)
액션 집합(register / load / nag / protected-change / compaction-trigger / retry)을 서버 API로 어떻게 매핑할까요?

A) (권장) **액션 지향 엔드포인트** — `POST /skills/register`, `POST /skills/{id}/nag`, `POST /skills/{id}/load`, `POST /skills/{id}/protected-change`, `POST /skills/{id}/compact` 등 액션별 명시 경로. 자연어·`/jansori:*`·load Skill 모두 이 공통 경로로 수렴. 도메인 액션이 명확해 계약·검증이 단순.

B) 순수 REST 리소스 — `POST/GET/PATCH /skills`, `/skills/{id}/versions`, `/skills/{id}/corrections` 등 리소스 중심. HTTP 메서드로 의미 표현.

C) 단일 RPC 엔드포인트 — `POST /rpc` 하나에 `action` 필드로 분기.

X) 기타 (아래 [Answer]:에 서술)

[Answer]: A

### Question 2 — 공통 세션 상태 보관 위치 (§8 D-01: common session state)
활성 parent+직속 children, 로드된 version, 진행 상태(콘텐츠와 분리)를 어디서 관리할까요? (§4B: 소비자는 parent SKILL.md 로컬 사본을 보관하지 않음, 진행 상태는 콘텐츠와 분리)

A) (권장) **서버측 세션 레코드** — 서버가 `session_id`별로 활성 parent/children ID+version, 진행 상태를 인메모리 보관. 플러그인은 `session_id`만 전달. 단일 진실원 유지·원자성 적용 용이.

B) 클라이언트(플러그인) 보관 — 플러그인이 활성 범위·진행 상태를 들고 매 호출에 전달. 서버는 무상태.

C) 하이브리드 — 콘텐츠·version은 서버, 진행 상태는 플러그인.

X) 기타

[Answer]: A

### Question 3 — 훅 fail-open 타임아웃 상한 (§8 D-03: 한계값; I-08)
UserPromptSubmit 훅이 서버 응답을 기다리는 상한(초과 시 fail-open, 사용자 작업 비차단). SPEC 예시 60s는 데모 UX엔 과도.

A) (권장) **2000ms** — 데모에서 체감 지연 최소, fail-open 신속.

B) 5000ms

C) 1000ms

X) 기타(구체 값)

[Answer]: A

### Question 4 — 렌더·인덱스 길이 한계 L (§8 D-03: 한계값; I-09)
register/nag/PATCH 진입 시 렌더 길이 검사. 초과 시 콘텐츠 보존·변경 거부·자식 분리 권고(truncate/defer 아님). SPEC 예시 10,000은 예시일 뿐.

A) (권장) **8,000자** — 인덱스 주입 컨텍스트 부담과 표현력의 균형.

B) 10,000자

C) 4,000자

X) 기타(구체 값)

[Answer]: B, 최대한 원래 의견 유지하는 방향

### Question 5 — 멱등 키 & 오류 표현 (§8 D-03: errors/limits; I-05)
재시도 멱등(동일 요청 중복 방지)과 오류 응답 표현 방식.

A) (권장) **요청 본문 `request_id`(UUID) 필드 + 구조화 오류** `{ "error": { "code": "STALE_BASE_VERSION" | "OVER_LENGTH" | "PROTECTED_CHANGE_DENIED" | "SKILL_ABSENT" | "SERVER_ERROR" | "DEPTH_LIMIT" | "DUPLICATE_REGISTRATION", "message": "..." } }`. 서버 실패(SERVER_ERROR)와 skill 부재(SKILL_ABSENT)를 명확 구분(I-07).

B) HTTP 헤더 멱등 키(`Idempotency-Key`) + HTTP 상태코드 중심 오류.

C) 본문 `request_id` + 단순 문자열 오류 메시지.

X) 기타

[Answer]: A

### Question 6 — 인메모리 쓰기 원자성 전략 (§8 D-04: 데이터·쓰기 원자성; I-12)
새 version + latest 포인터 + 재시도 기록의 원자적 반영(동시 잔소리 + 백그라운드 compaction 겹침 대비).

A) (권장) **skill_id 단위 락 + 원자적 포인터 스왑** — 준비된 새 버전 객체를 만든 뒤 락 안에서 latest 포인터를 한 번에 교체(copy-on-write). 세밀한 동시성, 교착 위험 낮음.

B) 전역 단일 락 — 저장소 전체를 한 번에 하나만 쓰기. 단순하나 동시성 낮음.

C) 트랜잭션 유사 저널 — 변경 로그 후 커밋/롤백.

X) 기타

[Answer]: A

### Question 7 — compaction 실행 방식 (§8 D-07: compaction 실행; I-10/I-11)
임계값(=3) 도달 시 백그라운드 subagent로 compaction 실행. 소비자는 폴링/대기 없이 즉시 진행(진행 상태 ≠ 콘텐츠). 성공 시 새 version+body, corrections 비움. 실패 시 콘텐츠 무변경.

A) (권장) **서버가 백그라운드 작업으로 큐잉 → Claude Code subagent가 병합 수행 → 결과를 base_version 기반으로 서버에 커밋**(stale면 거부, I-04). 진행 상태는 세션 레코드의 플래그로 표현, 콘텐츠와 분리.

B) 플러그인이 subagent 트리거·병합 후 서버에 결과 제출. 서버는 검증·커밋만.

C) 서버 내부 스레드에서 병합(별도 subagent 없이). — 주의: SPEC의 "별도 subagent" 요건과 상충 가능.

X) 기타

[Answer]: B, 복잡성이 낮은 방향으로 결정.

### Question 8 — I-15 depth 위반 거부 응답 형식 (§8 D-06: refs 확장)
새 등록/refs 변경이 **저장 관계** depth 1을 넘길 때(손자 발생) 거부. (읽기 시 손자 무시로 대체하지 않음 — 거부만이 정답)

A) (권장) **거부 오류 `DEPTH_LIMIT` + 위반 경로·권고(자식 분리/평탄화) 포함**, 상태 무변경. 허용 경계(depth 1 정확)는 통과.

B) 거부 오류만(권고 메시지 없음).

X) 기타

[Answer]: A

### Question 9 — 컴포넌트/단위 분해 확인
Units Generation에서 확정하되, Application Design의 컴포넌트 경계를 다음 4-단위 기준으로 잡을까요?

A) (권장) **4단위**: (1) Server & Store & Contracts, (2) Claude Code Plugin(훅+load Skill+save/nag 공통 경로), (3) Compaction Subagent, (4) Build/Verify/Seed + PBT 하네스.

B) 3단위(Compaction을 Server에 통합).

C) 2단위(Server / Plugin만; 나머지는 하위 모듈).

X) 기타

[Answer]: A, 최대한 복잡성을 줄인 방향으로 진행해

### Question 10 — 서비스 계층 아키텍처 스타일
서버 내부 구조(서비스 계층 오케스트레이션).

A) (권장) **계층형(Layered)**: HTTP 어댑터 → 서비스(오케스트레이션: SkillService/NagService/CompactionService/SessionService) → 도메인 모델(Capsule/Version/Correction/RefsGraph) → 인메모리 Store. 어댑터는 얇게, 규칙은 도메인/서비스에.

B) 트랜잭션 스크립트(엔드포인트 핸들러에 로직 집중, 계층 최소).

X) 기타

[Answer]: A, 최대한 복잡성을 줄인 방향으로 진행해.

---

## 답변 작성 안내
- 각 질문의 `[Answer]:` 뒤에 선택지 문자(예: `A`) 또는 자유 서술을 적어 주세요.
- 모든 권장안 수용 시 전부 `A`로 적으시면 됩니다.
- 모든 태그 작성 후 알려 주시면, 답변을 분석하고(모호/모순 시 후속 질문) Part 2에서 설계 아티팩트 + `docs/contract-decisions.md`를 생성합니다.
