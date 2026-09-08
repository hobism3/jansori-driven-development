# U2 — Claude Code Plugin · Code Generation Plan (Single source of truth)

> 단계: CONSTRUCTION · U2 Code Generation. 유형: Greenfield 다중 단위(단일 저장소·단위별 최상위 디렉터리 = `plugin/`).
> 근거: `construction/U2-claude-code-plugin/functional-design/*`(business-logic-model 6 흐름, business-rules BR-01..BR-11, domain-entities), `contract-decisions.md`(D-01..D-08), `unit-of-work.md`(U2), `unit-of-work-story-map.md`, `aidlc-state.md`(Q1..Q12=A, 자연어 자동 판별).
> ⚠️ 용어: "정상화(normalize)" = SPEC "compaction" ≠ Claude Code context compaction. capsule-normalizer 서브에이전트 **정의는 U3**; U2는 **기동 지시**만.
> 코드 위치: **워크스페이스 루트 `plugin/`** (문서만 `aidlc-docs/`). 서버는 U1 `server/`(수정 없음).

## 단위 컨텍스트
- **구현 스토리(주)**: US-01, US-02, US-04, US-05, US-13. **(관여)**: US-03, US-06, US-07, US-08, US-09, US-10, US-11, US-14, US-17.
- **의존**: U2 → U1(loopback HTTP만). U1 엔드포인트/스키마/오류코드(D-02/D-03/D-08)를 소비. U1 코드 수정 없음.
- **불변식(U2 측면)**: I-08/I-07(fail-open·오류 분류), I-02/I-03(로드·확장은 서버, U2는 반영), I-05(request_id 멱등), I-13(대상 모호 확인), I-10(정상화 비차단 트리거). 나머지 불변식·원자성은 서버 강제.
- **비목표**: 서버측 상태·정상화 병합(U3)·`make verify`/PBT(U4)·데모 산출물(사용자).

## 확정 설계값 (Q1..Q12=A + 자동 판별)
- 주입: stdout JSON `additionalContext` = **행동 프리앰블 + skill 인덱스**(매 턴). 실패 시 무주입·exit 0.
- 호출: 번들 **Python + urllib(표준 라이브러리)**. 서버 `JANSORI_URL`(기본 `http://127.0.0.1:8765`). 훅 상한 `JANSORI_HOOK_TIMEOUT_MS`(기본 2000).
- Stop: 항상 일반 notice, **stderr**, exit 0(휴리스틱 없음).
- 공통경로: `plugin/scripts/jansori_client.py`(액션 서브커맨드). 커맨드·Skill·자연어가 모두 이를 사용.
- 로드 확장/version 기록: 서버 담당. nag 대상: resolve-target→409 시 사용자 확인. request_id: 액션당 UUID·재시도 재사용·skill 바인딩. 오류: SERVER_ERROR vs SKILL_ABSENT 구분. normalize_due 트리거 지시: `/jansori:nag`+load Skill 문서.

---

## 생성 단계 (순차 실행, 완료 시 [x])

### Step 1 — 플러그인 스캐폴드 (US-전반)
- [x] `plugin/.claude-plugin/plugin.json` (name=`jansori`, description, version `0.1.0`)
- [x] 디렉터리: `plugin/hooks/`, `plugin/skills/load/`, `plugin/commands/`, `plugin/scripts/` (agents/는 U3)

### Step 2 — 공통 클라이언트 스크립트 (BR-04/07/08, D-02/D-03/D-08 · US-02/06/07/08/09/10/13/14)
- [x] `plugin/scripts/jansori_client.py` — urllib 기반. 서브커맨드: `index`, `load`, `resolve-target`, `nag`, `register`, `protected-change`.
  - env `JANSORI_URL`/`JANSORI_HOOK_TIMEOUT_MS`; `--timeout-ms` 인자; `--session`, `--request-id`(미지정 시 UUID 생성).
  - 구조화 오류 봉투 파싱 → `{ok:bool, code?, message?, data?}` 표준 반환(stdout JSON). 네트워크 실패 = `SERVER_ERROR`.
  - request_id: skill 바인딩·재사용 안전(호출자가 동일 값 전달 시 그대로 전송).

### Step 3 — 공통 클라이언트 단위 테스트
- [x] `tests/unit/u2/test_jansori_client.py` — `urllib.request.urlopen` monkeypatch로 서버 응답/오류/타임아웃 모의. 검증: 오류코드 분류(SERVER_ERROR≠SKILL_ABSENT), 타임아웃→SERVER_ERROR, request_id 전달, JSON 계약 파싱, loopback URL 사용(BR-11.1).

### Step 4 — 훅 (BR-01/02/03 · US-01/05/13, I-08)
- [x] `plugin/hooks/user_prompt_submit.py` — stdin `session_id` 파싱 → client.index(2000ms) → 성공 시 `{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext": preamble+index}}` + exit 0; 실패/타임아웃 → 빈 stdout + exit 0. **LLM 호출 없음, exit 2 금지.** 행동 프리앰블 상수 포함(BR-02.3).
- [x] `plugin/hooks/stop_notice.py` — stdin 파싱 → 일반 저장/잔소리 안내를 **stderr**로 출력, stdout 비움, exit 0(BR-03).
- [x] `plugin/hooks/hooks.json` — 3단 중첩. UserPromptSubmit→user_prompt_submit.py, Stop→stop_notice.py. `command`는 `python ${CLAUDE_PLUGIN_ROOT}/hooks/xxx.py`, `shell` 명시.

### Step 5 — 훅 계약 테스트 (강화: 실제 서브프로세스, Claude Code 훅 계약 그대로)
- [x] `tests/unit/u2/test_hooks.py` — **훅을 실제 서브프로세스로 실행**하고 진짜 stdin JSON을 주입(함수 호출 모의가 아니라 CC가 부르는 방식 그대로): (a) 서버 다운 시 빈 stdout·exit 0(fail-open, I-08), (b) 성공 시 stdout 유효 JSON·`hookSpecificOutput.additionalContext`에 프리앰블+인덱스 포함, (c) **exit 2 절대 미발생**(모든 분기), (d) Stop이 stderr에만 쓰고 stdout 비움·exit 0, (e) 잘못된/빈 stdin에도 fail-open.

### Step 5b — 훅 통합 테스트 (강화: 실제 U1 서버 왕복 + 행업 타임아웃)
- [x] `tests/unit/u2/test_hooks_integration.py` — **실제 U1 앱을 127.0.0.1 임시 포트에 기동**(uvicorn 백그라운드 스레드) 후 훅 서브프로세스 실행: (a) 서버 정상 → 인덱스 실제 주입 확인, (b) 서버 종료 → 빈 출력·exit 0, (c) **행업 소켓(accept 후 무응답)** → `JANSORI_HOOK_TIMEOUT_MS`(예: 800ms) 예산 내 복귀·exit 0(I-08 실측). loopback 전용 사용 확인(BR-11.1).
> 이 두 단계로 **훅이 스스로 하는 동작 = 스크립트 계약 + HTTP 왕복 + 타임아웃**을 실측 보장한다. 나머지 CC 런타임 배선은 Step 9 잔여 체크리스트로 이월.

### Step 6 — load Skill (BR-05/10 · US-02/03/04/11)
- [x] `plugin/skills/load/SKILL.md` — frontmatter(description, allowed-tools: Bash로 client 호출). 본문: 인덱스에서 선택→`jansori_client.py load` 호출→응답(부모+직속 자식 확장·로드 version)을 컨텍스트에 반영. **normalize_due=true 관측 시 백그라운드 capsule-normalizer(U3) 기동** 지시(BR-10). 로드 실패 시 SERVER_ERROR/SKILL_ABSENT 구분 안내(BR-08).

### Step 7 — 커맨드 (BR-04/06/07/09/10 · US-02/06/07/08/09/10/14)
- [x] `plugin/commands/nag.md` — `/jansori:nag`. 공통경로: resolve-target→(409 시 사용자 확인, I-13)→nag(request_id)→normalize_due 시 서브에이전트 기동 지시. 오류/재시도 규칙 명시.
- [x] `plugin/commands/save.md` — `/jansori:save`. 유사 재검색 안내(US-06)→register(request_id)→중복(DUPLICATE_REGISTRATION)/보호필드 승인 전달(I-14) 처리.

### Step 8 — 문서 (요약)
- [x] `aidlc-docs/construction/U2-claude-code-plugin/code/` : `client-summary.md`, `hooks-summary.md`, `skills-commands-summary.md`, `README-u2.md`(설치·env·설계값·테스트 결과·U1/U3/U4 경계·검증 정직성 표기).

### Step 9 — 테스트 실행 + 정직성 기록 + U4 잔여 체크리스트
- [x] `python -m pytest tests/unit/u2 -q` 실행, 결과를 요약/audit에 사실대로 기록.
- [x] `code/README-u2.md`에 **U4 실기동/수동 검증 잔여 체크리스트** 명시(우리 테스트로 보장 불가·CC 런타임 필요, F-04):
  - [ ] CC가 UserPromptSubmit/Stop 훅을 실제 발화하고 `additionalContext`가 모델에 주입되는지 (U4 실기동/수동)
  - [ ] stderr notice가 CC UI에서 사용자에게 보이는지 (미확인 시 notice-only 유지 대안)
  - [ ] 모델이 `normalize_due` 관측 후 capsule-normalizer(U3) 서브에이전트를 실제 기동하는지 (U3+U4)
  - [ ] Windows 실제 설치에서 `${CLAUDE_PLUGIN_ROOT}`+`shell`로 python 훅이 실행되는지 (U4 `make verify`/수동)
  > 이 항목들은 **완료로 표기하지 않으며** unverified로 정직 표기(F-04). U2 코드/계약 테스트 통과 ≠ CC 런타임 배선 검증.

---

## 스토리 추적성
| Story | 단계 | 검증 |
|---|---|---|
| US-01 인덱스 주입·fail-open | Step 4,5 | auto(단위) + U4 실기동 |
| US-02 선택·로드·공통경로 | Step 2,6,7 | transcript(U4) |
| US-03 refs 확장 트리거 | Step 6 (서버가 확장) | auto(U1) |
| US-04 로드 반영 | Step 6 | transcript(U4) |
| US-05 저장 제안 notice | Step 4,5 | transcript(U4) |
| US-06 유사 재검색·중복 | Step 2,7 | auto/transcript |
| US-07 잔소리 version | Step 2,7 (서버 누적) | auto(U1) |
| US-08 대상 판정·모호 확인 | Step 2,7 | transcript |
| US-09 보호 필드 승인 전달 | Step 2,7 (서버 강제) | auto(U1) |
| US-10 임계값·멱등·원자 | Step 2 (request_id) | auto(U1) |
| US-11 정상화 비차단 트리거 | Step 6,7 (기동 지시) | transcript(U3/U4) |
| US-13 서버실패 비차단·분류 | Step 2,4,5 | auto |
| US-14 중복 등록 방지 | Step 2,7 (request_id) | auto |
| US-17 증거 정직성 | Step 8,9 | transcript(U4) |

## 완료 기준
- Step 1..9 전부 [x], plugin/ 코드·훅·Skill·커맨드·문서 생성, U2 단위 테스트 실행·기록. U1 코드 무수정 확인. 실기동/전파 증거는 U4 이월 명시.
