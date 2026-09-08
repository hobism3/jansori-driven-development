# U3 — Capsule Normalizer Subagent · Code Generation Plan (Part 1)

> **이 문서는 U3 Code Generation의 단일 진실원(single source of truth)이다.** Part 2는 이 계획의 스텝만 정확히 실행한다(하드코딩·이탈 금지).
> 근거: FD 산출물(`U3-capsule-normalizer/functional-design/` NL-1..8, BR-U3-01..11, E1..5), U3 FD 답 Q1..Q11=A(Q2=A), U1 계약(`POST /skills/{id}/normalize`), U2 공통 클라이언트.
> ⚠️ 정상화=SPEC compaction ≠ Claude Code context compaction. 격리: 서브에이전트는 서버 GET Capsule JSON만 입력(§5/§8).

## 유닛 컨텍스트
- **주 스토리**: US-11(정상화가 유효 지시 보존, I-10/I-11). **관여**: US-12(3상태 전파), US-17(증거 정직성·F-04).
- **의존**: U3 → U1(loopback HTTP `GET /skills/{id}`, `POST /skills/{id}/normalize`). U3 → U2(공통 클라이언트 재사용). **역호출·코드 결합 없음.**
- **U1/U2 불변**: U1 서버 코드 변경 없음. U2 클라이언트는 **순수 추가**(normalize 액션)만; 기존 index/get/load/nag/register/protected-change 동작 불변.

## 코드 위치 (workspace root; 문서만 aidlc-docs/)
- 서브에이전트 정의: **`plugin/agents/capsule-normalizer.md`**
  - 편차 명시: unit-of-work.md 트리는 root `agents/`로 그렸으나, SKILL.md/nag.md가 "shipped by U3"(플러그인 배포물)로 참조하고 Claude Code 플러그인은 `plugin/agents/`에서 서브에이전트를 발견하므로 **플러그인 내부**에 배치해야 실제 로드·기동이 성립. (Q8=A "agents/capsule-normalizer.md" 파일명 유지, 위치만 플러그인 하위로 확정.)
- 공통 클라이언트 확장(추가): **`plugin/scripts/jansori_client.py`** — `act_normalize` + CLI `normalize` 서브커맨드 + dispatch 분기.
- 테스트: **`tests/unit/u3/`**
- 코드 요약(문서): **`aidlc-docs/construction/U3-capsule-normalizer/code/`** (markdown만)

## 정직성 경계 (F-04) — 처음부터 명시
- **U3에서 진짜 보장 가능(테스트로)**: 클라이언트 `normalize` 액션의 계약(요청 형태·응답/오류 파싱), **실기동 U1 서버**와의 라운드트립(커밋 성공 / STALE / OVER_LENGTH / PRESERVATION_FAILED), 서브에이전트 정의 파일의 구조(YAML frontmatter 파싱, 격리·최소 tools·normalize 호출 지시·용어 구분 문구 존재).
- **U3에서 보장 불가(런타임/수동, U4 잔여·F-04)**: Claude Code가 `normalize_due` 관측 시 서브에이전트를 실제로 기동하는지, 서브에이전트 **LLM의 병합 품질**(NL-2/BR-U3-05 보존을 실제 문장으로 달성), 격리가 런타임에서 강제되는지. 이들은 README-u3의 "U4 잔여 검증 체크리스트"에 **미검증(unchecked)** 으로 기록하고 완료로 표기하지 않음.

---

## 실행 스텝 (Part 2에서 이 순서대로만 실행; 각 완료 즉시 [x])

- [x] **Step 1 — 공통 클라이언트 normalize 액션 추가** (`plugin/scripts/jansori_client.py`, 순수 추가)
  - `act_normalize(skill_id, base_version, new_body, merged_correction_ids, request_id, timeout_ms)` → `POST /skills/{id}/normalize` body `{base_version,new_body,request_id,merged_correction_ids}`, 응답/오류 구조화 파싱(STALE_BASE_VERSION/OVER_LENGTH/PRESERVATION_FAILED[422]/SKILL_ABSENT/SERVER_ERROR).
  - CLI `normalize` 서브커맨드: `--id --base-version --new-body --merged-id(append, 1+) [--request-id]`; dispatch 분기 추가. `request_id` 미지정 시 uuid(시도 단위, BR-U3-09). new_body는 대용량/멀티라인 가능 → **stdin 입력 옵션 지원(Issue 2 반영)**. loopback-only 유지.
  - 기존 함수 시그니처·동작 **불변**. (US-11)

- [x] **Step 2 — 클라이언트 normalize 단위테스트** (`tests/unit/u3/test_normalize_client.py`)
  - 요청 바디/경로 계약, 성공 응답 파싱, 각 오류코드 분기 파싱(monkeypatch/stub HTTP). request_id 재사용 vs 신규 규칙 확인. (US-11, BR-U3-09/BR-U3-11)

- [x] **Step 3 — 서브에이전트 정의 생성** (`plugin/agents/capsule-normalizer.md`)
  - YAML frontmatter: `name: capsule-normalizer`, `description`(정상화=compaction, context compaction 아님 명시; normalize_due 시 기동), `tools`(서버 호출용 최소 — 공통 클라이언트 실행에 필요한 것만, BR-U3-01).
  - 본문 지시(NL-1..8, BR-U3-01..11 반영): 입력=skill_id만 · 트랜스크립트 미접근(격리) → `get`으로 스냅샷 → corrections 병합(전부 또는 부분, Q3=A) **축약·의역 허용** → 병합한 correction id를 `merged_correction_ids`로 선언(BR-U3-05, U1 id-선언 검증 정합) → 제출 전 셀프 게이트(선언 id ⊆ base·비어있지 않음·길이) → `normalize` 제출(시도별 request_id) → STALE 재시작(≤3) / OVER_LENGTH·PRESERVATION_FAILED 재병합(≤3) → 실패 시 무변경·정직 로그(F-04) → 비차단·콜백 없음. 공통 클라이언트 호출 예시 명령 포함. (US-11/US-12/US-17)

- [x] **Step 4 — 서브에이전트 정의 검증 테스트** (`tests/unit/u3/test_agent_definition.py`)
  - 파일 존재·YAML frontmatter 파싱 성공, `name==capsule-normalizer`, tools 최소 집합(Bash), 본문에 필수 요소 문구 존재(격리/트랜스크립트 미접근, merged-id 선언 규약, stale 재시작·재병합 상한, 무변경·정직성, normalize 호출, 정상화≠context compaction 용어 구분). 구조 계약만 검증(LLM 행동 아님, 정직성).

- [x] **Step 5 — 실기동 통합 테스트** (`tests/unit/u3/test_normalize_integration.py`)
  - **실제 U1 서버**를 uvicorn 백그라운드 스레드(127.0.0.1 임의 포트)로 기동(U2 통합테스트 패턴 재사용). 시나리오:
    (a) register→nag×3(normalize_due)→get으로 correction id 수집→client.normalize(**축약된** new_body + merged_correction_ids 전부)→**커밋 성공**·version 상승·corrections 비워짐;
    (b) 잘못된 base_version→**STALE_BASE_VERSION**;
    (c) 미지의 correction id 선언→**PRESERVATION_FAILED(422)**(무변경);
    (d) 과길이 new_body→**OVER_LENGTH**(무변경);
    (e) 부분 선언(일부 id만)→그 id만 제거·나머지 이월. (US-11, I-04/I-09/I-11)
  - **참고**: Issue 3(빠른 nag 시 stale 반복 포기)은 bounded·I-11-safe → "반복 포기는 expected-safe"를 명시하는 주석/테스트 노트 포함.

- [x] **Step 6 — 테스트 실행·정직 기록** — `python -m pytest tests/unit/u3 -q` 및 `tests` 전체 회귀(U1+U2+U3). 결과를 실제 숫자로 기록(허위 금지). Windows UTF-8 stdio 이슈 재확인.

- [x] **Step 7 — 코드 요약·README-u3** (`aidlc-docs/construction/U3-capsule-normalizer/code/`)
  - 요약(agent-definition / client-normalize / tests) + **README-u3**: U4 잔여 검증 체크리스트(미검증): ① CC가 normalize_due에 서브에이전트 실제 기동 ② 서브에이전트 LLM 병합 품질(보존 실제 달성) ③ 런타임 격리 강제 ④ 3.10/3.11 실행 ⑤ Windows 실설치 플러그인 agents 발견. 완료로 표기하지 않음. 스토리 추적표(US-11 주 / US-12·US-17 관여).

## 스토리 추적
| Story | 구현 스텝 |
|---|---|
| US-11 (주) | Step 1(제출 계약)·Step 3(병합·보존 지시)·Step 5(실기동 커밋/보존/무변경) |
| US-12 (관여) | Step 3(정상화 후 상태 산출) — 증거는 U4 |
| US-17 (관여) | Step 6(실제 결과 기록)·Step 7(U4 잔여 미검증 표기, F-04) |

## 완료 기준
- Step 1~7 전부 [x], 클라이언트 normalize 액션 + 서브에이전트 정의 + 테스트 생성, 전체 회귀 테스트 실행(실수치 기록), U1/U2 기존 동작 불변, U4 잔여는 미검증으로 정직 표기.
