# Jansori — Claude Code를 위한, 계속 남고 스스로 교정되는 스킬

Jansori("잔소리")는 Claude Code 사용자가 반복해서 하는 교정(지적)을 **오래 남고 버전이 매겨지는 스킬 캡슐**로 바꿔 줍니다. 로컬 loopback 서버가 캡슐의 단일 원천을 소유하고, Claude Code 플러그인이 스킬 인덱스를 주입하며 save/nag/load 동작을 라우팅합니다. 격리된 서브에이전트가 주기적으로 누적된 교정을 압축된 캡슐 본문으로 **정규화(Normalization)** 합니다.

> **용어:** *캡슐 정규화(Capsule Normalization, 이 제품의 `normalize`)* = SPEC의 **compaction**
> (교정들을 병합해 새 캡슐 본문 버전을 만드는 것). Claude Code의 컨텍스트/대화기록
> compaction과는 **무관**합니다.

한 줄 요약: **어제 시니어가 친 잔소리가, 오늘 새로 켠 터미널의 첫 작업에 자동으로 반영됩니다.**

---

## 빠른 시작 (Quick Start)

새 Claude Code 대화에 아래 프롬프트를 그대로 붙여넣으면 클론 → 설치 → 서버 기동 → 데모 스킬 등록까지 진행됩니다. (소개 사이트 `index.html` 좌측의 **"클로드에서 실행해보기"** 버튼을 누르면 같은 프롬프트가 클립보드로 복사됩니다.)

```text
Jansori 플러그인을 이 저장소에서 설치하고 실행할 수 있게 셋업해줘. 아래를 순서대로 해줘.

저장소(공개): https://github.com/hobism3/jansori-driven-development

1) 내 OS(Windows/macOS/Linux)를 감지하고 그에 맞는 쉘 명령을 써줘. Python이 3.10~3.12 범위인지, git과 (선택) g++가 있는지 확인해줘.
2) 저장소를 홈 아래 적당한 폴더(예: ~/jansori-driven-development)에 git clone 해줘. 이미 있으면 git pull.
3) 클론한 폴더에서 서버 의존성 설치:  python -m pip install -e ".[dev]"
4) 로컬 서버를 백그라운드로 기동해줘 (loopback 전용, 기본적으로 jansori-data.json 에 지속 저장):
   - 리눅스/맥:  JANSORI_NORMALIZE_THRESHOLD=3 python -m server.app.main
   - Windows PowerShell:  $env:JANSORI_NORMALIZE_THRESHOLD="3"; python -m server.app.main
   기동 후 http://127.0.0.1:8765/health 가 {"status":"ok"} 인지 확인하고, 데모 스킬을 심어줘:  python scripts/seed.py
   그리고  python plugin/scripts/jansori_client.py index  로 스킬이 뜨는지 확인해줘.
5) 플러그인은 이 저장소의 plugin/ 폴더에 있어(.claude-plugin/plugin.json + marketplace.json). 슬래시 명령은 네가 대신 못 치니, 내가 직접 입력할 수 있게 "클론된 절대경로"를 넣은 아래 두 줄을 정확히 출력해줘:
      /plugin marketplace add <클론경로>/plugin
      /plugin install jansori@jansori-local
   그리고 활성화 안 되면 /reload-plugins 하라고 안내해줘.
6) 설치 검증 방법도 알려줘: /hooks (UserPromptSubmit·Stop 등록 확인), /plugin details jansori (commands: nag/save, skill: load 확인).
7) 서버가 8765 기본 포트로 떠 있으면 클라이언트가 자동으로 붙으니 추가 설정은 필요 없다고 알려줘. 포트를 바꿨다면 JANSORI_URL 로 맞추라고 안내해줘.

주의: 이 서버는 loopback(127.0.0.1) 전용이라 다른 PC에서 원격으로 못 붙어. 각자 자기 PC에서 실행해야 해.
설치가 끝나면, "회식 장소 고르기" 같은 스킬을 하나 만들어서(save), 다른 새 대화에서 그 스킬이 로드되는지 시험해보라고 3줄로 안내해줘.
```

> **알아둘 점:** 플러그인만으로는 부족합니다 — 각자 **자기 PC에서 로컬 서버가 떠 있어야** 스킬이 저장/전파됩니다(loopback 전용, 원격 공유 안 됨). 플러그인 설치의 슬래시 명령(`/plugin ...`)은 사용자가 직접 입력해야 합니다.

---

## 요구 사항

- **Python 3.10–3.11** (`requires-python = ">=3.10,<3.12"`). 3.12도 실사용상 동작하나, 데모 전에는 3.10/3.11을 권장합니다.
- **Claude Code v2.1.263** (설계 시점 기록, 최소 v2.1.163 이상). 데모 전에 실제 설치 버전을 확인하세요.
- Windows(win32)가 1차 타깃이지만, 서버는 가능한 한 이식성 있게 유지합니다.

## 설치 & 실행

```bash
make install     # pip install -e ".[dev]"  (fastapi, uvicorn, pydantic + pytest, hypothesis, httpx)
make run         # loopback 서버 기동 127.0.0.1:8765 (./jansori-data.json 에 지속 저장)
make seed        # 다른 셸에서: fixtures/seed/*.json 으로 실행 중인 서버를 채움
```

`make run` 은 스토어를 JSON 스냅샷(기본 `./jansori-data.json`)으로 **영속화**합니다 — 스킬 생성/수정 때마다 즉시 기록되고 재시작 시 다시 읽습니다. 순수 in-memory(일회성 세션)로 돌리려면 `JANSORI_DATA_FILE=:memory:` 로 두세요. `make seed` 는 **하드코딩된 id가 없습니다**: `fixtures/seed/*.json` 캡슐을 전부 등록(자식 먼저, depth-1 기준)하고, 선언된 교정을 nag로 재생합니다.

환경 변수 오버라이드: `JANSORI_HOST`(기본 `127.0.0.1`, **loopback 전용**),
`JANSORI_PORT`(기본 `8765`), `JANSORI_URL`(클라이언트 대상), `JANSORI_MAX_CONTENT_LENGTH`
(기본 `10000`), `JANSORI_NORMALIZE_THRESHOLD`(기본 `3`),
`JANSORI_DATA_FILE`(기본 `jansori-data.json`; `:memory:` = 영속화 안 함).

Windows에서 GNU Make가 없으면 `Makefile` 의 레시피 명령을 직접 실행하세요.
예: `python -m server.app.main`.

## 플러그인 설치 (Claude Code)

플러그인은 이 저장소의 `plugin/` 폴더에 있습니다(`.claude-plugin/plugin.json` + `marketplace.json`). 슬래시 명령은 사용자가 직접 입력합니다 — 클론된 **절대경로**를 넣어 아래 두 줄을 실행하세요.

```text
/plugin marketplace add <클론경로>/plugin
/plugin install jansori@jansori-local
```

- 활성화가 안 되면 `/reload-plugins` 를 실행하세요.
- 검증: `/hooks` 에서 `UserPromptSubmit`·`Stop` 훅 등록 확인, `/plugin details jansori` 에서 commands(`nag`/`save`)와 skill(`load`) 확인.
- 서버가 기본 포트 `8765` 로 떠 있으면 클라이언트가 자동으로 붙습니다 — 추가 설정 불필요. 포트를 바꿨다면 `JANSORI_URL` 로 맞추세요.

## 테스트

```bash
make test        # 전체: unit(u1..u3) + pbt + golden + verify
make pbt         # property 기반 테스트만 (Hypothesis, PBT-01..10)
make verify      # 실서버 계약 스위트 (실제 uvicorn 서버를 띄우고 종료)
```

- **`make verify` 는 진짜 서버를 띄웁니다** — ephemeral loopback 포트에서 HTTP로 구동하며, 가짜/in-memory Store 스텁은 **허용하지 않습니다**(US-17).
- **property 실패 재현(PBT-08):** 실패 시 Hypothesis가 `@reproduce_failure` 블롭과 seed를 출력합니다. `pytest --hypothesis-seed=<seed>` 로 재생하고, `JANSORI_HYPOTHESIS_PROFILE=ci|dev` 로 프로파일을 고릅니다.

---

## 아키텍처

한 사람의 잔소리가 로컬 서버의 **버전 캡슐**에 쌓이고, 다음에 켜지는 세션의 첫 프롬프트로 자동 전파되는 흐름입니다. 대화·프롬프트·소스는 서버가 수집하지 않습니다.

```text
                 [ JDD Plugin · Claude Code Plugin ]
        모든 분산 조직(본사·해외·인접 그룹)의 CLI에 단일 설치
     캡슐의 단일 원천 = 중앙 캡슐 서버 (재시작에도 스냅샷으로 영속)
                             │
      ┌──────────────────────┴──────────────────────┐
      ▼                                              ▼
[ 1. 표준 인덱스 자동 주입 ]                 [ 2. 고수의 잔소리 실시간 흡수 ]
  UserPromptSubmit Hook                        /jansori:nag → capsule-normalizer
  - 스킬 인덱스(name·description)만 주입          - 자연어 지적을 correction 으로 축적
    (본문·교정·LLM 호출 없음, 순수 HTTP GET)     - 불변 버전 v1 → v2 (copy-on-write, 원본 보존)
  - 필요한 스킬만 load 로 온디맨드 로드           - 교정 3건 도달 시 배경 서브에이전트가
    (부모 + depth-1 자식 확장)                     Normalization(압축) — 규칙 유지, 길이만 축소 (비차단)
  - Fail-open (서버가 죽어도 프롬프트 안 막음)     - 10,000자 상한 초과 시 거부·보존 후 자식 분리 권고
                             │
                             ▼
                 [ 3. 다음 작업자 무혈입성 ]
   새 터미널을 켠 뉴커머·해외 동료가 첫 프롬프트만 쳐도 최신 캡슐 자동 로드
   "어제 미국 시니어가 친 잔소리가, 오늘 내 코드에 자동으로 반영된다"
```

### 유닛 구성

```text
server/        U1  loopback FastAPI 캡슐 서버 (SPEC-8 계약의 단일 원천)
plugin/        U2  Claude Code 플러그인 (UserPromptSubmit/Stop 훅, load Skill, /jansori:* 명령)
plugin/agents/ U3  capsule-normalizer 서브에이전트 (격리; 캡슐 JSON을 GET → normalize 제출)
tests/         U4  pbt/(Hypothesis) · golden/(예시) · verify/(실서버 계약)
fixtures/          제공 입력물(seed / acceptance-golden / C++ 워크로드) — 요구사항이지 제품 소스 아님
Makefile       U4  run / seed / verify / pbt / test
```

### 무엇을 어떻게 주입하나

- **프롬프트 주입은 `UserPromptSubmit` 훅** 하나입니다. 매 프롬프트마다 (1) 행동 지침 프리앰블과 (2) `GET /skills/index` 로 가져온 **스킬 인덱스(name·description만)** 를 붙입니다. 본문·교정은 붙이지 않고, 훅 안에서 LLM 호출도 없습니다(순수 HTTP GET + 텍스트 포맷). 훅은 **fail-open** — `JANSORI_HOOK_TIMEOUT_MS`(기본 2000ms)로 제한되고, 실패하면 아무것도 출력하지 않고 정상 종료합니다(절대 exit 2로 프롬프트를 막지 않음).
- 캡슐 **본문 + depth-1 자식**은 나중에 `load` Skill이 온디맨드로 가져옵니다.
- **`Stop` 훅**은 stderr에 안내("유용한 변경은 `/jansori:save` … 또는 `/jansori:nag …`")만 출력합니다 — 컨텍스트에 주입하지도, 저장하지도 않습니다.

### 교정(nag)이 흐르는 방식

1. **대상 해석** — `/jansori:nag` → `resolve-target`. 활성 세션 범위(부모 + 로드된 자식) 안에서 **정확한 `skill_id`** 를 매칭. 0개/여러 개/힌트 없음이면 `NEEDS_CONFIRMATION`(409)로 사용자에게 되묻습니다.
2. **nag 제출** — `POST /skills/{id}/nag`. `request_id` 로 멱등 재생(I-05). `Correction`(id, target, instruction_text, request_id, seq)을 추가하고 `with_new_content` 로 **새 불변 캡슐(version+1)** 을 만듭니다(I-01). 커밋은 `expected_base_version` 로 원자적으로; 어긋나면 `STALE_BASE_VERSION`(I-04)로 같은 `request_id` 재시도.
3. **정규화(=compaction)** — 응답의 `normalize_due`(교정 수 ≥ 임계값, 기본 3)가 참이면 배경 **`capsule-normalizer`** 서브에이전트가 비차단(I-10)으로 실행됩니다. 캡슐 JSON을 `get` 하고 `body` + `corrections` 를 seq 순으로 병합(요약/의역 가능, 나중 seq 우선)한 뒤 `normalize` 를 제출. 서버는 **선언 기반 보존 검증**(I-11)으로 `new_body ≤ L`, 병합된 교정 id가 기존의 부분집합인지 확인하고, 성공 시 본문 교체 + version+1 + 병합된 교정만 제거(나중에 도착한 교정은 이월).

### 10,000자 상한과 depth-1 자식

- **10,000자 상한**은 주입 예산이 아니라 **서버측 캡슐 렌더 상한**입니다(`Limits.max_content_length`, I-09). 한 노드의 `body + corrections` 렌더가 넘치면 `OVER_LENGTH` 로 **기존 내용을 보존한 채 변경을 거부하고 자식 분리를 권고**합니다. 오래된 교정을 먼저 잘라내지 않습니다.
- **depth-1 자식 참조**(I-15): 부모가 `refs_children` 로 직속 자식만 참조. 등록·참조 변경 양방향에서 `assert_depth_one` 로 강제 — 자식이 이미 자식을 가지면 `DEPTH_LIMIT` 로 거부. 로드 시 부모는 자식의 body+corrections를 depth-1까지 확장(I-03).

### 명령 · 클라이언트 · HTTP

- **명령/엔트리:** `/jansori:nag`(교정 추가), `/jansori:save`(신규 스킬 등록; 유사 스킬 재확인, `--ref` depth-1 자식, 보호 필드 변경은 `--approve`), `load`(슬래시가 아니라 **Skill**), `capsule-normalizer`(서브에이전트).
- 공용 클라이언트 `plugin/scripts/jansori_client.py` (stdlib `urllib`만, loopback 강제, `JANSORI_URL` 기본 `http://127.0.0.1:8765`). 서브커맨드: `index`, `get`, `load`, `resolve-target`, `nag`, `register`, `protected-change`, `normalize`.
- **HTTP 라우트:** `GET /skills/index`, `GET /skills/resolve-target`, `GET /skills/{id}`, `POST /skills/register`, `POST /skills/{id}/load`, `POST /skills/{id}/nag`, `POST /skills/{id}/protected-change`, `POST /skills/{id}/normalize`, `GET /health`.

### 캡슐 구조

- `skill_id`(불변 식별자), `name`, `description`, `body`, `version`(단조 증가 정수)
- `corrections: [{id, target, instruction_text, request_id, seq, created_at}]`
- `refs_children: [str]`(depth-1 직속 자식), `assets: [{name, path, is_script}]`(temp-dir 경로 제한, 스크립트 자동 실행 안 함)
- `protected_fields`, `created_at`, `updated_at`. 버전 이력은 별도 보관(`Version{number, body_snapshot, request_id, origin, created_at}`, `origin ∈ {register, nag, normalize, protected_change}`). 모든 내용 변경은 version+1의 새 캡슐로(copy-on-write, I-01).

---

## 불변식 & 보안 (U1이 강제, U4가 검증)

I-01 불변 버전 · I-02 로드 기록 · I-03 depth-1 자식 확장 · I-04 stale 거부 ·
I-05 멱등성(request_id) · I-06 중복 등록 차단 · I-07 실패≠부재 · I-08 훅 fail-open ·
I-09 초과 길이 거부+보존 · I-10 비차단 정규화 · I-11 보존(선언된 병합 id + 길이) ·
I-12 원자적 쓰기 · I-13 nag 대상 해석 · I-14 보호 필드 승인 · I-15 저장 depth-1(양방향).

**§5 보안(확장 설정과 무관하게 필수):** loopback 전용 바인딩(127.0.0.1/::1), temp-dir 경로 격리, 스크립트 자동 실행 금지, 그리고 작업 소스/프롬프트/대화 기록을 수집하지 않음.

## 증거 정직성 (F-04)

자동 스위트가 증명하는 것과, 사람/런타임 데모가 필요한 것을 명시적으로 구분합니다.

- **여기 테스트로 검증됨:** 캡슐 서버 계약, 위 불변식 전부, 3상태(C0/C1/C2) 전파의 바탕이 되는 캡슐 버전/교정 **상태**(`tests/golden/test_three_state.py` 가 `fixtures/acceptance/three-state-golden.json` 에 대해 필드 단위로 단언).
- **여기서 검증 안 됨(실제 Claude Code 세션 필요, NOT_RUN 표시):** 플러그인/서브에이전트의 런타임 실제 구동, LLM 병합 *품질*, 실제 C++ 코드 전파(`demo-cases.json` 트랜스크립트 등). 라이브 데모에서 산출됩니다.
- **사용자 산출물(팀은 입력/콘텐츠만 제공, "완료" 표시는 하지 않음):** **데모 영상** 과 **설명 HTML/PPT**. `fixtures/acceptance/demo-cases.json`(전부 `NOT_RUN`)과 데모/시나리오/트랜스크립트 입력 참고.

DEV-01..46 acceptance-case → test / out-of-scope 전체 매핑은
`aidlc-docs/construction/U4-build-verify-seed-pbt/code/golden-coverage-matrix.md` 에 있습니다.
