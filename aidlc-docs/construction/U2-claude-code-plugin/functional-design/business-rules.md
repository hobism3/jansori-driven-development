# U2 — Claude Code Plugin · Business Rules

> 근거: `business-logic-model.md`, `contract-decisions.md`(D-01..D-08), `stories.md`, 계획 Q1..Q12=A.
> 범위: U2(클라이언트)가 **강제/보장하는** 규칙. 서버가 강제하는 규칙은 "서버 강제"로 명시하고 U2는 전달·해석만.
> ⚠️ "정상화" = SPEC "compaction" ≠ Claude Code context compaction.

## BR-01 — 훅 fail-open (I-08, US-01·US-13)
- **BR-01.1** 훅(UserPromptSubmit/Stop)은 **절대 exit 2를 사용하지 않는다**(프롬프트 차단·삭제 금지). 정상·실패 모두 exit 0.
- **BR-01.2** UserPromptSubmit의 서버 호출은 `JANSORI_HOOK_TIMEOUT_MS`(기본 2000) 내 HTTP 타임아웃으로 제한. 초과·연결 실패·비200 → **빈 stdout + exit 0**(주입 없음).
- **BR-01.3** 훅 내부에서 **LLM 호출 금지**(US-01 AC3).
- **BR-01.4** 훅 실패는 사용자에게 오류로 노출하지 않음(조용한 fail-open, Q11=A). 오류 표면화는 명시적 액션 경로에서만.

## BR-02 — 컨텍스트 주입 형식 (Q1=A)
- **BR-02.1** UserPromptSubmit 성공 시 stdout은 유효 JSON이며 `hookSpecificOutput.additionalContext`(또는 최상위 `additionalContext`)에 인덱스 텍스트를 담는다. 잘못된 JSON을 출력하지 않는다(파싱 실패 시 무주입 취급).
- **BR-02.2** 주입 텍스트는 skill **이름/설명만** 포함(본문·corrections 미포함 — 로드 시점에 서버가 확장).
- **BR-02.3**(항상 자동 판별, 사용자 결정 2026-09-08) 주입 텍스트 앞에 **짧은 행동 프리앰블**을 매 턴 포함한다: 자연어 교정 감지 → `/jansori:nag` 공통경로 라우팅, 대상 모호 시 사전 확인(I-13), 새 규칙 저장 → `/jansori:save`, 서버 실패 시 작업 계속(fail-open). → Skill 로드 여부와 무관하게 잔소리 판별 근거가 항상 존재. 명시적 `/jansori:nag`도 그대로 지원(자동 판별은 이를 대체하지 않고 보완).
- **BR-02.4** 프리앰블은 인덱스 주입에 편승한다. 서버 실패로 무주입일 때는 프리앰블도 주입하지 않는다(별도 실패 경로 없음, BR-01.2 정합).

## BR-03 — Stop notice only (US-05)
- **BR-03.1** Stop 훅은 저장/잔소리 **안내 notice만** 제시하며, 대화 컨텍스트 주입도 직접 저장도 하지 않는다.
- **BR-03.2** notice는 **stderr**로 출력하고 stdout은 비운다(Q6=A). 세션을 차단하지 않는다(exit 0).
- **BR-03.3** Stop 훅은 저장 가치 판단을 하지 않는다(휴리스틱·LLM 없음, Q5=A). 판단은 사용자의 `/jansori:save|nag` 호출 시 수행.
- **BR-03.4**(검증) stderr notice의 실제 가시성은 Code Generation 실기동에서 확인; 미확인 시 notice-only 원칙을 지키는 대안으로 조정(F-04 정직 표기).

## BR-04 — 공통 액션 경로 수렴 (US-02 AC2, Q7=A)
- **BR-04.1** `/jansori:save`, `/jansori:nag`, 자연어 요청, `load` Skill은 **모두 동일 공통 클라이언트 스크립트**(`plugin/scripts/jansori_client.py`)를 통해 서버 액션을 호출한다(중복 구현 금지).
- **BR-04.2** 진입점별 로직 분기 없이, 액션 종류만 인자로 구분한다.

## BR-05 — 로드 확장 책임 분리 (I-02·I-03, Q8=A)
- **BR-05.1** refs 직속 자식(depth-1) 확장과 로드 version 기록은 **서버 강제**. U2는 서버 load 응답을 그대로 반영만 하고 클라이언트측 확장/병합을 하지 않는다.
- **BR-05.2** depth-1 초과(손자) 저장 관계 거부(I-15)도 **서버 강제**; U2는 `DEPTH_LIMIT` 오류를 해석·안내만.

## BR-06 — 잔소리 대상 판정 (I-13, US-08, Q9=A)
- **BR-06.1** nag/보호변경 전에 `GET /skills/resolve-target`로 대상을 판정한다.
- **BR-06.2** `409 NEEDS_CONFIRMATION`이면 **적용 전 사용자에게 확인**하고, 확정된 skill_id로만 진행한다(엉뚱한 대상 변경 방지).
- **BR-06.3** 클라이언트는 자체 이름 매칭을 하지 않는다(서버 resolve-target이 단일 출처).

## BR-07 — request_id·멱등·재시도 (I-05, US-14, D-08)
- **BR-07.1** 상태 변경 액션(register/nag/protected-change)마다 클라이언트가 **새 UUID request_id**를 생성한다.
- **BR-07.2** **재시도 시 동일 request_id를 재사용**한다 → 서버가 새 version/correction/등록을 추가하지 않음(멱등). 서버 실패·재시도가 중복 등록을 유발하지 않음(I-06/US-14).
- **BR-07.3** 하나의 request_id는 **하나의 skill_id에만** 사용(D-08). 다른 skill에 재사용 금지(`VALIDATION_ERROR`).

## BR-08 — 오류 분류 표면화 (I-07, US-13 AC2, Q11=A)
- **BR-08.1** 명시적 액션 경로는 구조화 오류 봉투 `{error:{code,message,detail?}}`를 파싱해 `SERVER_ERROR`(서버 실패)와 `SKILL_ABSENT`(부재)를 **구분**해 사용자에 안내한다.
- **BR-08.2** 어떤 오류도 사용자 작업 흐름을 차단하지 않는다(I-08).

## BR-09 — 보호 필드 변경 전달 (I-14, US-09)
- **BR-09.1** name/description/keywords/assets/refs 변경은 클라이언트가 **승인 플래그를 전달**만 하고, 승인 없으면 서버가 무변경으로 거부(서버 강제).
- **BR-09.2** 승인 플래그 존재를 실제 인간 동의 증거로 기록하지 않는다(US-09 AC3).

## BR-10 — 정상화 트리거 지시 (I-10, US-11, Q10=A)
- **BR-10.1** `/jansori:nag`·load Skill 문서에 "nag 응답 `normalize_due=true` 관측 시 백그라운드 **capsule-normalizer**(U3) 서브에이전트를 기동" 지시를 포함한다.
- **BR-10.2** 서브에이전트는 **메인 모델이 기동**한다(훅은 서브에이전트 기동 불가). 소비자 세션은 비차단으로 계속 진행(I-10). U2는 정의·병합·커밋을 하지 않는다(U3/U1 소유).

## BR-11 — 보안·격리 (§5, 서버 강제 / 클라이언트 준수)
- **BR-11.1** 클라이언트는 **loopback URL(`JANSORI_URL`, 기본 127.0.0.1)** 로만 호출한다. 외부 주소로 전송하지 않는다.
- **BR-11.2** 클라이언트는 작업 소스/프롬프트 전문을 서버로 자동 전송하지 않는다(§5 무수집). Capsule 콘텐츠는 사용자가 명시한 것만 전달.
- **BR-11.3** 스크립트 포함 Capsule 자동 실행 금지·요약 후 명시 동의는 서버·플로우가 강제; U2는 자동 실행 경로를 만들지 않는다.

## 규칙 → 스토리/불변식 커버리지

| 규칙 | 스토리 | 불변식/요건 |
|---|---|---|
| BR-01, BR-02 | US-01, US-13 | I-08 |
| BR-03 | US-05 | notice only |
| BR-04 | US-02 | — |
| BR-05 | US-03, US-04 | I-02, I-03, I-15(서버) |
| BR-06 | US-08 | I-13 |
| BR-07 | US-10, US-14 | I-05, I-06 |
| BR-08 | US-13, US-14 | I-07, I-08 |
| BR-09 | US-09 | I-14 |
| BR-10 | US-11 | I-10 |
| BR-11 | US-15(관여) | §5 |
