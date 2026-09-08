# U2 — Claude Code Plugin · Business Logic Model

> 단계: CONSTRUCTION · U2 Functional Design (깊이: Focused/Standard, Q12=A).
> 근거: `plans/U2-claude-code-plugin-functional-design-plan.md`(Q1..Q12=A), `contract-decisions.md`(D-01..D-08), `stories.md`(US-01/02/04/05/13 주 + 관여).
> ⚠️ 용어: "정상화(normalize)" = SPEC "compaction". Claude Code **context compaction과 무관**. capsule-normalizer 정의는 **U3**; U2는 **기동 지시**만.
> 성격: U2는 클라이언트측 오케스트레이션. **상태·불변식 검증·원자 커밋은 서버(U1)가 강제**. 아래 흐름은 U2가 담당하는 제어/상호작용 로직만 기술한다.

## 0. 공통 구성 (Q2/Q3/Q4/Q7)

- **공통 클라이언트**: 번들 Python 스크립트 `plugin/scripts/jansori_client.py`(표준 라이브러리 urllib만; 외부 의존 없음). 훅·Skill·커맨드가 모두 이 스크립트를 호출 → 액션 수렴(US-02 AC2).
- **서버 주소**: `JANSORI_URL`(미설정 시 기본 `http://127.0.0.1:8765`). loopback 전용.
- **타임아웃**: `JANSORI_HOOK_TIMEOUT_MS`(기본 2000). **훅 경로에서만** 이 상한을 강제(HTTP 소켓 타임아웃 = 값/1000초). 명시적 액션(load/save/nag) 경로는 더 관대한 상한 허용(예: 5000ms) — 훅과 달리 사용자 요청 결과를 기다려도 무방.
- **session_id**: 훅은 stdin JSON의 `session_id` 사용; Skill/커맨드 경로는 `${CLAUDE_SESSION_ID}` 치환값을 스크립트 인자로 전달.
- **주입/출력 규약**: 훅의 컨텍스트 주입은 stdout JSON `additionalContext`(Q1). 실패/타임아웃 시 빈 출력 + exit 0(주입 없음, 비차단). **exit 2는 어떤 경우에도 사용하지 않음**(프롬프트 차단·삭제 방지, I-08).

---

## 흐름 1 — 세션 시작 인덱스 주입 (UserPromptSubmit, US-01 / I-08)

**트리거**: 사용자가 프롬프트 제출 → UserPromptSubmit 훅 발화(턴당 1회).

1. 훅이 stdin JSON에서 `session_id` 파싱.
2. `jansori_client.py index --session <id> --timeout-ms <JANSORI_HOOK_TIMEOUT_MS>` 호출 → `GET /skills/index?session_id=`.
3. **성공(HTTP 200, 상한 내)**: **행동 프리앰블 + 인덱스(이름/설명 목록)**를 `{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext": <프리앰블 + 인덱스 텍스트>}}` 형태 stdout로 출력, exit 0.
   - **행동 프리앰블(항상 자동 판별, 사용자 결정 2026-09-08)**: 짧은 지시문을 매 턴 주입한다 — "사용자 발화에 기존 지시를 바꾸는 교정(잔소리)이 감지되면 `/jansori:nag` 공통경로로 라우팅하고, 대상 skill이 모호하면 적용 전 사용자에게 확인하라. 새 규칙 저장이면 `/jansori:save`. 서버 실패 시에도 작업은 계속 진행(fail-open)." → **Skill 로드 여부와 무관하게** 모델이 자연어 잔소리를 판별할 근거가 항상 컨텍스트에 존재.
   - 서버가 실패해 인덱스를 못 받은 경우(4단계 fail-open)에는 프리앰블도 주입하지 않는다(무주입·비차단). 즉 프리앰블은 인덱스 주입에 편승하며 별도 실패 경로를 만들지 않는다.
4. **실패/타임아웃/서버다운**: **빈 출력 + exit 0**(fail-open). 사용자 입력 비차단(I-08 AC2). 오류를 주입하지 않음(Q11 — 훅은 조용히 fail-open).
5. 훅 내부에서 **LLM 호출 없음**(US-01 AC3) — 순수 HTTP GET + 텍스트 포맷.

**불변식 매핑**: I-08(유한 대기·비차단), US-01 AC1/AC2/AC3.

---

## 흐름 2 — Skill 선택·로드 (load Skill / 공통경로, US-02·US-03·US-04 / I-02·I-03)

**트리거**: 주입된 인덱스를 근거로 모델이 `load` Skill 호출, 또는 자연어/`/jansori` 경로.

1. 모델이 인덱스의 이름/설명으로 적절 skill 선택(선택 판단은 모델·transcript 검증).
2. 공통경로 → `jansori_client.py load --id <skill_id> --session <id>` → `POST /skills/{id}/load`.
3. **서버가** depth-1 자식(refs) 확장(body+corrections) + 활성 범위·로드 version 세션 기록 수행(I-02/I-03). **클라이언트는 확장 로직 없음**(Q8=A).
4. 응답(부모 + 직속 자식 확장 콘텐츠, 로드된 parent/child version)을 **그대로 세션 컨텍스트에 반영** → 이후 작업 산출물에 지시 반영(US-04, transcript 검증).
5. 오류 시 흐름 6.

**불변식 매핑**: I-02(로드 version 기록·서버), I-03(자식 확장·서버), US-02 AC1/AC2, US-03(트리거), US-04.

---

## 흐름 3 — 저장 제안 (Stop 훅, US-05 / notice only)

**트리거**: 모델 턴 종료 → Stop 훅 발화.

1. 훅이 stdin에서 `session_id`, `last_assistant_message` 확보.
2. **감지 로직 없음(Q5=A)** — 휴리스틱/LLM 없이 **항상 일반 저장/잔소리 안내 notice** 준비(예: "이번 작업을 skill로 저장하거나 기존 skill에 잔소리를 남기려면 `/jansori:save` 또는 `/jansori:nag`를 사용하세요").
3. notice를 **stderr로 출력(Q6=A)**, **stdout 비움 + exit 0** → 모델 컨텍스트에 주입되지 않고(대화 아님), 세션도 차단하지 않음(notice only). 직접 저장하지 않음.
4. 실제 "저장할 만한 변경" 판단·수행은 사용자가 `/jansori:save|nag`를 호출할 때 모델·서버가 담당.

**규칙 매핑**: US-05 AC1(알림만·대화/직접 저장 아님·사용자 선택). Stop=notice only.

> 검증 주의(F-04): Stop stderr notice의 실제 사용자 가시성은 Code Generation에서 실기동 확인. 미확인 시 대안(예: additionalContext 안내)로 조정하되 "notice only" 원칙 유지.

---

## 흐름 4 — 잔소리(nag) 공통경로 (US-07·US-08·US-10·US-11 관여 / I-13·I-05·normalize_due)

**트리거**: 사용자가 `/jansori:nag ...` 또는 자연어로 교정 요청.

1. **대상 판정(I-13, US-08, Q9=A)**: `jansori_client.py resolve-target --hint <단서> --session <id>` → `GET /skills/resolve-target`.
   - **200**: 반환 `skill_id`를 확정 대상으로 사용.
   - **409 NEEDS_CONFIRMATION**: 모델이 **사용자에게 먼저 확인**(후보 제시) → 사용자가 고른 id로 확정. (모호 시 사전 확인, US-08 AC2)
2. **request_id 생성(I-05, Q 공통)**: 클라이언트가 이 nag 요청에 대해 새 UUID `request_id` 생성. 재시도 시 **동일 request_id 재사용**(멱등, I-05 AC3). request_id는 최초 skill_id에 바인딩(D-08) — 다른 skill에 재사용 금지.
3. `jansori_client.py nag --id <skill_id> --request-id <uuid> --body <교정> [--base-version <v>]` → `POST /skills/{id}/nag`.
   - 서버가 새 불변 version 누적(I-01)·순서 보존(I-03) 수행. 클라이언트는 결과 해석만.
4. **normalize_due 관측(Q10=A, US-11)**: nag 응답에 `normalize_due=true`이면, `/jansori:nag`·load Skill 문서 지시에 따라 **메인 모델이 백그라운드 capsule-normalizer(U3) 서브에이전트를 기동**. 소비자 세션 비차단(I-10). (서브에이전트 정의·병합·커밋은 U3/U1; U2는 기동 지시만.)
5. 오류 시 흐름 6.

**불변식 매핑**: I-13(대상·모호 확인), I-05(request_id 멱등), I-01/I-03(서버), normalize_due 트리거(I-10 비차단).

---

## 흐름 5 — 신규 등록(save/register) 공통경로 (US-06·US-09·US-14 관여 / I-06·I-14·I-07)

**트리거**: 사용자가 `/jansori:save ...` 또는 자연어로 저장 요청.

1. **유사 재검색 안내(US-06 AC1)**: 등록 전 `jansori_client.py index`/`resolve-target`로 유사 skill 조회 → 유사 항목이 있으면 모델이 **교정(nag) 경로 전환을 사용자에게 안내**(판단은 transcript). 없으면 신규 등록 진행.
2. **request_id 생성**: 새 UUID. 재시도 시 동일 값 재사용(I-05) → 서버 실패·재시도가 중복 등록을 유발하지 않음(US-14, I-06).
3. `jansori_client.py register --id <skill_id> --request-id <uuid> --body ... [--protected <fields>] [--approve]` → `POST /skills/register`.
   - **중복 차단(I-06)**: 동일 skill_id 신규 등록은 서버가 `DUPLICATE_REGISTRATION`으로 거부. 클라이언트는 이를 흐름 6으로 해석.
   - **보호 필드(I-14, US-09, Q4 무관)**: name/description/keywords/assets/refs 변경 시 클라이언트는 **승인 플래그를 전달만** 하고, 강제는 서버가 수행. 승인 플래그 존재는 인간 동의 증거로 기록하지 않음(US-09 AC3).
4. 오류 시 흐름 6.

**불변식 매핑**: I-06(중복 차단·서버), I-14(보호 변경 승인 전달), I-07(실패≠부재), I-05(재시도 멱등).

---

## 흐름 6 — 오류·재시도 (US-13·US-14 / I-07·I-08·I-05)

**적용 범위**: 명시적 액션 경로(load/save/nag/protected-change). (훅 경로는 흐름 1/3에서 이미 조용히 fail-open — Q11=A.)

1. 클라이언트가 서버 응답의 구조화 오류 봉투 `{error:{code,message,detail?}}` 파싱.
2. **오류 분류 표면화(I-07, US-13 AC2, Q11=A)**:
   - `SERVER_ERROR`(연결 실패/타임아웃/5xx) → 모델이 **"서버 일시 실패, 작업은 계속 가능"** 로 사용자에 안내. 사용자 작업 비차단(I-08).
   - `SKILL_ABSENT` → **"해당 skill 없음"**(서버 실패와 구분).
   - 기타(`STALE_BASE_VERSION`/`OVER_LENGTH`/`PROTECTED_CHANGE_DENIED`/`DEPTH_LIMIT`/`DUPLICATE_REGISTRATION`/`NEEDS_CONFIRMATION`/`PRESERVATION_FAILED`/`VALIDATION_ERROR`) → 각 의미대로 안내(D-03/D-08).
3. **재시도(I-05)**: 네트워크성 실패는 **동일 request_id로 재시도** → 중복 version/등록 없음. `STALE_BASE_VERSION`이면 최신 base로 재구성 후 재시도(정상화는 U3가 재시작).
4. 어떤 오류도 **사용자 작업 흐름을 차단하지 않음**(I-08). 훅은 exit 0 유지.

**불변식 매핑**: I-07(실패≠부재), I-08(fail-open·비차단), I-05(재시도 멱등).

---

## 액션 → 엔드포인트 매핑 (D-02/D-08 재확인, U2 관점)

| U2 액션 | 진입점 | 서버 엔드포인트 | 상한 |
|---|---|---|---|
| 인덱스 주입 | UserPromptSubmit 훅 | `GET /skills/index?session_id=` | 2000ms fail-open |
| 로드 | load Skill / 공통경로 | `POST /skills/{id}/load` | 액션 상한 |
| 대상 판정 | 공통경로 | `GET /skills/resolve-target` | 액션 상한 |
| 잔소리 | `/jansori:nag`/자연어 | `POST /skills/{id}/nag` | 액션 상한 |
| 신규 등록 | `/jansori:save`/자연어 | `POST /skills/register` | 액션 상한 |
| 보호 변경 | 공통경로(승인 플래그) | `POST /skills/{id}/protected-change` | 액션 상한 |
| 저장 제안 | Stop 훅 | (엔드포인트 아님) stderr notice | — |
| 정상화 커밋 | (U3 서브에이전트) | `POST /skills/{id}/normalize` | (U2 아님) |

> U2는 위 매핑의 **호출·결과 해석·오류/재시도**만 담당. 실제 상태 전이·불변식·원자성은 U1이 강제한다.
