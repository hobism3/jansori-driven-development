# U1 Business Rules — Server & Store & Contracts

> 각 규칙 = 검증 가능한 문장 + **PBT 속성 후보**(활성 확장 PBT full). 값·경계는 D-03/확정답 Q1..Q10=A.
> ⚠️ "정상화" = SPEC "compaction" ≠ Claude Code context compaction.

---

## 1. 불변식 규칙 (I-01..I-15)

| ID | 규칙 문장 (검증 가능) | PBT 속성 후보 |
|---|---|---|
| **I-01** | 부여된 version의 body_snapshot은 절대 변경되지 않는다. 콘텐츠 변경은 항상 version+1. | 임의의 연산열 후에도 과거 version의 body_snapshot 불변; version은 콘텐츠 변경 횟수와 단조 증가 일치. |
| **I-02** | load 성공 시 세션에 실제 로드한 parent/children의 skill_id+version이 기록된다. | load 후 active_scope의 version == 그 시점 store latest version. |
| **I-03** | parent 로드 시 depth-1 직속 자식 body+corrections가 확장 전달된다. 부모·자식 모두 교정 대상. | refs_children 있는 parent load 결과에 각 child 콘텐츠 포함; child nag가 정상 적용. |
| **I-04** | base_version != current.version인 쓰기는 거부(STALE_BASE_VERSION), 상태 무변경. | 오래된 base_version으로 nag/normalize/protected-change 시 거부 + 상태 불변. |
| **I-05** | 동일 request_id 재수신은 새 version/correction을 만들지 않고 직전 결과를 반환. | 같은 요청 N회 반복 == 1회 적용(멱등); version 증가 정확히 1. |
| **I-06** | 이미 존재하는 skill_id 신규 등록은 DUPLICATE_REGISTRATION로 차단. | 등록된 skill_id 재등록 시 항상 거부, 기존 Capsule 불변. |
| **I-07** | 서버 실패(SERVER_ERROR)와 skill 부재(SKILL_ABSENT)는 구분된다. | 부재 조회 -> SKILL_ABSENT(정상 응답); 주입 실패 -> SERVER_ERROR; 둘은 다른 코드. |
| **I-09** | body/correction/합성 렌더가 L(=10,000) 초과면 OVER_LENGTH, **콘텐츠 보존·변경 거부**(truncate 아님). | 임의 초과 입력 -> 거부 + 기존 상태 불변; L 이하 -> 통과. |
| **I-10** | 진행 플래그 변경은 콘텐츠 바이트를 바꾸지 않는다. 정상화 중에도 소비자 비차단. | progress_flag 토글 전후 body/version 불변; normalize_in_progress 중 nag/load 정상 진행. |
| **I-11** | 정상화 커밋은 유효 지시·assets·refs를 보존한다. 실패 시 콘텐츠 무변경. | validate_preservation PASS만 커밋; assets/refs 집합 보존; FAIL 시 body/version 불변. |
| **I-12** | 새 version + latest 포인터 + request_id 기록은 하나의 원자 단위. 부분 저장 없음. | 동시 nag+정상화 겹침에도 중간 상태 관측 불가; latest는 항상 완결 version. |
| **I-13** | 잔소리 대상(parent/child)은 활성 범위에서 판정; 모호 시 NEEDS_CONFIRMATION. | 유일 매칭 -> 정확한 target; 0/다중 -> NEEDS_CONFIRMATION; 자동 parent 귀속 없음. |
| **I-14** | 보호 필드 변경은 approval 플래그 + freshness 필요; 미충족 시 PROTECTED_CHANGE_DENIED. | approval 없이 보호필드 변경 -> 거부; body/corrections는 nag로 자유 변경. |
| **I-15** | 저장 관계 depth ≤ 1. 손자를 만드는 등록/refs 변경은 DEPTH_LIMIT, 상태 무변경. | 자식이 자식을 갖는 연결 -> 거부; depth-1 정확 경계는 허용. |

---

## 2. 상한·경계 규칙 (D-03)

| 규칙 | 값/동작 |
|---|---|
| 길이 상한 L | **10,000자**(설정 가능, 기본 10,000). body / correction 개별 / depth-1 자식 합성 각각 검사(Q6=A). |
| 정상화 임계값 | corrections **== 3**(설정 가능, 기본 3; aidlc-state Q5=B). 데모 정렬. |
| 훅 fail-open 상한 | 2,000ms — **U2 책임**(서버 규칙 아님). 서버는 정상 응답만 담당. |
| request_id | UUID, 필수(쓰기). 미제공은 입력 검증 오류. 전역 멱등(Q10=A). |
| refs depth | ≤ 1(I-15). 신규 등록·refs 변경 둘 다 검사. |

---

## 3. 구조화 오류 코드 매핑 (D-03)

```
{ "error": { "code": <CODE>, "message": "...", "detail"?: {...} } }
```
| CODE | 발생 조건 | 상태 변경 |
|---|---|---|
| `STALE_BASE_VERSION` | base_version != current.version | 무변경 |
| `OVER_LENGTH` | body/correction/합성 > L | 무변경(보존) |
| `PROTECTED_CHANGE_DENIED` | 보호필드 변경에 approval/freshness 미충족 | 무변경 |
| `SKILL_ABSENT` | 조회/대상 skill 부재 (서버 정상) | 무변경 |
| `SERVER_ERROR` | 서버 내부 실패 | 불특정(호출측 재시도/fail-open) |
| `DEPTH_LIMIT` | refs 손자 발생 | 무변경(+위반 경로·권고) |
| `DUPLICATE_REGISTRATION` | 기존 skill_id 재등록 | 무변경 |

**SERVER_ERROR vs SKILL_ABSENT 구분 규칙 (I-07)**: 서버가 요청을 정상 처리했으나 대상이 없으면 `SKILL_ABSENT`(2xx/4xx 의미론상 "정상 응답, 자원 없음"). 서버 자체 장애(예외/타임아웃/의존 실패)는 `SERVER_ERROR`. 호출측은 SERVER_ERROR에 fail-open/재시도, SKILL_ABSENT에는 부재로 취급(중복 등록 유발 금지, US-14).

---

## 4. §5 보안 규칙 (US-15, 확장 OFF여도 필수 제품 요건)

| 규칙 | 문장 | 검증 |
|---|---|---|
| 루프백 전용 | 서버는 127.0.0.1/::1에만 바인딩. 외부 인터페이스 바인딩 시 기동 거부. | 비루프백 host로 기동 시도 -> 거부. |
| 경로 격리 | assets/refs 파일 쓰기는 지정 temp-dir 하위로 격리(path-traversal 차단). | `../` 등 이탈 경로 -> 거부. |
| 스크립트 비자동실행 | 스크립트 자산 자동 실행 금지; 요약(ScriptNotice) 후 명시 동의. | 스크립트 자산 등록 -> 실행 안 됨, notice 반환. |
| 무수집 | 작업 소스/프롬프트/대화 트랜스크립트를 서버가 수집·저장하지 않음. | 요청에 트랜스크립트 없음; 저장소에 트랜스크립트 필드 부재. |

---

## 5. PBT 속성 세트 (활성 확장, US-16 / PBT-01..10 대비)

U1 도메인·저장소가 주 대상. Code Generation/U4에서 Hypothesis로 구현.

| 속성 | 내용 |
|---|---|
| P-멱등 | 동일 request_id 반복 == 1회(I-05). |
| P-단조version | 콘텐츠 변경 횟수와 version 단조 증가 일치(I-01). |
| P-불변스냅샷 | 과거 version body_snapshot 불변(I-01). |
| P-stale거부 | 오래된 base_version 쓰기 거부·무변경(I-04). |
| P-과길이보존 | L 초과 입력 거부 + 상태 불변(I-09). |
| P-중복차단 | 등록된 skill_id 재등록 거부(I-06). |
| P-depth1 | 손자 유발 등록/refs 변경 거부(I-15). |
| P-보존 | 정상화 커밋 후 assets/refs 집합 보존, corrections 유효 지시 추적(I-11). |
| P-원자성(stateful) | 임의 연산 시퀀스 후 latest는 항상 완결 version, 부분 상태 관측 불가(I-12). |
| P-oracle/golden | 핵심 경로 golden 예제와 일치(PBT-10). |

---

## 6. 엣지 케이스·대체 흐름

| 케이스 | 처리 |
|---|---|
| 정상화 중 추가 nag 도착 | 정상 누적(version+1), normalize_in_progress 유지. 커밋 시 base 불일치면 STALE 재시작(Q7=A). |
| resolve_target 후보 0개 | NEEDS_CONFIRMATION (활성 skill 없음 또는 hint 불일치). |
| resolve_target 다중 매칭 | NEEDS_CONFIRMATION (parent+child 동명 등). |
| load 중 child 부재 | 해당 child는 SKILL_ABSENT로 표기(부분 확장) 또는 오류 표면화 — v1: 누락 child는 확장에서 제외+경고(콘텐츠 무결성 우선). |
| depth-1 정확 경계(자식이 자식 없음) | 허용(DEV-46). |
| 보호필드를 일반 nag로 변경 시도 | 어댑터 라우팅: 보호필드는 protected-change 경로만; nag로 오면 거부. |
| request_id 누락(쓰기) | 입력 검증 오류로 거부(멱등 보장 불가). |
| 동시 두 클라이언트가 같은 skill_id 등록 | 락 하에 하나만 성공, 다른 하나 DUPLICATE_REGISTRATION(I-06/I-12). |
| 정상화 커밋 보존 검증 실패 | 커밋 거부, 콘텐츠 무변경, 서브에이전트에 실패 신호(I-11). |
| assets 경로 이탈 | contain_path 거부(§5). |

---

## 7. 추적성 (요구·DEV 매핑)
- I-01..I-15 → domain-entities.md 매핑표 + business-logic-model.md BL-1..BL-12.
- D-01(세션)→BL-10 / D-02(API)→BL-1..8 / D-03(오류·상한)→§2·§3 / D-04(원자성)→BL-11 / D-05(플러그인)→U2 / D-06(refs)→BL-2·I-15 / D-07(정상화)→BL-6·BL-7.
- §5 → §4 / PBT → §5 / F-04 증거 정직성 → U4(본 단위는 상태 전이 근거 제공).
