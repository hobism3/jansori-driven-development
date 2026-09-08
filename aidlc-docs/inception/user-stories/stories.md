# User Stories — Jansori Plugin

> 근거: `aidlc-docs/inception/requirements/requirements.md`. 페르소나: `personas.md`.
> 형식(Q4=C): 각 스토리는 사용자 서사 + Given/When/Then 수용 기준. 각 수용 기준에 **[검증: auto|transcript]** 모드와 관련 **DEV** 케이스를 태깅.
> 분해(Q1=D): Journey 에픽(A~D) 아래 Feature 스토리 + 불변식 수용 기준. 횡단 관심사(Q5=C)는 별도 스토리(에픽 E, F).
> 3상태(Q6=C): 전파 에픽(D)에 C0/C1/C2를 수용 기준/시나리오 단계로 포함.
> 우선순위(Q7=C): 우선순위/스프린트 표기 없음. 스토리는 INVEST(독립·협상가능·가치·추정가능·작음·테스트가능)를 지향.
> 검증 모드 정의: **auto** = `make verify` 기계적 계약 검사(실제 기동 서버 대상). **transcript** = 사전 기대치 대비 실제 A/B/C 실행 증거(expected+actual). 불변식·§5·재시도는 관련 스토리의 수용 조건.

---

## 에픽 A — Skill 발견·로드·활성화 (세션 시작)

### US-01 — 작업 시작 시 skill 인덱스 주입
**As** 다음-세션 소비자(P2), **I want** 작업을 시작할 때 사용 가능한 skill 인덱스가 자동으로 주입되기를, **so that** 관련 skill을 곧바로 발견할 수 있다.
- **AC1** — Given 세션에서 사용자가 첫 프롬프트를 제출하고 서버가 정상일 때, When UserPromptSubmit 훅이 실행되면, Then 인덱스(이름/설명)가 컨텍스트에 주입된다. `[검증: auto]` (DEV-01, DEV-21)
- **AC2** — Given 훅이 서버 응답을 기다릴 때, When 상한 시간이 초과되거나 서버가 실패하면, Then 훅 대기는 유한하고 사용자 입력은 막히지 않는다(fail-open). `[검증: auto]` (I-08, DEV-21)
- **AC3** — Given 훅 실행 시, When 인덱스를 구성할 때, Then 훅 내부에서 LLM 호출을 하지 않는다. `[검증: auto]`
- **불변식**: I-08.

### US-02 — 인덱스에서 skill 선택·로드
**As** 다음-세션 소비자(P2), **I want** 인덱스의 이름/설명을 근거로 적절한 skill을 선택해 로드하기를, **so that** 해당 작업에 맞는 지시를 적용할 수 있다.
- **AC1** — Given 주입된 인덱스가 있을 때, When Claude가 이름/설명으로 skill을 선택해 `load` Skill을 호출하면, Then 해당 skill 콘텐츠가 로드된다. `[검증: transcript]` (DEV-01, DEV-25, DEV-36)
- **AC2** — Given `load`가 호출될 때, When 자연어 요청·`/jansori` 경로 어느 쪽이든, Then 공통 처리 경로를 통해 동일하게 로드된다. `[검증: auto]`
- **불변식**: — (선택 판단은 transcript).

### US-03 — 부모 로드 시 refs 자식 확장 (depth-1)
**As** 다음-세션 소비자(P2), **I want** 부모 skill을 로드하면 그 직속 자식(refs)이 body+corrections로 함께 확장되기를, **so that** 활성 범위가 부모 + 직속 자식으로 일관되게 구성된다.
- **AC1** — Given 부모 skill이 refs로 자식을 참조할 때, When 부모를 로드하면, Then 각 직속 자식의 body와 corrections가 확장·반영된다. `[검증: auto]` (DEV-02, DEV-08)
- **AC2** — Given refs 그래프에 손자(depth 2 이상)가 저장되어 있을 때, When 새 등록 또는 refs 변경이 일어나면, Then **저장된 관계** 자체가 depth 1을 넘지 못하도록 거부/제약된다(읽기 시 손자 무시로 대체하지 않음). `[검증: auto]` (I-15, DEV-03, DEV-43, DEV-44, DEV-45)
- **AC3** — Given depth-1 허용 경계 케이스일 때, When 등록/변경하면, Then 허용된다. `[검증: auto]` (DEV-46, allow-boundary)
- **불변식**: I-02, I-03, I-15.

### US-04 — 로드된 skill이 작업 실행에 반영
**As** 다음-세션 소비자(P2), **I want** 로드된 skill의 지시가 실제 작업 산출물에 반영되기를, **so that** 축적된 규칙이 결과에 실질적으로 작동한다.
- **AC1** — Given skill이 로드된 세션일 때, When 사용자가 작업을 요청하면, Then 산출물에 해당 skill 지시가 반영된다. `[검증: transcript]` (DEV-18, DEV-25, DEV-27)
- **불변식**: — (실행 반영은 transcript).

---

## 에픽 B — 저장·잔소리 (교정 포착)

### US-05 — 작업 완료 후 저장 제안
**As** 교정자(P1), **I want** 작업이 끝날 때 저장(등록/교정) 제안 알림을 받기를, **so that** 유용한 변경을 놓치지 않고 축적할 수 있다.
- **AC1** — Given 작업이 완료되어 Stop 훅이 실행될 때, When 저장할 만한 변경이 감지되면, Then 저장 제안 **알림만** 제시하고(대화·직접 저장 아님) 사용자가 선택한다. `[검증: transcript]` (DEV-05, DEV-19, DEV-26)
- **불변식**: — (Stop notice only).

### US-06 — 신규 등록 전 유사 skill 재검색
**As** 교정자(P1), **I want** 새 skill을 등록하기 전에 유사한 기존 skill을 재검색하기를, **so that** 동일 목적 skill을 중복 생성하지 않는다.
- **AC1** — Given 신규 등록 요청일 때, When 등록을 진행하기 전, Then 유사 skill 재검색을 수행한다. `[검증: auto]` (DEV-10, DEV-22)
- **AC2** — Given 동일 `skill_id`가 이미 존재할 때, When 신규 등록을 시도하면, Then 중복 신규 등록을 차단한다. `[검증: auto]` (I-06, DEV-26)
- **AC3** — Given 재검색 후 등록/교정 판단, When 유사 항목이 발견되면, Then 신규 대신 교정 경로로 안내(판단은 transcript). `[검증: transcript]`
- **불변식**: I-06, I-07.

### US-07 — 잔소리를 대상에 적용하고 version 상승
**As** 교정자(P1), **I want** 남긴 잔소리가 대상 skill의 새 version으로 누적되기를, **so that** 기존 유효 지시를 보존하면서 교정이 반영된다.
- **AC1** — Given 대상 skill의 latest version일 때, When 잔소리를 적용하면, Then 콘텐츠 version이 불변(immutable)인 새 version이 생성된다(기존 version 덮어쓰기 없음). `[검증: auto]` (I-01, DEV-04)
- **AC2** — Given 여러 교정이 누적될 때, When 순서를 기록하면, Then oldest→newest 순서가 보존되고 조건별 최신 명시 교정이 우선한다. `[검증: auto]` (DEV-05, DEV-07)
- **AC3** — Given 첫 등록일 때, Then 첫 version은 v1이다. `[검증: auto]`
- **불변식**: I-01, I-03, I-13.

### US-08 — 잔소리 대상 parent/child 판정
**As** 교정자(P1), **I want** 잔소리가 부모/자식 중 올바른 대상에 적용되기를, **so that** 엉뚱한 skill이 바뀌지 않는다.
- **AC1** — Given 잔소리 내용에 대상 단서가 있을 때, When 대상을 판정하면, Then parent/child 중 올바른 대상에 적용된다. `[검증: transcript]` (DEV-08, DEV-25)
- **AC2** — Given 대상/공유 의도가 모호할 때, When 시스템이 추론하면, Then 적용 전 사용자에게 먼저 확인한다. `[검증: transcript]` (I-13)
- **불변식**: I-13.

### US-09 — 보호 필드 변경은 승인 플래그 필요
**As** 교정자(P1), **I want** 보호 필드(name·description·keywords·assets·refs) 변경이 명시 승인 없이는 적용되지 않기를, **so that** 실수로 식별·구조가 바뀌지 않는다.
- **AC1** — Given 보호 필드 변경 요청일 때, When 승인 플래그가 없으면, Then 변경이 적용되지 않고 상태가 바뀌지 않는다. `[검증: auto]` (I-14, DEV-11, DEV-12, DEV-24)
- **AC2** — Given 승인 플래그가 있을 때, When freshness 체크를 통과하면, Then 변경이 적용된다. `[검증: auto]` (DEV-33, DEV-35)
- **AC3** — Given 승인 플래그 존재는 플래그일 뿐일 때, Then 이를 실제 인간 동의 증거로 기록하지 않는다. `[검증: transcript]` (I-14 주의)
- **불변식**: I-14.

---

## 에픽 C — 임계값·compaction (차별화 기능)

### US-10 — 임계값 판정 + base_version 기반 적용/거부 (원자적·멱등)
**As** 다음-세션 소비자·교정자, **I want** 교정 적용이 base_version 기준으로 안전하게 판정되고 재시도해도 중복되지 않기를, **so that** 경쟁/재시도 상황에서도 상태가 일관된다.
- **AC1** — Given 누적 교정 수가 임계값(=3)에 도달할 때, When 판정하면, Then compaction 트리거 조건이 인식된다. `[검증: auto]` (DEV-06, DEV-13)
- **AC2** — Given 변경 제안이 stale base_version 기반일 때, When 적용을 시도하면, Then latest를 덮어쓰지 못하고 거부된다. `[검증: auto]` (I-04, DEV-29)
- **AC3** — Given 동일 `request_id` 재시도일 때, When 다시 적용을 시도하면, Then 새 version/correction이 추가되지 않는다(멱등). `[검증: auto]` (I-05, DEV-15, DEV-23)
- **AC4** — Given 쓰기(새 version + latest 포인터 + 재시도 기록)가 일어날 때, When 동시 잔소리/백그라운드 compaction과 겹쳐도, Then 인메모리 저장소에서 원자적으로 반영된다. `[검증: auto]` (I-12, DEV-30, DEV-31, DEV-32)
- **불변식**: I-04, I-05, I-09, I-12.

### US-11 — subagent compaction이 유효 지시를 보존
**As** 다음-세션 소비자(P2), **I want** compaction이 별도 subagent에서 진행되며 유효 지시·assets/refs를 잃지 않기를, **so that** 요약 과정에서 규칙이 사라지지 않는다.
- **AC1** — Given compaction이 트리거될 때, When 백그라운드 subagent에서 실행되면, Then 소비자는 폴링/대기 없이 즉시 진행한다(진행 상태 ≠ 콘텐츠). `[검증: transcript]` (I-10, DEV-16)
- **AC2** — Given compaction이 성공할 때, When 새 version과 새 body를 쓰면, Then 유효 지시의 합집합과 assets/refs가 보존되고 corrections가 비워진다. `[검증: transcript]` (I-11, DEV-14, DEV-18)
- **AC3** — Given compaction이 실패/중단될 때, When 결과를 반영하려 하면, Then 콘텐츠는 변경되지 않는다(무변경). `[검증: transcript]` (I-11, DEV-17, DEV-28)
- **불변식**: I-10, I-11, I-12.

---

## 에픽 D — 전파 증명 (C0/C1/C2)

### US-12 — 갱신된 skill이 다음 사용자에게 전달 (3상태 전파)
**As** 다음-세션 소비자(P2) 및 운영·검증자(P3), **I want** 한 사람의 교정이 다음 새 세션의 실제 코드 변화로 전달되는 것을, **so that** 전파 루프의 핵심 명제가 증명된다.
- **AC1 (C0, 교정 전)** — Given 깨끗한 원본 워크로드 + 동일 요청으로 교정 전 상태일 때, When 소비자가 작업하면, Then 교정 미반영 산출물(기준선)이 기록된다(로드된 version 기록). `[검증: transcript]` (DEV-27)
- **AC2 (C1, 교정 후·compaction 전)** — Given 교정이 적용된 새 version(아직 compaction 전)일 때, When 다음 새 세션에서 동일 요청을 실행하면, Then 교정이 반영된 실제 코드 변화가 나타난다. `[검증: transcript]` (DEV-27, DEV-37)
- **AC3 (C2, compaction 후)** — Given compaction 후 상태일 때, When 동일 요청을 실행하면, Then 교정이 유지된 채 반영되고 기존 유효 지시가 보존된다. `[검증: transcript]` (DEV-27, DEV-28)
- **AC4** — Given 3상태 실행 시, When 각 회차를 기록하면, Then 실제 로드된 parent/child version이 회차마다 기록되고 C 환경은 golden/스크립트/B-편집/평가기/리포트를 배제한다. `[검증: transcript]` (I-02, DEV-37, DEV-38)
- **AC5** — Given 전파 증명 시, When 방식을 선택하면, Then 새 `skill_id` 복제가 동일 `skill_id` 교정 전파를 대체하지 않는다. `[검증: transcript]`
- **불변식**: I-01, I-02, I-03.

---

## 에픽 E — 신뢰성·실패 격리 (횡단)

### US-13 — 서버 실패가 사용자 작업을 막지 않음 (fail-open)
**As** 다음-세션 소비자(P2) 및 운영·검증자(P3), **I want** 서버가 느리거나 실패해도 내 작업이 진행되기를, **so that** 도구 장애가 생산성을 막지 않는다.
- **AC1** — Given 서버가 느리거나 실패할 때, When 훅/호출이 상한을 초과하면, Then 사용자 작업은 차단되지 않고 진행된다. `[검증: auto]` (I-08, DEV-21)
- **AC2** — Given 서버 실패일 때, When 상태를 판단하면, Then "서버 실패"와 "skill 부재"를 구분한다. `[검증: auto]` (I-07)
- **불변식**: I-07, I-08.

### US-14 — 서버 실패가 중복 등록을 유발하지 않음
**As** 운영·검증자(P3), **I want** 실패·재시도 상황에서 동일 skill이 중복 등록되지 않기를, **so that** 저장소 무결성이 유지된다.
- **AC1** — Given 등록 중 서버 실패/재시도가 발생할 때, When 재시도가 일어나면, Then 동일 `skill_id`의 중복 신규 등록이 생기지 않는다. `[검증: auto]` (I-06, DEV-22)
- **AC2** — Given 실패 원인이 모호할 때, When 상태를 판단하면, Then 서버 실패와 skill 부재를 구분해 처리한다. `[검증: auto]` (I-07)
- **불변식**: I-06, I-07.

---

## 에픽 F — 보안 경계·품질·증거 (횡단, Q5=C)

### US-15 — §5 보안 경계 강제
**As** 운영·검증자(P3), **I want** 서버가 §5 보안 경계를 강제하기를, **so that** 로컬 도구가 안전하게 동작하고 의도치 않은 노출/실행이 없다.
- **AC1** — Given 서버가 기동될 때, When 바인딩하면, Then `127.0.0.1`/`::1`(loopback)에만 바인딩하고 LAN에 노출하지 않는다. `[검증: auto]` (DEV-34)
- **AC2** — Given assets/refs 파일 쓰기가 일어날 때, When 경로를 해석하면, Then 지정 temp 디렉터리 내부로 격리된다(path-traversal 안전). `[검증: auto]` (DEV-24)
- **AC3** — Given Capsule에 스크립트가 포함될 때, When 처리하면, Then 자동 실행하지 않고 요약 후 명시적 사용자 동의를 요구한다. `[검증: transcript]` (DEV-24)
- **AC4** — Given 작업 소스/프롬프트 텍스트가 있을 때, When 서버가 처리하면, Then 이를 자동 수집·저장하지 않으며 사용자 포함 Capsule 콘텐츠와 구분한다. `[검증: auto]` (DEV-35)
- **AC5** — Given secret-pattern 스캔이 있을 때, Then 이는 보조 수단이며 경로 검사와 본문/스크립트 검사를 혼동하지 않는다. `[검증: auto]` (DEV-33)
- **불변식/요건**: §5(F-02).

### US-16 — 속성 기반 테스트로 불변식 검증 (PBT)
**As** 운영·검증자(P3), **I want** 핵심 불변식이 속성 기반 테스트로 검증되기를, **so that** 예제만으로 놓칠 수 있는 경계·상태 조합까지 방어한다.
- **AC1** — Given Hypothesis 기반 PBT 스위트일 때, When 실행하면, Then version 단조 증가·corrections 순서 보존·refs depth ≤ 1·과길이 거부(내용 보존)·compaction 보존 속성이 검증된다. `[검증: auto]` (PBT-03)
- **AC2** — Given Capsule/rendered 텍스트일 때, When round-trip 하면, Then 손실 없이 역가능하거나 문서화된 lossy로 검증된다. `[검증: auto]` (PBT-02)
- **AC3** — Given 동일 `request_id` 재시도/무승인 보호 변경일 때, When 실행하면, Then 상태 무변경(멱등) 속성이 성립한다. `[검증: auto]` (PBT-04)
- **AC4** — Given 무작위 명령 시퀀스(register/load/nag/protected-change/compaction/retry)일 때, When stateful 테스트로 실행하면, Then 각 단계 후 I-01..I-14가 유지된다. `[검증: auto]` (PBT-06)
- **AC5** — Given 실패가 발생할 때, When 재현하면, Then shrinking·seed 로깅으로 재현 가능하고 CI에서 실행된다. `[검증: auto]` (PBT-08); 각 핵심 경로는 golden 기대치 예제 테스트도 병행. (PBT-10)
- **요건**: PBT-01..10.

### US-17 — 증거 정직성과 검증 접근
**As** 운영·검증자(P3), **I want** 검증이 실제 기동 서버 기계 계약 + 실제 transcript 증거로 이뤄지고 미수행 항목이 정직하게 표기되기를, **so that** 검증 결과를 신뢰할 수 있다.
- **AC1** — Given `make verify`를 실행할 때, When 검사하면, Then 실제 서버를 in-test로 기동/종료하며 자격증명 없이 기계적 계약을 검사한다(가짜 Store 통과 ≠ 검증). `[검증: auto]`
- **AC2** — Given transcript 항목일 때, When 증거로 인정하려면, Then expected와 actual이 모두 있어야 한다(둘 중 하나면 단순 로그). `[검증: transcript]`
- **AC3** — Given 시연/동의/이해도 점검 항목일 때, When 기록하면, Then 실제 수행 후에만 완료로 기록하고 unverified/failed/unimplemented/approved-exclusion을 구분한다(F-04). `[검증: transcript]`
- **AC4** — Given 샘플 기능 검사와 실제 전파 증거일 때, When 기록하면, Then 둘을 분리하고 C-original/golden을 수정해 EXPECTED_INCOMPLETE를 충족시키지 않는다. `[검증: transcript]`
- **요건**: §7/§11 F-04, deliverables 표.

---

## 추적성 매트릭스 (스토리 → 요구사항/불변식/DEV)

| Story | 페르소나 | R-ID | 불변식/요건 | DEV 케이스 | 주 검증 |
|---|---|---|---|---|---|
| US-01 | P2 | R-01 | I-08 | DEV-01, DEV-21 | auto |
| US-02 | P2 | R-02 | — | DEV-01, DEV-25, DEV-36 | transcript |
| US-03 | P2 | R-03 | I-02, I-03, I-15 | DEV-02, DEV-03, DEV-08, DEV-43..46 | auto |
| US-04 | P2 | R-04 | — | DEV-18, DEV-25, DEV-27 | transcript |
| US-05 | P1 | R-05 | — | DEV-05, DEV-19, DEV-26 | transcript |
| US-06 | P1 | R-06 | I-06, I-07 | DEV-10, DEV-22, DEV-26 | auto/transcript |
| US-07 | P1 | R-07 | I-01, I-03, I-13 | DEV-04, DEV-05, DEV-07 | auto |
| US-08 | P1 | R-08 | I-13 | DEV-08, DEV-25 | transcript |
| US-09 | P1 | R-11 | I-14 | DEV-11, DEV-12, DEV-24, DEV-33, DEV-35 | auto |
| US-10 | P1/P2 | R-09 | I-04, I-05, I-09, I-12 | DEV-06, DEV-07, DEV-13, DEV-15, DEV-23, DEV-29..32 | auto |
| US-11 | P2 | R-10 | I-10, I-11, I-12 | DEV-14, DEV-16, DEV-17, DEV-18, DEV-28 | transcript |
| US-12 | P2/P3 | R-14 | I-01, I-02, I-03 | DEV-27, DEV-28, DEV-37, DEV-38 | transcript |
| US-13 | P2/P3 | R-12 | I-07, I-08 | DEV-21 | auto |
| US-14 | P3 | R-13 | I-06, I-07 | DEV-22 | auto |
| US-15 | P3 | §5 (F-02) | §5 경계 | DEV-24, DEV-33, DEV-34, DEV-35 | auto/transcript |
| US-16 | P3 | PBT | PBT-01..10 | (속성 전반) | auto |
| US-17 | P3 | §7/§11 (F-04) | 증거 정직성 | (deliverables) | transcript |

**커버리지 확인**: R-01..R-14 전부 US-01..US-14에 1:1 정렬. 불변식 I-01..I-15 전부 하나 이상의 스토리 수용 기준에 매핑(특히 I-15 → US-03 AC2, 저장 관계 depth-1 양방향). 횡단 요건 §5/PBT/F-04 → US-15/US-16/US-17.
