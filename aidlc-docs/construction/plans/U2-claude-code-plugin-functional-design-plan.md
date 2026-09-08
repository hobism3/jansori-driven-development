# U2 — Claude Code Plugin · Functional Design Plan (Part 1: Planning)

> 단계: CONSTRUCTION · per-unit 루프 · U2 Functional Design.
> 근거: `unit-of-work.md`(U2), `unit-of-work-story-map.md`, `stories.md`(US-01/02/04/05/13 주 + 관여), `contract-decisions.md`(D-01..D-08), `aidlc-state.md`.
> ⚠️ 용어: 본 제품 "캡슐 정상화(normalize)" = SPEC "compaction". Claude Code **context compaction(대화 트랜스크립트 요약)과 무관**. capsule-normalizer 서브에이전트 정의 자체는 **U3** 소유 — U2는 "관측 시 기동" **지시**만 담는다.
> 성격: U2는 **클라이언트측 통합**. 데이터 모델·불변식 검증·원자 커밋은 U1 소유. U2는 상호작용/제어 규칙(훅 동작, 공통 액션 경로, fail-open, 대상 판정 흐름, 서브에이전트 트리거 지시)을 확정한다.

---

## 1. 단위 컨텍스트 (책임·경계)

- **컴포넌트**: CMP-09 Plugin Hooks(UserPromptSubmit / Stop), CMP-10 Load Skill, CMP-11 Command/NL Common Path.
- **서버와의 관계**: `plugin/` → `server/`는 **loopback HTTP만**. 서버는 클라이언트를 역호출하지 않음(`normalize_due`는 응답/세션 레코드 플래그).
- **주 스토리**: US-01(인덱스 주입·fail-open), US-02(선택·로드·공통경로), US-04(로드 반영), US-05(저장 제안 notice only), US-13(서버 실패 비차단·SERVER_ERROR≠SKILL_ABSENT).
- **관여 스토리**: US-03(부모 로드 시 refs 확장 트리거), US-06/07/08/09/10(등록·잔소리·보호변경·임계값 — U2는 공통경로로 U1 호출·모호 시 확인), US-11(정상화 — U2는 트리거 지시), US-14(중복 등록 방지 — U2는 request_id 재시도 처리), US-17(증거 정직성 — U2 경로 transcript 라벨).
- **핵심 불변식/요건(U2 측면)**: I-08(fail-open), I-07(실패≠부재 표면화), I-02/I-03(로드·확장 트리거), I-05(request_id 재시도 멱등 — 클라이언트가 동일 request_id 재사용), I-13(대상 모호 시 사용자 확인), Stop=notice only.

## 2. 설계 가정 — 확인된 Claude Code 플러그인/훅 메커니즘 (Code Generation에서 실제 재확인)

> claude-code-guide로 v2.1.263 기준 확인. 아래는 **설계 가정**이며 코드 생성 시 실기동으로 재검증한다(F-04 정직성).

- **플러그인 구조**: 루트에 `.claude-plugin/plugin.json`(name=`jansori`, description, version), `hooks/hooks.json`, `skills/<name>/SKILL.md`, `commands/*.md`, (U3 소유)`agents/`. `commands/skills/agents`는 `.claude-plugin/` 밖 루트에 둔다.
- **hooks.json 3단 중첩**: `{ "hooks": { "<Event>": [ { "matcher": ..., "hooks": [ { "type":"command", "command":"...", "shell":"bash|powershell" } ] } ] } }`.
- **UserPromptSubmit**: 턴당 1회, 매처 없음(항상 발화). stdin JSON에 `session_id`, `cwd`, `transcript_path`, `tool_input.prompt` 포함. 컨텍스트 주입 = stdout JSON의 `additionalContext`(구조화) 또는 평문 stdout. **exit 2는 프롬프트를 차단·삭제하므로 금지**(fail-open 위배).
- **훅 타임아웃**: 이벤트 기본 상한 ~30s. 우리 **2000ms fail-open은 훅 스크립트 내부**(HTTP 타임아웃 2s)에서 강제해야 함 — 초과/실패 시 빈 출력 + exit 0.
- **Stop 훅**: 매처 없음, 턴 종료 시 1회. stdin에 `session_id`, `last_assistant_message`. 트랜스크립트 파일 대신 `last_assistant_message` 사용.
- **Windows**: `curl` 신뢰 불가 → **번들 Python 스크립트**를 `python ${CLAUDE_PLUGIN_ROOT}/scripts/...`로 호출(표준 라이브러리 urllib, 외부 의존 없음). `${CLAUDE_SESSION_ID}` 치환 변수 사용 가능.
- **Skill/커맨드**: `skills/<n>/SKILL.md`(model-invocable, frontmatter description/allowed-tools), `commands/<n>.md`(`/jansori:<n>`). 둘 다 공통 스크립트 호출 가능.
- **서브에이전트**: 훅(shell)은 서브에이전트를 **직접 기동 불가**. `normalize_due` 관측 시 **메인 모델**이 지시(Skill/커맨드 문구)에 따라 백그라운드 서브에이전트를 기동. capsule-normalizer 정의는 **U3**.

## 3. Functional Design 산출 계획 (질문 확정 후 생성) — 완료 2026-09-08

- [x] `construction/U2-claude-code-plugin/functional-design/business-logic-model.md`
  - 흐름 1: 세션 시작 인덱스 주입(UserPromptSubmit) — fail-open 시퀀스(2000ms)
  - 흐름 2: skill 선택·로드(load Skill / 공통경로) — 서버 load 응답(부모+직속자식 확장, 로드 version) 반영
  - 흐름 3: 저장 제안(Stop) — notice only
  - 흐름 4: 잔소리(nag) 공통경로 — resolve-target → 대상 확정/모호 확인 → /nag → normalize_due 관측 → 서브에이전트 기동 지시
  - 흐름 5: 신규 등록(save/register) 공통경로 — 유사 재검색 안내 → register(request_id) → 중복/오류 처리
  - 흐름 6: 오류·재시도 — SERVER_ERROR vs SKILL_ABSENT 구분, request_id 재사용 멱등
- [x] `construction/U2-claude-code-plugin/functional-design/business-rules.md`
  - BR: fail-open 규칙(훅 상한·비차단·exit 코드), Stop notice-only 규칙, 공통경로 수렴 규칙, 대상 모호 시 사전 확인 규칙(I-13), request_id 생성·재사용 규칙(I-05), 오류 분류 표면화 규칙(I-07), 서브에이전트 기동 조건(normalize_due), 보호변경 승인 플래그 전달 규칙(I-14, 서버가 강제·클라이언트는 전달)
- [x] `construction/U2-claude-code-plugin/functional-design/domain-entities.md`
  - U2는 신규 도메인 엔티티 없음 → 클라이언트측 **상호작용 계약**(요청/응답 형태, session_id 전달, 액션→엔드포인트 매핑 D-02 재확인)만 문서화. Capsule/version 등은 U1 소유임을 명시.
- [ ] (프런트엔드 UI 없음 → frontend-components.md 생략)

---

## 4. 질문지 (한국어) — 모든 [Answer] 채워주세요

> 형식: 각 질문에 A~E 중 택1(복수 가능 명시). 권장안은 (권장). 자유 의견은 [Answer] 뒤에 서술 가능.
> 이미 D-01..D-08에서 확정된 사항은 재질문하지 않으며, U2 구현에서 실제로 열려 있는 결정만 묻습니다.

### Q1. UserPromptSubmit 인덱스 주입 방식
- A) stdout **JSON `additionalContext`** 필드로 구조화 주입 (권장 — 파싱 안정·모델 인식 명확)
- B) 평문 stdout 텍스트로 주입
- C) A 우선, 실패 시 평문 폴백

[Answer]:A

### Q2. 훅/클라이언트 호출 구현
- A) 번들 **Python 스크립트 + 표준 라이브러리(urllib)**, `python ${CLAUDE_PLUGIN_ROOT}/scripts/jansori_client.py` 호출 (권장 — Windows 이식·무의존)
- B) bash + curl (Windows에서 curl 신뢰성 낮음)
- C) Python + requests(외부 의존 추가)

[Answer]:A

### Q3. 2000ms fail-open 강제 위치·설정
- A) **훅 스크립트 내부 HTTP 타임아웃 2000ms**, 초과/실패 시 빈 출력·exit 0. 상한은 env `JANSORI_HOOK_TIMEOUT_MS`(기본 2000)로 설정 가능 (권장 — D-03 정합)
- B) Claude Code 훅 30s 상한에 의존(부적절)
- C) 고정 2000ms(설정 불가)

[Answer]:A

### Q4. 서버 base URL/포트 구성
- A) env `JANSORI_URL`(기본 `http://127.0.0.1:8765`) — 미설정 시 기본값 (권장). 포트는 U1 `make run`과 단일 출처로 문서화
- B) 고정 포트 하드코딩
- C) plugin `settings.json`에 기록

[Answer]: A. 기본으로 실행되는 포트로. (기본 포트를 8765 외 다른 값으로 원하시면 함께 적어주세요)

### Q5. Stop 훅 "저장할 만한 변경" 감지 전략 (훅에는 LLM 없음)
- A) Stop 훅은 **항상 일반 저장/잔소리 안내 notice**만 제시(휴리스틱 없음). "저장할 만한지" 실제 판단은 사용자가 `/jansori:save|nag`를 부를 때 모델·서버가 수행 (권장 — no-LLM·notice-only 정합, 단순)
- B) `last_assistant_message` 기반 경량 휴리스틱(키워드/길이)으로 **조건부** notice
- C) Stop notice 생략, UserPromptSubmit 주입에 상시 안내 문구만 포함

[Answer]:A

### Q6. 저장 제안 notice 전달 채널 (notice only = 대화/직접 저장 아님)
- A) Stop 훅이 **stderr로 사용자 가시 notice** 출력(모델 컨텍스트 주입 아님·비차단·exit 0) (권장 — "알림만" 정합). 코드 생성 시 실제 표시 여부 재확인
- B) stdout 평문(모델이 보게 됨 = 사실상 주입)
- C) `additionalContext`로 모델에 안내시켜 모델이 사용자에게 제안하도록

[Answer]:A

### Q7. 공통 액션 경로(common path) 실현 방식
- A) **공통 Python 클라이언트 스크립트**(`scripts/jansori_client.py`, 액션별 서브커맨드)를 `/jansori:save`·`/jansori:nag`·자연어·load Skill이 모두 호출, 모델이 결과 해석 (권장 — US-02 AC2 수렴)
- B) 각 커맨드가 독립 구현(중복 위험)
- C) 로컬 MCP 서버로 액션 노출(복잡성 증가)

[Answer]:A

### Q8. load Skill의 refs 확장·version 기록 책임
- A) **U1 `POST /skills/{id}/load`가 이미** depth-1 자식 확장 + 세션 로드 기록(I-02/I-03)을 수행 → U2 load Skill은 그 응답(부모+자식 확장 콘텐츠·로드 version)을 **그대로 세션 컨텍스트에 반영**만. 클라이언트측 확장 로직 없음 (권장)
- B) 클라이언트도 일부 확장/병합 처리

[Answer]:A

### Q9. 잔소리 대상 판정 흐름 (US-08 / I-13)
- A) 공통경로가 `GET /skills/resolve-target` 호출 → **200이면 그 id로 `/nag`**, **409 NEEDS_CONFIRMATION이면 모델이 사용자에게 먼저 확인** 후 확정 id로 진행 (권장 — U1 D-08 정합)
- B) 클라이언트가 자체 이름 매칭

[Answer]:A

### Q10. `normalize_due` 관측 시 서브에이전트 기동 지시 위치
- A) `/jansori:nag` 커맨드 + load Skill markdown에 **"nag 응답 `normalize_due=true`면 백그라운드 capsule-normalizer(U3) 서브에이전트를 기동하라"** 지시 포함(서브에이전트 정의 자체는 U3). 소비자 세션 비차단(I-10) (권장)
- B) 별도 전용 Skill로 분리

[Answer]:A

### Q11. 서버 오류의 사용자 표면화 (I-07 / US-13)
- A) **UserPromptSubmit 훅은 실패 시 조용히 fail-open**(주입 없음). 명시적 액션(load/save/nag)에서만 모델이 `SERVER_ERROR`(서버 실패)와 `SKILL_ABSENT`(부재)를 **구분해 사용자에 안내** (권장 — 훅 비차단 유지·I-07 충족)
- B) 훅에서도 오류 안내를 주입

[Answer]:A

### Q12. Functional Design 깊이
- A) **Focused/Standard** — 위 6개 흐름 + 규칙 + 상호작용 계약 문서화(권장, U2 범위 적정)
- B) Comprehensive — 모든 엣지케이스 상세 시퀀스까지
- C) Minimal — 규칙 요약만

[Answer]:A

---

## 5. 다음 단계
- 위 [Answer] 수집 → 모호 답변 후속 질문(functional-design.md Step 5) → §3 산출물 생성(Step 6) → 완료 메시지·승인(Step 7~9) → U2 Code Generation.
